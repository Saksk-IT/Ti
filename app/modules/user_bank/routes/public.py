# -*- coding: utf-8 -*-
"""公开题库广场路由。"""

from __future__ import annotations

from typing import Optional

from flask import Blueprint, render_template, request, session, redirect
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import (
    _validate_jwt_user,
    auth_required,
    current_user_id,
    login_required,
)
from app.core.utils.jwt_utils import decode_jwt_token
from app.modules.user_bank.services.plaza_metrics_service import ensure_plaza_metrics
from app.modules.user_bank.services.plaza_query_service import (
    build_legacy_bank_list,
    get_plaza_summary,
    get_public_bank_detail,
    list_hot_public_banks,
    list_joined_banks,
    list_plaza_boards,
    list_public_banks,
)

public_bank_bp = Blueprint('public_bank', __name__)


@public_bank_bp.route('/public/banks')
def bank_plaza():
    """论坛式题库广场页面。"""
    return render_template('user_bank/public/plaza.html', **_page_context())


@public_bank_bp.route('/public/banks/joined')
@login_required
def joined_bank_plaza():
    """旧加入题库页：统一重定向到“我的题库”。"""
    return redirect('/user/banks')


@public_bank_bp.route('/api/public/banks/summary', methods=['GET'])
def public_bank_summary():
    summary = get_plaza_summary(
        board_id=_query_int('board_id'),
        keyword=request.args.get('keyword', ''),
    )
    return success_response(summary)


@public_bank_bp.route('/api/public/banks/boards', methods=['GET'])
def public_bank_boards():
    items = list_plaza_boards(keyword=request.args.get('keyword', ''))
    return success_response({'items': items})


@public_bank_bp.route('/api/public/banks/hot', methods=['GET'])
def public_bank_hot():
    items = list_hot_public_banks(
        board_id=_query_int('board_id'),
        keyword=request.args.get('keyword', ''),
        limit=request.args.get('limit', 5, type=int),
    )
    return success_response({'items': items})


@public_bank_bp.route('/api/public/banks/list', methods=['GET'])
def public_bank_list():
    data = list_public_banks(
        tab=request.args.get('tab', 'latest'),
        board_id=_query_int('board_id'),
        keyword=request.args.get('keyword', ''),
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 12, type=int),
        user_id=_optional_user_id(),
    )
    return success_response(data)


@public_bank_bp.route('/api/public/banks/joined', methods=['GET'])
@auth_required
def public_bank_joined_list():
    data = list_joined_banks(
        user_id=int(current_user_id() or 0),
        scope=request.args.get('scope', 'all'),
        keyword=request.args.get('keyword', ''),
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 12, type=int),
    )
    return success_response(data)


@public_bank_bp.route('/api/public/banks', methods=['GET'])
def get_public_banks():
    """兼容旧客户端的题库广场列表接口。"""
    data = build_legacy_bank_list(
        sort=request.args.get('sort', 'newest'),
        bank_type=request.args.get('type', ''),
        keyword=request.args.get('keyword', ''),
        page=request.args.get('page', 1, type=int),
        per_page=request.args.get('per_page', 20, type=int),
        user_id=_optional_user_id(),
    )
    return success_response(data)


@public_bank_bp.route('/api/public/banks/<int:bank_id>', methods=['GET'])
def get_public_bank_detail_route(bank_id: int):
    bank = get_public_bank_detail(
        bank_id=bank_id,
        bank_type=request.args.get('type', 'user'),
    )
    if not bank:
        return error_response('题库不存在或未公开', status_code=404)
    return success_response(bank)


@public_bank_bp.route('/api/public/banks/<int:bank_id>/join', methods=['POST'])
@auth_required
def join_public_bank(bank_id: int):
    """加入公开题库并刷新使用统计。"""
    user_id = int(current_user_id() or 0)
    bank = db.session.execute(
        text(
            """
            SELECT id, user_id
            FROM user_question_banks
            WHERE id = :bank_id AND is_public = true AND status = 1
            """
        ),
        {'bank_id': int(bank_id)},
    ).mappings().first()
    if not bank:
        return error_response('题库不存在或未公开', status_code=404)

    if int(bank.get('user_id') or 0) == user_id:
        return success_response({'joined': False, 'self_owned': True}, message='这是你自己的公开题库')

    existing = db.session.execute(
        text(
            """
            SELECT id
            FROM public_bank_users
            WHERE bank_id = :bank_id AND user_id = :user_id
            """
        ),
        {'bank_id': int(bank_id), 'user_id': user_id},
    ).mappings().first()

    if existing:
        db.session.execute(
            text(
                """
                UPDATE public_bank_users
                SET last_access_at = CURRENT_TIMESTAMP,
                    access_count = COALESCE(access_count, 0) + 1
                WHERE id = :record_id
                """
            ),
            {'record_id': int(existing['id'])},
        )
    else:
        db.session.execute(
            text(
                """
                INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
                VALUES (:bank_id, :user_id, CURRENT_TIMESTAMP, 1)
                """
            ),
            {'bank_id': int(bank_id), 'user_id': user_id},
        )
        db.session.execute(
            text(
                """
                UPDATE user_question_banks
                SET public_use_count = COALESCE(public_use_count, 0) + 1
                WHERE id = :bank_id
                """
            ),
            {'bank_id': int(bank_id)},
        )

    db.session.commit()
    try:
        ensure_plaza_metrics(force=True)
    except Exception:
        pass
    return success_response({'joined': True}, message='已加入题库')


@public_bank_bp.route('/bank/join')
def join_bank_page():
    """分享链接跳转页面。"""
    token = request.args.get('token', '')
    return render_template('user_bank/share/join.html', token=token)


def _page_context() -> dict[str, object]:
    uid = session.get('user_id')
    return {
        'logged_in': bool(uid),
        'username': session.get('username'),
        'is_admin': session.get('is_admin', False),
        'is_subject_admin': session.get('is_subject_admin', False),
        'is_notification_admin': session.get('is_notification_admin', False),
        'user_id': uid or 0,
    }


def _optional_user_id() -> Optional[int]:
    token = request.headers.get('Authorization') or request.headers.get('authorization')
    if token:
        raw_token = str(token).strip()
        if raw_token.startswith('Bearer '):
            raw_token = raw_token[7:].strip()
        try:
            payload = decode_jwt_token(raw_token)
        except Exception:
            payload = None
        if payload:
            try:
                ok, _err = _validate_jwt_user(payload)
            except Exception:
                ok = False
            if ok:
                try:
                    uid = int(payload.get('user_id') or 0)
                    if uid > 0:
                        return uid
                except Exception:
                    return None

    try:
        uid = int(session.get('user_id') or 0)
        return uid if uid > 0 else None
    except Exception:
        return None


def _query_int(name: str) -> int | None:
    value = request.args.get(name, type=int)
    return int(value) if value and int(value) > 0 else None
