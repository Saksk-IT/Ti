#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建更完整的论坛演示用户、帖子、私信与通知数据。

用途：
- 补充 5 位真实感更强的演示用户；
- 在论坛中创建教程型、目录型、投票型与课程复习型帖子；
- 追加评论、点赞、收藏、投票、关注、私信、系统通知与互动通知；
- 重复执行时尽量复用现有记录，方便持续更新演示内容。

推荐执行：
    docker exec -i ti-main-web-1 sh -lc 'PYTHONPATH=/app python -' < scripts/创建论坛演示用户与帖子.py
或：
    docker cp scripts/创建论坛演示用户与帖子.py ti-main-web-1:/tmp/create_demo_forum_seed.py
    docker exec ti-main-web-1 sh -lc 'PYTHONPATH=/app python /tmp/create_demo_forum_seed.py'

前置资源：
- 把 /Users/saksk/Downloads/头像 下的图片复制到 var/import_assets/demo_avatars/
- 容器内对应路径：/data/import_assets/demo_avatars/
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import text
from werkzeug.security import generate_password_hash


def _add_project_root_to_path() -> None:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)


_add_project_root_to_path()

from app import create_app  # noqa: E402
from app.core.extensions import db  # noqa: E402
from app import models as m  # noqa: E402
from app.models.follow import InteractionNotification  # noqa: E402
from app.models.quiz import UserProgress  # noqa: E402
from app.modules.forum.services import comment_service, post_service  # noqa: E402


DEMO_PASSWORD = 'ForumDemo2026!'
IMPORT_ASSET_DIR = Path('/data/import_assets/demo_avatars')
UPLOAD_ROOT = Path('/data/uploads')
AVATAR_UPLOAD_DIR = UPLOAD_ROOT / 'avatars'
FORUM_UPLOAD_DIR = UPLOAD_ROOT / 'forum'
PROFILE_EXTRA_KEY = 'user_profile_extra_v1'
POST_TOKEN_RE = re.compile(r'^\{post:(.+)\}$')


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
    poll: dict | None = None
    is_featured: bool = False
    is_pinned: bool = False


@dataclass(frozen=True)
class DemoCommentSpec:
    post_title: str
    author: str
    content: str
    created_at: str
    parent_content: str | None = None
    reply_to_user: str | None = None


@dataclass(frozen=True)
class NotificationSpec:
    title: str
    content: str
    n_type: str
    priority: int
    start_at: str
    end_at: str
    dismiss_users: tuple[str, ...] = ()


@dataclass(frozen=True)
class InteractionSpec:
    user: str
    actor: str
    action_type: str
    target_type: str
    target_ref: str
    post_ref: str | None
    content_preview: str
    created_at: str
    is_read: bool = False


@dataclass(frozen=True)
class ChatMessageSpec:
    sender: str
    content: str
    created_at: str
    content_type: str = 'text'


@dataclass(frozen=True)
class ChatThreadSpec:
    participants: tuple[str, str]
    title: str
    messages: tuple[ChatMessageSpec, ...]
    unread_users: tuple[str, ...] = ()


@dataclass(frozen=True)
class PollVoteSpec:
    post_title: str
    username: str
    option_indices: tuple[int, ...]


@dataclass(frozen=True)
class CommentReactionSpec:
    comment_content: str
    username: str
    emoji: str


@dataclass(frozen=True)
class SystemUserPatch:
    username: str
    phone: str | None
    contact: str
    college: str
    signature: str
    last_active: str


def forum_asset_url(source_name: str) -> str:
    stem = Path(source_name).stem.lower().replace(' ', '_')
    suffix = Path(source_name).suffix.lower() or '.png'
    return f'/uploads/forum/demo_forum_{stem}{suffix}'


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


SYSTEM_USER_PATCHES: tuple[SystemUserPatch, ...] = (
    SystemUserPatch(
        username='admin',
        phone='13573028533',
        contact='站内联系优先｜邮箱：admin@example.dev',
        college='SAK 题库维护组',
        signature='负责题库维护、导题抽检与论坛专题整理。',
        last_active='2026-04-06 09:20:00',
    ),
)


BASE_DEMO_POSTS: tuple[DemoPostSpec, ...] = (
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


EXTENDED_DEMO_POSTS: tuple[DemoPostSpec, ...] = (
    DemoPostSpec(
        author='admin',
        board_slug='study-share',
        title='【站务教程】批量导题前先把数据整理到“可导入状态”：我会先检查这 6 项',
        markdown=f'''## 一、先确认你准备走哪条导入路径\n\n我现在在后台真正会用到的入口，基本都在 ` /admin/subjects ` 这一页：\n\n1. **导入题库**：适合从 JSON 文本或 JSON 文件直接导入；\n2. **批量导入题库（Excel）**：适合把整批题目先整理成分列表格；\n3. **导入题目包（ZIP）**：适合题目和图片一起迁移。\n\n如果只是补 10~20 道题，我更倾向先用 JSON；如果是一个老师给了一整套题，我一般直接走 Excel；如果题目带很多图，我会优先用题目包。\n\n## 二、Excel 模板里最关键的列\n\n后台现在读取的是 Excel 的 `题目示例` 工作表，最少要保证这几列存在：\n\n- `subject`\n- `q_type`\n- `content`\n\n### 1）选择题 / 多选题\n\n我自己的习惯是：\n\n- 每个选项只写**纯文本**，放在所有 `option_` 开头的列里；\n- `answer` 直接写字母答案，例如 `A`、`AC`；\n- 不在 Excel 里手动再补 `A.`、`B.` 前缀，系统会按列顺序处理。\n\n### 2）填空题 / 判断题 / 简答题\n\n- 填空题会去读所有 `blank_` 开头的列；\n- 判断题、简答题直接看 `answer`；\n- `q_type` 最稳妥的写法就是：`选择题 / 多选题 / 判断题 / 填空题 / 简答题`。\n\n## 三、导题前我一定会先做的 6 项检查\n\n### 1）同一份表里别混不同命名\n\n最怕的是同一个文件里既写“单选题”，又写“选择题”，后面排错时会很烦。\n\n### 2）题干只保留题干\n\n很多旧资料会把“答案：”“解析：”也贴进题干，这种导进来之后，前端练习体验会直接变差。\n\n### 3）先用小样本测试一轮\n\n我通常不会一上来就把 300 道题全塞进去，而是先拿 20 道混合题型走一遍，看错误信息和最终展示。\n\n### 4）科目命名提前统一\n\n系统允许根据 `subject` 自动创建科目，但演示环境里我还是会先统一命名，避免“计算机网络 / 计网 / 网络”被拆成三份。\n\n### 5）图片题别假设 Excel 就能一次搞定\n\n如果一套题图片很多，我会直接改走题目包，把 `data.json` 和图片目录一起打包，返工会少很多。\n\n### 6）导入后必须反向抽检\n\n我自己的顺序是：题目列表看统计 → 打开几道题看详情 → 再导出一次 Excel / Word 回查。\n\n## 四、什么时候我会改走 ZIP 题目包\n\n### 1）题目里带大量图片\n\n题目包会要求压缩包里至少有 `data.json`，图片可以跟着一起进来，这比单独补路径靠谱得多。\n\n### 2）从旧系统迁移时\n\n如果原始数据已经是结构化 JSON，我几乎不会再人为拆回 Excel，而是直接整理成题目包。\n\n## 五、导入后我会怎么抽检\n\n我一般只抽三层：\n\n1. **统计层**：题型数量是否大致对得上；\n2. **结构层**：题干、答案、解析、图片有没有串位；\n3. **展示层**：前台练习页和后台导出结果是否一致。\n\n![导题准备示意]({forum_asset_url('IMG_0661.PNG')})\n\n如果这三层都稳了，再继续批量灌数据，后面会省掉非常多重复返工。''',
        summary='我在后台批量导题前，会先把导入路径、Excel 列、题型命名和抽检顺序全部整理清楚。',
        tags=('题目导入', '后台教程', '批量导入'),
        cover_source='IMG_0661.PNG',
        gallery_sources=('IMG_1658.jpg',),
        created_at='2026-01-08 20:18:00',
        updated_at='2026-01-08 21:02:00',
        view_count=286,
        is_featured=True,
        is_pinned=True,
    ),
    DemoPostSpec(
        author='admin',
        board_slug='study-share',
        title='【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出',
        markdown='''## 一、入口我通常怎么找\n\n真正做导题演示时，我一般不会从“题目编辑”单点开始，而是直接进 ` /admin/subjects `。这里把几条链路都放在一起了：\n\n- 新增题目；\n- 导入题库（JSON 文本 / JSON 文件）；\n- 导入题目包；\n- 导出 JSON / Excel / Word / 题目包；\n- 批量操作与查重去重。\n\n如果要给别人演示“平台不是只能手工录题”，这一页最有说服力。\n\n## 二、我自己实际的操作顺序\n\n### 步骤 A：先下载 Excel 模板\n\n我会先从“批量导入题库”区域下载模板，确认列名和自己准备的数据结构一致，再让资料提供方回填。\n\n### 步骤 B：先导一小批混合题型\n\n我喜欢先放 20 道左右的小样本进去，而且一定要混：选择题、多选题、判断题、填空题、简答题。这样报错最早暴露。\n\n### 步骤 C：导完先看题目管理页\n\n我第一眼看的是：\n\n- 总题数有没有明显不对；\n- 题型统计有没有倾斜；\n- 更新时间是不是刚刚刷过；\n- 有没有整批空题干、空答案。\n\n### 步骤 D：反向导出一遍\n\n导入成功不代表真正结束。我会再用后台把这批题导出成 Excel 或 Word，看导出结构和原始资料是不是还对得上。\n\n## 三、如果报错，我会怎么定位\n\n### 1）先看是不是缺列\n\n后台现在会直接提示缺少必填列，这一类错误通常最好修。\n\n### 2）再看题型名称\n\n如果 `q_type` 填得不标准，整行都会被跳过。\n\n### 3）最后看答案与选项关系\n\n很多多选题不是“题目错”，而是 `answer` 跟选项列顺序没对上。这个时候别急着重导，先抽样核对。\n\n## 四、导题之后我会立刻做的 4 件事\n\n1. 在后台点开几道不同题型看详情；\n2. 去前台练习页刷几道题，确认展示正常；\n3. 随机导出 Excel / Word 看结构；\n4. 对明显有问题的字段做一次批量修正。\n\n## 五、什么时候我会改走题目包\n\n如果我手上拿到的是一份已经结构化过的 JSON，再加一批图片题，我会直接走题目包。它要求压缩包里至少有 `data.json`，很适合做整批迁移。\n\n这一条链路演示出来之后，别人会更容易理解：这个站点不是“只能在线录题”，而是已经具备了比较完整的题库输入输出能力。''',
        summary='从后台科目页开始，完整走一遍导题、抽检、导出，是我最常用的演示链路。',
        tags=('题目导入', '后台教程', '导出回查'),
        cover_source='IMG_1658.jpg',
        gallery_sources=('IMG_0661.PNG',),
        created_at='2026-01-14 21:05:00',
        updated_at='2026-01-14 21:48:00',
        view_count=314,
        poll={
            'question': '你现在最常用哪种导题方式？',
            'options': ['JSON 文本 / 文件', 'Excel 模板导入', 'ZIP 题目包', '先手工录少量再批量导入'],
            'multiple': False,
        },
        is_featured=True,
    ),
    DemoPostSpec(
        author='admin',
        board_slug='study-share',
        title='【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试',
        markdown=f'''## 一、第一步：先从公共题库确认范围\n\n我自己开一个新专题时，第一件事一般不是建个人题库，而是先去 ` /public/banks ` 或对应的公共题库页确认：\n\n- 这门课目前覆盖了哪些题型；\n- 我是想先扫知识面，还是先盯住一两个薄弱章节；\n- 有没有必要立刻拆出一份自己的专题题库。\n\n## 二、第二步：刷题时让收藏和错题自动长出来\n\n公共题库最适合解决“覆盖面”问题。真正刷的时候，我最关心的是两类资产：\n\n1. **收藏**：以后还会反复回看的题；\n2. **错题**：必须尽快闭环的题。\n\n这一步我不会追求把每道题都整理完，而是先让收藏和错题积累起来。\n\n## 三、第三步：再把高频内容沉到个人题库\n\n等我发现某个知识点已经连续几天都在反复出错，我才会把它拆到 ` /user/banks ` 这条线里。个人题库最适合做三件事：\n\n### 1）按专题建自己的索引\n\n比如“TCP 连接管理”“链表边界处理”“Cache 命中率计算”这种小范围专题。\n\n### 2）给题打标签\n\n标签的价值不在“好看”，而在于后面你能直接切到一个很窄的训练范围。\n\n### 3）做错题闭环\n\n把真正高频出错的题拉回一个可控集合，比盲目加题更有效。\n\n## 四、第四步：去复盘中心和数据中心看结构\n\n我常看的页面其实不是单一题目，而是：\n\n- ` /mistakes `\n- ` /favorites `\n- ` /tags `\n- ` /review `\n- ` /data `\n\n这里能让我更快回答一个问题：**我到底是不会，还是会但不稳定。**\n\n## 五、第五步：最后才去做模拟考试\n\n我一般不会把模拟考试放在学习一开始，而是放在一个专题已经做过一轮、错题和收藏也整理出轮廓之后。\n\n这时候去 ` /exams/select ` 会更有意义，因为你看到的不只是分数，而是：\n\n- 哪类题型还在掉分；\n- 哪些错题值得直接回收进错题本；\n- 这轮练习和前几天相比是不是更稳。\n\n## 六、这个流程为什么适合演示\n\n因为它不是一句“先刷题再复盘”的空话，而是能真实串起平台里几个核心模块：\n\n- 公共题库；\n- 个人题库；\n- 收藏 / 错题 / 标签；\n- 数据中心；\n- 模拟考试。\n\n![学习流程示意]({forum_asset_url('IMG_1658.jpg')})\n\n如果要让我只演示一条链路，我就会演示这条。它最能说明这个站不是单点功能，而是完整的学习闭环。''',
        summary='我自己最常用的学习流程，是先用公共题库拉覆盖，再把真正高价值的内容沉到个人题库和复盘模块。',
        tags=('学习流程', '公共题库', '个人题库', '模拟考试'),
        cover_source='IMG_1658.jpg',
        gallery_sources=('IMG_0617.JPG',),
        created_at='2026-02-08 20:32:00',
        updated_at='2026-02-08 21:16:00',
        view_count=342,
        poll={
            'question': '你现在最常卡在学习流程哪一段？',
            'options': ['公共题库定范围', '个人题库与标签整理', '错题闭环与复盘', '模拟考试后回收问题'],
            'multiple': False,
        },
        is_featured=True,
    ),
    DemoPostSpec(
        author='admin',
        board_slug='study-share',
        title='【功能说明】为什么这个站要同时保留“公共题库”和“个人题库”两条线',
        markdown='''## 一、公共题库解决的是“覆盖面”\n\n公共题库更像一个共享底盘。它的价值在于：\n\n- 你不用先整理，就能直接开始做题；\n- 适合判断一门课的总体覆盖是否够用；\n- 很适合起步阶段和考前扫面。\n\n## 二、个人题库解决的是“组织方式”\n\n个人题库不是公共题库的重复版，而是给你一个重新组织知识的地方。\n\n我自己会在这些情况下建个人题库：\n\n1. 某一类题已经连续三四次做错；\n2. 我需要把不同来源的题重新拼成一个专题；\n3. 我想做一份只属于自己的复习顺序。\n\n## 三、两条线最稳的衔接方式\n\n我最推荐的顺序其实很简单：\n\n- **先用公共题库发现问题**；\n- **再用个人题库整理问题**；\n- **最后用错题、标签、考试验证问题有没有解决。**\n\n## 四、如果只剩一周，我会怎么选\n\n### 情况 A：知识面还没扫全\n\n优先公共题库。\n\n### 情况 B：已经知道自己卡在哪\n\n优先个人题库。\n\n### 情况 C：已经做过一轮，但状态不稳\n\n优先错题、收藏、标签和模拟考试。\n\n## 五、为什么演示时一定要把这两条线讲清楚\n\n因为很多人一开始会把“公共题库”和“个人题库”误以为只是两个入口，但其实它们解决的是两种完全不同的任务：\n\n- 一个负责**覆盖**；\n- 一个负责**组织**。\n\n把这两条线讲清楚，别人才能真正理解平台为什么不是单纯的刷题页集合。''',
        summary='公共题库负责覆盖，个人题库负责组织；把两条线分开理解，学习路径才会清楚。',
        tags=('公共题库', '个人题库', '学习策略'),
        cover_source='IMG_0617.JPG',
        gallery_sources=(),
        created_at='2026-02-16 19:46:00',
        updated_at='2026-02-16 20:08:00',
        view_count=251,
    ),
    DemoPostSpec(
        author='admin',
        board_slug='study-share',
        title='【功能说明】这个站里哪些数据会同步：收藏、错题、答案、进度、考试、论坛',
        markdown='''## 一、我为什么特别在意“同步”这件事\n\n如果一个学习系统只能在单端成立，那它的复盘价值会很快打折。这个站里我最看重的一点，是很多关键数据语义并不是“网页一个版本、小程序一个版本”，而是尽量保持一致。\n\n## 二、我日常最关心的同步对象\n\n### 1）收藏\n\n收藏不是一个装饰按钮，而是高价值题目的清单。它在后续复习里非常重要。\n\n### 2）错题\n\n错题决定了你下一轮该补哪里，所以它必须稳定可追踪。\n\n### 3）用户答案与学习进度\n\n这两类数据决定了你今天刷到哪、上次做到哪、现在回去是从头再来还是继续推进。\n\n### 4）模拟考试\n\n考试记录如果不能回看，模拟就会变成一次性事件。\n\n### 5）论坛互动\n\n论坛不只是发帖，它还是学习记录、教程沉淀和经验交流的一部分。\n\n## 三、为什么这对演示很重要\n\n因为这能直接解释两件事：\n\n1. 为什么网页适合做系统复盘；\n2. 为什么移动端适合做碎片练习。\n\n但不管你从哪一端进入，真正关键的数据都不应该被切碎。\n\n## 四、我会怎么向新同学解释\n\n如果你今天在公共题库里刷到一半，明天去个人题库里做专项，后天再去模拟考试，这三天看起来像三个入口，但背后其实在说同一个学习过程。\n\n站点真正值钱的地方，不是入口多，而是这些入口说的是同一套学习语义。\n\n## 五、什么时候最能感受到同步的价值\n\n- 白天用网页做整理；\n- 晚上用手机补几道题；\n- 第二天回到网页继续看错题、收藏和考试记录。\n\n这时候如果数据是连着的，学习节奏就不会断。''',
        summary='收藏、错题、答案、进度、考试和论坛这几类数据要保持同一套语义，学习链路才不会被切碎。',
        tags=('数据同步', '双端协同', '平台特色'),
        cover_source='IMG_1626.PNG',
        gallery_sources=('IMG_0645.PNG',),
        created_at='2026-03-02 20:40:00',
        updated_at='2026-03-02 21:10:00',
        view_count=268,
        poll={
            'question': '你最常同步查看哪些数据？',
            'options': ['收藏', '错题', '学习进度', '模拟考试', '论坛互动'],
            'multiple': True,
        },
        is_featured=True,
    ),
    DemoPostSpec(
        author='admin',
        board_slug='study-share',
        title='【功能说明】我最想展示给新同学的 5 个特色：题库、复盘、数据、论坛、双端协同',
        markdown='''## 一、题库不是只有“做题”\n\n这个站点最容易被低估的一点，是它不只是题目列表。公共题库、个人题库、导入导出、批量整理，其实是在把题目当成“可维护资产”。\n\n## 二、复盘不是一句口号\n\n错题、收藏、标签、复盘中心、数据中心这些模块如果拆开看都不算惊艳，但真正串起来以后，就能形成稳定的复盘闭环。\n\n## 三、数据中心不是摆设\n\n我最喜欢数据中心的一点，是它会把“错题、收藏、覆盖、正确率、标签”放到同一个视角里。这样你不是只知道自己做了多少题，而是知道自己现在该补哪里。\n\n## 四、论坛是学习系统的一部分\n\n我这次特意把教程帖、学习流程帖、课程大纲帖都补到论坛里，就是想把论坛从“闲聊区”拉回到学习系统里。它最适合沉淀：\n\n- 教程；\n- 大纲；\n- 复盘；\n- 经验交换。\n\n## 五、双端协同是使用场景，不是口号\n\n网页更适合系统整理，小程序更适合碎片练习。真正的价值不是“我也有移动端”，而是你换场景以后不需要重新开始。\n\n## 六、为什么我觉得这 5 点最值得演示\n\n因为这五点放在一起，最能说明平台不是“几个页面拼起来”，而是围绕学习过程做了一套相互咬合的工具链。''',
        summary='题库、复盘、数据、论坛和双端协同是我最想优先展示给新同学的 5 个特色。',
        tags=('平台特色', '数据中心', '论坛', '双端协同'),
        cover_source='IMG_1626.PNG',
        gallery_sources=('IMG_0661.PNG',),
        created_at='2026-03-18 21:12:00',
        updated_at='2026-03-18 21:45:00',
        view_count=297,
        is_featured=True,
    ),
    DemoPostSpec(
        author='admin',
        board_slug='study-share',
        title='【站务说明】题目导入后为什么还要导出一次：我会用 Excel / Word / 题目包做回归',
        markdown='''## 一、导入成功不等于真正完成\n\n很多人第一次做题库演示时，只要后台弹出“成功导入 xx 道题”，就觉得事情结束了。其实真正稳妥的做法，是再做一次反向导出回查。\n\n## 二、我为什么会导出 Excel\n\nExcel 最适合做结构核对：\n\n- 题干有没有断行错位；\n- 选项顺序有没有漂；\n- 题型数量是不是和预期一致。\n\n## 三、我为什么会导出 Word\n\nWord 的价值在于看阅读感。尤其是老师给我的资料原本就是文档格式时，导出 Word 更容易对照。\n\n## 四、什么时候我会导出题目包\n\n如果这批题后面还要迁移、备份、交接，我更愿意直接导出题目包。因为它把结构化数据和图片一并带走，最适合做环境之间的迁移回归。\n\n## 五、我自己的回归顺序\n\n1. 导入一批小样本；\n2. 导出 Excel 看结构；\n3. 导出 Word 看阅读；\n4. 如果涉及图片，再补一次题目包。\n\n这个顺序虽然多花几分钟，但能明显减少“演示时才发现题目有错位”的尴尬。''',
        summary='导题后的反向导出，是我做站务演示时最稳定的一道保险。',
        tags=('题目导出', '回归检查', '后台教程'),
        cover_source='IMG_0661.PNG',
        gallery_sources=(),
        created_at='2026-03-27 20:26:00',
        updated_at='2026-03-27 20:54:00',
        view_count=205,
    ),
    DemoPostSpec(
        author='周既白',
        board_slug='study-share',
        title='计算机网络期末复习框架：我会把应用层、传输层、网络层拆成三轮',
        markdown='''## 第一轮：先把应用层和传输层拉顺\n\n我复习计网时，第一轮一般不会先碰路由算法，而是先把最容易反复出现的应用层和传输层题目刷熟：HTTP、DNS、TCP、UDP。\n\n### 我第一轮只追求两件事\n\n1. 每个协议是干什么的；\n2. 常见题目会怎么换着问。\n\n## 第二轮：再把网络层和链路层补上\n\n等上面这部分稳了，我再去补：\n\n- IP 地址与子网；\n- 路由与转发；\n- ARP、ICMP；\n- MTU、分片、差错控制。\n\n## 第三轮：把容易混的概念重新串一次\n\n第三轮我不会再按章节，而是按“容易混”的概念成对回看，比如：\n\n- 流量控制 vs 拥塞控制；\n- 递归解析 vs 迭代解析；\n- 面向连接 vs 可靠传输。\n\n## 我在题库里怎么安排这三轮\n\n- 公共题库：拉覆盖；\n- 个人题库：收最容易错的专题；\n- 错题本：只留真正会反复错的题。\n\n这套拆法最大的好处，是不会一上来就被“计网章节很多”吓住。''',
        summary='我复习计算机网络时，会按应用层/传输层、网络层/链路层、易混概念三轮推进。',
        tags=('计算机网络', '复习框架', '期末复习'),
        cover_source='IMG_0645.PNG',
        gallery_sources=(),
        created_at='2026-01-21 21:10:00',
        updated_at='2026-01-21 21:44:00',
        view_count=224,
        is_featured=True,
    ),
    DemoPostSpec(
        author='许清和',
        board_slug='study-share',
        title='计网里最容易混的 8 组概念，我是怎么在个人题库里拆标签的',
        markdown='''## 一、我为什么不按章节打标签\n\n如果只按“传输层”“网络层”打标签，后面复盘时范围还是太大。我现在更喜欢按容易混淆的概念对来打。\n\n## 二、我最常拆的 8 组概念\n\n### 1）流量控制 vs 拥塞控制\n### 2）面向连接 vs 可靠传输\n### 3）递归解析 vs 迭代解析\n### 4）端口号 vs IP 地址\n### 5）确认重传 vs 快速重传\n### 6）滑动窗口 vs 拥塞窗口\n### 7）MTU vs MSS\n### 8）路由选择 vs 分组转发\n\n## 三、我会怎么落到题库里\n\n每一组概念我都会做三件事：\n\n1. 收藏一两道最典型的辨析题；\n2. 把反复错的题拉进个人题库；\n3. 给它们打同一个标签，方便单独开练。\n\n## 四、这样做的效果\n\n我后来发现自己不是“计网都不会”，而是总被这几组概念绊住。拆出来以后，复盘会精准很多。''',
        summary='我在个人题库里不按章节打计网标签，而是按最容易混淆的概念对拆专题。',
        tags=('计算机网络', '标签', '易混概念'),
        cover_source='IMG_0852.PNG',
        gallery_sources=('IMG_0661.PNG',),
        created_at='2026-01-30 20:56:00',
        updated_at='2026-01-30 21:22:00',
        view_count=198,
    ),
    DemoPostSpec(
        author='林粤',
        board_slug='ds-board',
        title='数据结构刷题路线：链表、栈队列、树、图，我现在按这个顺序推进',
        markdown='''## 一、先从链表开始\n\n链表最适合练基本功：边界、指针、dummy node、局部反转。\n\n## 二、再做栈和队列\n\n栈队列题型不一定难，但特别适合建立“什么时候该用什么结构”的直觉。\n\n## 三、第三步才碰树\n\n树题一上来容易觉得多，其实我更建议先把：\n\n- 遍历；\n- 递归返回值；\n- 二叉搜索树性质；\n- 层序模板；\n\n这几块单独拆熟。\n\n## 四、图和并查集放到后面\n\n图题一多，很多同学容易直接失去节奏。我现在会等前面几块比较稳，再补 BFS / DFS / 拓扑 / 最短路。\n\n## 五、这个顺序为什么适合题库练习\n\n因为它遵循的是“先练手感，再拉结构，再补综合”的顺序，比较符合题库训练的节奏。''',
        summary='我现在的数据结构刷题顺序是：链表 → 栈队列 → 树 → 图。',
        tags=('数据结构', '刷题路线', '专题训练'),
        cover_source='IMG_0617.JPG',
        gallery_sources=(),
        created_at='2026-02-14 19:58:00',
        updated_at='2026-02-14 20:18:00',
        view_count=176,
    ),
    DemoPostSpec(
        author='陈泊安',
        board_slug='study-share',
        title='用“个人题库 + 标签 + 错题本”整理操作系统，我目前最稳定的结构',
        markdown='''## 一、我不会把操作系统全塞进一个题库\n\n操作系统最容易出问题的地方，是内容跨度很大：进程线程、调度、同步互斥、内存、文件系统，硬塞在一起会很乱。\n\n## 二、我现在拆成 4 个专题\n\n### 1）进程与线程\n### 2）同步与互斥\n### 3）内存管理\n### 4）文件系统与磁盘调度\n\n## 三、标签怎么配合\n\n我会再给题目打第二层标签，比如：\n\n- 经典模型；\n- 易错概念；\n- 计算题；\n- 简答题。\n\n## 四、错题本只留“会反复犯同一种错”的题\n\n如果某题只是第一次没看清，我不会急着长期留在错题本里。真正值得留的是：它暴露了我稳定的错误模式。\n\n## 五、为什么这个结构最稳\n\n因为操作系统的题一旦不拆专题，复盘时会非常散。拆完以后，每次回看都能快速找到自己该补的那一块。''',
        summary='操作系统我不会只建一个大题库，而是按专题 + 标签 + 错题模式分层整理。',
        tags=('操作系统', '个人题库', '标签', '错题本'),
        cover_source='IMG_1658.jpg',
        gallery_sources=('IMG_1626.PNG',),
        created_at='2026-02-23 21:24:00',
        updated_at='2026-02-23 21:52:00',
        view_count=183,
    ),
    DemoPostSpec(
        author='宋闻溪',
        board_slug='study-share',
        title='计算机组成原理复习框架：指令、流水线、Cache，题库应该怎么建',
        markdown='''## 一、先把“会被反复考”的主干找出来\n\n组成原理里我最先抓的是：\n\n- 指令系统；\n- 流水线；\n- 存储层次；\n- Cache；\n- 中断与总线。\n\n## 二、题库不要按教材目录机械照抄\n\n我现在更喜欢按“出题方式”来建：\n\n### 1）概念辨析\n### 2）流程推导\n### 3）性能计算\n\n## 三、流水线和 Cache 要单独留一组\n\n这两块题看起来分散，实际上特别适合做专题，因为很多题都是同一种计算思路换皮。\n\n## 四、我自己的复盘方法\n\n- 先刷概念题；\n- 再补计算题；\n- 最后把容易掉坑的题放进个人题库反复回看。\n\n这样不会一上来就被公式和图表压住。''',
        summary='组成原理题库我不会机械照搬教材目录，而是按概念辨析、流程推导、性能计算来拆。',
        tags=('组成原理', '复习框架', '专题题库'),
        cover_source='IMG_1626.PNG',
        gallery_sources=(),
        created_at='2026-03-10 20:15:00',
        updated_at='2026-03-10 20:46:00',
        view_count=162,
    ),
    DemoPostSpec(
        author='周既白',
        board_slug='study-share',
        title='数据库复习不只是 SQL：ER、范式、查询优化我会分三轮做',
        markdown='''## 第一轮：ER、关系模型、范式\n\n这一轮我只要求自己能解释清楚：实体、联系、主键、外键、函数依赖、1NF / 2NF / 3NF。\n\n## 第二轮：SQL 语句与查询题\n\n这部分才是很多同学最熟悉的练习内容，但如果第一轮没打好，后面 SQL 很容易只停留在套模板。\n\n## 第三轮：索引、连接、查询优化\n\n这部分我会放在最后，因为它更依赖前面的结构理解。\n\n## 我在题库里的拆法\n\n- 公共题库：先扫覆盖；\n- 个人题库：收最常错的范式题和连接题；\n- 标签：把“范式 / 连接 / 索引 / 聚合”拆开。\n\n## 为什么我不只刷 SQL\n\n因为数据库考试真正拉分的地方，常常不是单句 SQL，而是你有没有把“模型、约束、查询”串起来。''',
        summary='数据库复习我会按“模型与范式 → SQL → 查询优化”三轮推进，而不是只刷 SQL。',
        tags=('数据库', '复习框架', 'SQL'),
        cover_source='IMG_0661.PNG',
        gallery_sources=('IMG_0852.PNG',),
        created_at='2026-03-24 21:06:00',
        updated_at='2026-03-24 21:28:00',
        view_count=171,
    ),
    DemoPostSpec(
        author='陈泊安',
        board_slug='study-share',
        title='导题后怎么做抽检：我只盯这 5 类高风险字段，能省很多返工',
        markdown='''## 一、题干\n\n题干是我第一个必看字段。只要题干里混入“答案：”“解析：”，后面整条链路都会变脏。\n\n## 二、答案\n\n我第二个看答案，特别是多选题和判断题。很多时候导题不是失败，而是答案格式没和题型对齐。\n\n## 三、选项\n\nExcel 导题最容易出现的一个问题，就是选项列里已经手动写了 `A.`、`B.`，结果导进来又被系统加了一次前缀。\n\n## 四、图片路径\n\n只要一涉及图片题，我一定会再额外看一次：\n\n- 图片是不是都落到了统一目录；\n- 题干里的图和答案解析的图有没有串位。\n\n## 五、题型\n\n题型命名一旦漂掉，后面统计页和导出页都会跟着乱。\n\n## 为什么我只盯这 5 类\n\n因为这 5 类一旦稳住，导题的主要风险基本就降下来了。剩下的问题，往往只需要小修。''',
        summary='导题后的抽检我不会全量细看，而是优先盯题干、答案、选项、图片路径和题型这 5 类高风险字段。',
        tags=('导题抽检', '题目导入', '后台经验'),
        cover_source='IMG_1658.jpg',
        gallery_sources=(),
        created_at='2026-03-28 20:42:00',
        updated_at='2026-03-28 21:05:00',
        view_count=154,
    ),
    DemoPostSpec(
        author='宋闻溪',
        board_slug='study-share',
        title='软工 / 计基这种大纲型课程，我现在会先建“章节导航帖”再回填题库',
        markdown='''## 一、为什么先写导航帖\n\n像软件工程、计算机导论这种课，章节很多、知识点也碎。如果一开始就只顾着往题库里塞题，很容易越做越散。\n\n## 二、我会先把目录搭出来\n\n我一般会先写一篇导航帖，把章节顺序、重点、专题范围先列出来。这样后面回填题库时，自己不会乱。\n\n## 三、再把题库按目录一点点补满\n\n等目录稳了，我才开始：\n\n- 哪些章节先收公共题；\n- 哪些章节需要单独建个人题库；\n- 哪些章节只留错题和简答题。\n\n## 四、这个方法最适合什么课\n\n最适合那种“大纲明显、内容宽、题量不一定大，但复习时很容易找不到入口”的课。\n\n## 五、为什么我觉得论坛在这里很好用\n\n因为论坛里的长帖天然适合放目录。题库负责题目，导航帖负责路线，两者分工反而很清楚。''',
        summary='面对大纲型课程，我现在会先建导航帖，再按目录回填题库和错题专题。',
        tags=('学习方法', '课程大纲', '导航帖'),
        cover_source='ff1f9f0c65514eb06ea8e792515026b1.jpg',
        gallery_sources=('IMG_0617.JPG',),
        created_at='2026-03-31 20:08:00',
        updated_at='2026-03-31 20:35:00',
        view_count=149,
    ),
)


DEMO_POSTS = BASE_DEMO_POSTS + EXTENDED_DEMO_POSTS


BASE_COMMENTS: tuple[DemoCommentSpec, ...] = (
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


EXTENDED_COMMENTS: tuple[DemoCommentSpec, ...] = (
    DemoCommentSpec(
        post_title='【站务教程】批量导题前先把数据整理到“可导入状态”：我会先检查这 6 项',
        author='陈泊安',
        content='Excel 那条里如果能强调一下“标签不是在这一轮处理”，新手会少走很多弯路。',
        created_at='2026-01-08 21:16:00',
    ),
    DemoCommentSpec(
        post_title='【站务教程】批量导题前先把数据整理到“可导入状态”：我会先检查这 6 项',
        author='admin',
        content='对，这一点我这两次导题都踩过坑，Excel 先保结构，标签放导入后做批量整理会更稳。',
        created_at='2026-01-08 21:28:00',
        parent_content='Excel 那条里如果能强调一下“标签不是在这一轮处理”，新手会少走很多弯路。',
        reply_to_user='陈泊安',
    ),
    DemoCommentSpec(
        post_title='【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出',
        author='林粤',
        content='我很认同先做 20 道小样本这一条，导题最怕的不是失败，而是批量成功后才发现结构错了。',
        created_at='2026-01-14 22:02:00',
    ),
    DemoCommentSpec(
        post_title='计算机网络期末复习框架：我会把应用层、传输层、网络层拆成三轮',
        author='许清和',
        content='我也是先把应用层和传输层拉顺，不然一上来就做路由题很容易直接失去节奏。',
        created_at='2026-01-21 21:58:00',
    ),
    DemoCommentSpec(
        post_title='计网里最容易混的 8 组概念，我是怎么在个人题库里拆标签的',
        author='陈泊安',
        content='MTU 和 MSS 这组我也会单独打标签，题目稍微一换场景就特别容易错。',
        created_at='2026-01-30 21:36:00',
    ),
    DemoCommentSpec(
        post_title='【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试',
        author='宋闻溪',
        content='我现在也是先用公共题库确认范围，再把高频错题沉到个人题库里，不然很容易整理过度。',
        created_at='2026-02-08 22:04:00',
    ),
    DemoCommentSpec(
        post_title='数据结构刷题路线：链表、栈队列、树、图，我现在按这个顺序推进',
        author='admin',
        content='这个顺序很适合做演示，因为能明显看出从“手感”到“结构”的推进关系。',
        created_at='2026-02-14 20:30:00',
    ),
    DemoCommentSpec(
        post_title='【功能说明】为什么这个站要同时保留“公共题库”和“个人题库”两条线',
        author='周既白',
        content='我以前也会把两条线混在一起，后来才发现一个负责覆盖，一个负责组织，任务完全不一样。',
        created_at='2026-02-16 20:36:00',
    ),
    DemoCommentSpec(
        post_title='用“个人题库 + 标签 + 错题本”整理操作系统，我目前最稳定的结构',
        author='宋闻溪',
        content='我最近也在把操作系统拆成专题，最大的感受是“同步与互斥”必须单独收，不然后面回看特别散。',
        created_at='2026-02-23 22:08:00',
    ),
    DemoCommentSpec(
        post_title='【功能说明】这个站里哪些数据会同步：收藏、错题、答案、进度、考试、论坛',
        author='许清和',
        content='对我来说考试记录和错题同步最重要，不然模拟完第二天很难接着复盘。',
        created_at='2026-03-02 21:34:00',
    ),
    DemoCommentSpec(
        post_title='计算机组成原理复习框架：指令、流水线、Cache，题库应该怎么建',
        author='林粤',
        content='组成原理我也是把 Cache 和流水线单独抽出来做专题，这两块真的很适合反复回练。',
        created_at='2026-03-10 21:12:00',
    ),
    DemoCommentSpec(
        post_title='【功能说明】我最想展示给新同学的 5 个特色：题库、复盘、数据、论坛、双端协同',
        author='宋闻溪',
        content='我最喜欢的其实是“论坛是学习系统的一部分”这一点，教程和大纲沉淀下来以后，社区就不空了。',
        created_at='2026-03-18 22:01:00',
    ),
    DemoCommentSpec(
        post_title='数据库复习不只是 SQL：ER、范式、查询优化我会分三轮做',
        author='陈泊安',
        content='很多同学数据库只刷 SQL，后面一到范式和索引题就掉分，这三轮拆法很有用。',
        created_at='2026-03-24 21:48:00',
    ),
    DemoCommentSpec(
        post_title='【站务说明】题目导入后为什么还要导出一次：我会用 Excel / Word / 题目包做回归',
        author='林粤',
        content='导出回查这一步特别像做接口回归，不是为了多做一次，而是为了尽早发现结构偏差。',
        created_at='2026-03-27 21:26:00',
    ),
    DemoCommentSpec(
        post_title='导题后怎么做抽检：我只盯这 5 类高风险字段，能省很多返工',
        author='admin',
        content='我现在也是先看这 5 类字段，尤其是多选题答案和图片路径，最容易在演示时暴露问题。',
        created_at='2026-03-28 21:22:00',
    ),
    DemoCommentSpec(
        post_title='软工 / 计基这种大纲型课程，我现在会先建“章节导航帖”再回填题库',
        author='周既白',
        content='先写导航帖真的能省很多力气，不然题库和笔记会越整理越碎。',
        created_at='2026-03-31 21:06:00',
    ),
)


DEMO_COMMENTS = BASE_COMMENTS + EXTENDED_COMMENTS


FOLLOW_RELATIONS: tuple[tuple[str, str], ...] = (
    ('林粤', 'admin'),
    ('周既白', 'admin'),
    ('许清和', 'admin'),
    ('陈泊安', 'admin'),
    ('宋闻溪', 'admin'),
    ('admin', '林粤'),
    ('admin', '周既白'),
    ('林粤', '周既白'),
    ('林粤', '宋闻溪'),
    ('周既白', '林粤'),
    ('周既白', '陈泊安'),
    ('许清和', '林粤'),
    ('陈泊安', '周既白'),
    ('陈泊安', 'admin'),
    ('宋闻溪', '林粤'),
    ('宋闻溪', '许清和'),
)


POLL_VOTES: tuple[PollVoteSpec, ...] = (
    PollVoteSpec('【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出', '林粤', (1,)),
    PollVoteSpec('【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出', '周既白', (1,)),
    PollVoteSpec('【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出', '许清和', (2,)),
    PollVoteSpec('【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出', '陈泊安', (0,)),
    PollVoteSpec('【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出', '宋闻溪', (1,)),
    PollVoteSpec('【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试', '林粤', (2,)),
    PollVoteSpec('【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试', '周既白', (0,)),
    PollVoteSpec('【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试', '许清和', (3,)),
    PollVoteSpec('【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试', '陈泊安', (1,)),
    PollVoteSpec('【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试', '宋闻溪', (2,)),
    PollVoteSpec('【功能说明】这个站里哪些数据会同步：收藏、错题、答案、进度、考试、论坛', '林粤', (0, 1, 2)),
    PollVoteSpec('【功能说明】这个站里哪些数据会同步：收藏、错题、答案、进度、考试、论坛', '周既白', (1, 2, 3)),
    PollVoteSpec('【功能说明】这个站里哪些数据会同步：收藏、错题、答案、进度、考试、论坛', '许清和', (1, 3)),
    PollVoteSpec('【功能说明】这个站里哪些数据会同步：收藏、错题、答案、进度、考试、论坛', '陈泊安', (0, 2, 4)),
    PollVoteSpec('【功能说明】这个站里哪些数据会同步：收藏、错题、答案、进度、考试、论坛', '宋闻溪', (0, 1, 4)),
)


COMMENT_REACTIONS: tuple[CommentReactionSpec, ...] = (
    CommentReactionSpec('我也做过按知识点分组，最后发现按“为什么会错”更适合复盘，特别是看漏条件这种错误。', '周既白', '👍'),
    CommentReactionSpec('Markdown 和可视化编辑并存真的很实用，我发学习周报的时候就很依赖这个。', '陈泊安', '✨'),
    CommentReactionSpec('换环境真的有用，我最近也会去图书馆外面的长廊背概念题，效率会比闷在座位上更高。', '许清和', '🌊'),
    CommentReactionSpec('Excel 那条里如果能强调一下“标签不是在这一轮处理”，新手会少走很多弯路。', '林粤', '👍'),
    CommentReactionSpec('我最喜欢的其实是“论坛是学习系统的一部分”这一点，教程和大纲沉淀下来以后，社区就不空了。', 'admin', '✅'),
)


SYSTEM_NOTIFICATIONS: tuple[NotificationSpec, ...] = (
    NotificationSpec(
        title='站务：Excel 导题模板与导出链路已统一',
        content='后台科目页已支持统一的 Excel 导题模板、JSON 导入、题目包导入与 Excel / Word / 题目包导出，适合演示完整题库维护链路。',
        n_type='info',
        priority=9,
        start_at='2026-03-27 09:00:00',
        end_at='2026-05-01 09:00:00',
        dismiss_users=('林粤',),
    ),
    NotificationSpec(
        title='站务：论坛已补充学习流程专题与投票帖',
        content='论坛新增了导题教程、学习流程、平台特色与课程复习框架等长帖，部分帖子带目录和投票，便于展示阅读与互动能力。',
        n_type='success',
        priority=7,
        start_at='2026-04-01 10:00:00',
        end_at='2026-05-10 10:00:00',
        dismiss_users=('宋闻溪',),
    ),
    NotificationSpec(
        title='论坛专题：欢迎补充各科复习大纲与抽检经验',
        content='如果你正在整理计网、数据结构、操作系统、数据库等课程的题库和复习框架，欢迎在论坛继续补充专题帖。',
        n_type='info',
        priority=5,
        start_at='2026-04-02 08:00:00',
        end_at='2026-05-20 08:00:00',
    ),
)


INTERACTION_EVENTS: tuple[InteractionSpec, ...] = (
    InteractionSpec('admin', '林粤', 'follow', 'user', 'user:admin', None, '林粤 关注了你', '2026-03-12 20:10:00', False),
    InteractionSpec('admin', '陈泊安', 'follow', 'user', 'user:admin', None, '陈泊安 关注了你', '2026-03-18 21:12:00', False),
    InteractionSpec('admin', '宋闻溪', 'follow', 'user', 'user:admin', None, '宋闻溪 关注了你', '2026-03-31 21:08:00', True),
    InteractionSpec('林粤', 'admin', 'like_post', 'post', 'post:数据结构刷题路线：链表、栈队列、树、图，我现在按这个顺序推进', 'post:数据结构刷题路线：链表、栈队列、树、图，我现在按这个顺序推进', 'admin 点赞了你的帖子', '2026-02-14 20:31:00', False),
    InteractionSpec('许清和', '林粤', 'comment', 'post', 'post:周末在海边背了 40 道计网题，意外比在宿舍更专注', 'post:周末在海边背了 40 道计网题，意外比在宿舍更专注', '林粤 评论了你的帖子', '2026-04-04 20:10:00', False),
    InteractionSpec('陈泊安', 'admin', 'reply', 'comment', 'comment:Excel 那条里如果能强调一下“标签不是在这一轮处理”，新手会少走很多弯路。', 'post:【站务教程】批量导题前先把数据整理到“可导入状态”：我会先检查这 6 项', 'admin 回复了你的评论', '2026-01-08 21:28:00', False),
    InteractionSpec('admin', '宋闻溪', 'comment', 'post', 'post:【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试', 'post:【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试', '宋闻溪 评论了你的帖子', '2026-02-08 22:04:00', True),
)


CHAT_THREADS: tuple[ChatThreadSpec, ...] = (
    ChatThreadSpec(
        participants=('admin', '陈泊安'),
        title='导题抽检讨论',
        unread_users=('陈泊安',),
        messages=(
            ChatMessageSpec('admin', '{post:【站务教程】从 /admin/subjects 开始，完整走一遍题目导入、抽检、导出}', '2026-01-14 21:56:00'),
            ChatMessageSpec('admin', '这篇我已经发出来了，你从“实际导题的人”角度看看，还有没有哪一步要再写显眼一点。', '2026-01-14 21:57:00'),
            ChatMessageSpec('陈泊安', '我建议把“先导 20 道小样本”单独拉出来写，很多人第一次导题最容易忽略这一步。', '2026-01-14 22:03:00'),
            ChatMessageSpec('admin', '收到，我再补一条“导入成功后先反向导出回查”。', '2026-01-14 22:08:00'),
        ),
    ),
    ChatThreadSpec(
        participants=('admin', '林粤'),
        title='学习流程演示讨论',
        unread_users=('admin',),
        messages=(
            ChatMessageSpec('admin', '{post:【功能说明】我自己在站内的完整学习流程：公共题库 → 收藏/错题 → 标签 → 模拟考试}', '2026-02-08 21:18:00'),
            ChatMessageSpec('admin', '我准备把这条链路当成默认演示路径，你从学习者视角帮我看看有没有断层。', '2026-02-08 21:19:00'),
            ChatMessageSpec('林粤', '我觉得顺序是对的，最重要的是把“什么时候才需要建个人题库”讲清楚。', '2026-02-08 21:28:00'),
            ChatMessageSpec('林粤', '如果先整理后刷题，很多人会在第一步就把自己耗住。', '2026-02-08 21:29:00'),
        ),
    ),
    ChatThreadSpec(
        participants=('周既白', '许清和'),
        title='计网复习串题',
        unread_users=('周既白',),
        messages=(
            ChatMessageSpec('周既白', '{post:计算机网络期末复习框架：我会把应用层、传输层、网络层拆成三轮}', '2026-01-21 21:46:00'),
            ChatMessageSpec('周既白', '我把复习框架先发出来了，你看看有没有哪块应该再拆细一点。', '2026-01-21 21:47:00'),
            ChatMessageSpec('许清和', '我觉得可以把“易混概念”单独抽成一轮，你前两轮更像覆盖，第三轮更像纠错。', '2026-01-21 21:55:00'),
            ChatMessageSpec('周既白', '对，这样更像真的复盘节奏。', '2026-01-21 22:00:00'),
        ),
    ),
    ChatThreadSpec(
        participants=('宋闻溪', '陈泊安'),
        title='课程导航帖讨论',
        unread_users=('宋闻溪',),
        messages=(
            ChatMessageSpec('宋闻溪', '{post:软工 / 计基这种大纲型课程，我现在会先建“章节导航帖”再回填题库}', '2026-03-31 20:40:00'),
            ChatMessageSpec('宋闻溪', '我现在越来越觉得，先把目录写出来再回填题库，会比一开始就堆题稳定很多。', '2026-03-31 20:42:00'),
            ChatMessageSpec('陈泊安', '认同，尤其是那种章节多、题不一定很多的课，导航帖能先把路线钉住。', '2026-03-31 20:49:00'),
            ChatMessageSpec('陈泊安', '后面你再把题库和论坛串起来，整套学习路径就很完整了。', '2026-03-31 20:50:00'),
        ),
    ),
    ChatThreadSpec(
        participants=('admin', '宋闻溪'),
        title='论坛特色展示',
        unread_users=('宋闻溪',),
        messages=(
            ChatMessageSpec('admin', '{post:【功能说明】我最想展示给新同学的 5 个特色：题库、复盘、数据、论坛、双端协同}', '2026-03-18 21:48:00'),
            ChatMessageSpec('admin', '这篇我主要想拿来解释“论坛不是闲聊区”，你看看表达会不会太站务。', '2026-03-18 21:49:00'),
            ChatMessageSpec('宋闻溪', '我觉得很好，尤其是把教程帖和大纲帖放进论坛这件事，会让人一下子明白社区在学什么。', '2026-03-18 22:02:00'),
        ),
    ),
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


def _upsert_signature(user_id: int, signature: str) -> None:
    row = (
        db.session.query(UserProgress)
        .filter(UserProgress.user_id == user_id, UserProgress.p_key == PROFILE_EXTRA_KEY)
        .first()
    )
    payload = {'signature': signature, 'privacy_favorites': 'public', 'privacy_likes': 'public'}
    now_dt = datetime.now()
    if row is None:
        db.session.add(
            UserProgress(
                user_id=user_id,
                p_key=PROFILE_EXTRA_KEY,
                data=json.dumps(payload, ensure_ascii=False),
                created_at=now_dt,
                updated_at=now_dt,
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
    row.updated_at = now_dt


def _get_or_create_demo_user(profile: DemoUserProfile) -> m.User:
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


def _resolve_required_users() -> dict[str, m.User]:
    users = {profile.username: _get_or_create_demo_user(profile) for profile in DEMO_USERS}

    for patch in SYSTEM_USER_PATCHES:
        query = m.User.query.filter(m.User.username == patch.username)
        if patch.phone:
            query = m.User.query.filter((m.User.username == patch.username) | (m.User.phone == patch.phone))
        user = query.order_by(m.User.id.asc()).first()
        if user is None:
            raise RuntimeError(f'缺少系统用户：{patch.username}')
        user.contact = patch.contact
        user.college = patch.college
        user.last_active = _parse_dt(patch.last_active)
        _upsert_signature(user.id, patch.signature)
        users[patch.username] = user

    return users


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
            poll=spec.poll,
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
            poll=spec.poll,
        )
        post = db.session.get(m.ForumPost, existing.id)

    if post is None:
        raise RuntimeError(f'帖子写入后未找到：{spec.title}')

    post.created_at = _parse_dt(spec.created_at)
    post.updated_at = _parse_dt(spec.updated_at)
    post.view_count = int(spec.view_count)
    post.is_featured = bool(spec.is_featured)
    post.is_pinned = bool(spec.is_pinned)
    db.session.flush()
    return post


def _comment_lookup(post_id: int, content: str, author_id: int) -> m.ForumComment | None:
    return (
        m.ForumComment.query.filter_by(post_id=post_id, author_id=author_id, content=content, is_deleted=False)
        .order_by(m.ForumComment.id.asc())
        .first()
    )


def _get_or_create_comment(spec: DemoCommentSpec, posts: dict[str, m.ForumPost], users: dict[str, m.User]) -> m.ForumComment:
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


def _ensure_post_like(post_id: int, user_id: int) -> None:
    db.session.execute(
        text(
            'INSERT INTO forum_likes (user_id, target_type, target_id) '
            "VALUES (:uid, 'post', :tid) ON CONFLICT (user_id, target_type, target_id) DO NOTHING"
        ),
        {'uid': user_id, 'tid': post_id},
    )


def _ensure_post_favorite(post_id: int, user_id: int) -> None:
    db.session.execute(
        text(
            'INSERT INTO forum_favorites (user_id, post_id) '
            'VALUES (:uid, :pid) ON CONFLICT (user_id, post_id) DO NOTHING'
        ),
        {'uid': user_id, 'pid': post_id},
    )


def _apply_post_engagement(posts: dict[str, m.ForumPost], users: dict[str, m.User]) -> None:
    demo_usernames = [profile.username for profile in DEMO_USERS]
    for spec in DEMO_POSTS:
        post = posts[spec.title]
        if spec.author == 'admin':
            like_names = demo_usernames
            fav_names = ('林粤', '陈泊安', '宋闻溪')
        else:
            peer_names = [name for name in demo_usernames if name != spec.author]
            like_names = ('admin', peer_names[0], peer_names[1])
            fav_names = ('admin', peer_names[-1])
        for username in like_names:
            _ensure_post_like(post.id, users[username].id)
        for username in fav_names:
            if username != spec.author:
                _ensure_post_favorite(post.id, users[username].id)


def _sync_poll_votes(posts: dict[str, m.ForumPost], users: dict[str, m.User]) -> None:
    votes_by_post: dict[str, list[PollVoteSpec]] = {}
    for item in POLL_VOTES:
        votes_by_post.setdefault(item.post_title, []).append(item)

    for spec in DEMO_POSTS:
        if not spec.poll:
            continue
        post = posts[spec.title]
        related_votes = votes_by_post.get(spec.title, [])
        if not related_votes:
            continue
        target_user_ids = [users[item.username].id for item in related_votes]
        db.session.execute(
            text('DELETE FROM forum_poll_votes WHERE post_id = :pid AND user_id = ANY(:uids)'),
            {'pid': post.id, 'uids': target_user_ids},
        )
        for item in related_votes:
            for option_index in item.option_indices:
                db.session.execute(
                    text(
                        'INSERT INTO forum_poll_votes (post_id, user_id, option_index) '
                        'VALUES (:pid, :uid, :oi) '
                        'ON CONFLICT (post_id, user_id, option_index) DO NOTHING'
                    ),
                    {'pid': post.id, 'uid': users[item.username].id, 'oi': int(option_index)},
                )


def _ensure_comment_reaction(comment_id: int, user_id: int, emoji: str) -> None:
    db.session.execute(
        text(
            'INSERT INTO forum_reactions (user_id, target_type, target_id, emoji) '
            'VALUES (:uid, :tt, :tid, :emoji) '
            'ON CONFLICT (user_id, target_type, target_id, emoji) DO NOTHING'
        ),
        {'uid': user_id, 'tt': 'comment', 'tid': comment_id, 'emoji': emoji},
    )


def _apply_comment_reactions(comments: dict[str, m.ForumComment], users: dict[str, m.User]) -> None:
    for item in COMMENT_REACTIONS:
        comment = comments.get(item.comment_content)
        if comment is None:
            continue
        _ensure_comment_reaction(comment.id, users[item.username].id, item.emoji)


def _ensure_follow(follower_id: int, following_id: int) -> None:
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


def _apply_follows(users: dict[str, m.User]) -> None:
    for follower_name, following_name in FOLLOW_RELATIONS:
        _ensure_follow(users[follower_name].id, users[following_name].id)


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


def _upsert_notification(spec: NotificationSpec, admin_user_id: int, users: dict[str, m.User]) -> None:
    row = (
        m.Notification.query.filter_by(title=spec.title, created_by=admin_user_id)
        .order_by(m.Notification.id.asc())
        .first()
    )
    start_at = _parse_dt(spec.start_at)
    end_at = _parse_dt(spec.end_at)
    if row is None:
        row = m.Notification(
            title=spec.title,
            content=spec.content,
            n_type=spec.n_type,
            priority=spec.priority,
            is_active=True,
            start_at=start_at,
            end_at=end_at,
            created_by=admin_user_id,
            created_at=start_at,
            updated_at=start_at,
        )
        db.session.add(row)
        db.session.flush()
    else:
        row.content = spec.content
        row.n_type = spec.n_type
        row.priority = spec.priority
        row.is_active = True
        row.start_at = start_at
        row.end_at = end_at
        row.updated_at = start_at

    for username in spec.dismiss_users:
        uid = users[username].id
        existing = (
            m.NotificationDismissal.query.filter_by(user_id=uid, notification_id=row.id)
            .order_by(m.NotificationDismissal.id.asc())
            .first()
        )
        if existing is None:
            db.session.add(
                m.NotificationDismissal(
                    user_id=uid,
                    notification_id=row.id,
                    dismissed_at=start_at,
                )
            )
        else:
            existing.dismissed_at = start_at


def _seed_system_notifications(users: dict[str, m.User]) -> None:
    admin_user = users['admin']
    for spec in SYSTEM_NOTIFICATIONS:
        _upsert_notification(spec, admin_user.id, users)


def _resolve_target_ref(target_ref: str, posts: dict[str, m.ForumPost], comments: dict[str, m.ForumComment], users: dict[str, m.User]) -> tuple[str, int | None]:
    if target_ref.startswith('post:'):
        title = target_ref[5:]
        post = posts.get(title)
        return 'post', post.id if post else None
    if target_ref.startswith('comment:'):
        content = target_ref[8:]
        comment = comments.get(content)
        return 'comment', comment.id if comment else None
    if target_ref.startswith('user:'):
        username = target_ref[5:]
        user = users.get(username)
        return 'user', user.id if user else None
    return 'unknown', None


def _upsert_interaction_notifications(posts: dict[str, m.ForumPost], comments: dict[str, m.ForumComment], users: dict[str, m.User]) -> None:
    for spec in INTERACTION_EVENTS:
        target_type, target_id = _resolve_target_ref(spec.target_ref, posts, comments, users)
        if target_type == 'unknown' or target_id is None:
            continue
        post_id = None
        if spec.post_ref:
            _, resolved_post_id = _resolve_target_ref(spec.post_ref, posts, comments, users)
            post_id = resolved_post_id
        db.session.execute(
            text(
                '''
                INSERT INTO interaction_notifications
                    (user_id, actor_id, action_type, target_type, target_id, post_id, content_preview, is_read, created_at)
                VALUES (:uid, :aid, :atype, :ttype, :tid, :pid, :preview, :is_read, :created_at)
                ON CONFLICT (user_id, actor_id, action_type, target_type, target_id) DO UPDATE
                SET post_id = EXCLUDED.post_id,
                    content_preview = EXCLUDED.content_preview,
                    is_read = EXCLUDED.is_read,
                    created_at = EXCLUDED.created_at
                '''
            ),
            {
                'uid': users[spec.user].id,
                'aid': users[spec.actor].id,
                'atype': spec.action_type,
                'ttype': target_type,
                'tid': target_id,
                'pid': post_id,
                'preview': spec.content_preview[:200],
                'is_read': spec.is_read,
                'created_at': _parse_dt(spec.created_at),
            },
        )


def _pair_key(left_user_id: int, right_user_id: int) -> str:
    return f'{min(left_user_id, right_user_id)}:{max(left_user_id, right_user_id)}'


def _get_or_create_direct_conversation(left: m.User, right: m.User, title: str, created_at: datetime) -> m.ChatConversation:
    pair_key = _pair_key(left.id, right.id)
    conv = (
        m.ChatConversation.query.filter_by(c_type='direct', direct_pair_key=pair_key)
        .order_by(m.ChatConversation.id.asc())
        .first()
    )
    if conv is None:
        conv = m.ChatConversation(
            c_type='direct',
            title=title,
            direct_pair_key=pair_key,
            created_at=created_at,
            updated_at=created_at,
        )
        db.session.add(conv)
        db.session.flush()
    else:
        conv.title = title
        conv.created_at = min(conv.created_at or created_at, created_at)

    members = {member.user_id: member for member in conv.members.all()}
    if left.id not in members:
        db.session.add(m.ChatMember(conversation_id=conv.id, user_id=left.id, role='owner', joined_at=created_at))
    if right.id not in members:
        db.session.add(m.ChatMember(conversation_id=conv.id, user_id=right.id, role='member', joined_at=created_at))
    db.session.flush()
    return conv


def _render_chat_content(raw: str, posts: dict[str, m.ForumPost]) -> str:
    match = POST_TOKEN_RE.match(raw.strip())
    if not match:
        return raw
    title = match.group(1).strip()
    post = posts.get(title)
    if post is None:
        raise RuntimeError(f'聊天内容引用了不存在的帖子：{title}')
    return f'[转发帖子] {title}\n/forum/post/{post.id}'


def _ensure_chat_message(conv: m.ChatConversation, sender_id: int, content: str, content_type: str, created_at: datetime) -> m.ChatMessage:
    existing = (
        m.ChatMessage.query.filter_by(
            conversation_id=conv.id,
            sender_id=sender_id,
            content=content,
            content_type=content_type,
            created_at=created_at,
        )
        .order_by(m.ChatMessage.id.asc())
        .first()
    )
    if existing is not None:
        return existing
    message = m.ChatMessage(
        conversation_id=conv.id,
        sender_id=sender_id,
        content=content,
        content_type=content_type,
        created_at=created_at,
    )
    db.session.add(message)
    db.session.flush()
    return message


def _seed_private_chats(posts: dict[str, m.ForumPost], users: dict[str, m.User]) -> None:
    for thread in CHAT_THREADS:
        left = users[thread.participants[0]]
        right = users[thread.participants[1]]
        first_time = _parse_dt(thread.messages[0].created_at)
        conv = _get_or_create_direct_conversation(left, right, thread.title, first_time)
        messages: list[m.ChatMessage] = []
        for item in thread.messages:
            created_at = _parse_dt(item.created_at)
            content = _render_chat_content(item.content, posts)
            message = _ensure_chat_message(conv, users[item.sender].id, content, item.content_type, created_at)
            messages.append(message)
        if messages:
            conv.updated_at = max(msg.created_at for msg in messages if msg.created_at)
        db.session.flush()
        last_message_id = messages[-1].id if messages else 0
        prev_message_id = messages[-2].id if len(messages) >= 2 else 0
        for member in conv.members.all():
            member.last_read_message_id = last_message_id
        for username in thread.unread_users:
            member = (
                m.ChatMember.query.filter_by(conversation_id=conv.id, user_id=users[username].id)
                .order_by(m.ChatMember.id.asc())
                .first()
            )
            if member is not None:
                member.last_read_message_id = prev_message_id


def _count_managed_posts(posts: dict[str, m.ForumPost]) -> int:
    return len(posts)


def _count_managed_comments(comments: dict[str, m.ForumComment]) -> int:
    return len(comments)


def main() -> int:
    app = create_app('development')
    with app.app_context():
        _ensure_dev_or_test_env(app)
        _require_import_assets()
        _ensure_upload_dirs()

        users = _resolve_required_users()
        db.session.commit()

        boards = _board_map()
        posts = {spec.title: _get_or_create_post(spec, users, boards) for spec in DEMO_POSTS}
        db.session.commit()

        comments = {spec.content: _get_or_create_comment(spec, posts, users) for spec in DEMO_COMMENTS}
        _apply_follows(users)
        _apply_post_engagement(posts, users)
        _sync_poll_votes(posts, users)
        _apply_comment_reactions(comments, users)
        _refresh_comment_stats()
        _refresh_post_stats()
        _seed_system_notifications(users)
        _upsert_interaction_notifications(posts, comments, users)
        _seed_private_chats(posts, users)
        db.session.commit()

        print('已写入扩展论坛演示数据：')
        print(f'- 演示用户：{len(DEMO_USERS)} 位（另复用系统管理员 1 位）')
        print(f'- 管理帖子：{_count_managed_posts(posts)} 篇')
        print(f'- 管理评论：{_count_managed_comments(comments)} 条')
        print(f'- 系统通知：{len(SYSTEM_NOTIFICATIONS)} 条')
        print(f'- 私信线程：{len(CHAT_THREADS)} 个')
        print(f'- 通用登录密码：{DEMO_PASSWORD}')
        print('- 演示用户列表：')
        for profile in DEMO_USERS:
            print(f'  * {profile.username} / {profile.email} / {profile.phone}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
