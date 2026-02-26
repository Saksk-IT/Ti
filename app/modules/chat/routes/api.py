# -*- coding: utf-8 -*-
"""用户聊天路由蓝图

实现：
- /chat ：聊天主页面（左侧会话列表、右侧消息区）
- /api/chat/* ：创建会话、拉取会话列表、拉取消息、发送消息、轮询未读

说明：
- 采用 SQLAlchemy ORM 持久化（chat_conversations/chat_members/chat_messages）
- 采用轮询方式实时刷新（不引入 WebSocket，保持现有项目依赖简单）
"""

from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from app.core.extensions import db, limiter
from app.core.utils.json_helpers import safe_load as _safe_load
from app.core.utils.options_parser import parse_options
from app.core.utils.time_utils import now_bj
from app.core.utils.cache_utils import (
    get_chat_version, bump_chat_version, make_cache_key,
)
from app.core.utils.redis_utils import redis_get_json, redis_set_json
from app.models.chat import ChatConversation, ChatMember, ChatMessage, UserRemark
from app.models.user import User
from app.models.subject import Question, Subject
from sqlalchemy import func, case, literal, text
import os
import uuid
import json
import subprocess
import shutil

chat_api_bp = Blueprint('chat_api', __name__)


CHAT_IMAGE_EXTS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
CHAT_AUDIO_EXTS = {'webm', 'wav', 'mp3', 'm4a', 'ogg'}

# iOS Safari 对 audio/webm 支持不稳定（很多机型直接无法播放），
# 因此上传时建议优先使用 m4a/mp3（前端录音也会尽量选择 ogg/webm，但播放端可能失败）。
# 后端这里允许多种格式，但不会做转码；如需"全端可播"，建议后续引入转码到 m4a/mp3。


def _allowed_image(filename: str) -> bool:
    return bool(filename) and ('.' in filename) and (filename.rsplit('.', 1)[1].lower() in CHAT_IMAGE_EXTS)


def _allowed_audio(filename: str) -> bool:
    return bool(filename) and ('.' in filename) and (filename.rsplit('.', 1)[1].lower() in CHAT_AUDIO_EXTS)


def _ffmpeg_exists() -> bool:
    """检测系统是否可用 ffmpeg"""
    try:
        return shutil.which('ffmpeg') is not None
    except Exception:
        return False


def _transcode_to_m4a(src_abs: str, dst_abs: str) -> tuple[bool, str]:
    """使用 ffmpeg 将音频转码为 m4a(aac)

    返回：(success, error_message)
    """
    if not _ffmpeg_exists():
        return False, 'ffmpeg_not_found'

    # -y 覆盖；-vn 去视频；aac 兼容性最好；-movflags +faststart 便于流式播放
    cmd = [
        'ffmpeg', '-y',
        '-i', src_abs,
        '-vn',
        '-c:a', 'aac',
        '-b:a', '64k',
        '-ar', '44100',
        '-ac', '1',
        '-movflags', '+faststart',
        dst_abs,
    ]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if p.returncode != 0:
            return False, (p.stderr.decode('utf-8', errors='ignore')[:4000] or 'ffmpeg_failed')
        return True, ''
    except Exception as e:
        return False, str(e)


def _transcode_to_mp3(src_abs: str, dst_abs: str) -> tuple[bool, str]:
    """使用 ffmpeg 将音频转码为 mp3（作为 m4a 失败时的兜底）

    返回：(success, error_message)
    """
    if not _ffmpeg_exists():
        return False, 'ffmpeg_not_found'

    cmd = [
        'ffmpeg', '-y',
        '-i', src_abs,
        '-vn',
        '-c:a', 'libmp3lame',
        '-b:a', '96k',
        '-ar', '44100',
        '-ac', '1',
        dst_abs,
    ]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if p.returncode != 0:
            return False, (p.stderr.decode('utf-8', errors='ignore')[:4000] or 'ffmpeg_failed')
        return True, ''
    except Exception as e:
        return False, str(e)


def _is_member(conversation_id: int, user_id: int) -> bool:
    """检查用户是否为会话成员"""
    r = db.session.query(ChatMember.id).filter_by(
        conversation_id=conversation_id, user_id=user_id
    ).first()
    return r is not None


def _insert_message_and_update(
    conversation_id: int, sender_id: int, content: str, content_type: str
) -> int:
    """插入消息、更新会话时间戳、推进发送者已读，返回 message_id"""
    msg = ChatMessage(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        content_type=content_type,
        created_at=now_bj(),
    )
    db.session.add(msg)
    db.session.flush()
    mid = msg.id

    # 更新会话时间戳
    conv = db.session.get(ChatConversation, conversation_id)
    if conv:
        conv.updated_at = now_bj()

    # 发送者已读推进
    member = db.session.query(ChatMember).filter_by(
        conversation_id=conversation_id, user_id=sender_id
    ).first()
    if member and (member.last_read_message_id or 0) < mid:
        member.last_read_message_id = mid

    db.session.commit()

    # bump 所有会话成员的聊天缓存版本号
    members = db.session.query(ChatMember.user_id).filter_by(
        conversation_id=conversation_id
    ).all()
    for m in members:
        bump_chat_version(m.user_id)

    return mid


@chat_api_bp.route('/chat/users')
@limiter.limit("120/minute")
def chat_users():
    """用于创建聊天时的用户列表（简单按活跃/用户名排序）"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    q = (request.args.get('q') or '').strip()[:100]

    query = db.session.query(
        User.id, User.username, User.avatar, User.last_active
    ).filter(User.id != uid)

    if q:
        query = query.filter(User.username.ilike(f"%{q}%"))

    # 排序优化：精确命中优先，其次前缀命中；再按活跃度与用户名
    if q:
        query = query.order_by(
            (func.lower(User.username) == func.lower(q)).desc(),
            (func.lower(User.username).like(func.lower(f"{q}%"))).desc(),
            case((User.last_active.is_(None), 1), else_=0).asc(),
            User.last_active.desc(),
            User.username.asc(),
        )
    else:
        query = query.order_by(
            case((User.last_active.is_(None), 1), else_=0).asc(),
            User.last_active.desc(),
            User.username.asc(),
        )

    rows = query.limit(50).all()
    data = [
        {
            'id': r.id,
            'username': r.username,
            'avatar': r.avatar,
            'last_active': r.last_active.isoformat() if r.last_active else None,
        }
        for r in rows
    ]
    return jsonify({'status': 'success', 'data': data})



@chat_api_bp.route('/chat/conversations')
@limiter.limit("120/minute")
def chat_conversations():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')

    # Redis 缓存：版本号 + TTL 5s
    ver = get_chat_version(uid)
    cache_key = make_cache_key("chat:convs", {"uid": uid, "ver": ver})
    cached = redis_get_json(cache_key)
    if cached is not None:
        return jsonify({'status': 'success', 'data': cached})

    # 别名：当前用户的成员行（用于 last_read）
    cm = db.aliased(ChatMember, name='cm')
    # 别名：对方成员行（direct 私聊）
    pmb = db.aliased(ChatMember, name='pmb')
    # 别名：对方用户
    pu = db.aliased(User, name='pu')

    # 最后一条消息子查询
    last_msg_id_sq = (
        db.session.query(func.max(ChatMessage.id))
        .filter(ChatMessage.conversation_id == ChatConversation.id)
        .correlate(ChatConversation)
        .scalar_subquery()
    )

    # 未读数子查询
    unread_sq = (
        db.session.query(func.count(ChatMessage.id))
        .filter(
            ChatMessage.conversation_id == ChatConversation.id,
            ChatMessage.id > func.coalesce(cm.last_read_message_id, 0),
            ChatMessage.sender_id != uid,
        )
        .correlate(ChatConversation, cm)
        .scalar_subquery()
    )

    lm = db.aliased(ChatMessage, name='lm')

    # 会话列表查询
    query = (
        db.session.query(
            ChatConversation.id.label('conversation_id'),
            ChatConversation.c_type,
            ChatConversation.title,
            ChatConversation.updated_at,
            pu.id.label('peer_user_id'),
            pu.username.label('peer_username'),
            pu.avatar.label('peer_avatar'),
            UserRemark.remark.label('peer_remark'),
            lm.content_type.label('last_message_type'),
            lm.content.label('last_message'),
            unread_sq.label('unread_count'),
        )
        # 当前用户必须是成员（内连接）
        .join(ChatMember, (ChatMember.conversation_id == ChatConversation.id) & (ChatMember.user_id == uid))
        # 当前用户的成员行（用于 last_read）
        .outerjoin(cm, (cm.conversation_id == ChatConversation.id) & (cm.user_id == uid))
        # 对方成员
        .outerjoin(pmb, (pmb.conversation_id == ChatConversation.id) & (pmb.user_id != uid))
        # 对方用户信息
        .outerjoin(pu, pu.id == pmb.user_id)
        # 当前用户对对方的备注
        .outerjoin(UserRemark, (UserRemark.owner_user_id == uid) & (UserRemark.target_user_id == pu.id))
        # 最后一条消息
        .outerjoin(lm, lm.id == last_msg_id_sq)
        .order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())
    )

    rows = query.all()

    data = []
    for r in rows:
        d = {
            'conversation_id': r.conversation_id,
            'c_type': r.c_type,
            'title': r.title,
            'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            'peer_user_id': r.peer_user_id,
            'peer_username': r.peer_username,
            'peer_avatar': r.peer_avatar,
            'peer_remark': r.peer_remark,
            'last_message_type': r.last_message_type,
            'last_message': r.last_message,
            'unread_count': r.unread_count or 0,
        }
        if d.get('last_message_type') == 'image':
            d['last_message'] = '[图片]'
        elif d.get('last_message_type') == 'audio':
            d['last_message'] = '[语音]'
        elif d.get('last_message_type') == 'file':
            d['last_message'] = '[文件]'
        elif d.get('last_message_type') == 'question':
            d['last_message'] = '[题目]'
        elif d.get('last_message_type') == 'forward':
            d['last_message'] = '[转发帖子]'
        data.append(d)

    # 写入 Redis 缓存（TTL 5s）
    redis_set_json(cache_key, data, ttl_seconds=5)

    return jsonify({'status': 'success', 'data': data})



@chat_api_bp.route('/chat/conversation_users')
@limiter.limit("120/minute")
def chat_conversation_users():
    """获取已有会话的用户列表（仅返回direct会话中的对方用户），用于题目转发等功能"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    q = (request.args.get('q') or '').strip()[:100]

    # 别名
    pmb = db.aliased(ChatMember, name='pmb')
    pu = db.aliased(User, name='pu')

    query = (
        db.session.query(
            pu.id,
            pu.username,
            pu.avatar,
            UserRemark.remark,
            ChatConversation.updated_at,
        )
        .join(ChatMember, (ChatMember.conversation_id == ChatConversation.id) & (ChatMember.user_id == uid))
        .join(pmb, (pmb.conversation_id == ChatConversation.id) & (pmb.user_id != uid))
        .join(pu, pu.id == pmb.user_id)
        .outerjoin(UserRemark, (UserRemark.owner_user_id == uid) & (UserRemark.target_user_id == pu.id))
        .filter(ChatConversation.c_type == 'direct')
    )

    if q:
        query = query.filter(
            (pu.username.ilike(f"%{q}%")) | (UserRemark.remark.ilike(f"%{q}%"))
        )

    query = query.distinct().order_by(ChatConversation.updated_at.desc(), pu.username.asc()).limit(50)
    rows = query.all()

    data = [
        {
            'id': r.id,
            'username': r.username,
            'avatar': r.avatar,
            'remark': r.remark,
        }
        for r in rows
    ]

    return jsonify({'status': 'success', 'data': data})


@chat_api_bp.route('/chat/conversations/create', methods=['POST'])
@limiter.limit("30/minute")
def chat_create_conversation():
    """创建或复用 1v1 会话（从根源避免重复 direct 会话）"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    data = request.json or {}
    peer_id = int(data.get('peer_user_id') or 0)
    if peer_id <= 0 or peer_id == uid:
        return jsonify({'status': 'error', 'message': '对方用户不合法'}), 400

    # 检查对方是否存在
    peer = db.session.query(User.id, User.username).filter_by(id=peer_id).first()
    if not peer:
        return jsonify({'status': 'error', 'message': '对方用户不存在'}), 404

    # 数据库层唯一约束：direct_pair_key = "min_uid:max_uid"
    u1, u2 = (uid, peer_id) if uid < peer_id else (peer_id, uid)
    pair_key = f"{u1}:{u2}"

    # 先按 pair_key 复用（最快且唯一）
    row = db.session.query(ChatConversation.id).filter_by(
        c_type='direct', direct_pair_key=pair_key
    ).order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc()).first()
    if row:
        return jsonify({'status': 'success', 'conversation_id': row.id, 'reused': True})

    # 新建：直接写入 pair_key，并依赖唯一索引从根源杜绝重复
    try:
        now = now_bj()
        conv = ChatConversation(c_type='direct', title=None, direct_pair_key=pair_key, created_at=now, updated_at=now)
        db.session.add(conv)
        db.session.flush()
        cid = conv.id

        db.session.add(ChatMember(conversation_id=cid, user_id=uid, role='member', joined_at=now))
        db.session.add(ChatMember(conversation_id=cid, user_id=peer_id, role='member', joined_at=now))
        db.session.commit()
        return jsonify({'status': 'success', 'conversation_id': cid, 'reused': False})
    except Exception:
        # 并发/竞态：可能另一请求已创建成功，回退到查询复用
        db.session.rollback()
        row2 = db.session.query(ChatConversation.id).filter_by(
            c_type='direct', direct_pair_key=pair_key
        ).order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc()).first()
        if row2:
            return jsonify({'status': 'success', 'conversation_id': row2.id, 'reused': True})
        raise



@chat_api_bp.route('/chat/user_remark', methods=['GET', 'POST'])
@limiter.limit("60/minute")
def chat_user_remark():
    """读取/设置对某个用户的备注（仅自己可见）

    GET  /api/chat/user_remark?target_user_id=xx
    POST /api/chat/user_remark  JSON: {target_user_id, remark}
      - remark 为空字符串表示清除备注
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)

    if request.method == 'GET':
        try:
            target_user_id = int(request.args.get('target_user_id') or 0)
        except Exception:
            target_user_id = 0
        if target_user_id <= 0:
            return jsonify({'status': 'error', 'message': 'target_user_id 不合法'}), 400
        # 允许查询"自己"的备注（一般为空），避免前端误传自己 id 时直接报错
        if target_user_id == uid:
            return jsonify({'status': 'success', 'remark': ''})

        row = db.session.query(UserRemark.remark).filter_by(
            owner_user_id=uid, target_user_id=target_user_id
        ).first()
        return jsonify({'status': 'success', 'remark': (row.remark if row else '')})

    data = request.json or {}
    try:
        target_user_id = int(data.get('target_user_id') or 0)
    except Exception:
        target_user_id = 0
    remark = (data.get('remark') or '').strip()

    if target_user_id <= 0:
        return jsonify({'status': 'error', 'message': 'target_user_id 不合法'}), 400
    # 禁止给自己设置备注（没有意义，也容易误操作）
    if target_user_id == uid:
        return jsonify({'status': 'error', 'message': '不能给自己设置备注'}), 400
    if len(remark) > 30:
        return jsonify({'status': 'error', 'message': '备注过长（最多30字）'}), 400

    # 清除备注
    if remark == '':
        db.session.query(UserRemark).filter_by(
            owner_user_id=uid, target_user_id=target_user_id
        ).delete()
        db.session.commit()
        return jsonify({'status': 'success', 'remark': ''})

    # UPSERT
    existing = db.session.query(UserRemark).filter_by(
        owner_user_id=uid, target_user_id=target_user_id
    ).first()
    if existing:
        existing.remark = remark
        existing.updated_at = now_bj()
    else:
        db.session.add(UserRemark(
            owner_user_id=uid, target_user_id=target_user_id, remark=remark,
            created_at=now_bj(), updated_at=now_bj(),
        ))
    db.session.commit()
    return jsonify({'status': 'success', 'remark': remark})


@chat_api_bp.route('/chat/user_profile')
@limiter.limit("120/minute")
def chat_user_profile():
    """聊天页查看对方资料（类似微信好友资料）

    GET /api/chat/user_profile?user_id=xx
    返回：
      - user: {id, username, avatar, contact, college, created_at}
      - remark: 我对TA的备注（可为空）
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    try:
        target_user_id = int(request.args.get('user_id') or 0)
    except Exception:
        target_user_id = 0

    if target_user_id <= 0:
        return jsonify({'status': 'error', 'message': 'user_id 不合法'}), 400

    u = db.session.query(
        User.id, User.username, User.avatar, User.contact, User.college, User.created_at
    ).filter_by(id=target_user_id).first()
    if not u:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404

    # 备注（仅对方时才返回；自己则为空）
    remark = ''
    if target_user_id != uid:
        r = db.session.query(UserRemark.remark).filter_by(
            owner_user_id=uid, target_user_id=target_user_id
        ).first()
        remark = (r.remark if r else '')

    user_dict = {
        'id': u.id,
        'username': u.username,
        'avatar': u.avatar,
        'contact': u.contact,
        'college': u.college,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    }
    return jsonify({'status': 'success', 'user': user_dict, 'remark': remark})



@chat_api_bp.route('/chat/messages')
@limiter.limit("120/minute")
def chat_messages():
    """拉取会话消息（增量）并推进已读。

    关键点：已读推进应当以"当前会话的最新消息 id"为准，而不是仅推进到本次返回的最后一条。

    否则会出现：
    - 其他轮询/页面（如首页 /api/chat/unread_count）仍显示未读
    - 当 after_id 很大或 limit 较小导致返回为空时，已读永远无法推进
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    conversation_id = int(request.args.get('conversation_id') or 0)
    after_id = int(request.args.get('after_id') or 0)
    limit = int(request.args.get('limit') or 50)
    limit = max(1, min(limit, 200))

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400

    if not _is_member(conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权访问该会话'}), 403

    rows = (
        db.session.query(
            ChatMessage.id,
            ChatMessage.conversation_id,
            ChatMessage.sender_id,
            User.username.label('sender_username'),
            User.avatar.label('sender_avatar'),
            ChatMessage.content,
            ChatMessage.content_type,
            ChatMessage.created_at,
        )
        .outerjoin(User, User.id == ChatMessage.sender_id)
        .filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.id > after_id,
        )
        .order_by(ChatMessage.id.asc())
        .limit(limit)
        .all()
    )

    # 更新已读到当前会话的最新消息ID（无论是否有新消息）
    latest_msg = db.session.query(
        func.coalesce(func.max(ChatMessage.id), 0).label('max_id')
    ).filter(ChatMessage.conversation_id == conversation_id).first()

    if latest_msg and latest_msg.max_id > 0:
        member = db.session.query(ChatMember).filter_by(
            conversation_id=conversation_id, user_id=uid
        ).first()
        if member and (member.last_read_message_id or 0) < latest_msg.max_id:
            member.last_read_message_id = latest_msg.max_id
            db.session.commit()

    data = [
        {
            'id': r.id,
            'conversation_id': r.conversation_id,
            'sender_id': r.sender_id,
            'sender_username': r.sender_username,
            'sender_avatar': r.sender_avatar,
            'content': r.content,
            'content_type': r.content_type,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return jsonify({'status': 'success', 'data': data})


@chat_api_bp.route('/chat/messages/send', methods=['POST'])
@limiter.limit("30/minute")
def chat_send_message():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    data = request.json or {}
    conversation_id = int(data.get('conversation_id') or 0)
    content = (data.get('content') or '').strip()

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400
    if not content:
        return jsonify({'status': 'error', 'message': '消息不能为空'}), 400
    if len(content) > 2000:
        return jsonify({'status': 'error', 'message': '消息过长（最多2000字）'}), 400

    if not _is_member(conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权发送到该会话'}), 403

    mid = _insert_message_and_update(conversation_id, uid, content, 'text')
    return jsonify({'status': 'success', 'message_id': mid})



@chat_api_bp.route('/chat/messages/upload_image', methods=['POST'])
@limiter.limit("10/minute")
def chat_upload_image():
    """上传聊天图片并作为一条图片消息写入会话

    multipart/form-data:
      - conversation_id
      - image (file)  主图（建议前端已压缩）
      - thumb (file) 可选缩略图（用于列表展示，减少拉取流量）
      - width/height 可选（主图宽高）

    返回：
      - url: 主图URL
      - thumb: 缩略图URL（如有）
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    try:
        conversation_id = int(request.form.get('conversation_id') or 0)
    except Exception:
        conversation_id = 0

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400

    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': '缺少图片文件'}), 400

    f = request.files['image']
    if not f or not f.filename:
        return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    if not _allowed_image(f.filename):
        return jsonify({'status': 'error', 'message': '不支持的图片类型'}), 400

    thumb_f = request.files.get('thumb')
    if thumb_f and thumb_f.filename and (not _allowed_image(thumb_f.filename)):
        return jsonify({'status': 'error', 'message': '不支持的缩略图类型'}), 400

    try:
        width = int(request.form.get('width') or 0)
    except Exception:
        width = 0
    try:
        height = int(request.form.get('height') or 0)
    except Exception:
        height = 0

    if not _is_member(conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权发送到该会话'}), 403

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    chat_dir = os.path.join(upload_root, 'chat')
    os.makedirs(chat_dir, exist_ok=True)

    # 保存主图
    ext = f.filename.rsplit('.', 1)[1].lower()
    fname = secure_filename(f"chat_{conversation_id}_{uid}_{uuid.uuid4().hex[:10]}.{ext}")
    abs_path = os.path.join(chat_dir, fname)
    f.save(abs_path)
    url = f"/uploads/chat/{fname}"

    # 保存缩略图（可选）
    thumb_url = None
    if thumb_f and thumb_f.filename:
        thumb_ext = thumb_f.filename.rsplit('.', 1)[1].lower()
        thumb_name = secure_filename(f"chat_{conversation_id}_{uid}_{uuid.uuid4().hex[:10]}_thumb.{thumb_ext}")
        thumb_abs = os.path.join(chat_dir, thumb_name)
        thumb_f.save(thumb_abs)
        thumb_url = f"/uploads/chat/{thumb_name}"

    # content：兼容展示与扩展，image 类型存 JSON
    content_obj = {
        'url': url,
        'thumb': thumb_url,
        'w': width if width > 0 else None,
        'h': height if height > 0 else None,
    }
    content_str = json.dumps(content_obj, ensure_ascii=False)

    mid = _insert_message_and_update(conversation_id, uid, content_str, 'image')
    return jsonify({'status': 'success', 'message_id': mid, 'url': url, 'thumb': thumb_url})



@chat_api_bp.route('/chat/messages/upload_audio', methods=['POST'])
@limiter.limit("10/minute")
def chat_upload_audio():
    """上传聊天语音并作为一条语音消息写入会话

    multipart/form-data:
      - conversation_id
      - audio (file)  建议 webm/ogg/wav/mp3/m4a
      - duration 可选（秒）

    返回：
      - url: 语音URL
      - duration: 秒
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    try:
        conversation_id = int(request.form.get('conversation_id') or 0)
    except Exception:
        conversation_id = 0

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400

    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'message': '缺少语音文件'}), 400

    f = request.files['audio']
    if not f or not f.filename:
        return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    if not _allowed_audio(f.filename):
        return jsonify({'status': 'error', 'message': '不支持的语音类型'}), 400

    try:
        duration = float(request.form.get('duration') or 0)
    except Exception:
        duration = 0

    if not _is_member(conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权发送到该会话'}), 403

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    chat_dir = os.path.join(upload_root, 'chat')
    os.makedirs(chat_dir, exist_ok=True)

    ext = f.filename.rsplit('.', 1)[1].lower()
    base = secure_filename(f"chat_{conversation_id}_{uid}_{uuid.uuid4().hex[:10]}")

    # 1) 先保存原始文件
    raw_name = f"{base}.{ext}"
    raw_abs = os.path.join(chat_dir, raw_name)
    f.save(raw_abs)
    raw_url = f"/uploads/chat/{raw_name}"

    # 2) 尝试转码为 m4a（AAC），以获得 iOS/安卓最佳兼容；失败则回退转 mp3
    m4a_name = f"{base}.m4a"
    m4a_abs = os.path.join(chat_dir, m4a_name)
    m4a_url = f"/uploads/chat/{m4a_name}"

    mp3_name = f"{base}.mp3"
    mp3_abs = os.path.join(chat_dir, mp3_name)
    mp3_url = f"/uploads/chat/{mp3_name}"

    m4a_ok = False
    mp3_ok = False
    transcode_err = ''

    # 先转 m4a
    try:
        ok, err = _transcode_to_m4a(raw_abs, m4a_abs)
        m4a_ok = bool(ok)
        transcode_err = err or ''
    except Exception as e:
        m4a_ok = False
        transcode_err = str(e)

    if not m4a_ok:
        # 清理可能的残留
        try:
            if os.path.exists(m4a_abs):
                os.remove(m4a_abs)
        except Exception:
            pass

        # 回退转 mp3
        try:
            ok2, err2 = _transcode_to_mp3(raw_abs, mp3_abs)
            mp3_ok = bool(ok2)
            transcode_err = err2 or transcode_err
        except Exception as e:
            mp3_ok = False
            transcode_err = str(e)

        if not mp3_ok:
            try:
                if os.path.exists(mp3_abs):
                    os.remove(mp3_abs)
            except Exception:
                pass

        current_app.logger.warning(
            f"audio transcode failed(m4a) fallback(mp3)={'ok' if mp3_ok else 'failed'}: conv={conversation_id} uid={uid} raw={raw_name} err={transcode_err}"
        )

    # content：存 raw + m4a/mp3（如有），前端播放优先：m4a > mp3 > raw
    best_url = m4a_url if m4a_ok else (mp3_url if mp3_ok else raw_url)
    content_obj = {
        'url': best_url,
        'url_raw': raw_url,
        'url_m4a': (m4a_url if m4a_ok else None),
        'url_mp3': (mp3_url if mp3_ok else None),
        'duration': duration if duration > 0 else None,
    }
    content_str = json.dumps(content_obj, ensure_ascii=False)

    mid = _insert_message_and_update(conversation_id, uid, content_str, 'audio')
    return jsonify({
        'status': 'success',
        'message_id': mid,
        'url': content_obj.get('url'),
        'url_raw': content_obj.get('url_raw'),
        'url_m4a': content_obj.get('url_m4a'),
        'url_mp3': content_obj.get('url_mp3'),
        'duration': duration,
        'transcoded': bool(content_obj.get('url_m4a') or content_obj.get('url_mp3')),
    })



@chat_api_bp.route('/chat/messages/send_question', methods=['POST'])
@limiter.limit("30/minute")
def chat_send_question():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    data = request.json or {}
    conversation_id = int(data.get('conversation_id') or 0)
    question_id = int(data.get('question_id') or 0)

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400
    if question_id <= 0:
        return jsonify({'status': 'error', 'message': 'question_id 不合法'}), 400

    if not _is_member(conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权发送到该会话'}), 403

    # 获取题目信息
    q = (
        db.session.query(
            Question.id,
            Question.type,
            Question.content,
            Question.options,
            Question.answer,
            Question.analysis,
            Question.tags,
            Question.difficulty,
            Question.image_path,
            Subject.name.label('subject_name'),
        )
        .outerjoin(Subject, Question.subject_id == Subject.id)
        .filter(Question.id == question_id)
        .first()
    )
    if not q:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    # PQF -> 兼容字段（q_type/答案字符串/填空 __）
    from app.core.utils.portable_question_format import portable_question_to_internal
    import json as _json

    portable = {
        "id": q.id,
        "type": q.type or "",
        "content": q.content or "",
        "options": _safe_load(q.options, []),
        "answer": _safe_load(q.answer, []),
        "analysis": q.analysis or "",
        "tags": _safe_load(q.tags, []),
        "difficulty": q.difficulty if q.difficulty is not None else 1,
    }
    internal, _errors = portable_question_to_internal(portable, scope="question_center")

    # 解析 options（统一入口）
    options_payload = []
    try:
        current_app.logger.info(f"[send_question] qid={q.id} raw_options={internal.get('options')}")
    except Exception:
        pass

    try:
        options_payload = parse_options(internal.get('options'))
    except Exception as _e:
        options_payload = []
        try:
            current_app.logger.warning(f"[send_question] qid={q.id} options_parse_failed err={_e}")
        except Exception:
            pass

    try:
        current_app.logger.info(f"[send_question] qid={q.id} options_payload_len={len(options_payload)} head={options_payload[:2]}")
    except Exception:
        pass

    content_obj = {
        'id': q.id,
        'content': internal.get('content') or (q.content or ''),
        'type': internal.get('q_type') or '',
        'subject': q.subject_name or '',
        'options': options_payload,
        'answer': internal.get('answer') or '',
        'explanation': internal.get('explanation') or '',
        'image_path': (q.image_path or ''),
        'has_full_data': True,
    }
    content_str = json.dumps(content_obj, ensure_ascii=False)

    mid = _insert_message_and_update(conversation_id, uid, content_str, 'question')
    return jsonify({'status': 'success', 'message_id': mid})



@chat_api_bp.route('/chat/question/<int:question_id>')
@limiter.limit("120/minute")
def chat_get_question_detail(question_id: int):
    """获取题目完整信息（用于历史题目卡片弹层补全）"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    q = (
        db.session.query(
            Question.id,
            Question.type,
            Question.content,
            Question.options,
            Question.answer,
            Question.analysis,
            Question.tags,
            Question.difficulty,
            Question.image_path,
            Subject.name.label('subject_name'),
        )
        .outerjoin(Subject, Question.subject_id == Subject.id)
        .filter(Question.id == int(question_id))
        .first()
    )
    if not q:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    from app.core.utils.portable_question_format import portable_question_to_internal
    import json as _json

    portable = {
        "id": q.id,
        "type": q.type or "",
        "content": q.content or "",
        "options": _safe_load(q.options, []),
        "answer": _safe_load(q.answer, []),
        "analysis": q.analysis or "",
        "tags": _safe_load(q.tags, []),
        "difficulty": q.difficulty if q.difficulty is not None else 1,
    }
    internal, _errors = portable_question_to_internal(portable, scope="question_center")

    options_payload = []
    try:
        options_payload = parse_options(internal.get('options'))
    except Exception as _e:
        options_payload = []
        try:
            current_app.logger.warning(f"[get_question] qid={q.id} options_parse_failed err={_e}")
        except Exception:
            pass

    try:
        current_app.logger.info(f"[get_question] qid={q.id} options_payload_len={len(options_payload)} head={options_payload[:2]}")
    except Exception:
        pass

    return jsonify({
        'status': 'success',
        'question': {
            'id': q.id,
            'content': internal.get('content') or (q.content or ''),
            'type': internal.get('q_type') or '',
            'subject': q.subject_name or '',
            'options': options_payload,
            'answer': internal.get('answer') or '',
            'explanation': internal.get('explanation') or '',
            'image_path': (q.image_path or ''),
            'has_full_data': True,
        }
    })


@chat_api_bp.route('/chat/unread_count')
@limiter.limit("120/minute")
def chat_unread_count():
    """首页角标等（可选）"""
    if not session.get('user_id'):
        return jsonify({'status': 'success', 'count': 0})

    uid = session.get('user_id')

    # 说明：历史上可能存在重复的 direct 私聊会话（尤其 direct_pair_key 为空的遗留数据）。
    # 前端会话列表会按 peer_user_id 去重显示"最新的一条"，但首页角标如果直接对所有会话求和，
    # 就会把这些隐藏的旧会话也算进去，造成角标长期不归零。
    #
    # 这里做"按 pair 去重"：
    # - 对 direct：按 direct_pair_key 分组，只取 updated_at 最新的会话参与统计
    # - 对非 direct：按会话 id 直接参与统计
    #
    # 使用 CTE + ROW_NUMBER 实现去重
    gkey = func.coalesce(
        ChatConversation.direct_pair_key,
        db.cast(ChatConversation.id, db.Text),
    ).label('gkey')

    my_convs = (
        db.session.query(
            ChatConversation.id.label('conversation_id'),
            ChatConversation.c_type,
            ChatConversation.updated_at,
            gkey,
        )
        .join(ChatMember, (ChatMember.conversation_id == ChatConversation.id) & (ChatMember.user_id == uid))
        .subquery('my_convs')
    )

    ranked = (
        db.session.query(
            my_convs.c.conversation_id,
            func.row_number().over(
                partition_by=my_convs.c.gkey,
                order_by=[my_convs.c.updated_at.desc(), my_convs.c.conversation_id.desc()],
            ).label('rn'),
        )
        .subquery('ranked')
    )

    latest_conv_ids = (
        db.session.query(ranked.c.conversation_id)
        .filter(ranked.c.rn == 1)
        .subquery('latest_conv_ids')
    )

    # 对每个去重后的会话，统计未读消息数
    cm2 = db.aliased(ChatMember, name='cm2')
    total_unread = (
        db.session.query(func.coalesce(func.count(ChatMessage.id), 0))
        .join(latest_conv_ids, ChatMessage.conversation_id == latest_conv_ids.c.conversation_id)
        .join(cm2, (cm2.conversation_id == ChatMessage.conversation_id) & (cm2.user_id == uid))
        .filter(
            ChatMessage.id > func.coalesce(cm2.last_read_message_id, 0),
            ChatMessage.sender_id != uid,
        )
        .scalar()
    )

    return jsonify({'status': 'success', 'count': int(total_unread or 0)})


@chat_api_bp.route('/chat/badge_counts')
@limiter.limit("120/minute")
def chat_badge_counts():
    """合并端点：一次返回聊天未读 + 论坛互动未读（替代前端两次请求）"""
    if not session.get('user_id'):
        return jsonify({'status': 'success', 'data': {'chat_unread': 0, 'interact_unread': 0, 'total': 0}})

    uid = session.get('user_id')

    # 聊天未读（复用 chat_unread_count 的逻辑）
    gkey = func.coalesce(
        ChatConversation.direct_pair_key,
        db.cast(ChatConversation.id, db.Text),
    ).label('gkey')

    my_convs = (
        db.session.query(
            ChatConversation.id.label('conversation_id'),
            ChatConversation.c_type,
            ChatConversation.updated_at,
            gkey,
        )
        .join(ChatMember, (ChatMember.conversation_id == ChatConversation.id) & (ChatMember.user_id == uid))
        .subquery('my_convs_badge')
    )

    ranked = (
        db.session.query(
            my_convs.c.conversation_id,
            func.row_number().over(
                partition_by=my_convs.c.gkey,
                order_by=[my_convs.c.updated_at.desc(), my_convs.c.conversation_id.desc()],
            ).label('rn'),
        )
        .subquery('ranked_badge')
    )

    latest_conv_ids = (
        db.session.query(ranked.c.conversation_id)
        .filter(ranked.c.rn == 1)
        .subquery('latest_conv_ids_badge')
    )

    cm2 = db.aliased(ChatMember, name='cm2_badge')
    chat_unread = (
        db.session.query(func.coalesce(func.count(ChatMessage.id), 0))
        .join(latest_conv_ids, ChatMessage.conversation_id == latest_conv_ids.c.conversation_id)
        .join(cm2, (cm2.conversation_id == ChatMessage.conversation_id) & (cm2.user_id == uid))
        .filter(
            ChatMessage.id > func.coalesce(cm2.last_read_message_id, 0),
            ChatMessage.sender_id != uid,
        )
        .scalar()
    ) or 0

    # 论坛互动未读
    interact_unread = db.session.execute(text(
        "SELECT COUNT(*) FROM forum_notifications WHERE user_id = :uid AND is_read = false"
    ), {'uid': uid}).scalar() or 0

    total = int(chat_unread) + int(interact_unread)
    return jsonify({'status': 'success', 'data': {
        'chat_unread': int(chat_unread),
        'interact_unread': int(interact_unread),
        'total': total,
    }})
# api_follow 已迁移至 forum 模块 (forum/routes/api_follow.py)
from . import api_interactions  # noqa: F401,E402
