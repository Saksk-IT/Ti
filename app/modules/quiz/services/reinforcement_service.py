# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter, defaultdict
import json
import difflib
import re
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from sqlalchemy import text as sa_text

from app.core.extensions import db
from app.core.utils.options_parser import parse_options


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def similarity_ratio(text1: str, text2: str) -> float:
    a = normalize_text(text1)
    b = normalize_text(text2)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return float(difflib.SequenceMatcher(None, a, b).ratio())


def options_to_text(raw_options) -> str:
    if not raw_options:
        return ""
    try:
        opts = parse_options(raw_options) or []
    except Exception:
        opts = []
    parts: List[str] = []
    for opt in opts:
        try:
            v = (opt or {}).get("value")
        except Exception:
            v = None
        if v is None:
            continue
        v = str(v).strip()
        if not v:
            continue
        parts.append(v)
    parts.sort(key=normalize_text)
    return " ".join(parts)
# __CONTINUE_HERE__


def pick_anchors(text: str, max_anchors: int = 6) -> List[str]:
    norm = normalize_text(text).replace(" ", "")
    if len(norm) < 4:
        return []

    stop = {
        "以下", "下列", "关于", "哪项", "什么", "的是", "属于", "可以",
        "不能", "不可以", "主要", "描述", "说法", "正确", "错误", "符合", "不符合",
    }

    def _good(s: str) -> bool:
        if not s or s in stop:
            return False
        if re.fullmatch(r"[\W_]+", s):
            return False
        return True

    anchors: List[str] = []
    seen = set()
    positions = sorted({0, max(0, len(norm) // 4), max(0, len(norm) // 2), max(0, (len(norm) * 3) // 4), max(0, len(norm) - 3)})
    for p in positions:
        s = norm[p : p + 3]
        if len(s) == 3 and _good(s) and s not in seen:
            seen.add(s)
            anchors.append(s)
        if len(anchors) >= max_anchors:
            return anchors[:max_anchors]

    positions2 = sorted({0, max(0, len(norm) // 3), max(0, (len(norm) * 2) // 3), max(0, len(norm) - 2)})
    for p in positions2:
        s = norm[p : p + 2]
        if len(s) == 2 and _good(s) and s not in seen:
            seen.add(s)
            anchors.append(s)
        if len(anchors) >= max_anchors:
            break

    return anchors[:max_anchors]


def _dedup_keep_order(items: Iterable[int]) -> List[int]:
    seen = set()
    out: List[int] = []
    for x in items:
        try:
            v = int(x)
        except Exception:
            continue
        if v <= 0 or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out
# __CONTINUE_HERE2__


def _build_named_in(prefix: str, values: list) -> tuple[str, dict]:
    """构建命名参数 IN 子句"""
    params = {}
    names = []
    for i, v in enumerate(values):
        key = f"{prefix}_{i}"
        params[key] = v
        names.append(f":{key}")
    return ", ".join(names), params


def _load_similar_pairs_cache(
    conn, *, source: str, scope_id: int, version: str,
) -> Optional[List[Tuple[int, int, float, float]]]:
    try:
        row = conn.execute(
            sa_text("SELECT version, pairs_json FROM reinforce_similar_cache WHERE source = :source AND scope_id = :scope_id"),
            {"source": str(source), "scope_id": int(scope_id)},
        ).fetchone()
    except Exception:
        return None

    if not row:
        return None
    if str(row._mapping["version"] or "") != str(version or ""):
        return None

    raw = row._mapping["pairs_json"] or ""
    if not raw:
        return None

    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, list):
        return None

    out: List[Tuple[int, int, float, float]] = []
    for it in data:
        if not isinstance(it, (list, tuple)) or len(it) < 2:
            continue
        try:
            a = int(it[0])
            b = int(it[1])
            stem = float(it[2]) if len(it) >= 3 else 0.0
            opt = float(it[3]) if len(it) >= 4 else 0.0
        except Exception:
            continue
        if a <= 0 or b <= 0:
            continue
        out.append((a, b, stem, opt))
    return out


def _save_similar_pairs_cache(
    conn, *, source: str, scope_id: int, version: str,
    pairs: Sequence[Tuple[int, int, float, float]],
) -> None:
    try:
        payload = json.dumps([[int(a), int(b), float(stem), float(opt)] for a, b, stem, opt in pairs], ensure_ascii=False)
    except Exception:
        payload = "[]"

    try:
        conn.execute(
            sa_text("""
            INSERT INTO reinforce_similar_cache (source, scope_id, version, pairs_json, pairs_count, computed_at, updated_at)
            VALUES (:source, :scope_id, :version, :payload, :pairs_count, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(source, scope_id) DO UPDATE SET
              version = excluded.version,
              pairs_json = excluded.pairs_json,
              pairs_count = excluded.pairs_count,
              computed_at = CURRENT_TIMESTAMP,
              updated_at = CURRENT_TIMESTAMP
            """),
            {"source": str(source), "scope_id": int(scope_id), "version": str(version),
             "payload": payload, "pairs_count": int(len(pairs) if pairs else 0)},
        )
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
# __CONTINUE_HERE3__


def _ids_from_pairs(pairs: Sequence[Tuple[int, int, float, float]], max_total_ids: int) -> List[int]:
    max_total_ids = max(0, int(max_total_ids or 0))
    if max_total_ids <= 0:
        return []
    ids: List[int] = []
    seen: Set[int] = set()
    for a, b, _stem, _opt in pairs or []:
        for x in (int(a), int(b)):
            if x in seen:
                continue
            seen.add(x)
            ids.append(x)
            if len(ids) >= max_total_ids:
                return ids
    return ids


def _ratio_norm(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return float(difflib.SequenceMatcher(None, a, b).ratio())


def _fetch_seed_map(conn, table: str, scope_col: str, scope_id: int, seed_ids: Sequence[int]) -> dict:
    """通用：获取 seed 题目的 id/content/options 映射"""
    seed_ids = _dedup_keep_order(seed_ids)
    if not seed_ids:
        return {}
    in_str, in_params = _build_named_in("sid", seed_ids)
    params = {"scope_id": int(scope_id)}
    params.update(in_params)
    rows = conn.execute(
        sa_text(f"SELECT id, content, options FROM {table} WHERE {scope_col} = :scope_id AND id IN ({in_str})"),
        params,
    ).fetchall()
    out = {}
    for r in rows or []:
        try:
            d = dict(r._mapping)
        except Exception:
            continue
        rid = d.get("id")
        if rid is None:
            continue
        try:
            out[int(rid)] = d
        except Exception:
            continue
    return out


def _fetch_public_seed_map(conn, subject_id: int, seed_ids: Sequence[int]) -> dict:
    return _fetch_seed_map(conn, "questions", "subject_id", subject_id, seed_ids)


def _fetch_user_bank_seed_map(conn, bank_id: int, seed_ids: Sequence[int]) -> dict:
    return _fetch_seed_map(conn, "user_bank_questions", "bank_id", bank_id, seed_ids)
# __CONTINUE_HERE4__


def _fetch_candidates_by_anchors(
    conn, table: str, where_prefix_sql: str, where_prefix_params: dict,
    seed_id: int, anchors: Sequence[str], limit: int,
) -> List[dict]:
    limit = max(1, min(int(limit or 600), 1200))
    anchors = [str(a) for a in (anchors or []) if a]

    params: dict = dict(where_prefix_params)
    params["_seed_id"] = int(seed_id)
    params["_limit"] = limit

    cond_parts: List[str] = []
    for i, a in enumerate(anchors[:12]):
        ck = f"_like_c_{i}"
        ok = f"_like_o_{i}"
        cond_parts.append(f"content LIKE :{ck}")
        params[ck] = f"%{a}%"
        cond_parts.append(f"options LIKE :{ok}")
        params[ok] = f"%{a}%"

    if not cond_parts:
        sql = f"SELECT id, content, options FROM {table} WHERE {where_prefix_sql} AND id != :_seed_id ORDER BY id DESC LIMIT :_limit"
        return [dict(r._mapping) for r in conn.execute(sa_text(sql), params).fetchall()]

    or_sql = " OR ".join(cond_parts)
    sql = f"SELECT id, content, options FROM {table} WHERE {where_prefix_sql} AND id != :_seed_id AND ({or_sql}) LIMIT :_limit"
    rows = conn.execute(sa_text(sql), params).fetchall()
    if rows:
        return [dict(r._mapping) for r in rows]

    sql2 = f"SELECT id, content, options FROM {table} WHERE {where_prefix_sql} AND id != :_seed_id ORDER BY id DESC LIMIT :_limit"
    # 去掉 LIKE 参数，只保留基础参数
    base_params = dict(where_prefix_params)
    base_params["_seed_id"] = int(seed_id)
    base_params["_limit"] = limit
    return [dict(r._mapping) for r in conn.execute(sa_text(sql2), base_params).fetchall()]
# __CONTINUE_HERE5__


def _rank_candidates(
    seed_content: str, seed_options, candidates: Sequence[dict],
    exclude_ids: Set[int], stem_threshold: float, option_threshold: float,
) -> List[Tuple[int, float, float]]:
    seed_content_norm = normalize_text(seed_content)
    seed_opt_norm = normalize_text(options_to_text(seed_options))

    ranked: List[Tuple[int, float, float]] = []
    for r in candidates or []:
        try:
            cid = int(r.get("id") or 0)
        except Exception:
            cid = 0
        if cid <= 0 or cid in exclude_ids:
            continue
        c_content = r.get("content") or ""
        c_content_norm = normalize_text(c_content)
        if not c_content_norm:
            continue
        stem_sim = _ratio_norm(seed_content_norm, c_content_norm)
        opt_sim = 0.0
        if seed_opt_norm:
            c_opt_norm = normalize_text(options_to_text(r.get("options")))
            if c_opt_norm:
                opt_sim = _ratio_norm(seed_opt_norm, c_opt_norm)
        if stem_sim < stem_threshold and opt_sim < option_threshold:
            continue
        ranked.append((cid, stem_sim, opt_sim))

    def _sort_key(item: Tuple[int, float, float]):
        _cid, stem_sim, opt_sim = item
        stem_hit = 1 if stem_sim >= stem_threshold else 0
        if stem_hit:
            return (1, stem_sim, opt_sim)
        return (0, opt_sim, stem_sim)

    ranked.sort(key=_sort_key, reverse=True)
    return ranked


def _find_similar_training_ids(
    conn, table: str, scope_col: str, scope_id: int,
    fetch_seed_map_fn, *, seed_ids: Sequence[int],
    exclude_ids: Optional[Set[int]] = None, per_seed: int = 3,
    max_total: int = 30, candidate_limit: int = 700,
    stem_threshold: float = 0.62, option_threshold: float = 0.72,
) -> List[int]:
    seed_ids = _dedup_keep_order(seed_ids)
    if not seed_ids:
        return []
    per_seed = max(1, min(int(per_seed or 3), 10))
    max_total = max(1, min(int(max_total or 30), 200))
    exclude_ids = set([int(x) for x in (exclude_ids or set()) if x is not None])

    seed_map = fetch_seed_map_fn(conn, int(scope_id), seed_ids)
    if not seed_map:
        return []

    out: List[int] = []
    used = set(exclude_ids)

    for sid in seed_ids:
        if len(out) >= max_total:
            break
        seed = seed_map.get(int(sid))
        if not seed:
            continue
        if int(sid) not in out:
            out.append(int(sid))
        used.add(int(sid))

        anchors = pick_anchors(seed.get("content") or "", max_anchors=6)
        anchors += pick_anchors(options_to_text(seed.get("options")), max_anchors=4)

        candidates = _fetch_candidates_by_anchors(
            conn, table=table,
            where_prefix_sql=f"{scope_col} = :scope_id",
            where_prefix_params={"scope_id": int(scope_id)},
            seed_id=int(sid), anchors=anchors, limit=candidate_limit,
        )
        ranked = _rank_candidates(
            seed.get("content") or "", seed.get("options"),
            candidates, exclude_ids=used,
            stem_threshold=stem_threshold, option_threshold=option_threshold,
        )
        picked = 0
        for cid, _stem_sim, _opt_sim in ranked:
            if len(out) >= max_total:
                break
            if cid in used:
                continue
            out.append(cid)
            used.add(cid)
            picked += 1
            if picked >= per_seed:
                break

    return out[:max_total]
# __CONTINUE_HERE6__


def find_similar_training_ids_public(conn, subject_id: int, **kwargs) -> List[int]:
    return _find_similar_training_ids(
        conn, "questions", "subject_id", subject_id,
        _fetch_public_seed_map, **kwargs,
    )


def find_similar_training_ids_user_bank(conn, bank_id: int, **kwargs) -> List[int]:
    return _find_similar_training_ids(
        conn, "user_bank_questions", "bank_id", bank_id,
        _fetch_user_bank_seed_map, **kwargs,
    )


def _find_similar_pairs(
    conn, table: str, scope_col: str, scope_id: int,
    source_label: str, ts_col: str,
    *, max_total_ids: int = 30, max_pairs: Optional[int] = None,
    candidate_limit: int = 500, stem_threshold: float = 0.62,
    option_threshold: float = 0.72,
) -> Tuple[List[int], int, List[Tuple[int, int, float, float]]]:
    """通用相似题对查找"""
    try:
        scope_id = int(scope_id)
    except Exception:
        return ([], 0, [])
    max_total_ids = max(0, min(int(max_total_ids or 0), 200))
    if max_total_ids <= 0:
        return ([], 0, [])

    if max_pairs is None:
        max_pairs = (max_total_ids + 1) // 2
    max_pairs = max(0, min(int(max_pairs or 0), 300))
    if max_pairs <= 0:
        return ([], 0, [])

    candidate_limit = max(20, min(int(candidate_limit or 500), 1200))
    cache_pairs_limit = 300

    cnt = 0
    max_id = 0
    max_ts = ""
    try:
        fp = conn.execute(
            sa_text(f"SELECT COUNT(1) AS cnt, MAX(id) AS max_id, MAX({ts_col}) AS max_ts FROM {table} WHERE {scope_col} = :scope_id"),
            {"scope_id": scope_id},
        ).fetchone()
        if fp:
            cnt = int(fp._mapping["cnt"] or 0)
            max_id = int(fp._mapping["max_id"] or 0)
            max_ts = str(fp._mapping["max_ts"] or "")
    except Exception:
        pass
    version = (
        f"sim_v1|src={source_label}|scope={scope_id}|cnt={cnt}|max_id={max_id}|ts={max_ts}"
        f"|cand={candidate_limit}|stem={float(stem_threshold):.3f}|opt={float(option_threshold):.3f}|pairs={cache_pairs_limit}"
    )

    cached_pairs = _load_similar_pairs_cache(conn, source=source_label, scope_id=scope_id, version=version)
    if cached_pairs is not None:
        picked_pairs = list(cached_pairs[:max_pairs])
        ids = _ids_from_pairs(picked_pairs, max_total_ids)
        return (ids, len(picked_pairs), picked_pairs)
# __CONTINUE_HERE7__

    try:
        rows = conn.execute(
            sa_text(f"SELECT id, content, options FROM {table} WHERE {scope_col} = :scope_id ORDER BY id ASC"),
            {"scope_id": scope_id},
        ).fetchall()
    except Exception:
        rows = []
    if not rows:
        _save_similar_pairs_cache(conn, source=source_label, scope_id=scope_id, version=version, pairs=[])
        return ([], 0, [])

    items: List[Dict] = []
    id_to_item: Dict[int, Dict] = {}
    for r in rows:
        try:
            d = dict(r._mapping)
        except Exception:
            continue
        try:
            qid = int(d.get("id") or 0)
        except Exception:
            qid = 0
        if qid <= 0:
            continue
        content = d.get("content") or ""
        if not normalize_text(content):
            continue
        opt_text = options_to_text(d.get("options"))
        item = {
            "id": qid,
            "content_norm": normalize_text(content),
            "opt_norm": normalize_text(opt_text),
            "anchors": [],
        }
        anchors = pick_anchors(content, max_anchors=6)
        if opt_text:
            anchors += pick_anchors(opt_text, max_anchors=4)
        seen_a: set = set()
        uniq: List[str] = []
        for a in anchors:
            a = str(a or "").strip()
            if not a or a in seen_a:
                continue
            seen_a.add(a)
            uniq.append(a)
        item["anchors"] = uniq
        items.append(item)
        id_to_item[qid] = item

    if len(items) < 2:
        _save_similar_pairs_cache(conn, source=source_label, scope_id=scope_id, version=version, pairs=[])
        return ([], 0, [])
# __CONTINUE_HERE8__

    anchor_index: Dict[str, List[int]] = defaultdict(list)
    for it in items:
        qid = int(it["id"])
        for a in it.get("anchors") or []:
            anchor_index[a].append(qid)

    def _pair_key(stem_sim: float, opt_sim: float) -> Tuple[int, float, float]:
        stem_hit = 1 if stem_sim >= stem_threshold else 0
        if stem_hit:
            return (1, float(stem_sim), float(opt_sim))
        return (0, float(opt_sim), float(stem_sim))

    best_pairs: Dict[Tuple[int, int], Tuple[float, float]] = {}

    for seed in items:
        sid = int(seed["id"])
        s_anchors = seed.get("anchors") or []
        if not s_anchors:
            continue

        counter = Counter()
        for a in s_anchors[:16]:
            counter.update(anchor_index.get(a, []))
        if sid in counter:
            del counter[sid]
        if not counter:
            continue

        cand_ids = [cid for cid, _cnt in counter.most_common(candidate_limit)]
        seed_content = seed.get("content_norm") or ""
        seed_opt = seed.get("opt_norm") or ""

        best_cid = 0
        best_stem = 0.0
        best_opt = 0.0
        best_k = (0, 0.0, 0.0)

        for cid in cand_ids:
            it2 = id_to_item.get(int(cid))
            if not it2:
                continue
            s_sim = _ratio_norm(seed_content, it2.get("content_norm") or "")
            o_sim = 0.0
            if seed_opt and it2.get("opt_norm"):
                o_sim = _ratio_norm(seed_opt, it2.get("opt_norm") or "")
            if s_sim < stem_threshold and o_sim < option_threshold:
                continue
            k = _pair_key(s_sim, o_sim)
            if k > best_k:
                best_k = k
                best_cid = int(cid)
                best_stem = float(s_sim)
                best_opt = float(o_sim)

        if best_cid <= 0:
            continue
        a, b = (sid, best_cid) if sid < best_cid else (best_cid, sid)
        cur = best_pairs.get((a, b))
        if not cur or _pair_key(best_stem, best_opt) > _pair_key(cur[0], cur[1]):
            best_pairs[(a, b)] = (best_stem, best_opt)

    if not best_pairs:
        _save_similar_pairs_cache(conn, source=source_label, scope_id=scope_id, version=version, pairs=[])
        return ([], 0, [])

    pairs_sorted: List[Tuple[int, int, float, float]] = sorted(
        ((a, b, v[0], v[1]) for (a, b), v in best_pairs.items()),
        key=lambda x: _pair_key(x[2], x[3]),
        reverse=True,
    )
    pairs_cache = pairs_sorted[:cache_pairs_limit]
    _save_similar_pairs_cache(conn, source=source_label, scope_id=scope_id, version=version, pairs=pairs_cache)

    picked_pairs = list(pairs_cache[:max_pairs])
    ids = _ids_from_pairs(picked_pairs, max_total_ids)
    return (ids, len(picked_pairs), picked_pairs)
# __CONTINUE_FINAL__


def find_similar_pairs_user_bank(conn, bank_id: int, **kwargs):
    return _find_similar_pairs(
        conn, "user_bank_questions", "bank_id", bank_id,
        "user_bank", "updated_at", **kwargs,
    )


def find_similar_pairs_public(conn, subject_id: int, **kwargs):
    return _find_similar_pairs(
        conn, "questions", "subject_id", subject_id,
        "public", "created_at", **kwargs,
    )
