# -*- coding: utf-8 -*-
"""Build AI explain payloads with source-specific permission checks."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from sqlalchemy import text

from app.core.extensions import db
from app.core.services.question_service import QuestionService as Question


PayloadResult = Tuple[Dict[str, Any], Optional[Dict[str, Any]]]


def _parse_int(value: Any) -> Optional[int]:
    try:
        if value is None or str(value).strip() == '':
            return None
        parsed = int(value)
        return parsed if parsed > 0 else None
    except Exception:
        return None


def _base_payload(data: Dict[str, Any], qid: Optional[int]) -> Dict[str, Any]:
    return {
        'question_id': qid,
        'content': (data.get('content') or '').strip(),
        'q_type': (data.get('q_type') or '').strip(),
        'options': data.get('options'),
        'answer': (data.get('answer') or '').strip(),
    }


def _error(message: str, *, status_code: int = 400, status: str = 'error') -> Dict[str, Any]:
    return {'status': status, 'message': message, 'status_code': int(status_code)}


def _build_public_payload(uid: Optional[int], data: Dict[str, Any], qid: Optional[int]) -> PayloadResult:
    from app.core.utils.subject_permissions import can_user_access_subject

    payload = _base_payload(data, qid)
    payload['source'] = 'public'

    if qid:
        q = Question.get_by_id(qid)
        if q:
            subject_id = q.get('subject_id')
            if subject_id and uid and not can_user_access_subject(uid, subject_id):
                return payload, _error('无权限访问该题目', status_code=403, status='forbidden')

            payload['content'] = (q.get('content') or '').strip()
            payload['q_type'] = (q.get('q_type') or '').strip()
            payload['options'] = q.get('options')
            payload['answer'] = (q.get('answer') or '').strip()

    return payload, None


def _build_user_bank_payload(
    uid: Optional[int],
    data: Dict[str, Any],
    qid: Optional[int],
    bank_id: Optional[int],
    ai_cfg: Dict[str, Any],
) -> PayloadResult:
    if not ai_cfg.get('user_bank_explain_enabled'):
        return {}, _error('个人题库 AI 解析未开启，请联系管理员在后台 AI 配置中启用。', status_code=403)

    if not uid:
        return {}, _error('请先登录', status_code=401, status='unauthorized')

    if not bank_id:
        return {}, _error('缺少题库信息', status_code=400)

    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, _access_type = check_bank_access(int(uid), int(bank_id))
    if not has_access:
        return {}, _error('无权限访问该题库', status_code=403, status='forbidden')

    payload = _base_payload(data, qid)
    payload['source'] = 'user_bank'
    payload['bank_id'] = int(bank_id)

    if qid:
        row = db.session.execute(
            text('SELECT * FROM user_bank_questions WHERE id = :qid AND bank_id = :bank_id'),
            {'qid': int(qid), 'bank_id': int(bank_id)},
        ).fetchone()
        if not row:
            return payload, _error('题目不存在或无权限', status_code=404)

        q = Question._row_to_internal(row, scope='user_bank')
        payload['content'] = (q.get('content') or '').strip()
        payload['q_type'] = (q.get('q_type') or '').strip()
        payload['options'] = q.get('options')
        payload['answer'] = (q.get('answer') or '').strip()

    return payload, None


def build_ai_explain_payload(uid: Optional[int], data: Dict[str, Any], ai_cfg: Dict[str, Any]) -> PayloadResult:
    """Build trusted AI explain payload from request data.

    Public question requests continue to resolve by question_id. User-bank
    requests must opt in via source=user_bank or bank_id, pass the admin
    feature switch, and pass bank access checks before DB values are used.
    """
    raw = data if isinstance(data, dict) else {}
    qid = _parse_int(raw.get('question_id'))
    bank_id = _parse_int(raw.get('bank_id'))
    source = str(raw.get('source') or '').strip().lower()

    if source == 'user_bank' or bank_id:
        return _build_user_bank_payload(uid, raw, qid, bank_id, ai_cfg)

    return _build_public_payload(uid, raw, qid)
