# -*- coding: utf-8 -*-
"""题库选择页数据装载（公共题库 / 个人题库）。

用于 Web 端「收藏 / 错题 / 考试」先选题库的入口页，避免在各模块重复拼 SQL。
"""

from typing import Any, Dict, List, Optional


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

            placeholders = ",".join(["?"] * len(accessible_subject_ids))
            rows = conn.execute(
                f"""
                SELECT id, name
                FROM subjects
                WHERE id IN ({placeholders})
                  AND (is_locked=0 OR is_locked IS NULL)
                ORDER BY id
                """,
                accessible_subject_ids,
            ).fetchall()
            subject_rows = [dict(r) for r in (rows or []) if r]
        else:
            rows = conn.execute(
                """
                SELECT id, name
                FROM subjects
                WHERE (is_locked=0 OR is_locked IS NULL)
                ORDER BY id
                """
            ).fetchall()
            subject_rows = [dict(r) for r in (rows or []) if r]

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
            placeholders = ",".join(["?"] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id as subject_id, COUNT(*) as cnt
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE q.subject_id IN ({placeholders})
                  AND (s.is_locked=0 OR s.is_locked IS NULL)
                GROUP BY q.subject_id
                """,
                subject_ids,
            ).fetchall()
            subject_counts = {
                int(r["subject_id"]): int(r["cnt"] or 0)
                for r in (rows or [])
                if r and r["subject_id"] is not None
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


def load_user_bank_cards(conn, uid: Optional[int]) -> List[Dict[str, Any]]:
    """加载个人题库卡片（包含我创建与收到分享）：id/name/question_count/is_shared/owner/permission。"""
    if not uid:
        return []

    cards: List[Dict[str, Any]] = []
    seen: set[int] = set()

    try:
        rows = conn.execute(
            """
            SELECT id, name, COALESCE(question_count, 0) as question_count
            FROM user_question_banks
            WHERE user_id = ? AND status = 1
            ORDER BY updated_at DESC, id DESC
            """,
            (int(uid),),
        ).fetchall()
        for r in rows or []:
            if not r:
                continue
            r = dict(r)
            if r.get("id") is None:
                continue
            bid = int(r["id"])
            if bid <= 0 or bid in seen:
                continue
            seen.add(bid)
            cards.append(
                {
                    "id": bid,
                    "name": r.get("name") or "",
                    "question_count": int(r.get("question_count") or 0),
                    "is_shared": False,
                    "owner_nickname": None,
                    "permission": "owner",
                }
            )
    except Exception:
        pass

    try:
        rows = conn.execute(
            """
            SELECT b.id as bank_id,
                   b.name as bank_name,
                   COALESCE(b.question_count, 0) as question_count,
                   bs.permission as permission,
                   u.username as owner_nickname
            FROM bank_share_records bsr
            JOIN bank_shares bs ON bsr.share_id = bs.id
            JOIN user_question_banks b ON bsr.bank_id = b.id
            JOIN users u ON b.user_id = u.id
            WHERE bsr.user_id = ?
              AND bsr.status = 1
              AND b.status = 1
              AND bs.is_active = 1
            ORDER BY bsr.last_access_at DESC, bsr.access_count DESC, bsr.id DESC
            """,
            (int(uid),),
        ).fetchall()
        for r in rows or []:
            if not r:
                continue
            r = dict(r)
            if r.get("bank_id") is None:
                continue
            bid = int(r["bank_id"])
            if bid <= 0 or bid in seen:
                continue
            seen.add(bid)
            cards.append(
                {
                    "id": bid,
                    "name": r.get("bank_name") or "",
                    "question_count": int(r.get("question_count") or 0),
                    "is_shared": True,
                    "owner_nickname": r.get("owner_nickname") or "",
                    "permission": (r.get("permission") or "").strip(),
                }
            )
    except Exception:
        pass

    # 兜底：用 user_bank_questions 重新统计题目数量，避免 question_count 维护不一致导致入口页展示错误
    try:
        bank_ids = [int(c.get("id") or 0) for c in (cards or []) if c and c.get("id") is not None]
        bank_ids = [bid for bid in bank_ids if bid > 0]
        if bank_ids:
            placeholders = ",".join(["?"] * len(bank_ids))
            rows = conn.execute(
                f"""
                SELECT bank_id, COUNT(1) as cnt
                FROM user_bank_questions
                WHERE bank_id IN ({placeholders})
                GROUP BY bank_id
                """,
                bank_ids,
            ).fetchall()
            cnt_map = {
                int(r["bank_id"]): int(r["cnt"] or 0)
                for r in (rows or [])
                if r and r["bank_id"] is not None
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
