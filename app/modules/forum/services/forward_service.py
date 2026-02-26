# -*- coding: utf-8 -*-
"""帖子转发到私聊服务"""
import json

from sqlalchemy import text

from app.core.extensions import db
from .content_sanitizer import strip_html_tags


def forward_post_to_chat(post_id: int, sender_id: int, receiver_id: int) -> dict:
    """将帖子转发到私聊"""
    # 获取帖子信息
    post = db.session.execute(text(
        'SELECT id, title, LEFT(content, 800) AS content_raw, images '
        'FROM forum_posts WHERE id=:pid AND is_deleted=false'
    ), {'pid': post_id}).fetchone()
    if not post:
        return {'error': '帖子不存在'}

    pm = post._mapping
    title = pm['title']
    preview = strip_html_tags(pm['content_raw'] or '', 120)

    # 取第一张图作为缩略图
    image = ''
    try:
        imgs = pm['images']
        if isinstance(imgs, str):
            imgs = json.loads(imgs)
        if isinstance(imgs, list) and imgs:
            image = str(imgs[0])
    except Exception:
        pass

    # 查找或创建私聊会话 — pair_key 使用 : 分隔（与 chat/routes/api.py 一致）
    u1, u2 = (min(sender_id, receiver_id), max(sender_id, receiver_id))
    pair_key = f'{u1}:{u2}'

    conv = db.session.execute(text(
        "SELECT id FROM chat_conversations WHERE direct_pair_key=:pk AND c_type='direct'"
    ), {'pk': pair_key}).fetchone()

    if conv:
        conv_id = conv._mapping['id']
    else:
        db.session.execute(text('''
            INSERT INTO chat_conversations (c_type, direct_pair_key)
            VALUES ('direct', :pk)
        '''), {'pk': pair_key})
        conv_row = db.session.execute(text(
            "SELECT id FROM chat_conversations WHERE direct_pair_key=:pk"
        ), {'pk': pair_key}).fetchone()
        conv_id = conv_row._mapping['id']
        # 添加双方为成员
        for uid in (sender_id, receiver_id):
            db.session.execute(text(
                'INSERT INTO chat_members (conversation_id, user_id) '
                'VALUES (:cid, :uid) ON CONFLICT DO NOTHING'
            ), {'cid': conv_id, 'uid': uid})

    # 发送转发消息 — JSON 格式
    content = json.dumps({
        'post_id': post_id,
        'title': title,
        'preview': preview,
        'image': image,
    }, ensure_ascii=False)

    db.session.execute(text('''
        INSERT INTO chat_messages (conversation_id, sender_id, content, content_type)
        VALUES (:cid, :sid, :content, 'forward')
    '''), {'cid': conv_id, 'sid': sender_id, 'content': content})

    db.session.execute(text(
        'UPDATE chat_conversations SET updated_at=NOW() WHERE id=:cid'
    ), {'cid': conv_id})
    db.session.commit()

    return {'success': True, 'conversation_id': conv_id}
