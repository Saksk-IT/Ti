# Ti-Java 重构进度

> 本文件是跨轮次、跨夜恢复工作的唯一进度入口。继续执行前，先核对本文件、当前 Git 状态和受保护工作区清单；事实以仓库当前内容和可复现验证结果为准。

## 当前阶段

- **阶段 1：架构决策与契约固化（进行中）**。
- 基线提交：旧 Ti `700006dfdfa063deb4387be572911e782bcea0d9`。
- 盘点日期：2026-07-16（Asia/Shanghai）。
- 最近通过的提交：`20f926bd4218826bff3a6a44db8f117c3d025d84`（`docs(refactor): inventory legacy contracts`）。
- 阶段 0 已通过结构化门禁、全量基线和独立只读审计；当前从该绿色检查点进入阶段 1。
- 旧项目目录只读；当前实施范围仅为 `Ti-Java/`，未连接生产环境、未读取真实密钥、未切换部署或 DNS。

## 本轮已完成

- 建立独立 `Ti-Java/` 边界、补充工程规则和 README。
- 从根仓库固定提交创建受控小程序副本，排除嵌套 `.git`、依赖目录、缓存、日志和本地配置，并保存 SHA-256 来源清单。
- 生成旧系统事实盘点：动态 URL map 592 条规则、展开后 611 个 `path + method` 组合；小程序 116 次请求表达式、113 个唯一接口均可映射到旧 URL map，其中 102 条注册规则具有小程序调用证据。
- 盘点 69 张应用表；本地迁移后 PostgreSQL 的 `public` schema 为 70 张物理表，其中 1 张是 `alembic_version`。
- 记录 84 类 PostgreSQL KV、Redis、队列、SSE、文件、定时任务及第三方接口等非表资源的旧 owner、具体来源与初始目标所有权；连同 70 张表共 154 个资源。
- 记录 309 个 HTML 模板、61 个 app.json 声明小程序页面、7 套未声明完整页源码、181 个后台运行时入口、7 个未注册后台 popup 声明和 14 条关键旅程；证据来自固定旧提交与 `Ti-Java/miniprogram` 受控副本。
- 在临时 SQLite 与测试身份下保存 7 组脱敏黄金请求/响应，覆盖身份、题库、学习、考试、社区、教务和后台；学习域通过固定题目执行真实 `POST /api/record_result` 并验证 `user_answers` 写入及错题不变量，7 组均为 HTTP 200。
- 完成旧实例的初步响应时间与内存观察；该结果仅用于定位，尚不是阶段 9 的正式性能基线。
- 在临时 SQLite 上补充应用导入/创建、RSS 和核心请求 SQL 次数样本：公共题库摘要 7 条、题目计数 1 条、`/hub` 2 条、浅健康 0 条；全部 5/5 为 HTTP 200。
- 建立旧工作区与嵌套小程序仓库的禁触碰清单。
- 建立可重复的阶段 0 强门禁：路由、数据、页面入口、源码副本、黄金样本和性能证据均结构化校验，且在临时目录重生成后逐字节比对。

## 验证命令与结果

| 验证 | 结果 | 判定 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q -p no:cacheprovider`（临时 `DATA_DIR`、内存限流存储） | 659 收集；`654 passed, 2 failed, 3 skipped`；三次隔离执行观察到 364–366 warnings | 两个既有失败，已记录复现与归因 |
| `.venv/bin/python -m compileall -q app tests`（临时 pycache） | 通过 | 绿色 |
| `node --test miniprogram-1/tests/*.test.js` | 36/36 通过 | 绿色 |
| `node --test Ti-Java/miniprogram/tests/*.test.js` | 36/36 通过 | 绿色；新项目副本可独立读取自身源码 |
| `node scripts/check_miniprogram_runtime_deps.js` | 通过 | 绿色 |
| 小程序 `tsc --noEmit --pretty false` | 退出码 2；392 个既有类型错误 | 既有失败，不能作为 Ti-Java 新回归 |
| 受控副本 `tsc --noEmit --pretty false` | 退出码 2；386 个既有类型错误 | 与旧树活跃源码错误逐条一致；仅少 6 个被排除的归档 `TS2393` |
| `docker compose --env-file .env -f compose.dev.yml config --quiet` | 通过 | 绿色 |
| `docker compose --env-file .env.production -f compose.prod.yml config --quiet` | 缺少必需变量 `BACKUP_CREDENTIAL_SECRET` | 本机配置前置条件未满足；未读取真实配置 |
| 本机旧实例 `/api/ping` 与 `/api/ping?deep=1` | 均为 HTTP 200，深检查 `db=true`、`redis=true` | 绿色，仅代表当前开发实例 |
| 黄金样本捕获 | 7/7 为 HTTP 200，真实答题写入后置条件通过，`manifest.json` 为 `all_success=true` | 绿色，使用临时 SQLite |
| `measure_legacy_baseline.py --samples 5` | 4 个入口全部 5/5 HTTP 200；记录启动 RSS/耗时和 SQL 次数 | 绿色，空 SQLite 仅作方向性基线 |
| `.venv/bin/python -m pytest -q -p no:cacheprovider Ti-Java/tools/test_inventory_legacy.py` | 4/4 通过 | 绿色；路由证据扫描回归 |
| `verify_legacy_test_baseline.py --legacy-root .` | 659 收集；654 passed、2 个允许失败、3 skipped、0 errors、364 warnings | 绿色；计数、失败 nodeid 与 364–366 警告窗口均匹配 |
| `verify_miniprogram_type_baseline.py --legacy-root .` | 旧树 392、受控副本 386；活跃错误多重集一致 | 绿色；差异仅 6 个已排除归档 `TS2393` |
| `TI_BACKUP_SCHEDULER=1 inventory_surfaces.py ...`（连续两次） | 与已保存 `09-surface-inventory.json` 逐字节一致 | 绿色；不受调用者 sidecar 环境污染 |
| `validate_phase0.py --legacy-root .` | 13/13 通过 | 绿色；确定性重生成与跨矩阵闭环 |
| `validate_phase0.py --legacy-root . --legacy-python .venv/bin/python` | 13/13 通过 | 绿色；显式虚拟环境解释器未被符号链接解引失真 |

完整命令、两个 pytest 失败说明及初步性能数字见 `07-baseline-results.md`。

## 尚未迁移的路由与数据

- **路由：** 592/592 仍属于旧 Flask 运行时；阶段 0 仅完成盘点，没有任何路由迁入 Java。矩阵中的迁移状态应保持 `pending`，直到对应兼容契约和实现通过验证。
- **表：** 69/69 应用表仍由旧项目拥有；阶段 0 只分配初始目标模块，没有切换运行时写所有权，也没有建立 Flyway 正式 baseline。
- **客户端：** Web 仍是 Jinja/原生 JavaScript，小程序当前只是固定来源副本；Vue、OpenAPI 生成客户端和适配尚未开始。
- **部署：** Java 服务、独立 PostgreSQL/Redis、网关和新项目 Compose 尚未建立；不得让 Flask 与未来 Java 实例同时写同一数据库。

## 已知风险与未收口项

- `GET /profile` 存在两个已注册 Endpoint，真实路由顺序由 `main.main_pages.profile_page` 遮蔽 `user.user_pages.profile`；迁移时必须保留当前匹配行为。
- 匿名小程序忘记密码的两个写接口在旧基线中被全局 CSRF/匿名白名单拒绝为 403；这是需固化或纠正的产品语义，不能静默改变。
- SQLAlchemy 标准 metadata 与完整模型定义、Alembic 迁移和物理 PostgreSQL 之间存在覆盖差异；正式所有权矩阵须以完整模型导入和迁移事实校验。
- Redis/RQ/SSE 等资源存在命名与运行配置漂移；尤其聊天音频任务使用默认 RQ 队列，而当前 Worker 监听 `saksk`，需要在阶段 1 明确可靠异步边界。
- 黄金样本除真实答题写入外，大多来自最小/空测试数据集，只能固定基础响应与空值语义；不能替代脱敏非空快照、权限矩阵、错误路径、分页边界与幂等验证。
- 黄金样本捕获器已删除 `request_id`、`trace_id`、`correlation_id` 等动态标识；日期窗口等稳定结构中的运行日期仍需由后续对比器按 `08-golden-samples.md` 明确归一化。
- 小程序旧树 392/受控副本 386 个既有 TypeScript 错误仍会降低后续回归信噪比；当前已用结构化多重集门禁锁定，后续禁止跳过或放宽检查掩盖新增错误。
- 当前机器没有 JDK/Maven；阶段 2 应使用固定 JDK 25 环境与 Maven Wrapper，不依赖全局 Maven。
- 正式性能基线尚未完成独立数据、独立 Redis、SQL 数、启动耗时和页面指标采集；当前小样本不可作为验收门槛。
- `page/partial` 与动态模板映射是明确标注的迁移启发式，不能在阶段 6 直接当作分支级精确契约；须结合真实请求与页面测试收口。

## 下一项具体动作

1. 完成语言与版本、模块化单体、Spring MVC、数据库共存、认证过渡、前端迁移和 Python 保留边界 7 类 ADR，并建立可检索索引。
2. 从 592 条真实路由生成 OpenAPI 3.1 初稿，固定状态码、信封、分页、时间、精度、空值、枚举与认证契约，并用自动门禁与路由矩阵交叉校验。
3. 为 11 个目标业务模块及 Web 适配边界定义公开应用 API、内部实现、表所有权和允许依赖，生成并验证无环 DAG。
4. 固定重复交卷、答案幂等、题库权限、考试评分、账号锁定和教务快照去重等关键不变量，收口只读/隔离写对比、停写切换和回滚协议。
