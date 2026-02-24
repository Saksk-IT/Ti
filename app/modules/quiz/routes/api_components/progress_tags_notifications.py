# -*- coding: utf-8 -*-

import json
import logging
from typing import Optional

from flask import request, jsonify, session
from sqlalchemy import or_

from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.cache_utils import bump_user_quiz_version
from app.core.utils.time_utils import now_bj
from app.models.quiz import UserProgress
from app.models.subject import Subject
from app.models.notification import Notification, NotificationDismissal

from ..api_bp import quiz_api_bp
from ..api_shared import _get_uid_from_request, _resolve_study_scope, _check_question_scope

logger = logging.getLogger(__name__)


@quiz_api_bp.route('/progress', methods=['GET', 'POST', 'DELETE'])
@auth_required
@limiter.exempt
def progress_api():
    """用户答题进度同步API"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    if request.method == 'GET':
        key = request.args.get('key', '').strip()
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400

        try:
            row = UserProgress.query.filter_by(user_id=uid, p_key=key).first()
            if row:
                data = json.loads(row.data)
                return jsonify({'status': 'success', 'data': data})
            else:
                return jsonify({'status': 'success', 'data': None})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    elif request.method == 'POST':
        data = request.json
        key = data.get('key', '').strip()
        progress_data = data.get('data')

        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400

        try:
            data_json = json.dumps(progress_data, ensure_ascii=False)

            existing = UserProgress.query.filter_by(user_id=uid, p_key=key).first()
            if existing:
                existing.data = data_json
            else:
                db.session.add(UserProgress(user_id=uid, p_key=key, data=data_json))
            db.session.commit()

            return jsonify({'status': 'success', 'message': '进度已保存'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500

    elif request.method == 'DELETE':
        key = request.args.get('key', '').strip()
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400

        try:
            UserProgress.query.filter_by(user_id=uid, p_key=key).delete()
            db.session.commit()
            return jsonify({'status': 'success', 'message': '进度已删除'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/tags', methods=['GET', 'POST', 'DELETE'])
@auth_required
@limiter.exempt
def tags_api():
    """用户题目标签（公共题库：按"用户 × 科目(subject_id)"隔离）。"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    from app.modules.quiz.services.question_tags_service import (
        list_user_tags,
        create_user_tag,
        delete_user_tag,
    )

    conn = db.session.connection()

    def _resolve_subject_id(payload: Optional[dict] = None) -> int:
        payload = payload or {}

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

        subject_name = (request.args.get('subject') or payload.get('subject') or '').strip()
        if not subject_name or subject_name.lower() == 'all':
            return 0
        try:
            row = Subject.query.filter_by(name=subject_name).filter(
                or_(Subject.is_locked == False, Subject.is_locked.is_(None))
            ).first()
            if not row:
                return 0
            return row.id
        except Exception:
            return 0

    def _check_subject_access(subject_id: int) -> Optional[tuple]:
        try:
            sid = int(subject_id or 0)
        except Exception:
            sid = 0
        if sid <= 0:
            return None

        try:
            row = Subject.query.filter_by(id=sid).filter(
                or_(Subject.is_locked == False, Subject.is_locked.is_(None))
            ).first()
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
            db.session.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        db.session.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        tags = list_user_tags(conn, uid, sid)
        return jsonify({'status': 'success', 'data': {'tag': tag, 'tags': tags, 'subject_id': sid}})

    if request.method == 'DELETE':
        ok, msg = delete_user_tag(conn, uid, sid, name)
        if not ok:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        db.session.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        tags = list_user_tags(conn, uid, sid)
        return jsonify({'status': 'success', 'data': {'tags': tags, 'subject_id': sid}})

    return jsonify({'status': 'error', 'message': '不支持的请求方式'}), 405


@quiz_api_bp.route('/questions/<int:question_id>/tags', methods=['GET', 'POST'])
@auth_required
@limiter.exempt
def question_tags_api(question_id: int):
    """题目标签管理（对当前用户生效）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    from app.models.subject import Question as QuestionModel
    question_obj = db.session.get(QuestionModel, question_id)
    if not question_obj:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    from app.core.utils.subject_permissions import can_user_access_subject
    if question_obj.subject_id and not can_user_access_subject(uid, question_obj.subject_id):
        return jsonify({'status': 'error', 'message': '无权限访问该题目'}), 403

    from app.modules.quiz.services.question_tags_service import (
        get_question_tags,
        set_question_tags,
        update_question_tags,
    )

    conn = db.session.connection()

    if request.method == 'GET':
        tags = get_question_tags(conn, uid, question_id)
        sid = question_obj.subject_id or 0
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
            db.session.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        db.session.commit()
        try:
            bump_user_quiz_version(int(uid))
        except Exception:
            pass
        sid = question_obj.subject_id or 0
        return jsonify({'status': 'success', 'data': {'question_id': question_id, 'subject_id': sid, 'tags': tags}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/notifications_legacy', methods=['GET'])
@limiter.exempt
def get_notifications_legacy():
    """[兼容] 获取当前用户可见的通知列表（旧接口）"""
    uid = session.get('user_id')
    now = now_bj()

    base_query = Notification.query.filter(
        Notification.is_active == True,
        or_(Notification.start_at.is_(None), Notification.start_at <= now),
        or_(Notification.end_at.is_(None), Notification.end_at >= now),
    )

    if uid:
        dismissed_ids = db.session.query(
            NotificationDismissal.notification_id
        ).filter(
            NotificationDismissal.user_id == uid
        ).subquery()

        rows = base_query.filter(
            ~Notification.id.in_(db.session.query(dismissed_ids))
        ).order_by(
            Notification.priority.desc(), Notification.created_at.desc()
        ).all()
    else:
        rows = base_query.order_by(
            Notification.priority.desc(), Notification.created_at.desc()
        ).all()

    return jsonify({
        'status': 'success',
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'content': n.content,
                'n_type': n.n_type,
                'priority': n.priority,
            }
            for n in rows
        ]
    })


@quiz_api_bp.route('/notifications_legacy/<int:nid>/dismiss', methods=['POST'])
@limiter.exempt
def dismiss_notification_legacy(nid):
    """[兼容] 关闭/隐藏指定通知（旧接口）"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401

    try:
        existing = NotificationDismissal.query.filter_by(
            user_id=uid, notification_id=nid
        ).first()
        if not existing:
            db.session.add(NotificationDismissal(user_id=uid, notification_id=nid))
            db.session.commit()
        return jsonify({'status': 'success', 'message': '通知已关闭'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
