# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import text

from app.core.extensions import db


def _safe_int(v: Any) -> int:
    try:
        return int(v or 0)
    except Exception:
        return 0


def _pct(numer: int, denom: int) -> float:
    try:
        numer = int(numer or 0)
        denom = int(denom or 0)
        return round(numer * 100.0 / denom, 1) if denom > 0 else 0.0
    except Exception:
        return 0.0


def _to_ymd_text(raw: Any) -> str:
    s = (raw or "").strip() if isinstance(raw, str) else str(raw or "").strip()
    if not s:
        return "—"
    # 兼容 "YYYY-MM-DD HH:MM:SS" / ISO
    try:
        iso = s if "T" in s else s.replace(" ", "T")
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return s[:10]


def _chunked(items: List[int], size: int) -> Iterable[List[int]]:
    if size <= 0:
        size = 500
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _column_exists(conn, table: str, column: str) -> bool:
    """ORM 模型已定义所有字段，始终返回 True。保留签名以兼容旧调用。"""
    return True


def _get_accessible_subject_ids(conn, user_id: int) -> List[int]:
    try:
        from app.core.utils.subject_permissions import get_user_accessible_subjects

        ids = get_user_accessible_subjects(user_id) or []
        ids = [int(x) for x in ids if x is not None]
        if not ids:
            return []

        params = {f"p_{i}": v for i, v in enumerate(ids)}
        placeholders = ",".join(f":p_{i}" for i in range(len(ids)))
        rows = db.session.execute(
            text(f"SELECT id FROM subjects WHERE id IN ({placeholders}) AND (is_locked=false OR is_locked IS NULL)"),
            params,
        ).fetchall()
        out: List[int] = []
        for r in rows or []:
            try:
                rid = r._mapping["id"]
            except Exception:
                continue
            if rid is None:
                continue
            try:
                out.append(int(rid))
            except Exception:
                continue
        return out
    except Exception:
        return []


def _filter_public_question_ids(conn, question_ids: Set[int], accessible_subject_ids: List[int]) -> Set[int]:
    if not question_ids:
        return set()

    qids = sorted({int(x) for x in question_ids if int(x) > 0})
    if not qids:
        return set()

    subject_ids = [int(x) for x in (accessible_subject_ids or []) if int(x) > 0]
    base = 850
    chunk_size = max(100, base - len(subject_ids))

    allowed: Set[int] = set()
    for chunk in _chunked(qids, chunk_size):
        params: Dict[str, Any] = {f"q_{i}": v for i, v in enumerate(chunk)}
        placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
        sql = f"""
            SELECT q.id
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.id IN ({placeholders})
              AND (s.is_locked=false OR s.is_locked IS NULL)
        """
        if subject_ids:
            sp_params = {f"s_{i}": v for i, v in enumerate(subject_ids)}
            sp = ",".join(f":s_{i}" for i in range(len(subject_ids)))
            sql += f" AND q.subject_id IN ({sp})"
            params.update(sp_params)

        rows = db.session.execute(text(sql), params).fetchall()
        for r in rows or []:
            try:
                allowed.add(int(r._mapping["id"]))
            except Exception:
                continue

    return allowed


def _aggregate_public_activity(
    conn, user_id: int, question_ids: Set[int], window_days: int
) -> Tuple[Dict[int, Dict[str, Any]], Set[int], Dict[int, int]]:
    qids = sorted({int(x) for x in (question_ids or set()) if int(x) > 0})
    if not qids:
        return {}, set(), {}

    cutoff = (datetime.now(timezone.utc) + timedelta(hours=8) - timedelta(days=int(window_days))).strftime('%Y-%m-%d %H:%M:%S')
    answer_map: Dict[int, Dict[str, Any]] = {}
    favorites_set: Set[int] = set()
    mistakes_times_map: Dict[int, int] = {}

    chunk_size = 850
    for chunk in _chunked(qids, chunk_size):
        params: Dict[str, Any] = {f"q_{i}": v for i, v in enumerate(chunk)}
        placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
        params["user_id"] = int(user_id)
        params["cutoff"] = cutoff
        rows = db.session.execute(
            text(f"""
            SELECT
              question_id,
              COUNT(*) AS answered,
              SUM(CASE WHEN is_correct=true THEN 1 ELSE 0 END) AS correct,
              MAX(created_at) AS last_activity
            FROM user_answers
            WHERE user_id = :user_id
              AND created_at >= :cutoff
              AND question_id IN ({placeholders})
            GROUP BY question_id
            """),
            params,
        ).fetchall()
        for r in rows or []:
            try:
                qid = int(r._mapping["question_id"])
            except Exception:
                continue
            answer_map[qid] = {
                "answered": _safe_int(r._mapping["answered"]),
                "correct": _safe_int(r._mapping["correct"]),
                "last_activity": (r._mapping["last_activity"] or None),
            }

    for chunk in _chunked(qids, chunk_size):
        params = {f"q_{i}": v for i, v in enumerate(chunk)}
        placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
        params["user_id"] = int(user_id)
        rows = db.session.execute(
            text(f"SELECT question_id FROM favorites WHERE user_id=:user_id AND question_id IN ({placeholders})"),
            params,
        ).fetchall()
        for r in rows or []:
            try:
                favorites_set.add(int(r._mapping["question_id"]))
            except Exception:
                continue

    # _column_exists always returns True now (ORM models define all fields)
    for chunk in _chunked(qids, chunk_size):
        params = {f"q_{i}": v for i, v in enumerate(chunk)}
        placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
        params["user_id"] = int(user_id)
        sql = f"""
            SELECT question_id, SUM(COALESCE(wrong_count, 1)) AS times
            FROM mistakes
            WHERE user_id=:user_id AND question_id IN ({placeholders})
            GROUP BY question_id
        """
        rows = db.session.execute(text(sql), params).fetchall()
        for r in rows or []:
            try:
                qid = int(r._mapping["question_id"])
            except Exception:
                continue
            mistakes_times_map[qid] = _safe_int(r._mapping["times"])

    return answer_map, favorites_set, mistakes_times_map


def _aggregate_bank_activity(
    conn, user_id: int, bank_id: int, question_ids: Set[int], window_days: int
) -> Tuple[Dict[int, Dict[str, Any]], Set[int], Dict[int, int]]:
    qids = sorted({int(x) for x in (question_ids or set()) if int(x) > 0})
    if not qids:
        return {}, set(), {}

    cutoff = (datetime.now(timezone.utc) + timedelta(hours=8) - timedelta(days=int(window_days))).strftime('%Y-%m-%d %H:%M:%S')
    answer_map: Dict[int, Dict[str, Any]] = {}
    favorites_set: Set[int] = set()
    mistakes_times_map: Dict[int, int] = {}

    chunk_size = 850
    for chunk in _chunked(qids, chunk_size):
        params: Dict[str, Any] = {f"q_{i}": v for i, v in enumerate(chunk)}
        placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
        params["user_id"] = int(user_id)
        params["bank_id"] = int(bank_id)
        params["cutoff"] = cutoff
        rows = db.session.execute(
            text(f"""
            SELECT
              question_id,
              COUNT(*) AS answered,
              SUM(CASE WHEN is_correct=true THEN 1 ELSE 0 END) AS correct,
              MAX(created_at) AS last_activity
            FROM user_bank_answers
            WHERE user_id = :user_id
              AND bank_id = :bank_id
              AND created_at >= :cutoff
              AND question_id IN ({placeholders})
            GROUP BY question_id
            """),
            params,
        ).fetchall()
        for r in rows or []:
            try:
                qid = int(r._mapping["question_id"])
            except Exception:
                continue
            answer_map[qid] = {
                "answered": _safe_int(r._mapping["answered"]),
                "correct": _safe_int(r._mapping["correct"]),
                "last_activity": (r._mapping["last_activity"] or None),
            }

    for chunk in _chunked(qids, chunk_size):
        params = {f"q_{i}": v for i, v in enumerate(chunk)}
        placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
        params["user_id"] = int(user_id)
        params["bank_id"] = int(bank_id)
        rows = db.session.execute(
            text(f"""
            SELECT question_id
            FROM user_bank_favorites
            WHERE user_id=:user_id AND bank_id=:bank_id AND question_id IN ({placeholders})
            """),
            params,
        ).fetchall()
        for r in rows or []:
            try:
                favorites_set.add(int(r._mapping["question_id"]))
            except Exception:
                continue

    # _column_exists always returns True now (ORM models define all fields)
    for chunk in _chunked(qids, chunk_size):
        params = {f"q_{i}": v for i, v in enumerate(chunk)}
        placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
        params["user_id"] = int(user_id)
        params["bank_id"] = int(bank_id)
        sql = f"""
            SELECT question_id, SUM(COALESCE(wrong_count, 1)) AS times
            FROM user_bank_mistakes
            WHERE user_id=:user_id AND bank_id=:bank_id AND question_id IN ({placeholders})
            GROUP BY question_id
        """
        rows = db.session.execute(text(sql), params).fetchall()
        for r in rows or []:
            try:
                qid = int(r._mapping["question_id"])
            except Exception:
                continue
            mistakes_times_map[qid] = _safe_int(r._mapping["times"])

    return answer_map, favorites_set, mistakes_times_map


def compute_data_tags_context(conn, user_id: int, window_days: int = 30) -> Dict[str, Any]:
    """
    标签聚合统计：
    - public：公共题库 tags（按"用户 × 科目(subject_id)"隔离，存 user_question_tag_items）
    - banks：个人题库 tags（按"用户 × 题库(bank_id)"隔离，存 user_question_tag_items）
    """
    window_days = int(window_days or 30)
    if window_days not in (7, 30, 90):
        window_days = 30

    from app.modules.quiz.services.question_tags_service import _normalize_tag_name

    accessible_subject_ids = _get_accessible_subject_ids(conn, int(user_id))

    # ======================
    # 公共题库标签（user_question_tag_items：scope=question_center）
    # ======================
    public_rows: List[Dict[str, Any]] = []
    public_all_qids: Set[int] = set()
    public_tag_qids: Dict[str, Set[int]] = {}

    try:
        from app.core.utils.user_question_tags import SCOPE_QUESTION_CENTER, ensure_tag_tables

        ensure_tag_tables(conn)

        # 优先 subject 维度（scope_id<>0）；若没有，则回退旧结构 scope_id=0
        use_scope0 = False
        try:
            row = db.session.execute(
                text("SELECT 1 FROM user_question_tag_items WHERE user_id=:user_id AND scope=:scope AND scope_id<>0 LIMIT 1"),
                {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
            ).fetchone()
            use_scope0 = row is None
        except Exception:
            use_scope0 = True

        if use_scope0:
            rows = db.session.execute(
                text("""
                SELECT question_id, tag
                FROM user_question_tag_items
                WHERE user_id=:user_id AND scope=:scope AND scope_id=0 AND question_id>0
                ORDER BY question_id ASC, tag ASC
                """),
                {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
            ).fetchall()
        else:
            rows = db.session.execute(
                text("""
                SELECT question_id, tag
                FROM user_question_tag_items
                WHERE user_id=:user_id AND scope=:scope AND scope_id<>0 AND question_id>0
                ORDER BY question_id ASC, tag ASC
                """),
                {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
            ).fetchall()

        for r in rows or []:
            try:
                qid = int(r._mapping["question_id"])
            except Exception:
                continue
            if qid <= 0:
                continue

            tag = _normalize_tag_name(r._mapping["tag"])
            if not tag or tag.lower() == "all":
                continue

            public_tag_qids.setdefault(tag, set()).add(qid)
            public_all_qids.add(qid)
    except Exception:
        public_tag_qids = {}
        public_all_qids = set()

    public_allowed_qids = _filter_public_question_ids(conn, public_all_qids, accessible_subject_ids) if accessible_subject_ids else set()
    public_answer_map, public_fav_set, public_mis_times_map = _aggregate_public_activity(
        conn, int(user_id), public_allowed_qids, window_days
    )

    public_total_answered = 0
    public_total_correct = 0
    public_last_activity = None

    for qid, st in (public_answer_map or {}).items():
        public_total_answered += _safe_int(st.get("answered"))
        public_total_correct += _safe_int(st.get("correct"))
        la = st.get("last_activity")
        if la and (not public_last_activity or str(la) > str(public_last_activity)):
            public_last_activity = la

    for tag in sorted(public_tag_qids.keys()):
        qids = public_tag_qids.get(tag) or set()
        qids = set(int(x) for x in qids if int(x) > 0)
        qids = qids.intersection(public_allowed_qids)
        if not qids:
            continue

        answered = 0
        correct = 0
        favorites = 0
        mistakes_times = 0
        last_activity = None

        for qid in qids:
            st = public_answer_map.get(qid) or {}
            answered += _safe_int(st.get("answered"))
            correct += _safe_int(st.get("correct"))
            la = st.get("last_activity")
            if la and (not last_activity or str(la) > str(last_activity)):
                last_activity = la
            if qid in public_fav_set:
                favorites += 1
            mistakes_times += _safe_int(public_mis_times_map.get(qid))

        public_rows.append(
            {
                "key": f"public:{tag}",
                "scope": "public",
                "tag": tag,
                "question_count": len(qids),
                "answered": answered,
                "accuracy": _pct(correct, answered),
                "favorites": favorites,
                "mistakes_times": mistakes_times,
                "last_activity": last_activity,
            }
        )

    # ======================
    # 个人题库标签（bank_{id}_tags）
    # ======================
    bank_rows: List[Dict[str, Any]] = []
    bank_unique_tags: Set[str] = set()
    bank_all_qids: Set[int] = set()
    bank_total_answered = 0
    bank_total_correct = 0
    bank_last_activity = None

    bank_name_cache: Dict[int, str] = {}

    # ----------------------
    # 新结构：user_question_tag_items（按用户维度隔离）
    # ----------------------
    bank_seen_ids: Set[int] = set()
    bank_tag_qids_map: Dict[int, Dict[str, Set[int]]] = {}
    try:
        from app.core.utils.user_question_tags import SCOPE_USER_BANK, ensure_tag_tables

        ensure_tag_tables(conn)
        rows = db.session.execute(
            text("""
            SELECT scope_id AS bank_id, question_id, tag
            FROM user_question_tag_items
            WHERE user_id = :user_id AND scope = :scope AND scope_id IS NOT NULL AND question_id > 0
            ORDER BY scope_id ASC, tag ASC, question_id ASC
            """),
            {"user_id": int(user_id), "scope": str(SCOPE_USER_BANK)},
        ).fetchall()
    except Exception:
        rows = []

    for r in rows or []:
        try:
            bank_id = int(r._mapping["bank_id"])
            qid = int(r._mapping["question_id"])
        except Exception:
            continue
        if bank_id <= 0 or qid <= 0:
            continue

        tag = _normalize_tag_name(r._mapping["tag"])
        if not tag or tag.lower() == "all":
            continue

        bank_seen_ids.add(bank_id)
        bank_tag_qids_map.setdefault(bank_id, {}).setdefault(tag, set()).add(qid)

    for bank_id, tag_qids in (bank_tag_qids_map or {}).items():
        all_qids: Set[int] = set()
        for s in (tag_qids or {}).values():
            all_qids.update(set(s or []))
        if not all_qids:
            continue

        allowed_qids: Set[int] = set()
        qids_list = sorted({int(x) for x in all_qids if int(x) > 0})
        if not qids_list:
            continue

        chunk_size = 850
        for chunk in _chunked(qids_list, chunk_size):
            params: Dict[str, Any] = {f"q_{i}": v for i, v in enumerate(chunk)}
            placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
            params["bank_id"] = int(bank_id)
            rows = db.session.execute(
                text(f"SELECT id FROM user_bank_questions WHERE bank_id=:bank_id AND id IN ({placeholders})"),
                params,
            ).fetchall()
            for r in rows or []:
                try:
                    allowed_qids.add(int(r._mapping["id"]))
                except Exception:
                    continue

        if not allowed_qids:
            continue

        # bank 名称
        bank_name = bank_name_cache.get(bank_id)
        if bank_name is None:
            try:
                b = db.session.execute(
                    text("SELECT name FROM user_question_banks WHERE id=:bank_id"),
                    {"bank_id": int(bank_id)},
                ).fetchone()
                try:
                    bank_name = (b._mapping["name"] or "").strip() if b and b._mapping["name"] is not None else ""
                except Exception:
                    bank_name = ""
            except Exception:
                bank_name = ""
            bank_name_cache[bank_id] = bank_name
        if not bank_name:
            bank_name = f"题库 {bank_id}"

        ans_map, fav_set, mis_times_map = _aggregate_bank_activity(conn, int(user_id), bank_id, allowed_qids, window_days)
        for qid, st in (ans_map or {}).items():
            bank_total_answered += _safe_int(st.get("answered"))
            bank_total_correct += _safe_int(st.get("correct"))
            la = st.get("last_activity")
            if la and (not bank_last_activity or str(la) > str(bank_last_activity)):
                bank_last_activity = la

        bank_all_qids.update(allowed_qids)

        for tag in sorted(set(tag_qids.keys())):
            qids = (tag_qids.get(tag) or set()).intersection(allowed_qids)
            if not qids:
                continue

            answered = 0
            correct = 0
            favorites = 0
            mistakes_times = 0
            last_activity = None

            for qid in qids:
                st = ans_map.get(qid) or {}
                answered += _safe_int(st.get("answered"))
                correct += _safe_int(st.get("correct"))
                la = st.get("last_activity")
                if la and (not last_activity or str(la) > str(last_activity)):
                    last_activity = la
                if qid in fav_set:
                    favorites += 1
                mistakes_times += _safe_int(mis_times_map.get(qid))

            bank_rows.append(
                {
                    "key": f"bank:{bank_id}:{tag}",
                    "scope": "bank",
                    "tag": tag,
                    "bank_id": int(bank_id),
                    "bank_name": bank_name,
                    "question_count": len(qids),
                    "answered": answered,
                    "accuracy": _pct(correct, answered),
                    "favorites": favorites,
                    "mistakes_times": mistakes_times,
                    "last_activity": last_activity,
                }
            )
            if tag:
                bank_unique_tags.add(tag)

    # ----------------------
    # 旧结构（兜底）：user_progress.bank_{id}_tags
    # ----------------------
    try:
        up_rows = db.session.execute(
            text("SELECT p_key, data FROM user_progress WHERE user_id=:user_id AND p_key LIKE 'bank_%_tags'"),
            {"user_id": int(user_id)},
        ).fetchall()
    except Exception:
        up_rows = []

    for row in up_rows or []:
        row_map = dict(row._mapping)
        key = row_map.get("p_key")
        data = row_map.get("data")
        if not key:
            continue
        parts = str(key).split("_")
        if len(parts) < 3:
            continue
        try:
            bank_id = int(parts[1])
        except Exception:
            continue
        if bank_id <= 0 or bank_id in bank_seen_ids:
            continue

        try:
            store = json.loads(data) if data else {}
        except Exception:
            continue
        if not isinstance(store, dict):
            continue

        raw_tags = store.get("tags") if isinstance(store.get("tags"), list) else []
        tag_set: Set[str] = set()
        tag_names: List[str] = []
        for t in raw_tags:
            name = _normalize_tag_name(t)
            if not name or name.lower() == "all" or name in tag_set:
                continue
            tag_set.add(name)
            tag_names.append(name)

        question_tags = store.get("question_tags") if isinstance(store.get("question_tags"), dict) else {}
        tag_qids: Dict[str, Set[int]] = {t: set() for t in tag_names}
        all_qids: Set[int] = set()

        for qid_raw, tags in (question_tags or {}).items():
            try:
                qid = int(qid_raw)
            except Exception:
                continue
            if qid <= 0 or not isinstance(tags, list):
                continue
            for t in tags:
                name = _normalize_tag_name(t)
                if not name or name not in tag_set:
                    continue
                tag_qids[name].add(qid)
                all_qids.add(qid)

        if not all_qids:
            continue

        # 过滤：确保题目仍在该 bank 中
        allowed_qids: Set[int] = set()
        qids_list = sorted({int(x) for x in all_qids if int(x) > 0})
        if not qids_list:
            continue

        chunk_size = 850
        for chunk in _chunked(qids_list, chunk_size):
            params: Dict[str, Any] = {f"q_{i}": v for i, v in enumerate(chunk)}
            placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
            params["bank_id"] = int(bank_id)
            rows = db.session.execute(
                text(f"SELECT id FROM user_bank_questions WHERE bank_id=:bank_id AND id IN ({placeholders})"),
                params,
            ).fetchall()
            for r in rows or []:
                try:
                    allowed_qids.add(int(r._mapping["id"]))
                except Exception:
                    continue

        if not allowed_qids:
            continue

        # bank 名称
        bank_name = bank_name_cache.get(bank_id)
        if bank_name is None:
            try:
                b = db.session.execute(
                    text("SELECT name FROM user_question_banks WHERE id=:bank_id"),
                    {"bank_id": int(bank_id)},
                ).fetchone()
                try:
                    bank_name = (b._mapping["name"] or "").strip() if b and b._mapping["name"] is not None else ""
                except Exception:
                    bank_name = ""
            except Exception:
                bank_name = ""
            bank_name_cache[bank_id] = bank_name
        if not bank_name:
            bank_name = f"题库 {bank_id}"

        ans_map, fav_set, mis_times_map = _aggregate_bank_activity(conn, int(user_id), bank_id, allowed_qids, window_days)
        for qid, st in (ans_map or {}).items():
            bank_total_answered += _safe_int(st.get("answered"))
            bank_total_correct += _safe_int(st.get("correct"))
            la = st.get("last_activity")
            if la and (not bank_last_activity or str(la) > str(bank_last_activity)):
                bank_last_activity = la

        bank_all_qids.update(allowed_qids)

        for tag in tag_names:
            qids = (tag_qids.get(tag) or set()).intersection(allowed_qids)
            if not qids:
                continue

            answered = 0
            correct = 0
            favorites = 0
            mistakes_times = 0
            last_activity = None

            for qid in qids:
                st = ans_map.get(qid) or {}
                answered += _safe_int(st.get("answered"))
                correct += _safe_int(st.get("correct"))
                la = st.get("last_activity")
                if la and (not last_activity or str(la) > str(last_activity)):
                    last_activity = la
                if qid in fav_set:
                    favorites += 1
                mistakes_times += _safe_int(mis_times_map.get(qid))

            bank_rows.append(
                {
                    "key": f"bank:{bank_id}:{tag}",
                    "scope": "bank",
                    "tag": tag,
                    "bank_id": int(bank_id),
                    "bank_name": bank_name,
                    "question_count": len(qids),
                    "answered": answered,
                    "accuracy": _pct(correct, answered),
                    "favorites": favorites,
                    "mistakes_times": mistakes_times,
                    "last_activity": last_activity,
                }
            )
            if tag:
                bank_unique_tags.add(tag)

    # ======================
    # 汇总 + Top 列表
    # ======================
    public_tagged_questions = len(public_allowed_qids)
    public_favorites = len(public_fav_set)
    public_mistakes_times = sum(_safe_int(v) for v in (public_mis_times_map or {}).values())

    bank_tagged_questions = len(bank_all_qids)
    bank_favorites = sum(_safe_int(r.get("favorites")) for r in bank_rows)
    bank_mistakes_times = sum(_safe_int(r.get("mistakes_times")) for r in bank_rows)

    # 注意：bank_rows 的 favorites/mistakes_times 可能在多标签下重复计数；
    # summary 以"题目集合"维度为主，避免重复（更接近用户直觉）。
    bank_favorites_set: Set[Tuple[int, int]] = set()
    bank_mistakes_times_map2: Dict[int, int] = {}
    if bank_all_qids:
        # favorites
        qids_list = sorted(bank_all_qids)
        chunk_size = 850
        for chunk in _chunked(qids_list, chunk_size):
            params: Dict[str, Any] = {f"q_{i}": v for i, v in enumerate(chunk)}
            placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
            params["user_id"] = int(user_id)
            rows = db.session.execute(
                text(f"SELECT question_id, bank_id FROM user_bank_favorites WHERE user_id=:user_id AND question_id IN ({placeholders})"),
                params,
            ).fetchall()
            for r in rows or []:
                try:
                    bank_favorites_set.add((int(r._mapping["bank_id"]), int(r._mapping["question_id"])))
                except Exception:
                    continue

        # _column_exists always returns True now (ORM models define all fields)
        for chunk in _chunked(qids_list, chunk_size):
            params = {f"q_{i}": v for i, v in enumerate(chunk)}
            placeholders = ",".join(f":q_{i}" for i in range(len(chunk)))
            params["user_id"] = int(user_id)
            sql = f"""
                SELECT question_id, SUM(COALESCE(wrong_count,1)) AS times
                FROM user_bank_mistakes
                WHERE user_id=:user_id AND question_id IN ({placeholders})
                GROUP BY question_id
            """
            rows = db.session.execute(text(sql), params).fetchall()
            for r in rows or []:
                try:
                    bank_mistakes_times_map2[int(r._mapping["question_id"])] = _safe_int(r._mapping["times"])
                except Exception:
                    continue

    bank_favorites = len(bank_favorites_set)
    bank_mistakes_times = sum(_safe_int(v) for v in bank_mistakes_times_map2.values())

    all_last_activity = public_last_activity or bank_last_activity
    if public_last_activity and bank_last_activity:
        all_last_activity = public_last_activity if str(public_last_activity) > str(bank_last_activity) else bank_last_activity

    public_summary = {
        "tag_total": len(public_rows),
        "tagged_questions": public_tagged_questions,
        "answered": public_total_answered,
        "accuracy": _pct(public_total_correct, public_total_answered),
        "favorites": public_favorites,
        "mistakes_times": public_mistakes_times,
        "last_activity_text": _to_ymd_text(public_last_activity),
    }
    banks_summary = {
        "tag_total": len(bank_unique_tags),
        "tagged_questions": bank_tagged_questions,
        "answered": bank_total_answered,
        "accuracy": _pct(bank_total_correct, bank_total_answered),
        "favorites": bank_favorites,
        "mistakes_times": bank_mistakes_times,
        "last_activity_text": _to_ymd_text(bank_last_activity),
    }

    all_tag_total = len(set([r.get("tag") for r in public_rows if r.get("tag")]) | bank_unique_tags)
    all_tagged_questions = public_tagged_questions + bank_tagged_questions
    all_answered = public_total_answered + bank_total_answered
    all_correct = public_total_correct + bank_total_correct
    all_favorites = public_favorites + bank_favorites
    all_mistakes_times = public_mistakes_times + bank_mistakes_times

    all_summary = {
        "tag_total": all_tag_total,
        "tagged_questions": all_tagged_questions,
        "answered": all_answered,
        "accuracy": _pct(all_correct, all_answered),
        "favorites": all_favorites,
        "mistakes_times": all_mistakes_times,
        "last_activity_text": _to_ymd_text(all_last_activity),
    }

    all_rows = public_rows + bank_rows

    def _row_score_usage(r: Dict[str, Any]) -> Tuple[int, int]:
        return (_safe_int(r.get("question_count")), _safe_int(r.get("answered")))

    def _row_score_mistakes(r: Dict[str, Any]) -> Tuple[int, int]:
        return (_safe_int(r.get("mistakes_times")), _safe_int(r.get("question_count")))

    top_usage = sorted(all_rows, key=_row_score_usage, reverse=True)[:30]
    top_mistakes = [r for r in all_rows if _safe_int(r.get("mistakes_times")) > 0]
    top_mistakes = sorted(top_mistakes, key=_row_score_mistakes, reverse=True)[:30]

    low_accuracy = [r for r in all_rows if _safe_int(r.get("answered")) >= 10 and _safe_int(r.get("question_count")) >= 5]
    low_accuracy = sorted(low_accuracy, key=lambda r: float(r.get("accuracy") or 0.0))[:30]

    return {
        "summary": {
            "all": all_summary,
            "public": public_summary,
            "banks": banks_summary,
        },
        "top_usage": top_usage,
        "top_mistakes": top_mistakes,
        "low_accuracy": low_accuracy,
    }
