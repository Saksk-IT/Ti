# -*- coding: utf-8 -*-
"""首页与小程序我的页个人题库统计口径回归。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import text

from app.core.extensions import db


ROOT = Path(__file__).resolve().parents[1]
MINIPROGRAM_MINE_DIR = ROOT / "miniprogram-1" / "miniprogram" / "pages" / "mine"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _create_bank_stats(app, user_id: int) -> int:
    with app.app_context():
        bank_id = db.session.execute(
            text(
                """
                INSERT INTO user_question_banks (user_id, name, status, question_count)
                VALUES (:user_id, '首页个人题库统计回归', 1, 2)
                RETURNING id
                """
            ),
            {"user_id": int(user_id)},
        ).scalar_one()
        question_ids = []
        for index in range(1, 3):
            question_id = db.session.execute(
                text(
                    """
                    INSERT INTO user_bank_questions
                    (bank_id, user_id, type, content, options, answer, analysis, tags, difficulty, source_type, sort_order)
                    VALUES
                    (:bank_id, :user_id, 'single_choice', :content, :options, :answer, '', '[]', 1, 'custom', :sort_order)
                    RETURNING id
                    """
                ),
                {
                    "bank_id": int(bank_id),
                    "user_id": int(user_id),
                    "content": f"首页统计题目 {index}",
                    "options": json.dumps(["A", "B"], ensure_ascii=False),
                    "answer": json.dumps([0], ensure_ascii=False),
                    "sort_order": index,
                },
            ).scalar_one()
            question_ids.append(int(question_id))

        db.session.execute(
            text(
                """
                INSERT INTO user_bank_favorites (user_id, bank_id, question_id)
                VALUES (:user_id, :bank_id, :question_id)
                """
            ),
            {"user_id": int(user_id), "bank_id": int(bank_id), "question_id": question_ids[0]},
        )
        db.session.execute(
            text(
                """
                INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count)
                VALUES (:user_id, :bank_id, :question_id, 2)
                """
            ),
            {"user_id": int(user_id), "bank_id": int(bank_id), "question_id": question_ids[1]},
        )
        for index, question_id in enumerate(question_ids):
            db.session.execute(
                text(
                    """
                    INSERT INTO user_bank_answers (user_id, bank_id, question_id, user_answer, is_correct)
                    VALUES (:user_id, :bank_id, :question_id, :user_answer, :is_correct)
                    """
                ),
                {
                    "user_id": int(user_id),
                    "bank_id": int(bank_id),
                    "question_id": int(question_id),
                    "user_answer": "A",
                    "is_correct": index == 0,
                },
            )
        db.session.commit()
        return int(bank_id)


def _delete_bank_stats(app, bank_id: int) -> None:
    with app.app_context():
        db.session.execute(text("DELETE FROM user_bank_answers WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.execute(text("DELETE FROM user_bank_favorites WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.execute(text("DELETE FROM user_bank_mistakes WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.execute(text("DELETE FROM user_bank_questions WHERE bank_id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.execute(text("DELETE FROM user_question_banks WHERE id = :bank_id"), {"bank_id": int(bank_id)})
        db.session.commit()


def _hub_bento_value(html: str, label: str) -> str:
    match = re.search(
        rf'<span class="hub-bento-label">{re.escape(label)}</span>\s*'
        rf'<span class="hub-bento-value">([^<]+)</span>',
        html,
    )
    assert match is not None, f"未找到首页统计项：{label}"
    return match.group(1).strip()


def test_web_hub_uses_global_personal_bank_stats(app, auth_client, seed_user):
    """Web 首页统计应使用公共 + 个人题库口径，不能在仅有个人题库时显示为 0。"""
    bank_id = _create_bank_stats(app, seed_user["id"])
    try:
        response = auth_client.get("/hub")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert _hub_bento_value(html, "题目数") == "2"
        assert _hub_bento_value(html, "收藏") == "1"
        assert _hub_bento_value(html, "错题") == "1"
        assert _hub_bento_value(html, "正确率") == "50.0%"
    finally:
        _delete_bank_stats(app, bank_id)


def test_web_hub_daily_stats_api_uses_personal_bank_answers(app, auth_client, seed_user):
    """首页近 7 天图表接口应包含个人题库答题记录。"""
    bank_id = _create_bank_stats(app, seed_user["id"])
    try:
        response = auth_client.get("/api/stats/daily?days=7")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"

        total = sum(int(row.get("total") or 0) for row in payload["data"])
        correct = sum(int(row.get("correct") or 0) for row in payload["data"])
        assert total == 2
        assert correct == 1
    finally:
        _delete_bank_stats(app, bank_id)


def test_miniprogram_mine_uses_data_center_global_summary():
    """小程序我的页应与 Web 数据中心共用全局汇总口径。"""
    mine_ts = _read(MINIPROGRAM_MINE_DIR / "mine.ts")
    mine_js = _read(MINIPROGRAM_MINE_DIR / "mine.js")

    for source in (mine_ts, mine_js):
        assert "getDataCenter(30)" in source
        assert "all_summary" in source
        assert "getUserCounts({ subject: 'all' })" not in source
