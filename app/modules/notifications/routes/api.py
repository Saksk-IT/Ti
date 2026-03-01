# -*- coding: utf-8 -*-
"""用户侧通知 API（ORM 版本）

接口：
- GET  /api/notifications               列表
- GET  /api/notifications/<id>          详情
- POST /api/notifications/<id>/read     标记已读
- POST /api/notifications/<id>/dismiss  关闭通知
- GET  /api/notifications/unread_count  未读数
"""
import logging

from flask import Blueprint, jsonify, session, request
from app.core.extensions import db, limiter
from app.core.utils.decorators import auth_required, current_user_id, _validate_jwt_user
from app.core.utils.jwt_utils import decode_jwt_token
from app.core.utils.time_utils import now_bj
from app.models.notification import Notification, NotificationDismissal

logger = logging.getLogger(__name__)

notifications_api_bp = Blueprint('notifications_api', __name__)


def _bool_arg(val) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ('1', 'true', 'yes', 'y', 'on')


def _optional_auth_user_id():
    """可选鉴权：若带 JWT 则校验并返回 uid；否则回退 session；无鉴权返回 None。"""
    token = request.headers.get('Authorization') or request.headers.get('authorization')
    if token:
        raw = str(token).strip()
        if raw.startswith('Bearer '):
            raw = raw[7:].strip()
        try:
            payload = decode_jwt_token(raw)
        except Exception:
            return None, 'token验证失败'

        ok, err = _validate_jwt_user(payload or {})
        if not ok:
            return None, err or 'token无效或已过期'

        try:
            uid = int((payload or {}).get('user_id') or 0)
        except Exception:
            uid = 0
        return (uid if uid > 0 else None), None

    uid = session.get('user_id')
    if uid:
        try:
            return int(uid), None
        except Exception:
            return None, None
    return None, None
def _active_filter():
    """返回通知活跃状态的通用过滤条件列表。"""
    now = now_bj()
    return [
        Notification.is_active == True,  # noqa: E712
        db.or_(Notification.start_at.is_(None), Notification.start_at <= now),
        db.or_(Notification.end_at.is_(None), Notification.end_at >= now),
    ]


def _notification_to_dict(n, is_read: bool = False) -> dict:
    return {
        'id': n.id,
        'title': n.title,
        'content': n.content,
        'n_type': n.n_type,
        'priority': n.priority,
        'start_at': n.start_at.isoformat() if n.start_at else None,
        'end_at': n.end_at.isoformat() if n.end_at else None,
        'created_at': n.created_at.isoformat() if n.created_at else None,
        'is_read': 1 if is_read else 0,
    }


@notifications_api_bp.route('/notifications')
@limiter.limit("60 per minute;600 per hour")
def api_notifications_list():
    uid, auth_err = _optional_auth_user_id()
    if auth_err:
        return jsonify({'status': 'unauthorized', 'message': auth_err}), 401

    limit = max(1, min(int(request.args.get('limit') or 50), 200))
    include_dismissed = _bool_arg(request.args.get('include_dismissed'))
    now = now_bj()

    if uid is not None:
        # 已登录：LEFT JOIN dismissals 判断已读
        dismissed_sub = (
            db.session.query(NotificationDismissal.notification_id)
            .filter(NotificationDismissal.user_id == uid)
            .subquery()
        )

        query = (
            db.session.query(
                Notification,
                dismissed_sub.c.notification_id.isnot(None).label('is_read'),
            )
            .outerjoin(dismissed_sub, Notification.id == dismissed_sub.c.notification_id)
            .filter(*_active_filter())
        )

        if not include_dismissed:
            query = query.filter(dismissed_sub.c.notification_id.is_(None))

        rows = (
            query
            .order_by(Notification.priority.desc(), Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .all()
        )
        data = [_notification_to_dict(n, bool(is_read)) for n, is_read in rows]
    else:
        # 未登录：全部标记为未读
        rows = (
            db.session.query(Notification)
            .filter(*_active_filter())
            .order_by(Notification.priority.desc(), Notification.created_at.desc(), Notification.id.desc())
            .limit(limit)
            .all()
        )
        data = [_notification_to_dict(n, False) for n in rows]

    return jsonify({'status': 'success', 'data': data})
@notifications_api_bp.route('/notifications/<int:nid>')
@limiter.limit("60 per minute;600 per hour")
@auth_required
def api_notifications_detail(nid: int):
    uid = int(current_user_id() or 0)
    include_dismissed = _bool_arg(request.args.get('include_dismissed'))

    dismissed_sub = (
        db.session.query(NotificationDismissal.notification_id)
        .filter(NotificationDismissal.user_id == uid)
        .subquery()
    )

    query = (
        db.session.query(
            Notification,
            dismissed_sub.c.notification_id.isnot(None).label('is_read'),
        )
        .outerjoin(dismissed_sub, Notification.id == dismissed_sub.c.notification_id)
        .filter(Notification.id == nid, *_active_filter())
    )

    if not include_dismissed:
        query = query.filter(dismissed_sub.c.notification_id.is_(None))

    result = query.first()
    if not result:
        return jsonify({'status': 'error', 'message': '通知不存在或已失效'}), 404

    n, is_read = result
    return jsonify({'status': 'success', 'data': _notification_to_dict(n, bool(is_read))})


def _upsert_dismissal(uid: int, nid: int):
    """插入或更新 dismissal 记录。"""
    existing = (
        db.session.query(NotificationDismissal)
        .filter_by(user_id=uid, notification_id=nid)
        .first()
    )
    if existing:
        existing.dismissed_at = now_bj()
    else:
        db.session.add(NotificationDismissal(user_id=uid, notification_id=nid))
    db.session.commit()


@notifications_api_bp.route('/notifications/<int:nid>/read', methods=['POST'])
@limiter.limit("30 per minute;300 per hour")
@auth_required
def api_notifications_mark_read(nid: int):
    uid = int(current_user_id() or 0)

    n = db.session.query(Notification).filter(Notification.id == nid, *_active_filter()).first()
    if not n:
        return jsonify({'status': 'error', 'message': '通知不存在或已失效'}), 404

    try:
        _upsert_dismissal(uid, nid)
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@notifications_api_bp.route('/notifications/<int:nid>/dismiss', methods=['POST'])
@limiter.limit("30 per minute;300 per hour")
@auth_required
def api_notifications_dismiss(nid: int):
    """关闭通知（刷新不再出现）"""
    uid = int(current_user_id() or 0)

    n = db.session.query(Notification).filter(Notification.id == nid, *_active_filter()).first()
    if not n:
        return jsonify({'status': 'error', 'message': '通知不存在或已失效'}), 404

    try:
        _upsert_dismissal(uid, nid)
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@notifications_api_bp.route('/notifications/unread_count')
@limiter.limit("60 per minute;600 per hour")
@auth_required
def api_notifications_unread_count():
    uid = int(current_user_id() or 0)

    dismissed_ids = (
        db.session.query(NotificationDismissal.notification_id)
        .filter(NotificationDismissal.user_id == uid)
        .subquery()
    )

    count = (
        db.session.query(db.func.count(Notification.id))
        .filter(*_active_filter())
        .filter(Notification.id.notin_(db.session.query(dismissed_ids.c.notification_id)))
        .scalar()
    ) or 0

    return jsonify({'status': 'success', 'count': count})
