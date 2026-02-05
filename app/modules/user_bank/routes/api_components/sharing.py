# -*- coding: utf-8 -*-

import json
import uuid
from datetime import datetime, timedelta

from flask import request, jsonify, current_app

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import now_bj

from ..api_bp import user_bank_api_bp
from ..api_shared import (
    check_bank_access,
    generate_share_code,
    get_bank_category_name,
    _parse_question_ids_from_request_args,
    _get_bank_tag_store_key,
    _load_bank_tag_store,
    _save_bank_tag_store,
)


@user_bank_api_bp.route('/join', methods=['POST'])
@auth_required
def join_bank():
    """通过分享码/链接加入题库"""
    user_id = current_user_id()
    data = request.get_json() or {}
    share_code = (data.get('share_code') or '').strip().upper()
    share_token = (data.get('token') or '').strip()

    if not share_code and not share_token:
        return jsonify({'code': 1, 'message': '请提供分享码或分享链接'}), 400

    conn = get_db()

    if share_code:
        share = conn.execute(
            'SELECT * FROM bank_shares WHERE share_code = ? AND is_active = 1',
            (share_code,)
        ).fetchone()
    else:
        share = conn.execute(
            'SELECT * FROM bank_shares WHERE share_token = ? AND is_active = 1',
            (share_token,)
        ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享码/链接无效或已过期'}), 404

    # 检查过期
    if share['expires_at']:
        if datetime.fromisoformat(share['expires_at']) < now_bj():
            return jsonify({'code': 1, 'message': '分享已过期'}), 400

    # 检查使用次数
    if share['max_uses'] and share['current_uses'] >= share['max_uses']:
        return jsonify({'code': 1, 'message': '分享已达到最大使用次数'}), 400

    # 不能加入自己的题库
    if share['owner_id'] == user_id:
        return jsonify({'code': 1, 'message': '不能加入自己的题库'}), 400

    bank_id = share['bank_id']

    # 检查题库状态
    bank = conn.execute(
        'SELECT b.*, u.username as owner_username FROM user_question_banks b JOIN users u ON b.user_id = u.id WHERE b.id = ? AND b.status = 1',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或已被删除'}), 404

    # 检查是否已加入
    existing = conn.execute(
        'SELECT id, status FROM bank_share_records WHERE share_id = ? AND user_id = ?',
        (share['id'], user_id)
    ).fetchone()

    if existing:
        if existing['status'] == 1:
            return jsonify({'code': 1, 'message': '您已加入此题库'}), 400
        else:
            # 重新激活
            conn.execute(
                'UPDATE bank_share_records SET status = 1, last_access_at = CURRENT_TIMESTAMP WHERE id = ?',
                (existing['id'],)
            )
    else:
        conn.execute('''
            INSERT INTO bank_share_records (share_id, bank_id, user_id, last_access_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (share['id'], bank_id, user_id))

        # 更新使用次数
        conn.execute(
            'UPDATE bank_shares SET current_uses = current_uses + 1 WHERE id = ?',
            (share['id'],)
        )

    conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'bank_id': bank_id,
            'bank_name': bank['name'],
            'owner_nickname': bank['owner_username'],
            'question_count': bank['question_count'],
            'permission': share['permission']
        }
    })


@user_bank_api_bp.route('/shared', methods=['GET'])
@auth_required
def get_shared_banks():
    """获取收到的分享列表"""
    user_id = current_user_id()
    conn = get_db()

    banks = conn.execute('''
        SELECT b.id as bank_id, b.name as bank_name, b.question_count,
               bs.permission, bsr.last_access_at, bsr.access_count,
               u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar
        FROM bank_share_records bsr
        JOIN bank_shares bs ON bsr.share_id = bs.id
        JOIN user_question_banks b ON bsr.bank_id = b.id
        JOIN users u ON b.user_id = u.id
        WHERE bsr.user_id = ? AND bsr.status = 1 AND b.status = 1 AND bs.is_active = 1
        ORDER BY bsr.last_access_at DESC
    ''', (user_id,)).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'banks': [dict(b) for b in banks]
        }
    })


@user_bank_api_bp.route('/shared/<int:bank_id>', methods=['DELETE'])
@auth_required
def remove_shared_bank(bank_id):
    """移除收到的分享"""
    user_id = current_user_id()
    conn = get_db()

    conn.execute('''
        UPDATE bank_share_records SET status = 0
        WHERE user_id = ? AND bank_id = ?
    ''', (user_id, bank_id))
    conn.commit()

    return jsonify({'code': 0, 'message': '已移除'})
