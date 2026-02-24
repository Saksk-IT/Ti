# -*- coding: utf-8 -*-

"""用户题库：分享/加入/授权 API"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from flask import request, jsonify, current_app
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.time_utils import now_bj

from .api_base import user_bank_api_bp, check_bank_access, generate_share_code


def _share_is_expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        return datetime.fromisoformat(str(expires_at)) < now_bj()
    except Exception:
        # 若时间格式异常，保守处理为已过期
        return True


@user_bank_api_bp.route('/<int:bank_id>/shares', methods=['GET'])
@auth_required
def get_shares(bank_id):
    """获取分享列表"""
    user_id = current_user_id()

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bank_id AND user_id = :uid AND status = 1'),
        {'bank_id': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    shares = db.session.execute(
        text('SELECT * FROM bank_shares WHERE bank_id = :bank_id ORDER BY created_at DESC'),
        {'bank_id': bank_id}
    ).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'shares': [dict(s._mapping) for s in shares]
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/usage-stats', methods=['GET'])
@auth_required
def get_bank_usage_stats(bank_id):
    """题库使用人数（仅创建者可看）

    口径（与需求 4B 对齐）：
    - 所有者（1） + 有效分享用户（bank_share_records） + 公开使用用户（public_bank_users）
    - total_users 为去重后的唯一用户数
    """
    user_id = current_user_id()

    bank = db.session.execute(
        text('SELECT id, user_id, is_public, status FROM user_question_banks WHERE id = :bank_id'),
        {'bank_id': int(bank_id)},
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或已被删除'}), 404

    bank = dict(bank._mapping)
    if int(bank.get('status') or 0) != 1:
        return jsonify({'code': 1, 'message': '题库不存在或已被删除'}), 404

    uid_int = 0
    if user_id is not None:
        try:
            uid_int = int(user_id)
        except Exception:
            uid_int = 0
    owner_id = int(bank.get('user_id') or 0)
    if uid_int <= 0 or owner_id <= 0 or uid_int != owner_id:
        return jsonify({'code': 403, 'message': '无权查看（仅创建者可见）'}), 403

    # 有效分享用户（排除已撤销/过期的 share）
    shared_user_ids = set()
    try:
        rows = db.session.execute(text('''
            SELECT DISTINCT bsr.user_id as user_id, bs.expires_at as expires_at
            FROM bank_share_records bsr
            JOIN bank_shares bs ON bsr.share_id = bs.id
            WHERE bsr.bank_id = :bank_id AND bsr.status = 1 AND bs.is_active = true
        '''), {'bank_id': int(bank_id)}).fetchall()
        for r in rows or []:
            if not r:
                continue
            expires_at = r._mapping['expires_at']
            if _share_is_expired(expires_at):
                continue
            try:
                shared_user_ids.add(int(r._mapping['user_id'] or 0))
            except Exception:
                continue
    except Exception:
        shared_user_ids = set()

    # 公开使用用户（有访问记录的人）
    public_user_ids = set()
    try:
        rows = db.session.execute(
            text('SELECT DISTINCT user_id FROM public_bank_users WHERE bank_id = :bank_id'),
            {'bank_id': int(bank_id)},
        ).fetchall()
        for r in rows or []:
            if not r:
                continue
            try:
                public_user_ids.add(int(r._mapping['user_id'] or 0))
            except Exception:
                continue
    except Exception:
        public_user_ids = set()

    # total 去重
    all_ids = set([owner_id])
    all_ids.update([i for i in shared_user_ids if i])
    all_ids.update([i for i in public_user_ids if i])

    shared_ex_owner = set([i for i in shared_user_ids if i and i != owner_id])
    public_ex_owner = set([i for i in public_user_ids if i and i != owner_id])
    total_ex_owner = set([i for i in all_ids if i and i != owner_id])

    return jsonify({
        'code': 0,
        'data': {
            'bank_id': int(bank_id),
            'is_public': bool(bank.get('is_public')),
            'owner_id': owner_id,
            'owner_count': 1,
            'shared_users': len(shared_ex_owner),
            'public_users': len(public_ex_owner),
            'total_users': len(all_ids),
            'total_users_excluding_owner': len(total_ex_owner),
        }
    })


@user_bank_api_bp.route('/shares/all', methods=['GET'])
@auth_required
def get_all_shares():
    """获取我创建的所有分享（跨题库汇总）"""
    user_id = current_user_id()

    rows = db.session.execute(text('''
        SELECT bs.*,
               b.name as bank_name
        FROM bank_shares bs
        JOIN user_question_banks b ON bs.bank_id = b.id
        WHERE bs.owner_id = :uid AND b.status = 1
        ORDER BY bs.created_at DESC
    '''), {'uid': user_id}).fetchall()

    base_url = current_app.config.get('SHARE_BASE_URL', request.host_url.rstrip('/'))
    shares = []
    for r in rows:
        d = dict(r._mapping)
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
    permission = data.get('permission', 'read')
    expires_in = data.get('expires_in')  # 有效天数
    max_uses = data.get('max_uses')

    if permission not in ('read', 'copy'):
        return jsonify({'code': 1, 'message': '无效的权限级别'}), 400

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bank_id AND user_id = :uid AND status = 1'),
        {'bank_id': bank_id, 'uid': user_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 检查分享数量限制
    share_count = db.session.execute(
        text('SELECT COUNT(*) as cnt FROM bank_shares WHERE bank_id = :bank_id AND is_active = true'),
        {'bank_id': bank_id}
    ).fetchone()._mapping['cnt']

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
            existing = db.session.execute(
                text('SELECT id FROM bank_shares WHERE share_code = :code'), {'code': share_code}
            ).fetchone()
            if not existing:
                break
    else:
        share_token = str(uuid.uuid4()).replace('-', '')

    cursor = db.session.execute(text('''
        INSERT INTO bank_shares (bank_id, owner_id, share_code, share_token, permission, expires_at, max_uses)
        VALUES (:bank_id, :uid, :share_code, :share_token, :permission, :expires_at, :max_uses)
        RETURNING id
    '''), {
        'bank_id': bank_id, 'uid': user_id, 'share_code': share_code,
        'share_token': share_token, 'permission': permission,
        'expires_at': expires_at, 'max_uses': max_uses,
    })
    new_share_id = cursor.fetchone()._mapping['id']

    # 更新分享数量
    db.session.execute(
        text('UPDATE user_question_banks SET share_count = share_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = :bank_id'),
        {'bank_id': bank_id}
    )
    db.session.commit()

    result = {
        'share_id': new_share_id,
        'expires_at': expires_at
    }

    if share_code:
        result['share_code'] = share_code
    if share_token:
        # 小程序名片分享需要 token（便于拼接 path），同时保留 share_link 兼容 Web
        result['share_token'] = share_token
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

    share = db.session.execute(
        text('SELECT id FROM bank_shares WHERE id = :sid AND bank_id = :bank_id AND owner_id = :uid'),
        {'sid': share_id, 'bank_id': bank_id, 'uid': user_id}
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    db.session.execute(text('UPDATE bank_shares SET is_active = false WHERE id = :sid'), {'sid': share_id})
    db.session.commit()

    return jsonify({'code': 0, 'message': '分享已撤销'})


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>/records', methods=['GET'])
@auth_required
def get_share_records(bank_id, share_id):
    """查看分享使用记录"""
    user_id = current_user_id()

    share = db.session.execute(
        text('SELECT id FROM bank_shares WHERE id = :sid AND bank_id = :bank_id AND owner_id = :uid'),
        {'sid': share_id, 'bank_id': bank_id, 'uid': user_id}
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    records = db.session.execute(text('''
        SELECT bsr.*, u.username as nickname, u.avatar
        FROM bank_share_records bsr
        JOIN users u ON bsr.user_id = u.id
        WHERE bsr.share_id = :sid
        ORDER BY bsr.created_at DESC
    '''), {'sid': share_id}).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'records': [dict(r._mapping) for r in records]
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>/records/<int:target_user_id>', methods=['DELETE'])
@auth_required
def remove_share_record(bank_id, share_id, target_user_id):
    """移除特定用户的访问权限"""
    user_id = current_user_id()

    share = db.session.execute(
        text('SELECT id FROM bank_shares WHERE id = :sid AND bank_id = :bank_id AND owner_id = :uid'),
        {'sid': share_id, 'bank_id': bank_id, 'uid': user_id}
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    db.session.execute(
        text('UPDATE bank_share_records SET status = 0 WHERE share_id = :sid AND user_id = :target_uid'),
        {'sid': share_id, 'target_uid': target_user_id}
    )
    db.session.commit()

    return jsonify({'code': 0, 'message': '已移除该用户的访问权限'})


@user_bank_api_bp.route('/join/preview', methods=['GET'])
@auth_required
def preview_join_bank():
    """预览通过分享码/链接加入题库（不写入记录）"""
    user_id = current_user_id()
    share_code = (request.args.get('share_code') or '').strip().upper()
    share_token = (request.args.get('token') or '').strip()

    if not share_code and not share_token:
        return jsonify({'code': 1, 'message': '请提供分享码或分享链接'}), 400

    if share_code:
        share = db.session.execute(
            text('SELECT * FROM bank_shares WHERE share_code = :code AND is_active = true'),
            {'code': share_code}
        ).fetchone()
    else:
        share = db.session.execute(
            text('SELECT * FROM bank_shares WHERE share_token = :token AND is_active = true'),
            {'token': share_token}
        ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享码/链接无效或已过期'}), 404

    share = dict(share._mapping)

    # 过期/次数校验（与 join 保持一致）
    if _share_is_expired(share.get('expires_at')):
        return jsonify({'code': 1, 'message': '分享已过期'}), 400
    if share.get('max_uses') and int(share.get('current_uses') or 0) >= int(share.get('max_uses') or 0):
        return jsonify({'code': 1, 'message': '分享已达到最大使用次数'}), 400

    bank_id = int(share['bank_id'])
    bank = db.session.execute(
        text('SELECT b.*, u.username as owner_username FROM user_question_banks b JOIN users u ON b.user_id = u.id WHERE b.id = :bank_id AND b.status = 1'),
        {'bank_id': bank_id},
    ).fetchone()
    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或已被删除'}), 404

    bank = dict(bank._mapping)

    has_access, permission, access_type = check_bank_access(user_id, bank_id)
    uid_int = 0
    if user_id is not None:
        try:
            uid_int = int(user_id)
        except Exception:
            uid_int = 0
    is_owner = int(bank['user_id']) == uid_int

    # 预期加入后权限：以分享权限为准
    join_permission = share.get('permission') or 'read'
    current_permission = permission if has_access else join_permission
    current_access_type = access_type if has_access else 'share'

    return jsonify({
        'code': 0,
        'data': {
            'bank_id': bank_id,
            'bank_name': bank.get('name') or '',
            'owner_id': int(bank['user_id']),
            'owner_nickname': bank.get('owner_username') or '',
            'question_count': int(bank.get('question_count') or 0),
            'join_permission': join_permission,
            'has_access': bool(has_access),
            'permission': current_permission,
            'access_type': current_access_type,
            'is_owner': bool(is_owner),
            'share_id': int(share['id']),
            'expires_at': share.get('expires_at'),
            'max_uses': share.get('max_uses'),
            'current_uses': int(share.get('current_uses') or 0),
        }
    })


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

    if share_code:
        share = db.session.execute(
            text('SELECT * FROM bank_shares WHERE share_code = :code AND is_active = true'),
            {'code': share_code}
        ).fetchone()
    else:
        share = db.session.execute(
            text('SELECT * FROM bank_shares WHERE share_token = :token AND is_active = true'),
            {'token': share_token}
        ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享码/链接无效或已过期'}), 404

    share = dict(share._mapping)

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
    bank = db.session.execute(
        text('SELECT b.*, u.username as owner_username FROM user_question_banks b JOIN users u ON b.user_id = u.id WHERE b.id = :bank_id AND b.status = 1'),
        {'bank_id': bank_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或已被删除'}), 404

    bank = dict(bank._mapping)

    # 检查是否已加入
    existing = db.session.execute(
        text('SELECT id, status FROM bank_share_records WHERE share_id = :sid AND user_id = :uid'),
        {'sid': share['id'], 'uid': user_id}
    ).fetchone()

    if existing:
        existing = dict(existing._mapping)
        if existing['status'] == 1:
            return jsonify({'code': 1, 'message': '您已加入此题库'}), 400
        else:
            # 重新激活
            db.session.execute(
                text('UPDATE bank_share_records SET status = 1, last_access_at = CURRENT_TIMESTAMP WHERE id = :rid'),
                {'rid': existing['id']}
            )
    else:
        db.session.execute(text('''
            INSERT INTO bank_share_records (share_id, bank_id, user_id, last_access_at)
            VALUES (:sid, :bank_id, :uid, CURRENT_TIMESTAMP)
        '''), {'sid': share['id'], 'bank_id': bank_id, 'uid': user_id})

        # 更新使用次数
        db.session.execute(
            text('UPDATE bank_shares SET current_uses = current_uses + 1 WHERE id = :sid'),
            {'sid': share['id']}
        )

    db.session.commit()

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

    banks = db.session.execute(text('''
        SELECT b.id as bank_id, b.name as bank_name, b.question_count,
               bs.permission, bsr.last_access_at, bsr.access_count,
               u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar
        FROM bank_share_records bsr
        JOIN bank_shares bs ON bsr.share_id = bs.id
        JOIN user_question_banks b ON bsr.bank_id = b.id
        JOIN users u ON b.user_id = u.id
        WHERE bsr.user_id = :uid AND bsr.status = 1 AND b.status = 1 AND bs.is_active = true
        ORDER BY bsr.last_access_at DESC
    '''), {'uid': user_id}).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'banks': [dict(b._mapping) for b in banks]
        }
    })


@user_bank_api_bp.route('/shared/<int:bank_id>', methods=['DELETE'])
@auth_required
def remove_shared_bank(bank_id):
    """移除收到的分享"""
    user_id = current_user_id()

    db.session.execute(text('''
        UPDATE bank_share_records SET status = 0
        WHERE user_id = :uid AND bank_id = :bank_id
    '''), {'uid': user_id, 'bank_id': bank_id})
    db.session.commit()

    return jsonify({'code': 0, 'message': '已移除'})
