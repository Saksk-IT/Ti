# -*- coding: utf-8 -*-
"""刷题 API 共享工具函数"""

from flask import request, session
from typing import Optional

def _get_uid_from_request():
    """获取用户ID（优先 session，其次 JWT header；无需强制登录）"""
    uid = session.get('user_id')
    if uid:
        return uid

    token = request.headers.get('Authorization') or request.headers.get('authorization')
    if not token:
        return None
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        from app.core.utils.jwt_utils import decode_jwt_token
        payload = decode_jwt_token(token)
        if payload and payload.get('user_id'):
            return payload.get('user_id')
    except Exception:
        return None

    return None


def _resolve_study_scope(conn, source: str, subject: Optional[str], bank_id: Optional[int], uid: int):
    """èŽ·å– Study å¯¹åº"çš„ scope_idï¼Œå¹¶æ£€æŸ¥æƒé™"""
    source = (source or 'public').strip().lower()
    if source == 'user_bank':
        if not bank_id:
            return None, 'bank_id 参数错误'
        from app.modules.user_bank.routes.api import check_bank_access
        has_access, _permission, _access_type = check_bank_access(uid, int(bank_id))
        if not has_access:
            return None, '无权访问该题库'
        return int(bank_id), None

    subject = (subject or '').strip()
    if not subject:
        return None, 'subject 参数错误'
    row = conn.execute("SELECT id FROM subjects WHERE name = ?", (subject,)).fetchone()
    if not row:
        return None, 'subject 不存在'
    return int(row['id']), None


def _check_question_scope(conn, source: str, scope_id: int, question_id: int) -> bool:
    if source == 'user_bank':
        row = conn.execute(
            "SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?",
            (question_id, scope_id),
        ).fetchone()
        return bool(row)
    row = conn.execute(
        "SELECT id FROM questions WHERE id = ? AND subject_id = ?",
        (question_id, scope_id),
    ).fetchone()
    return bool(row)

