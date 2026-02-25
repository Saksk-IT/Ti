# -*- coding: utf-8 -*-
"""题库选择页数据装载（公共题库 / 个人题库）。

用于 Web 端「收藏 / 错题 / 考试」先选题库的入口页，避免在各模块重复拼 SQL。
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.core.extensions import db


def load_public_subject_cards(conn, uid: Optional[int]) -> List[Dict[str, Any]]:
    """加载公共题库（科目）卡片：id/name/question_count。"""
    subject_rows: List[Dict[str, Any]] = []
    subject_ids: List[int] = []

    try:
        if uid:
            from app.core.utils.subject_permissions import get_user_accessible_subjects

            accessible_subject_ids = [
                int(x)
                for x in (get_user_accessible_subjects(int(uid)) or [])
                if x is not None
            ]
            if not accessible_subject_ids:
                return []

            placeholders = ",".join([f":id_{i}" for i in range(len(accessible_subject_ids))])
            params = {f"id_{i}": sid for i, sid in enumerate(accessible_subject_ids)}
            rows = db.session.execute(
                text(
                    f"SELECT id, name FROM subjects"
                    f" WHERE id IN ({placeholders})"
                    f" AND (is_locked=false OR is_locked IS NULL)"
                    f" ORDER BY id"
                ),
                params,
            ).fetchall()
            subject_rows = [dict(r._mapping) for r in (rows or []) if r]
        else:
            rows = db.session.execute(
                text("SELECT id, name FROM subjects WHERE (is_locked=false OR is_locked IS NULL) ORDER BY id")
            ).fetchall()
            subject_rows = [dict(r._mapping) for r in (rows or []) if r]
        subject_ids = [
            int(r["id"])
            for r in (subject_rows or [])
            if r and r.get("id") is not None
        ]
    except Exception:
        subject_rows = []
        subject_ids = []

    subject_counts: Dict[int, int] = {}
    if subject_ids:
        try:
            placeholders = ",".join([f":sid_{i}" for i in range(len(subject_ids))])
            params = {f"sid_{i}": sid for i, sid in enumerate(subject_ids)}
            rows = db.session.execute(
                text(
                    f"SELECT q.subject_id as subject_id, COUNT(*) as cnt"
                    f" FROM questions q"
                    f" LEFT JOIN subjects s ON q.subject_id = s.id"
                    f" WHERE q.subject_id IN ({placeholders})"
                    f" AND (s.is_locked=false OR s.is_locked IS NULL)"
                    f" GROUP BY q.subject_id"
                ),
                params,
            ).fetchall()
            subject_counts = {
                int(r._mapping["subject_id"]): int(r._mapping["cnt"] or 0)
                for r in (rows or [])
                if r and r._mapping["subject_id"] is not None
            }
        except Exception:
            subject_counts = {}

    cards: List[Dict[str, Any]] = []
    for r in subject_rows or []:
        try:
            sid = int(r.get("id") or 0)
        except Exception:
            sid = 0
        if sid <= 0:
            continue
        cards.append(
            {
                "id": sid,
                "name": r.get("name") or "",
                "question_count": int(subject_counts.get(sid, 0) or 0),
            }
        )
    return cards
# __CONTINUE_HERE__

def load_user_bank_cards(conn, uid: Optional[int]) -> List[Dict[str, Any]]:
    """加载个人题库卡片（包含我创建与收到分享）：id/name/question_count/is_shared/owner/permission。"""
    if not uid:
        return []

    cards: List[Dict[str, Any]] = []
    seen: set[int] = set()

    try:
        rows = db.session.execute(
            text(
                "SELECT id, name, COALESCE(question_count, 0) as question_count"
                " FROM user_question_banks"
                " WHERE user_id = :uid AND status = 1"
                " ORDER BY updated_at DESC, id DESC"
            ),
            {"uid": int(uid)},
        ).fetchall()
        for r in rows or []:
            if not r:
                continue
            d = dict(r._mapping)
            if d.get("id") is None:
                continue
            bid = int(d["id"])
            if bid <= 0 or bid in seen:
                continue
            seen.add(bid)
            cards.append(
                {
                    "id": bid,
                    "name": d.get("name") or "",
                    "question_count": int(d.get("question_count") or 0),
                    "is_shared": False,
                    "owner_nickname": None,
                    "permission": "owner",
                }
            )
    except Exception:
        pass

    try:
        rows = db.session.execute(
            text(
                "SELECT b.id as bank_id,"
                "       b.name as bank_name,"
                "       COALESCE(b.question_count, 0) as question_count,"
                "       bs.permission as permission,"
                "       u.username as owner_nickname"
                " FROM bank_share_records bsr"
                " JOIN bank_shares bs ON bsr.share_id = bs.id"
                " JOIN user_question_banks b ON bsr.bank_id = b.id"
                " JOIN users u ON b.user_id = u.id"
                " WHERE bsr.user_id = :uid"
                "   AND bsr.status = 1"
                "   AND b.status = 1"
                "   AND bs.is_active = true"
                " ORDER BY bsr.last_access_at DESC, bsr.access_count DESC, bsr.id DESC"
            ),
            {"uid": int(uid)},
        ).fetchall()
        for r in rows or []:
            if not r:
                continue
            d = dict(r._mapping)
            if d.get("bank_id") is None:
                continue
            bid = int(d["bank_id"])
            if bid <= 0 or bid in seen:
                continue
            seen.add(bid)
            cards.append(
                {
                    "id": bid,
                    "name": d.get("bank_name") or "",
                    "question_count": int(d.get("question_count") or 0),
                    "is_shared": True,
                    "owner_nickname": d.get("owner_nickname") or "",
                    "permission": (d.get("permission") or "").strip(),
                }
            )
    except Exception:
        pass
# __CONTINUE_HERE2__

    # 兜底：用 user_bank_questions 重新统计题目数量
    try:
        bank_ids = [int(c.get("id") or 0) for c in (cards or []) if c and c.get("id") is not None]
        bank_ids = [bid for bid in bank_ids if bid > 0]
        if bank_ids:
            placeholders = ",".join([f":bid_{i}" for i in range(len(bank_ids))])
            params = {f"bid_{i}": bid for i, bid in enumerate(bank_ids)}
            rows = db.session.execute(
                text(
                    f"SELECT bank_id, COUNT(1) as cnt"
                    f" FROM user_bank_questions"
                    f" WHERE bank_id IN ({placeholders})"
                    f" GROUP BY bank_id"
                ),
                params,
            ).fetchall()
            cnt_map = {
                int(r._mapping["bank_id"]): int(r._mapping["cnt"] or 0)
                for r in (rows or [])
                if r and r._mapping["bank_id"] is not None
            }
            for c in cards or []:
                try:
                    bid = int(c.get("id") or 0)
                except Exception:
                    bid = 0
                if bid > 0 and bid in cnt_map:
                    c["question_count"] = int(cnt_map.get(bid) or 0)
    except Exception:
        pass

    return cards


def load_bank_select_payload(conn, uid: Optional[int]) -> Dict[str, Any]:
    """统一返回：public_cards / bank_cards / totals。"""
    public_cards = load_public_subject_cards(conn, uid)
    bank_cards = load_user_bank_cards(conn, uid)
    return {
        "public_cards": public_cards,
        "bank_cards": bank_cards,
        "public_total": len(public_cards or []),
        "bank_total": len(bank_cards or []),
    }
