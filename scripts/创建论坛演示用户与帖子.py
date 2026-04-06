#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建论坛演示用户与帖子。

用途：
- 在 Docker 开发环境数据库中补充几位真实感更强的演示用户；
- 复制本地准备好的头像/配图到 uploads 目录；
- 在论坛中创建若干带图片的帖子、评论、点赞、收藏与关注关系；
- 尽量保持幂等：重复执行时优先复用已创建的记录，不重复灌入同一批内容。

推荐执行方式：
    docker compose --env-file .env -f compose.dev.yml exec web \
      python scripts/创建论坛演示用户与帖子.py

前置资源：
- 将用户提供的头像目录内容复制到：var/import_assets/demo_avatars/
  容器内对应路径：/data/import_assets/demo_avatars/
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from werkzeug.security import generate_password_hash
from sqlalchemy import text


def _add_project_root_to_path() -> None:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)


_add_project_root_to_path()

from app import create_app  # noqa: E402
from app.core.extensions import db  # noqa: E402
from app import models as m  # noqa: E402
from app.models.quiz import UserProgress  # noqa: E402
from app.modules.forum.services import comment_service, post_service  # noqa: E402


DEMO_PASSWORD = 'ForumDemo2026!'
IMPORT_ASSET_DIR = Path('/data/import_assets/demo_avatars')
UPLOAD_ROOT = Path('/data/uploads')
AVATAR_UPLOAD_DIR = UPLOAD_ROOT / 'avatars'
FORUM_UPLOAD_DIR = UPLOAD_ROOT / 'forum'
PROFILE_EXTRA_KEY = 'user_profile_extra_v1'


@dataclass(frozen=True)
class DemoUserProfile:
    username: str
    email: str
    phone: str
    contact: str
    college: str
    signature: str
    avatar_source: str
    avatar_target: str
    created_at: str
    last_active: str


@dataclass(frozen=True)
class DemoPostSpec:
    author: str
    board_slug: str
    title: str
    markdown: str
    summary: str
    tags: tuple[str, ...]
    cover_source: str | None
    gallery_sources: tuple[str, ...]
    created_at: str
    updated_at: str
    view_count: int
    is_featured: bool = False


@dataclass(frozen=True)
class DemoCommentSpec:
    post_title: str
    author: str
    content: str
    created_at: str
    parent_content: str | None = None
    reply_to_user: str | None = None


DEMO_USERS: tuple[DemoUserProfile, ...] = (
    DemoUserProfile(
        username='林粤',
        email='yuelin.study@example.com',
        phone='13900001011',
        contact='微信：yuelin_notes｜邮箱：yuelin.study@example.com',
        college='华东师范大学 软件工程学院',
        signature='刷题不是做得多，而是复盘得细。',
        avatar_source='ff1f9f0c65514eb06ea8e792515026b1.jpg',
        avatar_target='avatar_demo_lin_yue.jpg',
        created_at='2025-10-18 21:30:00',
        last_active='2026-04-05 22:10:00',
    ),
    DemoUserProfile(
        username='周既白',
        email='jibai.zhou@example.com',
        phone='13900001012',
        contact='微信：jibai.study｜邮箱：jibai.zhou@example.com',
        college='杭州电子科技大学 计算机学院',
        signature='最近在补计网和数据结构，晚上常在线。',
        avatar_source='IMG_0852.PNG',
        avatar_target='avatar_demo_zhou_jibai.png',
        created_at='2025-11-02 20:10:00',
        last_active='2026-04-05 23:15:00',
    ),
    DemoUserProfile(
        username='许清和',
        email='qinghe.xu@example.com',
        phone='13900001013',
        contact='微信：qinghe.xu｜邮箱：qinghe.xu@example.com',
        college='南京邮电大学 网络空间安全学院',
        signature='白天上课，晚上整理错题，周末出门背题。',
        avatar_source='IMG_0645.PNG',
        avatar_target='avatar_demo_xu_qinghe.png',
        created_at='2025-09-26 19:45:00',
        last_active='2026-04-06 07:50:00',
    ),
    DemoUserProfile(
        username='陈泊安',
        email='boan.chen@example.com',
        phone='13900001014',
        contact='站内私信优先｜邮箱：boan.chen@example.com',
        college='深圳大学 计算机与软件学院',
        signature='喜欢把复杂流程拆成能复用的小步骤。',
        avatar_source='IMG_1658.jpg',
        avatar_target='avatar_demo_chen_boan.jpg',
        created_at='2025-12-08 18:20:00',
        last_active='2026-04-06 09:05:00',
    ),
    DemoUserProfile(
        username='宋闻溪',
        email='wenxi.song@example.com',
        phone='13900001015',
        contact='微信：wenxi.notes｜邮箱：wenxi.song@example.com',
        college='苏州大学 计算机科学与技术学院',
        signature='把论坛当学习日志之后，复盘变得轻很多。',
        avatar_source='IMG_1626.PNG',
        avatar_target='avatar_demo_song_wenxi.png',
        created_at='2025-11-19 22:05:00',
        last_active='2026-04-05 21:40:00',
    ),
)


DEMO_POSTS: tuple[DemoPostSpec, ...] = (
    DemoPostSpec(
        author='林粤',
        board_slug='study-share',
        title='把错题拆成“概念 / 易混 / 计算”三类后，我的个人题库终于不乱了',
        markdown='''最近两周我把公共题库里反复错的题，重新按“为什么会错”整理了一遍，效果比我预想中好很多。\n\n我现在会把题目分成三类：\n\n1. **概念不牢**：一看就知道自己没记住定义或者条件；\n2. **易混知识点**：明明会做，但总在相邻概念里打架；\n3. **计算型题**：思路没问题，就是手感和边界不稳。\n\n现在的做法是：\n\n- 白天刷公共题库，晚上只回看个人题库里的错题；\n- 每道题只写一句最短备注，强迫自己抓住真正卡住的地方；\n- 周末统一清一次已经彻底掌握的题，不让题库越积越重。\n\n这样改完以后，我每天复盘时间从一个多小时降到了四十分钟左右，但第二天回忆的时候反而更稳。\n\n如果你也在整理个人题库，真的很推荐先按“错因”分类，再按知识点打标签，会清爽很多。''',
        summary='我把错题按“概念不牢 / 易混 / 计算”三类拆开后，复盘时间明显缩短了。',
        tags=('个人题库', '错题整理', '学习方法'),
        cover_source='IMG_0617.JPG',
        gallery_sources=('IMG_0661.PNG',),
        created_at='2026-04-02 20:12:00',
        updated_at='2026-04-02 20:38:00',
        view_count=168,
        is_featured=True,
    ),
    DemoPostSpec(
        author='陈泊安',
        board_slug='study-share',
        title='今晚把论坛发帖链路从用户视角走了一遍，有 3 个细节我很喜欢',
        markdown='''今晚把发帖流程完整走了一遍，从选版块、写正文、配封面，到最后回到帖子详情页，整体节奏其实挺顺的。\n\n我最喜欢的有三个点：\n\n- **版块、摘要、标签分开设置**，不会让编辑区本身太吵；\n- **封面图和正文图分开管理**，帖子列表看起来会整齐很多；\n- **Markdown 和可视化编辑并存**，写学习记录和技术帖都比较舒服。\n\n如果后面还要继续打磨，我个人最想补的功能是：\n\n1. 自动草稿；\n2. 图片顺序拖拽；\n3. 发帖成功后给出相关版块或相关帖子推荐。\n\n做社区产品很容易越做越重，但现在这个发帖链路给我的感觉是：功能足够用，交互也没把人赶走。这个平衡其实不容易。''',
        summary='从用户视角完整走了一遍论坛发帖流程，记录了 3 个特别值得保留的细节。',
        tags=('论坛', '产品细节', '技术观察'),
        cover_source='IMG_1658.jpg',
        gallery_sources=('IMG_1626.PNG',),
        created_at='2026-04-03 22:18:00',
        updated_at='2026-04-03 22:44:00',
        view_count=134,
    ),
    DemoPostSpec(
        author='许清和',
        board_slug='study-share',
        title='周末在海边背了 40 道计网题，意外比在宿舍更专注',
        markdown='''周六傍晚去海边走了一圈，顺手把这周整理的计网错题卡片也带上了。原本只是想边走边看看，结果两个小时里居然把传输层和应用层的重点又过了一遍。\n\n以前我总觉得学习必须坐在书桌前，后来发现只要题量不大、目标够清楚，换个环境反而更容易把脑子放松下来。\n\n我这次带出去的内容很轻：\n\n- 三次握手、四次挥手的关键状态；\n- DNS 递归解析和迭代解析的区别；\n- 拥塞控制里最容易记混的几个阶段。\n\n海边风很大，手机也没怎么想拿出来，反而把该背的内容一口气过完了。以后周末我可能会固定安排一次这种“出门轻复盘”，比闷在宿舍里刷短视频强太多。''',
        summary='带着计网错题卡片去海边散步，结果比在宿舍里更能集中注意力。',
        tags=('计网', '备考日常', '生活记录'),
        cover_source='IMG_0645.PNG',
        gallery_sources=('IMG_0852.PNG',),
        created_at='2026-04-04 18:42:00',
        updated_at='2026-04-04 19:05:00',
        view_count=191,
    ),
    DemoPostSpec(
        author='周既白',
        board_slug='ds-board',
        title='如果你也在刷数据结构，链表题真的很适合放进“短回路复习”',
        markdown='''最近我把链表题从“大块时间集中刷”改成了“短回路高频复习”，手感回来得特别快。\n\n原因很简单：链表题不是不会，而是细节太容易丢。只要隔久了不碰，指针更新顺序、dummy node、边界处理就会开始飘。\n\n我现在的节奏是：\n\n- 晚饭后 15 分钟，先口述一遍指针怎么走；\n- 睡前 10 分钟，只做 1~2 道反转、合并或者快慢指针；\n- 第二天早上再看一遍前一天卡住的边界。\n\n这个方法对链表、栈、队列这种“会但是容易手生”的题型特别友好。\n\n如果你最近也在补数据结构，真的可以试试把最容易掉手感的题拆到碎片时间里，效果比一次坐两小时硬刷要稳。''',
        summary='链表题不是适合长时间硬刷，而是更适合拆成 10～15 分钟的高频短回路。',
        tags=('数据结构', '链表', '复习节奏'),
        cover_source='IMG_0852.PNG',
        gallery_sources=(),
        created_at='2026-04-05 23:06:00',
        updated_at='2026-04-05 23:19:00',
        view_count=149,
    ),
    DemoPostSpec(
        author='宋闻溪',
        board_slug='study-share',
        title='最近开始把论坛当学习日志用了，比发朋友圈更有动力',
        markdown='''最近开始把论坛当成自己的学习日志，发现它比发朋友圈轻松太多。\n\n朋友圈会让我忍不住想把内容写得“像成果”，但学习本身很多时候就是碎的、慢的、甚至有点狼狈。论坛反而更适合记这些真实过程：今天补了什么、哪里卡住了、明天准备怎么补。\n\n我现在一般会记三件事：\n\n- 今天真正解决了什么问题；\n- 还有哪一块没有想明白；\n- 明天第一件事要补什么。\n\n写下来以后有两个变化特别明显：\n\n1. 不会再觉得自己一直原地打转；\n2. 第二天打开题库时更容易直接进入状态。\n\n如果你平时复盘总是拖着不写，可以试试先把它当成“学习日记”而不是“经验总结”，压力会小很多。''',
        summary='把论坛当成学习日志之后，复盘压力小了，第二天重新进入状态也更快。',
        tags=('学习日志', '复盘', '论坛氛围'),
        cover_source='ff1f9f0c65514eb06ea8e792515026b1.jpg',
        gallery_sources=('IMG_1658.jpg',),
        created_at='2026-04-06 08:26:00',
        updated_at='2026-04-06 08:54:00',
        view_count=116,
    ),
)


DEMO_COMMENTS: tuple[DemoCommentSpec, ...] = (
    DemoCommentSpec(
        post_title='把错题拆成“概念 / 易混 / 计算”三类后，我的个人题库终于不乱了',
        author='陈泊安',
        content='我也做过按知识点分组，最后发现按“为什么会错”更适合复盘，特别是看漏条件这种错误。',
        created_at='2026-04-02 21:06:00',
    ),
    DemoCommentSpec(
        post_title='把错题拆成“概念 / 易混 / 计算”三类后，我的个人题库终于不乱了',
        author='周既白',
        content='对，我最近会额外标一个“边界没写全”，复盘的时候一眼就能看出自己是知识点问题还是习惯问题。',
        created_at='2026-04-02 21:17:00',
        parent_content='我也做过按知识点分组，最后发现按“为什么会错”更适合复盘，特别是看漏条件这种错误。',
        reply_to_user='陈泊安',
    ),
    DemoCommentSpec(
        post_title='今晚把论坛发帖链路从用户视角走了一遍，有 3 个细节我很喜欢',
        author='宋闻溪',
        content='Markdown 和可视化编辑并存真的很实用，我发学习周报的时候就很依赖这个。',
        created_at='2026-04-03 22:51:00',
    ),
    DemoCommentSpec(
        post_title='今晚把论坛发帖链路从用户视角走了一遍，有 3 个细节我很喜欢',
        author='许清和',
        content='如果后面再加一个草稿箱，我应该会更愿意把每周复盘发出来。',
        created_at='2026-04-03 23:02:00',
    ),
    DemoCommentSpec(
        post_title='周末在海边背了 40 道计网题，意外比在宿舍更专注',
        author='林粤',
        content='换环境真的有用，我最近也会去图书馆外面的长廊背概念题，效率会比闷在座位上更高。',
        created_at='2026-04-04 20:10:00',
    ),
    DemoCommentSpec(
        post_title='周末在海边背了 40 道计网题，意外比在宿舍更专注',
        author='陈泊安',
        content='我一般在散步时听自己录的知识点，脚步一慢下来，很多概念反而能串起来。',
        created_at='2026-04-04 20:22:00',
        parent_content='换环境真的有用，我最近也会去图书馆外面的长廊背概念题，效率会比闷在座位上更高。',
        reply_to_user='林粤',
    ),
    DemoCommentSpec(
        post_title='如果你也在刷数据结构，链表题真的很适合放进“短回路复习”',
        author='陈泊安',
        content='链表题我现在默认先把 dummy node 写出来，心里会稳很多。',
        created_at='2026-04-05 23:35:00',
    ),
    DemoCommentSpec(
        post_title='最近开始把论坛当学习日志用了，比发朋友圈更有动力',
        author='林粤',
        content='学习日志最大的好处就是能看见自己不是一直原地打转，哪怕每天只补一点也有痕迹。',
        created_at='2026-04-06 08:58:00',
    ),
)


FOLLOW_RELATIONS: tuple[tuple[str, str], ...] = (
    ('林粤', '周既白'),
    ('林粤', '宋闻溪'),
    ('周既白', '林粤'),
    ('周既白', '陈泊安'),
    ('许清和', '林粤'),
    ('陈泊安', '周既白'),
    ('宋闻溪', '林粤'),
    ('宋闻溪', '许清和'),
)


POST_LIKES: tuple[tuple[str, str], ...] = (
    ('把错题拆成“概念 / 易混 / 计算”三类后，我的个人题库终于不乱了', '陈泊安'),
    ('把错题拆成“概念 / 易混 / 计算”三类后，我的个人题库终于不乱了', '周既白'),
    ('把错题拆成“概念 / 易混 / 计算”三类后，我的个人题库终于不乱了', '宋闻溪'),
    ('今晚把论坛发帖链路从用户视角走了一遍，有 3 个细节我很喜欢', '林粤'),
    ('今晚把论坛发帖链路从用户视角走了一遍，有 3 个细节我很喜欢', '宋闻溪'),
    ('周末在海边背了 40 道计网题，意外比在宿舍更专注', '林粤'),
    ('周末在海边背了 40 道计网题，意外比在宿舍更专注', '陈泊安'),
    ('周末在海边背了 40 道计网题，意外比在宿舍更专注', '宋闻溪'),
    ('如果你也在刷数据结构，链表题真的很适合放进“短回路复习”', '林粤'),
    ('如果你也在刷数据结构，链表题真的很适合放进“短回路复习”', '陈泊安'),
    ('最近开始把论坛当学习日志用了，比发朋友圈更有动力', '林粤'),
    ('最近开始把论坛当学习日志用了，比发朋友圈更有动力', '许清和'),
)


POST_FAVORITES: tuple[tuple[str, str], ...] = (
    ('把错题拆成“概念 / 易混 / 计算”三类后，我的个人题库终于不乱了', '周既白'),
    ('今晚把论坛发帖链路从用户视角走了一遍，有 3 个细节我很喜欢', '宋闻溪'),
    ('周末在海边背了 40 道计网题，意外比在宿舍更专注', '林粤'),
    ('如果你也在刷数据结构，链表题真的很适合放进“短回路复习”', '陈泊安'),
    ('最近开始把论坛当学习日志用了，比发朋友圈更有动力', '许清和'),
)


COMMENT_REACTIONS: tuple[tuple[str, str, str], ...] = (
    ('我也做过按知识点分组，最后发现按“为什么会错”更适合复盘，特别是看漏条件这种错误。', '周既白', '👍'),
    ('Markdown 和可视化编辑并存真的很实用，我发学习周报的时候就很依赖这个。', '陈泊安', '✨'),
    ('换环境真的有用，我最近也会去图书馆外面的长廊背概念题，效率会比闷在座位上更高。', '许清和', '🌊'),
)


def _parse_dt(value: str) -> datetime:
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


def _ensure_dev_or_test_env(app) -> None:
    if not (bool(app.config.get('DEBUG')) or bool(app.config.get('TESTING'))):
        raise RuntimeError('仅允许在开发/测试环境执行演示数据脚本。')


def _require_import_assets() -> None:
    if IMPORT_ASSET_DIR.is_dir():
        return
    raise FileNotFoundError(
        '未找到导入素材目录：/data/import_assets/demo_avatars\n'
        '请先把 /Users/saksk/Downloads/头像 下的图片复制到 var/import_assets/demo_avatars/'
    )


def _ensure_upload_dirs() -> None:
    AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    FORUM_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _copy_image(source_name: str, target_dir: Path, target_name: str) -> str:
    source_path = IMPORT_ASSET_DIR / source_name
    if not source_path.exists():
        raise FileNotFoundError(f'缺少素材文件：{source_path}')
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / target_name
    if not target_path.exists():
        shutil.copy2(source_path, target_path)
    return target_path.name


def _avatar_url(profile: DemoUserProfile) -> str:
    filename = _copy_image(profile.avatar_source, AVATAR_UPLOAD_DIR, profile.avatar_target)
    return f'/uploads/avatars/{filename}'


def _forum_image_url(source_name: str) -> str:
    stem = Path(source_name).stem.lower().replace(' ', '_')
    suffix = Path(source_name).suffix.lower() or '.png'
    filename = f'demo_forum_{stem}{suffix}'
    copied = _copy_image(source_name, FORUM_UPLOAD_DIR, filename)
    return f'/uploads/forum/{copied}'


def _get_or_create_user(profile: DemoUserProfile) -> m.User:
    existing = (
        m.User.query.filter(
            (m.User.username == profile.username)
            | (m.User.email == profile.email)
            | (m.User.phone == profile.phone)
        )
        .order_by(m.User.id.asc())
        .first()
    )
    avatar = _avatar_url(profile)
    password_hash = generate_password_hash(DEMO_PASSWORD)
    created_at = _parse_dt(profile.created_at)
    last_active = _parse_dt(profile.last_active)

    if existing is None:
        existing = m.User(
            username=profile.username,
            email=profile.email,
            phone=profile.phone,
            contact=profile.contact,
            college=profile.college,
            avatar=avatar,
            password_hash=password_hash,
            created_at=created_at,
            last_active=last_active,
            email_verified=True,
            phone_verified=True,
            has_password_set=True,
            email_verified_at=created_at,
            phone_verified_at=created_at,
        )
        db.session.add(existing)
        db.session.flush()
    else:
        existing.username = profile.username
        existing.email = profile.email
        existing.phone = profile.phone
        existing.contact = profile.contact
        existing.college = profile.college
        existing.avatar = avatar
        existing.password_hash = password_hash
        existing.created_at = created_at
        existing.last_active = last_active
        existing.email_verified = True
        existing.phone_verified = True
        existing.has_password_set = True
        existing.email_verified_at = created_at
        existing.phone_verified_at = created_at

    _upsert_signature(existing.id, profile.signature)
    return existing


def _upsert_signature(user_id: int, signature: str) -> None:
    row = (
        db.session.query(UserProgress)
        .filter(UserProgress.user_id == user_id, UserProgress.p_key == PROFILE_EXTRA_KEY)
        .first()
    )
    payload = {'signature': signature, 'privacy_favorites': 'public', 'privacy_likes': 'public'}
    if row is None:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.session.add(
            UserProgress(
                user_id=user_id,
                p_key=PROFILE_EXTRA_KEY,
                data=json.dumps(payload, ensure_ascii=False),
                created_at=now_str,
                updated_at=now_str,
            )
        )
        return

    try:
        current_data = json.loads(row.data or '{}')
        current_dict = current_data if isinstance(current_data, dict) else {}
    except Exception:
        current_dict = {}
    next_payload = {**current_dict, **payload}
    row.data = json.dumps(next_payload, ensure_ascii=False)
    row.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _board_map() -> dict[str, m.ForumBoard]:
    boards = m.ForumBoard.query.filter(m.ForumBoard.slug.in_(['study-share', 'ds-board'])).all()
    result = {board.slug: board for board in boards}
    missing = {'study-share', 'ds-board'} - set(result)
    if missing:
        raise RuntimeError(f'缺少论坛版块：{", ".join(sorted(missing))}')
    return result


def _normalize_gallery_urls(cover_url: str | None, gallery_urls: Iterable[str]) -> list[str]:
    values = [url for url in gallery_urls if url]
    if cover_url and cover_url not in values:
        return [cover_url, *values]
    return values


def _get_or_create_post(spec: DemoPostSpec, users: dict[str, m.User], boards: dict[str, m.ForumBoard]) -> m.ForumPost:
    author = users[spec.author]
    board = boards[spec.board_slug]
    existing = (
        m.ForumPost.query.filter_by(author_id=author.id, title=spec.title, is_deleted=False)
        .order_by(m.ForumPost.id.asc())
        .first()
    )

    cover_url = _forum_image_url(spec.cover_source) if spec.cover_source else None
    gallery_urls = tuple(_forum_image_url(name) for name in spec.gallery_sources)
    images = _normalize_gallery_urls(cover_url, gallery_urls)

    if existing is None:
        created = post_service.create_post(
            author_id=author.id,
            board_id=board.id,
            title=spec.title,
            content='',
            content_format='markdown',
            markdown_source=spec.markdown,
            cover_image=cover_url,
            images=images,
            tags=list(spec.tags),
            summary=spec.summary,
        )
        if 'error' in created:
            raise RuntimeError(f'创建帖子失败：{spec.title} -> {created["error"]}')
        post = db.session.get(m.ForumPost, int(created['id']))
    else:
        post_service.update_post(
            existing.id,
            author_id=author.id,
            title=spec.title,
            content='',
            content_format='markdown',
            markdown_source=spec.markdown,
            cover_image=cover_url,
            images=images,
            tags=list(spec.tags),
            summary=spec.summary,
        )
        post = db.session.get(m.ForumPost, existing.id)

    if post is None:
        raise RuntimeError(f'帖子写入后未找到：{spec.title}')

    post.created_at = _parse_dt(spec.created_at)
    post.updated_at = _parse_dt(spec.updated_at)
    post.view_count = int(spec.view_count)
    post.is_featured = bool(spec.is_featured)
    db.session.flush()
    return post


def _comment_lookup(post_id: int, content: str, author_id: int) -> m.ForumComment | None:
    return (
        m.ForumComment.query.filter_by(post_id=post_id, author_id=author_id, content=content, is_deleted=False)
        .order_by(m.ForumComment.id.asc())
        .first()
    )


def _get_or_create_comment(
    spec: DemoCommentSpec,
    posts: dict[str, m.ForumPost],
    users: dict[str, m.User],
) -> m.ForumComment:
    post = posts[spec.post_title]
    author = users[spec.author]
    existing = _comment_lookup(post.id, spec.content, author.id)
    if existing is not None:
        existing.created_at = _parse_dt(spec.created_at)
        existing.updated_at = _parse_dt(spec.created_at)
        db.session.flush()
        return existing

    parent = None
    reply_to = None
    if spec.parent_content:
        parent = (
            m.ForumComment.query.filter_by(post_id=post.id, content=spec.parent_content, is_deleted=False)
            .order_by(m.ForumComment.id.asc())
            .first()
        )
        if parent is None:
            raise RuntimeError(f'未找到父评论：{spec.parent_content}')
    if spec.reply_to_user:
        reply_to = users[spec.reply_to_user]

    created = comment_service.create_comment(
        post_id=post.id,
        author_id=author.id,
        content=spec.content,
        parent_id=parent.id if parent else None,
        reply_to_user_id=reply_to.id if reply_to else None,
    )
    if 'error' in created:
        raise RuntimeError(f'创建评论失败：{spec.content} -> {created["error"]}')
    comment = db.session.get(m.ForumComment, int(created['id']))
    if comment is None:
        raise RuntimeError(f'评论写入后未找到：{spec.content}')
    comment.created_at = _parse_dt(spec.created_at)
    comment.updated_at = _parse_dt(spec.created_at)
    db.session.flush()
    return comment


def _insert_post_like(post_id: int, user_id: int) -> None:
    db.session.execute(
        text(
            'INSERT INTO forum_likes (user_id, target_type, target_id) '
            "VALUES (:uid, 'post', :tid) ON CONFLICT (user_id, target_type, target_id) DO NOTHING"
        ),
        {'uid': user_id, 'tid': post_id},
    )


def _insert_post_favorite(post_id: int, user_id: int) -> None:
    db.session.execute(
        text(
            'INSERT INTO forum_favorites (user_id, post_id) '
            'VALUES (:uid, :pid) ON CONFLICT (user_id, post_id) DO NOTHING'
        ),
        {'uid': user_id, 'pid': post_id},
    )


def _insert_comment_reaction(comment_id: int, user_id: int, emoji: str) -> None:
    db.session.execute(
        text(
            'INSERT INTO forum_reactions (user_id, target_type, target_id, emoji) '
            'VALUES (:uid, :tt, :tid, :emoji) '
            'ON CONFLICT (user_id, target_type, target_id, emoji) DO NOTHING'
        ),
        {'uid': user_id, 'tt': 'comment', 'tid': comment_id, 'emoji': emoji},
    )


def _insert_follow(follower_id: int, following_id: int) -> None:
    if follower_id == following_id:
        return
    db.session.execute(
        text(
            'INSERT INTO user_follows (follower_id, following_id) '
            'VALUES (:follower_id, :following_id) '
            'ON CONFLICT (follower_id, following_id) DO NOTHING'
        ),
        {'follower_id': follower_id, 'following_id': following_id},
    )


def _refresh_comment_stats() -> None:
    db.session.execute(
        text(
            '''
            UPDATE forum_comments c
            SET reply_count = sub.reply_count,
                like_count = sub.like_count
            FROM (
                SELECT base.id,
                       COALESCE(reply_counts.reply_count, 0) AS reply_count,
                       COALESCE(like_counts.like_count, 0) AS like_count
                FROM forum_comments base
                LEFT JOIN (
                    SELECT parent_id, COUNT(*) AS reply_count
                    FROM forum_comments
                    WHERE parent_id IS NOT NULL AND is_deleted = false
                    GROUP BY parent_id
                ) reply_counts ON reply_counts.parent_id = base.id
                LEFT JOIN (
                    SELECT target_id, COUNT(*) AS like_count
                    FROM forum_likes
                    WHERE target_type = 'comment'
                    GROUP BY target_id
                ) like_counts ON like_counts.target_id = base.id
            ) AS sub
            WHERE c.id = sub.id
            '''
        )
    )


def _refresh_post_stats() -> None:
    db.session.execute(
        text(
            '''
            UPDATE forum_posts p
            SET comment_count = sub.comment_count,
                like_count = sub.like_count,
                favorite_count = sub.favorite_count,
                last_comment_at = sub.last_comment_at
            FROM (
                SELECT base.id,
                       COALESCE(comment_counts.comment_count, 0) AS comment_count,
                       COALESCE(like_counts.like_count, 0) AS like_count,
                       COALESCE(favorite_counts.favorite_count, 0) AS favorite_count,
                       comment_counts.last_comment_at AS last_comment_at
                FROM forum_posts base
                LEFT JOIN (
                    SELECT post_id,
                           COUNT(*) AS comment_count,
                           MAX(created_at) AS last_comment_at
                    FROM forum_comments
                    WHERE is_deleted = false
                    GROUP BY post_id
                ) comment_counts ON comment_counts.post_id = base.id
                LEFT JOIN (
                    SELECT target_id, COUNT(*) AS like_count
                    FROM forum_likes
                    WHERE target_type = 'post'
                    GROUP BY target_id
                ) like_counts ON like_counts.target_id = base.id
                LEFT JOIN (
                    SELECT post_id, COUNT(*) AS favorite_count
                    FROM forum_favorites
                    GROUP BY post_id
                ) favorite_counts ON favorite_counts.post_id = base.id
            ) AS sub
            WHERE p.id = sub.id
            '''
        )
    )


def _commit_checkpoint() -> None:
    db.session.commit()


def main() -> int:
    app = create_app('development')
    with app.app_context():
        _ensure_dev_or_test_env(app)
        _require_import_assets()
        _ensure_upload_dirs()

        users = {profile.username: _get_or_create_user(profile) for profile in DEMO_USERS}
        _commit_checkpoint()

        boards = _board_map()
        posts = {spec.title: _get_or_create_post(spec, users, boards) for spec in DEMO_POSTS}
        _commit_checkpoint()

        comments = {
            spec.content: _get_or_create_comment(spec, posts, users)
            for spec in DEMO_COMMENTS
        }

        for follower_name, following_name in FOLLOW_RELATIONS:
            _insert_follow(users[follower_name].id, users[following_name].id)

        for post_title, username in POST_LIKES:
            _insert_post_like(posts[post_title].id, users[username].id)

        for post_title, username in POST_FAVORITES:
            _insert_post_favorite(posts[post_title].id, users[username].id)

        for comment_content, username, emoji in COMMENT_REACTIONS:
            _insert_comment_reaction(comments[comment_content].id, users[username].id, emoji)

        _refresh_comment_stats()
        _refresh_post_stats()
        _commit_checkpoint()

        print('已写入论坛演示数据：')
        print(f'- 演示用户：{len(users)} 位')
        print(f'- 论坛帖子：{len(posts)} 篇')
        print(f'- 论坛评论：{len(comments)} 条')
        print(f'- 通用登录密码：{DEMO_PASSWORD}')
        print('- 用户列表：')
        for profile in DEMO_USERS:
            print(f'  * {profile.username} / {profile.email} / {profile.phone}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
