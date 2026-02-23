# -*- coding: utf-8 -*-
"""复盘中心 — 共享辅助函数（meta / url / preview / tag_ids）。"""

from urllib.parse import urlencode


def _review_center_meta(kind: str) -> dict:
    kind = (kind or '').strip().lower()
    if kind == 'favorites':
        return {
            'kind': 'favorites',
            'title': '收藏中心',
            'subtitle': '在当前题库范围内完成练习、搜索与数据复盘（与小程序保持同语义）。',
            'quiz_label': '开始刷题',
            'memo_label': '开始背题',
        }
    if kind == 'tags':
        return {
            'kind': 'tags',
            'title': '标签中心',
            'subtitle': '按你的标签体系聚类题目：练习、搜索与统计均可按标签过滤。',
            'quiz_label': '开始刷标签',
            'memo_label': '开始背标签',
        }
    return {
        'kind': 'mistakes',
        'title': '错题中心',
        'subtitle': '聚焦错题复盘：练习、搜索与统计均在错题范围内联动。',
        'quiz_label': '开始刷错题',
        'memo_label': '开始背错题',
    }


def _url_with_params(base: str, params: dict) -> str:
    clean = {k: v for k, v in (params or {}).items() if v is not None and str(v) != ''}
    if not clean:
        return base
    return f"{base}?{urlencode(clean)}"


def _build_preview(raw: str, limit: int = 80) -> str:
    try:
        import re as _re

        text = _re.sub(r'<[^>]+>', '', raw or '').replace('\n', ' ').strip()
    except Exception:
        text = (raw or '').replace('\n', ' ').strip()
    if len(text) > limit:
        return text[:limit] + '...'
    return text


def _load_public_tag_ids(conn, uid: int, tag: str):
    tag = (tag or '').strip()
    if not tag or tag.lower() == 'all':
        return None
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag

    ids = get_question_ids_by_tag(conn, uid, tag)
    return sorted({int(x) for x in ids}) if ids else []


def _load_bank_tag_ids(conn, uid: int, bank_id: int, tag: str):
    tag = (tag or '').strip()
    if not tag or tag.lower() == 'all':
        return None
    from app.modules.user_bank.routes.api import _load_bank_tag_store

    store = _load_bank_tag_store(conn, int(bank_id), int(uid))
    question_tags = store.get('question_tags', {}) or {}
    ids = []
    for q_id, tags in (question_tags or {}).items():
        if not isinstance(tags, list) or tag not in tags:
            continue
        try:
            ids.append(int(q_id))
        except Exception:
            continue
    return sorted(set(ids)) if ids else []
