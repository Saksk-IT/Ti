# -*- coding: utf-8 -*-

"""用户题库 API：蓝图与通用工具

说明：
- 将 `app.modules.user_bank.routes.api` 拆分后的公共部分集中在此文件。
- 仅放置蓝图对象、兼容返回处理、以及跨模块复用的权限/分享工具函数。
"""

import json
import random
import string
from datetime import datetime

from flask import Blueprint

from app.core.utils.database import get_db
from app.core.utils.time_utils import now_bj


user_bank_api_bp = Blueprint('user_bank_api', __name__)


@user_bank_api_bp.after_request
def _compat_add_status_field(response):
    try:
        if not response.is_json:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict):
            return response
        if 'status' in payload or 'code' not in payload:
            return response

        payload['status'] = 'success' if payload.get('code') == 0 else 'error'
        response.set_data(json.dumps(payload, ensure_ascii=False))
    except Exception:
        return response
    return response


def generate_share_code(length=6):
    """生成6位大写字母+数字分享码"""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        # 确保至少包含1个字母和1个数字
        if any(c.isalpha() for c in code) and any(c.isdigit() for c in code):
            return code


def check_bank_access(user_id, bank_id):
    """
    检查用户是否有权访问题库
    返回: (has_access: bool, permission: str, access_type: str)
    """
    conn = get_db()
    bank = conn.execute(
        'SELECT * FROM user_question_banks WHERE id = ?',
        (bank_id,)
    ).fetchone()

    if not bank or bank['status'] == 0:
        return (False, None, None)

    # 1. 创建者：完全权限
    if bank['user_id'] == user_id:
        return (True, 'owner', 'owner')

    # 2. 公开题库：所有登录用户可访问
    if bank['is_public']:
        return (True, 'read', 'public')

    # 3. 分享授权：检查分享记录
    share_record = conn.execute('''
        SELECT bsr.*, bs.permission, bs.is_active, bs.expires_at
        FROM bank_share_records bsr
        JOIN bank_shares bs ON bsr.share_id = bs.id
        WHERE bsr.user_id = ? AND bsr.bank_id = ? AND bsr.status = 1
    ''', (user_id, bank_id)).fetchone()

    if share_record:
        share_active = share_record['is_active']
        expires_at = share_record['expires_at']
        if share_active and (not expires_at or datetime.fromisoformat(expires_at) > now_bj()):
            return (True, share_record['permission'], 'shared')

    # 4. 未授权
    return (False, None, None)


def get_bank_category_name(category_id, user_id):
    """获取分类名称"""
    if not category_id:
        return None
    conn = get_db()
    cat = conn.execute(
        'SELECT name FROM user_bank_categories WHERE id = ? AND user_id = ?',
        (category_id, user_id)
    ).fetchone()
    return cat['name'] if cat else None
