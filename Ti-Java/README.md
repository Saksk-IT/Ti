# Ti-Java

Ti-Java 是 Ti 的独立重构项目，目标是以 Java 25、Spring Boot 4.1、Spring MVC 和 Spring Modulith 重新实现现有业务，并逐步加入 Vue 3 + TypeScript Web 与项目自有的小程序。

阶段 0 事实基线与阶段 1 架构/契约已经固化，阶段 2 Java 基础骨架与阶段 3 认证兼容切片也已通过门禁；阶段 4A 的有界 catalog 范围已由 `docs/refactor/phase4a/phase4a-final-acceptance.json` 完成最终 closure。Phase 4B 已完成 personal-bank 分类、按题库分享列表、我创建的全部分享和使用人数统计四项 HTTP-neutral 内部读取能力；user-counts 双 alias 的调用方、59-case golden、八个 SQL family 与 PostgreSQL 16.14/18.4 实现前证据也已闭合，但所有八条 personalbank HTTP operation 都保持 pending。Phase 4C 已实现 `learning -> personalbank::api` 的 user-counts HTTP-neutral 组合和 personalbank 题目事实边界，累计生产 shape 为 27 个公开应用方法；跨题库分享授权、逐次鉴权、typed `integer[]`、独立只读事务及字段级失败边界由第二层固定合同约束。`bank_<bank_id>_tags` 所有权 overlay 与逐行迁移原语仍只属于证据层，完整迁移设计因全局 preflight、持久 migration ledger/tombstone 与真实 ambiguous-commit 恢复未闭合而保持未授权。user-counts HTTP 候选实现已物化：双 alias Controller、安全错误 writer、Unicode `Nd` 路径解析、GET/派生 HEAD、API-only CORS/OPTIONS、按有效 actor HMAC 假名的 Redis 三窗口限流，以及配置、OpenAPI overlay 和两行 pending route delta 均已存在。typed-normalization successor 已在同一绿色 leaf 中用 Java `String` bind 证明 PostgreSQL 16.14/18.4 及 UTC/America-Los_Angeles Session 时区均按 `timestamp without time zone` 规范化为 13:00 墙钟；PG18.4 完整过滤链 HTTP 使用请求追踪前由该 bind 创建的 share 行并返回 200。malformed expiry 继续是 SQLSTATE `22007` 的唯一域外 typed rejection。有效 59-case 账本现为 47 个普通完整上下文 HTTP、11 个真实 PostgreSQL abort HTTP 和 1 个 typed rejection，即 58 HTTP + 1 typed；其中 50 个 HTTP 到达业务 JDBC、8 个在认证边界提前终止。历史 60 leaves 加新增 1 leaf 物理合计 61，但旧 aware leaf 被显式替换，逻辑证明仍为 59 disposition + 1 supplementary leaf，不双计数。固定外锚已从提交 `b0861d61438f649ed48d5d5e6806e02c804fa2e4` 锚定 typed-normalization bootstrap。INT 又审查并集成 PG、TOMCAT、REDIS 三条独立 Worker 证据：双 PostgreSQL 关键终止 identity/SQL/九表指纹、无 application/auth/session/limiter mock 的真实 Tomcat GET/HEAD 完整响应头矩阵，以及同一服务 Redis 拒绝、中断、同端口恢复、限流复原和双实例收敛均已闭合；定向 Failsafe 13/13 与完整 `clean verify` 709+167 均为零失败/错误/跳过。因此 `pg16_pg18_termination_fingerprints_complete=true`、`real_tomcat_complete_response_header_matrix_complete=true`、`same_service_redis_outage_and_recovery_complete=true`、`full_target_parity_closed=true`。当前 full-parity bootstrap 的六个控制源仍自排除且等待固定 Git 外锚，所以 `route_migration_eligible=false`，两条 GET 继续 pending，有效状态保持 **11 个 migrated operation、600 个 pending、0 个 production cutover**。旧 Flask 仍是生产运行所有者，整个长期重构目标尚未完成。

历史 HTTP-neutral read predecessor 固定 40 个 `learning`/`personalbank` 主源码与 288 文件生产面；第二层历史合同 77/77、全部 source tools 442/442、完整 Maven 545 个 surefire + 79 个 failsafe 均为零失败。该历史时点的追加式 WORM tip 绑定 Java build-context `935e6a95a33621b01e1e04d752a09513c8037cffe807a73fa1ce9850fb5912f0`，在 PostgreSQL 18.4 的 70 表/617 列恢复副本上通过只读 ACL、Hibernate `validate` 和 readiness；前三份报告保持字节不可变。该 read predecessor 的物理 SHA-256 固定为 `458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73`，后续 HTTP 工作只能通过显式 successor 承接，禁止改写这份历史合同。上述 442/442、545+79 与 `935e6a95…12f0` 均是 predecessor 历史证据，不代表当前 HTTP successor 的最终验收结果。

Phase 4C user-counts 的历史 HTTP entry gate 已固定实现前边界：旧栈最终捕获 62 个双 alias case，其中包含 8 个 CORS/OPTIONS 运行时观察；case payload SHA-256 为 `f577ff99a7f04030fd5f4dae0f95610351d4fcfff92de7e9ca0c406516725dbf`，document payload SHA-256 为 `3e8f7c24548d979723d2601c11221b9e569de7b342e6c3c0d8daa25de74cdd2f`。独立限流证据固定三组窗口、alias scope、429 协商、key 选择和 Redis 拒绝共 7 组观察；旧基础预算是 `10/second;500/hour;5000/day`，但固定生产部署默认乘数为 100，即 `1000/second;50000/hour;500000/day`，且仍允许显式部署覆盖。批准差异 `P4C-LEARNING-007` 至 `P4C-LEARNING-012` 分别冻结凭据选择、`last_active` 零写入、限流、路由级 CORS/OPTIONS、路径整数和 HEAD 零体边界。

历史 entry gate 已由“implementation present、parity incomplete、routes pending”的后继检查点承接。该 implementation predecessor 覆盖 297 个 production runtime files；相对 288 文件 predecessor 精确新增 9 个、修改 6 个，并固定 44 个 source contract 路径。第五节点 WORM 报告 SHA-256 为 `7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39`，绑定 Java build-context `273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3`。首次独立验收在 Compose 运行阶段发现 `read_only` API 服务不支持 environment-backed secret，整轮已作废；改为 file-backed configtree 后，验收时冻结的 pre-documentation checkpoint 已从头重跑并通过。该冻结点的权威副本包含 1,449 个受控文件，源/副本清单 SHA-256 均为 `154013da39c75fb33c7b0c9d02f4e0f34038b259972d4a9a7f93a7ae47e90d63`，临时结构化报告 SHA-256 为 `2b3cd6e4ea34a501809b5083bad0b49db82dba0aea92b36a4328c5d2ac530f8d`；496/496 source tools、Phase 1 23/23、Phase 2、Phase 3 29/29、topology 60/60、小程序 36/36、独立数据面、专用空缓存 Maven 661+93、唯一镜像、3/3 Compose readiness 与重启恢复均绿色。9 个只读 bind 全部来自独立副本，其中 user-counts Secret 为文件型挂载；临时容器、网络、卷、镜像、缓存卷和端口均清理至 0 残留。该 manifest 与临时报告只描述验收冻结点，不是当前工作树的字节清单；验收后的证据措辞、固定 trust/contract 与 parity 测试更新由当前 source/contract 门禁另行约束，未重新冒充为一次完整独立验收。

生产 HTTP 适配代码、配置、OpenAPI 和历史 pending route delta 已存在；新的目标执行套件对 59 个 disposition 消除了 `BOUND_*` 与 mocked-result 回显，typed-normalization 又以双版本、双 Session 时区的 String CAST 证明 offset 擦除，并用真实 PG18.4/Redis 7.4.7、完整生产过滤链和真实 Flask→Target Session 链替换 aware case 的历史 typed-collapse 表示，使有效账本收敛为 58 HTTP + 1 typed rejection。aware HTTP fixture 明确由 Java String bind + 显式 CAST 创建，请求固定 HTTP 200 与 `total=9/favorites=0/mistakes=0`；malformed 继续只在 PostgreSQL typed 边界以 `22007` 拒绝。58 个 HTTP 中 50 个到达 Controller、应用层和业务 JDBC，8 个认证前置终止明确证明业务 JDBC 未触达；补充探针不计入 59 disposition。历史 MockMvc 缺口现由三条固定 Worker 实现对象追加闭合，INT 全量验证为 709 个 Surefire + 167 个 Failsafe，全部绿色。full-parity bootstrap 合同固定 BASE `765e4470f1ddb60f0ce6f23227d6303961f47fcf`、PG `0f584743dbdc187b6bc6fc67899a2d6718cb13c8`、TOMCAT `cd7eba9bbee4edcb6a0e14fec5fdfdf613d2ea70`、REDIS `ad4d90b30cc5d244983fe759199f77ddeacdfc52` 以及六个证据文件的字节；Worker handoff 只作审计输入，没有合入 main。四个 parity 前提均为 true，但当前 bootstrap 六源尚未被后继 Git 提交外锚，故 `route_migration_eligible=false`，有效路由仍为 **11 migrated、600 pending、0 cutover**。下一门禁是固定该 bootstrap 提交的 Git 外锚；operator、schema/index、真实数据迁移和 production cutover 继续禁止。

## 当前技术与边界

- `server/` 固定使用 Java 25、Maven Wrapper 3.9.16、Spring Boot 4.1.0 和 Spring Modulith 2.1.0；默认采用 Spring MVC，不引入 WebFlux、R2DBC 或阶段 8 之前的 Flyway。
- 模块化单体包含 `identity`、`catalog`、`personalbank`、`learning`、`assessment`、`community`、`messaging`、`campus`、`coding`、`intelligence`、`operations` 11 个业务模块，以及 `sharedkernel`、`web` 两个支撑模块。
- `identity`、`catalog`、`operations`、`personalbank` 与 `learning` 已部分实现，共有 27 个受机器合同约束的公开应用方法；其余 6 个业务模块仍保持延后形状。新增 4 个方法全部是 HTTP-neutral 内部边界，不代表两条 user-counts alias 已迁移。
- PostgreSQL 是唯一业务事实源；Redis 只用于可重建的辅助状态。Hibernate 始终使用 `ddl-auto=validate`，禁止 ORM 自动建表或改表。
- `catalog` 已通过 `identity::api` 迁移 `GET /api/quiz/subjects` 与 `/meta`；业务用例固定两条 SELECT，加上 HTTP 认证权威查询后正常成功请求总计三条 SELECT。读取保持稳定 ID 顺序和 per-identity/per-route Redis 限流，不拥有写入权，也未启用无法完整失效的应用数据缓存。
- `catalog` 还已实现公共题库 search/list/summary/hot/boards/detail/card 共 7 条旧路径兼容 GET。GET 只读取原子发布的完整 snapshot：`<= 300s` 正常服务、`300–900s` 服务最后完整快照并记陈旧指标、`> 900s` 或冷/残缺状态稳定返回 503 且 readiness fail closed；PostgreSQL 事务级 advisory lock 是最终单写者边界，Redis 仅作可过期、可接管的刷新协调。
- `catalog` 的 `QuestionMetadataApplicationApi` 以一条精确 `SELECT DISTINCT questions.type` 返回不可变的原始题型值，保留空串与 Unicode 空白供未来路径级兼容投影使用。它不包含中文展示、认证或错误信封；`GET /admin/api/types` 与 `GET /admin/types` 尚未迁入 Java HTTP 层，也不计入 migrated operation。
- 同一 API 还提供只读题量原语：显式区分匿名可保留 null 科目与认证必须匹配现存科目，支持精确科目/题型、受限科目和候选题集合。65,536 或 100,000 个候选 ID 仍使用一个 PostgreSQL `bigint[]` 参数，不展开动态 `IN`、不创建临时表，也不读取 learning/identity 自有表。`GET /api/questions/count` 与 `/api/quiz/questions/count` 的收藏、错题、私有标签、条件认证、缓存和限流仍待 Phase 4C 完整迁移。
- 同一 API 的 `findQuestionById(long)` 返回 `Optional<QuestionCatalogRecordView>`，只从 `questions` 读取 15 个原始事实字段；`options/answer/tags/image_path` 的畸形历史文本与所有 nullable 列均不被解析或丢失。`q_type`、`explanation`、portable/image-group 投影、鉴权和错误信封仍由未来 `operations` HTTP 适配层负责；`GET /admin/api/questions/{question_id}` 与 `GET /admin/questions/{question_id}` 延后到 4H，当前仍为 pending。
- 同一 API 的 `listQuestionSummaries(QuestionCatalogListQuery)` 只从 `questions` 读取 9 个原始事实字段，按可选 signed integer `subjectId` 与精确文本 `questionType` 选择四条固定 SQL，并始终 `q.id DESC`。返回不可变、无隐藏分页的集合；`createdBy` 只是原始 ID，catalog 不连接 `users/subjects`，也不做用户名、PQF、题型别名、tags/image 或 modern/legacy 投影。`GET /admin/api/questions` 与 `GET /admin/questions` 仍由 `operations` 持有并保持 pending。
- `catalog` 的 `SubjectMetadataApplicationApi#listSubjectInventorySummaries` 以一条无参数聚合查询返回 `id/name/isLocked/questionCount` 四个原始库存事实，保留 signed ID、空名称、nullable lock 和零题科目，并严格按 `id ASC` 返回不可变集合。它不复用会过滤锁定、空名称或受限科目的公共目录；`GET /admin/api/subjects` 仍由 `operations` 持有并保持 pending。
- 同一 API 的 `findSubjectById(long)` 返回 `Optional<SubjectContextView>`，只以一个 PostgreSQL `bigint` bind 读取 `subjects.id/name`；负 ID 在 JDBC 前拒绝，0 与 `Long.MAX_VALUE` 下沉查询。它不复用公共目录或库存聚合，也不加入 Controller、route/OpenAPI delta 或 cutover；`GET /admin/subjects/{subject_id}/questions` 与其 `/duplicate-check` 页面仍由 `operations` 持有并保持 pending。
- `QuestionMetadataApplicationApi#listQuestionExportRecords` 按可选的 `Optional<Integer> subjectId` 在两条固定 SQL 中二选一，以 `questions LEFT JOIN subjects` 返回严格 `q.id ASC` 的不可变十字段原始快照。catalog 保留 nullable/孤儿科目、空名称与畸形 JSON 文本，不做默认值、JSON 解析、认证、响应信封或安全错误投影；`GET /admin/api/questions/export` 与 `GET /admin/questions/export` 仍由 `operations` 持有，延后到 Phase 4H 并保持 pending。
- `PersonalBankApplicationApi#listCategories` 在只读事务中以一条固定 SQL 返回当前身份的不可变八字段分类事实；只统计关联到分类且 `status = 1` 的题库，保留旧栈的跨 owner 关联计数，并严格 `sort_order ASC NULLS LAST, id ASC`。双 alias 的认证、信封、日期/null 序列化、Session `last_active` 与安全故障投影尚未进入 Java HTTP 层，因此仍为 pending。
- `PersonalBankApplicationApi#findShares` 已实现 HTTP-neutral 分享列表读取：只读事务先用 `int bankId + bigint viewerId` 执行 owner/status probe，命中后再以第二条 SQL 原样读取 11 个 nullable 字段并按 `created_at DESC NULLS FIRST` 返回；不增加 tie-breaker、过滤、分页或 Java 重排。`Optional.empty` 与 present-empty 不混淆，列表由 `List.copyOf` 防御性复制。双 alias 的 Controller、认证、信封、OpenAPI、schema/index 与 cutover 仍未授权。
- 当前有效数据所有权为 **160 个资源且 160 个均有唯一 owner**。新增的 `learning` user-counts 限流 namespace 与 catalog snapshot/viewer 投影控制表、限流键和刷新锁一样，都是可重建辅助状态；`production cutover=0`，不能据此宣称接管旧业务事实或生产流量。

## 目录

- `server/`：Java 模块化单体、Maven Wrapper、架构/单元/集成测试和多阶段 Dockerfile。
- `infra/phase2/`：阶段 2 静态门禁、固定构建环境、PostgreSQL/Redis 夹具和本地参考结构验证工具。
- `infra/phase3/`：仅用于 local/test 的只读比较、隔离写终态比较及 stop/restore/start/rollback 拓扑工具。
- `compose.dev.yml`：与旧项目隔离的阶段 2 本地 Compose。
- `docs/refactor/phase2/`：阶段 2 范围、证据和未完成边界。
- `docs/refactor/phase3/`：阶段 3 路由增量、认证兼容、批准差异和 p3-009 双运行时证据。
- `docs/refactor/phase4a/`：科目、公共题库、题型、题量、单题详情、后台题目摘要集合、后台科目库存摘要、后台科目上下文与后台题目导出的读取金样、snapshot 决策、业务不变量、批准差异、累计路由/API 形状、查询计划证据、24-operation 候选处置与 Phase 4A closure 记录。
- `docs/refactor/phase4b/`：个人题库分类读取的最终验收证据，以及分享列表的调用方、40-case golden、PG16/18 SQL/计划、历史入口合同、累计 API shape 与已通过完整 Maven 的内部实现合同。
- `docs/refactor/phase4c/`：learning 组合、个人题库标签 compatibility namespace 所有权 overlay、显式迁移证据与批准差异，以及 user-counts HTTP pending implementation、59-disposition 目标执行 successor、OpenAPI、pending route delta 和限流资源所有权；完整 parity、operator、真实迁移与生产切流仍未闭合。
- `contracts/`：确定性生成的 OpenAPI 3.1.2 初稿与人工证据 override。
- `openapi/phase3-authentication.openapi.json`：两条 Phase 3 operation 的自包含 OpenAPI 3.1.2 增量。
- `openapi/phase4a-subject-directory.openapi.json`：两条科目目录 operation 的自包含 OpenAPI 3.1.2 增量。
- `openapi/phase4a-public-bank.openapi.json`：7 条公共题库 GET 的自包含 OpenAPI 3.1.2 增量，全部保持 `productionCutover=false`。
- `openapi/phase4c-personal-bank-user-counts.openapi.json`：两条 user-counts GET 的自包含 OpenAPI 3.1.2 implemented-pending 增量；HEAD/OPTIONS 是派生语义，不增加 migrated operation。
- `docs/refactor/adr/`：已接受的架构决策。
- `docs/refactor/phase1/`：API 约定、模块合同、关键不变量和对比/切换协议。
- `docs/refactor/`：事实盘点、迁移矩阵、数据所有权、运行手册与连续进度。
- `tools/`：迁移期盘点和黄金样本工具；不是生产运行依赖。
- `miniprogram/`：阶段 0 从旧项目受版本控制源码复制的新项目小程序基线。
- `web/`：计划在阶段 6 创建，目前尚未创建。
- `services/`：只有后续证明确需 Python 独立工作负载时才创建。

## Phase 2/3 验证

从本目录运行固定镜像构建的完整验证：

```bash
../.venv/bin/python -B -m unittest discover -s tools -p 'test_*.py'
./infra/phase2/verify-static.sh
./infra/phase2/verify-in-maven-container.sh -DargLine=-javaagent:/root/.m2/repository/org/mockito/mockito-core/5.23.0/mockito-core-5.23.0.jar clean verify
./infra/phase3/verify-static.sh
./infra/phase3/topology/verify-static.sh
./infra/phase3/topology/verify-data-plane.sh
```

第三条命令把本目录挂载到固定 Maven/Temurin 25 容器，以显式 Mockito Java agent 运行 JDK 25 测试，并挂载 Docker socket 供 Testcontainers 启动固定 digest 的 PostgreSQL 与 Redis。**Docker socket 近似授予容器主机 root 控制能力，只能对受信代码运行。** 若本机已经安装匹配的 Java 25 和 Maven 3.9.16，也可以运行，但同样必须通过 `-DargLine=-javaagent:<本机 mockito-core-5.23.0.jar 的绝对路径>` 显式加载 agent：

```bash
cd server
./mvnw -DargLine=-javaagent:"${HOME}/.m2/repository/org/mockito/mockito-core/5.23.0/mockito-core-5.23.0.jar" clean verify
```

阶段 2 最小夹具与完整 70 表本地参考结构验证的适用范围见 [`docs/refactor/phase2/README.md`](docs/refactor/phase2/README.md)；阶段 3 的读写、切换和回滚证据边界见 [`docs/refactor/phase3/README.md`](docs/refactor/phase3/README.md)。Phase 3 绿色检查点的完整 Maven 结果为 208 个 surefire 与 22 个 failsafe，Python 门禁为 29 项比较器测试与 59 项拓扑/审计/写证据测试；最终 WORM 与仅复制 `Ti-Java/` 的独立构建、启动、挂载边界和清理也已通过。

公共题库当前定向证据为 HTTP CatalogIT 7/7、Unicode Nd/控制器/限流/黄金定向 24/24、刷新 Coordinator 6/6、Redis 过期接管 3/3，以及 PostgreSQL 16/18 snapshot maintenance 2/2。固定旧提交 `700006dfdfa063deb4387be572911e782bcea0d9` 的完整应用归档含 46 个 case，SHA-256 为 `a63240ac2d22b0faff6daa143782eaa748bb54cda60b6c7ec9843a959eb486b5`；精确运行时 SQL 在 50,000 条 metrics 与 100,000 条 viewer state 上固定 7 条查询、无 N+1，计划 SHA-256 为 `570e471e85374f32f3d50c33b9b4d199a3230f17c2893c37a2fcf7469e1f2476`。本切片后的完整 `clean verify` 已通过 323 个 surefire 与 44 个 failsafe，0 failure/error/skip；当前 Java build-context 的 WORM 证据也已重捕并通过 Phase 2 静态门禁。仅复制 1,091 个受控源文件的 `Ti-Java/` 独立副本还通过 Phase 1、Phase 2/3 静态门禁、323+44 Maven 与独立 PostgreSQL/Redis 数据面往返，临时副本、容器和专用缓存卷均已清理。

题目类型元数据内部能力的固定旧提交 golden 为 22 个独立 case，覆盖 full admin、科目管理员、普通用户、匿名、Bearer-only、Session+Bearer、空表、Unicode 空白、别名/未知值和两种数据库故障信封；文件 SHA-256 为 `928e278edb35043126628c1050280c4792142c38088d47fefa86a12d401d8d6b`。精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 50,000 题目夹具上固定为一次查询、一次 `questions` 扫描和 12 个原始值，无 N+1；计划 SHA-256 为 `28f7221cb09fbc1f23ed1a2c92acf77e283d38874199b22465868a5f43f23853`，并在 PostgreSQL 16.14/18.4 兼容测试中通过。该证据只接受 catalog 内部能力，不接受两条后台 HTTP operation 已迁移。

题型内部能力切片的完整 `clean verify` 已通过 329 个 surefire 与 46 个 failsafe，0 failure/error/skip。该切片 Java build-context SHA-256 `fdc94000537d266595a22082ee28df0e7f04414855d6f4b36ba2125707153a8d` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness，并通过 Phase 2 静态新鲜度门禁。仅复制 1,109 个受控源文件的独立 `Ti-Java/` 副本还通过 Phase 1、Phase 2/3 静态门禁、329+46 Maven 与独立 PostgreSQL/Redis 数据面往返；临时副本、容器和专用缓存卷均已清理。

题量内部能力的固定旧提交 golden 为 36 个独立 case，覆盖双路由条件认证、Session/Bearer 优先级、首参数和 source/mode 优先级、锁定/受限/null 科目、题型转换、收藏/错题/标签及 GET 时缓存、限流、DDL 和故障副作用；文件 SHA-256 为 `8da18675ed9f2c38fdf4444606ecbd1b465fd08e8084829b6d20314271c62b00`。精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 50,000/150,000 题目夹具上覆盖 5 个固定变体和 7 个观测；65,536/100,000 个候选 ID 均保持一个 `bigint[]` bind，计划 SHA-256 为 `d1958ab2b471f5454614c20018e85840aed82d68ddea6575efe3cc33132161db`。该证据只接受 catalog 内部能力，不接受两条题量 HTTP operation 已迁移。

题量内部能力切片的完整 `clean verify` 已通过 346 个 surefire 与 48 个 failsafe，0 failure/error/skip。该切片 Java build-context SHA-256 `cc9bed50c29c379b6e2183b66e82f5c042c72ad934bfe3391c503639f3d9a9d7` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness；结构化报告 SHA-256 为 `e1b5d3a7a66864c31d0b6fb9d2e5d0494b58338d97f446b751d20acab0853842`。仅复制 1,126 个受控文件的独立 `Ti-Java/` 副本还通过 Phase 1、Phase 2/3 静态门禁、346+48 Maven、独立 PostgreSQL/Redis 数据面、镜像构建、Compose readiness 与 bind-source 审计；临时副本、容器、网络和卷均已清理。

单题详情内部能力的固定旧提交 golden 为 46 个隔离 case，覆盖双路由六类鉴权、五类正常题型、NULL/坏 JSON/图片组/未知题型、零号与 Unicode/前导零/不存在/`Long.MAX_VALUE`/溢出/负数 ID，以及 HTML/JSON 数据库故障；所有 case 的 15 列 `questions` 指纹不变且 DML=0。文件 SHA-256 为 `7920f17a7d28b647fd8d7ec59eebaa9f7fdd91e1f016cf4d2d78908d41b77155`，payload SHA-256 为 `5f7fc1ba7f13cf790bb5c130d5b1d39933217dd3b62a3cb91e4551fe72f19e16`。现代路由保留 raw options、生成兼容 answer、把合法 tags 数组连接为逗号字符串，并对标量或分组对象 image path 做单元素数组包装；旧路由投影显示数组、portable 与图片组字段，因此 catalog 没有固化任一路径的 HTTP DTO。

精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 150,000 题目夹具上固定 5 个观测：ID 1/75,000/150,000 命中，150,001 与 `Long.MAX_VALUE` 未命中；每次均为 1 个 `bigint` bind、1 条 SELECT、1 次 `questions_pkey` Index Scan、loops=1、TEMP=0。计划 SHA-256 为 `9cdac9cbc8709ee47049e09dc58612aadc77a236ab64e5ef086d0d45af41b4dc`，runtime SQL manifest SHA-256 为 `e861c39afe6c11b431cac0379e8174f842a31e988941baf3edde00e6a4e5cac1`；这是合成数据观察，不是生产延迟或容量 SLA。该详情切片的完整 `clean verify` 为 355 个 surefire 与 50 个 failsafe，0 failure/error/skip；build-context SHA-256 `50550a7f5f07ae1dd02ef11a16a71045c43aee5ec0d90e0d0ce81b2b8cc67783` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness，报告 SHA-256 为 `a6a88bc98b047896bf97046bfec1292610f01f620684a63171afcebbb9758b91`。仅复制 1,142 个受控文件且无符号链接、缓存或构建产物的独立副本也通过 Phase 1、Phase 2/3、355+50 Maven、独立 PostgreSQL/Redis 数据面、镜像构建、Compose readiness 与 bind-source 审计；8 个 bind 均来自副本且清理后无临时资源残留。

后台题目摘要集合内部能力的固定旧提交 golden 为 50 个隔离 case，覆盖双路由六类鉴权、首参数、signed subject、现代/旧题型归一化、NULL/畸形 raw 字段、负题目 ID 和 HTML/JSON 数据库故障；文件 SHA-256 为 `bc107912c61ee632457cb8563b29f9d69e99126d5c4be212d90dbdca40aac3b6`，case payload SHA-256 为 `cba2ad0d1a9e1ae75476fcf7e15d9821a65151930713da58a7ec595fc83ed1bc`。所有 case 的 15 列 `questions` 指纹不变且题目 DML/DDL=0；Session 请求仍可能由全局认证链更新一次 `users.last_active`，因此不能把完整 HTTP 请求误称为绝对零写入。

Java 导出的四条摘要 SQL 在 PostgreSQL 18.4 的 150,000 题目、5,000 科目与五种均匀题型夹具上固定 9 个观测，分别使用 0/1/1/2 个 typed bind；每次只有一条 statement、一次 `questions` 关系扫描、loops=1、TEMP=0、严格 `id DESC`，且不扫描 `users/subjects`。计划 SHA-256 为 `af368af15be3557882bf0e673271e0c685b43d23738f9226c8e908d95928c525`，runtime SQL manifest SHA-256 为 `98787090da5c5a0cdb95b6b9dddd8f7763caec872f3c7796c4a998930ed32fd5`；测试索引只描述合成观测，不授权生产 migration 或延迟 SLA。该集合切片的完整 `clean verify` 为 367 个 surefire 与 52 个 failsafe，0 failure/error/skip；build-context SHA-256 `ec1f76dc23acb1832f6c8d08953d7dd3df09cbeff1dfdb99c57545a0b0aed91a` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness，报告 SHA-256 为 `c5abd4833682ddf37350cdfe038944f0301b0b8affb656d235c5c86d01ca7abf`。两条集合 HTTP operation 继续是 `operations,pending,production_cutover=false`；本证据只接受 catalog 内部能力。

仅复制 1,160 个受控文件、0 个符号链接且不含缓存或构建产物的独立 `Ti-Java/` 副本，还以专用空 Maven 缓存通过 Phase 1、Phase 2/3 静态门禁、367+52 Maven、独立 PostgreSQL/Redis 数据面、镜像构建、3/3 Compose readiness 与重启恢复。8 个只读 bind 全部来自副本，源工作树 bind 为 0；临时目录、容器、网络、卷、镜像标签、专用缓存卷和测试端口均已清理至 0 残留。

后台科目库存摘要内部能力的固定旧提交 golden 为 11 个隔离 case，覆盖六类鉴权、空/单/多科目、signed ID 排序、空与 Unicode 名称、nullable lock、零题科目、孤儿/NULL 题目归属、HTML/JSON 数据库故障及 Session `users.last_active` 单列记账；文件 SHA-256 为 `6ce049b13741c2f095ca988fe4f02afc58951389ebdc9c40cf092555d9bb5d07`，case payload SHA-256 为 `f1ae276b9922cc66b1e8d2c613f060d7f30a4700cfac41a4b8a05f54adcaf0f9`。该证据只接受 catalog 内部能力，不接受 `GET /admin/api/subjects` 已迁移。

精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 5,002 科目、150,000 题目夹具上固定为一条 statement、0 个 bind、`subjects/questions` 各扫描一次、loops=1、TEMP=0，并严格返回 signed `id ASC`；计划 SHA-256 为 `f7c684273579e676b9da0024f76593ae9fb69bde47309e6d396c6fdf5a1cfb0c`，runtime SQL manifest SHA-256 为 `3c514f7f1ac79fe8d393f973fa19f136023be70e06968676f6a584d6199f09d7`。Java/合同定向 28/28、PostgreSQL 16.14/18.4 兼容 2/2、全部 source tools 132/132 均通过；完整 `clean verify` 为 379 个 surefire 与 54 个 failsafe，0 failure/error/skip。

build-context SHA-256 `befc34d1f79baab4ad7c895ca2718ed1d8e2efbf964978313f35806ff0ab8403` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness；结构化报告 SHA-256 为 `da9a55b6df570904760d868696497cd046030b67789d1457d8e94cd8af6f53ca`。该路由继续是 `operations,pending,production_cutover=false`。

仅复制 1,180 个受控文件、0 个符号链接且不含缓存或构建产物的独立 `Ti-Java/` 副本已完成最终验收；验收时源/副本的“相对路径 + 文件 SHA-256”清单均为 `c6a4156f180676e39717abc49a945fc9b4178b867e5dd2791a368693ca2622b7`，两者 build-context 均为 `befc34d1f79baab4ad7c895ca2718ed1d8e2efbf964978313f35806ff0ab8403`。权威 Maven 轮使用专用隔离缓存和原始 `./infra/phase2/verify-in-maven-container.sh clean verify` 命令，全程只有一个 Maven 容器，379+54 测试全部通过，墙钟 189 秒、Maven 计时 03:03；前置 Maven Central 传输中断及遗留工具 cell 并发轮全部作废，不计入通过证据。同一受控内容的重建副本还通过 Phase 1、Phase 2/3 静态门禁、独立 PostgreSQL/Redis 数据面、镜像构建、3/3 Compose readiness、API 重启恢复与 bind-source 审计；8 个只读 bind 全部来自副本，源工作树 bind 为 0，临时目录、容器、网络、卷、镜像标签、专用缓存卷和测试端口均已清理至 0 残留。

后台题集页面科目上下文内部能力的固定旧提交 golden 为 38 个隔离 case、每条路由 19 个，覆盖 7 类鉴权、3 类数据、7 类路径整数和 2 类数据库故障；文件 SHA-256 为 `fe9d29a6e3731062f2b00b5b9e953cb940c93a13cb4a146a7617875b8413945d`，case payload SHA-256 为 `fce72c233b1d9637e066d15803b55f4310a5452d6e9bf07f13367632c3a946c8`。静态调用方审计只发现 `_question_scripts.html:788` 与 `_scripts.html:789` 两处 duplicate-check 动态调用。该证据只接受 catalog 内部能力，不接受两条后台页面 HTTP operation 已迁移。

精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 150,000 科目夹具上固定 5 个观测：ID 1/75,000/150,000 命中，150,001 与 `Long.MAX_VALUE` 未命中；每次均为 1 个 `bigint` bind、1 条 SELECT、1 次 `subjects_pkey` Index Scan、loops=1、TEMP=0。计划 SHA-256 为 `f602a76a4764d098bb86aa9a8ef2a44048b0bcb977ed46cb675024e51c6d6db3`，runtime SQL manifest SHA-256 为 `dfbdd1e8efa66892d0efaa040690c412256b0b7c692f8d01098851509fa63e9c`；这是合成数据观察，不是生产延迟或容量 SLA。

该切片 Java/合同定向 36/36、PostgreSQL 16.14/18.4 compatibility 2/2、golden/计划工具 23/23、全部 source tools 155/155 均通过；源目录与仅复制 1,197 个受控文件的独立副本都以原始命令通过 391 个 surefire + 56 个 failsafe，0 failure/error/skip，独立轮 Maven 计时 02:13。build-context SHA-256 `19a4cf2f629762362c6d7104e88ec726266ff50da2a4a045faeb581a2e0fe6d9` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness，报告 SHA-256 为 `ad0a89753d7dd4aa884f95fe3a8e76b394869f69732414996d1042170bcf5c11`。独立副本还通过 Phase 1、Phase 2/3 静态门禁、PostgreSQL/Redis 数据面、镜像构建、3/3 Compose readiness、API 重启恢复与 8-bind source 审计；临时目录、容器、网络、卷、镜像标签、专用缓存卷和测试端口均已清理至 0 残留。对应绿色功能检查点为 `643c3b3`。

后台题目导出 catalog-only 能力的固定旧提交 golden 为 44 个隔离 case、每条路由 22 个，文件 SHA-256 为 `89ce148cb32d1ca26d2f9d617385ae86243cf264f6d33dede97018435d00530d`。它固定两条路由的认证/角色、首个原始 `subject_id`、十字段导出投影、modern/legacy 信封、Accept 相关故障与 Session `users.last_active` 身份副作用；所有 case 的 `questions`、`subjects` 和身份事实指纹保持不变，catalog DML/DDL 为 0。

Java 导出的两条固定 SQL 已在 PostgreSQL 18.4 的 150,000 题目、5,002 科目夹具上形成 9 个观测；全量查询的单个 Memoize 节点有 5,004 个 distinct subject-key probe，每次执行仍只有 1 条 statement、`questions/subjects` 各 1 个 scan node、root loops=1、TEMP=0 且严格 `q.id ASC`。计划 SHA-256 为 `96f04c1018f5c3a826c48972c2273096f8507e45900616ca6c842ee0318ae541`；这是合成观测，不是生产延迟、容量或索引 SLA。

题目导出切片的 Java/合同定向 53/53、PostgreSQL 16.14/18.4 compatibility 2/2、全部 source tools 215/215 与最终完整 `clean verify` 406 个 surefire + 58 个 failsafe 已通过，0 failure/error/skip。WORM 以 build-context SHA-256 `9fbff246ce5f7ca8fc7fb3e723261c1b5a75f39ac43e935974be6025b663741e` 通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness，报告 SHA-256 为 `f245d1def582c0527ad419e5fad8bcafbfff40270dec15007a8dec77f453c410`。完整运行态验收在仅复制 1,220 个受控文件、0 个符号链接且不含缓存或构建产物的独立副本中，以专用空 Maven 缓存通过 Phase 1、Phase 2/3 静态门禁、406+58 Maven、独立 PostgreSQL/Redis 数据面、唯一镜像、3/3 Compose readiness、API 重启恢复与 8-bind source 审计；8 个只读 bind 全部来自副本，源工作树 bind 为 0，清理后临时目录、容器、网络、卷、镜像标签、缓存卷和端口均为 0 残留。随后 `phase4a-final-acceptance.json` 绑定该原始报告、WORM 与候选处置，并对当前 1,220 个受控文件中的其余 1,219 个文件做非递归最终清单（只排除合同自身）。两条导出 HTTP operation 仍是 `operations,pending,production_cutover=false` 并延后到 Phase 4H；24 个有界候选已处置为 Phase 4H 16 条、Phase 4C 4 条、Phase 6 4 条、implement-now 0 条。最终合同只授权 Phase 4B 的 `19b37a262989` 与 `e32aec766730` 两条 category alias 作为下一步，二者本身仍是 pending 且未切流。

个人题库分类内部读取的旧栈 golden 共 22 个 case，文件 SHA-256 为 `c81ad22b70e1e9e25eed96e2f06a475ba590eb7ae00b7a106c6bcedac3818515`；PG18 查询计划证据 SHA-256 为 `0b23e9af5cdbaec543fb798a45dd3c6fcd5c8a11cd9f7d27aeb92550cc80cffc`。PostgreSQL 16.14/18.4 JDBC 兼容测试、全部 source tools 248/248 与完整 `clean verify` 424 个 surefire + 60 个 failsafe 均通过，0 failure/error/skip。build-context SHA-256 `51d381c5b85885b9fe902d7afd20324a34525f3cbc97acde27673ea6a7a11154` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness；结构化快照 SHA-256 为 `778519fffe693f37ddec34cb458bc712c40d90054e99606a6e9c4b8abc64e0d3`。仅复制 1,249 个受控文件的独立副本还通过 Phase 1/2/3 静态门禁、36 项小程序测试、空缓存 424+60 Maven、独立数据面、镜像、3/3 Compose readiness、重启与 bind-source 审计，并对除最终合同自身外的 1,248 个文件形成非递归清单。该结果只接受 personalbank 内部能力；两条 category alias 仍是 `pending,production_cutover=false`。

分享列表入口证据已经闭合固定提交上的活跃 Web、小程序 `bank-detail`、可外部直达的 `bank-share` 页面及 dormant/orphan 来源，并以 40 个双 alias case 固定认证、owner/status 短路、11 个 nullable 原始字段、故障与可观察排序。历史入口检查点保持 22/22 工具、7/7 合同、277/277 source tools 与 429+62 Maven 不变；后续 read-contract 以 predecessor 哈希承接该快照，并锁定生产 API/DTO/service/port/adapter。生产 SQL 与入口计划逐字一致，PG16.14/18.4 adapter IT、全部 source tools 284/284、实现后完整 Maven 446+64 及 WORM 均通过。WORM 在 PostgreSQL 18.4 的 70 表/617 列隔离恢复上通过只读 ACL、Hibernate `validate`、启动与 readiness，报告 SHA-256 为 `779154127fc700e213fbb3d5f83c112c090d3481236dcd361dbd72b74a0bd1ad`。同一受控内容的独立副本验收与只排除 read-contract 自身的最终控制面也已闭合；四条 personalbank HTTP alias、OpenAPI、Security、schema/index 与 production cutover 均未改变。

## 启动独立开发 Compose

```bash
cp .env.example .env
docker compose --env-file .env -f compose.dev.yml config --quiet
docker compose --env-file .env -f compose.dev.yml up --build -d
curl --fail http://127.0.0.1:18080/livez
curl --fail http://127.0.0.1:18080/readyz
```

默认只向宿主机发布 Java API `127.0.0.1:18080` 和 PostgreSQL `127.0.0.1:25432`；二者同时连接专用宿主接入网与内部后端网，Redis 只连接内部后端网且不发布宿主端口。Prometheus 端点只监听容器管理端口 `9090`，不映射到宿主机，也不经 `18080` 暴露。镜像基础版本均在 `server/Dockerfile` 与 `compose.dev.yml` 中按 digest 固定。

此 Compose 已承载 Phase 3 本地认证垂直切片，但只允许连接隔离的本地开发数据；不得连接生产数据库，也不得与旧 Flask 共享可写数据库、卷或 Redis。

## 阶段 0/1 可重复命令

从仓库根目录运行：

```bash
.venv/bin/python Ti-Java/tools/inventory_legacy.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor

.venv/bin/python Ti-Java/tools/capture_golden_samples.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor/golden-samples

.venv/bin/python Ti-Java/tools/measure_legacy_baseline.py \
  --legacy-root . \
  --output Ti-Java/docs/refactor/legacy-performance-sample.json \
  --samples 5

.venv/bin/python Ti-Java/tools/inventory_surfaces.py \
  --legacy-root . \
  --miniprogram-root Ti-Java/miniprogram \
  --output Ti-Java/docs/refactor/09-surface-inventory.json

node --test Ti-Java/miniprogram/tests/*.test.js
python3 Ti-Java/tools/validate_phase0.py --legacy-root .

python3 Ti-Java/tools/generate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_boundaries.py
python3 Ti-Java/tools/validate_phase1.py
```

阶段 0 工具只读取旧代码，并在临时测试数据库中构造脱敏样本；阶段 1 生成器只读取已冻结在本目录内的矩阵、黄金样本和人工 override。它们均不是新项目生产运行依赖。

## 进度入口

继续实施前先阅读 [`docs/refactor/05-progress.md`](docs/refactor/05-progress.md)。只有迁移计划的最终完成定义全部满足，才能宣告 Ti-Java 具备替代旧项目的条件。
