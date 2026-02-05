# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from flask import request, jsonify, session, g, current_app
from app.core.utils.database import get_db
from app.core.extensions import limiter
from app.core.utils.decorators import jwt_required, auth_required, current_user_id
from app.core.utils.cache_utils import bump_user_quiz_version
from typing import Optional
from app.core.models.question import Question
from app.core.utils.options_parser import parse_options
from app.modules.quiz.services.study_service import now_bj, dt_to_str, next_4am, calc_next_due, clamp_level
from app.modules.quiz.services.reinforcement_service import (
    find_similar_pairs_public,
    find_similar_pairs_user_bank,
    find_similar_training_ids_public,
    find_similar_training_ids_user_bank,
)

from ..api_bp import quiz_api_bp
from ..api_shared import _get_uid_from_request, _resolve_study_scope, _check_question_scope


@quiz_api_bp.route('/progress', methods=['GET', 'POST', 'DELETE'])
@auth_required  # 支持session和JWT（小程序/网页共用 user_progress）
@limiter.exempt  # 进度同步接口不限流
def progress_api():
    """用户答题进度同步API"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    conn = get_db()
    
    if request.method == 'GET':
        # 获取进度
        key = request.args.get('key', '').strip()
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400
        
        try:
            row = conn.execute(
                'SELECT data FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, key)
            ).fetchone()
            
            if row:
                import json
                data = json.loads(row['data'])
                return jsonify({'status': 'success', 'data': data})
            else:
                return jsonify({'status': 'success', 'data': None})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    elif request.method == 'POST':
        # 保存进度
        data = request.json
        key = data.get('key', '').strip()
        progress_data = data.get('data')
        
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400
        
        try:
            import json
            data_json = json.dumps(progress_data, ensure_ascii=False)
            
            # 先检查是否存在，存在则更新，不存在则插入
            existing = conn.execute(
                'SELECT id FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, key)
            ).fetchone()
            
            if existing:
                conn.execute(
                    """UPDATE user_progress 
                       SET data = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE user_id = ? AND p_key = ?""",
                    (data_json, uid, key)
                )
            else:
                # 检查是否有created_at字段
                try:
                    conn.execute(
                        """INSERT INTO user_progress (user_id, p_key, data, updated_at, created_at) 
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                        (uid, key, data_json)
                    )
                except:
                    # 如果created_at字段不存在,则不包含它
                    conn.execute(
                        """INSERT INTO user_progress (user_id, p_key, data, updated_at) 
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                        (uid, key, data_json)
                    )
            conn.commit()
            
            return jsonify({'status': 'success', 'message': '进度已保存'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    elif request.method == 'DELETE':
        # 删除进度
        key = request.args.get('key', '').strip()
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400
        
        try:
            conn.execute(
                'DELETE FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, key)
            )
            conn.commit()
            return jsonify({'status': 'success', 'message': '进度已删除'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/tags', methods=['GET', 'POST', 'DELETE'])
@auth_required  # 支持session和JWT
@limiter.exempt
def tags_api():
    """用户题目标签（公共题库：按“用户 × 科目(subject_id)”隔离）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    from app.modules.quiz.services.question_tags_service import (
        list_user_tags,
        create_user_tag,
        delete_user_tag,
    )

    conn = get_db()

    def _resolve_subject_id(payload: Optional[dict] = None) -> int:
        payload = payload or {}

        # 优先 subject_id
        raw_id = (
            request.args.get('subject_id')
            or request.args.get('subjectId')
            or payload.get('subject_id')
            or payload.get('subjectId')
        )
        if raw_id is not None and str(raw_id).strip() != "":
            try:
                return int(raw_id)
            except Exception:
                return 0

        # 兼容 subject=name
        subject_name = (request.args.get('subject') or payload.get('subject') or '').strip()
        if not subject_name or subject_name.lower() == 'all':
            return 0
        try:
            row = conn.execute(
                "SELECT id, is_locked FROM subjects WHERE name = ? AND (is_locked=0 OR is_locked IS NULL)",
                (subject_name,),
            ).fetchone()
            if not row:
                return 0
            return int(row["id"] or 0)
        except Exception:
            return 0

    def _check_subject_access(subject_id: int) -> Optional[tuple]:
        """返回 (ok:bool, err_msg:str)；ok==True 时 err_msg 为空。"""
        try:
            sid = int(subject_id or 0)
        except Exception:
            sid = 0
        if sid <= 0:
            return None

        try:
            row = conn.execute(
                "SELECT id, is_locked FROM subjects WHERE id = ? AND (is_locked=0 OR is_locked IS NULL)",
                (int(sid),),
            ).fetchone()
            if not row:
                return (False, '科目不存在')
        except Exception:
            return (False, '科目不存在')

        try:
            from app.core.utils.subject_permissions import can_user_access_subject

            if not can_user_access_subject(uid, int(sid)):
                return (False, '无权限访问该科目')
        except Exception:
            return (False, '无权限访问该科目')

        return (True, '')

    if request.method == 'GET':
        sid = _resolve_subject_id()
        if sid > 0:
            chk = _check_subject_access(sid)
            if chk and chk[0] is False:
                return jsonify({'status': 'error', 'message': chk[1]}), 403
            tags = list_user_tags(conn, uid, sid)
            return jsonify({'status': 'success', 'data': {'tags': tags, 'subject_id': sid}})

        tags = list_user_tags(conn, uid, None)
        return jsonify({'status': 'success', 'data': {'tags': tags}})

    data = request.get_json(silent=True) or {}
    name = data.get('name') or data.get('tag') or data.get('tag_name')
    sid = _resolve_subject_id(data)
    if sid <= 0:
        return jsonify({'status': 'error', 'message': '缺少 subject_id/subject 参数'}), 400
    chk = _check_subject_access(sid)
    if chk and chk[0] is False:
        return jsonify({'status': 'error', 'message': chk[1]}), 403

    if request.method == 'POST':
        ok, msg, tag = create_user_tag(conn, uid, sid, name)
        if not ok:
            conn.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        conn.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        tags = list_user_tags(conn, uid, sid)
        return jsonify({'status': 'success', 'data': {'tag': tag, 'tags': tags, 'subject_id': sid}})

    if request.method == 'DELETE':
        ok, msg = delete_user_tag(conn, uid, sid, name)
        if not ok:
            conn.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        conn.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        tags = list_user_tags(conn, uid, sid)
        return jsonify({'status': 'success', 'data': {'tags': tags, 'subject_id': sid}})

    return jsonify({'status': 'error', 'message': '不支持的请求方式'}), 405


@quiz_api_bp.route('/questions/<int:question_id>/tags', methods=['GET', 'POST'])
@auth_required  # 支持session和JWT
@limiter.exempt
def question_tags_api(question_id: int):
    """题目标签管理（对当前用户生效）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    # 校验题目存在 + 权限
    question = Question.get_by_id(question_id)
    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    from app.core.utils.subject_permissions import can_user_access_subject
    if question.get('subject_id') and not can_user_access_subject(uid, question['subject_id']):
        return jsonify({'status': 'error', 'message': '无权限访问该题目'}), 403

    from app.modules.quiz.services.question_tags_service import (
        get_question_tags,
        set_question_tags,
        update_question_tags,
    )

    conn = get_db()

    if request.method == 'GET':
        tags = get_question_tags(conn, uid, question_id)
        try:
            sid = int((question or {}).get('subject_id') or 0)
        except Exception:
            sid = 0
        return jsonify({'status': 'success', 'data': {'question_id': question_id, 'subject_id': sid, 'tags': tags}})

    data = request.json or {}
    try:
        if 'tags' in data:
            ok, msg, tags = set_question_tags(conn, uid, question_id, data.get('tags'))
        else:
            ok, msg, tags = update_question_tags(
                conn,
                uid,
                question_id,
                add=data.get('add'),
                remove=data.get('remove'),
            )
        if not ok:
            conn.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        conn.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        try:
            sid = int((question or {}).get('subject_id') or 0)
        except Exception:
            sid = 0
        return jsonify({'status': 'success', 'data': {'question_id': question_id, 'subject_id': sid, 'tags': tags}})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/notifications_legacy', methods=['GET'])
@limiter.exempt
def get_notifications_legacy():
    """[兼容] 获取当前用户可见的通知列表（旧接口）"""
    uid = session.get('user_id')
    conn = get_db()

    if uid:
        # 登录用户：排除已关闭的通知（旧逻辑：关闭=不显示）
        sql = '''
            SELECT n.id, n.title, n.content, n.n_type, n.priority
            FROM notifications n
            LEFT JOIN notification_dismissals d
                ON d.notification_id = n.id AND d.user_id = ?
            WHERE n.is_active = 1
              AND d.id IS NULL
              AND (n.start_at IS NULL OR replace(n.start_at, 'T', ' ') <= datetime('now', '+8 hours'))
              AND (n.end_at IS NULL OR replace(n.end_at, 'T', ' ') >= datetime('now', '+8 hours'))
            ORDER BY n.priority DESC, n.created_at DESC
        '''
        rows = conn.execute(sql, (uid,)).fetchall()
    else:
        # 游客：显示所有活跃通知
        sql = '''
            SELECT id, title, content, n_type, priority
            FROM notifications
            WHERE is_active = 1
              AND (start_at IS NULL OR replace(start_at, 'T', ' ') <= datetime('now', '+8 hours'))
              AND (end_at IS NULL OR replace(end_at, 'T', ' ') >= datetime('now', '+8 hours'))
            ORDER BY priority DESC, created_at DESC
        '''
        rows = conn.execute(sql).fetchall()

    return jsonify({
        'status': 'success',
        'notifications': [dict(row) for row in rows]
    })


@quiz_api_bp.route('/notifications_legacy/<int:nid>/dismiss', methods=['POST'])
@limiter.exempt
def dismiss_notification_legacy(nid):
    """[兼容] 关闭/隐藏指定通知（旧接口）"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401

    conn = get_db()
    try:
        conn.execute(
            'INSERT OR IGNORE INTO notification_dismissals (user_id, notification_id) VALUES (?, ?)',
            (uid, nid)
        )
        conn.commit()
        return jsonify({'status': 'success', 'message': '通知已关闭'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
