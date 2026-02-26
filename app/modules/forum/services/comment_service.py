# -*- coding: utf-8 -*-
"""评论业务逻辑"""
import logging
from typing import Optional

from sqlalchemy import text

from app.core.extensions import db
from ..services.content_sanitizer import sanitize_html, strip_html_tags
from ..services import mention_service, ban_service, interaction_service

logger = logging.getLogger(__name__)


def get_comments(post_id: int, page: int = 1, per_page: int = 30,
                 user_id: Optional[int] = None,
                 sort: str = 'time') -> dict:
    """获取帖子的评论列表（含楼中楼）— 批量查询优化版

    sort: 'time'（默认按时间升序）| 'hot'（按热度降序：like_count*2 + reply_count）
    """
    params: dict = {'pid': post_id, 'limit': per_page, 'offset': (page - 1) * per_page}

    liked_sql = ''
    if user_id:
        params['uid'] = user_id
        liked_sql = ", EXISTS(SELECT 1 FROM forum_likes WHERE user_id=:uid AND target_type='comment' AND target_id=c.id) AS liked"

    total = db.session.execute(text(
        'SELECT COUNT(*) FROM forum_comments WHERE post_id = :pid AND parent_id IS NULL AND is_deleted = false'
    ), {'pid': post_id}).scalar()

    order_clause = 'c.created_at ASC'
    if sort == 'hot':
        order_clause = '(c.like_count * 2 + c.reply_count) DESC, c.created_at DESC'

    # 一级评论
    rows = db.session.execute(text(f'''
        SELECT c.*, u.username AS author_name, u.avatar AS author_avatar
               {liked_sql}
        FROM forum_comments c
        JOIN users u ON u.id = c.author_id
        WHERE c.post_id = :pid AND c.parent_id IS NULL AND c.is_deleted = false
        ORDER BY {order_clause}
        LIMIT :limit OFFSET :offset
    '''), params).fetchall()

    comments = [dict(r._mapping) for r in rows]
    parent_ids = [c['id'] for c in comments]

    # 批量查询所有楼中楼（每组最多5条，用 ROW_NUMBER 窗口函数）
    replies_by_parent: dict[int, list[dict]] = {pid: [] for pid in parent_ids}
    if parent_ids:
        reply_liked = ''
        reply_params: dict = {}
        if user_id:
            reply_params['uid'] = user_id
            reply_liked = ", EXISTS(SELECT 1 FROM forum_likes WHERE user_id=:uid AND target_type='comment' AND target_id=sub.id) AS liked"

        # 动态生成 IN 子句的绑定参数
        in_placeholders = ', '.join(f':pid_{i}' for i in range(len(parent_ids)))
        for i, pid in enumerate(parent_ids):
            reply_params[f'pid_{i}'] = pid

        reply_rows = db.session.execute(text(f'''
            SELECT sub.*, u.username AS author_name, u.avatar AS author_avatar,
                   ru.username AS reply_to_name
                   {reply_liked}
            FROM (
                SELECT rc.*,
                       ROW_NUMBER() OVER (PARTITION BY rc.parent_id ORDER BY rc.created_at ASC) AS rn
                FROM forum_comments rc
                WHERE rc.parent_id IN ({in_placeholders}) AND rc.is_deleted = false
            ) sub
            JOIN users u ON u.id = sub.author_id
            LEFT JOIN users ru ON ru.id = sub.reply_to_user_id
            WHERE sub.rn <= 5
            ORDER BY sub.parent_id, sub.created_at ASC
        '''), reply_params).fetchall()

        for rr in reply_rows:
            rd = dict(rr._mapping)
            rd.pop('rn', None)
            pid = rd['parent_id']
            if pid in replies_by_parent:
                replies_by_parent[pid].append(rd)

    for c in comments:
        c['replies'] = replies_by_parent.get(c['id'], [])

    return {'comments': comments, 'total': total, 'page': page, 'per_page': per_page}


def create_comment(post_id: int, author_id: int, content: str,
                   parent_id: Optional[int] = None,
                   reply_to_user_id: Optional[int] = None) -> dict:
    """发表评论"""
    if ban_service.is_banned(author_id):
        return {'error': '您已被禁言，无法评论'}

    safe_content = sanitize_html(content)
    params: dict = {
        'pid': post_id, 'uid': author_id, 'content': safe_content,
        'parent_id': parent_id, 'reply_to': reply_to_user_id,
    }
    result = db.session.execute(text('''
        INSERT INTO forum_comments (post_id, author_id, content, parent_id, reply_to_user_id)
        VALUES (:pid, :uid, :content, :parent_id, :reply_to)
        RETURNING id
    '''), params)
    new_comment_id = result.fetchone()._mapping['id']

    # 更新帖子评论计数和最后评论时间
    db.session.execute(text('''
        UPDATE forum_posts
        SET comment_count = comment_count + 1, last_comment_at = NOW()
        WHERE id = :pid
    '''), {'pid': post_id})

    # 如果是楼中楼，更新父评论回复计数
    if parent_id:
        db.session.execute(text(
            'UPDATE forum_comments SET reply_count = reply_count + 1 WHERE id = :cid'
        ), {'cid': parent_id})

    db.session.commit()

    row = db.session.execute(text(
        'SELECT * FROM forum_comments WHERE id = :cid'
    ), {'cid': new_comment_id}).fetchone()
    comment = dict(row._mapping)

    # 解析 @提及
    mention_service.create_mentions('comment', comment['id'], author_id, safe_content)

    # 触发互动通知
    try:
        preview = strip_html_tags(safe_content, 100) if safe_content else ''
        notified_uids: set[int] = set()

        if parent_id and reply_to_user_id:
            # 楼中楼回复 → 通知被回复者
            if reply_to_user_id != author_id:
                interaction_service.create_notification(
                    user_id=reply_to_user_id, actor_id=author_id,
                    action_type=interaction_service.ACTION_REPLY,
                    target_type='comment', target_id=parent_id,
                    post_id=post_id, content_preview=preview,
                )
                notified_uids.add(reply_to_user_id)

            # 同时通知父评论作者（如果不同于被回复者且不是自己）
            parent_row = db.session.execute(text(
                'SELECT author_id FROM forum_comments WHERE id=:cid'
            ), {'cid': parent_id}).fetchone()
            if parent_row:
                parent_author = parent_row._mapping['author_id']
                if parent_author != author_id and parent_author not in notified_uids:
                    interaction_service.create_notification(
                        user_id=parent_author, actor_id=author_id,
                        action_type=interaction_service.ACTION_REPLY,
                        target_type='comment', target_id=parent_id,
                        post_id=post_id, content_preview=preview,
                    )
                    notified_uids.add(parent_author)

        elif parent_id:
            # 有 parent_id 但无 reply_to_user_id → 通知父评论作者
            parent_row = db.session.execute(text(
                'SELECT author_id FROM forum_comments WHERE id=:cid'
            ), {'cid': parent_id}).fetchone()
            if parent_row:
                parent_author = parent_row._mapping['author_id']
                if parent_author != author_id:
                    interaction_service.create_notification(
                        user_id=parent_author, actor_id=author_id,
                        action_type=interaction_service.ACTION_REPLY,
                        target_type='comment', target_id=parent_id,
                        post_id=post_id, content_preview=preview,
                    )
                    notified_uids.add(parent_author)

        # 一级评论或楼中楼 → 都通知帖子作者（避免重复）
        post_row = db.session.execute(text(
            'SELECT author_id FROM forum_posts WHERE id=:pid'
        ), {'pid': post_id}).fetchone()
        if post_row:
            post_author = post_row._mapping['author_id']
            if post_author != author_id and post_author not in notified_uids:
                action = interaction_service.ACTION_COMMENT if not parent_id else interaction_service.ACTION_REPLY
                interaction_service.create_notification(
                    user_id=post_author, actor_id=author_id,
                    action_type=action,
                    target_type='post', target_id=post_id,
                    post_id=post_id, content_preview=preview,
                )
    except Exception as _e:
        logger.warning(
            "评论互动通知写入失败 post=%s comment=%s: %s",
            post_id, comment.get('id'), _e,
        )

    return comment


def delete_comment(comment_id: int, user_id: int, is_admin: bool = False) -> bool:
    """软删除评论"""
    row = db.session.execute(text(
        'SELECT author_id, post_id, parent_id FROM forum_comments WHERE id = :cid AND is_deleted = false'
    ), {'cid': comment_id}).fetchone()
    if not row:
        return False
    m = row._mapping
    if m['author_id'] != user_id and not is_admin:
        return False

    db.session.execute(text('''
        UPDATE forum_comments
        SET is_deleted = true, deleted_by = :uid, deleted_at = NOW()
        WHERE id = :cid
    '''), {'cid': comment_id, 'uid': user_id})

    # 更新帖子评论计数
    db.session.execute(text(
        'UPDATE forum_posts SET comment_count = GREATEST(comment_count - 1, 0) WHERE id = :pid'
    ), {'pid': m['post_id']})

    # 如果是楼中楼，更新父评论回复计数
    if m['parent_id']:
        db.session.execute(text(
            'UPDATE forum_comments SET reply_count = GREATEST(reply_count - 1, 0) WHERE id = :cid'
        ), {'cid': m['parent_id']})

    db.session.commit()
    return True
