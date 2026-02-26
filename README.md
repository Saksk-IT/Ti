# Ti — 题库系统

面向考试备考的全栈题库平台，支持微信小程序和 Web 双端访问，共享同一后端与数据。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3 / Flask 3.1 / SQLAlchemy 2 / Alembic |
| 数据库 | PostgreSQL 16（生产） / SQLite（开发可选） |
| 缓存 & 队列 | Redis 7 / RQ |
| Web 前端 | Jinja2 模板 + 原生 JS/CSS（响应式，深色/浅色模式） |
| 小程序 | TypeScript + LESS，微信原生框架（Skyline 渲染） |
| AI | 阿里云 DashScope（通义千问）— 题目 AI 解析 |
| 部署 | Docker Compose / Gunicorn / Nginx 反代 |

## 项目结构

```
Ti/
├── app/                        # Flask 后端
│   ├── __init__.py             # create_app() 工厂
│   ├── core/                   # 基础设施
│   │   ├── config.py           # 环境配置类
│   │   ├── extensions.py       # db, migrate, csrf, limiter, cors
│   │   ├── errors.py           # 全局错误处理
│   │   ├── models/             # 数据模型（user, question, exam）
│   │   └── utils/              # JWT、校验、Redis、RQ 等工具
│   ├── modules/                # 业务模块（Blueprint）
│   │   ├── auth/               # 登录注册、微信 OAuth、邮箱验证
│   │   ├── quiz/               # 刷题练习、收藏、错题、AI 解析
│   │   ├── exam/               # 模拟考试
│   │   ├── coding/             # 编程题判题
│   │   ├── user_bank/          # 用户自建题库（CRUD、分享、公开）
│   │   ├── chat/               # 聊天消息
│   │   ├── forum/              # 论坛
│   │   ├── admin/              # 后台管理
│   │   ├── notifications/      # 系统通知
│   │   ├── popups/             # 弹窗管理
│   │   ├── user/               # 用户资料与设置
│   │   └── main/               # 首页、导航
│   └── tasks/                  # RQ 异步任务（AI 解析等）
├── miniprogram-1/              # 微信小程序
│   └── miniprogram/
│       ├── pages/              # ~50 个页面
│       ├── packages/           # 分包（数据中心等）
│       ├── components/         # 公共组件
│       └── utils/              # 工具函数
├── templates/                  # Jinja2 Web 模板
├── static/                     # 静态资源（CSS/JS/图标）
├── migrations/                 # Alembic 迁移脚本
├── docker/                     # Dockerfile
├── compose.dev.yml             # 开发环境编排
├── compose.prod.yml            # 生产环境编排
├── run.py                      # 开发启动入口
├── requirements.txt            # Python 依赖
└── var/                        # 运行时数据（日志、上传、SQLite）
```
## 快速开始

### 前置条件

- Python 3.10+
- Node.js（小程序开发时需要）
- 微信开发者工具（小程序开发时需要）
- Docker & Docker Compose（容器化部署时需要）

### 本地开发（最简方式）

```bash
# 1. 克隆并进入项目
git clone <repo-url> && cd Ti

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env，填入微信 AppID 等必要配置

# 5. 初始化数据库（默认 SQLite，零配置）
flask db upgrade

# 6. 启动
python run.py
# 访问 http://127.0.0.1:5000
```

### Docker 开发环境

```bash
docker compose -f compose.dev.yml up
# Web: http://localhost:8000
# 包含: Flask + PostgreSQL 16 + Redis 7 + RQ Worker
```

### 生产部署

```bash
# 准备 .env.production（参考 .env.example 中的生产配置部分）
docker compose --env-file .env.production -f compose.prod.yml up -d
# Gunicorn 绑定 127.0.0.1:8000，需配合 Nginx 反代
```
## 环境变量

完整配置见 `.env.example`，关键项：

| 变量 | 说明 | 开发默认值 |
|---|---|---|
| `SECRET_KEY` | Flask 密钥 | `dev-secret-key` |
| `DATABASE_URL` | PostgreSQL 连接串（不设则回退 SQLite） | — |
| `REDIS_URL` | Redis 连接串（不设则缓存降级、限流用内存） | — |
| `WECHAT_APPID` / `WECHAT_SECRET` | 微信小程序凭证 | — |
| `DASHSCOPE_API_KEY` | 通义千问 API 密钥（AI 解析功能） | — |
| `MAIL_ENABLED` | 邮件服务开关 | `true` |
| `MAIL_CONSOLE_OUTPUT` | 开发环境验证码输出到控制台 | `true` |

## 模块说明

每个模块为独立 Blueprint，内含 `pages.py`（Web 路由）和 `api.py`（JSON API）：

| 模块 | 功能 |
|---|---|
| `auth` | 登录注册、微信 OAuth、邮箱验证码、JWT 签发 |
| `quiz` | 刷题练习、收藏/错题本、答题记录、AI 解析、间隔复习 |
| `exam` | 模拟考试创建与提交、考试模板 |
| `coding` | 编程题目与在线判题 |
| `user_bank` | 用户自建题库、分享码/链接分享、公开题库 |
| `chat` | 用户间聊天消息 |
| `forum` | 论坛（帖子发布、评论、点赞） |
| `admin` | 后台管理（用户、题目、科目、通知、系统配置） |
| `notifications` | 系统通知推送 |
| `popups` | 弹窗公告管理 |
| `user` | 用户资料、设置、签到、统计 |
| `main` | 首页、导航枢纽 |

## 认证机制

- Web 端：Flask Session，支持 `session_version` 强制下线、邮箱绑定拦截
- 小程序端：JWT Bearer Token（PyJWT），微信 `openid` 登录 + 邮箱 OTP 登录

## 数据库

- 40+ 张表，通过 Alembic 管理迁移
- 开发环境默认 SQLite（`var/instance/submissions.db`），零配置即可运行
- 生产环境使用 PostgreSQL 16，支持连接池配置（`DB_POOL_SIZE` / `DB_MAX_OVERFLOW`）
- 迁移命令：`flask db upgrade`（应用）/ `flask db migrate -m "描述"`（生成）

## 小程序开发

```bash
# 用微信开发者工具打开 miniprogram-1/ 目录
# 四 Tab 导航：首页 / 科目 / 题库 / 我的
# 支持分包加载、深色模式（theme.json）
```

## 许可证

私有项目，未经授权禁止使用。
