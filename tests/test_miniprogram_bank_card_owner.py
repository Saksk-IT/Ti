# -*- coding: utf-8 -*-
"""小程序题库卡片作者信息渲染约束。"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from sqlalchemy import text

from app.core.extensions import db


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BANK_DIR = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "public-bank-v2"
MY_BANKS_DIR = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "my-banks-v2"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_bank_cards_render_owner_name_and_avatar():
    """题库广场卡片底部应显示真实作者昵称头像，且不再显示“用户”类型标签。"""
    ts = _read(PUBLIC_BANK_DIR / "public-bank-v2.ts")
    wxml = _read(PUBLIC_BANK_DIR / "public-bank-v2.wxml")
    owner_block = re.search(r'<view class="pb-owner"[\s\S]+?</view>', wxml)

    assert "return `${y}-${m}`" in ts
    assert "owner_avatar_url" in ts
    assert "resolveUploadUrl(b?.owner_avatar)" in ts
    assert owner_block is not None
    assert "{{item.owner_avatar_url}}" in owner_block.group(0)
    assert "{{item.owner_label}}" in owner_block.group(0)
    assert '<text>{{item.type_label}}</text>' not in wxml
    assert '<text class="mini-cover-sub">{{item.type_label}}</text>' not in wxml
    assert "用户分享" not in wxml


def test_my_bank_cards_render_owner_name_and_avatar():
    """个人题库卡片底部应显示创建者或分享者昵称头像，且日期只到月份。"""
    ts = _read(MY_BANKS_DIR / "my-banks-v2.ts")
    wxml = _read(MY_BANKS_DIR / "my-banks-v2.wxml")
    owner_block = re.search(r'<view class="mb-owner"[\s\S]+?</view>', wxml)

    assert "return `${y}-${m}`" in ts
    assert "owner_avatar_url" in ts
    assert "resolveUploadUrl(b?.owner_avatar)" in ts
    assert "owner_label" in ts
    assert owner_block is not None
    assert "{{item.owner_avatar_url}}" in owner_block.group(0)
    assert "{{item.owner_label}}" in owner_block.group(0)
    assert "<text>用户</text>" not in wxml


def test_my_created_bank_api_returns_owner_name_and_avatar(app, auth_client, seed_user):
    """我的题库接口应为小程序创建题库卡片提供作者昵称和头像。"""
    suffix = uuid.uuid4().hex[:8]
    bank_name = f"小程序作者信息题库-{suffix}"
    owner_avatar = f"/uploads/avatars/miniprogram_owner_{suffix}.png"
    bank_id = None
    old_avatar = None

    try:
        with app.app_context():
            old_avatar = db.session.execute(
                text("SELECT avatar FROM users WHERE id = :user_id"),
                {"user_id": int(seed_user["id"])},
            ).scalar_one_or_none()
            db.session.execute(
                text("UPDATE users SET avatar = :avatar WHERE id = :user_id"),
                {"avatar": owner_avatar, "user_id": int(seed_user["id"])},
            )
            bank_id = db.session.execute(
                text(
                    """
                    INSERT INTO user_question_banks (user_id, name, status, question_count)
                    VALUES (:user_id, :name, 1, 2)
                    RETURNING id
                    """
                ),
                {"user_id": int(seed_user["id"]), "name": bank_name},
            ).scalar_one()
            db.session.commit()

        response = auth_client.get("/user/banks/api/list")

        assert response.status_code == 200
        banks = response.get_json()["data"]["banks"]
        item = next(bank for bank in banks if int(bank["id"]) == int(bank_id))
        assert item["owner_nickname"] == seed_user["username"]
        assert item["owner_avatar"] == owner_avatar
    finally:
        with app.app_context():
            if bank_id is not None:
                db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
            db.session.execute(
                text("UPDATE users SET avatar = :avatar WHERE id = :user_id"),
                {"avatar": old_avatar, "user_id": int(seed_user["id"])},
            )
            db.session.commit()
