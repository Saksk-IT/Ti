# -*- coding: utf-8 -*-
"""帖子转发到私聊服务"""
from sqlalchemy import text

from app.core.extensions import db


def forward_post_to_chat(post_id: int, sender_id: int, receiver_id: int) -> dict:
    """将帖子转发到私聊"""
    # 获取帖子信息
    post = db.session.execute(text(
        'SELECT id, title FROM forum_posts WHERE id=:pid AND is_deleted=false'
    ), {'pid': post_id}).fetchone()
    if not post:
        return {'error': '帖子不存在'}

    title = post._mapping['title']

    # 查找或创建私聊会话
    pair_key_a = f'{min(sender_id, receiver_id)}_{max(sender_id, receiver_id)}'
    conv = db.session.execute(text(
        "SELECT id FROM chat_conversations WHERE direct_pair_key=:pk AND c_type='direct'"
    ), {'pk': pair_key_a}).fetchone()

    if conv:
        conv_id = conv._mapping['id']
    else:
        db.session.execute(text('''
            INSERT INTO chat_conversations (c_type, direct_pair_key)
            VALUES ('direct', :pk)
        '''), {'pk': pair_key_a})
        conv_row = db.session.execute(text(
            "SELECT id FROM chat_conversations WHERE direct_pair_key=:pk"
        ), {'pk': pair_key_a}).fetchone()
        conv_id = conv_row._mapping['id']
        # 添加双方为成员
        for uid in (sender_id, receiver_id):
            db.session.execute(text(
                'INSERT INTO chat_members (conversation_id, user_id) VALUES (:cid, :uid) ON CONFLICT DO NOTHING'
            ), {'cid': conv_id, 'uid': uid})

    # 发送转发消息
    content = f'[转发帖子] {title}\n/forum/post/{post_id}'
    db.session.execute(text('''
        INSERT INTO chat_messages (conversation_id, sender_id, content, content_type)
        VALUES (:cid, :sid, :content, 'forward')
    '''), {'cid': conv_id, 'sid': sender_id, 'content': content})

    db.session.execute(text(
        'UPDATE chat_conversations SET updated_at=NOW() WHERE id=:cid'
    ), {'cid': conv_id})
    db.session.commit()

    return {'success': True, 'conversation_id': conv_id}
