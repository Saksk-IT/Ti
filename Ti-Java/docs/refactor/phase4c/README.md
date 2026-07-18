# Phase 4C：练习与学习记录

本目录保存 `learning` 垂直切片的实现前合同、HTTP-neutral read 后继合同、HTTP pending implementation 与 target-execution successor、OpenAPI/route delta、所有权 overlay、批准差异和可重复证据。
Phase 1/Phase 4A/Phase 4B 的历史基线保持不可变；Phase 4C 只能通过显式 successor
合同推进，不得把后续结论回写成早期事实。

Phase 4B 合同文档本身也保持 immutable。为维护 WORM 而调整的历史验收测试，只能接受
Phase 4C successor 合同中绑定的 accepted commit 与精确 source hash allowlist；不得按工作树、
HEAD 或任意新 source hash 动态放行，也不得据此改变 Phase 4B 的历史结论。

Phase 2 的历史 `local-reference-verification.json` 及 Phase 4B 副本同样保持字节不可变。
Phase 4C 使用版本化 successor 报告追加当前 build-context，由固定 allowlist gate 校验“Phase 4B 锚点 →
Phase 4C 入口 → Phase 4C HTTP-neutral read → access fail-closed hardening → HTTP pending implementation”的五节点连续链和唯一 tip；第五节点报告 SHA-256 为 `7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39`，绑定 build-context `273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3`。静态门禁不得扫描任意报告或接受调用方传入的报告路径，采集脚本也必须显式指定新路径、
拒绝任何已存在目标并以原子 no-clobber 方式发布。固定门禁同时绑定 canonical schema SHA，采集期间
Dockerfile/build-context 的前后摘要必须一致。

当前第一个有界切片是个人题库 `user-counts` 双 alias。Phase 4B 已冻结调用方、golden、
八个 SQL family 与 PostgreSQL 16/18 证据，并确认完整用例和未来 HTTP owner 为
`learning`。本目录首先闭合以下实现前门禁：

- `learning` 的完整 HTTP-neutral 请求、结果、查询顺序与失败边界；
- `personalbank::api` 只暴露访问判定和题目范围事实，禁止读取 learning persistence；
- 共享访问同时绑定请求题库、分享记录与分享本体，拒绝跨题库、未知权限和非确定性首行授权；
- `bank_<bank_id>_tags` compatibility namespace 的唯一 owner overlay；
- operator-only、幂等、逐来源行原子的显式迁移；
- 在 HTTP-neutral predecessor 时点，GET 禁止 DDL/DML，生产 schema/index、Controller、OpenAPI、route delta 和切流均为 0。

实现前合同已经由 `personal-bank-user-counts-read-contract.json` 的固定第二层后继承接。在 HTTP-neutral read predecessor 时点，生产面只新增
17 个 `learning`/`personalbank` 主源码并修改 `LearningApplicationApi`，累计形成 27 个公开应用方法；
`learning` 以 `NOT_SUPPORTED` 编排，模块内查询与 personalbank facts 使用独立 `REQUIRES_NEW` 只读事务，
候选题使用单个 PostgreSQL `integer[]` 参数。每次 facts 调用重新鉴权，任何 `DENIED` 都终止并丢弃部分字段；
只有可选字段的基础设施/事务查询异常允许局部降级。该历史 predecessor 的第四个 WORM tip 固定 40 文件模块 manifest、
288 文件生产面与 Java build-context；前三个 WORM 报告保持字节不可变，最后一次追加专门绑定空/未知
分享权限 fail closed 与 optional 事务 25P02 故障不扩散的最终生产面。

当前测试证据同时闭合逐来源行事务原语、
严格兼容数据解析、目标真子集/冲突和提交结果未知的阻断表达；完整 operator 的全局
dry-run/preflight、全量 blocker 汇总与逐项批准仍未闭合。生产
operator 实现必须在 dedicated connection 上用 session-level advisory lock 覆盖整个 preflight 与 apply，并在窗口内
冻结 legacy source、normalized target 及 bank/question membership 写入，或记录可比较的 version/digest
并在 apply 前复核；还必须用持久 migration ledger/version 或等价 tombstone 防止目标被有意清空后
从保留的 legacy source 复活标签。因此完整迁移设计和生产执行器均尚未闭合。在该历史 predecessor 时点，两条 HTTP alias 仍需独立的 Security、限流、
Controller、OpenAPI、双运行时对比与切流门禁；当前实现状态由后文的显式 successor 描述。

## User-counts HTTP entry gate

HTTP 入口通过第三层显式 successor 承接已经实现的 HTTP-neutral read，而不改写历史合同。
`personal-bank-user-counts-read-contract.json` 的物理 SHA-256
`458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73`
保持不可变；HTTP entry gate 只能精确绑定它并记录后续 source allowlist，不能从当前工作树、HEAD
或任意新哈希反向放宽 predecessor。

固定旧提交的 HTTP boundary evidence 最终包含 62 个双 alias case，并额外执行 8 个
CORS/OPTIONS 运行时观察，覆盖 GET/HEAD/OPTIONS、API/Web 认证协商、首参数、路径整数、错误信封、
请求 ID、CORS 与无业务副作用边界。其 case payload SHA-256 为
`f577ff99a7f04030fd5f4dae0f95610351d4fcfff92de7e9ca0c406516725dbf`，document payload
SHA-256 为 `3e8f7c24548d979723d2601c11221b9e569de7b342e6c3c0d8daa25de74cdd2f`。
这只是在 HTTP-neutral predecessor 时点固定的旧栈观察，不代表 Java HTTP 等价已闭合，也不替代浏览器、真实 Servlet、反向代理或生产流量证据。

独立 rate-limit evidence 固定 7 组旧栈事实：`10/second`、`500/hour`、`5000/day` 三个窗口，
两个注册 endpoint 的 alias scope，API/Web 429 内容协商，Session/Bearer/IP key 选择，以及 Redis
连接拒绝。`10/500/5000` 是旧 base 配置；固定生产部署默认乘数为 100，实际默认是
`1000/second;50000/hour;500000/day`，并可由部署环境显式覆盖。该证据不宣称真实生产吞吐、
多 worker 收敛、Redis 恢复连续性或可信代理地址链已验证。

`P4C-LEARNING-007` 至 `P4C-LEARNING-012` 是本入口的批准差异集合，依次固定：显式 Bearer
选择与统一拒绝、user-counts 不写 `users.last_active`、按有效 actor 的 HMAC 假名独立限流与 Redis
故障 503、仅 API alias 的 CORS 和无副作用 OPTIONS、Unicode `Nd`/溢出/防火墙路径边界，以及
GET 与派生 HEAD 的状态和语义一致，只有 HEAD 在所有状态保持零字节响应体。后续实现必须逐项携带差异 ID、强制测试和可观察影响，
不得把批准差异解释为绕过证据或切流门禁。

历史 entry gate 的状态是“只授权未来精确 HTTP slice，生产实现尚未开始”；该时点公开应用方法为 27 个，有效迁移状态为 **11 migrated、600 pending、0 production cutover**。这些实现前事实保持不变，但已由下述 successor 承接，不再是当前工作树状态。

## User-counts HTTP pending implementation checkpoint（历史 predecessor）

HTTP 生产适配已经存在：双 alias Controller、安全错误投影、严格路径解析、API-only CORS/OPTIONS、GET 与派生 HEAD 状态/语义一致且 HEAD 零响应体、独立 Redis 三窗口限流与相应配置/OpenAPI 均已物化。OpenAPI 和 route delta 将两条 GET 明确登记为 implemented-pending；派生 HEAD/OPTIONS 不计迁移 operation。新的 Redis namespace 由 `learning` 唯一拥有，有效所有权总数为 **160/160**。

该 implementation predecessor 固定 297 个 production runtime files；相对 288 文件 predecessor 精确新增 9 个、修改 6 个，并绑定 44 个 source contract 路径。第五节点 WORM 报告 SHA-256 为 `7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39`，Java build-context 为 `273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3`。

首次完整独立验收尝试虽逐段通过 source tools 与 Maven，但在 Compose 运行阶段发现 `read_only` API 服务不支持 environment-backed secret，因此整轮作废。将限流 HMAC Secret 改为 file-backed configtree 后，验收时冻结的 pre-documentation checkpoint 已从头重跑并通过：该冻结点 1,449 个受控文件的源/副本清单 SHA-256 均为 `154013da39c75fb33c7b0c9d02f4e0f34038b259972d4a9a7f93a7ae47e90d63`，临时报告 SHA-256 为 `2b3cd6e4ea34a501809b5083bad0b49db82dba0aea92b36a4328c5d2ac530f8d`。全部 source tools 496/496、Phase 1 23/23、Phase 2、Phase 3 29/29、topology 60/60、小程序 36/36、独立 PostgreSQL/Redis 数据面、专用空缓存 Maven 661+93、唯一镜像、3/3 Compose readiness 与重启恢复均绿色；9 个只读 bind 全部来自副本，environment Secret 为 0，临时资源和端口为 0 残留。该 manifest 与临时报告只描述验收冻结点，不是当前工作树的字节清单；其后的证据措辞、固定 trust/contract 与 parity 测试更新只由当前 source/contract 门禁另行约束。

真实随机端口 Tomcat `NetworkIT` 仍 mock `LearningApplicationApi` 与认证 ports；它证明网络和 Servlet 适配行为，但不证明 Target Session、Flask Session、Bearer、应用服务与 JDBC 的真实端到端链路。

在 implementation predecessor 时点，59-case 映射证据明确分类为 `PARTIAL_EXECUTION_MAPPING_LEDGER`：48 个 case 只通过 MockMvc 执行真实适配层并 mock `LearningApplicationApi`，8 个 case 仅绑定认证测试，3 个 case 仅绑定 typed PostgreSQL 测试。因此该历史时点的 `full_target_parity_closed=false`、`route_migration_eligible=false`，有效状态为 **11 migrated、600 pending、0 production cutover**。

该 predecessor 当时的下一门禁是消除绑定式和回显式证明；后文 target-execution successor 已完成此项。typed parity、真实 Tomcat、Redis 故障恢复、PG16/18 关键终止指纹和 bridge 外部提交锚定仍未闭合；operator、schema/index、真实数据迁移、客户端、网关和 production cutover 继续禁止。

## User-counts HTTP target-execution successor

历史 `PARTIAL_EXECUTION_MAPPING_LEDGER` 与 implementation contract 保持字节不可变。新的 target-execution successor 以 implementation contract 的物理 SHA-256 `c6a977f260bdd0ab4af6dace1b4c7d48803b5e8f9bc5299723b662226e45cfbd`、document payload `f6eff86bea6a1d04bc43bfe8a532ff952f295c6aa2d1d89f6b40f6fe02dc91f9` 和独立 trust payload `624bb2b801a51e0fd19ae4d4583d77c6b6195355685b202b4c5ac3aa56d2cf8f` 为唯一前驱，不回写早期账本。

59 个 golden disposition 现在分为：

- 46 个普通完整上下文 HTTP 执行；
- 11 个带真实 PostgreSQL transaction abort 的完整上下文 HTTP 执行；
- 1 个 malformed expiry typed rejection；
- 1 个 aware expiry offset-provenance collapse。

57 个 HTTP case 均在安装完整 Spring Security/Servlet 生产过滤链的上下文中使用 MockMvc 执行，测试上下文连接真实 PostgreSQL 18.4 与 Redis 7.4.7，且没有 mocked application/auth port。其中 49 个到达 Controller、应用服务和业务 JDBC adapter；5 个 Web 302 与 3 个 API 401 按契约在业务层前终止，并证明业务 JDBC 未被调用。它们覆盖 Target Session、Flask Session exchange 与 Bearer，逐 case 固定 200×34、302×5、401×3、403×10、500×5，且 API/Web HTTP 分布为 43/14。SQL tracer 观察每条执行及 read-only 状态，验证九张相关表前后指纹一致、观测到的 write DML 与 schema mutation statement 均为 0；11 个故障均形成同连接 `42703 -> 25P02 -> rollback`，需要继续降级的查询只允许在回滚后由不同连接成功。额外 1 个 supplementary JUnit 单独证明 Flask Session 与权威 Target Session 均到达应用/JDBC，不计入 59 disposition，所以套件的 JUnit leaf 总数是 60。

该 successor 只声明 `all_59_target_dispositions_executed=true`，不声明 `full_target_parity_closed`。57 个 HTTP 使用 MockMvc，不是真实随机端口 Tomcat；本套件只在 PostgreSQL 18.4 执行全部 59 disposition，PG16.14/18.4 双版本仍由较窄 JDBC IT 绑定；malformed 与 aware 两个 typed 处置没有伪造 HTTP status，最终 parity 接受仍待评审。真实 Tomcat HEAD/Location/Vary/CORS/安全头/Request ID/全部限流头矩阵、Redis 连接拒绝/中断/同实例恢复、生产流量与切流均不在本节点授权范围。

本轮只有 `src/test`、测试 seed、证据与门禁变化，生产 build-context 仍为 `273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3`。固定 WORM 链禁止重复 build-context，因此不伪造第六份报告；target-execution contract 显式复用第五节点 `7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39`，并记录 `new_worm_report_created=false`、`production_build_context_unchanged=true`。

target-execution 合同与两份 bridge 在 `0531b3c9272f9743a374edcf5c8bbeb72643eb1b` 提交时是诚实的 bootstrap，而不是外部前驱已固定的独立信任根。合同文档记录两份 bridge 的物理 SHA，但 bridge-normalized trust payload 会把这两个 source hash 替换为固定 sentinel 以打破递归哈希环；该历史节点因此记录 `external_bridge_bytes_anchor_complete=false`、`route_promotion_blocked_by_bridge_bootstrap=true`。`0531b3c` 已提交并推送，后续 `6c1b03dd7fa9cde7a6dcdbf6b555452e9a6d9e53` anchor checkpoint 也已推送，并从 Git 固定 `0531b3c` 及其合同和两份 bridge 的精确字节。

因此 target-execution bootstrap 的“等待首次提交”动作已完成，但两条 GET 仍保持 pending，有效账本仍为 **11 migrated、600 pending、0 production cutover**。operator、schema/index、真实数据迁移、客户端、网关和 production cutover 继续禁止。

## User-counts HTTP target-execution post-push external anchor（predecessor）

`6c1b03d` anchor checkpoint 包含九个精确文件，其中包括由原始 60-leaf JUnit XML 归一化得到的 60/60 manifest；随后提交 `1dae013e11c76ad858d6695f166a32631eb1525e` 物化 post-push successor。当前 external anchor 固定 `1dae013` 的 commit/root tree/parent/Ti-Java subtree、6 added + 10 modified 的完整 16 文件 delta，以及这 16 项中上一节点六个自排除来源的精确 Git blob、SHA-256、mode 与字节数。target-execution bootstrap `0531b3c`、anchor checkpoint `6c1b03d` 和 post-push `1dae013` 均已推送到 `main`。

该合同的普通构建与加载不读取 `.git`，显式 Git replay 只允许固定的 `1dae013` 对象和 16 路径 allowlist；新节点不导入历史 bridge 或 Phase 2，也不把外锚节点加入固定五节点 WORM 链。上一 post-push 节点的六个自排除来源现已外部锚定；本节点自身六个控制面来源在该时点继续声明 `independently_signed=false`，不能自授权 typed parity、full target parity、route migration 或 production cutover。该六来源现已由下述 typed-normalization 节点通过固定提交 `c38defa703b358a280122a09019031c040c58ea7` 承接。

## User-counts HTTP typed-normalization successor（predecessor）

`P4C-LEARNING-013` 固定了 offset-aware 字符串进入生产 PostgreSQL `timestamp without time zone` 数据域的墙钟语义：字符串 `2026-07-17T13:00:00+08:00` 通过显式 String CAST 后规范化为 `LocalDateTime 2026-07-17T13:00:00`，来源 offset 被擦除，不按 instant 或 Session 时区换算。旧 SQLite/Python 夹具因 aware/naive datetime 比较产生的 500 不是 PostgreSQL 该列可保持的合法生产状态；目标在固定北京 12:00 语义下获得有效分享授权并返回 HTTP 200，数据为 `total=9`、`favorites=0`、`mistakes=0`，题型顺序与普通 future-share case 一致。

同一绿色 leaf 先让 PG16.14 与 18.4 在 `UTC`、`America/Los_Angeles` 两种 Session 时区下接收相同的 Java `String` bind，固定 `+08:00` 与 `-05:00` 均得到 `LocalDateTime 13:00`，并断言双版本结果一致。PG18.4/Redis 7.4.7 完整过滤链随后使用请求追踪前由 `CAST(? AS timestamp without time zone)` 创建的 share 行，不允许初始化 SQL 字面量冒充 JDBC bind。测试不 mock application、authentication port 或 limiter；它从真实 Flask Session exchange 得到 Target Session，再读取私有题库。请求区间固定 authority/bank/share/favorite/mistake/summary/tag SQL family 计数，观测写 DML、`users.last_active` DML 与 schema mutation 均为 0，九表指纹不变，三枚 HMAC 路由限流 key 均为 1。该 HTTP 证据仍是 MockMvc，不冒充随机端口 Tomcat 网络证据。

successor 只替换 aware case 的一个有效证明叶：malformed expiry 继续是 SQLSTATE `22007`、无 target HTTP 的唯一 `EXECUTED_TYPED_REJECTION`；aware case 从历史 `EXECUTED_TYPED_COLLAPSE` 改为 `EXECUTED_FULL_CONTEXT_HTTP`。因此有效 59-case 账本为 47 个普通完整上下文 HTTP、11 个 PostgreSQL abort HTTP 和 1 个 typed rejection，即 **58 HTTP + 1 typed rejection**；HTTP 状态为 200×35、302×5、401×3、403×10、500×5，业务 JDBC 50、前置终止 8、API/Web 44/14。历史报告 60 leaves 与新增报告 1 leaf 物理合计 61，但旧 aware leaf 被显式 supersede，逻辑选择仍为 59 disposition + 1 supplementary authentication leaf，共 60，不双计数。

该合同固定回放 `c38defa` 的 commit/root tree/parent/Ti-Java subtree 和完整 18 路径 delta，并把前一节点六个自排除来源变成外部 Git 事实；普通构建与加载仍不依赖 `.git`。typed-normalization 节点自身六个控制面来源已由下述固定外锚从 `b0861d61438f649ed48d5d5e6806e02c804fa2e4` 承接；这只关闭 bootstrap 来源的外锚缺口，不改变 `typed_parity_review_complete=false`、`full_target_parity_closed=false`、`route_migration_eligible=false`。生产源码、schema、OpenAPI、route delta、第五 WORM tip 和 build-context 均未改变，有效路由继续是 **11 migrated、600 pending、0 production cutover**。

## User-counts HTTP typed-normalization external anchor（predecessor）

固定外锚精确绑定 `b0861d61438f649ed48d5d5e6806e02c804fa2e4`、父提交 `c38defa703b358a280122a09019031c040c58ea7`、root tree、Ti-Java subtree、原始 delta SHA-256，以及 **26 个路径（12 added + 14 modified）** 的 mode、前后 blob OID、SHA-256 和字节数。26 路径覆盖 typed-normalization 合同、manifest、差异说明、Java/Python acceptance/parity、真实双 PostgreSQL/Redis IT 和固定 Phase 2 接线；其中上一节点六个自排除控制源共 `280664` 字节，现已成为外部 Git 事实。

普通 builder/load 仍完全 Gitless；显式 replay 只接受固定 `b0861d6`，不把 `HEAD`、工作树或 `origin/main` 当作验证权威。当前外锚合同、builder、Python/Java acceptance/parity 六个来源继续自排除、`independently_signed_provenance=false`、`current_anchor_source_bytes_external_git_anchor_complete=false`。WORM 仍只复用第五节点与 build-context `273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3`，不伪造第六份生产报告；路由保持 **11 migrated、600 pending、0 production cutover**。

## User-counts HTTP full-parity bootstrap（当前节点）

INT 从共同 BASE `765e4470f1ddb60f0ce6f23227d6303961f47fcf` 审查三条 Worker 分支，并只集成固定实现对象：PG `0f584743dbdc187b6bc6fc67899a2d6718cb13c8`、TOMCAT `cd7eba9bbee4edcb6a0e14fec5fdfdf613d2ea70`、REDIS `ad4d90b30cc5d244983fe759199f77ddeacdfc52`。三份 lane handoff 及其 tip 只用于 BASE、允许路径、真实性和中央零修改审计，handoff 文件没有进入 main。六个新增证据文件均由合同固定 SHA-256/字节数，未修改生产源码、共享安全配置、全局 OpenAPI、既有 route delta、data ownership、Compose、`server/pom.xml` 或 WORM。

PG IT 在 PostgreSQL 16.14/18.4 各自固定 backend PID、权威与业务 SQL family、`42703 -> 25P02 -> rollback -> 同 PID 成功重试` 以及九表前后指纹；真实 Tomcat IT 以网络 HttpClient、真实 PostgreSQL/Redis/Session/auth/limiter 覆盖 GET/HEAD 的 `200/302/400/401/403/404/429/500/503` 和完整响应头/零 HEAD body；Redis IT 以真实连接拒绝、已接连接中断、同 context/port 恢复、429 后自然恢复及两个独立 Spring/Tomcat/Lettuce 实例收敛闭环。INT 持有 `heavy-verify.lock` 串行执行三类定向验证，Failsafe 13/13；随后完整 `clean verify` 为 Surefire 709 + Failsafe 167，全部 0 failure/error/skip，总用时 `07:02 min`，Testcontainers 残留为 0。

追加合同 `personal-bank-user-counts-http-full-parity-contract.json` 因此只把 `pg16_pg18_termination_fingerprints_complete`、`real_tomcat_complete_response_header_matrix_complete`、`same_service_redis_outage_and_recovery_complete`、`full_target_parity_closed` 固定为 `true`。合同、builder、Python/Java acceptance/parity 六个 bootstrap 控制源仍自排除，等待下一提交以固定 Git 对象外锚；在此之前 `route_migration_eligible=false`，路由仍为 **11 migrated、600 pending、0 production cutover**。历史合同与 WORM 保持字节不可变；operator、schema/index、真实数据迁移、客户端、网关和 production cutover 继续禁止。
