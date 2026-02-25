# -*- coding: utf-8 -*-
"""公开题库广场路由"""
from typing import Optional

from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import text

from app.core.extensions import db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.jwt_utils import decode_jwt_token
from app.core.utils.decorators import _validate_jwt_user
from app.core.utils.time_utils import now_bj

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

    all_banks = []

    # 1. 获取用户公开题库
    if bank_type != 'system':
        user_query = '''
            SELECT b.id, b.name, b.public_description as description, COALESCE(b.question_count, 0) as question_count,
                   b.public_use_count as use_count, 0 as allow_copy, b.public_at, b.created_at,
                   u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar,
                   'user' as bank_type
            FROM user_question_banks b
            JOIN users u ON b.user_id = u.id
            WHERE b.is_public = true AND b.status = 1
        '''
        user_params: dict = {}

        if keyword:
            user_query += ' AND (b.name LIKE :kw1 OR b.public_description LIKE :kw2)'
            user_params['kw1'] = f'%{keyword}%'
            user_params['kw2'] = f'%{keyword}%'

        user_rows = db.session.execute(text(user_query), user_params).fetchall()
        public_user_banks = []
        for b in (user_rows or []):
            d = dict(b._mapping)
            d['is_shared'] = 0
            public_user_banks.append(d)
        all_banks.extend(public_user_banks)
        # 1.1 收到的分享题库也展示在「题库广场」：
        # - 类型仍按「用户」归类
        # - 卡面显示「用户分享」标签
        # - 仅对当前登录用户可见（无 token/session 时不返回）
        if uid:
            shared_query = '''
                SELECT b.id, b.name,
                       COALESCE(NULLIF(b.public_description, ''), b.description) as description,
                       COALESCE(b.question_count, 0) as question_count,
                       0 as use_count,
                       0 as allow_copy,
                       bsr.created_at as public_at,
                       b.created_at,
                       u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar,
                       'user' as bank_type,
                       1 as is_shared
                FROM bank_share_records bsr
                JOIN bank_shares bs ON bsr.share_id = bs.id
                JOIN user_question_banks b ON bsr.bank_id = b.id
                JOIN users u ON b.user_id = u.id
                WHERE bsr.user_id = :uid
                  AND bsr.status = 1
                  AND b.status = 1
                  AND bs.is_active = true
                  AND (bs.expires_at IS NULL OR replace(bs.expires_at::text, 'T', ' ') > :now_bj)
            '''
            shared_params: dict = {'uid': int(uid), 'now_bj': str(now_bj())}
            if keyword:
                shared_query += ' AND (b.name LIKE :skw1 OR b.public_description LIKE :skw2 OR b.description LIKE :skw3)'
                shared_params['skw1'] = f'%{keyword}%'
                shared_params['skw2'] = f'%{keyword}%'
                shared_params['skw3'] = f'%{keyword}%'
            shared_rows = db.session.execute(text(shared_query), shared_params).fetchall()
            all_banks.extend([dict(b._mapping) for b in (shared_rows or [])])

    # 2. 获取管理员公共题库（subjects表）
    if bank_type != 'user':
        from app.core.utils.subject_permissions import get_user_accessible_subjects

        system_params: dict = {}
        subject_ids = []
        if uid:
            try:
                subject_ids = [int(x) for x in (get_user_accessible_subjects(int(uid)) or []) if x is not None]
            except Exception:
                subject_ids = []
            if not subject_ids:
                system_banks = []
                system_rows = []
            else:
                in_clause, in_params = _build_named_in('sid', subject_ids)
                system_params.update(in_params)
                system_rows = db.session.execute(
                    text(f"""
                    SELECT s.id, s.name, s.description, s.created_at as public_at, s.created_at as created_at,
                           (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                           0 as allow_copy, 0 as use_count,
                           NULL as owner_id, '系统管理员' as owner_nickname, NULL as owner_avatar,
                           'system' as bank_type
                    FROM subjects s
                    WHERE s.id IN ({in_clause})
                      AND (s.is_locked = false OR s.is_locked IS NULL)
                    """),
                    system_params,
                ).fetchall()
        else:
            system_rows = db.session.execute(
                text("""
                SELECT s.id, s.name, s.description, s.created_at as public_at, s.created_at as created_at,
                       (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                       0 as allow_copy, 0 as use_count,
                       NULL as owner_id, '系统管理员' as owner_nickname, NULL as owner_avatar,
                       'system' as bank_type
                FROM subjects s
                WHERE (s.is_locked = false OR s.is_locked IS NULL)
                """)
            ).fetchall()

        system_banks = [dict(b._mapping) for b in (system_rows or [])]

        if keyword and system_banks:
            kw = keyword.lower()
            system_banks = [
                b
                for b in system_banks
                if kw in str(b.get('name') or '').lower()
                or kw in str(b.get('description') or '').lower()
            ]

        all_banks.extend(system_banks)

    # 排序（public_at 是 datetime 对象，fallback 用 datetime.min 避免类型混合比较）
    from datetime import datetime as _dt
    _epoch = _dt.min
    if sort == 'popular':
        all_banks.sort(key=lambda x: (x.get('use_count') or 0, x.get('public_at') or _epoch), reverse=True)
    elif sort == 'questions':
        all_banks.sort(key=lambda x: (x.get('question_count') or 0, x.get('public_at') or _epoch), reverse=True)
    else:  # newest
        all_banks.sort(key=lambda x: x.get('public_at') or _epoch, reverse=True)

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

    if bank_type == 'system':
        # 查询系统公共题库（subjects表）
        bank = db.session.execute(text('''
            SELECT s.id, s.name, s.description,
                   (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                   0 as allow_copy, 0 as use_count,
                   '系统管理员' as owner_nickname, NULL as owner_avatar,
                   'system' as bank_type
            FROM subjects s
            WHERE s.id = :bid
        '''), {'bid': bank_id}).fetchone()

        if not bank:
            return jsonify({'code': 1, 'message': '题库不存在'}), 404
    else:
        # 查询用户公开题库
        bank = db.session.execute(text('''
            SELECT b.id, b.name, b.public_description as description, b.question_count,
                   b.public_use_count as use_count, 0 as allow_copy,
                   u.username as owner_nickname, u.avatar as owner_avatar,
                   'user' as bank_type
            FROM user_question_banks b
            JOIN users u ON b.user_id = u.id
            WHERE b.id = :bid AND b.is_public = true AND b.status = 1
        '''), {'bid': bank_id}).fetchone()

        if not bank:
            return jsonify({'code': 1, 'message': '题库不存在或未公开'}), 404

    return jsonify({
        'code': 0,
        'data': dict(bank._mapping)
    })


@public_bank_bp.route('/api/public/banks/<int:bank_id>/join', methods=['POST'])
@auth_required
def join_public_bank(bank_id):
    """加入公开题库刷题"""
    user_id = current_user_id()

    bank = db.session.execute(
        text('SELECT id FROM user_question_banks WHERE id = :bid AND is_public = true AND status = 1'),
        {'bid': bank_id}
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或未公开'}), 404

    # 记录使用
    existing = db.session.execute(
        text('SELECT id FROM public_bank_users WHERE bank_id = :bid AND user_id = :uid'),
        {'bid': bank_id, 'uid': user_id}
    ).fetchone()

    if not existing:
        db.session.execute(text('''
            INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
            VALUES (:bid, :uid, CURRENT_TIMESTAMP, 1)
        '''), {'bid': bank_id, 'uid': user_id})
        db.session.execute(
            text('UPDATE user_question_banks SET public_use_count = public_use_count + 1 WHERE id = :bid'),
            {'bid': bank_id}
        )
        db.session.commit()

    return jsonify({'code': 0, 'message': '已加入'})


@public_bank_bp.route('/bank/join')
def join_bank_page():
    """分享链接跳转页面"""
    token = request.args.get('token', '')
    return render_template('user_bank/share/join.html', token=token)


def _build_named_in(prefix: str, values: list) -> tuple[str, dict]:
    """构建命名参数 IN 子句，返回 (placeholder_str, params_dict)"""
    if not values:
        return 'NULL', {}
    params = {}
    names = []
    for i, v in enumerate(values):
        key = f"{prefix}_{i}"
        params[key] = v
        names.append(f":{key}")
    return ", ".join(names), params
