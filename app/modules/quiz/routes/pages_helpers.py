# -*- coding: utf-8 -*-
"""刷题页面路由 — 辅助函数（从 pages.py 拆分）"""
import json
import math
import random
import re

from app.core.utils.json_helpers import safe_json_load as _safe_json_load
from app.core.utils.options_parser import parse_options
from app.models.quiz import Favorite, Mistake
from app.models.user_bank import UserBankFavorite, UserBankMistake


def _parse_positive_int(val, default=10, min_val=1, max_val=200):
    try:
        num = int(val)
        if num < min_val:
            return min_val
        if num > max_val:
            return max_val
        return num
    except Exception:
        return default


def _parse_id_list(val, max_len=200):
    if not val:
        return []
    raw = str(val)
    parts = re.split(r"[^0-9]+", raw)
    out = []
    seen = set()
    for p in parts:
        if not p:
            continue
        try:
            n = int(p)
        except Exception:
            continue
        if n <= 0 or n in seen:
            continue
        seen.add(n)
        out.append(n)
        if len(out) >= max_len:
            break
    return out


def _build_learn_session(rows, target_n):
    target_n = _parse_positive_int(target_n, default=10)
    extra = max(2, min(10, int(math.ceil(target_n * 0.3))))
    session_size = min(len(rows), target_n + extra)

    in_progress = []
    new_items = []
    for r in rows:
        streak = r.get('streak')
        if streak is None:
            new_items.append(r)
        else:
            in_progress.append(r)

    random.shuffle(in_progress)
    random.shuffle(new_items)

    need_in_progress = min(len(in_progress), max(1, int(math.ceil(target_n * 0.6))))
    selected = list(in_progress[:need_in_progress])

    remaining = session_size - len(selected)
    if remaining > 0:
        selected.extend(new_items[:remaining])

    if len(selected) < session_size:
        rest = in_progress[need_in_progress:] + new_items[remaining:]
        random.shuffle(rest)
        selected.extend(rest[:(session_size - len(selected))])

    ids = [int(r['id']) for r in selected]
    streak_map = {int(r['id']): int(r.get('streak') or 0) for r in selected}
    return ids, streak_map


def _split_review_rows(rows):
    weak = []
    strong = []
    for r in rows:
        level = int(r.get('review_level') or 0)
        last_rating = (r.get('last_rating') or '').lower()
        if level <= 1 or last_rating in ('fuzzy', 'unknown'):
            weak.append(r)
        else:
            strong.append(r)
    return weak, strong


def _build_review_session(rows, target_n):
    target_n = _parse_positive_int(target_n, default=10)
    if not rows:
        return []
    weak, strong = _split_review_rows(rows)
    random.shuffle(weak)
    random.shuffle(strong)
    need_weak = min(len(weak), max(1, int(math.ceil(target_n * 0.8))))
    selected = list(weak[:need_weak])
    remaining = target_n - len(selected)
    if remaining > 0:
        selected.extend(strong[:remaining])
    if len(selected) < target_n:
        rest = weak[need_weak:] + strong[remaining:]
        random.shuffle(rest)
        selected.extend(rest[:(target_n - len(selected))])
    return [int(r['question_id']) for r in selected]


def _progress_key_prefix(mode: str) -> str:
    if mode in ('learn', 'review'):
        return 'study_progress'
    return 'quiz_progress'


def _normalize_answer(q):
    try:
        qtype = str(q.get('q_type') or '')
        ans_raw = str(q.get('answer') or '').strip()
        if qtype in ('选择题', '多选题'):
            q['answer'] = ''.join([c for c in ans_raw if c.isalpha()]).upper()
        elif qtype == '判断题':
            v = ans_raw.lower()
            if v in ('对', '正确', 'true', 't', '1', 'yes', 'y'):
                q['answer'] = '正确'
            elif v in ('错', '错误', 'false', 'f', '0', 'no', 'n'):
                q['answer'] = '错误'
    except Exception:
        pass


def _apply_pqf_legacy_fields(q: dict, *, scope: str) -> None:
    """把 DB(PQF) 字段转成 quiz 页面历史字段。"""
    from app.core.utils.portable_question_format import portable_question_to_internal

    portable = {
        "id": q.get("id"),
        "type": q.get("type") or "",
        "content": q.get("content") or "",
        "options": _safe_json_load(q.get("options"), []),
        "answer": _safe_json_load(q.get("answer"), []),
        "analysis": q.get("analysis") or "",
        "tags": _safe_json_load(q.get("tags"), []),
        "difficulty": q.get("difficulty") if q.get("difficulty") is not None else 1,
    }
    internal, _errors = portable_question_to_internal(portable, scope=scope)
    q["q_type"] = internal.get("q_type") or ""
    q["content"] = internal.get("content") or ""
    q["options"] = internal.get("options") or []
    q["answer"] = internal.get("answer") or ""
    q["explanation"] = internal.get("explanation") or ""


def _build_public_questions(rows, uid):
    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if uid and q_ids:
        fav_rows = Favorite.query.filter(
            Favorite.user_id == uid,
            Favorite.question_id.in_(q_ids),
        ).all()
        mis_rows = Mistake.query.filter(
            Mistake.user_id == uid,
            Mistake.question_id.in_(q_ids),
        ).all()
        fav_set = {int(r.question_id) for r in fav_rows}
        mis_set = {int(r.question_id) for r in mis_rows}

    questions = []
    for row in rows:
        q = dict(row) if not isinstance(row, dict) else row
        _apply_pqf_legacy_fields(q, scope='question_center')
        q['is_fav'] = 1 if int(q.get('id') or 0) in fav_set else 0
        q['is_mistake'] = 1 if int(q.get('id') or 0) in mis_set else 0

        image_path = q.get('image_path')
        image_path_json = '[]'
        if image_path and isinstance(image_path, str):
            if image_path.strip().startswith('[') and image_path.strip().endswith(']'):
                image_path_json = image_path
            else:
                image_path_json = json.dumps([image_path])
        q['image_path_json'] = image_path_json

        if q.get('options'):
            try:
                q['options'] = parse_options(q['options'])
            except Exception:
                q['options'] = []
        else:
            q['options'] = []

        _normalize_answer(q)
        questions.append(q)
    return questions


def _build_user_bank_questions(rows, uid, bank_id):
    q_ids = [int(r['id']) for r in rows] if rows else []
    fav_set = set()
    mis_set = set()
    if uid and q_ids:
        fav_rows = UserBankFavorite.query.filter(
            UserBankFavorite.user_id == uid,
            UserBankFavorite.question_id.in_(q_ids),
        ).all()
        mis_rows = UserBankMistake.query.filter(
            UserBankMistake.user_id == uid,
            UserBankMistake.question_id.in_(q_ids),
        ).all()
        fav_set = {int(r.question_id) for r in fav_rows}
        mis_set = {int(r.question_id) for r in mis_rows}

    questions = []
    for row in rows:
        q = dict(row) if not isinstance(row, dict) else row
        _apply_pqf_legacy_fields(q, scope='user_bank')
        q['is_fav'] = 1 if int(q.get('id') or 0) in fav_set else 0
        q['is_mistake'] = 1 if int(q.get('id') or 0) in mis_set else 0

        image_path = q.get('image_path')
        image_path_json = '[]'
        if image_path and isinstance(image_path, str):
            if image_path.strip().startswith('[') and image_path.strip().endswith(']'):
                image_path_json = image_path
            else:
                image_path_json = json.dumps([image_path])
        q['image_path_json'] = image_path_json

        if q.get('options'):
            try:
                q['options'] = parse_options(q['options'])
            except Exception:
                q['options'] = []
        else:
            q['options'] = []

        _normalize_answer(q)
        questions.append(q)
    return questions


def _orm_to_dict(obj) -> dict:
    """Convert an ORM model instance to a dict (column values only)."""
    if isinstance(obj, dict):
        return obj
    try:
        return {c.key: getattr(obj, c.key) for c in obj.__class__.__mapper__.column_attrs}
    except Exception:
        return dict(obj) if hasattr(obj, "__iter__") else {}


def _row_to_dict(row) -> dict:
    """Convert a SQLAlchemy Row/RowMapping to dict."""
    if isinstance(row, dict):
        return row
    try:
        return dict(row._mapping)
    except Exception:
        pass
    try:
        return {c.key: getattr(row, c.key) for c in row.__class__.__mapper__.column_attrs}
    except Exception:
        return {}
