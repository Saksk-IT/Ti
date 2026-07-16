# Ti-Java 重构进度

> 本文件是跨轮次、跨夜恢复工作的唯一进度入口。继续执行前，先核对本文件、当前 Git 状态和受保护工作区清单；事实以仓库当前内容和可复现验证结果为准。

## 当前阶段

- **阶段 4A：目录与公共题库（进行中）**；受保护科目目录与公共题库 7 条 GET 的 Java shadow 切片均已实现，题目类型与题量的 catalog 内部读取能力也已实现。两条后台题型 HTTP operation 仍由 `operations` 持有，两条题量 HTTP operation 延后由 Phase 4C 的 `learning` 组合；四条路由都保持 pending，全部保持 `production cutover=0`。下一项仍是公共题库剩余读取。
- 基线提交：旧 Ti `700006dfdfa063deb4387be572911e782bcea0d9`。
- 盘点日期：2026-07-16（Asia/Shanghai）。
- 题目类型元数据已提交并推送的绿色检查点：`1444814`（`feat(java): add question metadata catalog capability`）。其后的题量内部能力切片已完成提交前全部门禁；实际提交哈希以 Git 历史为准。
- 阶段 0、阶段 1、阶段 2 与阶段 3 均已通过各自结构化门禁、负向测试和独立审计；当前 Phase 4A 实现已在该检查点之后完成上述两个读取切片，但整个长期重构目标仍未完成。
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

## 阶段 2 已完成

- 创建独立 `server/`、Maven Wrapper 3.3.4，并固定 Java 25、Maven 3.9.16、Spring Boot 4.1.0、Spring MVC 与 Spring Modulith 2.1.0；依赖门禁拒绝 WebFlux、R2DBC、Flyway 和非稳定版本。
- 把阶段 1 机器合同落实为 11 个业务模块及 `sharedkernel`、`web`；真实 Modulith 校验、ArchUnit 边界、11 个独立模块上下文测试和故意非法依赖负例均通过。
- 建立 Request ID、统一成功/错误/分页合同、UTC/Jackson 3 序列化、默认拒绝安全策略、结构化脱敏日志、liveness/readiness、Micrometer 与内部 Prometheus 管理端口。
- 明确阶段 2 仍为 **0 条迁移路由、0 个公开业务操作**；11 个公开应用 API 只保留空边界，未根据名称虚构 DTO、方法或事件载荷。
- 建立 PostgreSQL 18.4/16.14 与 Redis 7.4.7 Testcontainers；Hibernate 仅 `validate`，最小 `subjects` 9 列只读探针及数据库 ACL 在关闭会话默认只读后仍拒绝 DML、DDL 与 TEMP DDL。
- 对显式授权的本地非生产参考库执行 schema-only 隔离恢复：PostgreSQL 18.4、70 表/617 列、Alembic `f5b6c7d8e9f0`；当前 Java build context 通过 Hibernate validate/readiness，生产数据库版本仍为 unknown，未创建 Flyway baseline。
- 建立固定 digest、非 root、只读根的 Java 镜像和独立 Compose；API/PG 使用专用宿主接入网与 internal backend，Redis 仅 internal backend，旧 Flask 入口、容器、卷和可写数据库均未接入。
- 原目录和仅复制 `Ti-Java/` 的临时目录均完成 `clean verify`：36 个单元/架构/模块测试 + 4 个 PostgreSQL/Redis 集成测试，0 failure/error/skip；独立抽取还通过静态门禁、Dockerfile check、镜像构建与 Compose 启动，结束后无临时资源残留。

## 阶段 3 已完成

- 保留 Phase 0 路由矩阵、Phase 1 OpenAPI 和 Phase 2 API 形状状态不变；新增 `phase3/route-parity-delta.csv`、有效物化视图和独立 OpenAPI 3.1.2 delta。有效状态为 611 个 operation 中 **2 migrated、609 pending、0 production cutover**，公开应用形状为 **2 个路由操作 + 5 个方法**；`migrated` 不冒充双运行时或生产切换。
- 实现公开无副作用 `GET /api/auth/login-methods`：目标 owner 依据 `system_config` 校正为 `operations`，保留旧信封、数据库/环境布尔解析和 phone → qr → password 默认模式；Testcontainers 集成测试核对 GET 前后 PostgreSQL/Redis 指纹。
- 实现 `POST /api/login` 的 Java 垂直切片：邮箱/手机号查找、重复邮箱 fail closed、锁定语义、Werkzeug scrypt/PBKDF2 严格验证、PBKDF2 向 Flask/Java 双兼容 `scrypt:32768:8:1` 的 compare-and-set 升级、Redis 服务端 Session、安全标量 serializer、旧 Cookie 清除、CSRF、安全相对 redirect和 KDF 并发预算。登录在 KDF 前使用 Redis Lua 的 global + HMAC-IP + HMAC-account 三维分钟桶；JSON 解析前以有界流读取真实请求体，超过 16 KiB 返回安全 413。
- 建立旧 HS256 JWT 与 Flask timed Session 的本进程严格格式验证、跨语言合成向量和 PostgreSQL 权威状态核对；`TargetSessionAuthenticationFilter` 在 kill switch 开启时让显式旧 Bearer 只认证当前请求且不创建、刷新或延长目标 Session。旧 Flask Cookie 在验签前经过 global/HMAC-IP 限流，验签和数据库权威核对后再以 HMAC credential marker 拒绝重放，并按 `identity_id + session_version` 最多允许 3 次兑换。密码登录与兑换共用每身份最多 3 个目标 Redis Session 的签发器，使用 immediate/on-set-attribute 持久化、最旧 Session 淘汰和位于 Spring Session 外层的链尾协调过滤器；remember Cookie 每次成功权威重授权后滑动刷新 7 天。权威源暂时不可用时返回 503 且保留既有 Session。kill switch 默认关闭，启用时强制未来且不超过 366 天的截止时间并记录指标，阶段 10 必须删除兼容 Secret/入口。
- 无既有 Session 时，`GET`/框架派生 `HEAD /api/csrf` 及所有 unsafe 方法在 CSRF 处理和匿名 Session 创建前统一经过 Redis global + HMAC-IP 限流；匿名 CSRF Session 默认只有 10 分钟。local Compose 与 Phase 3 Redis Testcontainers 使用 `noeviction`；生产必须配置同策略，并通过 Secret/configtree 提供至少 32 字节 HMAC key，Redis/Secret 不可用均 fail closed。
- 在 `infra/phase3/` 建立 local/test `READ_COMPARE` 与离线 `ISOLATED_WRITE_COMPARE`，只允许独立回环/资源、串行外部请求和 operation 精确规范化；报告不保存原始正文、凭据或差异原值。p3-009 冷读只因旧 Flask 首次创建 1 个明确排除的 Flask-Limiter 可重建运行时 Key 而预期失败，不存在业务事实或持久文件副作用；预热后暖读报告零差异通过。
- 在 `infra/phase3/topology/` 建立两套 API/PG/Redis/网络/卷的 stop → snapshot → fresh restore → start 与反向新 generation rollback 状态机。p3-009 使用固定 legacy `sha256:324b50f5ac0b5daa4d0e96cd6c495221e241b4fb0df90efe4de94a73387fb1b4` 和 Java `sha256:1dfca1d79f5b6fe8fa40ec9958028f14ee6c68db5371ac6c331231bf6a4c6077`，真实完成 `CUTOVER initial`、同快照读/写比较与 `ROLLBACK rb001`；来源先停、目标新卷恢复，全程没有共享写目标或双写。
- 公开 PBKDF2 夹具已由 Java 实际登录升级为精确 Werkzeug `scrypt:32768:8:1`，`session_version` 与 `last_active` 不变；固定 Flask/Werkzeug 3.1.4 在 rollback 后接受目标 hash 且不改写。该证据不推断生产/历史密码前缀分布。Phase 3 认证兼容清单、批准差异、双栈证据等级、route/OpenAPI delta 已同步；旧凭据 kill switch 的独立 HTTP 证据和首个受保护路由权限矩阵保留为后续受保护垂直切片与阶段 10 的明确边界。
- 最终 WORM 使用临时生成且只读 configtree 挂载的登录限流 HMAC Secret，通过 PostgreSQL 18.4、70 表/617 列的 schema-only 隔离恢复、ACL、Hibernate `validate` 和 readiness；临时 Secret、容器和恢复数据均已清理。
- 仅复制当前 `Ti-Java/` 的独立目录已通过 Phase 1、Phase 2/3 静态门禁、Phase 3 数据面、完整 Maven 208+22、镜像构建、Compose 健康检查和运行态 bind source 审计。Docker Desktop `/host_mnt` 前缀按仓库现有守卫规则等价归一化后，所有挂载均位于独立副本内且不引用原仓库；临时目录、容器、网络和卷无残留。

## 阶段 4A：科目目录、公共题库、题目类型与题量元数据

- 已把 `GET /api/quiz/subjects` 与 `GET /api/quiz/subjects/meta` 作为同一 catalog 垂直切片迁入 Java；catalog 只通过 identity 的 `SubjectAccessPolicyApi` 获取当前身份、管理员和受限科目决定，不共享 Entity，也不跨模块直查身份表。
- 已保存 7 组非空、脱敏、可确定重捕的科目旧栈 golden，覆盖普通用户、管理员、受限科目、空目录与两个响应形状；旧栈捕获和 Java 集成测试均证明业务数据库无写入。Java 明确采用每次请求 fresh read，不引入应用数据缓存。
- 首个受保护路由权限矩阵已覆盖旧 Bearer、首次 Flask Session 兑换与目标 Session。三类凭据的正常 HTTP 请求均固定为 3 条 SELECT（1 条 Session authority、1 条 identity 可见性、1 条 catalog 聚合），业务 use case 自身为 2 条 SELECT，无 N+1。
- 已实现科目路由专用 Redis 分钟/小时限流：本地/测试使用基数，生产倍率 100；身份限流键使用独立域分隔的 HMAC-SHA256 伪名，不保存原始身份 ID。Redis 或 Secret 不可用时 fail closed 503，超过额度返回带 `Retry-After` 的 429。
- Security、限流和 Controller 共用严格 RFC 3986 unreserved 路径解析器；真实 MockMvc 已证明单层编码合法路径受保护，保留字符、错误编码和双重编码不能绕过认证或落入错误响应形状。
- PostgreSQL 16.14 与 18.4 的科目兼容测试均通过；5,000 科目、50,000 题目、50,000 限制关系的查询计划已冻结，黄金响应、查询预算、OpenAPI、route delta、data ownership delta 与批准差异由机器合同互相校验。
- 已实现公共题库 search/list、summary、hot、boards、detail、card 共 7 条匿名或可选身份 GET。固定旧提交 `700006dfdfa063deb4387be572911e782bcea0d9` 的完整应用归档包含 46 个 case，覆盖 Unicode `Nd`（含阿拉伯-印度数字和全角数字）、任意精度路径/查询整数及错误形状；归档 SHA-256 为 `a63240ac2d22b0faff6daa143782eaa748bb54cda60b6c7ec9843a959eb486b5`。
- Java GET 只读取一次后台事务原子发布的 complete snapshot，不继承旧 GET 的惰性刷新写入。`<= 300s` 为 fresh，`300–900s` 服务最后完整快照并记录 stale，`> 900s`、冷启动或结构不一致均稳定 503 且 readiness fail closed。
- Snapshot maintenance 已在 PostgreSQL 16.14/18.4 证明失败回滚保留旧 complete、发布原子性和事务级 advisory lock 单写者；Redis 锁仅作短期协调，已证明真实过期后新 owner 接管，旧 token 不能删除新 token。刷新 Redis 不可用时降级到 PostgreSQL 最终锁，而不是放弃单写约束。
- 精确运行时 SQL 在 PostgreSQL 18.4 的 50,000 条 metrics、100,000 条 viewer state 合成夹具上捕获 7 条查询，无 N+1；计划证据 SHA-256 为 `570e471e85374f32f3d50c33b9b4d199a3230f17c2893c37a2fcf7469e1f2476`。该证据是观察结果，不是生产延迟 SLA。
- 公共题库 HTTP CatalogIT 7/7、Unicode/控制器/限流/黄金定向 24/24、刷新 Coordinator 6/6、Redis 3/3、PostgreSQL 16/18 maintenance 2/2 均通过；本切片后的完整 `clean verify` 为 323 个 surefire + 44 个 failsafe，0 failure/error/skip。
- 已从固定旧提交完整 `app/` 归档捕获 22 个后台题型双路由 case，覆盖 full admin、科目管理员、普通用户、匿名、Bearer-only、Session+Bearer、空表、Unicode 空白、别名/未知值以及 HTML/JSON 数据库故障。文件 SHA-256 为 `928e278edb35043126628c1050280c4792142c38088d47fefa86a12d401d8d6b`，所有 case 的 `questions` 全行指纹均保持不变。
- 已新增 HTTP-neutral 的 `QuestionMetadataApplicationApi#questionTypes`：catalog 只执行一条原始 `SELECT DISTINCT questions.type`，防御性排除 NULL，但保留空串和纯空白供未来两条路径分别投影；异常不在 catalog 中吞掉。PostgreSQL 16.14/18.4 兼容测试均通过。
- 精确 Java 运行时 SQL 在 PostgreSQL 18.4 的 50,000 题目夹具上执行一次、扫描 `questions` 一次、返回 12 个原始值且无 N+1；计划证据 SHA-256 为 `28f7221cb09fbc1f23ed1a2c92acf77e283d38874199b22465868a5f43f23853`。没有凭合成证据新增生产 `type` 单列索引。
- `GET /admin/api/types` 与 `GET /admin/types` 在冻结矩阵中仍是 `operations,pending`；route delta、有效路由状态和 Phase 4A OpenAPI 均未加入它们。公开应用方法数从 12 增为 13，但 migrated route 仍为 11。
- 已审计 `GET /api/questions/count` 与 `GET /api/quiz/questions/count` 的共用 handler、注册顺序、Web/小程序调用方、条件认证、Redis 缓存/限流和标签惰性迁移。完整用例读取 catalog、identity 与 learning 三个 owner，已接受 DAG 只允许由 `learning` 调用 `catalog::api`/`identity::api`，因此冻结矩阵中的 catalog 目标仅作为历史基线保留，两个 HTTP operation 继续 pending。
- 已新增 HTTP-neutral 的 `QuestionMetadataApplicationApi#countQuestions`。catalog 只读 `questions/subjects`，以独立 assignment scope 区分匿名 null 科目与认证现存科目要求；精确 subject/type、受限科目和候选题 ID 均通过 bind 参数表达。显式空候选返回 0 且不调用 JDBC，非空候选去重排序后以单个 PostgreSQL `bigint[]` + `ANY` 查询，不展开动态 `IN`、不分批、不创建 TEMP 状态。
- 题量内部能力把收藏、错题、用户标签、`mode/source/tag`、HTTP 鉴权/信封、响应缓存和 60/minute + 600/hour 限流留在 Phase 4C；本切片不读取 `favorites/mistakes/user_progress/user_question_tag_items/users/user_subjects`，不复制旧 GET 的 DDL/DML，也不写 route/OpenAPI/data ownership delta。公开应用方法数从 13 增为 14，migrated route 仍为 11。
- 已从固定旧提交完整 `app/` 归档捕获 36 个题量双路由 case，文件 SHA-256 为 `8da18675ed9f2c38fdf4444606ecbd1b465fd08e8084829b6d20314271c62b00`，case payload SHA-256 为 `db02705cf8de357398c888f1575cd591d7091324c23a409b48ab1f3a6efb397d`。所有 case 的 8 张业务表指纹保持不变；旧标签回退在固定 SQLAlchemy 栈下只证明 DDL 被尝试而迁移 DML 未到达，Phase 4C 不得把它误写为正向惰性迁移证据。
- Java 导出的 5 个题量 SQL 变体已在 PostgreSQL 18.4 的 50,000/150,000 题目夹具上形成 7 个观测；65,536/100,000 候选均为一个 `bigint[]` bind，statement=1、TEMP=0、关系仅 `questions/subjects`。计划文件 SHA-256 为 `d1958ab2b471f5454614c20018e85840aed82d68ddea6575efe3cc33132161db`，runtime manifest SHA-256 为 `4e49b6aa19f6d0d5370b1be3ff5fa4ac00f683c8a7a537e455d112db155cca7c`。
- 题量切片完整 `clean verify` 为 346 个 surefire + 48 个 failsafe，0 failure/error/skip；WORM 绑定 build-context SHA-256 `cc9bed50c29c379b6e2183b66e82f5c042c72ad934bfe3391c503639f3d9a9d7`，通过 PostgreSQL 18.4、70 表/617 列、只读 ACL、Hibernate `validate`、readiness 与 Phase 2 静态门禁，报告 SHA-256 为 `e1b5d3a7a66864c31d0b6fb9d2e5d0494b58338d97f446b751d20acab0853842`。
- 仅复制 1,126 个受控文件、无符号链接和 ignored 本地配置的独立 `Ti-Java/` 副本已通过 Phase 1、Phase 2/3 静态门禁、346+48 Maven、独立 PostgreSQL/Redis 数据面、镜像构建、Compose readiness 和 bind-source 审计；临时副本、Testcontainers、容器、网络和卷均已清理。固定旧提交归档重捕仍只在完整源仓库执行，不构成 Java 运行时父目录依赖。
- 有效路由状态现为 **11 migrated、600 pending、0 production cutover**；有效资源为 **159 个且 159 个均有唯一 owner**。`migrated` 只表示 Java 实现与兼容证据已物化，旧 Flask 仍是生产 owner，整个长期重构目标仍未完成。

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
| `./infra/phase2/verify-in-maven-container.sh clean verify` | 208 个 surefire + 22 个 failsafe，0 failure/error/skip；JAR 撤销 class 门禁通过 | 绿色；固定 Java 25/Maven 3.9.16，真实 PG18/PG16/Redis Testcontainers |
| `./infra/phase2/verify-static.sh` | 通过 | 绿色；固定 digest、Compose 拓扑、只读 ACL、真实结构报告与 Java build-context 新鲜度闭环 |
| `./infra/phase2/verify-in-maven-container.sh -Dtest=io.saksk.ti.architecture.ModuleContractParityTest test` | 5/5 通过，0 failure/error/skip | 绿色；Phase 3 的 2 个路由操作/5 个公开方法、冻结 SHA、route/OpenAPI delta 与 2 migrated/609 pending/0 cutover 物化一致 |
| `npx --yes @redocly/cli@2.39.0 lint openapi/phase3-authentication.openapi.json --extends=minimal` | OpenAPI valid，0 error、0 warning | 绿色；两条 Phase 3 operation 的自包含 OAS 3.1.2 delta 引用闭环 |
| `./infra/phase3/verify-static.sh` | 29/29 通过（READ_COMPARE 15 + ISOLATED_WRITE_COMPARE 14） | 绿色；回环/隔离/副作用/规范化/脱敏和串行写证据正反向门禁 |
| `./infra/phase3/topology/verify-static.sh` | 59/59 通过（topology 24 + auditor 15 + write capture 20） | 绿色；隔离 Compose、snapshot、单写者状态机、运行态审计和写证据采集门禁 |
| p3-009 `CUTOVER initial` | 报告 SHA-256 `ece1199c3e0bd3ca90df4756cc6709c1d211e03a621d2dce6cad5e5ebcf89091` | 绿色；来源先停、目标新卷、无双写，快照 ID `auth-parity-p3-009-cutover-initial` |
| p3-009 冷/暖 `READ_COMPARE` | 冷报告 `d733dc7f62c7b86dd185d0f2c731069cad6a2d2b82926d346ef2fd4ff8c275c2` 仅排除的 Flask-Limiter Key 计数差异；暖报告 `37128ff0786211474f84f60a131934ebcbaac4c8cc0fa02bd5299f46a19590aa` 零差异 | C 级本地证据；冷变化无业务/持久副作用，暖双侧 before=after |
| p3-009 `ISOLATED_WRITE_COMPARE` | 报告 SHA-256 `3dc21a524bfae335d763ac49d4f480962c536ec5c99af021ac27b583ae9c40f5`，差异数 0 | C 级本地证据；同快照、独立资源、串行各写一次，不是双写 |
| p3-009 `ROLLBACK rb001` + PBKDF2 实际升级 | 报告 SHA-256 `3fca94f6841ade5a26f0f53669026a04ee7c5293616a5754ab20c745d9c6fc1a`；固定 Flask/Werkzeug 3.1.4 接受 Java 目标 scrypt 且不改写 | 绿色公开夹具回滚证据；不推断生产密码前缀分布 |
| `verify-local-reference-wormhole.sh --source-container ti-postgres-1 ...` | 最终通过 PG18.4、70 表/617 列的 schema-only 隔离恢复、ACL、Hibernate `validate` 和 readiness；登录限流 HMAC Secret 临时生成并只读挂载，运行后清理 | 绿色；当前 `local-reference-verification.json` 固定 70 表/617 列及 build-context 摘要，不保存结构 dump |
| Phase 2 Compose 空卷构建与运行 | live/readiness 200，未声明路由 401，业务端口 metrics 404；内部 9090 有 JVM 指标；PG 25432 可达，Redis/9090 无宿主映射 | 绿色；UID 10001、只读根、cap drop、Secret 不进 inspect，API 重启后恢复健康 |
| 仅复制 `Ti-Java/` 后的完整验收 | 当前副本通过 Phase 1、Phase 2/3 静态门禁、Phase 3 数据面、208+22 Maven、镜像构建、独立 Compose 健康检查与 bind source 审计 | 绿色；不读取父目录或原仓库，Docker Desktop `/host_mnt` 映射已等价核验，清理后无临时目录/容器/网络/卷 |
| wormhole 失败路径 | 报告越界被拒绝且原文件不变；源容器命名冲突被拒绝且源仍运行；失败不覆盖既有报告 | 绿色；源只读与清理边界由负向执行证明 |
| `npx --yes @redocly/cli@2.39.0 lint ... --extends=minimal` | OpenAPI valid，0 error，48 warnings | 绿色；30 组旧路径歧义、4 个尾斜杠和 14 个预声明组件均已结构化解释 |
| Phase 4A 科目目录检查点 `./infra/phase2/verify-in-maven-container.sh clean verify` | 231 个 surefire + 28 个 failsafe，0 failure/error/skip | 绿色；这是公共题库切片之前的已保存全量结果，不作为本轮新的最终 `clean verify` 计数 |
| Phase 4A 科目 golden 确定性重捕 | 7/7 cases，逐字节一致，SHA-256 `54a7441ed7b7b9a0b49d60bc84d6a06f0387a3eee009370960ac65a19293a35f` | 绿色；旧栈临时数据库无业务副作用 |
| Phase 4A 科目查询计划捕获 | PG18.4；5,000 科目、50,000 题目、50,000 限制关系；SHA-256 `530409a4b1ffd8a9159e3241dce0997c368371aeba7c0c2c06a39f240f8059ea` | 绿色；业务 2 SELECT、正常 HTTP 3 SELECT，无 N+1 |
| `npx --yes @redocly/cli@2.39.0 lint openapi/phase4a-subject-directory.openapi.json --extends=minimal` | OpenAPI valid，0 error，0 warning | 绿色；429/503 双响应信封与动态响应头均显式建模 |
| Phase 4A 公共题库固定提交完整应用归档 | 46 cases；SHA-256 `a63240ac2d22b0faff6daa143782eaa748bb54cda60b6c7ec9843a959eb486b5` | 绿色；固定旧提交 `700006dfdfa063deb4387be572911e782bcea0d9`，覆盖 Unicode Nd、任意精度参数和批准错误形状 |
| Phase 4A 公共题库精确运行时 SQL 计划 | PG18.4；50,000 metrics、100,000 viewer state、7 queries；SHA-256 `570e471e85374f32f3d50c33b9b4d199a3230f17c2893c37a2fcf7469e1f2476` | 绿色；运行时 SQL 固定预算，无 N+1；不是生产延迟 SLA |
| Phase 4A 公共题库 HTTP 与兼容定向 | CatalogIT 7/7；Unicode/控制器/限流/黄金 24/24 | 绿色；7 条 GET 的身份、路径、限流、响应、300/900 freshness、fail-closed readiness 与 golden 定向通过 |
| Phase 4A 公共题库 snapshot P1 定向 | Coordinator 6/6；Redis 3/3；PG16/PG18 maintenance 2/2 | 绿色；覆盖失败回滚、原子发布、最终单写者锁和 Redis 过期接管 |
| Phase 4A 公共题库切片 `./infra/phase2/verify-in-maven-container.sh clean verify` | 323 个 surefire + 44 个 failsafe，0 failure/error/skip；总用时 48.796s | 绿色；固定 Java 25/Maven 3.9.16，包含 PG18/PG16/Redis Testcontainers |
| Phase 4A 公共题库切片 WORM + Phase 2 静态门禁 | PG18.4、70 表/617 列、Hibernate `validate`、readiness 通过；当前 build-context 摘要记录于结构化报告 | 绿色；证据不保存 schema dump/DSN/Secret，临时资源已清理 |
| Phase 4A 公共题库切片独立抽取 | 1,091 个受控源文件；Phase 1 聚合门禁、Phase 2/3 静态门禁、323+44 Maven、独立 PostgreSQL/Redis 数据面全绿 | 绿色；副本不含 ignored 产物/本地配置，无符号链接或父目录源码读取；临时副本、容器和专用 Maven 缓存卷无残留 |
| Phase 4A 题型双路由固定提交 golden | 22 cases；逐字节重复捕获一致；SHA-256 `928e278edb35043126628c1050280c4792142c38088d47fefa86a12d401d8d6b` | 绿色；覆盖角色/Bearer 分流、Unicode 空白、空表、别名/未知值、HTML/JSON 故障，questions 指纹全部不变 |
| Phase 4A 题型精确运行时 SQL 计划 | PG18.4；5,000 科目、50,000 题目、12 个 raw distinct；SHA-256 `28f7221cb09fbc1f23ed1a2c92acf77e283d38874199b22465868a5f43f23853` | 绿色；1 query、1 次 questions 扫描、无 N+1；三次捕获字节一致，不是生产延迟 SLA |
| Phase 4A 题型 Java 定向 | 核心 unit/SQL/manifest 5/5；PG16.14/PG18.4 compatibility 2/2；模块/契约定向 16/16 | 绿色；只接受 catalog 内部能力，两条 operations HTTP 路由继续 pending |
| Phase 4A 题型切片 `./infra/phase2/verify-in-maven-container.sh clean verify` | 329 个 surefire + 46 个 failsafe，0 failure/error/skip | 绿色；固定 Java 25/Maven 3.9.16，包含 PG18/PG16/Redis Testcontainers；最终独立副本构建总用时 49.930s |
| Phase 4A 题型切片 WORM + Phase 2 静态门禁 | PG18.4、70 表/617 列、只读 ACL、Hibernate `validate`、readiness；build-context SHA-256 `fdc94000537d266595a22082ee28df0e7f04414855d6f4b36ba2125707153a8d` | 绿色；报告 SHA-256 `02456e5a803b1fe6093390334b7eb94f35ed73513f219509aadfac5edfe64e7f`，临时 schema、Secret、容器、网络、卷和镜像已清理 |
| Phase 4A 题型切片独立抽取 | 1,109 个受控源文件；Phase 1、Phase 2/3 静态门禁、329+46 Maven、独立 PostgreSQL/Redis 数据面全绿 | 绿色；副本不含 ignored 产物/本地配置，无符号链接或父目录源码读取；临时副本、容器和专用 Maven 缓存卷无残留 |
| Phase 4A 题量双路由固定提交 golden | 36 cases；逐字节重复捕获一致；SHA-256 `8da18675ed9f2c38fdf4444606ecbd1b465fd08e8084829b6d20314271c62b00` | 绿色；覆盖双路由认证/参数优先级、catalog 与 learning 选择分界、缓存/限流/DDL/故障副作用，8 张业务表指纹不变 |
| Phase 4A 题量精确运行时 SQL 计划 | PG18.4；50,000/150,000 题目、5 variants、7 observations；SHA-256 `d1958ab2b471f5454614c20018e85840aed82d68ddea6575efe3cc33132161db` | 绿色；65,536/100,000 候选均为单个 `bigint[]` bind，1 statement、TEMP=0、无 N+1，不是生产延迟 SLA |
| Phase 4A 题量 Java/证据定向 | Java 22/22 + 模块合同 8/8；PG16.14/PG18.4 compatibility 2/2；Python 捕获/计划工具 16/16 | 绿色；catalog 只读 `questions/subjects`，两条 learning HTTP 路由继续 pending |
| Phase 4A 题量切片 `./infra/phase2/verify-in-maven-container.sh clean verify` | 346 个 surefire + 48 个 failsafe，0 failure/error/skip；源目录总用时 01:02 | 绿色；固定 Java 25/Maven 3.9.16，包含 PG18/PG16/Redis Testcontainers；独立副本同计数通过 |
| Phase 4A 题量切片 WORM + Phase 2 静态门禁 | PG18.4、70 表/617 列、只读 ACL、Hibernate `validate`、readiness；build-context SHA-256 `cc9bed50c29c379b6e2183b66e82f5c042c72ad934bfe3391c503639f3d9a9d7` | 绿色；报告 SHA-256 `e1b5d3a7a66864c31d0b6fb9d2e5d0494b58338d97f446b751d20acab0853842`，临时 schema、Secret、容器、网络、卷和镜像已清理 |
| Phase 4A 题量切片独立抽取 | 1,126 个受控文件；Phase 1、Phase 2/3 静态门禁、346+48 Maven、独立 PostgreSQL/Redis 数据面、镜像构建、Compose readiness 与 bind-source 审计全绿 | 绿色；副本不含 ignored 产物/本地配置或符号链接，不读取原仓库运行代码；固定旧提交归档重捕是源仓库测试期合同步骤；临时资源无残留 |
| Phase 4A 科目目录检查点独立抽取 | 1,251 个文件；Phase 1、Phase 2/3 静态门禁、231+28 Maven 全绿 | 绿色；这是科目目录检查点证据；无符号链接、无父目录运行时读取，临时副本和容器无残留 |
| Phase 4A 旧栈回归 | 374 个 Python 文件 compileall；654 passed、2 个登记失败、3 skipped；两套小程序各 36/36 | 绿色；登记基线和 warning 窗口保持一致 |

上表已记录题量内部能力切片真实运行的全量、WORM、静态、独立抽取及定向结果；题型、公共题库与更早历史检查点均单独标明，不与当前切片混用。

完整命令、两个 pytest 失败说明及初步性能数字见 `07-baseline-results.md`。

## 尚未迁移的路由与数据

- **路由：** Phase 0 冻结矩阵仍保存 592 条规则/611 个 operation 的历史 `pending` 事实；Phase 3 与 Phase 4A delta 已把认证 2 条、受保护科目目录 2 条和公共题库 GET 7 条物化为 **11 个 `migrated`**，其余 **600 个 operation 仍 pending**。生产切换数为 0，旧 Flask 仍是当前运行所有者。
- **表与非表资源：** 当前有效资源为 **159 个且全部唯一 owner**。Phase 4A 新增的科目/公共题库限流 Redis Key、公共题库 snapshot/viewer 投影控制表和刷新锁均归 catalog，但只是可重建辅助状态且 `production_cutover=false`；旧业务事实表未因 shadow 读取切片而转移生产所有权，仍未建立 Flyway 正式 baseline。
- **客户端：** Web 仍是 Jinja/原生 JavaScript，小程序当前只是固定来源副本；Vue、OpenAPI 生成客户端和适配尚未开始。
- **部署：** Java 骨架、独立 PostgreSQL/Redis 测试设施及 Phase 3 本地对比/切换工具已建立；p3-009 已对固定本地镜像完成真实恢复、切换和回滚。生产 Compose、网关入口和整体生产切换仍未实施；Flask 与 Java 仍不得同时写同一数据库。

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
- 生产 PostgreSQL 版本与完整生产 schema 仍为 unknown；阶段 2 的 70 表/617 列证据只来自显式授权的本地开发参考，不能替代阶段 8 的生产备份恢复与 Flyway baseline 演练。
- Mockito/Byte Buddy 在 Java 25 测试中仍发出动态 attach 警告；JDK 默认禁用动态 agent 前须改为显式 `-javaagent`，不得仅隐藏警告。Maven/Jansi 与 Testcontainers/JNA 的 native access 警告也需随工具链升级收口。
- identity 在冻结路由矩阵中有 69 行、Phase 1 OpenAPI 合并后 68 个 operation；Phase 3 只实现 `POST /api/login`，并把由 `system_config` 提供的 `GET /api/auth/login-methods` owner 校正到 operations。冻结统计不回写，剩余认证 operation 仍不得用桩接口冒充完成。
- 目前只对获准本地副本观察到 Werkzeug scrypt 哈希，生产/历史 PBKDF2 等前缀清单未知；阶段 3 只能支持脱敏清单和固定向量证明存在的格式，不能按猜测扩大接受面。
- `users.openid` 旧结构只有普通索引而无唯一约束；阶段 8 正式迁移前必须检测重复并拒绝并发冲突，不能宣称数据库已经保证微信身份唯一。
- 正式性能基线尚未完成独立数据、独立 Redis、SQL 数、启动耗时和页面指标采集；当前小样本不可作为验收门槛。
- `page/partial` 与动态模板映射是明确标注的迁移启发式，不能在阶段 6 直接当作分支级精确契约；须结合真实请求与页面测试收口。
- p3-009 已生成真实 `GET /api/auth/login-methods` 冷/暖 Flask/Java `READ_COMPARE` 和 `POST /api/login` 同源双隔离库终态报告；结论只覆盖这两条 operation。冷请求新增的 1 个排除 Flask-Limiter Key 必须继续按“无业务/持久副作用的可重建运行态变化”记账，不能篡改成绝对零 Redis 写入。
- 旧 JWT 当前请求认证、Flask Session 换发与目标 Session 每请求 PostgreSQL authority 已接入 Security filter；受保护科目目录已补齐角色、锁定、session version 与三类凭据 HTTP 权限矩阵。legacy bean 仍默认关闭，生产启用需独立批准，阶段 10 必须删除兼容 Secret、兑换入口与 kill switch。
- 旧 `POST /api/login` 没有持久失败次数/自动锁定写入；Java 只尊重既有 `is_locked` 并使用限流/KDF 容量控制，不应在没有 schema 与产品证据时虚构失败计数。
- 过渡密码目标已固定为 Flask/Java 都接受的 Werkzeug `scrypt:32768:8:1`，旧栈永久退出前禁止写入 Spring 专有格式。公开 PBKDF2 夹具已由 Java 实际升级，并在 `ROLLBACK rb001` 后由固定 Flask/Werkzeug 3.1.4 登录接受且保持 hash 不变；生产/历史前缀清单仍 unknown，不能由公开夹具外推。
- 公共题库 snapshot 已证明本地原子性、新鲜度和刷新协调，但旧 Flask 写路径尚未向 Java 发布题库撤回、权限收紧、板块变化等即时失效事件，生产刷新调度、真实数据、Redis `noeviction`、HMAC Secret 和入口切换也未获批；因此 7 条 GET 必须保持 `production cutover=0`。

## 下一项具体动作

1. 继续盘点 Phase 4A 公共题库剩余读取的真实 Flask 路由选择、注册顺序、调用方和数据库访问；从固定提交重捕非空、脱敏 golden 后再决定精确兼容 operation。
2. 在 Phase 4C 由 `learning` 完整迁移题量双路由与 `GET /api/quiz/subjects/{subject}/info` 的跨 `catalog`、`identity`、`learning` 组合；复用 catalog 题量原语，禁止 catalog 直查作答、错题、收藏或私有标签事实。题量切片必须先显式迁移旧 `question_tags_v1`，再批准移除 GET 内 DDL/DML、缓存和故障策略差异。
3. 两条后台题型 HTTP operation 延后到 4H；实现前必须正式决定并机器化 HTTP owner 的依赖方向，再由适配层复现 Python Unicode whitespace、角色/Bearer 分流及 modern/legacy 不同故障信封。当前内部 API 不授权 route/OpenAPI delta。
4. 公共题库生产 Redis、HMAC Secret、真实数据、刷新调度、即时撤回事件桥接和入口切换仍需另行获批；本地 shadow 证据不授权生产操作。
5. 后续每个切片都必须重新执行并记录与其风险相称的全量静态、契约、Maven、WORM 和独立抽取门禁；不得复用本轮 329+46 或 build-context 哈希冒充新切片证据。
