# -*- coding: utf-8 -*-
"""管理后台API路由（向后兼容的旧路径）"""
from flask import Blueprint, request, jsonify, current_app
from app.core.extensions import db
from sqlalchemy import text
from app.core.utils.cache_utils import bump_questions_version, bump_subjects_version
from app.core.utils.json_helpers import safe_load as _safe_load
from app.core.utils.image_helpers import normalize_image_paths as _normalize_image_paths
from app.core.utils.csv_helpers import csv_escape
import json

# 创建一个额外的蓝图用于向后兼容
admin_api_legacy_bp = Blueprint('admin_api_legacy', __name__)


@admin_api_legacy_bp.before_request
def _log_legacy_usage():
    """记录所有仍在被调用的 legacy 端点，便于追踪迁移进度。"""
    current_app.logger.warning(
        'Legacy API 调用: %s %s (来源: %s)',
        request.method,
        request.path,
        request.referrer or 'unknown',
    )


@admin_api_legacy_bp.route('/types', methods=['GET'])
def get_question_types():
    """获取题型列表（向后兼容路径：/admin/types）"""
    try:
        from app.core.utils.portable_question_format import portable_type_to_q_type

        rows = db.session.execute(text('SELECT DISTINCT type FROM questions')).fetchall()
        types = [
            portable_type_to_q_type((r._mapping['type'] or ''))
            for r in rows
            if r and r._mapping['type']
        ]
        types = sorted(list({t for t in types if t}))
    except Exception:
        types = []
    return jsonify(types)


@admin_api_legacy_bp.route('/questions', methods=['GET'])
def get_filtered_questions():
    """获取筛选后的题目列表（向后兼容路径：/admin/questions）"""
    subject_id = request.args.get('subject_id')
    q_type = request.args.get('type', 'all')
    
    conn_params = {}
    from app.core.utils.portable_question_format import portable_type_to_q_type, q_type_to_portable_type

    sql = '''
        SELECT q.id, q.subject_id, q.type, q.content, q.difficulty, q.tags, q.image_path, u.username as created_by, q.updated_at
        FROM questions q
        LEFT JOIN users u ON q.created_by = u.id
        WHERE 1=1
    '''

    if subject_id:
        sql += ' AND q.subject_id = :subject_id'
        conn_params['subject_id'] = subject_id

    if q_type != 'all':
        sql += ' AND q.type = :q_type'
        conn_params['q_type'] = q_type_to_portable_type(q_type)

    sql += ' ORDER BY q.id DESC'

    rows = db.session.execute(text(sql), conn_params).fetchall()
    questions = []
    for row in rows:
        question_dict = dict(row._mapping)
        question_dict['q_type'] = portable_type_to_q_type(question_dict.get('type') or '')

        # tags：优先解析 JSON 数组字符串；否则保留原值
        tags_raw = question_dict.get('tags')
        if isinstance(tags_raw, str) and tags_raw.strip().startswith('['):
            try:
                parsed = json.loads(tags_raw)
                if isinstance(parsed, list):
                    question_dict['tags'] = parsed
            except Exception:
                pass

        image_path = question_dict.get('image_path')
        # Compatibility: if it's a non-empty string and not a JSON array, wrap it
        if image_path and isinstance(image_path, str) and not image_path.strip().startswith('['):
            question_dict['image_path'] = json.dumps([image_path])
        # If it's an empty string or None, make it an empty JSON array
        elif not image_path:
             question_dict['image_path'] = '[]'
        questions.append(question_dict)
    
    return jsonify(questions)


@admin_api_legacy_bp.route('/questions', methods=['POST'])
def add_question_legacy():
    """添加题目（向后兼容路径：/admin/questions）"""
    from flask import request, session
    from app.core.utils.options_parser import parse_options
    from app.core.utils.portable_question_format import internal_question_to_portable
    
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400
    
    try:
        q_type = data.get('q_type')
        answer = (data.get('answer') or '').strip()
        options_str = data.get('options', '[]')
        
        # 多选题验证：确保答案至少有两个选项
        if q_type == '多选题':
            if len(answer) < 2:
                return jsonify({'status':'error','message':'多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
            # 验证答案中的所有字母是否在选项范围内
            try:
                options_list = json.loads(options_str) if isinstance(options_str, str) else options_str
                if isinstance(options_list, list) and len(options_list) > 0:
                    parsed_options = parse_options(options_list)
                    valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                    answer_keys = set(answer.upper())
                    invalid_keys = answer_keys - valid_keys
                    if invalid_keys:
                        return jsonify({'status':'error','message':f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'}), 400
            except Exception:
                pass  # 如果解析选项失败，跳过验证
        
        db.session.execute(
            text('''
            INSERT INTO questions (
                subject_id, type, content, options, answer, analysis, tags, difficulty,
                image_path, created_by, updated_by, created_at, updated_at
            ) VALUES (:subject_id, :type, :content, :options, :answer, :analysis, :tags, :difficulty,
                :image_path, :created_by, :updated_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            '''),
            {
                'subject_id': data.get('subject_id'),
                'type': portable.get('type') or 'essay',
                'content': portable.get('content') or '',
                'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                'answer': json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                'analysis': portable.get('analysis') or '',
                'tags': json.dumps(portable.get('tags') or [], ensure_ascii=False),
                'difficulty': int(portable.get('difficulty') or 1),
                'image_path': data.get('image_path'),
                'created_by': session.get('user_id'),
                'updated_by': session.get('user_id'),
            },
        )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        
        return jsonify({'status':'success','message':'题目添加成功'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/questions/<int:question_id>', methods=['GET'])
def get_single_question(question_id):
    """获取单个题目（向后兼容路径：/admin/questions/<id>）"""
    row = db.session.execute(text('SELECT * FROM questions WHERE id=:qid'), {'qid': question_id}).fetchone()
    
    if row:
        from app.core.utils.pqf_rows import pqf_row_to_internal

        question_dict = pqf_row_to_internal(row, scope="question_center")
        image_path = question_dict.get('image_path')
        # Compatibility: if it's a non-empty string and not a JSON array, wrap it
        if image_path and isinstance(image_path, str) and not image_path.strip().startswith('['):
            question_dict['image_path'] = json.dumps([image_path])
        # If it's an empty string or None, make it an empty JSON array
        elif not image_path:
             question_dict['image_path'] = '[]'
        return jsonify(question_dict)
    return jsonify({'error': 'not found'}), 404


@admin_api_legacy_bp.route('/questions/<int:question_id>', methods=['PUT'])
def edit_question_legacy(question_id):
    """编辑题目（向后兼容路径：/admin/questions/<id>）"""
    from flask import request, session
    from app.core.utils.options_parser import parse_options
    from app.core.utils.portable_question_format import internal_question_to_portable
    
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400
    
    try:
        q_type = data.get('q_type')
        answer = (data.get('answer') or '').strip()
        options_str = data.get('options', '[]')
        
        # 多选题验证：确保答案至少有两个选项
        if q_type == '多选题':
            if len(answer) < 2:
                return jsonify({'status':'error','message':'多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
            # 验证答案中的所有字母是否在选项范围内
            try:
                options_list = json.loads(options_str) if isinstance(options_str, str) else options_str
                if isinstance(options_list, list) and len(options_list) > 0:
                    parsed_options = parse_options(options_list)
                    valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                    answer_keys = set(answer.upper())
                    invalid_keys = answer_keys - valid_keys
                    if invalid_keys:
                        return jsonify({'status':'error','message':f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'}), 400
            except Exception:
                pass  # 如果解析选项失败，跳过验证

        portable = internal_question_to_portable(
            q_id=int(question_id),
            q_type=q_type,
            content=data.get('content'),
            options=options_str,
            answer=answer,
            explanation=data.get('explanation', ''),
            difficulty=data.get('difficulty', 1),
            tags=data.get('tags'),
        )

        db.session.execute(
            text('''
            UPDATE questions SET
                subject_id=:subject_id,
                type=:type,
                content=:content,
                options=:options,
                answer=:answer,
                analysis=:analysis,
                tags=:tags,
                difficulty=:difficulty,
                image_path=:image_path,
                updated_by=:updated_by,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=:qid
            '''),
            {
                'subject_id': data.get('subject_id'),
                'type': portable.get('type') or 'essay',
                'content': portable.get('content') or '',
                'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                'answer': json.dumps(portable.get('answer') if portable.get('answer') is not None else [], ensure_ascii=False),
                'analysis': portable.get('analysis') or '',
                'tags': json.dumps(portable.get('tags') or [], ensure_ascii=False),
                'difficulty': int(portable.get('difficulty') or 1),
                'image_path': data.get('image_path'),
                'updated_by': session.get('user_id'),
                'qid': int(question_id),
            },
        )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        
        return jsonify({'status':'success','message':'题目修改成功'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/questions/<int:question_id>', methods=['DELETE'])
def delete_question_legacy(question_id):
    """删除题目（向后兼容路径：/admin/questions/<id>）"""
    try:
        db.session.execute(text('DELETE FROM questions WHERE id = :qid'), {'qid': question_id})
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': '题目删除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/questions/import', methods=['POST'])
def import_questions_api():
    """导入题目（向后兼容路径：/admin/questions/import）"""
    from flask import request, session

    from app.core.utils.fill_blank_parser import parse_fill_blank
    from app.core.utils.options_parser import parse_options
    from app.core.utils.portable_question_format import (
        internal_question_to_portable,
        portable_question_to_internal,
    )

    data = request.json or {}
    subject_id = data.get('subject_id')
    questions = data.get('questions', [])

    if not subject_id or not isinstance(questions, list) or not questions:
        return jsonify({'status': 'error', 'message': '缺少科目或题库数据'}), 400

    count = 0

    try:
        for item in questions:
            if not isinstance(item, dict):
                continue

            try:
                # 统一格式优先：{type, content, options, answer, analysis, tags, difficulty}
                if 'type' in item or (isinstance(item.get('answer'), list) and 'content' in item):
                    internal, conv_errors = portable_question_to_internal(item, scope='question_center')
                    if conv_errors:
                        continue

                    q_type = (internal.get('q_type') or '未知').strip()
                    content = internal.get('content') or ''
                    answer = internal.get('answer') or ''
                    explanation = internal.get('explanation') or ''
                    options_list = internal.get('options') or []
                    diff_val = internal.get('difficulty') or 1
                    tags_val = internal.get('tags') or []
                    opts_json = json.dumps(options_list or [], ensure_ascii=False)
                else:
                    # 兼容旧格式（题型/题干/选项/答案/解析/难度/标签）
                    q_type = str(item.get('题型') or item.get('q_type') or '未知').strip()
                    content = item.get('题干') or item.get('content') or ''
                    answer = item.get('答案') or item.get('answer') or ''
                    explanation = item.get('解析') or item.get('explanation') or ''
                    diff_val = item.get('难度') or item.get('difficulty') or 1
                    tags_val = item.get('标签') or item.get('tags') or []

                    options_list = item.get('选项') or item.get('options') or []
                    if isinstance(options_list, str):
                        try:
                            options_list = json.loads(options_list)
                        except Exception:
                            options_list = []
                    if isinstance(options_list, list):
                        options_list = [str(o) for o in options_list]
                    else:
                        options_list = []
                    opts_json = json.dumps(options_list or [], ensure_ascii=False)

                    if q_type == '填空题':
                        # 支持题干中用 {答案} 标记空位，并自动提取答案
                        new_content, new_answer, _blank_count = parse_fill_blank(content)
                        if new_answer:
                            content = new_content
                            answer = new_answer

                if q_type in ('选择题', '多选题'):
                    if q_type == '多选题':
                        ans = str(answer or '').strip()
                        if len(ans) < 2:
                            continue

                    # 验证答案字母是否在选项范围内（尽量不阻断整体导入）
                    try:
                        parsed = parse_options(options_list or [])
                        valid_keys = {opt['key'] for opt in parsed if opt.get('key')}
                        answer_keys = set(str(answer or '').strip().upper())
                        if valid_keys and (answer_keys - valid_keys):
                            continue
                    except Exception:
                        pass

                portable = internal_question_to_portable(
                    q_id=None,
                    q_type=q_type,
                    content=content,
                    options=opts_json,
                    answer=answer,
                    explanation=explanation,
                    difficulty=diff_val,
                    tags=tags_val,
                )

                conn_execute_sql = """
                    INSERT INTO questions (
                        subject_id, type, content, options, answer, analysis, tags, difficulty,
                        created_by, updated_by, created_at, updated_at
                    ) VALUES (:subject_id, :type, :content, :options, :answer, :analysis, :tags, :difficulty,
                        :created_by, :updated_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                db.session.execute(
                    text(conn_execute_sql),
                    {
                        'subject_id': subject_id,
                        'type': portable.get('type') or 'essay',
                        'content': portable.get('content') or '',
                        'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                        'answer': json.dumps(
                            portable.get('answer') if portable.get('answer') is not None else [],
                            ensure_ascii=False,
                        ),
                        'analysis': portable.get('analysis') or '',
                        'tags': json.dumps(portable.get('tags') or [], ensure_ascii=False),
                        'difficulty': int(portable.get('difficulty') or 1),
                        'created_by': session.get('user_id'),
                        'updated_by': session.get('user_id'),
                    },
                )
                count += 1
            except Exception:
                continue

        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功导入{count}道题'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/questions/batch_delete', methods=['POST'])
def batch_delete_questions():
    """批量删除题目（向后兼容路径：/admin/questions/batch_delete）"""
    data = request.json
    ids = data.get('ids', [])

    if not ids:
        return jsonify({'status': 'error', 'message': '未提供要删除的题目 ID'}), 400

    try:
        for qid in ids:
            db.session.execute(text('DELETE FROM questions WHERE id = :qid'), {'qid': qid})
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': '批量删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'批量删除失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/questions/batch_change_type', methods=['POST'])
def batch_change_type():
    """批量修改题型（向后兼容路径：/admin/questions/batch_change_type）"""
    data = request.json
    ids = data.get('ids', [])
    target_type = data.get('target_type', '')
    
    if not ids or not target_type:
        return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
    
    try:
        from app.core.utils.portable_question_format import q_type_to_portable_type

        portable_type = q_type_to_portable_type(target_type)
        for qid in ids:
            db.session.execute(
                text('UPDATE questions SET type = :ptype WHERE id = :qid'),
                {'ptype': portable_type, 'qid': qid},
            )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功修改 {len(ids)} 道题目的题型'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'批量修改失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/questions/batch_move_subject', methods=['POST'])
def batch_move_subject():
    """批量移动科目（向后兼容路径：/admin/questions/batch_move_subject）"""
    data = request.json
    ids = data.get('ids', [])
    target_subject_id = data.get('target_subject_id')
    
    if not ids or not target_subject_id:
        return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
    
    try:
        for qid in ids:
            db.session.execute(
                text('UPDATE questions SET subject_id = :sid WHERE id = :qid'),
                {'sid': target_subject_id, 'qid': qid},
            )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功移动 {len(ids)} 道题目'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'批量移动失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/questions/batch_set_difficulty', methods=['POST'])
def batch_set_difficulty():
    """批量设置难度（向后兼容路径：/admin/questions/batch_set_difficulty）"""
    data = request.json
    ids = data.get('ids', [])
    difficulty = data.get('difficulty', '')
    
    if not ids or not difficulty:
        return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
    
    try:
        try:
            diff_val = int(difficulty or 1)
        except Exception:
            diff_val = 1
        diff_val = max(1, min(5, diff_val))
        for qid in ids:
            db.session.execute(
                text('UPDATE questions SET difficulty = :diff WHERE id = :qid'),
                {'diff': diff_val, 'qid': qid},
            )
        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': f'成功设置 {len(ids)} 道题目的难度'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'批量设置失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
def toggle_admin(user_id):
    """切换管理员权限（向后兼容路径：/admin/users/<id>/toggle_admin）"""
    from app.core.utils.user_state_cache import invalidate_user_state
    from flask import session, request, current_app
    
    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '管理员不能对自己进行操作'}), 400
    
    try:
        row = db.session.execute(text('SELECT is_admin, username FROM users WHERE id=:uid'), {'uid': user_id}).fetchone()

        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        target_is_admin = bool(row._mapping['is_admin'])

        if target_is_admin:
            admin_count = db.session.execute(text('SELECT COUNT(1) FROM users WHERE is_admin = true')).fetchone()[0]
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能取消最后一个管理员的权限'}), 400

        db.session.execute(text('UPDATE users SET is_admin = NOT is_admin WHERE id = :uid'), {'uid': user_id})
        db.session.execute(text('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'), {'uid': user_id})
        db.session.commit()
        invalidate_user_state(int(user_id))

        current_app.logger.info(f'管理员权限切换 - 目标用户: {row._mapping["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/toggle_subject_admin', methods=['POST'])
def toggle_subject_admin(user_id):
    """切换科目管理员权限（向后兼容路径：/admin/users/<id>/toggle_subject_admin）"""
    from app.core.utils.user_state_cache import invalidate_user_state
    from flask import session, request, current_app
    
    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400
    
    try:
        row = db.session.execute(text('SELECT is_subject_admin, username FROM users WHERE id=:uid'), {'uid': user_id}).fetchone()

        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        db.session.execute(text('UPDATE users SET is_subject_admin = NOT is_subject_admin WHERE id = :uid'), {'uid': user_id})
        db.session.execute(text('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'), {'uid': user_id})
        db.session.commit()
        invalidate_user_state(int(user_id))

        current_app.logger.info(f'科目管理员权限切换 - 目标用户: {row._mapping["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '科目管理员权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换科目管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/toggle_notification_admin', methods=['POST'])
def toggle_notification_admin(user_id):
    """切换通知管理员权限（向后兼容路径：/admin/users/<id>/toggle_notification_admin）"""
    from app.core.utils.user_state_cache import invalidate_user_state
    from flask import session, request, current_app

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400

    try:
        # is_notification_admin 字段在 PostgreSQL 中已存在，直接查询
        row = db.session.execute(
            text('SELECT is_notification_admin, username FROM users WHERE id=:uid'),
            {'uid': user_id},
        ).fetchone()

        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        db.session.execute(
            text('UPDATE users SET is_notification_admin = NOT is_notification_admin WHERE id = :uid'),
            {'uid': user_id},
        )
        db.session.execute(
            text('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'),
            {'uid': user_id},
        )
        db.session.commit()
        invalidate_user_state(int(user_id))

        current_app.logger.info(f'通知管理员权限切换 - 目标用户: {row._mapping["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '通知管理员权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error('切换通知管理员权限失败 - 用户ID: %s', user_id, exc_info=True)
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/toggle_lock', methods=['POST'])
def toggle_lock(user_id):
    """切换用户锁定状态（向后兼容路径：/admin/users/<id>/toggle_lock）"""
    from app.core.utils.user_state_cache import invalidate_user_state
    from flask import session
    
    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400

    try:
        conn_result = db.session.execute(
            text('UPDATE users SET is_locked = CASE WHEN COALESCE(is_locked,false)=true THEN false ELSE true END, session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id=:uid'),
            {'uid': user_id}
        )
        if conn_result.rowcount == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        db.session.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status':'success','message':'锁定状态已切换，并已强制下线'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
def reset_password(user_id):
    """重置用户密码（向后兼容路径：/admin/users/<id>/reset_password）"""
    from app.core.utils.user_state_cache import invalidate_user_state
    from flask import session, request
    from werkzeug.security import generate_password_hash
    from app.core.utils.validators import validate_password
    
    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400
    
    payload = request.json or {}
    new = payload.get('new_password') or payload.get('password') or ''
    
    valid, msg = validate_password(new)
    if not valid:
        return jsonify({'status':'error','message':msg}), 400
    
    ph = generate_password_hash(new)
    
    try:
        db.session.execute(
            text('UPDATE users SET password_hash=:ph, has_password_set=true, session_version = COALESCE(session_version,0) + 1 WHERE id=:uid'),
            {'ph': ph, 'uid': user_id}
        )
        # Check rowcount before commit
        db.session.commit()
        invalidate_user_state(int(user_id))

        return jsonify({'status':'success','message':'重置密码成功（已强制下线）'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/users/export')
def export_users():
    """导出用户CSV（向后兼容路径：/admin/users/export）"""
    rows = db.session.execute(
        text('SELECT id, username, is_admin, is_locked, created_at FROM users ORDER BY id')
    ).fetchall()
    
    out = '\ufeff' + 'id,username,is_admin,is_locked,created_at\n'
    for r in rows:
        rm = r._mapping
        out += ','.join([
            str(rm['id']),
            csv_escape(rm['username']),
            '1' if rm['is_admin'] else '0',
            '1' if (rm['is_locked'] or 0) else '0',
            csv_escape(rm['created_at'])
        ]) + '\n'
    
    from flask import Response
    return Response(
        out,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=users.csv'}
    )


@admin_api_legacy_bp.route('/users/create', methods=['POST'])
def create_user():
    """创建用户（向后兼容路径：/admin/users/create）"""
    from flask import request
    from werkzeug.security import generate_password_hash
    from app.core.utils.validators import validate_password
    from sqlalchemy.exc import IntegrityError
    
    payload = request.json or {}
    username = (payload.get('username') or '').strip()
    password = payload.get('password') or ''
    is_admin = 1 if payload.get('is_admin') in (1, True, '1', 'true') else 0
    
    if not username or not password:
        return jsonify({'status':'error','message':'用户名和密码不能为空'}), 400
    
    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'status':'error','message':msg}), 400
    
    ph = generate_password_hash(password)
    
    try:
        db.session.execute(
            text('INSERT INTO users (username, password_hash, is_admin, is_locked, session_version) VALUES (:username, :ph, :is_admin, false, 0)'),
            {'username': username, 'ph': ph, 'is_admin': is_admin}
        )
        db.session.commit()
        return jsonify({'status':'success','message':'用户创建成功'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'status':'error','message':'用户名已存在'}), 409
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户（向后兼容路径：/admin/users/<id>）"""
    from flask import session
    from sqlalchemy.exc import IntegrityError

    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能删除自己'}), 400

    try:
        u = db.session.execute(text('SELECT id, is_admin, username FROM users WHERE id=:uid'), {'uid': user_id}).fetchone()

        if not u:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        if u._mapping['is_admin']:
            admin_count = db.session.execute(text('SELECT COUNT(1) FROM users WHERE is_admin = true')).fetchone()[0]
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能删除最后一个管理员'}), 400

        # 级联清理所有关联数据（按依赖顺序删除，避免外键约束错误）
        _p = {'uid': user_id}

        # 1. 删除考试相关数据
        db.session.execute(text('DELETE FROM exam_questions WHERE exam_id IN (SELECT id FROM exams WHERE user_id=:uid)'), _p)
        db.session.execute(text('DELETE FROM exams WHERE user_id=:uid'), _p)

        # 2. 删除用户基础数据
        db.session.execute(text('DELETE FROM favorites WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM mistakes WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM user_answers WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM user_progress WHERE user_id=:uid'), _p)

        # 3. 删除聊天相关数据
        db.session.execute(text('DELETE FROM chat_messages WHERE sender_id=:uid'), _p)
        db.session.execute(text('DELETE FROM chat_members WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM user_remarks WHERE owner_user_id=:uid OR target_user_id=:uid'), _p)

        # 4. 删除通知相关数据
        db.session.execute(text('DELETE FROM notification_dismissals WHERE user_id=:uid'), _p)

        # 5. 删除编程相关数据
        db.session.execute(text('DELETE FROM code_submissions WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM coding_statistics WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM user_coding_stats WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM code_drafts WHERE user_id=:uid'), _p)

        # 6. 删除其他用户数据
        db.session.execute(text('DELETE FROM user_subjects WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM user_quiz_stats WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM email_verification_codes WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM popup_dismissals WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM edu_schedule_credentials WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM edu_schedule_snapshots WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM edu_grade_snapshots WHERE user_id=:uid'), _p)
        db.session.execute(text('DELETE FROM edu_grade_overview_snapshots WHERE user_id=:uid'), _p)

        # 7. 更新引用该用户的字段（SET NULL 处理）
        db.session.execute(text('UPDATE questions SET created_by=NULL WHERE created_by=:uid'), _p)
        db.session.execute(text('UPDATE notifications SET created_by=NULL WHERE created_by=:uid'), _p)
        db.session.execute(text('UPDATE popups SET created_by=NULL WHERE created_by=:uid'), _p)
        db.session.execute(text('UPDATE popup_views SET user_id=NULL WHERE user_id=:uid'), _p)
        db.session.execute(text('UPDATE system_config SET updated_by=NULL WHERE updated_by=:uid'), _p)
        db.session.execute(text('UPDATE user_subjects SET restricted_by=NULL WHERE restricted_by=:uid'), _p)

        # 8. 最后删除用户本身
        db.session.execute(text('DELETE FROM users WHERE id=:uid'), _p)
        db.session.commit()

        return jsonify({'status': 'success', 'message': '用户已删除'})

    except IntegrityError as e:
        db.session.rollback()
        msg = str(e)
        if 'foreign key' in msg.lower():
            return jsonify({
                'status': 'error',
                'message': '删除失败：该用户仍有关联数据（外键约束），请先删除/转移其相关记录后再删除。'
            }), 400
        return jsonify({'status': 'error', 'message': msg}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/download_template')
def download_template():
    """下载Excel模板文件（向后兼容路径：/admin/download_template）"""
    from flask import send_from_directory, current_app
    import os
    
    # 模板文件目录：项目根目录的instance文件夹
    # current_app.root_path 是 app/ 目录，需要向上两级到项目根目录
    directory = os.path.join(current_app.root_path, '..', 'instance')
    directory = os.path.abspath(directory)
    
    return send_from_directory(directory, 'question_import_template.xlsx', as_attachment=True)


@admin_api_legacy_bp.route('/questions/export', methods=['GET'])
def export_questions_api():
    """导出题目（向后兼容路径：/admin/questions/export）"""
    subject_id = request.args.get('subject_id')

    conn_params = {}
    sql = '''
        SELECT q.id, q.subject_id, s.name as subject_name,
               q.type, q.content, q.options, q.answer, q.analysis, q.difficulty, q.tags
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE 1=1
    '''

    if subject_id:
        sql += ' AND q.subject_id = :subject_id'
        conn_params['subject_id'] = subject_id

    sql += ' ORDER BY q.id'
    rows = db.session.execute(text(sql), conn_params).fetchall()

    items = []
    for r in rows:
        rm = r._mapping
        item = {
            'id': int(rm['id']),
            'type': (rm['type'] or ''),
            'content': (rm['content'] or ''),
            'options': _safe_load(rm['options'], []),
            'answer': _safe_load(rm['answer'], []),
            'analysis': (rm['analysis'] or ''),
            'tags': _safe_load(rm['tags'], []),
            'difficulty': int(rm['difficulty'] or 1),
        }
        # 题库中心导出：附带科目信息（便于全量导出备份）
        item['subject_id'] = rm['subject_id']
        item['subject_name'] = rm['subject_name'] or '默认科目'
        items.append(item)

    meta = {'scope': 'question_center'}
    if subject_id:
        meta['subject_id'] = subject_id
    return jsonify({'meta': meta, 'count': len(items), 'questions': items})


@admin_api_legacy_bp.route('/questions/export_package', methods=['GET'])
def export_questions_package():
    """导出题目包（向后兼容路径：/admin/questions/export_package）"""
    from flask import request, send_file, current_app
    import zipfile
    import io
    import datetime
    import os

    subject_id = request.args.get('subject_id')
    q_type = request.args.get('type')
    
    conn_params = {}
    from app.core.utils.portable_question_format import q_type_to_portable_type

    # 1. 获取科目名称
    subject_name = "all_subjects"
    if subject_id:
        subject_row = db.session.execute(text('SELECT name FROM subjects WHERE id = :sid'), {'sid': subject_id}).fetchone()
        if subject_row:
            subject_name = subject_row._mapping['name']

    # 2. 查询题目数据
    sql = '''
        SELECT q.id, q.subject_id, s.name as subject_name,
               q.type, q.content, q.options, q.answer, q.analysis,
               q.difficulty, q.tags, q.image_path
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE 1=1
    '''
    if subject_id:
        sql += ' AND q.subject_id = :subject_id'
        conn_params['subject_id'] = subject_id
    if q_type and q_type != 'all':
        sql += ' AND q.type = :q_type'
        conn_params['q_type'] = q_type_to_portable_type(q_type)

    sql += ' ORDER BY q.id'
    rows = db.session.execute(text(sql), conn_params).fetchall()

    # 3. 创建 ZIP 文件（统一 Portable Question Format）
    memory_file = io.BytesIO()
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))
    questions_data = []

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            rm = r._mapping
            item = {
                'id': int(rm['id']),
                'type': (rm['type'] or ''),
                'content': (rm['content'] or ''),
                'options': _safe_load(rm['options'], []),
                'answer': _safe_load(rm['answer'], []),
                'analysis': (rm['analysis'] or ''),
                'tags': _safe_load(rm['tags'], []),
                'difficulty': int(rm['difficulty'] or 1),
            }
            item['subject_id'] = rm['subject_id']
            item['subject_name'] = rm['subject_name'] or '默认科目'

            images_in_zip = []
            for img_rel in _normalize_image_paths(rm['image_path']):
                img_rel = str(img_rel).replace('\\', '/').lstrip('/')
                full_image_path = os.path.join(upload_folder, *img_rel.split('/'))
                if not os.path.exists(full_image_path):
                    continue
                arcname = f"images/{img_rel}"
                try:
                    zf.write(full_image_path, arcname)
                    images_in_zip.append(arcname)
                except Exception:
                    continue
            item['images'] = images_in_zip
            questions_data.append(item)

        payload = {
            'meta': {
                'scope': 'question_center_package',
                'subject_id': int(subject_id) if str(subject_id or '').isdigit() else None,
                'subject_name': subject_name,
                'exported_at': datetime.datetime.now().isoformat(),
            },
            'questions': questions_data,
        }
        zf.writestr('data.json', json.dumps(payload, ensure_ascii=False, indent=2))

    memory_file.seek(0)
    
    # 4. 生成文件名并发送文件
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"questions_export_{subject_name}_{timestamp}.zip"
    
    return send_file(
        memory_file,
        as_attachment=True,
        download_name=filename,
        mimetype='application/zip'
    )


@admin_api_legacy_bp.route('/questions/import_package', methods=['POST'])
def import_questions_package():
    """导入题目包（向后兼容路径：/admin/questions/import_package）"""
    from flask import current_app, session
    import zipfile
    import datetime
    import os
    import uuid

    from app.core.utils.portable_question_format import (
        internal_question_to_portable,
        portable_question_to_internal,
    )
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有文件部分'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({'status': 'error', 'message': '请上传有效的 .zip 文件'}), 400

    # 获取现有的科目 name -> id 映射
    subjects = db.session.execute(text('SELECT id, name FROM subjects')).fetchall()
    subject_map = {s._mapping['name']: s._mapping['id'] for s in subjects}

    imported_count = 0
    errors = []
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))

    try:

        with zipfile.ZipFile(file, 'r') as zf:
            if 'data.json' not in zf.namelist():
                return jsonify({'status': 'error', 'message': '压缩包中缺少 data.json 文件'}), 400
            
            with zf.open('data.json') as f:
                raw_payload = json.load(f)

            meta = raw_payload.get('meta', {}) if isinstance(raw_payload, dict) else {}
            if isinstance(raw_payload, dict):
                questions_data = raw_payload.get('questions') or []
            elif isinstance(raw_payload, list):
                questions_data = raw_payload
            else:
                return jsonify({'status': 'error', 'message': 'data.json 格式不支持'}), 400

            default_subject_name = meta.get('subject_name') if isinstance(meta, dict) else None
            
            for q in questions_data:
                try:
                    if not isinstance(q, dict):
                        continue

                    # 1. 处理科目
                    subject_name = q.get('subject_name') or default_subject_name
                    if not subject_name:
                        errors.append(f"题目ID {q.get('id')} 缺少科目名称，已跳过。")
                        continue

                    if subject_name not in subject_map:
                        result = db.session.execute(
                            text('INSERT INTO subjects (name) VALUES (:name) RETURNING id'),
                            {'name': subject_name},
                        )
                        subject_id = result.fetchone()[0]
                        subject_map[subject_name] = subject_id
                    else:
                        subject_id = subject_map[subject_name]

                    # 2. 解析题目（统一格式优先）
                    if 'type' in q or (isinstance(q.get('answer'), list) and 'content' in q):
                        internal, conv_errors = portable_question_to_internal(q, scope='question_center')
                        if conv_errors:
                            errors.append(f"题目ID {q.get('id', 'N/A')} 导入失败: {'；'.join(conv_errors)}")
                            continue
                        portable = internal_question_to_portable(
                            q_id=None,
                            q_type=internal.get('q_type') or '未知',
                            content=internal.get('content') or '',
                            options=internal.get('options') or [],
                            answer=internal.get('answer') or '',
                            explanation=internal.get('explanation') or '',
                            difficulty=internal.get('difficulty') or 1,
                            tags=internal.get('tags') or [],
                        )
                        images = q.get('images') or []
                    else:
                        # 兼容旧包格式（原始字段）
                        q_type = q.get('q_type') or q.get('题型') or '未知'
                        content = q.get('content') or q.get('题干') or ''
                        answer = q.get('answer') or q.get('答案') or ''
                        explanation = q.get('explanation') or q.get('解析') or ''
                        diff_val = q.get('difficulty') or q.get('难度') or 1
                        tags_val = q.get('tags') or q.get('标签') or []
                        options_val = q.get('options') or q.get('选项') or '[]'
                        if isinstance(options_val, list):
                            options_json = json.dumps(options_val, ensure_ascii=False)
                        else:
                            options_json = str(options_val or '[]')

                        portable = internal_question_to_portable(
                            q_id=None,
                            q_type=q_type,
                            content=content,
                            options=options_json,
                            answer=answer,
                            explanation=explanation,
                            difficulty=diff_val,
                            tags=tags_val,
                        )

                        images = q.get('images') or []
                        if not images:
                            for img_rel in _normalize_image_paths(q.get('image_path')):
                                img_rel = str(img_rel).replace('\\', '/').lstrip('/')
                                images.append('images/' + img_rel)

                    # 3. 处理图片（统一为 JSON 列表字符串存储）
                    saved_paths = []
                    if images and isinstance(images, list):
                        for arcname in images:
                            arcname = str(arcname).replace('\\', '/').lstrip('/')
                            if arcname not in zf.namelist():
                                continue
                            ext = os.path.splitext(arcname)[1] or '.png'
                            unique_filename = f"{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex}{ext}"
                            image_save_dir = os.path.join(upload_folder, 'question_images')
                            os.makedirs(image_save_dir, exist_ok=True)
                            image_save_path = os.path.join(image_save_dir, unique_filename)

                            with zf.open(arcname) as source, open(image_save_path, 'wb') as target:
                                target.write(source.read())
                            saved_paths.append(f'question_images/{unique_filename}')

                    image_path_val = json.dumps(saved_paths, ensure_ascii=False) if saved_paths else '[]'

                    # 4. 插入题目数据 (忽略原始ID，PQF 同名列)
                    created_by = session.get('user_id') or q.get('created_by')
                    db.session.execute(
                        text("""
                        INSERT INTO questions (
                            subject_id, type, content, options, answer, analysis, tags, difficulty,
                            image_path, created_by, updated_by, created_at, updated_at
                        ) VALUES (:subject_id, :type, :content, :options, :answer, :analysis, :tags, :difficulty,
                            :image_path, :created_by, :updated_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """),
                        {
                            'subject_id': subject_id,
                            'type': portable.get('type') or 'essay',
                            'content': portable.get('content') or '',
                            'options': json.dumps(portable.get('options') or [], ensure_ascii=False),
                            'answer': json.dumps(
                                portable.get('answer') if portable.get('answer') is not None else [],
                                ensure_ascii=False,
                            ),
                            'analysis': portable.get('analysis') or '',
                            'tags': json.dumps(portable.get('tags') or [], ensure_ascii=False),
                            'difficulty': int(portable.get('difficulty') or 1),
                            'image_path': image_path_val,
                            'created_by': created_by,
                            'updated_by': session.get('user_id') or created_by,
                        },
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f"导入题目ID {q.get('id', 'N/A')} 时出错: {str(e)}")

        db.session.commit()
        try:
            bump_questions_version()
        except Exception:
            pass
        try:
            bump_subjects_version()
        except Exception:
            pass

        message = f'成功导入 {imported_count} 道题。'
        if errors:
            message += f' 遇到 {len(errors)} 个问题。'

        return jsonify({
            'status': 'success' if not errors else 'warning',
            'message': message,
            'imported_count': imported_count,
            'errors': errors
        })

    except zipfile.BadZipFile:
        return jsonify({'status': 'error', 'message': '文件不是一个有效的ZIP压缩包'}), 400
    except Exception as e:
        db.session.rollback() # 如果发生意外错误，回滚事务
        return jsonify({'status': 'error', 'message': f'处理文件时发生未知错误: {str(e)}'}), 500
