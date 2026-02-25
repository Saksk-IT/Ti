# -*- coding: utf-8 -*-
"""统一 API 响应格式工具"""

from __future__ import annotations

from typing import Any, Optional

from flask import jsonify


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    **kwargs: Any,
):
    """构造成功响应。

    返回格式：{'status': 'success', 'code': 0, 'data': ..., 'message': ...}
    过渡期同时包含 status 和 code 字段，确保新旧客户端兼容。
    """
    payload: dict[str, Any] = {'status': 'success', 'code': 0}
    if data is not None:
        payload['data'] = data
    if message:
        payload['message'] = message
    payload.update(kwargs)
    return jsonify(payload)


def error_response(
    message: str = '操作失败',
    status_code: int = 400,
    code: int = 1,
    **kwargs: Any,
):
    """构造错误响应。

    返回格式：{'status': 'error', 'code': ..., 'message': ...}
    """
    payload: dict[str, Any] = {'status': 'error', 'code': code, 'message': message}
    payload.update(kwargs)
    return jsonify(payload), status_code
