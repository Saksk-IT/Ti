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
                 user_id: Optional[int] = None) -> dict:
    """获取帖子的评论列表（含楼中楼）"""
    params: dict = {'pid': post_id, 'limit': per_page, 'offset': (page - 1) * per_page}

    liked_sql = ''
    if user_id:
        params['uid'] = user_id
        liked_sql = ", EXISTS(SELECT 1 FROM forum_likes WHERE user_id=:uid AND target_type='comment' AND target_id=c.id) AS liked"

    total = db.session.execute(text(
        'SELECT COUNT(*) FROM forum_comments WHERE post_id = :pid AND parent_id IS NULL AND is_deleted = false'
    ), {'pid': post_id}).scalar()

    # 一级评论
    rows = db.session.execute(text(f'''
        SELECT c.*, u.username AS author_name, u.avatar AS author_avatar
               {liked_sql}
        FROM forum_comments c
        JOIN users u ON u.id = c.author_id
        WHERE c.post_id = :pid AND c.parent_id IS NULL AND c.is_deleted = false
        ORDER BY c.created_at ASC
        LIMIT :limit OFFSET :offset
    '''), params).fetchall()

    comments = []
    for r in rows:
        c = dict(r._mapping)
        # 加载楼中楼回复（最多 5 条，更多需展开）
        reply_params: dict = {'cid': c['id']}
        reply_liked = ''
        if user_id:
            reply_params['uid'] = user_id
            reply_liked = ", EXISTS(SELECT 1 FROM forum_likes WHERE user_id=:uid AND target_type='comment' AND target_id=rc.id) AS liked"
        reply_rows = db.session.execute(text(f'''
            SELECT rc.*, u.username AS author_name, u.avatar AS author_avatar,
                   ru.username AS reply_to_name
                   {reply_liked}
            FROM forum_comments rc
            JOIN users u ON u.id = rc.author_id
            LEFT JOIN users ru ON ru.id = rc.reply_to_user_id
            WHERE rc.parent_id = :cid AND rc.is_deleted = false
            ORDER BY rc.created_at ASC
            LIMIT 5
        '''), reply_params).fetchall()
        c['replies'] = [dict(rr._mapping) for rr in reply_rows]
        comments.append(c)

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
    db.session.execute(text('''
        INSERT INTO forum_comments (post_id, author_id, content, parent_id, reply_to_user_id)
        VALUES (:pid, :uid, :content, :parent_id, :reply_to)
    '''), params)

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
        'SELECT * FROM forum_comments WHERE post_id = :pid AND author_id = :uid ORDER BY id DESC LIMIT 1'
    ), {'pid': post_id, 'uid': author_id}).fetchone()
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
