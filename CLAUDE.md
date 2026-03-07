## 1) 范围与兼容性（MUST）

- 允许：修改后端（Flask）代码、添加新的小程序页面、添加新的后端端点、为可维护性做必要重构。
- 保持兼容性：小程序和网页必须共享相同的数据与语义（包括但不限于：收藏 / 错误 / 用户答案 / 用户进度 / 考试）。
- 本项目现在处于开发阶段，在本机运行的方式是 Docker 开发模式，一切调试与开发都要基于 Docker。
- 当用户提出某需求或某功能时，请你先参考业内最佳实践，然后再进行实现或改动。

## 双机器同步规范（MUST）

适用场景：同一开发者在 Mac / Windows 间切换开发，每次提交后必须立即同步到远端（不可省略）：
   - `git push -u <remote> <branch>`（首次）
   - `git push <remote> <branch>`（后续）

## 2.1 执行顺序（给 AI 的固定模板）

1. 用 1～2 句话复述目标 + 关键约束（端：小程序/Web；是否涉及 UI；是否要新增接口）。
2. 选择并声明将使用的 skills / MCP（如不需要也要声明"无"）。
3. 需要补充信息时，先用第 5 节的"选项式澄清问题"问 2～4 个问题再实施。
4. 修改代码尽量小步、可回滚；优先遵循现有模式与命名。
5. 交付前做最小验证（能跑就跑；不能跑就说明原因与手动验证步骤）。

## 2.2 任务开始检查清单（MUST）

每次收到新任务时，AI 必须在内部完成以下检查（无需输出给用户）：

1. [ ] 扫描用户消息中的关键词，匹配skills、mcp、commands触发条件
2. [ ] 若匹配到触发条件，自动加载对应 skill 或调用 MCP
3. [ ] 若涉及框架/库用法不确定，主动调用 Context7 查询
4. [ ] 若涉及前端页面调试，主动使用 chrome-devtools 获取页面状态
5. [ ] 若无匹配，声明"本次使用：工具（...）；MCP（无）；skills（无）"

注： 每次调用 chrome  MCP 用户没有要求时，应该默认打开 PC 端大小的窗口，我给你提供一套超级管理员的账号密码，用于调用时登录。
  账号：13573028533
  密码：aa658661

## 3) 前端设计要求（MUST）

- 所有 Web 页面必须适配移动端（响应式布局、触控友好）。
- Web 端与小程序端的主题在元素/颜色/风格上保持一致；新老页面都要适配主题风格切换与深色/浅色模式切换。
- 尽量避免高饱和颜色，使用半饱和颜色代替。
- UI 结构尽量避免“容器套容器”；能用一层容器解决就不要两层互相嵌套。

## 4) 代码风格与结构（SHOULD）

- 尽量保持小变更，避免无关重构（除非明确提出“重构/抛弃/重做”等）。
- 倾向模块化：避免巨大文件；当单文件代码行数超过 1500 行时，按领域/服务/工具等维度拆分。
- 遵循现有项目模式与命名规范。

## 5) 当需求不明确时（MUST）

- 在实施前先提出 2～4 个“可直接选项回复”的澄清问题（避免跑偏）。你可以只回复选项字母/数字，例如：`1C 2A 3B 4A`。
- 说明：这里不限制我“提问的范围”，只是要求尽量把问题做成选择题模板；仍可补充其他澄清问题，并尽量提供可选项。
- 推荐提问模板（按需选 2～4 条）：
  1) 影响端：A) 仅小程序 B) 仅 Web C) 两端都要 D) 先小程序后 Web
  2) 入口/页面/路由：A) 我会提供明确入口 B) 需要你在仓库里帮我定位 C) 题库广场→题库详情 D) 个人题库→题库详情 E) 其他（我补充）
  3) 后端与数据：A) 不需要后端改动 B) 只改现有接口 C) 新增接口 D) 调整数据结构（字段/表）
  4) 兼容性边界：A) 必须兼容旧数据/旧接口/旧页面 B) 允许新增字段但不破坏旧用法 C) 允许迁移（需说明迁移方式） D) 旧页面可保留但不保证一致
- 若仍不明确，最多再追问 1 个开放式问题：请给 1～2 个“期望输入→期望输出”的具体例子（或截图/接口样例）。
- 当功能或设计不完美时，可以给我 1～3 个可选优化灵感，但不要大幅发散。

## 6) 额外业务上下文（MUST）

- 题库详情页存在两个入口：（题库广场 → 题库详情页）与（个人题库 → 题库详情页）。
- **本地开发环境**：使用 Docker Dev 模式运行，数据库迁移和应用重启需在容器内执行。

## 7) ECC 插件可用命令参考

本项目已配置 Everything Claude Code 插件，以下命令可直接使用：

| 命令 | 用途 |
| ---- | ---- |
| `/plan` | 创建实现计划（复杂功能前必用） |
| `/tdd` | 测试驱动开发工作流 |
| `/code-review` | 代码质量审查 |
| `/python-review` | Python 专项代码审查 |
| `/build-fix` | 修复构建错误 |
| `/refactor-clean` | 清理死代码和冗余文件 |
| `/e2e` | 端到端测试 |
| `/test-coverage` | 检查测试覆盖率 |
| `/update-docs` | 更新文档 |

### 项目级 Python 规则

位于 `.claude/rules/`：

- `python-coding-style.md` — PEP 8、类型注解、不可变性
- `python-patterns.md` — Protocol、Dataclass、Flask 蓝图模式
- `python-testing.md` — pytest、覆盖率、Flask 测试 fixtures
- `python-security.md` — 密钥管理、bandit 扫描、Flask 安全要点
- `python-hooks.md` — PostToolUse hooks 说明

### 项目级 Hooks

配置于 `.claude/settings.local.json`：

- **PostToolUse**: 编辑 `.py` 文件后检测 `print()` 语句并警告；检测硬编码密钥
- **PreToolUse**: Flask 开发服务器和 pytest 运行前提醒使用 tmux

## 8) 骨架屏（Skeleton Loading）规范

### 已知坑点

- **flex 容器必须设 `width: 100%`**：若父容器使用 `max-width` + `flex`，骨架阶段内容少会导致容器宽度远小于数据加载后的宽度，产生跳动。修复方式：`width: 100%; box-sizing: border-box;`。
- **骨架必须复用真实组件的 CSS 类**：不要用 `border:none; background:transparent; padding:0` 覆盖真实样式。直接使用 `.forum-comment`、`.comment-header`、`.comment-footer` 等原始类，保证 padding/border/border-radius 一致。
- **骨架行高要匹配实际 font-size / line-height**：例如 `post-title` 是 20px，`post-body` 行高 25.5px（15px × 1.7），`comment-body` 行高 22.4px（14px × 1.6）。

### 验证方法（CDP 远程调试）

当骨架屏尺寸不确定时，使用 Chrome DevTools Protocol 实测：

1. 启动 Chrome：`chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/tmp/chrome-debug"`
2. 用 `Network.setBlockedURLs` 阻断 API 请求，使骨架保持可见
3. 用 `Runtime.evaluate` 获取 `offsetWidth` / `offsetHeight` 与加载后对比
4. 确保骨架阶段与数据加载后的容器宽度一致（高度差异可接受）

### 项目中已有骨架样式

复用 `_styles.html` 中的基础类：
- `.forum-skeleton-row`：矩形占位条（shimmer 动画）
- `.forum-skeleton-avatar`：圆形头像占位（shimmer 动画）
- `.forum-detail-skel`：详情页骨架容器（pulse 动画）
- `@keyframes skeleton-shimmer`：横向光泽滑动

# Ti 项目事实手册（供 AI 执行任何任务前阅读）

> 目标：降低 AI 对项目架构、技术栈、运行方式、业务语义的猜测。
> 适用范围：本仓库内所有开发、排障、重构、文档、接口与页面改动。
> 原则：若本文与代码不一致，以文中列出的“事实源文件”为准。

## 1. 先看结论

- 这是一个 **单仓库全栈项目**，不是前后端分离多仓库架构。
- **Web 端和微信小程序共用同一套 Flask 后端与数据语义**。
- **Web 端不是 SPA**，而是 **Flask + Jinja 模板 + 原生 JS/CSS**。
- **小程序不是 Taro/UniApp/React Native**，而是 **微信原生小程序 + TypeScript + Less**。
- 本机开发的标准方式是 **Docker 开发模式**，入口文件是 `compose.dev.yml`。
- 后端采用 **Flask 应用工厂 + 按业务模块拆分 Blueprint** 的结构。
- API 返回格式正在统一为 **`status/code/data/message` 信封结构**，新接口应尽量遵循它。

## 2. 事实源文件（AI 遇事先查这里）

### 2.1 运行与部署

- 项目总览：`README.md`
- Docker 开发编排：`compose.dev.yml`
- Docker 生产编排：`compose.prod.yml`
- 镜像入口：`docker/Dockerfile`
- 本地启动入口：`run.py`

### 2.2 Flask 后端骨架

- 应用工厂：`app/__init__.py`
- 配置中心：`app/core/config.py`
- 扩展初始化：`app/core/extensions.py`
- 模块注册入口：`app/modules/__init__.py`
- 错误处理：`app/core/errors.py`
- 统一 API 响应工具：`app/core/utils/api_response.py`

### 2.3 Web 前端事实源

- 主页面模块入口：`app/modules/main/__init__.py`
- 主页面路由聚合：`app/modules/main/routes/pages.py`
- 主页面具体拆分：`app/modules/main/routes/pages_components/`
- Web 公共壳层：`app/modules/main/templates/main/shared/app_shell.html`
- 静态资源：`static/css/`、`static/js/`

### 2.4 微信小程序事实源

- 小程序页面/分包/主题入口：`miniprogram-1/miniprogram/app.json`
- 小程序全局启动逻辑：`miniprogram-1/miniprogram/app.js`
- 小程序 TypeScript 配置：`miniprogram-1/tsconfig.json`
- 小程序 API 配置说明：`miniprogram-1/README_API_CONFIG.md`
- 小程序 API 地址与模式切换：`miniprogram-1/miniprogram/utils/config.ts`
- 小程序 HTTP 客户端：`miniprogram-1/miniprogram/utils/api-client.ts`
- 小程序 API 封装：`miniprogram-1/miniprogram/utils/api-endpoints.ts`

## 3. 技术栈与架构判断

### 3.1 后端

- 框架：Flask 3.x
- ORM：SQLAlchemy 2.x
- 迁移：Flask-Migrate + Alembic
- 缓存 / 队列 / 限流存储：Redis + RQ
- WSGI：Gunicorn
- 反代场景：Nginx（生产）

### 3.2 数据层

- 开发 Docker 默认数据库：PostgreSQL 16（见 `compose.dev.yml`）
- 开发兜底数据库：SQLite（见 `app/core/config.py` 的 `SQLALCHEMY_DATABASE_URI` 回退逻辑）
- 迁移目录：`migrations/`
- 运行数据目录：默认 `var/`，可由 `DATA_DIR` 覆盖

### 3.3 Web 前端

- 不是独立前端工程，没有单独的 `package.json`/构建产线。
- 主要形态是 **Jinja 模板服务端渲染 + 原生 JS/CSS 渐进增强**。
- 页面模板按业务模块放在 `app/modules/*/templates/`。
- 公共样式与页面脚本放在 `static/css/`、`static/js/`。

### 3.4 微信小程序

- 使用微信原生工程结构，主目录是 `miniprogram-1/miniprogram/`。
- 页面技术栈是 `wxml + less + ts + js + json`。
- `tsconfig.json` 开启 `allowJs: true`，仓库中大量页面同时保留 `.ts` 与同名 `.js`。
- `app.json` 开启了 `darkmode: true`，并启用 `themeLocation: "theme.json"`。
- `app.json` 使用了 `subPackages`，不要假设所有页面都在主包。

## 4. 标准运行方式（不要猜）

## 4.1 本机开发

本项目的本机标准开发方式是 Docker 开发模式：

```bash
docker compose --env-file .env -f compose.dev.yml up
```

事实：

- Web 服务容器名是 `web`
- Worker 容器名是 `worker`
- 数据库容器名是 `postgres`
- Redis 容器名是 `redis`
- Web 暴露端口是 `8000`
- PostgreSQL 暴露端口是 `5432`

### 4.2 容器内服务事实

开发编排 `compose.dev.yml` 中：

- `web` 使用 `flask run --host 0.0.0.0 --port 8000 --reload`
- `worker` 使用 `rq worker -u $REDIS_URL $RQ_QUEUE_NAME`
- `DATABASE_URL` 指向容器内 PostgreSQL
- `REDIS_URL` 与 `RATELIMIT_STORAGE_URI` 指向容器内 Redis
- `./var` 挂载到容器 `/data`

### 4.3 非 Docker 兜底方式

虽然仓库保留了 `run.py`，但根据项目规则，本机调试与开发应优先基于 Docker 开发模式，而不是把 `python run.py` 当成默认工作流。

## 5. Flask 应用骨架

### 5.1 应用入口

- `run.py` 负责加载 `.env`、解析环境名并调用 `create_app()`。
- `app/__init__.py` 中的 `create_app()` 是真正的应用工厂。

### 5.2 启动阶段会做什么

`create_app()` 会依次完成这些事情：

- 载入配置
- 初始化扩展
- 注册 Jinja 过滤器
- 配置日志
- 注册所有业务模块蓝图
- 豁免 API 蓝图的 CSRF
- 注册上下文处理器
- 注册 `before_request` 钩子
- 注册健康检查接口
- 注册错误处理器
- 预加载 ORM 模型
- 启动后台任务

如果 AI 需要定位“为什么请求会被拦截 / 为什么路由已存在 / 为什么日志格式不同”，先看 `app/__init__.py`。

## 6. 业务模块与路由组织

模块统一在 `app/modules/__init__.py` 注册，当前已注册模块包括：

- `auth`
- `main`
- `quiz`
- `exam`
- `user`
- `chat`
- `notifications`
- `popups`
- `coding`
- `user_bank`
- `forum`
- `admin`

### 6.1 常见模块职责

- `main`：Web 首页、导航枢纽、题库详情、数据中心、资源页、设置页
- `quiz`：刷题、题目详情、收藏、错题、进度、AI 解析、标签、搜索
- `exam`：模拟考试创建、保存草稿、提交、记录、模板、统计
- `user_bank`：个人题库、题目、分享、公开、标签、练习、加入题库
- `user`：个人资料、密码、邮箱、头像、签到、用户统计
- `auth`：登录、邮箱验证码、微信登录/绑定、Web 登录桥接
- `admin`：后台管理与题目导入导出

### 6.2 页面路由与 API 路由

通常每个模块都会同时包含：

- `routes/pages.py`：Web 页面路由
- `routes/api.py`：JSON API

但本仓库不是所有模块都只用这两个文件；多个模块还会继续拆到 `api_components/` 或 `pages_components/`。
因此 AI 不应假设“一个模块只有一个 pages.py / api.py 文件”。

## 7. Web 前端事实

### 7.1 Web 技术形态

- Web 页面由 Flask 直接 `render_template()` 输出。
- 不是 Vue/React SPA，不存在前端路由器作为唯一入口。
- 页面交互靠模板内脚本和 `static/js/*` 完成。

### 7.2 Web 公共壳层

`app/modules/main/templates/main/shared/app_shell.html` 是 Web 前台公共壳层，里面集中定义：

- 布局骨架
- 全局设计变量
- 深色 / 浅色模式
- 主题样式切换
- 通用导航壳

如果改的是 Web 新页面或重构旧页面，通常应接入这个壳层，而不是单独再造一套页面外壳。

### 7.3 Web 典型页面位置

- 题库详情：`app/modules/main/templates/main/subject/subject_detail.html`
- 题库广场：`app/modules/main/templates/main/bank/public_bank.html`
- 题库选择入口：`app/modules/main/templates/main/bank/bank_select_entry.html`
- 数据中心：`app/modules/main/templates/main/data/data_v2_shell.html`
- 错题/收藏详情：`app/modules/main/templates/main/mistakes/mistakes_detail.html`、`app/modules/main/templates/main/favorites/favorites_detail.html`
- 考试：`app/modules/exam/templates/exam/`
- 刷题：`app/modules/quiz/templates/quiz/`

## 8. 微信小程序事实

### 8.1 页面组织

小程序入口在 `miniprogram-1/miniprogram/app.json`，其中可以直接看出：

- 主包页面：登录、首页、题库、我的、练习、考试、设置、题库数据等
- 分包页面：`index-v2`、`subject-detail-v2`、`quiz`、`bank-detail`、数据中心等

### 8.2 小程序主题与字体

`miniprogram-1/miniprogram/app.js` 在全局启动时初始化：

- `themeManager`
- `fontManager`
- 用户设置同步
- 路由变化后的系统 UI 同步

因此，小程序新页面如果完全绕开这些能力，容易造成主题/字体/首屏闪烁不一致。

### 8.3 小程序请求方式

小程序请求的推荐入口不是页面内直接写 `wx.request`，而是：

1. 在 `utils/api-endpoints.ts` 中补或复用 API 方法
2. 让页面调用 `api.xxx()`
3. 统一经过 `utils/api-client.ts` 的 `request()`

这样才能复用：

- 基础 URL 拼接
- Bearer Token 注入
- 统一错误处理
- 统一响应解析
- 开发环境连接失败提示

### 8.4 小程序 API 地址配置

`miniprogram-1/miniprogram/utils/config.ts` 已经明确采用 **显式模式切换**：

- `prod`：生产地址
- `custom`：开发/测试自定义地址

不要再发明新的“自动探测本机 IP”“自动拼 localhost”的配置体系。

### 8.5 Web 容器页事实

小程序内存在一个用于承接 Web 前台能力的 `web-view` 页面：

- 页面：`miniprogram-1/miniprogram/pages/web-frontend/web-frontend.ts`
- 辅助工具：`miniprogram-1/miniprogram/utils/web.ts`

这意味着：当某个能力当前主要存在于 Web 端时，小程序并不一定要立即重做原生页面，也可能通过登录桥接后用 `web-view` 承接。

## 9. 双端共享的数据语义（非常重要）

Web 与小程序必须共享相同的数据语义，至少包括：

- 科目
- 公共题库
- 个人题库
- 题目
- 收藏
- 错题
- 标签
- 用户答案
- 用户进度
- 学习记录
- 数据中心统计
- 模拟考试
- 通知
- 个人资料

### 9.1 公共题库与个人题库是两条线

这是项目里最容易被 AI 混淆的地方：

- 公共题库 / 公共题目常走 `quiz` / `subjects` / `public banks` 语义
- 个人题库常走 `user_bank` / `user/banks/api/*` 语义

做需求前必须先判断：

- 当前操作对象是公共题库还是个人题库
- 路由入口来自题库广场还是个人题库
- 统计、收藏、错题、标签到底挂在哪条数据线上

### 9.2 题库详情页有两个入口

根据项目规则，题库详情相关能力存在两个入口：

- `题库广场 -> 题库详情`
- `个人题库 -> 题库详情`

做详情页功能时，不能只修一条入口链路。

## 10. API 设计事实

### 10.1 响应格式

统一响应工具在 `app/core/utils/api_response.py`，成功响应格式是：

```json
{
  "status": "success",
  "code": 0,
  "data": {},
  "message": "..."
}
```

错误响应格式是：

```json
{
  "status": "error",
  "code": 1,
  "message": "..."
}
```

仓库中仍存在部分旧接口只返回 `status` 或把字段直接铺平；新增或改造接口时，应尽量向统一信封靠拢，并确保旧客户端兼容。

### 10.2 小程序客户端的兼容规则

`miniprogram-1/miniprogram/utils/api-client.ts` 对成功的判断是：

- `result.status === 'success'`
- 或 `result.code === 0`

因此接口演进时，应尽量至少保住这两个兼容判断之一。

### 10.3 健康检查

后端已提供健康检查接口：

- `/api/ping`
- `/api/ping?deep=1`

定义位置在 `app/__init__.py`。

## 11. 认证与安全事实

### 11.1 认证模式不是单一的

当前项目至少有两套认证模式并存：

- Web：以 Session 为主
- 小程序/API：以 JWT Bearer Token 为主

因此，AI 不应假设“所有接口都只看 Session”或“所有页面都只看 JWT”。

### 11.2 CSRF 规则

`app/__init__.py` 中对 API 写请求有额外 CSRF/安全头检查：

- 小程序带有效 JWT 的请求会放行
- Web XHR 请求需带 `X-Requested-With: XMLHttpRequest`
- 登录/验证码等部分端点在豁免名单中

如果新增 Web 端写接口或调整请求方式，必须考虑这条校验链。

### 11.3 限流与 Redis

- 限流存储配置在 `app/core/config.py`
- 生产环境不允许继续使用 `memory://` 作为限流存储
- Redis 同时承担缓存 / RQ / 限流共享存储角色

## 12. 开发时的高频误判提醒

### 不要误判为：

- 前后端分离 SPA 项目
- 小程序跨端框架项目
- 只有 Web 或只有小程序的单端项目
- 只有公共题库、没有个人题库的单数据线项目
- 只有一种登录态（Session 或 JWT）的项目
- 开发环境默认 SQLite 的项目（Docker 开发默认其实是 PostgreSQL + Redis）

### 修改前建议先定位：

1. 这是 Web、微信小程序，还是两端都要？
2. 涉及公共题库还是个人题库？
3. 现有能力是页面模板、静态 JS，还是小程序页面？
4. 是否已有同名 API 或同语义 API 可以复用？
5. 是否会影响收藏 / 错题 / 标签 / 进度 / 考试等共享语义？

## 13. AI 查找路径建议（减少乱猜）

### 如果要改 Web 页面

- 先找 `app/modules/*/routes/pages*.py`
- 再找对应 `app/modules/*/templates/**`
- 最后找 `static/js/*` 和 `static/css/*`

### 如果要改小程序页面

- 先看 `miniprogram-1/miniprogram/app.json` 确认页面与分包
- 再看页面目录中的 `.ts/.wxml/.less/.json`
- 再看 `utils/api-endpoints.ts`、`utils/api-client.ts`

### 如果要改接口

- 先确认模块归属：`quiz` / `exam` / `user_bank` / `user` / `auth` / `main`
- 再确认响应格式是否需兼容已有客户端
- 再确认 Web 与小程序是否共用该接口

### 如果要改题库详情相关能力

- 先确认入口：题库广场还是个人题库
- 再确认是公共题库详情还是个人题库详情
- 再确认收藏 / 错题 / 标签 / 统计 / 考试是否都需要同步语义

## 14. 对 AI 最实用的落地规则

- 新功能优先复用已有模块与路由，不先发明新架构。
- 新接口优先复用统一响应信封，不随意返回裸数据。
- 小程序请求优先走 `api-endpoints.ts`，不要在页面散写 `wx.request`。
- Web 页面优先接入 `app_shell.html` 的主题与布局体系。
- 涉及题库、练习、考试、统计时，优先检查 Web 与小程序是否都存在同语义能力。
- 涉及账号、写接口、安全头时，优先检查 Session / JWT / CSRF 三者的兼容关系。
- 需要运行与联调时，优先使用 Docker 开发模式，而不是自行假设本地直接启动流程。

## 15. 一句话记忆版

这是一个 **Flask 单仓库全栈题库系统**：Web 是 **Jinja SSR**，小程序是 **微信原生 TS**，两端共用后端与数据语义，开发默认走 **Docker + PostgreSQL + Redis**，做改动前先分清 **公共题库 vs 个人题库**、**Web vs 小程序**、**Session vs JWT**。
