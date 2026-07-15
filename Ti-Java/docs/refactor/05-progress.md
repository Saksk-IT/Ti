# Ti-Java 重构进度

> 本文件是跨轮次、跨夜恢复工作的唯一进度入口。继续执行前，先核对本文件、当前 Git 状态和受保护工作区清单；事实以仓库当前内容和可复现验证结果为准。

## 当前阶段

- **阶段 2：Java 基础骨架（进行中）**。
- 基线提交：旧 Ti `700006dfdfa063deb4387be572911e782bcea0d9`。
- 盘点日期：2026-07-16（Asia/Shanghai）。
- 最近通过的提交：`627bfa096186ff400f916c6b7b0bef246ed0bb7e`（`docs(refactor): freeze architecture contracts`）。
- 阶段 0 与阶段 1 均已通过结构化门禁、负向测试和独立审计；当前从该绿色检查点进入阶段 2。
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

## 阶段 1 已完成

- 接受 10 份正式 ADR，固定 Java/Spring 版本、模块化单体、Spring MVC、数据库单写者、认证过渡、OpenAPI、Vue 迁移、Python 保留边界、可靠事件和模块 DAG。
- 从冻结路由矩阵确定性生成 OpenAPI 3.1.2 初稿：592 条规则、611 个旧方法映射为 610 个目标 operation 与 1 个显式 `/profile` 遮蔽来源；每个 operation 均有旧来源、目标接口、模块、认证、迁移状态和成熟度。
- 7 个黄金 operation 标为 `observed`，603 个仍为 `inferred`；未知响应显式使用 `LegacyOpaquePayload`，不得据此伪称路由迁移完成。
- 固定目标 `/api/v1` 的 success/error/meta 信封、分页、时间、十进制精度、null/缺失、枚举、安全和幂等策略，同时保留旧兼容 operation 的实际信封与路径语义。
- 建立 11 个业务模块与 Web 适配边界的机器合同：`io.saksk.ti` 根包、154/154 资源唯一归属、70 张物理表恰有一个 owner、跨模块只保存 ID、无共享 JPA Entity，允许依赖图无环。
- 固定账号锁定、题库权限、答题幂等、单次交卷、十进制评分和教务快照去重 6 项关键不变量；区分新 v1 精度决定与仍待逐字段取证的旧兼容精度。
- 固定无副作用只读对比、同源隔离写对比、最终停写、整套入口切换及写前/写后回滚；禁止双写、逐路由/比例拆流和 shadow write，写后优先前向修复或第三套库反向迁移。
- 增加阶段 1 聚合门禁，串联 ADR/互链、OpenAPI 确定性、覆盖、所有权、DAG、不变量、回滚语义、可移植性/敏感信息扫描和 23 项正反向测试。

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
| `python3 Ti-Java/tools/validate_phase1_openapi.py` | 592 rules / 611 legacy methods / 610 rendered + 1 shadow | 绿色；逐字节重生成、引用、安全、成熟度和目标接口闭环 |
| `python3 Ti-Java/tools/validate_phase1_boundaries.py` | 11 业务模块 + 1 Web；70 表 + 84 非表资源；6 不变量 | 绿色；唯一所有权、无环 DAG、无共享 Entity 与回滚协议通过 |
| `python3 Ti-Java/tools/validate_phase1.py` | 23 项测试通过 | 绿色；10 ADR + OpenAPI + 边界 + 文档/可移植性聚合门禁 |
| `npx --yes @redocly/cli@2.39.0 lint ... --extends=minimal` | OpenAPI valid，0 error，48 warnings | 绿色；30 组旧路径歧义、4 个尾斜杠和 14 个预声明组件均已结构化解释 |

完整命令、两个 pytest 失败说明及初步性能数字见 `07-baseline-results.md`。

## 尚未迁移的路由与数据

- **路由：** 592/592 仍属于旧 Flask 运行时；阶段 0 仅完成盘点，没有任何路由迁入 Java。矩阵中的迁移状态应保持 `pending`，直到对应兼容契约和实现通过验证。
- **表：** 69/69 应用表仍由旧项目拥有；阶段 0 只分配初始目标模块，没有切换运行时写所有权，也没有建立 Flyway 正式 baseline。
- **客户端：** Web 仍是 Jinja/原生 JavaScript，小程序当前只是固定来源副本；Vue、OpenAPI 生成客户端和适配尚未开始。
- **部署：** Java 服务、独立 PostgreSQL/Redis、网关和新项目 Compose 尚未建立；不得让 Flask 与未来 Java 实例同时写同一数据库。

## 已知风险与未收口项

- `GET /profile` 存在两个已注册 Endpoint，真实路由顺序由 `main.main_pages.profile_page` 遮蔽 `user.user_pages.profile`；迁移时必须保留当前匹配行为。
- OpenAPI 初稿仍有 603 个 `inferred` operation；它们只闭环来源与目标接口，阶段 3/4 必须按真实请求、测试、下载/SSE/multipart 和数据库后置条件逐批提升成熟度。
- OpenAPI 的 30 组潜在路径歧义来自必须兼容的旧静态/动态模板组合；Java Controller 映射时必须用契约测试证明与 Flask/Werkzeug 匹配优先级一致，不能依赖生成工具排序。
- 匿名小程序忘记密码的两个写接口在旧基线中被全局 CSRF/匿名白名单拒绝为 403；这是需固化或纠正的产品语义，不能静默改变。
- SQLAlchemy 标准 metadata 与完整模型定义、Alembic 迁移和物理 PostgreSQL 之间存在覆盖差异；正式所有权矩阵须以完整模型导入和迁移事实校验。
- Redis/RQ/SSE 等资源存在命名与运行配置漂移；尤其聊天音频任务使用默认 RQ 队列，而当前 Worker 监听 `saksk`。ADR-0009 已固定 PostgreSQL 可靠发布目标，阶段 5 仍须逐任务实现并证明存量处置未知数为零。
- 黄金样本除真实答题写入外，大多来自最小/空测试数据集，只能固定基础响应与空值语义；不能替代脱敏非空快照、权限矩阵、错误路径、分页边界与幂等验证。
- 黄金样本捕获器已删除 `request_id`、`trace_id`、`correlation_id` 等动态标识；日期窗口等稳定结构中的运行日期仍需由后续对比器按 `08-golden-samples.md` 明确归一化。
- 小程序旧树 392/受控副本 386 个既有 TypeScript 错误仍会降低后续回归信噪比；当前已用结构化多重集门禁锁定，后续禁止跳过或放宽检查掩盖新增错误。
- 当前机器没有 JDK/Maven；阶段 2 应使用固定 JDK 25 环境与 Maven Wrapper，不依赖全局 Maven。
- 正式性能基线尚未完成独立数据、独立 Redis、SQL 数、启动耗时和页面指标采集；当前小样本不可作为验收门槛。
- `page/partial` 与动态模板映射是明确标注的迁移启发式，不能在阶段 6 直接当作分支级精确契约；须结合真实请求与页面测试收口。

## 下一项具体动作

1. 创建 `Ti-Java/server/`、Maven Wrapper、Java 25/Spring Boot 4.1.0/Modulith 2.1.0 固定依赖和可重复构建入口。
2. 建立 Spring MVC 应用、分层配置、Request ID、结构化日志/脱敏、统一安全错误、健康检查、Actuator readiness/liveness 与 Micrometer。
3. 把 `module-contracts.json` 落实为 package、`@ApplicationModule(allowedDependencies=...)`、Named Interface、公开 API 占位合同和 Modulith/ArchUnit 负向架构测试。
4. 建立 PostgreSQL/Redis Testcontainers 与测试 Profile，使用 `ddl-auto=validate` 映射最小旧结构只读实体；不得提前创建正式 Flyway baseline。
5. 增加 Java Dockerfile 和独立 `compose.dev.yml`，验证不同端口、容器名和卷启动，不修改旧 Flask 入口或共享可写数据设施。
