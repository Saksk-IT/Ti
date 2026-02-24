# -*- coding: utf-8 -*-
"""编程题API路由"""
from flask import Blueprint, request, jsonify, session, current_app
from typing import Dict, Any
from sqlalchemy import func, case, distinct
from app.core.extensions import db, limiter
from app.core.utils.decorators import login_required
from app.models.coding import CodingSubject, CodingQuestion, CodeSubmission, CodeDraft
from app.models.user import User
from app.modules.coding.services.code_executor import PythonExecutor
from app.modules.coding.services.judge_service import JudgeService
from app.modules.coding.services.question_service import QuestionService
from app.modules.coding.services.submission_service import SubmissionService
from app.modules.coding.schemas.submission_schemas import (
    ExecuteCodeSchema,
    SubmitCodeSchema
)

coding_api_bp = Blueprint('coding_api', __name__)


# ==================== 题目相关API ====================

@coding_api_bp.route('/subjects', methods=['GET'])
@login_required
def api_get_subjects():
    """获取科目列表（用于筛选）"""
    try:
        rows = CodingSubject.query.order_by(CodingSubject.id).all()

        subjects = []
        for row in rows:
            try:
                subjects.append({
                    'id': row.id,
                    'name': row.name or ''
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
        current_app.logger.error(f"获取科目列表失败: {e}\n{error_detail}")
        return jsonify({
            'status': 'error',
            'message': f'获取科目列表失败: {str(e)}'
        }), 500


@coding_api_bp.route('/subjects/stats', methods=['GET'])
@login_required
def api_get_subjects_stats():
    """获取科目统计信息（用于首页展示）"""
    try:
        user_id = session.get('user_id')

        rows = (
            db.session.query(
                CodingSubject.id,
                CodingSubject.name,
                func.count(distinct(CodingQuestion.id)).label('total_questions'),
                func.count(distinct(case(
                    (CodeSubmission.status == 'accepted', CodingQuestion.id),
                ))).label('solved_questions'),
                func.count(distinct(CodeSubmission.id)).label('total_submissions'),
            )
            .outerjoin(CodingQuestion, CodingSubject.id == CodingQuestion.coding_subject_id)
            .outerjoin(
                CodeSubmission,
                db.and_(
                    CodingQuestion.id == CodeSubmission.question_id,
                    CodeSubmission.user_id == user_id,
                ),
            )
            .group_by(CodingSubject.id, CodingSubject.name)
            .order_by(CodingSubject.id)
            .all()
        )

        subjects = []
        for row in rows:
            total = row.total_questions or 0
            solved = row.solved_questions or 0
            subjects.append({
                'id': row.id,
                'name': row.name,
                'total_questions': total,
                'solved_questions': solved,
                'total_submissions': row.total_submissions or 0,
                'progress_rate': (solved / total * 100) if total > 0 else 0
            })

        return jsonify({
            'status': 'success',
            'data': {
                'subjects': subjects
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取科目统计失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取科目统计失败'
        }), 500


@coding_api_bp.route('/subjects/<int:subject_id>/overview', methods=['GET'])
@login_required
def api_get_subject_overview(subject_id: int):
    """获取题目集（科目）概述信息"""
    try:
        user_id = session.get('user_id')

        # 获取科目基本信息
        subject = CodingSubject.query.get(subject_id)
        if not subject:
            return jsonify({
                'status': 'error',
                'message': '科目不存在'
            }), 404

        # 获取题目统计
        question_stats = (
            db.session.query(
                func.count(distinct(CodingQuestion.id)).label('total_questions'),
                func.count(distinct(case(
                    (CodeSubmission.status == 'accepted', CodingQuestion.id),
                ))).label('solved_questions'),
                func.count(distinct(CodeSubmission.id)).label('total_submissions'),
            )
            .outerjoin(
                CodeSubmission,
                db.and_(
                    CodingQuestion.id == CodeSubmission.question_id,
                    CodeSubmission.user_id == user_id,
                ),
            )
            .filter(CodingQuestion.coding_subject_id == subject_id)
            .first()
        )

        # 获取各难度统计（包含已解决数量）
        type_stats = (
            db.session.query(
                CodingQuestion.difficulty,
                func.count(distinct(CodingQuestion.id)).label('total_count'),
                func.count(distinct(case(
                    (db.and_(CodeSubmission.status == 'accepted', CodeSubmission.user_id == user_id), CodeSubmission.question_id),
                ))).label('solved_count'),
            )
            .outerjoin(CodeSubmission, CodingQuestion.id == CodeSubmission.question_id)
            .filter(CodingQuestion.coding_subject_id == subject_id)
            .group_by(CodingQuestion.difficulty)
            .all()
        )

        # 计算用户分数
        user_score = (
            db.session.query(
                func.count(distinct(CodeSubmission.question_id)).label('solved_count'),
                func.sum(case(
                    (CodeSubmission.status == 'accepted', 1),
                    else_=0,
                )).label('accepted_count'),
            )
            .join(CodingQuestion, CodeSubmission.question_id == CodingQuestion.id)
            .filter(
                CodeSubmission.user_id == user_id,
                CodingQuestion.coding_subject_id == subject_id,
            )
            .first()
        )

        # 计算当前用户已解决题目数
        my_solved = (
            db.session.query(func.count(distinct(CodeSubmission.question_id)))
            .join(CodingQuestion, CodeSubmission.question_id == CodingQuestion.id)
            .filter(
                CodeSubmission.user_id == user_id,
                CodeSubmission.status == 'accepted',
                CodingQuestion.coding_subject_id == subject_id,
            )
            .scalar()
        ) or 0

        # 计算排名（基于已解决题目数）
        users_with_more = (
            db.session.query(func.count())
            .select_from(
                db.session.query(CodeSubmission.user_id)
                .join(CodingQuestion, CodeSubmission.question_id == CodingQuestion.id)
                .filter(
                    CodeSubmission.status == 'accepted',
                    CodingQuestion.coding_subject_id == subject_id,
                )
                .group_by(CodeSubmission.user_id)
                .having(func.count(distinct(CodeSubmission.question_id)) > my_solved)
                .subquery()
            )
            .scalar()
        ) or 0
        rank = users_with_more + 1

        # 获取用户首次提交时间
        first_submitted_at = (
            db.session.query(func.min(CodeSubmission.submitted_at))
            .join(CodingQuestion, CodeSubmission.question_id == CodingQuestion.id)
            .filter(
                CodeSubmission.user_id == user_id,
                CodingQuestion.coding_subject_id == subject_id,
            )
            .scalar()
        )

        # 获取总参与人数
        total_participants = (
            db.session.query(func.count(distinct(CodeSubmission.user_id)))
            .join(CodingQuestion, CodeSubmission.question_id == CodingQuestion.id)
            .filter(CodingQuestion.coding_subject_id == subject_id)
            .scalar()
        ) or 0

        # 构建题型统计
        difficulty_stats = {}
        for stat in type_stats:
            difficulty = stat.difficulty or 'easy'
            difficulty_stats[difficulty] = {
                'total': stat.total_count or 0,
                'solved': stat.solved_count or 0
            }

        total_q = (question_stats.total_questions or 0) if question_stats else 0
        solved_q = (question_stats.solved_questions or 0) if question_stats else 0
        total_sub = (question_stats.total_submissions or 0) if question_stats else 0

        overview = {
            'subject': {
                'id': subject.id,
                'name': subject.name or '',
                'description': subject.description or ''
            },
            'question_stats': {
                'total': total_q,
                'solved': solved_q,
                'total_submissions': total_sub,
                'difficulty_stats': difficulty_stats
            },
            'user_stats': {
                'score': (user_score.solved_count or 0) if user_score else 0,
                'solved_count': (user_score.accepted_count or 0) if user_score else 0,
                'rank': rank,
                'total_participants': total_participants,
                'first_submitted_at': str(first_submitted_at) if first_submitted_at else None,
                'progress_rate': (solved_q / total_q * 100) if total_q > 0 else 0
            },
            'status': {
                'is_open': True,
                'type': 'fixed',
                'set_type': 'normal'
            }
        }

        return jsonify({
            'status': 'success',
            'data': overview
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取题目集概述失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目集概述失败'
        }), 500


@coding_api_bp.route('/questions', methods=['GET'])
@login_required
def api_get_questions():
    """获取题目列表"""
    try:
        subject_id = request.args.get('subject', type=int)
        difficulty = request.args.get('difficulty')
        status = request.args.get('status', 'all')
        keyword = request.args.get('keyword', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        user_id = session.get('user_id')
        result = QuestionService.get_questions(
            subject_id=subject_id,
            difficulty=difficulty,
            status=status,
            keyword=keyword,
            page=page,
            per_page=per_page,
            user_id=user_id
        )

        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        current_app.logger.error(f"获取题目列表失败: {e}\n{error_detail}", exc_info=True)
        error_message = '获取题目列表失败'
        if current_app.config.get('DEBUG', False):
            error_message = f'获取题目列表失败: {str(e)}\n{error_detail}'
        return jsonify({
            'status': 'error',
            'message': error_message
        }), 500


@coding_api_bp.route('/questions/<int:question_id>', methods=['GET'])
@login_required
def api_get_question(question_id: int):
    """获取题目详情"""
    try:
        user_id = session.get('user_id')
        question = QuestionService.get_question(question_id, user_id=user_id)

        if not question:
            return jsonify({
                'status': 'error',
                'message': '题目不存在'
            }), 404

        return jsonify({
            'status': 'success',
            'data': question
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取题目详情失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目详情失败'
        }), 500


# ==================== 代码执行API ====================

@coding_api_bp.route('/execute', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def api_execute():
    """运行代码（不判题）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400

        try:
            schema = ExecuteCodeSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400

        executor = PythonExecutor(
            time_limit=schema.time_limit or 5,
            output_limit=10000
        )
        result = executor.execute(
            code=schema.code,
            language=schema.language,
            input_data=schema.input
        )

        return jsonify({
            'status': 'success',
            'data': result
        }), 200

    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"代码执行失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '代码执行失败'
        }), 500


@coding_api_bp.route('/submit', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def api_submit():
    """提交代码（自动判题）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400

        try:
            schema = SubmitCodeSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401

        judge_service = JudgeService()
        judge_result = judge_service.judge(
            question_id=schema.question_id,
            code=schema.code,
            language=schema.language
        )

        submission = SubmissionService.create_submission(
            user_id=user_id,
            question_id=schema.question_id,
            code=schema.code,
            language=schema.language,
            judge_result=judge_result
        )

        from app.modules.coding.models.coding_question import CodingQuestion as CQ
        question = CQ.get_by_id(schema.question_id)

        passed_cases = judge_result.get('passed_cases', 0)
        total_cases = judge_result.get('total_cases', 1)
        score = (passed_cases / total_cases * 100.0) if total_cases > 0 else 0.0

        return jsonify({
            'status': 'success',
            'data': {
                'submission_id': submission['id'],
                'status': judge_result['status'],
                'passed_cases': passed_cases,
                'total_cases': total_cases,
                'execution_time': judge_result.get('execution_time', 0),
                'error_message': judge_result.get('error_message', ''),
                'score': score,
                'total_score': 100.0,
                'time_limit': question.get('time_limit', 5) * 1000 if question else 5000,
                'memory_limit': question.get('memory_limit', 128) * 1024 if question else 131072,
                'memory_used': 0,
                'test_results': judge_result.get('test_results', [])
            }
        }), 200

    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"提交代码失败: {e}", exc_info=True)
        error_message = '提交代码失败'
        if current_app.config.get('DEBUG', False):
            error_message = f'提交代码失败: {str(e)}'
        return jsonify({
            'status': 'error',
            'message': error_message
        }), 500



# ==================== 代码草稿API ====================

@coding_api_bp.route('/drafts/<int:question_id>', methods=['GET'])
@login_required
def api_get_draft(question_id: int):
    """获取代码草稿"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401

        draft = CodeDraft.query.filter_by(
            user_id=user_id, question_id=question_id
        ).first()

        if draft:
            return jsonify({
                'status': 'success',
                'data': {
                    'code': draft.code,
                    'language': draft.language or 'python'
                }
            }), 200
        else:
            return jsonify({
                'status': 'success',
                'data': {
                    'code': '',
                    'language': 'python'
                }
            }), 200
    except Exception as e:
        current_app.logger.error(f"获取代码草稿失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取代码草稿失败'
        }), 500


@coding_api_bp.route('/drafts/<int:question_id>', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def api_save_draft(question_id: int):
    """保存代码草稿"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400

        code = data.get('code', '')
        language = data.get('language', 'python')

        # PostgreSQL 兼容的 upsert 模式
        draft = CodeDraft.query.filter_by(
            user_id=user_id, question_id=question_id
        ).first()

        if draft:
            draft.code = code
            draft.language = language
            draft.updated_at = db.func.now()
        else:
            draft = CodeDraft(
                user_id=user_id,
                question_id=question_id,
                code=code,
                language=language,
            )
            db.session.add(draft)

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': '代码已保存'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"保存代码草稿失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '保存代码草稿失败'
        }), 500


@coding_api_bp.route('/drafts/<int:question_id>', methods=['DELETE'])
@login_required
def api_delete_draft(question_id: int):
    """删除代码草稿"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401

        CodeDraft.query.filter_by(
            user_id=user_id, question_id=question_id
        ).delete()
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': '草稿已删除'
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除代码草稿失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除代码草稿失败'
        }), 500


# ==================== 提交历史API ====================

@coding_api_bp.route('/submissions', methods=['GET'])
@login_required
def api_get_submissions():
    """获取提交历史"""
    try:
        user_id = session.get('user_id')
        question_id = request.args.get('question_id', type=int)
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        result = SubmissionService.get_submissions(
            user_id=user_id,
            question_id=question_id,
            status=status,
            page=page,
            per_page=per_page
        )

        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取提交历史失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取提交历史失败'
        }), 500


@coding_api_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@login_required
def api_get_submission(submission_id: int):
    """获取提交详情"""
    try:
        user_id = session.get('user_id')
        submission = SubmissionService.get_submission(submission_id, user_id=user_id)

        if not submission:
            return jsonify({
                'status': 'error',
                'message': '提交记录不存在'
            }), 404

        return jsonify({
            'status': 'success',
            'data': submission
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取提交详情失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取提交详情失败'
        }), 500


# ==================== 统计API ====================

@coding_api_bp.route('/statistics', methods=['GET'])
@login_required
def api_get_statistics():
    """获取用户统计"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401

        stats = SubmissionService.get_user_statistics(user_id)

        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取统计信息失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取统计信息失败'
        }), 500


@coding_api_bp.route('/questions/<int:question_id>/rankings', methods=['GET'])
@login_required
def api_get_question_rankings(question_id: int):
    """获取题目排名（按得分排序）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        offset = (page - 1) * per_page

        accepted_score_col = func.max(case(
            (CodeSubmission.status == 'accepted', CodeSubmission.score),
            else_=0,
        )).label('accepted_score')
        best_score_col = func.max(CodeSubmission.score).label('best_score')
        best_time_col = func.min(case(
            (CodeSubmission.status == 'accepted', CodeSubmission.execution_time),
        )).label('best_time')
        first_accepted_col = func.min(case(
            (CodeSubmission.status == 'accepted', CodeSubmission.submitted_at),
        )).label('first_accepted_at')

        rankings_q = (
            db.session.query(
                CodeSubmission.user_id,
                User.username,
                best_score_col,
                accepted_score_col,
                best_time_col,
                first_accepted_col,
                func.count().label('total_submissions'),
                func.max(CodeSubmission.submitted_at).label('last_submitted_at'),
            )
            .join(User, CodeSubmission.user_id == User.id)
            .filter(CodeSubmission.question_id == question_id)
            .group_by(CodeSubmission.user_id, User.username)
            .order_by(
                accepted_score_col.desc(),
                best_score_col.desc(),
                best_time_col.asc(),
                first_accepted_col.asc(),
            )
            .limit(per_page)
            .offset(offset)
            .all()
        )

        # 获取总数
        total = (
            db.session.query(func.count(distinct(CodeSubmission.user_id)))
            .filter(CodeSubmission.question_id == question_id)
            .scalar()
        ) or 0

        # 获取当前用户的排名
        current_user_id = session.get('user_id')
        user_rank = None
        if current_user_id:
            user_best = (
                db.session.query(
                    func.max(CodeSubmission.score).label('best_score'),
                    func.max(case(
                        (CodeSubmission.status == 'accepted', CodeSubmission.score),
                        else_=0,
                    )).label('accepted_score'),
                    func.min(case(
                        (CodeSubmission.status == 'accepted', CodeSubmission.execution_time),
                    )).label('best_time'),
                )
                .filter(
                    CodeSubmission.question_id == question_id,
                    CodeSubmission.user_id == current_user_id,
                )
                .first()
            )

            if user_best and user_best.accepted_score:
                user_acc = user_best.accepted_score
                user_time = user_best.best_time or 999999

                sub_q = (
                    db.session.query(CodeSubmission.user_id)
                    .filter(CodeSubmission.question_id == question_id)
                    .group_by(CodeSubmission.user_id)
                    .having(
                        db.or_(
                            func.max(case(
                                (CodeSubmission.status == 'accepted', CodeSubmission.score),
                                else_=0,
                            )) > user_acc,
                            db.and_(
                                func.max(case(
                                    (CodeSubmission.status == 'accepted', CodeSubmission.score),
                                    else_=0,
                                )) == user_acc,
                                func.min(case(
                                    (CodeSubmission.status == 'accepted', CodeSubmission.execution_time),
                                )) < user_time,
                            ),
                        )
                    )
                    .subquery()
                )
                rank_count = db.session.query(func.count()).select_from(sub_q).scalar() or 0
                user_rank = rank_count + 1

        result = []
        for idx, row in enumerate(rankings_q, start=offset + 1):
            result.append({
                'rank': idx,
                'user_id': row.user_id,
                'username': row.username,
                'best_score': round(row.best_score, 2) if row.best_score else 0,
                'accepted_score': round(row.accepted_score, 2) if row.accepted_score else 0,
                'best_time': round(row.best_time, 3) if row.best_time else None,
                'first_accepted_at': str(row.first_accepted_at) if row.first_accepted_at else None,
                'total_submissions': row.total_submissions,
                'last_submitted_at': str(row.last_submitted_at) if row.last_submitted_at else None,
            })

        return jsonify({
            'status': 'success',
            'data': {
                'rankings': result,
                'total': total,
                'page': page,
                'per_page': per_page,
                'user_rank': user_rank
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取题目排名失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目排名失败'
        }), 500
