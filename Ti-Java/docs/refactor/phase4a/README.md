# Phase 4A：目录与公共题库

本目录保存 Phase 4A 的可执行契约、黄金样本、差异报告和性能证据。旧 Flask
只作为测试期契约来源；Java 生产运行时不得读取父目录或回调 Flask。

受保护科目目录与公共题库 7 条 GET 的 Java shadow 切片均已实现；题目类型、题目数量、
单题详情、后台题目摘要集合与后台科目库存摘要的 catalog 内部读取能力也已实现。两条后台题型、
两条单题详情、两条后台题目集合与一条后台科目库存 HTTP operation 仍由 `operations` 持有，
两条题量 HTTP operation 经审计应由 Phase 4C 的 `learning` 组合，九条路径都保持 pending。当前有效状态为
**11 migrated、600 pending、0 production cutover**，有效
资源为 **159 个且全部唯一 owner**；旧 Flask 仍是生产运行所有者，Phase 4A 后续切片和
整个长期重构目标都尚未完成。

## 垂直切片顺序

1. `GET /api/quiz/subjects` 与 `GET /api/quiz/subjects/meta`：受保护科目目录读取，已实现；
2. 公共题库广场 search/list、summary、hot、boards、detail、card 共 7 条 GET：已实现
   complete snapshot 只读边界，并隔离旧实现 GET 中的惰性刷新写入；
3. 题目类型元数据：已固定双路由真实 Flask 行为并实现原始类型 catalog 内部 API；两条
   HTTP operation 延后到 4H，当前不写 route/OpenAPI delta；
4. 题目数量：已审计双路由并实现只读 `questions/subjects` 的 catalog 计数原语；收藏、错题、
   私有标签、条件认证、缓存和限流组成完整用例，延后到 4C 由 `learning` 一次迁移双路由；
5. 单题详情：已固定双路由真实 Flask 行为并实现 15 列原始 `questions` 事实读取；现代/legacy
   响应投影和鉴权保留给 `operations`，延后到 4H，当前不写 route/OpenAPI delta；
6. 后台题目摘要集合：已固定双路由真实 Flask 行为并实现 9 列原始 `questions` 事实读取；
   catalog 只做精确可选过滤与 `id DESC`，两条 HTTP operation 延后到 4H；
7. 后台科目库存摘要：已固定 `GET /admin/api/subjects` 的 11-case 真实 golden，并实现 catalog
   内部 `subjects/questions` 聚合读取；HTTP operation 延后到 4H；
8. 后台题集页面科目上下文：下一项，以 `GET /admin/subjects/<int:subject_id>/questions` 为主、
   duplicate-check 页面为共享语义对照，固定单科目 `id/name` 读取而不迁移两条 HTTP operation；
9. 在 4C 由 `learning` 组合 `GET /api/quiz/subjects/{subject}/info` 中的作答、错题和收藏统计。

切片 1 不越权读取 `identity.user_subjects`：`catalog` 通过 `identity::api` 获取用户黑名单，
再在内存中与目录自有读取结果求差。它也不读取 `learning` 所有的 `user_answers`、
`mistakes` 或 `favorites`。

## 当前证据

- `golden-subject-reads.json`：7 个隔离 Flask 请求，覆盖普通用户、管理员、未认证、
  第 61 次请求限流、锁定科目、受限科目、空题量和稳定 ID 排序；
- `subject-read-contract.json`：字段、鉴权、排序、空值、查询预算和模块边界；
- `business-invariants.json`：可由 Java 单元/集成测试逐项证明的不变量。
- `data-ownership-delta.csv`：新增可重建 Redis 限流运行时键的唯一 owner 和生命周期；
- `subject-query-plan.json`：PostgreSQL 18 上 5,000 科目、50,000 题目和 50,000
  条限制关系的单次隔离 `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` 观测；它不是
  生产延迟承诺。
- `golden-public-bank-reads.json`：固定旧提交
  `700006dfdfa063deb4387be572911e782bcea0d9` 的 46-case 完整应用归档，覆盖匿名/可选
  身份、Unicode `Nd`（含阿拉伯-印度数字与全角数字）、任意精度路径/查询整数和错误形状；
  SHA-256 为 `a63240ac2d22b0faff6daa143782eaa748bb54cda60b6c7ec9843a959eb486b5`；
- `public-bank-read-contract.json` 与 `public-bank-rate-limit-contract.json`：固定 7 条 GET
  的字段、路径转换器、分页/排序/筛选、身份关系、错误信封与限流语义；
- `public-bank-metrics-snapshot-decision.md`：固定原子 complete snapshot、300/900 秒
  freshness、fail-closed readiness、PostgreSQL 最终单写者锁和 Redis 降级/过期接管边界；
- `public-bank-query-plan-evidence.json`：从 Java adapter 导出的精确运行时 SQL，在
  PostgreSQL 18.4 的 50,000 条 metrics 与 100,000 条 viewer state 上固定 7 条查询、
  无 N+1；SHA-256 为
  `570e471e85374f32f3d50c33b9b4d199a3230f17c2893c37a2fcf7469e1f2476`，不是生产延迟 SLA；
- `effective-route-parity-status.json` 与 `effective-data-ownership-status.json`：物化
  11/600/0 路由状态和 159/159 唯一资源 owner，不把 `migrated` 等同于生产切流。
- `golden-question-type-reads.json`：固定旧提交完整 `app/` 归档的 22-case 双路由证据，
  覆盖角色、匿名、Bearer 分流、空表、Unicode 空白、别名/未知值和 HTML/JSON 数据库故障；
  SHA-256 为 `928e278edb35043126628c1050280c4792142c38088d47fefa86a12d401d8d6b`；
- `question-type-read-contract.json`：明确 catalog 返回未经 trim/映射的原始题型值，
  `operations` 以后负责两条路径不同的认证、空白投影和故障信封；
- `question-type-query-plan-evidence.json`：从 Java adapter 导出的精确 SQL，在 PostgreSQL
  18.4 的 50,000 题目夹具上固定一次查询、一次 `questions` 扫描和无 N+1；SHA-256 为
  `28f7221cb09fbc1f23ed1a2c92acf77e283d38874199b22465868a5f43f23853`，不是生产延迟 SLA。
- `golden-question-count-reads.json`：固定旧提交完整 `app/` 归档，冻结双路径认证分流、原始
  参数、锁定/受限/null 科目、题型别名、收藏/错题/标签选择及 GET 时缓存/标签迁移副作用；
- `question-count-read-contract.json`：把 catalog-only 计数原语与 Phase 4C learning-owned HTTP
  用例分开，明确内部能力不授权 route/OpenAPI delta；
- `question-count-query-plan-evidence.json`：从 Java adapter 导出的固定 SQL 变体，在 PostgreSQL
  18.4 合成夹具上验证 catalog-only 关系预算，以及 65,536/100,000 个候选 ID 始终只占一个
  `bigint[]` bind parameter；它不是生产延迟或容量 SLA。
- `golden-question-detail-reads.json`：固定旧提交完整 `app/` 归档的 46-case 双路由证据，覆盖
  六类鉴权、正常与畸形题目、路径 ID 边界和 HTML/JSON 数据库故障；所有请求前后 15 列
  `questions` 指纹不变，DML=0；文件 SHA-256 为
  `7920f17a7d28b647fd8d7ec59eebaa9f7fdd91e1f016cf4d2d78908d41b77155`；
- `question-detail-read-contract.json`：把 catalog 的 15 列原始事实 DTO 与 `operations` 未来负责的
  鉴权、modern/legacy 响应投影、路径转换和安全错误信封分开；内部能力不授权 route/OpenAPI delta；
- `question-detail-query-plan-evidence.json`：从 Java adapter 导出的精确单行 SQL，在 PostgreSQL
  18.4 的 150,000 题目夹具上固定 5 个 ID 观测，每次只用一个 `bigint` bind 与
  `questions_pkey` Index Scan，loops=1、TEMP=0；SHA-256 为
  `9cdac9cbc8709ee47049e09dc58612aadc77a236ab64e5ef086d0d45af41b4dc`，不是生产延迟或容量 SLA。
- `golden-question-list-reads.json`：固定旧提交完整 `app/` 归档的 50-case 双路由证据，覆盖
  六类鉴权、signed subject/首参数、现代与旧题型归一化、NULL/畸形 raw 字段、负题目 ID
  和 HTML/JSON 数据库故障；文件 SHA-256 为
  `bc107912c61ee632457cb8563b29f9d69e99126d5c4be212d90dbdca40aac3b6`；
- `question-list-read-contract.json`：把 catalog 的 9 列原始摘要、两个 exact optional filter、
  四条固定 SQL 与 `operations` 未来负责的鉴权、参数解析、用户名/PQF/路径投影分开；内部能力
  不授权 Controller、模块依赖、route/OpenAPI delta 或 cutover；
- `question-list-query-plan-evidence.json`：从 Java adapter 导出的四条精确 SQL，在 PostgreSQL
  18.4 的 150,000 题目/5,000 科目夹具上固定 9 个观测；0/1/1/2 typed bind、每次一条
  statement、一次 `questions` 扫描、loops=1、TEMP=0、严格 `id DESC`，且 `users/subjects`
  零扫描。SHA-256 为 `af368af15be3557882bf0e673271e0c685b43d23738f9226c8e908d95928c525`；
  test-only synthetic indexes 不授权生产 migration 或延迟 SLA。
- `golden-subject-inventory-reads.json`：固定旧提交完整 `app/` 归档的 11-case 单路由证据，覆盖
  六类鉴权、空/单/多科目、signed ID、空/Unicode 名称、nullable lock、零题科目、孤儿/NULL
  题目归属及 HTML/JSON 数据库故障；Session `users.last_active` 单列记账与 catalog 业务零写入
  分开记录。文件 SHA-256 为 `6ce049b13741c2f095ca988fe4f02afc58951389ebdc9c40cf092555d9bb5d07`；
- `subject-inventory-read-contract.json`：固定四字段原始库存 DTO、严格 signed `id ASC`、禁止复用
  公共科目目录，以及无 Controller、模块依赖、route/OpenAPI delta 或 cutover 的边界；
- `subject-inventory-query-plan-evidence.json`：从 Java adapter 导出唯一无参数 SQL，在 PostgreSQL
  18.4 的 5,002 科目、150,000 题目夹具上固定 1 statement、0 bind、两表各扫描一次、
  loops=1、TEMP=0；SHA-256 为 `f7c684273579e676b9da0024f76593ae9fb69bde47309e6d396c6fdf5a1cfb0c`，
  仅为合成观测，不是生产延迟或容量 SLA。

Java 迁移路由不启用应用数据缓存；身份策略与目录两条业务查询读取同一只读、可重复读事务中的当前数据库状态；这是
`approved-differences.md` 中批准的过渡差异。业务用例是身份策略与目录各一条 SELECT，HTTP
认证权威边界再使用一条 SELECT，因此正常成功请求总计三条。

成功认证请求会原子写入按身份和精确路由隔离的 Redis 分钟/小时限流计数键；
身份键段使用域分离 HMAC 伪名，不包含原始用户 ID。
Bearer 不创建目标 Session；已有目标 Session 请求可刷新 Session 访问元数据并校验注册索引；
首次 Flask Session 兼容交换还会写入有界的交换/防重放键、新目标 Session 及其注册索引。
这些均是可重建的认证/限流运行态，不属于业务状态或响应缓存。

公共广场旧 GET 会在指标缺失或过期时取得 Redis 锁并重建数据库读模型，因此不能把
冷启动请求误称为无副作用读取。当前 Java GET 已改为只读原子发布的 complete snapshot：
`<= 300s` 正常服务，`300–900s` 服务最后完整快照并记录 stale，`> 900s`、冷启动或
结构不一致稳定返回 503，readiness fail closed。Snapshot maintenance 已在 PostgreSQL
16.14/18.4 证明失败回滚、原子发布与 advisory-lock 单写者；Redis 已证明真实过期后新 owner
接管且旧 token 不能删除新 token。

当前定向结果为 HTTP CatalogIT 7/7、Unicode/控制器/限流/黄金 24/24、Coordinator 6/6、
Redis 3/3、PostgreSQL 16/18 maintenance 2/2；本切片后的完整 `clean verify` 为 323 个
surefire + 44 个 failsafe，0 failure/error/skip。当前 build-context 的 WORM 证据和 Phase 2
静态门禁也已重新通过；只含 1,091 个受控源文件的独立 `Ti-Java/` 副本也已通过
Phase 1、Phase 2/3、323+44 Maven 和 PostgreSQL/Redis 数据面门禁，清理后无临时资源残留。旧 Flask
写路径的即时撤回事件、生产刷新调度、真实数据、Redis/HMAC
配置和入口切换仍未完成或获批，因此这 7 条 GET 必须保持 `production cutover=0`。

题型内部能力切片的完整 `clean verify` 为 329 个 surefire + 46 个 failsafe，
0 failure/error/skip。build-context SHA-256
`fdc94000537d266595a22082ee28df0e7f04414855d6f4b36ba2125707153a8d` 的 WORM、Phase 2
静态门禁与 Phase 3 数据面均已通过；仅含 1,109 个受控源文件的独立副本也通过 Phase 1、
Phase 2/3 静态门禁、329+46 Maven 和 PostgreSQL/Redis 数据面门禁，清理后无临时资源残留。

题量内部能力切片的完整 `clean verify` 为 346 个 surefire + 48 个 failsafe，
0 failure/error/skip。36 个固定旧提交 golden 的文件 SHA-256 为
`8da18675ed9f2c38fdf4444606ecbd1b465fd08e8084829b6d20314271c62b00`；5 个精确运行时
SQL 变体、7 个 PG18.4 观测和 65,536/100,000 候选数组的计划证据 SHA-256 为
`d1958ab2b471f5454614c20018e85840aed82d68ddea6575efe3cc33132161db`。build-context SHA-256
`cc9bed50c29c379b6e2183b66e82f5c042c72ad934bfe3391c503639f3d9a9d7` 的 WORM、Phase 2
静态门禁与 Phase 3 数据面均已通过；WORM 报告 SHA-256 为
`e1b5d3a7a66864c31d0b6fb9d2e5d0494b58338d97f446b751d20acab0853842`。仅含 1,126 个受控文件、
无符号链接的独立副本也通过 Phase 1、Phase 2/3 静态门禁、346+48 Maven、独立数据面、镜像
构建、Compose readiness 和 bind-source 审计，清理后无临时资源残留。固定旧提交归档的
重新捕获只在完整源仓库执行；独立副本消费已固定的合同与证据，不在运行时读取父目录。

单题详情内部能力加入后的完整 `clean verify` 为 355 个 surefire + 50 个 failsafe，
0 failure/error/skip。46-case golden 的 payload SHA-256 为
`5f7fc1ba7f13cf790bb5c130d5b1d39933217dd3b62a3cb91e4551fe72f19e16`；runtime SQL manifest
SHA-256 为 `e861c39afe6c11b431cac0379e8174f842a31e988941baf3edde00e6a4e5cac1`。build-context
SHA-256 `50550a7f5f07ae1dd02ef11a16a71045c43aee5ec0d90e0d0ce81b2b8cc67783` 的 WORM 已通过
PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness；结构化报告
SHA-256 为 `a6a88bc98b047896bf97046bfec1292610f01f620684a63171afcebbb9758b91`。仅复制 1,142 个
受控文件且无符号链接、缓存或构建产物的独立副本还通过 Phase 1、Phase 2/3、355+50 Maven、
独立 PostgreSQL/Redis 数据面、镜像构建、Compose readiness 与 bind-source 审计；8 个 bind
均来自副本且清理后无临时资源残留。两条详情 HTTP operation 继续是
`operations,pending,production_cutover=false`，本证据只接受 catalog 内部能力。

后台题目摘要集合内部能力加入后的完整 `clean verify` 为 367 个 surefire + 52 个 failsafe，
0 failure/error/skip。50-case golden 的 case payload SHA-256 为
`cba2ad0d1a9e1ae75476fcf7e15d9821a65151930713da58a7ec595fc83ed1bc`；runtime SQL manifest
SHA-256 为 `98787090da5c5a0cdb95b6b9dddd8f7763caec872f3c7796c4a998930ed32fd5`。build-context
SHA-256 `ec1f76dc23acb1832f6c8d08953d7dd3df09cbeff1dfdb99c57545a0b0aed91a` 的 WORM 已通过
PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness；结构化报告
SHA-256 为 `c5abd4833682ddf37350cdfe038944f0301b0b8affb656d235c5c86d01ca7abf`。两条后台集合 HTTP
operation 继续是 `operations,pending,production_cutover=false`，本证据只接受 catalog 内部能力。

仅含 1,160 个受控文件、0 个符号链接且不含缓存或构建产物的独立副本，还以专用空 Maven
缓存通过 Phase 1、Phase 2/3 静态门禁、367+52 Maven、独立 PostgreSQL/Redis 数据面、镜像
构建、3/3 Compose readiness、重启恢复与 bind-source 审计。8 个只读 bind 全部来自副本，
源工作树 bind 为 0；临时目录、容器、网络、卷、镜像标签、专用缓存卷与端口均已清理至 0 残留。

后台科目库存摘要内部能力的 Java/合同定向为 28/28，PostgreSQL 16.14/18.4 compatibility 为
2/2，golden/计划工具为 24/24，全部 source tools 为 132/132。完整 `clean verify` 为 379 个
surefire + 54 个 failsafe，0 failure/error/skip。runtime SQL manifest SHA-256 为
`3c514f7f1ac79fe8d393f973fa19f136023be70e06968676f6a584d6199f09d7`。

build-context SHA-256 `befc34d1f79baab4ad7c895ca2718ed1d8e2efbf964978313f35806ff0ab8403`
的 WORM 已通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate` 与 readiness；
结构化报告 SHA-256 为 `da9a55b6df570904760d868696497cd046030b67789d1457d8e94cd8af6f53ca`。
`GET /admin/api/subjects` 继续是 `operations,pending,production_cutover=false`，本证据只接受
catalog 内部能力。

仅含 1,180 个受控文件、0 个符号链接且不含缓存或构建产物的独立副本也已完成最终验收。
验收时源/副本的“相对路径 + 文件 SHA-256”清单均为
`c6a4156f180676e39717abc49a945fc9b4178b867e5dd2791a368693ca2622b7`，build-context 均为
`befc34d1f79baab4ad7c895ca2718ed1d8e2efbf964978313f35806ff0ab8403`。权威 Maven 轮使用
专用隔离缓存和原始 `./infra/phase2/verify-in-maven-container.sh clean verify` 命令，全程只有
一个 Maven 容器；379+54 测试全部通过，墙钟 189 秒、Maven 计时 03:03。前置 Maven Central
传输中断及遗留工具 cell 并发轮全部作废，不计入通过证据。同一受控内容的重建副本还通过
Phase 1、Phase 2/3 静态门禁、独立 PostgreSQL/Redis 数据面、镜像构建、3/3 Compose
readiness、API 重启恢复与 bind-source 审计；8 个只读 bind 全部来自副本，源工作树 bind 为
0，临时目录、容器、网络、卷、镜像标签、专用缓存卷和测试端口均已清理至 0 残留。
