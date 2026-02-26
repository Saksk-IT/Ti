# -*- coding: utf-8 -*-
"""聊天文件访问鉴权

拦截 ``chat/`` 前缀的上传文件，确保：
1. 用户已登录
2. 用户是该会话的成员
"""
from __future__ import annotations

import re
from typing import Optional

from flask import abort, session

# 文件名格式: chat_{conv_id}_{uid}_{hex}.ext  或  chat_{conv_id}_{uid}_{hex}_thumb.ext
_CHAT_FILE_RE = re.compile(r"^chat_(\d+)_(\d+)_[0-9a-f]+(?:_thumb)?\.\w+$")


def check_chat_file_access(filename: str) -> None:
    """检查当前用户是否有权访问聊天文件。

    仅拦截 ``chat/`` 前缀的文件路径；其他文件直接放行。

    Raises:
        abort(401): 未登录
        abort(403): 非会话成员
    """
    # 统一分隔符
    normalized = filename.replace("\\", "/")

    # 仅拦截 chat/ 目录下的文件
    if not normalized.startswith("chat/"):
        return

    basename = normalized.split("/")[-1]
    m = _CHAT_FILE_RE.match(basename)
    if not m:
        # 文件名不符合聊天文件格式，放行（可能是其他用途）
        return

    # 必须登录
    user_id = session.get("user_id")
    if not user_id:
        abort(401)

    conversation_id = int(m.group(1))
    uid = int(user_id)

    # 检查是否为会话成员
    from app.models.chat import ChatMember
    from app.core.extensions import db

    is_member = (
        db.session.query(ChatMember.id)
        .filter_by(conversation_id=conversation_id, user_id=uid)
        .first()
    )
    if not is_member:
        abort(403)
