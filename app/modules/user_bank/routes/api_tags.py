# -*- coding: utf-8 -*-

"""用户题库：标签管理 API"""

import json

from flask import request, jsonify

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.utils.portable_question_format import normalize_tags
from app.core.utils.user_question_tags import (
    SCOPE_USER_BANK,
    TAG_DEF_QUESTION_ID,
    ensure_tag_tables,
    delete_user_tag as _uq_delete_user_tag,
)

from .api_base import user_bank_api_bp, check_bank_access


def _get_bank_tag_store_key(bank_id: int) -> str:
    """获取题库标签存储的 key"""
    return f'bank_{bank_id}_tags'


def _clean_tag_list(raw) -> list:
    out = []
    for t in normalize_tags(raw):
        s = str(t or "").strip()
        if not s:
            continue
        if len(s) > 20:
            s = s[:20].strip()
        if not s or s.lower() == "all":
            continue
        if s not in out:
            out.append(s)
    return out


def _load_bank_tag_store_from_user_progress(conn, bank_id: int, user_id: int) -> dict:
    """旧版存储：user_progress.bank_{id}_tags"""
    key = _get_bank_tag_store_key(bank_id)
    row = conn.execute(
        "SELECT data FROM user_progress WHERE user_id = ? AND p_key = ?",
        (int(user_id), str(key)),
    ).fetchone()

    if row and row["data"]:
        try:
            raw = json.loads(row["data"])
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass

    return {"tags": [], "question_tags": {}}


def _has_any_new_bank_tags(conn, bank_id: int, user_id: int) -> bool:
    try:
        ensure_tag_tables(conn)
        row = conn.execute(
            "SELECT 1 FROM user_question_tag_items WHERE user_id = ? AND scope = ? AND scope_id IS ? LIMIT 1",
            (int(user_id), str(SCOPE_USER_BANK), int(bank_id)),
        ).fetchone()
        return row is not None
    except Exception:
        return False


def _load_bank_tag_store_from_uqti(conn, bank_id: int, user_id: int) -> dict:
    ensure_tag_tables(conn)
    rows = conn.execute(
        """
        SELECT question_id, tag
        FROM user_question_tag_items
        WHERE user_id = ? AND scope = ? AND scope_id IS ?
        ORDER BY question_id ASC, tag ASC
        """,
        (int(user_id), str(SCOPE_USER_BANK), int(bank_id)),
    ).fetchall()

    tags = []
    question_tags = {}
    for r in rows or []:
        try:
            qid = int(r["question_id"])
        except Exception:
            continue
        t = str(r["tag"] or "").strip()
        if not t or t.lower() == "all":
            continue
        if t not in tags:
            tags.append(t)
        if qid > 0:
            question_tags.setdefault(str(qid), [])
            if t not in question_tags[str(qid)]:
                question_tags[str(qid)].append(t)

    return {"tags": tags, "question_tags": question_tags}


def _load_bank_tag_store(conn, bank_id: int, user_id: int) -> dict:
    """
    加载题库的标签存储数据
    结构: { 'tags': ['tag1', ...], 'question_tags': { 'q_id': ['tag1', ...] } }
    优先从 user_question_tag_items 读取；兼容读取旧版 user_progress(bank_{id}_tags)。
    """
    if _has_any_new_bank_tags(conn, bank_id, user_id):
        return _load_bank_tag_store_from_uqti(conn, bank_id, user_id)

    # fallback：读取旧格式，并尽力迁移到新表
    old = _load_bank_tag_store_from_user_progress(conn, bank_id, user_id)
    try:
        tags = _clean_tag_list(old.get("tags") if isinstance(old.get("tags"), list) else [])
        q_tags = old.get("question_tags") if isinstance(old.get("question_tags"), dict) else {}
        if tags or q_tags:
            _save_bank_tag_store(conn, bank_id, user_id, {"tags": tags, "question_tags": q_tags})
            return _load_bank_tag_store_from_uqti(conn, bank_id, user_id)
    except Exception:
        pass
    return {"tags": [], "question_tags": {}}


def _save_bank_tag_store(conn, bank_id: int, user_id: int, store: dict):
    """保存题库的标签存储数据（写入 user_question_tag_items）"""
    ensure_tag_tables(conn)

    conn.execute(
        "DELETE FROM user_question_tag_items WHERE user_id = ? AND scope = ? AND scope_id IS ?",
        (int(user_id), str(SCOPE_USER_BANK), int(bank_id)),
    )

    raw_tags = store.get("tags") if isinstance(store.get("tags"), list) else []
    question_tags = store.get("question_tags") if isinstance(store.get("question_tags"), dict) else {}

    merged_tags = list(_clean_tag_list(raw_tags))
    if isinstance(question_tags, dict):
        for _qid, _tags in question_tags.items():
            merged_tags.extend(_clean_tag_list(_tags))
    merged_tags = _clean_tag_list(merged_tags)

    # tag 定义（question_id=0）：保留“0 使用次数”的 tag
    if merged_tags:
        conn.executemany(
            """
            INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (int(user_id), str(SCOPE_USER_BANK), int(bank_id), int(TAG_DEF_QUESTION_ID), t)
                for t in merged_tags
            ],
        )

    # tag 绑定（question_id>0）
    rows = []
    if isinstance(question_tags, dict):
        for qid_raw, tags in question_tags.items():
            try:
                qid = int(qid_raw)
            except Exception:
                continue
            if qid <= 0:
                continue
            cleaned = _clean_tag_list(tags)
            for t in cleaned:
                rows.append((int(user_id), str(SCOPE_USER_BANK), int(bank_id), int(qid), t))

    if rows:
        conn.executemany(
            """
            INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )

    conn.commit()


@user_bank_api_bp.route('/<int:bank_id>/tags', methods=['GET', 'POST', 'DELETE'])
@auth_required
def bank_tags_api(bank_id: int):
    """
    获取/创建题库标签
    GET: 获取题库的所有标签
    POST: 创建新标签
    """
    user_id = current_user_id()
    conn = get_db()

    # 检查题库访问权限（含公开/分享）
    has_access, _permission, _access_type = check_bank_access(user_id, bank_id)
    if not has_access:
        return jsonify({'status': 'error', 'message': '题库不存在或无权访问'}), 404

    store = _load_bank_tag_store(conn, bank_id, user_id)

    if request.method == 'GET':
        # 统计每个标签的使用次数
        tag_counts = {}
        for tag in store.get('tags', []):
            tag_counts[tag] = 0

        question_tags = store.get('question_tags', {})
        for q_id, tags in question_tags.items():
            for tag in tags:
                if tag in tag_counts:
                    tag_counts[tag] += 1

        tags_list = [{'name': tag, 'count': tag_counts.get(tag, 0)} for tag in store.get('tags', [])]

        return jsonify({
            'status': 'success',
            'data': {'tags': tags_list}
        })

    elif request.method == 'POST':
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()

        if not name:
            return jsonify({'status': 'error', 'message': '标签名不能为空'}), 400

        if len(name) > 20:
            return jsonify({'status': 'error', 'message': '标签名不能超过20个字符'}), 400

        tags = store.get('tags', [])
        if name in tags:
            return jsonify({'status': 'error', 'message': '标签已存在'}), 400

        tags.append(name)
        store['tags'] = tags
        _save_bank_tag_store(conn, bank_id, user_id, store)

        return jsonify({
            'status': 'success',
            'data': {'name': name}
        })

    elif request.method == 'DELETE':
        data = request.get_json(silent=True) or {}
        name = (
            (data.get('name') or data.get('tag') or data.get('tag_name') or '').strip()
            or (request.args.get('name') or request.args.get('tag') or '').strip()
        )
        cleaned = _clean_tag_list([name])
        if not cleaned:
            return jsonify({'status': 'error', 'message': '标签名不能为空'}), 400
        tag = cleaned[0]

        try:
            _uq_delete_user_tag(
                conn,
                user_id=int(user_id),
                scope=str(SCOPE_USER_BANK),
                scope_id=int(bank_id),
                tag=tag,
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500

        # 返回最新标签列表（含使用次数）
        store = _load_bank_tag_store(conn, bank_id, user_id)
        tag_counts = {t: 0 for t in store.get('tags', [])}
        question_tags = store.get('question_tags', {})
        for _q_id, tags in (question_tags or {}).items():
            if not isinstance(tags, list):
                continue
            for t in tags:
                if t in tag_counts:
                    tag_counts[t] += 1

        tags_list = [{'name': t, 'count': tag_counts.get(t, 0)} for t in store.get('tags', [])]
        return jsonify({'status': 'success', 'data': {'tags': tags_list, 'deleted': tag}})


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>/tags', methods=['GET', 'POST'])
@auth_required
def bank_question_tags_api(bank_id: int, question_id: int):
    """
    获取/设置题目标签
    GET: 获取题目的标签
    POST: 设置题目的标签
    """
    user_id = current_user_id()
    conn = get_db()

    # 检查题库访问权限（含公开/分享）
    has_access, _permission, _access_type = check_bank_access(user_id, bank_id)
    if not has_access:
        return jsonify({'status': 'error', 'message': '题库不存在或无权访问'}), 404

    # 检查题目是否存在
    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    store = _load_bank_tag_store(conn, bank_id, user_id)

    if request.method == 'GET':
        question_tags = store.get('question_tags', {})
        tags = question_tags.get(str(question_id), [])

        return jsonify({
            'status': 'success',
            'data': {'tags': tags}
        })

    elif request.method == 'POST':
        data = request.get_json() or {}
        new_tags = data.get('tags', [])

        if not isinstance(new_tags, list):
            return jsonify({'status': 'error', 'message': '标签必须是数组'}), 400

        # 过滤无效标签
        valid_tags = [t for t in new_tags if isinstance(t, str) and t.strip()]
        valid_tags = [t.strip()[:20] for t in valid_tags]  # 限制长度

        # 确保所有使用的标签都在 tags 列表中
        all_tags = set(store.get('tags', []))
        for tag in valid_tags:
            if tag not in all_tags:
                all_tags.add(tag)

        store['tags'] = list(all_tags)

        question_tags = store.get('question_tags', {})
        question_tags[str(question_id)] = valid_tags
        store['question_tags'] = question_tags

        _save_bank_tag_store(conn, bank_id, user_id, store)

        return jsonify({
            'status': 'success',
            'data': {'tags': valid_tags}
        })
