# -*- coding: utf-8 -*-
"""???? API ????

?????????????????????????????
"""

import json
import random
import string
from datetime import datetime

from flask import request

from app.core.utils.database import get_db
from app.core.utils.time_utils import now_bj

from .api_bp import user_bank_api_bp

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

# ============================================
# 工具函数
# ============================================

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
        permission = 'copy' if bank['allow_copy'] else 'read'
        return (True, permission, 'public')

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

def _parse_question_ids_from_request_args():
    raw = (request.args.get('ids') or request.args.get('question_ids') or '').strip()
    ids = []

    if raw:
        for part in raw.replace(' ', '').split(','):
            if not part:
                continue
            try:
                ids.append(int(part))
            except Exception:
                continue
    else:
        for key in ('id', 'question_id', 'question_ids'):
            for v in request.args.getlist(key):
                try:
                    ids.append(int(v))
                except Exception:
                    continue

    if not ids:
        return []

    # 去重但保留顺序
    seen = set()
    result = []
    for i in ids:
        if i in seen:
            continue
        seen.add(i)
        result.append(i)
    return result

def _get_bank_tag_store_key(bank_id: int) -> str:
    """获取题库标签存储的 key"""
    return f'bank_{bank_id}_tags'


def _load_bank_tag_store(conn, bank_id: int, user_id: int) -> dict:
    """
    加载题库的标签存储数据
    结构: { 'tags': ['tag1', 'tag2', ...], 'question_tags': { 'q_id': ['tag1', ...], ... } }
    """
    key = _get_bank_tag_store_key(bank_id)
    row = conn.execute(
        'SELECT data FROM user_progress WHERE user_id = ? AND p_key = ?',
        (user_id, key)
    ).fetchone()

    if row and row['data']:
        try:
            return json.loads(row['data'])
        except:
            pass

    return {'tags': [], 'question_tags': {}}


def _save_bank_tag_store(conn, bank_id: int, user_id: int, store: dict):
    """保存题库的标签存储数据"""
    key = _get_bank_tag_store_key(bank_id)
    data_str = json.dumps(store, ensure_ascii=False)

    existing = conn.execute(
        'SELECT id FROM user_progress WHERE user_id = ? AND p_key = ?',
        (user_id, key)
    ).fetchone()

    if existing:
        conn.execute(
            'UPDATE user_progress SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (data_str, existing['id'])
        )
    else:
        conn.execute(
            'INSERT INTO user_progress (user_id, p_key, data) VALUES (?, ?, ?)',
            (user_id, key, data_str)
        )

    conn.commit()

