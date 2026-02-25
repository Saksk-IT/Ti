# -*- coding: utf-8 -*-
"""投票服务"""
import json
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db


def get_poll_data(post_id: int, user_id: Optional[int] = None) -> Optional[dict]:
    """获取帖子的投票数据（含各选项票数和用户已投选项）"""
    row = db.session.execute(text(
        'SELECT poll FROM forum_posts WHERE id=:pid AND is_deleted=false'
    ), {'pid': post_id}).fetchone()
    if not row or not row._mapping['poll']:
        return None

    poll = row._mapping['poll']
    if isinstance(poll, str):
        poll = json.loads(poll)

    options = poll.get('options', [])
    # 统计每个选项的票数
    vote_rows = db.session.execute(text('''
        SELECT option_index, COUNT(*) AS count
        FROM forum_poll_votes WHERE post_id=:pid
        GROUP BY option_index
    '''), {'pid': post_id}).fetchall()
    vote_map = {r._mapping['option_index']: r._mapping['count'] for r in vote_rows}

    total_votes = sum(vote_map.values())
    results = []
    for i, opt in enumerate(options):
        results.append({
            'index': i,
            'text': opt,
            'count': vote_map.get(i, 0),
        })

    user_votes: list[int] = []
    if user_id:
        uv_rows = db.session.execute(text(
            'SELECT option_index FROM forum_poll_votes WHERE post_id=:pid AND user_id=:uid'
        ), {'pid': post_id, 'uid': user_id}).fetchall()
        user_votes = [r._mapping['option_index'] for r in uv_rows]

    return {
        'question': poll.get('question', ''),
        'multiple': poll.get('multiple', False),
        'options': results,
        'total_votes': total_votes,
        'user_votes': user_votes,
    }


def cast_vote(post_id: int, user_id: int, option_index: int) -> dict:
    """投票（单选时替换旧票，多选时切换）"""
    row = db.session.execute(text(
        'SELECT poll FROM forum_posts WHERE id=:pid AND is_deleted=false'
    ), {'pid': post_id}).fetchone()
    if not row or not row._mapping['poll']:
        return {'error': '该帖子没有投票'}

    poll = row._mapping['poll']
    if isinstance(poll, str):
        poll = json.loads(poll)

    options = poll.get('options', [])
    if option_index < 0 or option_index >= len(options):
        return {'error': '选项不存在'}

    multiple = poll.get('multiple', False)

    existing = db.session.execute(text(
        'SELECT id, option_index FROM forum_poll_votes WHERE post_id=:pid AND user_id=:uid'
    ), {'pid': post_id, 'uid': user_id}).fetchall()
    existing_indices = {r._mapping['option_index']: r._mapping['id'] for r in existing}

    if multiple:
        # 多选：切换该选项
        if option_index in existing_indices:
            db.session.execute(text(
                'DELETE FROM forum_poll_votes WHERE id=:vid'
            ), {'vid': existing_indices[option_index]})
        else:
            db.session.execute(text(
                'INSERT INTO forum_poll_votes (post_id, user_id, option_index) VALUES (:pid, :uid, :oi)'
            ), {'pid': post_id, 'uid': user_id, 'oi': option_index})
    else:
        # 单选：先删旧票再插新票（如果点同一个则取消）
        if existing_indices:
            db.session.execute(text(
                'DELETE FROM forum_poll_votes WHERE post_id=:pid AND user_id=:uid'
            ), {'pid': post_id, 'uid': user_id})
        if option_index not in existing_indices:
            db.session.execute(text(
                'INSERT INTO forum_poll_votes (post_id, user_id, option_index) VALUES (:pid, :uid, :oi)'
            ), {'pid': post_id, 'uid': user_id, 'oi': option_index})

    db.session.commit()
    return get_poll_data(post_id, user_id)
