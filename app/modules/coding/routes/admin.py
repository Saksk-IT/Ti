# -*- coding: utf-8 -*-
"""编程题管理端路由"""
from flask import Blueprint, request, jsonify, session, current_app, render_template
from typing import Dict, Any
from sqlalchemy import func, case, distinct
from app.core.extensions import db
from app.core.utils.decorators import admin_required
from app.core.utils.cache_utils import bump_subjects_version
from app.models.coding import CodingSubject, CodingQuestion, CodeSubmission
from app.modules.coding.services.question_service import QuestionService
from app.modules.coding.schemas.question_schemas import (
    QuestionCreateSchema,
    QuestionUpdateSchema
)

coding_admin_bp = Blueprint('coding_admin', __name__)


# ==================== 管理端页面路由 ====================

@coding_admin_bp.route('/')
@admin_required
def admin_coding_dashboard():
    """编程管理主页面（集成所有管理功能）"""
    return render_template('admin/coding/dashboard.html')


@coding_admin_bp.route('/subjects')
@admin_required
def admin_subjects_page():
    """题目集（科目）管理页面（独立页面，保留兼容性）"""
    return render_template('admin/coding/subjects.html')


@coding_admin_bp.route('/questions')
@admin_required
def admin_questions_page():
    """题目管理页面（独立页面，保留兼容性）"""
    subject_id = request.args.get('subject', type=int)
    return render_template('admin/coding/questions.html', subject_id=subject_id or 0)


@coding_admin_bp.route('/questions/edit')
@coding_admin_bp.route('/questions/edit/<int:question_id>')
@admin_required
def admin_question_edit_page(question_id: int = None):
    """题目编辑页面（创建/编辑）"""
    subject_id = request.args.get('subject', type=int)
    return render_template('admin/coding/edit.html', question_id=question_id, subject_id=subject_id or 0)


# ==================== 题目集管理API ====================

@coding_admin_bp.route('/api/subjects', methods=['GET'])
@admin_required
def api_get_subjects():
    """获取题目集列表（管理端）"""
    try:
        rows = (
            db.session.query(
                CodingSubject.id,
                CodingSubject.name,
                CodingSubject.description,
                CodingSubject.is_locked,
                CodingSubject.created_at,
                func.count(distinct(case(
                    (CodingQuestion.q_type == '函数题', CodingQuestion.id),
                ))).label('function_count'),
                func.count(distinct(case(
                    (CodingQuestion.q_type == '编程题', CodingQuestion.id),
                ))).label('coding_count'),
                func.count(distinct(CodingQuestion.id)).label('total_count'),
            )
            .outerjoin(CodingQuestion, CodingSubject.id == CodingQuestion.coding_subject_id)
            .group_by(
                CodingSubject.id,
                CodingSubject.name,
                CodingSubject.description,
                CodingSubject.is_locked,
                CodingSubject.created_at,
            )
            .order_by(CodingSubject.id)
            .all()
        )

        subjects = []
        for row in rows:
            try:
                subjects.append({
                    'id': row.id,
                    'name': row.name or '',
                    'description': row.description or '',
                    'is_locked': bool(row.is_locked) if row.is_locked is not None else False,
                    'created_at': str(row.created_at) if row.created_at else '',
                    'function_count': row.function_count or 0,
                    'coding_count': row.coding_count or 0,
                    'total_count': row.total_count or 0,
                })
            except Exception as row_error:
                current_app.logger.error(f"处理行数据失败: {row_error}")
                continue

        return jsonify({
            'status': 'success',
            'data': {
                'subjects': subjects
            }
        }), 200
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        current_app.logger.error("获取题目集列表失败: %s" % e, exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目集列表失败: ' + str(e)
        }), 500


@coding_admin_bp.route('/api/subjects', methods=['POST'])
@admin_required
def api_create_subject():
    """创建题目集"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        is_locked = data.get('is_locked', False)

        if not name:
            return jsonify({'status': 'error', 'message': '题目集名称不能为空'}), 400

        try:
            new_subject = CodingSubject(
                name=name,
                description=description,
                is_locked=bool(is_locked),
            )
            db.session.add(new_subject)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': '题目集创建成功',
                'data': {
                    'id': new_subject.id,
                    'name': new_subject.name,
                    'description': new_subject.description or '',
                    'is_locked': bool(new_subject.is_locked),
                    'created_at': str(new_subject.created_at) if new_subject.created_at else '',
                }
            }), 201
        except Exception as e:
            db.session.rollback()
            err_str = str(e).lower()
            if 'unique' in err_str or 'duplicate' in err_str:
                return jsonify({'status': 'error', 'message': '题目集名称已存在'}), 400
            raise

    except Exception as e:
        current_app.logger.error("创建题目集失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '创建题目集失败'}), 500


@coding_admin_bp.route('/api/subjects/<int:subject_id>', methods=['PUT'])
@admin_required
def api_update_subject(subject_id: int):
    """更新题目集"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        is_locked = data.get('is_locked', False)

        if not name:
            return jsonify({'status': 'error', 'message': '题目集名称不能为空'}), 400

        try:
            subject = CodingSubject.query.get(subject_id)
            if not subject:
                return jsonify({'status': 'error', 'message': '题目集不存在'}), 404

            subject.name = name
            subject.description = description
            subject.is_locked = bool(is_locked)
            db.session.commit()

            try:
                bump_subjects_version()
            except Exception:
                pass

            return jsonify({
                'status': 'success',
                'message': '题目集更新成功',
                'data': {
                    'id': subject.id,
                    'name': subject.name,
                    'description': subject.description or '',
                    'is_locked': bool(subject.is_locked),
                    'created_at': str(subject.created_at) if subject.created_at else '',
                }
            }), 200
        except Exception as e:
            db.session.rollback()
            err_str = str(e).lower()
            if 'unique' in err_str or 'duplicate' in err_str:
                return jsonify({'status': 'error', 'message': '题目集名称已存在'}), 400
            raise

    except Exception as e:
        current_app.logger.error("更新题目集失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '更新题目集失败'}), 500


@coding_admin_bp.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
@admin_required
def api_delete_subject(subject_id: int):
    """删除题目集"""
    try:
        question_count = CodingQuestion.query.filter_by(coding_subject_id=subject_id).count()

        if question_count > 0:
            msg = '该题目集下还有 %d 道题目，无法删除' % question_count
            return jsonify({'status': 'error', 'message': msg}), 400

        deleted = CodingSubject.query.filter_by(id=subject_id).delete()
        db.session.commit()

        if not deleted:
            return jsonify({'status': 'error', 'message': '题目集不存在'}), 404

        return jsonify({'status': 'success', 'message': '题目集删除成功'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("删除题目集失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '删除题目集失败'}), 500


# ==================== 题目管理API ====================

@coding_admin_bp.route('/api/questions', methods=['GET'])
@admin_required
def api_get_questions():
    """获取题目列表（管理端）"""
    try:
        subject_id = request.args.get('subject_id', type=int)
        q_type = request.args.get('q_type')
        difficulty = request.args.get('difficulty')
        is_enabled = request.args.get('is_enabled')
        keyword = request.args.get('keyword', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        base_q = db.session.query(
            CodingQuestion.id,
            CodingQuestion.coding_subject_id,
            CodingQuestion.title,
            CodingQuestion.q_type,
            CodingQuestion.description,
            CodingQuestion.difficulty,
            CodingQuestion.code_template,
            CodingQuestion.test_cases_json,
            CodingQuestion.is_enabled,
            CodingSubject.name.label('subject_name'),
            func.count(distinct(CodeSubmission.id)).label('total_submissions'),
            func.count(distinct(case(
                (CodeSubmission.status == 'accepted', CodeSubmission.id),
            ))).label('accepted_submissions'),
        ).outerjoin(
            CodingSubject, CodingQuestion.coding_subject_id == CodingSubject.id
        ).outerjoin(
            CodeSubmission, CodingQuestion.id == CodeSubmission.question_id
        )

        if subject_id:
            base_q = base_q.filter(CodingQuestion.coding_subject_id == subject_id)
        if q_type:
            base_q = base_q.filter(CodingQuestion.q_type == q_type)
        if difficulty:
            base_q = base_q.filter(CodingQuestion.difficulty == difficulty)
        if is_enabled is not None:
            base_q = base_q.filter(CodingQuestion.is_enabled == bool(is_enabled))
        if keyword:
            like_pattern = '%%' + keyword + '%%'
            base_q = base_q.filter(
                db.or_(
                    CodingQuestion.title.ilike(like_pattern),
                    CodingQuestion.description.ilike(like_pattern),
                )
            )

        count_q = CodingQuestion.query
        if subject_id:
            count_q = count_q.filter(CodingQuestion.coding_subject_id == subject_id)
        if q_type:
            count_q = count_q.filter(CodingQuestion.q_type == q_type)
        if difficulty:
            count_q = count_q.filter(CodingQuestion.difficulty == difficulty)
        if is_enabled is not None:
            count_q = count_q.filter(CodingQuestion.is_enabled == bool(is_enabled))
        if keyword:
            like_pattern = '%%' + keyword + '%%'
            count_q = count_q.filter(
                db.or_(
                    CodingQuestion.title.ilike(like_pattern),
                    CodingQuestion.description.ilike(like_pattern),
                )
            )
        total = count_q.count()

        offset = (page - 1) * per_page
        rows = (
            base_q
            .group_by(
                CodingQuestion.id,
                CodingQuestion.coding_subject_id,
                CodingQuestion.title,
                CodingQuestion.q_type,
                CodingQuestion.description,
                CodingQuestion.difficulty,
                CodingQuestion.code_template,
                CodingQuestion.test_cases_json,
                CodingQuestion.is_enabled,
                CodingSubject.name,
            )
            .order_by(CodingQuestion.id.desc())
            .limit(per_page)
            .offset(offset)
            .all()
        )

        questions = []
        for row in rows:
            total_sub = row.total_submissions or 0
            accepted_sub = row.accepted_submissions or 0
            acceptance_rate = (accepted_sub / total_sub) if total_sub > 0 else None

            questions.append({
                'id': row.id,
                'subject_id': row.coding_subject_id or 0,
                'subject_name': row.subject_name or '',
                'title': row.title or '',
                'content': row.title or '',
                'q_type': row.q_type or '编程题',
                'description': row.description or '',
                'difficulty': row.difficulty or 'easy',
                'code_template': row.code_template or '',
                'test_cases_json': row.test_cases_json or '',
                'is_enabled': bool(row.is_enabled),
                'total_submissions': total_sub,
                'acceptance_rate': acceptance_rate,
            })

        return jsonify({
            'status': 'success',
            'data': {
                'questions': questions,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200
    except Exception as e:
        current_app.logger.error("获取题目列表失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '获取题目列表失败'}), 500


@coding_admin_bp.route('/api/questions', methods=['POST'])
@admin_required
def api_create_question():
    """创建题目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400

        try:
            schema = QuestionCreateSchema.model_validate(data)
        except Exception as e:
            return jsonify({'status': 'error', 'message': '数据验证失败: ' + str(e)}), 400

        question = QuestionService.create_question(schema)

        return jsonify({'status': 'success', 'message': '题目创建成功', 'data': question}), 201

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error("创建题目失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '创建题目失败'}), 500


@coding_admin_bp.route('/api/questions/<int:question_id>', methods=['PUT'])
@admin_required
def api_update_question(question_id: int):
    """更新题目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400

        try:
            schema = QuestionUpdateSchema.model_validate(data)
        except Exception as e:
            return jsonify({'status': 'error', 'message': '数据验证失败: ' + str(e)}), 400

        question = QuestionService.update_question(question_id, schema)

        return jsonify({'status': 'success', 'message': '题目更新成功', 'data': question}), 200

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        current_app.logger.error("更新题目失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '更新题目失败'}), 500


@coding_admin_bp.route('/api/questions/<int:question_id>', methods=['DELETE'])
@admin_required
def api_delete_question(question_id: int):
    """删除题目"""
    try:
        success = QuestionService.delete_question(question_id)

        if not success:
            return jsonify({'status': 'error', 'message': '题目不存在或删除失败'}), 404

        return jsonify({'status': 'success', 'message': '题目删除成功'}), 200

    except Exception as e:
        current_app.logger.error("删除题目失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '删除题目失败'}), 500


@coding_admin_bp.route('/api/questions/batch_delete', methods=['POST'])
@admin_required
def api_batch_delete_questions():
    """批量删除题目"""
    try:
        data = request.get_json()
        if not data or 'ids' not in data:
            return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400

        ids = data.get('ids', [])
        if not isinstance(ids, list) or len(ids) == 0:
            return jsonify({'status': 'error', 'message': '请提供要删除的题目ID列表'}), 400

        deleted_count = 0
        for question_id in ids:
            if QuestionService.delete_question(question_id):
                deleted_count += 1

        return jsonify({
            'status': 'success',
            'message': '成功删除 %d 道题目' % deleted_count,
            'data': {
                'deleted_count': deleted_count,
                'total_count': len(ids)
            }
        }), 200

    except Exception as e:
        current_app.logger.error("批量删除题目失败: %s" % e, exc_info=True)
        return jsonify({'status': 'error', 'message': '批量删除题目失败'}), 500
