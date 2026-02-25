# -*- coding: utf-8 -*-
"""复盘中心 — 数据 tab 统计逻辑。"""

from __future__ import annotations

from datetime import timedelta

from flask import current_app

from app.core.extensions import db
from sqlalchemy import text as sa_text
from app.core.utils.time_utils import today_bj

from .review_center_helpers import _build_preview, _url_with_params


# ── 通用工具 ──────────────────────────────────────────────


def _pct(n: int, d: int) -> float:
    try:
        return round((float(n) * 100.0 / float(d)) if d else 0.0, 1)
    except Exception:
        return 0.0


def _build_named_in(col: str, values: list, prefix: str = "in") -> tuple[str, dict]:
    """Build a named-parameter IN clause for SQLAlchemy text() queries."""
    if not values:
        return f"{col} IN (NULL)", {}
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    placeholders = ", ".join(f":{k}" for k in params)
    return f"{col} IN ({placeholders})", params


def _append_tag_clause(sql: str, params: dict, tag_ids, col: str = "q.id") -> tuple[str, dict]:
    if isinstance(tag_ids, list):
        in_clause, in_params = _build_named_in(col, tag_ids, "tag")
        sql += f" AND {in_clause}"
        params.update(in_params)
    return sql, params


def _append_type_clause(sql: str, params: dict, q_type: str, col: str = "q.type") -> tuple[str, dict]:
    if q_type and q_type != "all":
        from app.core.utils.portable_question_format import any_type_to_portable_type
        portable_type = any_type_to_portable_type(q_type)
        col = str(col or "q.type").replace(".q_type", ".type")
        sql += f" AND {col} = :type_filter"
        params["type_filter"] = portable_type
    return sql, params


# ── 题型分布 ──────────────────────────────────────────────


def load_type_distribution(
    *, conn, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, tag_ids, tag: str,
    q_type: str, base_url: str, ctx: dict,
) -> tuple[list[dict], int]:
    """返回 (type_dist, data_type_count)。conn parameter kept for backward compatibility."""
    if isinstance(tag_ids, list) and len(tag_ids) == 0 and tag and tag.lower() != "all":
        return [], 0

    if source_type == "public":
        base = """
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON f.question_id = q.id AND f.user_id = :uid
            LEFT JOIN mistakes m ON m.question_id = q.id AND m.user_id = :uid2
            WHERE (s.is_locked=false OR s.is_locked IS NULL)
              AND q.subject_id = :subject_id
        """
        params: dict = {"uid": int(uid), "uid2": int(uid), "subject_id": int(subject_id)}
        if kind == "favorites":
            base += " AND f.id IS NOT NULL"
        elif kind == "mistakes":
            base += " AND m.id IS NOT NULL"
        if isinstance(tag_ids, list):
            in_clause, in_params = _build_named_in("q.id", tag_ids, "tdist")
            base += f" AND {in_clause}"
            params.update(in_params)
        base += " GROUP BY q.type ORDER BY cnt DESC"
        rows = db.session.execute(sa_text(base), params).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        dist = [
            {"q_type": portable_type_to_q_type((r._mapping["p_type"] or "")), "count": int(r._mapping["cnt"] or 0)}
            for r in (rows or []) if r and r._mapping["p_type"]
        ]
    else:
        base = """
            SELECT q.type as p_type, COUNT(1) as cnt
            FROM user_bank_questions q
            LEFT JOIN user_bank_favorites f ON f.question_id = q.id AND f.user_id = :uid
            LEFT JOIN user_bank_mistakes m ON m.question_id = q.id AND m.user_id = :uid2
            WHERE q.bank_id = :bank_id
        """
        params = {"uid": int(uid), "uid2": int(uid), "bank_id": int(bank_id)}
        if kind == "favorites":
            base += " AND f.id IS NOT NULL"
        elif kind == "mistakes":
            base += " AND m.id IS NOT NULL"
        if isinstance(tag_ids, list):
            in_clause, in_params = _build_named_in("q.id", tag_ids, "tdist")
            base += f" AND {in_clause}"
            params.update(in_params)
        base += " GROUP BY q.type ORDER BY cnt DESC"
        rows = db.session.execute(sa_text(base), params).fetchall()
        from app.core.utils.portable_question_format import portable_type_to_q_type
        dist = [
            {"q_type": portable_type_to_q_type((r._mapping["p_type"] or ""), essay_q_type="简答题"), "count": int(r._mapping["cnt"] or 0)}
            for r in (rows or []) if r and r._mapping["p_type"]
        ]

    max_n = max([d["count"] for d in dist], default=0)
    type_dist = []
    for d in dist[:10]:
        d["pct"] = int(round((d["count"] * 100.0 / max_n), 0)) if max_n else 0
        d["practice_url"] = _url_with_params(base_url, {**ctx, "tab": "practice", "type": d["q_type"], "tag": tag})
        type_dist.append(d)
    return type_dist, len(dist)


# ── data tab 完整加载 ─────────────────────────────────────


def load_data_tab(
    *, conn, uid: int, source_type: str, subject_id: int | None,
    bank_id: int, kind: str, q_type: str, tag: str, tag_ids,
    tags: list, available_count: int, data_total: int,
    base_url: str, ctx: dict,
) -> dict:
    """加载 data tab 所需的全部统计数据。conn kept for backward compat."""
    uid = int(uid or 0)
    today = today_bj()
    from app.core.utils.portable_question_format import portable_type_to_q_type

    # ── 构建基础 WHERE ──
    if source_type == "public":
        ans_table = "user_answers"
        q_join = "JOIN questions q ON a.question_id = q.id LEFT JOIN subjects s ON q.subject_id = s.id"
        base_where = "(s.is_locked=false OR s.is_locked IS NULL) AND q.subject_id = :subject_id AND a.user_id = :uid"
        base_params: dict = {"uid": uid, "subject_id": int(subject_id or 0)}
        fav_table = "favorites"
        mis_table = "mistakes"
        q_table = "questions"
        q_where = "(s.is_locked=false OR s.is_locked IS NULL) AND q.subject_id = :subject_id"
        q_params: dict = {"subject_id": int(subject_id or 0)}
    else:
        ans_table = "user_bank_answers"
        q_join = "JOIN user_bank_questions q ON a.question_id = q.id"
        base_where = "q.bank_id = :bank_id AND a.user_id = :uid"
        base_params = {"uid": uid, "bank_id": int(bank_id)}
        fav_table = "user_bank_favorites"
        mis_table = "user_bank_mistakes"
        q_table = "user_bank_questions"
        q_where = "q.bank_id = :bank_id"
        q_params = {"bank_id": int(bank_id)}

    # ── 答题统计 ──
    data_answer = {
        "answered": 0, "correct": 0, "accuracy": 0.0,
        "answered_7d": 0, "correct_7d": 0, "accuracy_7d": 0.0,
        "answered_30d": 0, "correct_30d": 0, "accuracy_30d": 0.0,
    }
    try:
        sql = f"""
            SELECT
              COUNT(*) AS answered,
              SUM(CASE WHEN a.is_correct = true THEN 1 ELSE 0 END) AS correct,
              SUM(CASE WHEN a.created_at >= :d7 THEN 1 ELSE 0 END) AS answered_7d,
              SUM(CASE WHEN a.created_at >= :d7 AND a.is_correct = true THEN 1 ELSE 0 END) AS correct_7d,
              SUM(CASE WHEN a.created_at >= :d30 THEN 1 ELSE 0 END) AS answered_30d,
              SUM(CASE WHEN a.created_at >= :d30 AND a.is_correct = true THEN 1 ELSE 0 END) AS correct_30d
            FROM {ans_table} a {q_join}
            WHERE {base_where}
        """
        p = {**base_params, "d7": today - timedelta(days=7), "d30": today - timedelta(days=30)}
        sql, p = _append_type_clause(sql, p, q_type, "q.type")
        sql, p = _append_tag_clause(sql, p, tag_ids)
        row = db.session.execute(sa_text(sql), p).fetchone()
        if row:
            m = row._mapping
            ans = int(m["answered"] or 0)
            cor = int(m["correct"] or 0)
            a7 = int(m["answered_7d"] or 0)
            c7 = int(m["correct_7d"] or 0)
            a30 = int(m["answered_30d"] or 0)
            c30 = int(m["correct_30d"] or 0)
            data_answer = {
                "answered": ans, "correct": cor, "accuracy": _pct(cor, ans),
                "answered_7d": a7, "correct_7d": c7, "accuracy_7d": _pct(c7, a7),
                "answered_30d": a30, "correct_30d": c30, "accuracy_30d": _pct(c30, a30),
            }
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 答题统计查询失败: {e}')

    # ── 近 14 天活动趋势 ──
    data_activity: list = []
    try:
        sql = f"""
            SELECT DATE(a.created_at) AS day,
                   COUNT(*) AS total,
                   SUM(CASE WHEN a.is_correct = true THEN 1 ELSE 0 END) AS correct
            FROM {ans_table} a {q_join}
            WHERE {base_where} AND a.created_at >= :d14
        """
        p = {**base_params, "d14": today - timedelta(days=13)}
        sql, p = _append_type_clause(sql, p, q_type, "q.type")
        sql, p = _append_tag_clause(sql, p, tag_ids)
        sql += " GROUP BY DATE(a.created_at) ORDER BY day"
        rows = db.session.execute(sa_text(sql), p).fetchall()
        day_map: dict = {}
        for r in rows or []:
            m = r._mapping
            d = m["day"]
            if d:
                ds = str(d) if not isinstance(d, str) else d
                day_map[ds] = {"total": int(m["total"] or 0), "correct": int(m["correct"] or 0)}
        max_total = 1
        for i in range(14):
            d = today - timedelta(days=13 - i)
            ds = str(d)
            info = day_map.get(ds, {"total": 0, "correct": 0})
            if info["total"] > max_total:
                max_total = info["total"]
            data_activity.append({"day": ds, **info})
        for item in data_activity:
            item["pct"] = int(round(item["total"] * 100.0 / max_total, 0)) if max_total else 0
            item["acc"] = _pct(item["correct"], item["total"])
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 近14天活动趋势查询失败: {e}')
        data_activity = []

    # ── 收藏统计 ──
    data_fav = {"count": 0, "new_7d": 0, "new_30d": 0}
    try:
        fav_join = f"JOIN {q_table} q ON f.question_id = q.id" + (" LEFT JOIN subjects s ON q.subject_id = s.id" if source_type == "public" else "")
        fav_where = ("(s.is_locked=false OR s.is_locked IS NULL) AND q.subject_id = :subject_id" if source_type == "public" else "q.bank_id = :bank_id")
        sql = f"""
            SELECT
              COUNT(*) AS cnt,
              SUM(CASE WHEN f.created_at >= :d7 THEN 1 ELSE 0 END) AS new_7d,
              SUM(CASE WHEN f.created_at >= :d30 THEN 1 ELSE 0 END) AS new_30d
            FROM {fav_table} f {fav_join}
            WHERE f.user_id = :uid AND {fav_where}
        """
        p = {**q_params, "uid": uid, "d7": today - timedelta(days=7), "d30": today - timedelta(days=30)}
        sql, p = _append_type_clause(sql, p, q_type, "q.type")
        sql, p = _append_tag_clause(sql, p, tag_ids)
        row = db.session.execute(sa_text(sql), p).fetchone()
        if row:
            m = row._mapping
            data_fav = {"count": int(m["cnt"] or 0), "new_7d": int(m["new_7d"] or 0), "new_30d": int(m["new_30d"] or 0)}
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 收藏统计查询失败: {e}')

    # ── 错题统计 ──
    data_mis = {"count": 0, "times": 0, "new_7d": 0, "new_30d": 0, "active_7d": 0}
    try:
        mis_join = f"JOIN {q_table} q ON m.question_id = q.id" + (" LEFT JOIN subjects s ON q.subject_id = s.id" if source_type == "public" else "")
        mis_where = ("(s.is_locked=false OR s.is_locked IS NULL) AND q.subject_id = :subject_id" if source_type == "public" else "q.bank_id = :bank_id")
        sql = f"""
            SELECT
              COUNT(*) AS cnt,
              SUM(COALESCE(m.wrong_count, 1)) AS times,
              SUM(CASE WHEN m.created_at >= :d7 THEN 1 ELSE 0 END) AS new_7d,
              SUM(CASE WHEN m.created_at >= :d30 THEN 1 ELSE 0 END) AS new_30d,
              SUM(CASE WHEN m.updated_at >= :d7 THEN 1 ELSE 0 END) AS active_7d
            FROM {mis_table} m {mis_join}
            WHERE m.user_id = :uid AND {mis_where}
        """
        p = {**q_params, "uid": uid, "d7": today - timedelta(days=7), "d30": today - timedelta(days=30)}
        sql, p = _append_type_clause(sql, p, q_type, "q.type")
        sql, p = _append_tag_clause(sql, p, tag_ids)
        row = db.session.execute(sa_text(sql), p).fetchone()
        if row:
            m = row._mapping
            data_mis = {
                "count": int(m["cnt"] or 0), "times": int(m["times"] or 0),
                "new_7d": int(m["new_7d"] or 0), "new_30d": int(m["new_30d"] or 0),
                "active_7d": int(m["active_7d"] or 0),
            }
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 错题统计查询失败: {e}')

    # ── 状态分布（已掌握 / 已做未掌握 / 未做）──
    data_state = {
        "total": 0, "answered": 0, "correct": 0, "wrong": 0, "unanswered": 0,
        "pct_correct": 0.0, "pct_wrong": 0.0, "pct_unanswered": 0.0,
    }
    try:
        if source_type == "public":
            state_sql = f"""
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END) AS answered,
                  SUM(CASE WHEN a.is_correct = true THEN 1 ELSE 0 END) AS correct
                FROM {q_table} q
                LEFT JOIN subjects s ON q.subject_id = s.id
                LEFT JOIN {ans_table} a ON a.question_id = q.id AND a.user_id = :uid
                LEFT JOIN {fav_table} f ON f.question_id = q.id AND f.user_id = :uid2
                LEFT JOIN {mis_table} m ON m.question_id = q.id AND m.user_id = :uid3
                WHERE {q_where}
            """
            p = {**q_params, "uid": uid, "uid2": uid, "uid3": uid}
        else:
            state_sql = f"""
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END) AS answered,
                  SUM(CASE WHEN a.is_correct = true THEN 1 ELSE 0 END) AS correct
                FROM {q_table} q
                LEFT JOIN {ans_table} a ON a.question_id = q.id AND a.user_id = :uid
                LEFT JOIN {fav_table} f ON f.question_id = q.id AND f.user_id = :uid2
                LEFT JOIN {mis_table} m ON m.question_id = q.id AND m.user_id = :uid3
                WHERE {q_where}
            """
            p = {**q_params, "uid": uid, "uid2": uid, "uid3": uid}

        if kind == "favorites":
            state_sql += " AND f.id IS NOT NULL"
        elif kind == "mistakes":
            state_sql += " AND m.id IS NOT NULL"
        state_sql, p = _append_type_clause(state_sql, p, q_type, "q.type")
        state_sql, p = _append_tag_clause(state_sql, p, tag_ids)
        row = db.session.execute(sa_text(state_sql), p).fetchone()
        if row:
            rm = row._mapping
            total = int(rm["total"] or 0)
            answered = int(rm["answered"] or 0)
            correct = int(rm["correct"] or 0)
            wrong = answered - correct
            unanswered = total - answered
            data_state = {
                "total": total, "answered": answered, "correct": correct,
                "wrong": wrong, "unanswered": unanswered,
                "pct_correct": _pct(correct, total),
                "pct_wrong": _pct(wrong, total),
                "pct_unanswered": _pct(unanswered, total),
            }
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 状态分布查询失败: {e}')

    # ── 错题次数分桶 ──
    mistake_buckets: list = []
    try:
        if data_mis["count"] > 0:
            mis_join = f"JOIN {q_table} q ON m.question_id = q.id" + (" LEFT JOIN subjects s ON q.subject_id = s.id" if source_type == "public" else "")
            mis_where = ("(s.is_locked=false OR s.is_locked IS NULL) AND q.subject_id = :subject_id" if source_type == "public" else "q.bank_id = :bank_id")
            sql = f"""
                SELECT
                  CASE
                    WHEN COALESCE(m.wrong_count, 1) = 1 THEN '1'
                    WHEN COALESCE(m.wrong_count, 1) = 2 THEN '2'
                    WHEN COALESCE(m.wrong_count, 1) = 3 THEN '3'
                    ELSE '4+'
                  END AS bucket,
                  COUNT(*) AS cnt
                FROM {mis_table} m {mis_join}
                WHERE m.user_id = :uid AND {mis_where}
            """
            p = {**q_params, "uid": uid}
            sql, p = _append_type_clause(sql, p, q_type, "q.type")
            sql, p = _append_tag_clause(sql, p, tag_ids)
            sql += " GROUP BY bucket ORDER BY bucket"
            rows = db.session.execute(sa_text(sql), p).fetchall()
            bucket_map = {"1": 0, "2": 0, "3": 0, "4+": 0}
            for r in rows or []:
                rm = r._mapping
                bucket_map[str(rm["bucket"])] = int(rm["cnt"] or 0)
            max_b = max(bucket_map.values(), default=1) or 1
            labels = {"1": "错 1 次", "2": "错 2 次", "3": "错 3 次", "4+": "错 4+ 次"}
            for k in ("1", "2", "3", "4+"):
                mistake_buckets.append({
                    "label": labels[k], "count": bucket_map[k],
                    "pct": int(round(bucket_map[k] * 100.0 / max_b, 0)),
                })
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 错题次数分桶查询失败: {e}')
        mistake_buckets = []

    # ── 标签分布 ──
    tag_dist: list = []
    try:
        if tags:
            tag_names = [t["name"] if isinstance(t, dict) else str(t) for t in tags]
            if source_type == "public":
                tag_qids = _load_public_tag_qids(uid, tag_names)
            else:
                tag_qids = _load_bank_tag_qids(uid, bank_id, tag_names)
            max_tc = 1
            for tname, qids in tag_qids.items():
                if qids:
                    cnt = len(qids)
                    if cnt > max_tc:
                        max_tc = cnt
            for tname, qids in tag_qids.items():
                cnt = len(qids) if qids else 0
                if cnt == 0:
                    continue
                tag_dist.append({
                    "name": tname, "count": cnt,
                    "pct": int(round(cnt * 100.0 / max_tc, 0)) if max_tc else 0,
                    "switch_url": _url_with_params(base_url, {**ctx, "tab": "data", "type": q_type, "tag": tname}),
                })
            tag_dist.sort(key=lambda x: -x["count"])
            tag_dist = tag_dist[:15]
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 标签分布查询失败: {e}')
        tag_dist = []

    # ── 快捷清单（最近收藏 Top 8 / 高频错题 Top 8）──
    data_items: list = []
    try:
        if kind == "favorites":
            fav_join = f"JOIN {q_table} q ON f.question_id = q.id" + (" LEFT JOIN subjects s ON q.subject_id = s.id" if source_type == "public" else "")
            fav_where = ("(s.is_locked=false OR s.is_locked IS NULL) AND q.subject_id = :subject_id" if source_type == "public" else "q.bank_id = :bank_id")
            sql = f"""
                SELECT q.id, q.type AS p_type, f.created_at
                FROM {fav_table} f {fav_join}
                WHERE f.user_id = :uid AND {fav_where}
            """
            p = {**q_params, "uid": uid}
            sql, p = _append_type_clause(sql, p, q_type, "q.type")
            sql, p = _append_tag_clause(sql, p, tag_ids)
            sql += " ORDER BY f.created_at DESC LIMIT 8"
            rows = db.session.execute(sa_text(sql), p).fetchall()
            for r in rows or []:
                rm = r._mapping
                qt = portable_type_to_q_type(str(rm["p_type"] or ""))
                preview = _build_preview(source_type, int(rm["id"]))
                data_items.append({
                    "title": preview or f"题目 #{rm['id']}",
                    "q_type": qt or "未知",
                    "meta": f"收藏于 {str(rm['created_at'] or '')[:10]}",
                    "practice_url": _url_with_params(base_url, {**ctx, "tab": "practice", "type": qt or "all", "tag": tag}),
                })
        elif kind == "mistakes":
            mis_join = f"JOIN {q_table} q ON m.question_id = q.id" + (" LEFT JOIN subjects s ON q.subject_id = s.id" if source_type == "public" else "")
            mis_where = ("(s.is_locked=false OR s.is_locked IS NULL) AND q.subject_id = :subject_id" if source_type == "public" else "q.bank_id = :bank_id")
            sql = f"""
                SELECT q.id, q.type AS p_type, COALESCE(m.wrong_count, 1) AS wc
                FROM {mis_table} m {mis_join}
                WHERE m.user_id = :uid AND {mis_where}
            """
            p = {**q_params, "uid": uid}
            sql, p = _append_type_clause(sql, p, q_type, "q.type")
            sql, p = _append_tag_clause(sql, p, tag_ids)
            sql += " ORDER BY wc DESC, m.updated_at DESC LIMIT 8"
            rows = db.session.execute(sa_text(sql), p).fetchall()
            for r in rows or []:
                rm = r._mapping
                qt = portable_type_to_q_type(str(rm["p_type"] or ""))
                preview = _build_preview(source_type, int(rm["id"]))
                data_items.append({
                    "title": preview or f"题目 #{rm['id']}",
                    "q_type": qt or "未知",
                    "meta": f"错 {int(rm['wc'] or 1)} 次",
                    "practice_url": _url_with_params(base_url, {**ctx, "tab": "practice", "type": qt or "all", "tag": tag}),
                })
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 快捷清单查询失败: {e}')
        data_items = []

    # ── 建议 tips ──
    data_tips: list = []
    try:
        ans = data_answer["answered"]
        acc = data_answer["accuracy"]
        if ans == 0:
            data_tips.append("还没有做过题，开始刷题吧！")
        else:
            if acc < 60:
                data_tips.append(f"当前正确率 {acc}%，建议先回顾错题再继续新题。")
            elif acc < 80:
                data_tips.append(f"正确率 {acc}%，继续保持！可以尝试打乱题目顺序加强记忆。")
            if data_mis["count"] > 0 and data_mis["active_7d"] > 3:
                data_tips.append(f"近 7 天有 {data_mis['active_7d']} 道活跃错题，建议优先处理高频错题。")
            if kind == "favorites" and data_fav["count"] > 10 and data_fav["new_7d"] == 0:
                data_tips.append("近 7 天没有新收藏，试试用背题模式复习已收藏的题目。")
            if kind == "tags" and not tag_dist:
                data_tips.append("当前范围暂无标签数据，选择一个标签后再查看会更清晰。")
    except Exception as e:
        current_app.logger.warning(f'load_data_tab 建议tips生成失败: {e}')
        data_tips = []

    return {
        "data_answer": data_answer,
        "data_activity": data_activity,
        "data_fav": data_fav,
        "data_mis": data_mis,
        "data_tips": data_tips,
        "data_state": data_state,
        "mistake_buckets": mistake_buckets,
        "tag_dist": tag_dist,
        "data_items": data_items,
    }


# ── 标签 → 题目 ID 映射辅助 ─────────────────────────────


def _load_public_tag_qids(uid: int, tag_names: list[str]) -> dict[str, list[int]]:
    """加载公共题库中各标签对应的题目 ID 列表。"""
    result: dict[str, list[int]] = {}
    try:
        from app.modules.quiz.services.question_tags_service import get_user_question_tags_map
        tags_map = get_user_question_tags_map(db.session, int(uid))
        for tname in tag_names:
            qids = [int(qid) for qid, tlist in (tags_map or {}).items() if tname in (tlist or [])]
            result[tname] = qids
    except Exception:
        for tname in tag_names:
            result[tname] = []
    return result


def _load_bank_tag_qids(uid: int, bank_id: int, tag_names: list[str]) -> dict[str, list[int]]:
    """加载个人题库中各标签对应的题目 ID 列表。"""
    result: dict[str, list[int]] = {}
    try:
        from app.modules.user_bank.routes.api import _load_bank_tag_store
        store = _load_bank_tag_store(db.session, int(bank_id), int(uid))
        qt = store.get("question_tags") or {}
        for tname in tag_names:
            qids = [int(qid) for qid, tlist in qt.items() if tname in (tlist or [])]
            result[tname] = qids
    except Exception:
        for tname in tag_names:
            result[tname] = []
    return result
