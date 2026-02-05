# -*- coding: utf-8 -*-
"""公开题库广场路由"""
from typing import Optional

from flask import Blueprint, render_template, request, jsonify, session
from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.jwt_utils import decode_jwt_token
from app.core.utils.decorators import _validate_jwt_user
from app.core.utils.time_utils import SQLITE_BJ_NOW_EXPR

public_bank_bp = Blueprint('public_bank', __name__)


@public_bank_bp.route('/public/banks')
def bank_plaza():
    """题库广场页面（系统题库 + 用户公开题库）"""
    uid = session.get('user_id')
    return render_template(
        'user_bank/public/plaza.html',
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


def _optional_user_id() -> Optional[int]:
    """尝试从 JWT / Session 获取用户ID（不强制登录）。"""
    # 1) JWT（小程序）
    token = request.headers.get('Authorization') or request.headers.get('authorization')
    if token:
        raw_token = str(token).strip()
        if raw_token.startswith('Bearer '):
            raw_token = raw_token[7:].strip()
        payload = None
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
                    return uid if uid > 0 else None
                except Exception:
                    return None

    # 2) Session（Web）
    try:
        uid = int(session.get('user_id') or 0)
        return uid if uid > 0 else None
    except Exception:
        return None


@public_bank_bp.route('/api/public/banks', methods=['GET'])
def get_public_banks():
    """获取公开题库列表（包含用户公开题库和管理员公共题库）"""
    uid = _optional_user_id()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort = request.args.get('sort', 'newest')  # newest, popular, questions
    keyword = request.args.get('keyword', '').strip()
    bank_type = request.args.get('type', '')  # all, user, system

    conn = get_db()
    all_banks = []

    # 1. 获取用户公开题库
    if bank_type != 'system':
        user_query = '''
            SELECT b.id, b.name, b.public_description as description, COALESCE(b.question_count, 0) as question_count,
                   b.public_use_count as use_count, b.allow_copy, b.public_at, b.created_at,
                   u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar,
                   'user' as bank_type
            FROM user_question_banks b
            JOIN users u ON b.user_id = u.id
            WHERE b.is_public = 1 AND b.status = 1
        '''
        user_params = []

        if keyword:
            user_query += ' AND (b.name LIKE ? OR b.public_description LIKE ?)'
            user_params.extend([f'%{keyword}%', f'%{keyword}%'])

        user_rows = conn.execute(user_query, user_params).fetchall()
        public_user_banks = []
        for b in (user_rows or []):
            d = dict(b)
            d['is_shared'] = 0
            public_user_banks.append(d)
        all_banks.extend(public_user_banks)

        # 1.1 鏀跺埌鐨勫垎浜搴撲篃灞曠ず鍦ㄣ€岄搴撳箍鍦恒€嶏細
        # - 绫诲瀷浠?「鐢ㄦ埛」褰掔被
        # - 鍗￠潰鏄剧ず「鐢ㄦ埛鍒嗕韩」鏍囩
        # - 浠呭褰撳墠鐧诲綍鐢ㄦ埛鍙锛堟棤 token/session 鏃朵笉杩斿洖锛?
        if uid:
            shared_query = f'''
                SELECT b.id, b.name,
                       COALESCE(NULLIF(b.public_description, ''), b.description) as description,
                       COALESCE(b.question_count, 0) as question_count,
                       0 as use_count,
                       CASE WHEN bs.permission = 'copy' THEN 1 ELSE 0 END as allow_copy,
                       bsr.created_at as public_at,
                       b.created_at,
                       u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar,
                       'user' as bank_type,
                       1 as is_shared
                FROM bank_share_records bsr
                JOIN bank_shares bs ON bsr.share_id = bs.id
                JOIN user_question_banks b ON bsr.bank_id = b.id
                JOIN users u ON b.user_id = u.id
                WHERE bsr.user_id = ?
                  AND bsr.status = 1
                  AND b.status = 1
                  AND bs.is_active = 1
                  AND (bs.expires_at IS NULL OR replace(bs.expires_at, 'T', ' ') > {SQLITE_BJ_NOW_EXPR})
            '''
            shared_params = [int(uid)]
            if keyword:
                shared_query += ' AND (b.name LIKE ? OR b.public_description LIKE ? OR b.description LIKE ?)'
                shared_params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
            shared_rows = conn.execute(shared_query, shared_params).fetchall()
            all_banks.extend([dict(b) for b in (shared_rows or [])])

    # 2. 获取管理员公共题库（subjects表）
    if bank_type != 'user':
        from app.core.utils.subject_permissions import get_user_accessible_subjects

        system_params = []
        subject_ids = []
        if uid:
            try:
                subject_ids = [int(x) for x in (get_user_accessible_subjects(int(uid)) or []) if x is not None]
            except Exception:
                subject_ids = []
            if not subject_ids:
                system_banks = []
                # 仍允许后续逻辑继续处理 user_banks
                system_rows = []
            else:
                placeholders = ",".join(["?"] * len(subject_ids))
                system_params.extend(subject_ids)
                system_rows = conn.execute(
                    f"""
                    SELECT s.id, s.name, s.description, s.created_at as public_at, s.created_at as created_at,
                           (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                           1 as allow_copy, 0 as use_count,
                           NULL as owner_id, '系统管理员' as owner_nickname, NULL as owner_avatar,
                           'system' as bank_type
                    FROM subjects s
                    WHERE s.id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    system_params,
                ).fetchall()
        else:
            system_rows = conn.execute(
                """
                SELECT s.id, s.name, s.description, s.created_at as public_at, s.created_at as created_at,
                       (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                       1 as allow_copy, 0 as use_count,
                       NULL as owner_id, '系统管理员' as owner_nickname, NULL as owner_avatar,
                       'system' as bank_type
                FROM subjects s
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                """
            ).fetchall()

        system_banks = [dict(b) for b in (system_rows or [])]

        if keyword and system_banks:
            kw = keyword.lower()
            system_banks = [
                b
                for b in system_banks
                if kw in str(b.get('name') or '').lower()
                or kw in str(b.get('description') or '').lower()
            ]

        all_banks.extend(system_banks)

    # 排序
    if sort == 'popular':
        all_banks.sort(key=lambda x: (x.get('use_count') or 0, x.get('public_at') or ''), reverse=True)
    elif sort == 'questions':
        all_banks.sort(key=lambda x: (x.get('question_count') or 0, x.get('public_at') or ''), reverse=True)
    else:  # newest
        all_banks.sort(key=lambda x: x.get('public_at') or '', reverse=True)

    # 分页
    total = len(all_banks)
    start = (page - 1) * per_page
    end = start + per_page
    paged_banks = all_banks[start:end]

    return jsonify({
        'code': 0,
        'data': {
            'banks': paged_banks,
            'total': total,
            'page': page
        }
    })


@public_bank_bp.route('/api/public/banks/<int:bank_id>', methods=['GET'])
def get_public_bank_detail(bank_id):
    """获取公开题库详情"""
    bank_type = request.args.get('type', 'user')  # user or system
    conn = get_db()

    if bank_type == 'system':
        # 查询系统公共题库（subjects表）
        bank = conn.execute('''
            SELECT s.id, s.name, s.description,
                   (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                   1 as allow_copy, 0 as use_count,
                   '系统管理员' as owner_nickname, NULL as owner_avatar,
                   'system' as bank_type
            FROM subjects s
            WHERE s.id = ?
        ''', (bank_id,)).fetchone()

        if not bank:
            return jsonify({'code': 1, 'message': '题库不存在'}), 404
    else:
        # 查询用户公开题库
        bank = conn.execute('''
            SELECT b.id, b.name, b.public_description as description, b.question_count,
                   b.public_use_count as use_count, b.allow_copy,
                   u.username as owner_nickname, u.avatar as owner_avatar,
                   'user' as bank_type
            FROM user_question_banks b
            JOIN users u ON b.user_id = u.id
            WHERE b.id = ? AND b.is_public = 1 AND b.status = 1
        ''', (bank_id,)).fetchone()

        if not bank:
            return jsonify({'code': 1, 'message': '题库不存在或未公开'}), 404

    return jsonify({
        'code': 0,
        'data': dict(bank)
    })


@public_bank_bp.route('/api/public/banks/<int:bank_id>/join', methods=['POST'])
@auth_required
def join_public_bank(bank_id):
    """加入公开题库刷题"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND is_public = 1 AND status = 1',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或未公开'}), 404

    # 记录使用
    existing = conn.execute(
        'SELECT id FROM public_bank_users WHERE bank_id = ? AND user_id = ?',
        (bank_id, user_id)
    ).fetchone()

    if not existing:
        conn.execute('''
            INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
            VALUES (?, ?, CURRENT_TIMESTAMP, 1)
        ''', (bank_id, user_id))
        conn.execute(
            'UPDATE user_question_banks SET public_use_count = public_use_count + 1 WHERE id = ?',
            (bank_id,)
        )
        conn.commit()

    return jsonify({'code': 0, 'message': '已加入'})


@public_bank_bp.route('/bank/join')
def join_bank_page():
    """分享链接跳转页面"""
    token = request.args.get('token', '')
    return render_template('user_bank/share/join.html', token=token)
