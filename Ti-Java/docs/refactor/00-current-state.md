# 旧 Ti 事实基线

## 1. 快照与边界

- 盘点日期：2026-07-16（Asia/Shanghai）。
- 根仓库基线提交：`700006dfdfa063deb4387be572911e782bcea0d9`。
- 根分支：`main`，开始时与 `origin/main` 一致。
- 本文只描述旧项目事实；旧 `app/`、`templates/`、`static/`、`miniprogram-1/`、`migrations/` 和根部署文件不由本重构修改。
- 未连接生产环境、未读取真实密钥；黄金样本使用临时 SQLite，运行观察只访问本机 `127.0.0.1` 上的既有开发容器。

任务开始前必须保护的根工作区：

```text
 M AGENTS.md
 D CLAUDE.md
?? .playwright-cli/
?? miniprogram-1/.gitignore
?? output/
```

`miniprogram-1/` 还是一个嵌套 Git 仓库。其 HEAD 为 `0717f0a4c5c1fa699f760bb05d5a9e8d88051596`，内部另有 12 个修改文件；根仓库状态不能展示这组差异。完整禁触碰说明见 `06-protected-worktree.md`。

## 2. 旧系统结构

旧系统是 Flask 应用工厂 + Blueprint 模块、Jinja/原生 JavaScript Web、微信原生 TypeScript 小程序的单仓系统：

```text
Web / Mini Program
        |
Flask + Session/JWT + CSRF/CORS/rate limit
        |
PostgreSQL ---- Redis cache/RQ/SSE coordination
        |                 |
backup sidecar        RQ worker
```

`app/modules/__init__.py` 实际注册 13 个业务模块：`auth`、`main`、`quiz`、`exam`、`user`、`ai_chat`、`chat`、`notifications`、`coding`、`user_bank`、`forum`、`edu_schedule`、`admin`，另注册 SSE Blueprint。README 中的“12 个模块”已过时。`popups` 有实现但未注册；`payment` 当前主要由后台设置服务调用。

旧 `app/` 共有 309 个 HTML 模板，其中 304 个位于业务模块下（包含大量 partial）；源码有 104 处 Flask `render_template` 调用（101 字面量 + 3 动态表达式），运行时有 91 条路由直接映射字面量模板、12 条路由映射静态候选模板，未解析模板字面量为 0。客户端清单还固定了 61 个 app.json 声明页面（50 主包 + 11 分包）、7 套完整但未声明的小程序页源码、181 个后台运行时入口（30 Web + 151 API）、7 个未注册后台 popup 声明和 14 条关键旅程。完整证据见 `09-surface-inventory.json`。

## 3. 路由事实

- 动态 `app.url_map`：592 条 URL 规则，其中 591 条应用规则、1 条 Flask 静态规则。
- 展开 HTTP 方法后：611 个 `path + method` 组合。
- 静态源码：538 个 `route()` 装饰器定义；其中 10 个 popup 定义未注册。
- 覆盖闭环：528 个已注册装饰器 + 54 个个人题库双前缀别名 + 9 个 quiz `add_url_rule` 别名 + 1 个 Flask static = 592。
- 唯一相同 `path + method` 冲突：`GET /profile`。`main.main_pages.profile_page` 先注册并遮蔽 `user.user_pages.profile`；兼容迁移必须按真实匹配顺序处理。
- 小程序源码可解析出 116 次请求表达式、113 个唯一 `path + method`；其中 102 条注册 URL 规则带有小程序调用证据，全部 113 个调用签名均能映射到当前 URL map（同一规则可承载多方法或被多处调用）。
- 旧基线异常：匿名访问 `/api/mini/forgot-password/send-code` 与 `/api/mini/forgot-password/reset` 会被全局 CSRF/匿名白名单拒绝为 403；阶段 0 只记录，不修改旧实现。

完整矩阵在 `02-route-parity-matrix.csv`。每一行都保留路径、方法、Endpoint、注册来源/方式、源码、路由装饰器、函数内认证信号、全局门禁与 CSRF 语义、按方法识别的静态调用证据、目标模块和迁移状态。真实执行层级为“全局写请求 CSRF → 全局匿名/Session/JWT 门禁 → Admin Blueprint 钩子 → 路由装饰器 → Handler 内联检查”；无认证装饰器统一记为 `route_auth:none`，它不等于公开接口。`inline_auth_signals` 只是 AST 静态证据，最终契约仍由前述执行链与运行测试共同确认。静态调用扫描没有证据时显式标记，不静默推断。

未注册的 10 个 popup 装饰器不进入 592 条运行时矩阵，但作为代码漂移明确保留：`GET/POST /admin/api/popups`、`GET/PUT/DELETE /admin/api/popups/<int:pid>`、`GET /admin/api/popups/stats`、`GET /admin/api/popups/<int:pid>/stats`，以及 `GET /api/popups/active`、`POST /api/popups/<int:popup_id>/dismiss`、`POST /api/popups/<int:popup_id>/view`。前 7 个因聚合器未导入 `api_components/popups.py`，后 3 个因 `init_popups_module()` 未被应用模块注册器调用。`phase0-inventory-summary.json` 保存这 10 个装饰器的源码行、相对路径和方法，门禁同时断言 `538 = 528 + 10` 以及 `592 = 528 + 54 + 9 + 1` 的闭环。

## 4. 数据事实

- 只执行 `import app.models` 时，SQLAlchemy 元数据注册 67 张表；导入全部 `app/models/*.py` 后注册 69 张。
- `user_follows`、`interaction_notifications` 均在 `app/models/follow.py` 有 ORM 定义，但未由 `app/models/__init__.py` 导入；它们不是“仅迁移维护”的表。
- 本机迁移后 PostgreSQL 的 `public` schema 有 70 张物理表、617 个物理列：69 张应用表为 616 列（完整 ORM 元数据 615 列，再加迁移创建的 `forum_posts.search_vector` generated column），`alembic_version` 另有 1 列。
- Alembic：单一 base `3a7dbef5d592`、单一 head `f5b6c7d8e9f0`，共 22 个 revision。
- 迁移定义的 59 个显式索引在本机开发库均存在；`forum_posts.search_vector` 是 ORM 未声明的 PostgreSQL generated column，并有 GIN `ix_forum_posts_search`。
- PostgreSQL 是业务事实源；SQLite 只用于旧测试。
- 模型、服务和原生 SQL 并存；完整模型导入、Alembic 与物理结构之间仍有约束名、生成列和索引漂移。代码还读取不存在的 `forum_notifications` 表，需在契约固化阶段决定正确语义。

`03-data-ownership.csv` 为 70 张物理表（含 Alembic 控制表）及 84 类数据库 KV、Redis、队列任务、SSE、后台任务、文件前缀和第三方接口指定唯一初始目标所有者，并记录旧 owner、具体源码、外键、唯一约束和索引线索。合计 154 个资源条目；阶段 1 会通过 ADR 校正边界，但不得出现无所有者资源。

关键非表资源：

- PostgreSQL KV：15 类扫码登录/绑定会话、短期 token、跨端设置、个人题库查重和学习进度均实际存于 `user_progress`；4 类扫码/绑定协调项挂在固定 `KV_OWNER_USER_ID`（默认 1）而非业务用户下，部分短期项仅在读取时判断 JSON `expires_at`，未发现统一定时清理。
- Redis：12 类响应缓存、5 类版本 Key、聊天未读 Hash、AI 结果/作业、短信/邮件失败遥测、教务查询协调、限流和 RQ 元数据；全部使用 DB 0 且部署采用 `allkeys-lru`，不能成为最终事实源。
- RQ：Compose Worker 只监听 `saksk`（AI 解析、邮件、短信）；聊天音频转码直接进入 `default`，当前无人消费，是已知旧风险。
- SSE：通用 `sse:events` 包含 7 类业务事件；AI 对话另有 `meta/delta/done/error` 直连流。生产默认可禁用，持久消息/通知仍在 PostgreSQL。
- 文件：头像、公共/个人题库题图、题库封面、论坛、聊天、扫码二维码、备份归档及可选 R2/S3 前缀；扫码二维码未发现实际 TTL 文件清理。
- 外部：微信、OpenAI 兼容模型接口、SMTP、阿里云短信、学校 WebVPN/JWXT、Epay 兼容网关、R2/S3，以及在用户浏览器中使用学习站点 Cookie 的 Chaoxing/PTA/Yuketang 导出扩展。

## 5. 运行与部署事实

| 入口 | 当前事实 |
| --- | --- |
| 宿主机开发 | `.venv/bin/python run.py`，默认 `0.0.0.0:5000` |
| Docker 开发 | `compose.dev.yml`：web、worker、postgres、redis、backup |
| Docker 生产 | `compose.prod.yml`：nginx、web、worker、postgres、redis、backup |
| Web 生产进程 | Gunicorn，默认 2 workers × 4 threads |
| 健康接口 | `/api/ping` 与 `/api/ping?deep=1` |
| 当前本机旧实例 | Web `127.0.0.1:18000`，PostgreSQL `127.0.0.1:15432` |

文档/运行漂移：

- README 引用的 `docs/DEVELOPMENT.md` 不存在；`run.py` 引用的 `docs/systemd/README.md` 不存在。
- README 记录小程序 58 页；当前 `app.json` 为 50 个主包页、6 个分包、11 个分包页，共 61 个声明页面。
- Dockerfile 默认 Python 3.11，当前旧 Web 容器为 Python 3.12.13；当前镜像额外含 `fastapi/sqlmodel` 并与固定的 Pydantic 2.5.0 产生 `pip check` 冲突。
- 当前 `web` 和 `backup` 容器的 Compose config hash 与仓库配置不一致；`backup` 仍运行旧 cron 形态。
- 开发 Compose 缺少 Web/Redis 健康检查；生产 Web 只有 TCP 探针。
- 生产 Compose 使用本机现有 `.env.production` 校验时因缺少 `BACKUP_CREDENTIAL_SECRET` 失败；未读取该文件内容或任何密钥。

## 6. 工具链事实与稳定版本核验

- macOS arm64；Node 26.0.0；pnpm 11.7.0；系统 Python 3.9.6；项目 `.venv` Python 3.11.15。
- 本机没有 Java Runtime 和 Maven。阶段 2 应使用 JDK 25 容器或安装 Temurin 25，并以 Maven Wrapper 固定 Maven。
- 官方稳定版本核验：Spring Boot `4.1.0`、Spring Modulith `2.1.0`、Java 25 LTS。Spring Boot 4.1.0 官方声明兼容 Java 17 至 26。
- 参考：<https://spring.io/projects/spring-boot/>、<https://docs.spring.io/spring-boot/system-requirements.html>、<https://docs.spring.io/spring-modulith/reference/index.html>、<https://openjdk.org/projects/jdk/25/spec>。

## 7. 基线验证

| 验证 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q`（临时 `DATA_DIR`） | 659 收集；654 passed、2 failed、3 skipped；三次隔离执行观察到 364–366 warnings，首次 70.33s |
| `python3 -m compileall -q app tests` | 通过 |
| `node --test miniprogram-1/tests/*.test.js` | 36/36 通过 |
| `scripts/check_miniprogram_runtime_deps.js` | 通过 |
| 小程序 `tsc --noEmit` | 既有失败，共 392 个错误 |
| 开发 Compose `config --quiet` | 通过 |
| 生产 Compose `config --quiet` | 缺少必需环境变量，未通过 |
| 本机旧实例浅/深健康 | 均为 HTTP 200，深检查 `db=true`、`redis=true` |

两个 Python 既有失败：

1. `test_production_policy_expands_decorator_and_manual_limits`：完整套件中 session 级 Flask 测试 app context 仍处于 testing，覆盖了测试手工配置的生产策略，表现为顺序/上下文耦合；单独执行路径需另行区分。
2. `test_export_pdf_returns_pdf_download`：macOS 缺少 WeasyPrint 所需 `libpango-1.0-0`，接口返回 500；容器镜像包含相关系统库。

旧小程序 392 个类型错误主要涉及实例私有字段未声明、ES2017 缺少 `Promise.finally`、隐式 `any`、未使用符号、ECharts 非模块与类型声明漂移。受控 `Ti-Java/miniprogram` 副本为 386 个；两者的活跃源码错误多重集合完全一致，恰少的 6 个均是已排除 `_archived/` 下的 `TS2393` 重复实现错误，不能把其余既有错误归因于 Ti-Java。

## 8. 初始性能观察

这些数字来自运行约三天、缓存已热且配置漂移的本机旧开发容器，只用于定位，不是阶段 9 的正式 p95：

| 观察项 | 单次/小样本结果 |
| --- | --- |
| `/api/ping` | 中位约 4.59 ms；12 样本 p95 约 5.16 ms |
| `/api/ping?deep=1` | 中位约 6.90 ms；12 样本 p95 约 9.50 ms |
| `/api/public/banks` | 单次暖态约 128.3 ms |
| `/api/questions/count` | 单次暖态约 25.8 ms |
| 旧 Web 容器空闲内存 | 约 262.5 MiB |
| Worker / PostgreSQL / Redis | 约 12.6 / 42.1 / 10.9 MiB |

对 `/` 和 `/public/banks` 的 12 次连续 GET 触发了旧限流的 429，说明正式性能基线必须使用独立数据库、Redis、端口与卷，并记录缓存冷暖、数据规模、并发、SQL 数和资源限制。

另以临时 SQLite、空夹具、后台线程关闭的测试 Profile 测得一次隔离启动与 SQL 方向性样本：旧模块导入加 `create_app()` 约 875.873 ms，进程 RSS 从约 18.562 MiB 增至 163.391 MiB；5 次暖态样本中，`/api/public/banks/summary` 每次 7 条 SQL、`/api/questions/count` 1 条、`/hub` 2 条、`/api/ping` 0 条，全部 HTTP 200。完整环境和限制见 `legacy-performance-sample.json`；空 SQLite 结果不能代表 PostgreSQL 查询计划、真实数据规模或阶段 9 性能门槛。

## 9. 关键旅程

阶段 0 将真实入口归并为 14 条关键旅程：登录认证、首页与公共题目目录、练习与答题记录、学习数据与趋势、考试、个人题库、题库广场、论坛社区、站内聊天、校园课表与成绩、编程练习、通知中心、设置与个人资料、管理后台。每条都在 `09-surface-inventory.json` 中关联实际 Web/API 路由，可用时再关联小程序页。

后续黄金契约和 E2E 还须细化登录与账号绑定、公共题库浏览/加入、个人题库 CRUD/导入导出、练习/收藏/错题/统计、考试/评分、论坛/聊天/通知、教务课表与成绩、编程题、AI 对话/解析、后台用户/题目/权限/配置/备份。

阶段 0 已保存 identity、catalog、learning、assessment、community、campus、operations 七组脱敏 200 响应，见 `golden-samples/manifest.json`。
