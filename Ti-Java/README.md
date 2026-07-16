# Ti-Java

Ti-Java 是 Ti 的独立重构项目，目标是以 Java 25、Spring Boot 4.1、Spring MVC 和 Spring Modulith 重新实现现有业务，并逐步加入 Vue 3 + TypeScript Web 与项目自有的小程序。

阶段 0 事实基线与阶段 1 架构/契约已经固化，阶段 2 Java 基础骨架与阶段 3 认证兼容切片也已通过门禁；阶段 4A 已实现受保护科目目录和公共题库 7 条 GET 的 Java shadow 切片，并补齐题目类型、题量与单题详情的 catalog 内部读取能力。当前有效状态仍是 **11 个 migrated operation、600 个 pending、0 个 production cutover**；两条后台题型与两条单题详情 HTTP 路由继续由 `operations` 持有，两条题量 HTTP 路由延后由 Phase 4C 的 `learning` 组合，六条路径都保持 pending。旧 Flask 仍是生产运行所有者，整个长期重构目标也尚未完成。

## 当前技术与边界

- `server/` 固定使用 Java 25、Maven Wrapper 3.9.16、Spring Boot 4.1.0 和 Spring Modulith 2.1.0；默认采用 Spring MVC，不引入 WebFlux、R2DBC 或阶段 8 之前的 Flyway。
- 模块化单体包含 `identity`、`catalog`、`personalbank`、`learning`、`assessment`、`community`、`messaging`、`campus`、`coding`、`intelligence`、`operations` 11 个业务模块，以及 `sharedkernel`、`web` 两个支撑模块。
- `identity`、`catalog` 与 `operations` 已部分实现，共有 15 个受机器合同约束的公开应用方法；其余 8 个业务模块仍保持延后形状，不能从占位名称推断为已迁移能力。
- PostgreSQL 是唯一业务事实源；Redis 只用于可重建的辅助状态。Hibernate 始终使用 `ddl-auto=validate`，禁止 ORM 自动建表或改表。
- `catalog` 已通过 `identity::api` 迁移 `GET /api/quiz/subjects` 与 `/meta`；业务用例固定两条 SELECT，加上 HTTP 认证权威查询后正常成功请求总计三条 SELECT。读取保持稳定 ID 顺序和 per-identity/per-route Redis 限流，不拥有写入权，也未启用无法完整失效的应用数据缓存。
- `catalog` 还已实现公共题库 search/list/summary/hot/boards/detail/card 共 7 条旧路径兼容 GET。GET 只读取原子发布的完整 snapshot：`<= 300s` 正常服务、`300–900s` 服务最后完整快照并记陈旧指标、`> 900s` 或冷/残缺状态稳定返回 503 且 readiness fail closed；PostgreSQL 事务级 advisory lock 是最终单写者边界，Redis 仅作可过期、可接管的刷新协调。
- `catalog` 的 `QuestionMetadataApplicationApi` 以一条精确 `SELECT DISTINCT questions.type` 返回不可变的原始题型值，保留空串与 Unicode 空白供未来路径级兼容投影使用。它不包含中文展示、认证或错误信封；`GET /admin/api/types` 与 `GET /admin/types` 尚未迁入 Java HTTP 层，也不计入 migrated operation。
- 同一 API 还提供只读题量原语：显式区分匿名可保留 null 科目与认证必须匹配现存科目，支持精确科目/题型、受限科目和候选题集合。65,536 或 100,000 个候选 ID 仍使用一个 PostgreSQL `bigint[]` 参数，不展开动态 `IN`、不创建临时表，也不读取 learning/identity 自有表。`GET /api/questions/count` 与 `/api/quiz/questions/count` 的收藏、错题、私有标签、条件认证、缓存和限流仍待 Phase 4C 完整迁移。
- 同一 API 的 `findQuestionById(long)` 返回 `Optional<QuestionCatalogRecordView>`，只从 `questions` 读取 15 个原始事实字段；`options/answer/tags/image_path` 的畸形历史文本与所有 nullable 列均不被解析或丢失。`q_type`、`explanation`、portable/image-group 投影、鉴权和错误信封仍由未来 `operations` HTTP 适配层负责；`GET /admin/api/questions/{question_id}` 与 `GET /admin/questions/{question_id}` 延后到 4H，当前仍为 pending。
- 当前有效数据所有权为 **159 个资源且 159 个均有唯一 owner**。公共题库新增的 snapshot/viewer 投影控制表、读取限流键和刷新锁均是可重建辅助状态，`production cutover=0`，不能据此宣称接管旧业务事实或生产流量。

## 目录

- `server/`：Java 模块化单体、Maven Wrapper、架构/单元/集成测试和多阶段 Dockerfile。
- `infra/phase2/`：阶段 2 静态门禁、固定构建环境、PostgreSQL/Redis 夹具和本地参考结构验证工具。
- `infra/phase3/`：仅用于 local/test 的只读比较、隔离写终态比较及 stop/restore/start/rollback 拓扑工具。
- `compose.dev.yml`：与旧项目隔离的阶段 2 本地 Compose。
- `docs/refactor/phase2/`：阶段 2 范围、证据和未完成边界。
- `docs/refactor/phase3/`：阶段 3 路由增量、认证兼容、批准差异和 p3-009 双运行时证据。
- `docs/refactor/phase4a/`：科目、公共题库、题型、题量与单题详情的读取金样、snapshot 决策、业务不变量、批准差异、累计路由/API 形状和查询计划证据。
- `contracts/`：确定性生成的 OpenAPI 3.1.2 初稿与人工证据 override。
- `openapi/phase3-authentication.openapi.json`：两条 Phase 3 operation 的自包含 OpenAPI 3.1.2 增量。
- `openapi/phase4a-subject-directory.openapi.json`：两条科目目录 operation 的自包含 OpenAPI 3.1.2 增量。
- `openapi/phase4a-public-bank.openapi.json`：7 条公共题库 GET 的自包含 OpenAPI 3.1.2 增量，全部保持 `productionCutover=false`。
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
./infra/phase2/verify-static.sh
./infra/phase2/verify-in-maven-container.sh clean verify
./infra/phase3/verify-static.sh
./infra/phase3/topology/verify-static.sh
./infra/phase3/topology/verify-data-plane.sh
```

第二条命令把本目录挂载到固定 Maven/Temurin 25 容器，并挂载 Docker socket 供 Testcontainers 启动固定 digest 的 PostgreSQL 与 Redis。**Docker socket 近似授予容器主机 root 控制能力，只能对受信代码运行。** 若本机已经安装匹配的 Java 25 和 Maven 3.9.16，也可以运行：

```bash
cd server
./mvnw clean verify
```

阶段 2 最小夹具与完整 70 表本地参考结构验证的适用范围见 [`docs/refactor/phase2/README.md`](docs/refactor/phase2/README.md)；阶段 3 的读写、切换和回滚证据边界见 [`docs/refactor/phase3/README.md`](docs/refactor/phase3/README.md)。Phase 3 绿色检查点的完整 Maven 结果为 208 个 surefire 与 22 个 failsafe，Python 门禁为 29 项比较器测试与 59 项拓扑/审计/写证据测试；最终 WORM 与仅复制 `Ti-Java/` 的独立构建、启动、挂载边界和清理也已通过。

公共题库当前定向证据为 HTTP CatalogIT 7/7、Unicode Nd/控制器/限流/黄金定向 24/24、刷新 Coordinator 6/6、Redis 过期接管 3/3，以及 PostgreSQL 16/18 snapshot maintenance 2/2。固定旧提交 `700006dfdfa063deb4387be572911e782bcea0d9` 的完整应用归档含 46 个 case，SHA-256 为 `a63240ac2d22b0faff6daa143782eaa748bb54cda60b6c7ec9843a959eb486b5`；精确运行时 SQL 在 50,000 条 metrics 与 100,000 条 viewer state 上固定 7 条查询、无 N+1，计划 SHA-256 为 `570e471e85374f32f3d50c33b9b4d199a3230f17c2893c37a2fcf7469e1f2476`。本切片后的完整 `clean verify` 已通过 323 个 surefire 与 44 个 failsafe，0 failure/error/skip；当前 Java build-context 的 WORM 证据也已重捕并通过 Phase 2 静态门禁。仅复制 1,091 个受控源文件的 `Ti-Java/` 独立副本还通过 Phase 1、Phase 2/3 静态门禁、323+44 Maven 与独立 PostgreSQL/Redis 数据面往返，临时副本、容器和专用缓存卷均已清理。

题目类型元数据内部能力的固定旧提交 golden 为 22 个独立 case，覆盖 full admin、科目管理员、普通用户、匿名、Bearer-only、Session+Bearer、空表、Unicode 空白、别名/未知值和两种数据库故障信封；文件 SHA-256 为 `928e278edb35043126628c1050280c4792142c38088d47fefa86a12d401d8d6b`。精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 50,000 题目夹具上固定为一次查询、一次 `questions` 扫描和 12 个原始值，无 N+1；计划 SHA-256 为 `28f7221cb09fbc1f23ed1a2c92acf77e283d38874199b22465868a5f43f23853`，并在 PostgreSQL 16.14/18.4 兼容测试中通过。该证据只接受 catalog 内部能力，不接受两条后台 HTTP operation 已迁移。

题型内部能力切片的完整 `clean verify` 已通过 329 个 surefire 与 46 个 failsafe，0 failure/error/skip。当前 Java build-context SHA-256 `fdc94000537d266595a22082ee28df0e7f04414855d6f4b36ba2125707153a8d` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness，并通过 Phase 2 静态新鲜度门禁。仅复制 1,109 个受控源文件的独立 `Ti-Java/` 副本还通过 Phase 1、Phase 2/3 静态门禁、329+46 Maven 与独立 PostgreSQL/Redis 数据面往返；临时副本、容器和专用缓存卷均已清理。

题量内部能力的固定旧提交 golden 为 36 个独立 case，覆盖双路由条件认证、Session/Bearer 优先级、首参数和 source/mode 优先级、锁定/受限/null 科目、题型转换、收藏/错题/标签及 GET 时缓存、限流、DDL 和故障副作用；文件 SHA-256 为 `8da18675ed9f2c38fdf4444606ecbd1b465fd08e8084829b6d20314271c62b00`。精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 50,000/150,000 题目夹具上覆盖 5 个固定变体和 7 个观测；65,536/100,000 个候选 ID 均保持一个 `bigint[]` bind，计划 SHA-256 为 `d1958ab2b471f5454614c20018e85840aed82d68ddea6575efe3cc33132161db`。该证据只接受 catalog 内部能力，不接受两条题量 HTTP operation 已迁移。

题量内部能力切片的完整 `clean verify` 已通过 346 个 surefire 与 48 个 failsafe，0 failure/error/skip。当前 Java build-context SHA-256 `cc9bed50c29c379b6e2183b66e82f5c042c72ad934bfe3391c503639f3d9a9d7` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness；结构化报告 SHA-256 为 `e1b5d3a7a66864c31d0b6fb9d2e5d0494b58338d97f446b751d20acab0853842`。仅复制 1,126 个受控文件的独立 `Ti-Java/` 副本还通过 Phase 1、Phase 2/3 静态门禁、346+48 Maven、独立 PostgreSQL/Redis 数据面、镜像构建、Compose readiness 与 bind-source 审计；临时副本、容器、网络和卷均已清理。

单题详情内部能力的固定旧提交 golden 为 46 个隔离 case，覆盖双路由六类鉴权、五类正常题型、NULL/坏 JSON/图片组/未知题型、零号与 Unicode/前导零/不存在/`Long.MAX_VALUE`/溢出/负数 ID，以及 HTML/JSON 数据库故障；所有 case 的 15 列 `questions` 指纹不变且 DML=0。文件 SHA-256 为 `7920f17a7d28b647fd8d7ec59eebaa9f7fdd91e1f016cf4d2d78908d41b77155`，payload SHA-256 为 `5f7fc1ba7f13cf790bb5c130d5b1d39933217dd3b62a3cb91e4551fe72f19e16`。现代路由保留 raw options、生成兼容 answer、把合法 tags 数组连接为逗号字符串，并对标量或分组对象 image path 做单元素数组包装；旧路由投影显示数组、portable 与图片组字段，因此 catalog 没有固化任一路径的 HTTP DTO。

精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 150,000 题目夹具上固定 5 个观测：ID 1/75,000/150,000 命中，150,001 与 `Long.MAX_VALUE` 未命中；每次均为 1 个 `bigint` bind、1 条 SELECT、1 次 `questions_pkey` Index Scan、loops=1、TEMP=0。计划 SHA-256 为 `9cdac9cbc8709ee47049e09dc58612aadc77a236ab64e5ef086d0d45af41b4dc`，runtime SQL manifest SHA-256 为 `e861c39afe6c11b431cac0379e8174f842a31e988941baf3edde00e6a4e5cac1`；这是合成数据观察，不是生产延迟或容量 SLA。当前完整 `clean verify` 为 355 个 surefire 与 50 个 failsafe，0 failure/error/skip；build-context SHA-256 `50550a7f5f07ae1dd02ef11a16a71045c43aee5ec0d90e0d0ce81b2b8cc67783` 的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness，报告 SHA-256 为 `a6a88bc98b047896bf97046bfec1292610f01f620684a63171afcebbb9758b91`。仅复制 1,142 个受控文件且无符号链接、缓存或构建产物的独立副本也通过 Phase 1、Phase 2/3、355+50 Maven、独立 PostgreSQL/Redis 数据面、镜像构建、Compose readiness 与 bind-source 审计；8 个 bind 均来自副本且清理后无临时资源残留。

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
