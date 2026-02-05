# -*- coding: utf-8 -*-

import json
import uuid
from datetime import datetime, timedelta

from flask import request, jsonify, current_app

from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id

from ..api_bp import user_bank_api_bp
from ..api_shared import (
    check_bank_access,
    generate_share_code,
    get_bank_category_name,
    _parse_question_ids_from_request_args,
    _get_bank_tag_store_key,
    _load_bank_tag_store,
    _save_bank_tag_store,
)


@user_bank_api_bp.route('/<int:bank_id>/tags', methods=['GET', 'POST'])
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
