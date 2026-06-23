# -*- coding: utf-8 -*-
"""小程序我的题库详情页退出已加入题库约束。"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MY_BANKS_TS = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "my-banks-v2" / "my-banks-v2.ts"
BANK_JOIN_TS = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "bank-join" / "bank-join.ts"
BANK_DETAIL_TS = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "bank-detail" / "bank-detail.ts"
BANK_DETAIL_WXML = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "bank-detail" / "bank-detail.wxml"
API_ENDPOINTS_TS = ROOT / "miniprogram-1" / "miniprogram" / "utils" / "api-endpoints.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_my_banks_joined_detail_entry_carries_leave_context():
    """进入加入题库详情时，应携带来源，避免公开题库误显示退出。"""
    page_ts = _read(MY_BANKS_TS)
    join_ts = _read(BANK_JOIN_TS)

    assert "source_type=${encodeURIComponent(sourceType)}" in page_ts
    assert "source=${encodeURIComponent(source)}" in page_ts
    assert "relation=${encodeURIComponent(relation)}" in page_ts
    assert "&source=${source}&relation=${source}" in join_ts
    assert "joinedBankDetailUrl(bankId, 'public')" in join_ts
    assert "joinedBankDetailUrl(bankId, 'shared')" in join_ts


def test_bank_detail_supports_leaving_joined_user_bank():
    """加入的用户题库详情页应在设置页显示退出按钮，并调用 Web 同款退出接口。"""
    detail_ts = _read(BANK_DETAIL_TS)
    detail_wxml = _read(BANK_DETAIL_WXML)
    api_ts = _read(API_ENDPOINTS_TS)

    assert "leavePublicBank" in api_ts
    assert "showLeaveBankAction" in detail_ts
    assert "showSettingsTab = showLeaveBankAction" in detail_ts
    assert "leavingBank" in detail_ts
    assert "onLeaveJoinedBank" in detail_ts
    assert "api.leavePublicBank('user', bankId)" in detail_ts
    assert "确定要退出该题库吗？退出后会从“我的题库”中移除。" in detail_ts
    assert "tab === 'settings'" in detail_wxml
    assert '<text class="card-title">设置</text>' in detail_wxml
    assert "退出题库" in detail_wxml
    assert "bindtap=\"onLeaveJoinedBank\"" in detail_wxml
    assert "wx:if=\"{{showLeaveBankAction}}\"" in detail_wxml
    assert "actions-with-leave" not in detail_wxml


def test_joined_bank_detail_no_longer_shows_non_owner_share_page():
    """非创建者加入的题库不应再保留“分享/让好友加入”的详情页。"""
    helper_ts = _read(ROOT / "miniprogram-1" / "miniprogram" / "pages" / "bank-detail" / "modules" / "bank-detail-helpers.ts")
    detail_ts = _read(BANK_DETAIL_TS)
    detail_wxml = _read(BANK_DETAIL_WXML)

    assert "showShareTab: boolean = true" in helper_ts
    assert "showSettingsTab: boolean = false" in helper_ts
    assert "settings: '设置'" in helper_ts
    assert "key === 'share'" in helper_ts
    assert "key === 'settings'" in helper_ts
    assert "showShareTab = canManageShare" in detail_ts
    assert "你当前不是创建者，无法创建或撤销分享。" not in detail_wxml
    assert '<text class="card-title">让好友加入</text>' not in detail_wxml
