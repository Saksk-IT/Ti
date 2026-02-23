# -*- coding: utf-8 -*-
"""复盘中心 — 路由入口（拆分后保留向后兼容）。

子模块：
  review_center_helpers  — 共享辅助函数
  review_center_search   — 搜索 tab 数据加载
  review_center_data     — 数据 tab 统计逻辑
  review_center_core     — _review_center_page 主函数
"""

from flask import render_template, request, session

from app.core.utils.database import get_db
from app.core.utils.decorators import login_required

from .bp import main_pages_bp

# re-export：确保外部 import 路径不变
from .review_center_core import _review_center_page  # noqa: F401
from .review_center_helpers import (  # noqa: F401
    _build_preview,
    _load_bank_tag_ids,
    _load_public_tag_ids,
    _review_center_meta,
    _url_with_params,
)


@main_pages_bp.route('/favorites')
@login_required
def favorites_detail_page():
    """收藏：先选题库（公共题库 / 个人题库），再进入题库详情页。"""
    uid = session.get('user_id')
    conn = get_db()

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='favorites',
        entry_title='收藏',
        entry_subtitle='先选择题库，再进入收藏中心。',
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/review')
@login_required
def review_entry_page():
    """复盘：错题 / 收藏 / 标签统一入口，先选题库再进入对应中心。"""
    uid = session.get('user_id')
    conn = get_db()

    kind = (request.args.get('kind') or 'mistakes').strip().lower()
    if kind not in ('mistakes', 'favorites', 'tags'):
        kind = 'mistakes'
    kind_label_map = {'mistakes': '错题', 'favorites': '收藏', 'tags': '标签'}
    kind_label = kind_label_map.get(kind, '错题')

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='review',
        entry_title='复盘',
        entry_subtitle='错题 / 收藏 / 标签 统一入口：先选择题库，再开始复盘。',
        review_kind=kind,
        review_kind_label=kind_label,
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/mistakes')
@login_required
def mistakes_detail_page():
    """错题：先选题库（公共题库 / 个人题库），再进入题库详情页。"""
    uid = session.get('user_id')
    conn = get_db()

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='mistakes',
        entry_title='错题',
        entry_subtitle='先选择题库，再进入错题中心。',
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/tags')
@login_required
def tags_select_page():
    """标签：先选题库（公共题库 / 个人题库），再进入标签中心页。"""
    uid = session.get('user_id')
    conn = get_db()

    from app.core.utils.bank_select import load_bank_select_payload

    payload = load_bank_select_payload(conn, uid)

    return render_template(
        'main/bank/bank_select_entry.html',
        entry_key='tags',
        entry_title='标签',
        entry_subtitle='先选择题库，再进入标签中心。',
        public_cards=payload.get('public_cards') or [],
        bank_cards=payload.get('bank_cards') or [],
        public_total=payload.get('public_total') or 0,
        bank_total=payload.get('bank_total') or 0,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/mistakes/center')
@login_required
def mistakes_center_page():
    return _review_center_page('mistakes')


@main_pages_bp.route('/favorites/center')
@login_required
def favorites_center_page():
    return _review_center_page('favorites')


@main_pages_bp.route('/tags/center')
@login_required
def tags_center_page():
    return _review_center_page('tags')
