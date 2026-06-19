# -*- coding: utf-8 -*-
"""刷题页面路由 — 辅助函数（从 pages.py 拆分）"""
import json
import math
import random
import re
from typing import Any

from app.core.utils.image_helpers import normalize_question_image_groups
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


_OPTION_KEYS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_OPTION_Q_TYPES = {"选择题", "多选题"}


def _option_value(option: Any) -> str:
    if isinstance(option, dict):
        return str(option.get("value") or "")
    return str(option or "")


def _option_key(option: Any, index: int) -> str:
    if isinstance(option, dict):
        raw = str(option.get("key") or "").strip().upper()
        if raw:
            return raw[:1]
    return _OPTION_KEYS[index] if index < len(_OPTION_KEYS) else str(index + 1)


def shuffle_choice_options(question: dict, *, rng: random.Random | None = None) -> dict:
    """Return a copy with shuffled choice options and remapped answer letters."""
    q_type = str(question.get("q_type") or "")
    if q_type not in _OPTION_Q_TYPES:
        return dict(question)

    options = question.get("options") or []
    if not isinstance(options, list) or len(options) <= 1:
        return dict(question)

    parsed_options = parse_options(options)
    if len(parsed_options) <= 1:
        return dict(question)

    answer_letters = {
        c.upper()
        for c in str(question.get("answer") or "")
        if c.isalpha()
    }
    original_answer_indexes = set()
    for index, option in enumerate(parsed_options):
        key = _option_key(option, index)
        if key in answer_letters:
            original_answer_indexes.add(index)

    indexed_options = [
        {"original_index": index, "value": _option_value(option)}
        for index, option in enumerate(parsed_options)
    ]
    shuffled = list(indexed_options)
    (rng or random).shuffle(shuffled)

    next_options = []
    next_answers = []
    for index, option in enumerate(shuffled):
        next_key = _OPTION_KEYS[index] if index < len(_OPTION_KEYS) else str(index + 1)
        next_options.append({"key": next_key, "value": option["value"]})
        if option["original_index"] in original_answer_indexes:
            next_answers.append(next_key)

    out = dict(question)
    out["options"] = next_options
    out["answer"] = "".join(sorted(next_answers))
    return out


def build_quiz_progress_key(
    *,
    uid: int,
    mode: str,
    subject: str,
    q_type: str,
    data_scope: str,
    tag: str = "",
    rk: str = "",
    shuffle_questions: bool = False,
    shuffle_options: bool = False,
) -> str:
    key_parts = [
        f"{_progress_key_prefix(mode)}_{uid}",
        mode,
        subject,
        q_type,
        data_scope,
        f"tag{tag}" if tag and str(tag).lower() != "all" else None,
        f"rk{rk}" if mode == "reinforce" and rk in ("wrong", "similar") else None,
        f"q{1 if shuffle_questions else 0}",
        f"o{1 if shuffle_options else 0}",
    ]
    return "_".join([p for p in key_parts if p])


def load_saved_question_order(*, uid: int, progress_key: str, progress_model) -> list[int] | None:
    try:
        saved = progress_model.query.filter_by(user_id=uid, p_key=progress_key).first()
        if not saved or not saved.data:
            return None
        saved_json = json.loads(saved.data)
        if isinstance(saved_json, dict) and isinstance(saved_json.get("order"), list):
            return [int(x) for x in saved_json["order"]]
    except Exception:
        return None
    return None


def save_question_order(
    *,
    uid: int,
    progress_key: str,
    order: list[int],
    progress_model,
    session,
) -> None:
    try:
        existing = progress_model.query.filter_by(user_id=uid, p_key=progress_key).first()
        if existing and existing.data:
            try:
                payload = json.loads(existing.data)
                if not isinstance(payload, dict):
                    payload = {}
            except Exception:
                payload = {}
        else:
            payload = {}
        payload["order"] = order
        payload["timestamp"] = payload.get("timestamp", 0)
        data_to_save = json.dumps(payload, ensure_ascii=False)
        if existing:
            existing.data = data_to_save
        else:
            session.add(progress_model(user_id=uid, p_key=progress_key, data=data_to_save))
        session.commit()
    except Exception:
        session.rollback()


def apply_question_shuffle(
    questions: list[dict],
    *,
    saved_order: list[int] | None = None,
    rng: random.Random | None = None,
) -> tuple[list[dict], list[int]]:
    if saved_order:
        q_map = {int(q.get("id") or 0): q for q in questions}
        ordered_questions = []
        for qid in saved_order:
            if qid in q_map:
                ordered_questions.append(q_map.pop(qid))
        if q_map:
            ordered_questions.extend(q_map.values())
        return ordered_questions, [int(q.get("id") or 0) for q in ordered_questions]

    shuffled = list(questions)
    (rng or random).shuffle(shuffled)
    return shuffled, [int(q.get("id") or 0) for q in shuffled]


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
    image_groups = normalize_question_image_groups(q.get("image_path"))
    q["question_image_groups"] = image_groups
    q["content_images"] = image_groups["content"]
    q["answer_images"] = image_groups["answer"]
    q["explanation_images"] = image_groups["explanation"]
    q["image_path"] = image_groups["content"][0] if image_groups["content"] else ""
    q["image_path_json"] = json.dumps(image_groups["content"], ensure_ascii=False)
    q["answer_image_paths_json"] = json.dumps(image_groups["answer"], ensure_ascii=False)
    q["explanation_image_paths_json"] = json.dumps(image_groups["explanation"], ensure_ascii=False)


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


def _build_user_bank_questions(rows, uid, bank_id, *, shuffle_options=False):
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

        if q.get('options'):
            try:
                q['options'] = parse_options(q['options'])
            except Exception:
                q['options'] = []
        else:
            q['options'] = []

        _normalize_answer(q)
        if shuffle_options:
            rng = random.Random((int(uid or 0) * 1000000) + int(q.get('id') or 0))
            q = shuffle_choice_options(q, rng=rng)
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
