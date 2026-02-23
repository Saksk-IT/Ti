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


@user_bank_api_bp.route('/<int:bank_id>/shares', methods=['GET'])
@auth_required
def get_shares(bank_id):
    """获取分享列表"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    shares = conn.execute('''
        SELECT * FROM bank_shares WHERE bank_id = ? ORDER BY created_at DESC
    ''', (bank_id,)).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'shares': [dict(s) for s in shares]
        }
    })


@user_bank_api_bp.route('/shares/all', methods=['GET'])
@auth_required
def get_all_shares():
    """获取我创建的所有分享（跨题库汇总）"""
    user_id = current_user_id()
    conn = get_db()

    rows = conn.execute('''
        SELECT bs.*,
               b.name as bank_name
        FROM bank_shares bs
        JOIN user_question_banks b ON bs.bank_id = b.id
        WHERE bs.owner_id = ? AND b.status = 1
        ORDER BY bs.created_at DESC
    ''', (user_id,)).fetchall()

    base_url = current_app.config.get('SHARE_BASE_URL', request.host_url.rstrip('/'))
    shares = []
    for r in rows:
        d = dict(r)
        if d.get('share_token'):
            d['share_link'] = f'{base_url}/bank/join?token={d["share_token"]}'
        shares.append(d)

    return jsonify({
        'code': 0,
        'data': {
            'shares': shares
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/shares', methods=['POST'])
@auth_required
def create_share(bank_id):
    """创建分享"""
    user_id = current_user_id()
    data = request.get_json() or {}
    share_type = data.get('type', 'code')  # 'code' or 'link'
    permission = 'read'  # 复制功能已移除，统一为只读
    expires_in = data.get('expires_in')  # 有效天数
    max_uses = data.get('max_uses')

    if permission not in ('read',):
        return jsonify({'code': 1, 'message': '无效的权限级别'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 检查分享数量限制
    share_count = conn.execute(
        'SELECT COUNT(*) as cnt FROM bank_shares WHERE bank_id = ? AND is_active = 1',
        (bank_id,)
    ).fetchone()['cnt']

    if share_count >= 10:
        return jsonify({'code': 1, 'message': '每个题库最多只能创建10个分享'}), 400

    # 计算过期时间
    expires_at = None
    if expires_in:
        expires_at = (now_bj() + timedelta(days=int(expires_in))).isoformat()

    share_code = None
    share_token = None

    if share_type == 'code':
        # 生成唯一分享码
        while True:
            share_code = generate_share_code()
            existing = conn.execute(
                'SELECT id FROM bank_shares WHERE share_code = ?', (share_code,)
            ).fetchone()
            if not existing:
                break
    else:
        share_token = str(uuid.uuid4()).replace('-', '')

    cursor = conn.execute('''
        INSERT INTO bank_shares (bank_id, owner_id, share_code, share_token, permission, expires_at, max_uses)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (bank_id, user_id, share_code, share_token, permission, expires_at, max_uses))

    # 更新分享数量
    conn.execute(
        'UPDATE user_question_banks SET share_count = share_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    result = {
        'share_id': cursor.lastrowid,
        'expires_at': expires_at
    }

    if share_code:
        result['share_code'] = share_code
    if share_token:
        # 构建分享链接
        base_url = current_app.config.get('SHARE_BASE_URL', request.host_url.rstrip('/'))
        result['share_link'] = f'{base_url}/bank/join?token={share_token}'

    return jsonify({
        'code': 0,
        'data': result
    })


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>', methods=['DELETE'])
@auth_required
def delete_share(bank_id, share_id):
    """撤销分享"""
    user_id = current_user_id()
    conn = get_db()

    share = conn.execute(
        'SELECT id FROM bank_shares WHERE id = ? AND bank_id = ? AND owner_id = ?',
        (share_id, bank_id, user_id)
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    conn.execute('UPDATE bank_shares SET is_active = 0 WHERE id = ?', (share_id,))
    conn.commit()

    return jsonify({'code': 0, 'message': '分享已撤销'})


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>/records', methods=['GET'])
@auth_required
def get_share_records(bank_id, share_id):
    """查看分享使用记录"""
    user_id = current_user_id()
    conn = get_db()

    share = conn.execute(
        'SELECT id FROM bank_shares WHERE id = ? AND bank_id = ? AND owner_id = ?',
        (share_id, bank_id, user_id)
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    records = conn.execute('''
        SELECT bsr.*, u.username as nickname, u.avatar
        FROM bank_share_records bsr
        JOIN users u ON bsr.user_id = u.id
        WHERE bsr.share_id = ?
        ORDER BY bsr.created_at DESC
    ''', (share_id,)).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'records': [dict(r) for r in records]
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>/records/<int:target_user_id>', methods=['DELETE'])
@auth_required
def remove_share_record(bank_id, share_id, target_user_id):
    """移除特定用户的访问权限"""
    user_id = current_user_id()
    conn = get_db()

    share = conn.execute(
        'SELECT id FROM bank_shares WHERE id = ? AND bank_id = ? AND owner_id = ?',
        (share_id, bank_id, user_id)
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    conn.execute(
        'UPDATE bank_share_records SET status = 0 WHERE share_id = ? AND user_id = ?',
        (share_id, target_user_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '已移除该用户的访问权限'})
