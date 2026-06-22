# -*- coding: utf-8 -*-
"""用户题库：题目查重 API。"""

from __future__ import annotations

from flask import request
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import auth_required, current_user_id
from app.modules.user_bank.services.duplicate_check_service import (
    DEFAULT_SIMILARITY_THRESHOLD,
    check_bank_duplicates,
    normalize_similarity_threshold,
)

from .api_base import user_bank_api_bp


@user_bank_api_bp.route("/<int:bank_id>/questions/duplicate-check", methods=["GET"])
@auth_required
def get_question_duplicates(bank_id: int):
    user_id = _current_int_user_id()
    if user_id is None:
        return error_response("请先登录", 401, code=401)
    if not _is_bank_owner(bank_id, user_id):
        return error_response("题库不存在或无权操作", 404)

    threshold = normalize_similarity_threshold(
        request.args.get("similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD, type=float)
    )
    result = check_bank_duplicates(int(bank_id), threshold)
    return success_response(data=result)


def _current_int_user_id() -> int | None:
    try:
        return int(current_user_id())
    except Exception:
        return None


def _is_bank_owner(bank_id: int, user_id: int) -> bool:
    row = db.session.execute(
        text(
            """
            SELECT id
            FROM user_question_banks
            WHERE id = :bank_id AND user_id = :user_id AND status = 1
            """
        ),
        {"bank_id": int(bank_id), "user_id": int(user_id)},
    ).fetchone()
    return row is not None
