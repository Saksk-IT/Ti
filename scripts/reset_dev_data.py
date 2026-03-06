#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开发环境用户数据重置 + 种子数据构造脚本。

功能概述：
- 清除数据库中所有用户相关的数据（用户、私聊、个人题库、论坛互动、刷题记录、考试记录等）。
- 构造一套用于开发/联调的模拟数据，覆盖：
  * 多种权限的用户
  * 每个用户的个人题库
  * 论坛版块/帖子/评论及互动
  * 用户之间的私聊会话与消息
  * 公共题库上的刷题与统计数据
  * 考试模板与考试历史
  * 系统通知与通知关闭记录

安全措施：
- 仅允许在 DEBUG 或 TESTING 环境下运行（防止误删生产数据）。
- 所有操作在一个事务中完成，任意步骤失败将整体回滚。

使用方式示例：
- 本地直接运行（默认 SQLite 或本机指定 DATABASE_URL）：
    python scripts/reset_dev_data.py

- Docker 开发环境（PostgreSQL）：
    docker compose -f compose.dev.yml exec web python scripts/reset_dev_data.py
"""

from __future__ import annotations

import os
import sys
import json
import math
import struct
import wave
from datetime import datetime, timedelta
from typing import Dict, List, Sequence, Tuple

from werkzeug.security import generate_password_hash
from flask import current_app
from sqlalchemy import inspect


def _add_project_root_to_path() -> None:
    """将项目根目录加入 sys.path，便于脚本独立运行。

    采用不可变风格：不返回值，不修改传入参数，仅通过 sys.path 追加新条目。
    """

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)


_add_project_root_to_path()

from app import create_app  # noqa: E402
from app.core.extensions import db  # noqa: E402
from app import models as m  # noqa: E402
from app.models.follow import (  # noqa: E402
    InteractionNotification,
    UserFollow,
)
from app.models.forum import ForumUpload  # noqa: E402


def _ensure_dev_or_test_env(app) -> None:
    """确保在开发或测试环境下运行脚本。

    - DEBUG=True 或 TESTING=True 视为安全环境。
    - 若为生产环境（非 debug 且非 testing），直接抛异常终止。
    """

    debug_flag = bool(app.config.get("DEBUG")) or bool(getattr(app, "debug", False))
    testing_flag = bool(app.config.get("TESTING"))
    if not debug_flag and not testing_flag:
        raise RuntimeError("安全保护：仅允许在开发/测试环境运行 reset_dev_data 脚本。")


def _pick_existing_image_url(upload_root: str) -> str:
    """从现有上传目录中挑选一张图片，返回可直接被前端访问的 URL。"""

    candidate_dirs = [
        os.path.join(upload_root, "forum"),
        os.path.join(upload_root, "question_images"),
        os.path.join(upload_root, "avatars"),
    ]
    allowed_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    for directory in candidate_dirs:
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            _, ext = os.path.splitext(name)
            if ext.lower() not in allowed_exts:
                continue
            relative_dir = os.path.basename(directory)
            return f"/uploads/{relative_dir}/{name}"

    return "/uploads/avatars/default-avatar.png"


def _ensure_seed_audio_url(upload_root: str) -> str:
    """生成一个可复用的短语音文件，返回其 URL。

    使用标准库生成一个约 1.2 秒的 wav 音频，避免依赖 ffmpeg。
    """

    chat_dir = os.path.join(upload_root, "chat")
    os.makedirs(chat_dir, exist_ok=True)

    filename = "seed_voice_demo.wav"
    abs_path = os.path.join(chat_dir, filename)
    if os.path.exists(abs_path):
        return f"/uploads/chat/{filename}"

    sample_rate = 16000
    duration_seconds = 1.2
    frequency = 660.0
    amplitude = 12000
    frame_count = int(sample_rate * duration_seconds)

    with wave.open(abs_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for index in range(frame_count):
            value = int(amplitude * math.sin(2.0 * math.pi * frequency * index / sample_rate))
            frames.extend(struct.pack("<h", value))
        wav_file.writeframes(frames)

    return f"/uploads/chat/{filename}"


def _clear_user_related_data() -> Dict[str, int]:
    """严格清除除系统题库/题目外的所有业务数据。

    保留内容：
    - subjects（系统题库分类）
    - questions（系统题目）
    - schema_migrations（迁移元数据）

    返回一个字典，记录每个表删除的行数，便于最终统计输出。
    """

    deleted_counts: Dict[str, int] = {}
    inspector = inspect(db.engine)

    def _bulk_delete(model) -> int:
        table = getattr(model, "__tablename__", model.__name__)
        if not inspector.has_table(table):
            deleted_counts[table] = 0
            return 0
        q = model.query
        # 使用 bulk delete，避免逐条加载 ORM 实例
        rows = q.delete(synchronize_session=False)
        deleted_counts[table] = int(rows or 0)
        return deleted_counts[table]

    # 删除顺序：先子表后父表，确保满足外键约束
    # --- Chat & 私聊 ---
    _bulk_delete(m.ChatMessage)
    _bulk_delete(m.ChatMember)
    _bulk_delete(m.ChatConversation)
    _bulk_delete(m.UserRemark)

    # --- 论坛相关 ---
    _bulk_delete(m.ForumLike)
    _bulk_delete(m.ForumFavorite)
    _bulk_delete(m.ForumReaction)
    _bulk_delete(m.ForumPollVote)
    _bulk_delete(m.ForumReport)
    _bulk_delete(m.ForumMention)
    _bulk_delete(ForumUpload)
    _bulk_delete(m.ForumComment)
    _bulk_delete(m.ForumPost)
    _bulk_delete(m.ForumUserBan)
    _bulk_delete(m.ForumBoard)

    # --- 关注与互动通知 ---
    _bulk_delete(InteractionNotification)
    _bulk_delete(UserFollow)

    # --- 用户题库（个人题库）---
    _bulk_delete(m.UserBankFavorite)
    _bulk_delete(m.UserBankMistake)
    _bulk_delete(m.UserBankAnswer)
    _bulk_delete(m.PublicBankUser)
    _bulk_delete(m.BankShareRecord)
    _bulk_delete(m.BankShare)
    _bulk_delete(m.UserBankQuestion)
    _bulk_delete(m.UserQuestionBank)
    _bulk_delete(m.UserBankCategory)

    # --- Quiz / 刷题数据 ---
    _bulk_delete(m.Favorite)
    _bulk_delete(m.Mistake)
    _bulk_delete(m.UserAnswer)
    _bulk_delete(m.UserProgress)
    _bulk_delete(m.UserCheckin)
    _bulk_delete(m.UserQuizStats)

    # --- 学习/复习记录 ---
    _bulk_delete(m.StudyReview)
    _bulk_delete(m.StudyLearning)

    # --- 编程题相关 ---
    _bulk_delete(m.CodeDraft)
    _bulk_delete(m.CodingStatistics)
    _bulk_delete(m.CodeSubmission)
    _bulk_delete(m.UserCodingStats)
    _bulk_delete(m.CodingQuestion)
    _bulk_delete(m.CodingSubject)

    # --- 考试相关 ---
    _bulk_delete(m.ExamQuestion)
    _bulk_delete(m.ExamTemplate)
    _bulk_delete(m.Exam)

    # --- 通知与弹窗 ---
    _bulk_delete(m.NotificationDismissal)
    _bulk_delete(m.Notification)
    _bulk_delete(m.PopupView)
    _bulk_delete(m.PopupDismissal)
    _bulk_delete(m.Popup)

    # --- 用户在系统辅助表中的数据 ---
    _bulk_delete(m.SystemConfig)
    _bulk_delete(m.UserQuestionTagItem)
    _bulk_delete(m.UserSubject)

    # --- 学科相关的去重/缓存数据与用户强相关，这里也一并清理 ---
    _bulk_delete(m.DuplicateCheckRecord)
    _bulk_delete(m.ReinforceSimilarCache)

    # --- 邮箱验证码 ---
    _bulk_delete(m.EmailVerificationCode)

    # --- 最后删除用户自身 ---
    _bulk_delete(m.User)

    return deleted_counts


def _seed_users() -> Dict[str, m.User]:
    """创建一批用于开发的模拟用户，包含不同权限与状态。

    返回以用户名为键、User 实例为值的映射。
    """

    now = datetime.utcnow()
    password_plain = "DevPass123!"
    password_hash = generate_password_hash(password_plain)

    # 说明：所有用户统一密码，便于开发登录；真实环境请勿沿用
    base_kwargs = {
        "password_hash": password_hash,
        "created_at": now,
        "last_active": now,
        "email_verified": True,
        "email_verified_at": now,
        "phone_verified": True,
        "phone_verified_at": now,
        "has_password_set": True,
    }

    def _build_user(username: str, **extra) -> m.User:
        # 显式写入 username 字段，避免出现空用户名导致的约束错误
        merged = {"username": username, **base_kwargs, **extra}
        return m.User(**merged)

    users: List[m.User] = [
        _build_user(
            "admin",
            email="admin@example.dev",
            phone="13900000001",
            is_admin=True,
            is_subject_admin=True,
            is_notification_admin=True,
        ),
        _build_user(
            "subject_admin",
            email="subject_admin@example.dev",
            phone="13900000002",
            is_subject_admin=True,
            is_notification_admin=False,
        ),
        _build_user(
            "notification_admin",
            email="notification_admin@example.dev",
            phone="13900000003",
            is_subject_admin=False,
            is_notification_admin=True,
        ),
        _build_user(
            "teacher",
            email="teacher@example.dev",
            phone="13900000004",
        ),
        _build_user(
            "student_a",
            email="student_a@example.dev",
            phone="13900000005",
        ),
        _build_user(
            "student_b",
            email="student_b@example.dev",
            phone="13900000006",
        ),
        _build_user(
            "locked_user",
            email="locked_user@example.dev",
            phone="13900000007",
            is_locked=True,
        ),
    ]

    for user in users:
        db.session.add(user)

    db.session.flush()  # 获取自增 ID

    return {u.username: u for u in users}


def _seed_subjects_and_questions(admin_user: m.User) -> Tuple[List[m.Subject], List[m.Question]]:
    """初始化若干公共科目与基础题目，供公共题库和考试使用。

    为了兼容已经存在的开发/测试数据库：
    - 不新建 Subject 记录，只复用当前库中已有科目；
    - 仅在这些科目下插入少量示例题目，避免主键/唯一约束冲突。
    """

    from json import dumps

    # 复用已有科目：最多取前两个科目作为示例科目
    subjects: List[m.Subject] = list(m.Subject.query.order_by(m.Subject.id).limit(2))
    if not subjects:
        # 极端情况下数据库里没有任何科目，则跳过题目种子数据
        return [], []

    questions: List[m.Question] = []

    def _add_question(subject: m.Subject, content: str, options: Sequence[str], answer_indices: Sequence[int], tags: Sequence[str], difficulty: int = 1) -> None:
        answer_keys = [str(idx) for idx in answer_indices]
        q = m.Question(
            subject_id=subject.id,
            type="single" if len(answer_indices) == 1 else "multi",
            content=content,
            options=dumps(list(options), ensure_ascii=False),
            answer=dumps(answer_keys, ensure_ascii=False),
            analysis="示例解析：用于开发环境演示。",
            tags=dumps(list(tags), ensure_ascii=False),
            difficulty=difficulty,
            created_by=admin_user.id,
            updated_by=admin_user.id,
        )
        db.session.add(q)
        questions.append(q)

    # 数据结构示例题
    ds = subjects[0]
    _add_question(
        ds,
        "以下哪种数据结构最适合实现 LRU 缓存？",
        ["数组", "链表 + 哈希表", "栈", "队列"],
        [1],
        ["LRU", "缓存", "哈希表"],
        difficulty=2,
    )
    _add_question(
        ds,
        "下面关于二叉搜索树（BST）的说法，正确的是？",
        ["任意节点左子树都比右子树大", "中序遍历结果有序", "先序遍历结果有序", "层序遍历结果有序"],
        [1],
        ["BST", "中序遍历"],
    )

    # 计算机网络示例题（若不存在第二个科目，则复用第一个）
    net = subjects[1] if len(subjects) > 1 else subjects[0]
    _add_question(
        net,
        "HTTP 状态码 404 的含义是？",
        ["服务器内部错误", "未授权", "未找到资源", "请求过多"],
        [2],
        ["HTTP", "状态码"],
    )
    _add_question(
        net,
        "下列哪些协议工作在应用层？",
        ["TCP", "IP", "HTTP", "DNS"],
        [2, 3],
        ["应用层", "协议"],
        difficulty=2,
    )

    db.session.flush()
    return subjects, questions


def _seed_personal_banks(users: Dict[str, m.User], questions: List[m.Question]) -> None:
    """为每个普通用户创建个人题库及若干自定义题目。"""

    from json import dumps

    owner_keys = [
        "admin",
        "subject_admin",
        "notification_admin",
        "teacher",
        "student_a",
        "student_b",
        "locked_user",
    ]
    owners = [users[k] for k in owner_keys if k in users]
    now = datetime.utcnow()
    public_banks: List[Tuple[m.User, m.UserQuestionBank]] = []

    bank_specs = {
        "admin": [
            ("系统巡检题库", "超级管理员维护的系统巡检与应急题库"),
            ("论坛运营题库", "超级管理员整理的论坛运营与审核题库"),
            ("综合联调题库", "超级管理员用于联调各端功能的综合题库"),
        ],
        "subject_admin": [("科目管理题库", "科目管理员公开分享的科目管理题库")],
        "notification_admin": [("通知运营题库", "通知管理员公开分享的通知运营题库")],
        "teacher": [("teacher 的专项训练", "teacher 公开分享的开发示例题库")],
        "student_a": [("student_a 的专项训练", "student_a 公开分享的开发示例题库")],
        "student_b": [("student_b 的专项训练", "student_b 公开分享的开发示例题库")],
        "locked_user": [("locked_user 的留档题库", "锁定用户的留档公开题库")],
    }

    for owner in owners:
        specs = bank_specs.get(owner.username) or [(f"{owner.username} 的专项训练", f"{owner.username} 公开分享的开发示例题库")]
        for bank_index, (bank_name, public_desc) in enumerate(specs, start=1):
            category = m.UserBankCategory(
                user_id=owner.id,
                name="个人错题本" if len(specs) == 1 else f"个人错题本{bank_index}",
                description=f"{owner.username} 在开发环境的个人错题本分类 {bank_index}",
            )
            db.session.add(category)
            db.session.flush()

            bank = m.UserQuestionBank(
                user_id=owner.id,
                category_id=category.id,
                name=bank_name,
                description="用于本地开发调试的示例题库",
                is_public=True,
                public_description=public_desc,
                allow_copy=True,
                public_at=now,
                status=1,
            )
            db.session.add(bank)
            db.session.flush()

            samples = [
                (
                    f"单选题示例{bank_index}：{owner.username} 题库中用于创建列表的是？",
                    ["{}", "[]", "()", "<>"],
                    [1],
                ),
                (
                    f"多选题示例{bank_index}：下列哪些属于 {owner.username} 题库中的关系型数据库？",
                    ["MySQL", "MongoDB", "PostgreSQL", "Redis"],
                    [0, 2],
                ),
            ]

            for content, opts, ans_idx in samples:
                q = m.UserBankQuestion(
                    bank_id=bank.id,
                    user_id=owner.id,
                    type="single" if len(ans_idx) == 1 else "multi",
                    content=content,
                    options=dumps(list(opts), ensure_ascii=False),
                    answer=dumps([str(i) for i in ans_idx], ensure_ascii=False),
                    analysis="个人题库示例题，用于本地开发。",
                    tags=dumps(["示例", "个人题库", owner.username], ensure_ascii=False),
                    difficulty=1,
                    source_type="custom",
                )
                db.session.add(q)

            bank.question_count = 2
            bank.public_use_count = 0
            bank.share_count = 0
            db.session.add(bank)
            public_banks.append((owner, bank))

    # 给公开个人题库补充一些“其他用户访问”的痕迹，便于前端验证公开状态与使用人数
    for owner, bank in public_banks:
        for other_user in owners:
            if other_user.id == owner.id:
                continue
            db.session.add(
                m.PublicBankUser(
                    bank_id=bank.id,
                    user_id=other_user.id,
                    last_access_at=now,
                    access_count=1,
                )
            )
            bank.public_use_count = int(bank.public_use_count or 0) + 1
        db.session.add(bank)

    db.session.flush()


def _seed_forum(users: Dict[str, m.User], subjects: List[m.Subject]) -> None:
    """初始化论坛版块、帖子、评论及互动数据。"""

    admin = users.get("admin")
    teacher = users.get("teacher")
    student_a = users.get("student_a")
    student_b = users.get("student_b")

    if not admin or not teacher or not student_a or not student_b:
        return

    ds_subject = subjects[0] if subjects else None

    boards: List[m.ForumBoard] = []

    # 科目关联版块：若已存在相同 slug，则复用
    if ds_subject is not None:
        existing_ds_board = m.ForumBoard.query.filter_by(slug="ds-board").first()
        if existing_ds_board is None:
            existing_ds_board = m.ForumBoard(
                name="数据结构讨论区",
                slug="ds-board",
                description="围绕数据结构刷题、考试的日常讨论。",
                board_type="subject",
                subject_id=ds_subject.id,
                created_by=admin.id,
            )
            db.session.add(existing_ds_board)
            db.session.flush()
        boards.append(existing_ds_board)

    # 自定义版块：同样尝试复用
    existing_study_board = m.ForumBoard.query.filter_by(slug="study-share").first()
    if existing_study_board is None:
        existing_study_board = m.ForumBoard(
            name="学习心得",
            slug="study-share",
            description="分享刷题心得与备考经验。",
            board_type="custom",
            created_by=admin.id,
        )
        db.session.add(existing_study_board)
        db.session.flush()
    boards.append(existing_study_board)

    if not boards:
        return

    study_board = existing_study_board

    # 管理员置顶贴
    post_announcement = m.ForumPost(
        board_id=study_board.id,
        author_id=admin.id,
        title="【公告】开发环境论坛示例数据",
        content="这是用于本地开发的论坛示例数据，你可以随意增删改查。",
        is_pinned=True,
        is_featured=True,
        tags=["公告", "示例数据"],
    )
    db.session.add(post_announcement)
    db.session.flush()

    # 教师发帖
    post_teacher = m.ForumPost(
        board_id=study_board.id,
        author_id=teacher.id,
        title="如何高效利用个人题库？",
        content="欢迎在本帖下交流你在个人题库中的整理习惯和刷题策略。",
        tags=["个人题库", "学习方法"],
    )
    db.session.add(post_teacher)
    db.session.flush()

    # 学生评论与互动
    comment_a = m.ForumComment(
        post_id=post_teacher.id,
        author_id=student_a.id,
        content="我会把做错的题单独集中到一个题库里反复练。",
    )
    db.session.add(comment_a)
    db.session.flush()

    comment_b_reply = m.ForumComment(
        post_id=post_teacher.id,
        author_id=student_b.id,
        parent_id=comment_a.id,
        reply_to_user_id=student_a.id,
        content="我还会给错题打标签，方便按知识点复习。",
    )
    db.session.add(comment_b_reply)
    db.session.flush()

    # 点赞、收藏与表情回应
    db.session.add(m.ForumLike(user_id=student_a.id, target_type="post", target_id=post_teacher.id))
    db.session.add(m.ForumLike(user_id=student_b.id, target_type="post", target_id=post_teacher.id))
    db.session.add(m.ForumFavorite(user_id=student_a.id, post_id=post_teacher.id))
    db.session.add(m.ForumReaction(user_id=student_b.id, target_type="comment", target_id=comment_a.id, emoji="👍"))

    # 投票示例
    poll_post = m.ForumPost(
        board_id=study_board.id,
        author_id=teacher.id,
        title="你更常在什么时候刷题？",
        content="选择一个你最常刷题的时间段～",
        poll={
            "question": "你更常在什么时候刷题？",
            "options": ["早上", "下午", "晚上", "周末集中刷"],
            "multiple": False,
        },
    )
    db.session.add(poll_post)
    db.session.flush()

    db.session.add(m.ForumPollVote(post_id=poll_post.id, user_id=student_a.id, option_index=2))
    db.session.add(m.ForumPollVote(post_id=poll_post.id, user_id=student_b.id, option_index=3))

    # @ 提及
    db.session.add(
        m.ForumMention(
            source_type="comment",
            source_id=comment_b_reply.id,
            mentioned_user_id=student_a.id,
            mentioner_id=student_b.id,
        )
    )

    db.session.flush()


def _seed_private_chats(users: Dict[str, m.User], questions: List[m.Question]) -> None:
    """创建用户之间的私聊会话与消息记录。"""

    admin = users.get("admin")
    teacher = users.get("teacher")
    student_a = users.get("student_a")
    student_b = users.get("student_b")

    if not admin or not teacher or not student_a or not student_b:
        return

    now = datetime.utcnow()
    upload_root = current_app.config.get("UPLOAD_FOLDER")
    image_url = _pick_existing_image_url(upload_root)
    audio_url = _ensure_seed_audio_url(upload_root)

    question_payload = None
    if questions:
        seed_question = questions[0]
        question_payload = {
            "id": seed_question.id,
            "content": seed_question.content,
            "type": seed_question.type,
            "subject": "开发环境示例题",
            "options": [],
            "answer": seed_question.answer or "",
            "explanation": seed_question.analysis or "",
            "image_path": seed_question.image_path or image_url,
            "has_full_data": True,
        }

    def _create_direct_conversation(left_user: m.User, right_user: m.User, title: str) -> m.ChatConversation:
        pair_key = f"{min(left_user.id, right_user.id)}:{max(left_user.id, right_user.id)}"
        conv = m.ChatConversation(
            c_type="direct",
            title=title,
            direct_pair_key=pair_key,
            created_at=now,
            updated_at=now,
        )
        db.session.add(conv)
        db.session.flush()
        db.session.add(m.ChatMember(conversation_id=conv.id, user_id=left_user.id, role="owner"))
        db.session.add(m.ChatMember(conversation_id=conv.id, user_id=right_user.id, role="member"))
        return conv

    # 超级管理员与 teacher 的私聊（补齐全类型消息）
    conv_a = _create_direct_conversation(admin, teacher, "超级管理员与教师")
    messages_a = [
        m.ChatMessage(
            conversation_id=conv_a.id,
            sender_id=admin.id,
            content="我刚把开发环境数据重置好了，你那边帮我看看题库和论坛联调是否正常。",
            content_type="text",
            created_at=now - timedelta(minutes=10),
        ),
        m.ChatMessage(
            conversation_id=conv_a.id,
            sender_id=teacher.id,
            content="收到，我先从题库详情和考试流程开始回归。",
            content_type="text",
            created_at=now - timedelta(minutes=8),
        ),
        m.ChatMessage(
            conversation_id=conv_a.id,
            sender_id=admin.id,
            content=json.dumps(question_payload or {}, ensure_ascii=False),
            content_type="question",
            created_at=now - timedelta(minutes=7),
        ),
        m.ChatMessage(
            conversation_id=conv_a.id,
            sender_id=teacher.id,
            content=json.dumps({"url": image_url, "thumb": image_url, "w": 720, "h": 720}, ensure_ascii=False),
            content_type="image",
            created_at=now - timedelta(minutes=6),
        ),
        m.ChatMessage(
            conversation_id=conv_a.id,
            sender_id=admin.id,
            content=json.dumps({"url": audio_url, "url_raw": audio_url, "url_m4a": None, "url_mp3": None, "duration": 1.2}, ensure_ascii=False),
            content_type="audio",
            created_at=now - timedelta(minutes=5),
        ),
    ]
    for msg in messages_a:
        db.session.add(msg)

    # 超级管理员与 student_a 的私聊
    conv_b = _create_direct_conversation(admin, student_a, "超级管理员与 student_a")
    messages_b = [
        m.ChatMessage(
            conversation_id=conv_b.id,
            sender_id=admin.id,
            content="你重点帮我看看公共题库答题、错题和收藏状态有没有同步。",
            content_type="text",
            created_at=now - timedelta(minutes=5),
        ),
        m.ChatMessage(
            conversation_id=conv_b.id,
            sender_id=student_a.id,
            content="好的，我先测公共题库，再顺手看下个人题库公开页。",
            content_type="text",
            created_at=now - timedelta(minutes=3),
        ),
        m.ChatMessage(
            conversation_id=conv_b.id,
            sender_id=student_a.id,
            content=json.dumps({"url": image_url, "thumb": image_url, "w": 720, "h": 720}, ensure_ascii=False),
            content_type="image",
            created_at=now - timedelta(minutes=2),
        ),
    ]
    for msg in messages_b:
        db.session.add(msg)

    # 其他所有用户都与超级管理员建立私聊，保证主账号登录时能看到充分关联数据
    other_usernames = ["subject_admin", "notification_admin", "student_b", "locked_user"]
    for index, name in enumerate(other_usernames, start=1):
        peer = users.get(name)
        if peer is None:
            continue
        conv = _create_direct_conversation(admin, peer, f"超级管理员与 {name}")
        db.session.add(
            m.ChatMessage(
                conversation_id=conv.id,
                sender_id=admin.id,
                content=f"这里是与 {name} 的开发环境示例私聊，用于验证会话列表与消息加载。",
                content_type="text",
                created_at=now - timedelta(minutes=2 + index),
            )
        )
        if name == "subject_admin":
            db.session.add(
                m.ChatMessage(
                    conversation_id=conv.id,
                    sender_id=peer.id,
                    content=json.dumps(question_payload or {}, ensure_ascii=False),
                    content_type="question",
                    created_at=now - timedelta(minutes=1 + index),
                )
            )
        elif name == "notification_admin":
            db.session.add(
                m.ChatMessage(
                    conversation_id=conv.id,
                    sender_id=peer.id,
                    content=json.dumps({"url": image_url, "thumb": image_url, "w": 720, "h": 720}, ensure_ascii=False),
                    content_type="image",
                    created_at=now - timedelta(minutes=1 + index),
                )
            )
        elif name == "student_b":
            db.session.add(
                m.ChatMessage(
                    conversation_id=conv.id,
                    sender_id=peer.id,
                    content=json.dumps({"url": audio_url, "url_raw": audio_url, "url_m4a": None, "url_mp3": None, "duration": 1.2}, ensure_ascii=False),
                    content_type="audio",
                    created_at=now - timedelta(minutes=1 + index),
                )
            )
        else:
            db.session.add(
                m.ChatMessage(
                    conversation_id=conv.id,
                    sender_id=peer.id,
                    content="当前账号已被锁定，保留该会话用于验证锁定用户展示。",
                    content_type="text",
                    created_at=now - timedelta(minutes=1 + index),
                )
            )

    # 备注关系示例
    db.session.add(
        m.UserRemark(
            owner_user_id=admin.id,
            target_user_id=teacher.id,
            remark="负责协助超级管理员验证题库和考试流程。",
        )
    )
    db.session.add(
        m.UserRemark(
            owner_user_id=admin.id,
            target_user_id=student_a.id,
            remark="负责回归公共题库、错题与收藏联动。",
        )
    )

    db.session.flush()


def _seed_quiz_activity(users: Dict[str, m.User], questions: List[m.Question]) -> None:
    """为公共题库创建用户刷题记录、收藏、错题与学习记录。"""

    if not questions:
        return

    student_a = users.get("student_a")
    student_b = users.get("student_b")
    teacher = users.get("teacher")

    if not student_a or not student_b or not teacher:
        return

    now = datetime.utcnow()

    def _record_for_user(user: m.User, correct_indices: Sequence[int]) -> None:
        total_answered = 0

        for idx, q in enumerate(questions):
            is_correct = idx in correct_indices
            db.session.add(
                m.UserAnswer(
                    user_id=user.id,
                    question_id=q.id,
                    user_answer="示例作答",
                    is_correct=is_correct,
                    created_at=now - timedelta(minutes=idx + 1),
                )
            )

            # 收藏前两道题作为示例
            if idx < 2:
                db.session.add(m.Favorite(user_id=user.id, question_id=q.id))

            # 错题记录
            if not is_correct:
                db.session.add(
                    m.Mistake(
                        user_id=user.id,
                        question_id=q.id,
                        wrong_count=1,
                    )
                )

            # 学习/复习追踪
            db.session.add(
                m.StudyLearning(
                    user_id=user.id,
                    source="subject",
                    scope_id=q.subject_id or 0,
                    question_id=q.id,
                    streak=1 if is_correct else 0,
                    correct_count=1 if is_correct else 0,
                    wrong_count=0 if is_correct else 1,
                    last_result="correct" if is_correct else "wrong",
                    last_answered_at=now - timedelta(minutes=idx + 1),
                )
            )
            db.session.add(
                m.StudyReview(
                    user_id=user.id,
                    source="subject",
                    scope_id=q.subject_id or 0,
                    question_id=q.id,
                    review_level=1,
                    next_due_at=now + timedelta(days=1),
                    last_review_at=now,
                    last_rating="good" if is_correct else "again",
                    lapse_count=0 if is_correct else 1,
                )
            )

            total_answered += 1

        # 进度与签到示例
        db.session.add(
            m.UserProgress(
                user_id=user.id,
                p_key="subject:overview",
                data="示例进度：已完成基础练习。",
                updated_at=now,
            )
        )
        db.session.add(
            m.UserCheckin(
                user_id=user.id,
                checkin_date=now.strftime("%Y-%m-%d"),
                created_at=now,
            )
        )

        db.session.add(
            m.UserQuizStats(
                user_id=user.id,
                total_answered=total_answered,
                last_reset_at=now - timedelta(days=1),
                updated_at=now,
            )
        )

    # 不同用户有不同的正确率
    _record_for_user(student_a, correct_indices=[0, 1, 2])
    _record_for_user(student_b, correct_indices=[1, 3])
    _record_for_user(teacher, correct_indices=list(range(len(questions))))

    db.session.flush()


def _seed_exams(users: Dict[str, m.User], questions: List[m.Question]) -> None:
    """为用户创建考试模板与考试历史记录。"""

    if len(questions) < 2:
        return

    student_a = users.get("student_a")
    student_b = users.get("student_b")
    teacher = users.get("teacher")

    if not student_a or not student_b or not teacher:
        return

    from json import dumps

    now = datetime.utcnow()
    q_ids = [q.id for q in questions]

    template = m.ExamTemplate(
        user_id=teacher.id,
        title="数据结构与网络综合测试（示例）",
        config_json=dumps(
            {
                "duration_minutes": 30,
                "total_score": 100,
                "question_ids": q_ids,
            },
            ensure_ascii=False,
        ),
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )
    db.session.add(template)
    db.session.flush()

    def _create_exam(user: m.User, score: float, finished: bool) -> None:
        exam = m.Exam(
            user_id=user.id,
            subject="综合测试",
            duration_minutes=30,
            config_json=template.config_json,
            total_score=score,
            status="finished" if finished else "ongoing",
            started_at=now - timedelta(hours=2),
            submitted_at=now - timedelta(hours=1) if finished else None,
        )
        db.session.add(exam)
        db.session.flush()

        per_question_score = score / len(q_ids) if finished else 0

        for order_idx, q_id in enumerate(q_ids):
            db.session.add(
                m.ExamQuestion(
                    exam_id=exam.id,
                    question_id=q_id,
                    order_index=order_idx,
                    score_val=per_question_score,
                    user_answer="示例作答",
                    is_correct=True if finished else None,
                    answered_at=exam.submitted_at,
                )
            )

    _create_exam(student_a, score=86.0, finished=True)
    _create_exam(student_b, score=72.0, finished=True)
    _create_exam(student_b, score=0.0, finished=False)

    db.session.flush()


def _seed_notifications(users: Dict[str, m.User]) -> None:
    """创建系统通知和部分通知关闭记录。"""

    admin = users.get("admin")
    student_a = users.get("student_a")
    student_b = users.get("student_b")

    if not admin or not student_a or not student_b:
        return

    now = datetime.utcnow()

    notif_1 = m.Notification(
        title="系统维护通知",
        content="本地开发环境示例：今晚 23:00-23:30 进行数据库结构调试，无实际停机。",
        n_type="info",
        priority=10,
        is_active=True,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(days=7),
        created_by=admin.id,
    )
    notif_2 = m.Notification(
        title="新功能上线：个人题库导出",
        content="你可以在题库详情页导出个人题库到本地文件。",
        n_type="success",
        priority=5,
        is_active=True,
        start_at=now - timedelta(days=1),
        end_at=now + timedelta(days=30),
        created_by=admin.id,
    )

    db.session.add(notif_1)
    db.session.add(notif_2)
    db.session.flush()

    # 学生 A 已关闭维护通知
    db.session.add(
        m.NotificationDismissal(
            user_id=student_a.id,
            notification_id=notif_1.id,
            dismissed_at=now,
        )
    )

    db.session.flush()


def _seed_interaction_notifications(users: Dict[str, m.User]) -> None:
    """基于简单场景构造关注关系和互动通知。"""

    admin = users.get("admin")
    teacher = users.get("teacher")
    student_a = users.get("student_a")
    student_b = users.get("student_b")

    if not admin or not teacher or not student_a or not student_b:
        return

    now = datetime.utcnow()

    follows = [
        UserFollow(follower_id=student_a.id, following_id=teacher.id, created_at=now),
        UserFollow(follower_id=student_b.id, following_id=teacher.id, created_at=now),
        UserFollow(follower_id=teacher.id, following_id=admin.id, created_at=now),
    ]
    for f in follows:
        db.session.add(f)

    notifications = [
        InteractionNotification(
            user_id=teacher.id,
            actor_id=student_a.id,
            action_type="follow",
            target_type="user",
            target_id=teacher.id,
            content_preview="student_a 关注了你",
            is_read=False,
            created_at=now,
        ),
        InteractionNotification(
            user_id=teacher.id,
            actor_id=student_b.id,
            action_type="follow",
            target_type="user",
            target_id=teacher.id,
            content_preview="student_b 关注了你",
            is_read=True,
            created_at=now,
        ),
    ]
    for n in notifications:
        db.session.add(n)

    db.session.flush()


def _run_reset_and_seed() -> Dict[str, object]:
    """执行清库与造数的主流程，并返回简单统计信息。"""

    deleted = _clear_user_related_data()

    users = _seed_users()
    admin = users.get("admin")
    if not admin:
        raise RuntimeError("种子用户创建失败：缺少 admin 用户。")

    subjects, questions = _seed_subjects_and_questions(admin_user=admin)

    _seed_personal_banks(users, questions)
    _seed_forum(users, subjects)
    _seed_private_chats(users, questions)
    _seed_quiz_activity(users, questions)
    _seed_exams(users, questions)
    _seed_notifications(users)
    _seed_interaction_notifications(users)

    summary: Dict[str, object] = {
        "deleted_tables": deleted,
        "user_count": len(users),
        "subject_count": len(subjects),
        "question_count": len(questions),
    }
    return summary


def main() -> int:
    print("=" * 60)
    print("开发环境用户数据重置 + 种子数据构造工具")
    print("=" * 60)

    app = create_app()

    try:
        _ensure_dev_or_test_env(app)
    except Exception as exc:  # noqa: BLE001
        print(f"[安全终止] {exc}")
        return 1

    with app.app_context():
        try:
            summary: Dict[str, object]
            # 单事务执行：任一步骤抛错则整体回滚
            summary = _run_reset_and_seed()
            db.session.commit()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            print("\n[错误] 重置/种子数据构造失败：", exc)
            import traceback

            traceback.print_exc()
            return 1

    print("\n重置与种子数据构造已完成。统计信息：")
    deleted_tables: Dict[str, int] = summary.get("deleted_tables", {}) or {}
    for table, count in sorted(deleted_tables.items()):
        print(f"  - {table}: 删除 {count} 行")

    print(
        f"\n新建用户数量: {summary.get('user_count')}\n"
        f"公共科目数量: {summary.get('subject_count')}\n"
        f"公共题目数量: {summary.get('question_count')}"
    )

    print("\n提示：")
    print("  - 所有种子用户统一密码为: DevPass123!")
    print("  - 你可以使用 admin / student_a / student_b 等账号进行登录调试。")

    print("\n完成。")
    return 0


if __name__ == "__main__":  # pragma: no cover - 手动执行脚本入口
    raise SystemExit(main())
