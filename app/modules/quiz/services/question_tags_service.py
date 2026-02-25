# -*- coding: utf-8 -*-
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text

from app.core.utils.user_question_tags import (
    SCOPE_QUESTION_CENTER,
    delete_user_tag as _uq_delete_user_tag,
    ensure_tag_tables,
    ensure_user_tag_exists as _ensure_user_tag_exists,
    get_question_ids_by_tag as _uq_get_question_ids_by_tag,
    get_question_tags as _uq_get_question_tags,
    list_tags_with_counts as _list_tags_with_counts,
    set_question_tags as _uq_set_question_tags,
)

TAG_STORE_KEY = "question_tags_v1"
MAX_TAG_NAME_LEN = 20
MAX_TAGS_PER_USER = 200
MAX_TAGS_PER_QUESTION = 20


def _normalize_tag_name(name: Any) -> str:
    s = (name or "").strip()
    if not s:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip()
    if len(s) > MAX_TAG_NAME_LEN:
        s = s[:MAX_TAG_NAME_LEN].strip()
    return s


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "tags": [], "bindings": {}}


def _load_store_from_user_progress(conn, user_id: int) -> Dict[str, Any]:
    """旧实现：从 user_progress 读取标签 store（用于向新表迁移）。"""
    row = conn.execute(
        text("SELECT data FROM user_progress WHERE user_id = :user_id AND p_key = :p_key"),
        {"user_id": user_id, "p_key": TAG_STORE_KEY},
    ).fetchone()
    if not row:
        return _empty_store()

    try:
        data = row["data"]
    except Exception:
        data = None

    if not data:
        return _empty_store()

    try:
        raw = json.loads(data)
    except Exception:
        return _empty_store()

    if not isinstance(raw, dict):
        return _empty_store()

    tags = raw.get("tags")
    bindings = raw.get("bindings")
    store = {
        "version": 1,
        "tags": tags if isinstance(tags, list) else [],
        "bindings": bindings if isinstance(bindings, dict) else {},
    }
    return store


def _has_any_new_tags(conn, user_id: int) -> bool:
    try:
        ensure_tag_tables(conn)
        row = conn.execute(
            text("SELECT 1 FROM user_question_tag_items WHERE user_id = :user_id AND scope = :scope LIMIT 1"),
            {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _resolve_subject_id_from_question(conn, question_id: int) -> int:
    """从 questions 表解析该题所属 subject_id（失败返回 0）。"""
    try:
        row = conn.execute(text("SELECT subject_id FROM questions WHERE id = :qid"), {"qid": int(question_id)}).fetchone()
        sid = int(row._mapping["subject_id"] or 0) if row else 0
        return sid if sid > 0 else 0
    except Exception:
        return 0


def _ensure_migrated(conn, user_id: int) -> None:
    """若新表为空，则把历史 user_progress 标签迁移到 user_question_tag_items。"""
    if _has_any_new_tags(conn, user_id):
        return

    old = _load_store_from_user_progress(conn, user_id)
    tags = old.get("tags") if isinstance(old.get("tags"), list) else []
    bindings = old.get("bindings") if isinstance(old.get("bindings"), dict) else {}

    if not tags and not bindings:
        return

    # 说明：user_progress.tags（未绑定 tag）无法可靠归属到某个 subject，避免"全局污染"，这里不强行迁移。
    ensure_tag_tables(conn)
    if isinstance(bindings, dict):
        for qid_raw, tag_list in bindings.items():
            try:
                qid = int(qid_raw)
            except Exception:
                continue
            if qid <= 0:
                continue
            try:
                sid = _resolve_subject_id_from_question(conn, int(qid))
                if sid <= 0:
                    continue
                for t in (tag_list or []):
                    _ensure_user_tag_exists(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=int(sid), tag=t)
                _uq_set_question_tags(
                    conn,
                    user_id=int(user_id),
                    scope=SCOPE_QUESTION_CENTER,
                    scope_id=int(sid),
                    question_id=qid,
                    tags=tag_list,
                )
            except Exception:
                continue


def load_store(conn, user_id: int) -> Dict[str, Any]:
    """新实现：从 user_question_tag_items 读取，并保持旧 store 结构（tags + bindings）。

    说明：公共题库标签已升级为"用户 × subject_id"隔离；此函数返回跨 subject 的合并视图（兼容旧调用方）。
    """
    _ensure_migrated(conn, user_id)
    ensure_tag_tables(conn)

    # 优先读取 subject 维度（scope_id<>0）；若没有，则回退旧结构 scope_id=0
    use_scope0 = False
    try:
        row = conn.execute(
            text("SELECT 1 FROM user_question_tag_items WHERE user_id = :user_id AND scope = :scope AND scope_id <> 0 LIMIT 1"),
            {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
        ).fetchone()
        use_scope0 = row is None
    except Exception:
        use_scope0 = True

    tags: List[str] = []
    if use_scope0:
        tags_rows = _list_tags_with_counts(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=0)
        tags = [str(r.get("name") or "").strip() for r in (tags_rows or []) if str(r.get("name") or "").strip()]
    else:
        try:
            rows2 = conn.execute(
                text("""
                SELECT tag, SUM(CASE WHEN question_id>0 THEN 1 ELSE 0 END) AS cnt
                FROM user_question_tag_items
                WHERE user_id = :user_id AND scope = :scope AND scope_id <> 0
                GROUP BY tag
                ORDER BY cnt DESC, tag ASC
                """),
                {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
            ).fetchall()
            tags = [str(r._mapping["tag"] or "").strip() for r in (rows2 or []) if r and str(r._mapping["tag"] or "").strip()]
        except Exception:
            tags = []

    bindings: Dict[str, List[str]] = {}
    if use_scope0:
        rows = conn.execute(
            text("""
            SELECT question_id, tag
            FROM user_question_tag_items
            WHERE user_id = :user_id AND scope = :scope AND scope_id = :scope_id AND question_id > 0
            ORDER BY question_id ASC, tag ASC
            """),
            {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER), "scope_id": 0},
        ).fetchall()
    else:
        rows = conn.execute(
            text("""
            SELECT question_id, tag
            FROM user_question_tag_items
            WHERE user_id = :user_id AND scope = :scope AND scope_id <> 0 AND question_id > 0
            ORDER BY question_id ASC, tag ASC
            """),
            {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
        ).fetchall()
    for r in rows or []:
        try:
            qid = int(r._mapping["question_id"])
        except Exception:
            continue
        t = str(r._mapping["tag"] or "").strip()
        if not t or t.lower() == "all":
            continue
        bindings.setdefault(str(qid), [])
        if t not in bindings[str(qid)]:
            bindings[str(qid)].append(t)

    return {"version": 1, "tags": tags, "bindings": bindings}


def save_store(conn, user_id: int, store: Dict[str, Any]) -> None:
    """新实现：写回 user_question_tag_items（不再依赖 user_progress）。"""
    ensure_tag_tables(conn)

    # 全量覆盖：先清空该用户公共题库 tags（含占位行），再按 store 重建
    conn.execute(
        text("DELETE FROM user_question_tag_items WHERE user_id = :user_id AND scope = :scope AND scope_id = :scope_id"),
        {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER), "scope_id": 0},
    )

    tags = store.get("tags") if isinstance(store.get("tags"), list) else []
    for t in tags:
        _ensure_user_tag_exists(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=None, tag=t)

    bindings = store.get("bindings") if isinstance(store.get("bindings"), dict) else {}
    if isinstance(bindings, dict):
        for qid_raw, tag_list in bindings.items():
            try:
                qid = int(qid_raw)
            except Exception:
                continue
            if qid <= 0:
                continue
            _uq_set_question_tags(
                conn,
                user_id=int(user_id),
                scope=SCOPE_QUESTION_CENTER,
                scope_id=None,
                question_id=qid,
                tags=tag_list,
            )


def list_user_tags(conn, user_id: int, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """列出用户标签（公共题库）。

    - subject_id 指定时：仅返回该 subject（题库/科目）下的标签（实现"用户 × 题库"隔离）。
    - subject_id 为空：返回跨 subject 的合并视图（兼容旧调用方）。
    """
    _ensure_migrated(conn, user_id)
    ensure_tag_tables(conn)

    try:
        sid = int(subject_id) if subject_id is not None else 0
    except Exception:
        sid = 0

    if sid > 0:
        return _list_tags_with_counts(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=int(sid))

    # 合并视图：优先 subject 维度（scope_id<>0）；否则回退旧结构 scope_id=0
    try:
        row = conn.execute(
            text("SELECT 1 FROM user_question_tag_items WHERE user_id = :user_id AND scope = :scope AND scope_id <> 0 LIMIT 1"),
            {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
        ).fetchone()
        if row is not None:
            rows = conn.execute(
                text("""
                SELECT tag, SUM(CASE WHEN question_id>0 THEN 1 ELSE 0 END) AS cnt
                FROM user_question_tag_items
                WHERE user_id = :user_id AND scope = :scope AND scope_id <> 0
                GROUP BY tag
                ORDER BY cnt DESC, tag ASC
                """),
                {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER)},
            ).fetchall()
            return [{"name": str(r._mapping["tag"]), "count": int(r._mapping["cnt"])} for r in (rows or []) if r and r._mapping["tag"] is not None]
    except Exception:
        pass

    return _list_tags_with_counts(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=0)


def create_user_tag(conn, user_id: int, subject_id: int, name: Any) -> Tuple[bool, str, str]:
    tag = _normalize_tag_name(name)
    if not tag:
        return False, "标签名不能为空", ""
    if tag.lower() == "all":
        return False, "标签名不可用", ""

    try:
        sid = int(subject_id or 0)
    except Exception:
        sid = 0
    if sid <= 0:
        return False, "缺少科目/题库参数", ""

    _ensure_migrated(conn, user_id)

    existing_rows = _list_tags_with_counts(
        conn,
        user_id=int(user_id),
        scope=SCOPE_QUESTION_CENTER,
        scope_id=int(sid),
    )
    existing = [str(r.get("name") or "").strip() for r in (existing_rows or []) if str(r.get("name") or "").strip()]

    if tag in existing:
        return True, "已存在", tag

    if len(existing) >= MAX_TAGS_PER_USER:
        return False, f"标签数量已达上限（{MAX_TAGS_PER_USER}）", ""

    _ensure_user_tag_exists(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=int(sid), tag=tag)
    return True, "已创建", tag


def delete_user_tag(conn, user_id: int, subject_id: int, name: Any) -> Tuple[bool, str]:
    tag = _normalize_tag_name(name)
    if not tag:
        return False, "标签名不能为空"
    if tag.lower() == "all":
        return False, "标签名不可用"

    try:
        sid = int(subject_id or 0)
    except Exception:
        sid = 0
    if sid <= 0:
        return False, "缺少科目/题库参数"

    _ensure_migrated(conn, user_id)
    _uq_delete_user_tag(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=int(sid), tag=tag)
    return True, "已删除"


def get_question_tags(conn, user_id: int, question_id: int) -> List[str]:
    _ensure_migrated(conn, user_id)
    sid = _resolve_subject_id_from_question(conn, int(question_id))
    return _uq_get_question_tags(
        conn,
        user_id=int(user_id),
        scope=SCOPE_QUESTION_CENTER,
        scope_id=int(sid),
        question_id=int(question_id),
    )


def set_question_tags(conn, user_id: int, question_id: int, tags: Any) -> Tuple[bool, str, List[str]]:
    if tags is None:
        tags_list: List[Any] = []
    elif isinstance(tags, list):
        tags_list = tags
    else:
        tags_list = [tags]

    normalized: List[str] = []
    for t in tags_list:
        name = _normalize_tag_name(t)
        if not name or name.lower() == "all":
            continue
        if name not in normalized:
            normalized.append(name)
        if len(normalized) >= MAX_TAGS_PER_QUESTION:
            break

    _ensure_migrated(conn, user_id)
    sid = _resolve_subject_id_from_question(conn, int(question_id))

    # 确保 tag 定义存在（question_id=0），避免解绑后 tag 消失
    for t in normalized:
        try:
            _ensure_user_tag_exists(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=int(sid), tag=t)
        except Exception:
            continue
    cleaned = _uq_set_question_tags(
        conn,
        user_id=int(user_id),
        scope=SCOPE_QUESTION_CENTER,
        scope_id=int(sid),
        question_id=int(question_id),
        tags=normalized,
    )
    return True, "已更新", cleaned


def update_question_tags(
    conn,
    user_id: int,
    question_id: int,
    *,
    add: Optional[Any] = None,
    remove: Optional[Any] = None,
) -> Tuple[bool, str, List[str]]:
    cur = get_question_tags(conn, user_id, question_id)
    cur_set = list(cur)

    add_list: List[Any] = []
    if add is not None:
        add_list = add if isinstance(add, list) else [add]

    remove_list: List[Any] = []
    if remove is not None:
        remove_list = remove if isinstance(remove, list) else [remove]

    to_add: List[str] = []
    for t in add_list:
        name = _normalize_tag_name(t)
        if name and name not in cur_set and name.lower() != "all":
            to_add.append(name)

    to_remove: Set[str] = set()
    for t in remove_list:
        name = _normalize_tag_name(t)
        if name:
            to_remove.add(name)

    next_tags: List[str] = []
    for name in cur_set:
        if name in to_remove:
            continue
        next_tags.append(name)
    for name in to_add:
        if name not in next_tags:
            next_tags.append(name)

    if len(next_tags) > MAX_TAGS_PER_QUESTION:
        next_tags = next_tags[:MAX_TAGS_PER_QUESTION]

    ok, msg, updated = set_question_tags(conn, user_id, question_id, next_tags)
    return ok, msg, updated


def get_question_ids_by_tag(conn, user_id: int, tag_name: Any) -> Set[int]:
    tag = _normalize_tag_name(tag_name)
    if not tag:
        return set()
    _ensure_migrated(conn, user_id)

    # 优先：subject 维度（scope_id<>0）
    out: Set[int] = set()
    try:
        ensure_tag_tables(conn)
        rows = conn.execute(
            text("""
            SELECT DISTINCT question_id
            FROM user_question_tag_items
            WHERE user_id = :user_id AND scope = :scope AND scope_id <> 0 AND tag = :tag AND question_id > 0
            """),
            {"user_id": int(user_id), "scope": str(SCOPE_QUESTION_CENTER), "tag": str(tag)},
        ).fetchall()
        for r in rows or []:
            try:
                out.add(int(r._mapping["question_id"]))
            except Exception:
                continue
    except Exception:
        out = set()

    if out:
        return out

    # fallback：旧结构 scope_id=0
    ids = _uq_get_question_ids_by_tag(conn, user_id=int(user_id), scope=SCOPE_QUESTION_CENTER, scope_id=0, tag=tag)
    out2: Set[int] = set()
    for v in ids or []:
        try:
            out2.add(int(v))
        except Exception:
            continue
    return out2
