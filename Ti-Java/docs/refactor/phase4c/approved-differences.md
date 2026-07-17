# Phase 4C 已批准差异：learning 组合与个人题库标签迁移

## P4C-LEARNING-001：user-counts GET 不再执行标签 DDL/DML

- **旧行为意图：** 非空且非精确小写 `all` 的 tag 过滤会在请求线程尝试创建
  `user_question_tag_items` 及两个索引；目标 scope 为空时再读取
  `user_progress.bank_<bank_id>_tags`，尝试删除、重建并提交规范化行。
- **固定旧栈观察：** SQLAlchemy 2.0.51 下 raw string/qmark 参数在游标执行前失败，
  PostgreSQL 也不支持 `INSERT OR IGNORE`；legacy-only golden 因而返回全零，迁移 commit
  没有到达。该观察不能冒充成功迁移。
- **Java 行为：** HTTP GET 永远只读已规范化的 learning-owned 标签事实，不建表、不建索引、
  不回读兼容 JSON、不提交迁移。表或必要结构缺失时部署/readiness 失败，禁止请求自愈。
- **迁移替代：** compatibility namespace 只允许由显式 operator-only 任务迁移；默认 dry-run，
  apply 前必须完成全局 preflight。生产实现须在 dedicated connection 上取得 session-level advisory
  lock，并让该锁覆盖完整 preflight 与 apply；窗口内冻结 legacy source、normalized target 以及
  bank/question membership 写入，或捕获可比较的 version/digest 并在 apply 前复核。逐来源行仍需
  加锁，并在独立事务内只执行 `INSERT ... ON CONFLICT DO NOTHING`。由于源数据保留，operator
  还必须用持久 migration ledger/version 或等价 tombstone 区分“从未迁移”与“迁移后用户清空目标”；
  否则目标清空后重跑会复活旧标签。目标仍存在时的紧邻第二遍必须零 DML。
- **兼容输入边界：** 旧 JSON-array-string 与 CSV 语义仅在能够无损解析、规范化和复现时支持。
  单个 tag 保持旧 `normalize_tags` 的 20 Unicode code point 截断语义；不同原值在清洗或截断后
  碰撞、ID 规范化冲突、raw compatibility 非法形态，以及语义可识别但无法无损复现的形态都是
  blocker，禁止任意猜测或静默合并。
- **批准理由：** GET 不能拥有 schema 和迁移副作用；固定旧运行时本来也无法可靠完成该迁移。
  把错误的“请求时尽力迁移”改为可审计、可回滚、可阻断切流的显式步骤，才能保护现有数据。
- **切流门禁：** unresolved、conflict、orphan、invalid disposition 必须为零或有逐项批准；全局锁、
  写冻结或 version/digest 复核也必须闭合。当前 operator 实现和全局 preflight 证据均未闭合，
  schema/index 变更、真实数据 apply、operator 执行与 HTTP 切流均未获授权。

## P4C-LEARNING-002：可选统计采用独立本地事务实现字段级 fail-soft

- **旧行为意图：** total/access 失败向外传播；favorites 失败只回退 0，mistakes 失败只回退 0，
  types 失败只回退空列表。
- **PostgreSQL 实际边界：** 同一事务中的首个 SQL 错误会使后续语句进入 `25P02`，单纯
  `try/catch` 会把一个可选字段故障扩散到后续字段。
- **Java 行为：** access 与 total 保持硬失败；favorites、mistakes、types 的 learning 读取和
  personalbank 事实查询各自使用干净的模块本地只读事务。一个可选阶段失败只触发该阶段回退，
  后续阶段继续执行；禁止跨模块数据库事务。
- **批准理由：** 这实现了旧代码明确表达的字段级降级意图，同时消除 PostgreSQL poisoned
  transaction 的偶然级联。PG16/18 必须覆盖失败、回滚与后续可读性。
- **保持不变：** 四阶段顺序、source 为 favorites/mistakes 时的严格 total、types 映射、
  计数和 shuffle 语义保持 golden 兼容。

## P4C-LEARNING-003：非法 compatibility 数据显式阻断，不再静默吞弃

- **旧行为：** 非法 JSON、非法字段、题目 ID 解析失败和迁移异常多由宽泛异常捕获吞掉，
  tag 过滤随后表现为全零。
- **Java 迁移行为：** dry-run 对 raw compatibility 非法形态、非法 root/字段、规范化 ID 冲突、
  截断冲突、孤儿 bank/question 和目标分歧生成确定性 disposition；apply 不删除源、不自动 merge、
  不静默丢弃，任一未处置项阻断本次 run 和后续切流。
- **旧格式支持边界：** JSON-array-string 与 CSV 语义只有在能够无损还原题目 ID、标签、顺序无关
  集合语义和目标行时才可迁移；即使能识别旧格式，只要无法无损复现，仍必须报告 blocker。
- **目标优先：** 目标 scope 已有任意行时保持旧“目标整体优先”语义并零写入；源派生集合不是
  目标子集时报告 conflict，不复活用户已经删除或修改的标签。
- **批准理由：** 数据迁移的异常不能伪装成空业务结果。显式报告让人工修复或逐项差异批准成为
  可追踪决定，且源数据始终保留。
- **回滚：** 单来源行提交前故障会尝试回滚该行全部插入；只有回滚成功或 PostgreSQL 返回明确
  非歧义 SQLSTATE 时才能证明零提交，其中 `40001`/`40P01` 供未来 operator 有界重试。回滚失败
  且已经写入，或写入后的 SQLSTATE class 08、`40003`、缺失 SQLSTATE commit 异常，必须保持提交
  数未知。恢复 legacy 写入后禁止自动反向删除，只允许回滚流量并前向修复。
- **当前证据边界：** test-only fixture sweep 只证明逐来源行锁、回滚、仅插入与幂等原语；它会在
  同一 fixture 中分别观察 blocker 与可迁移行，且已固定严格 JSON、Python Unicode whitespace、
  非法字段/规范化冲突、目标真子集与 target-conflict、目标题目 membership、回滚失败及提交结果
  未知等逐行 disposition；它仍不是生产全局 apply，也没有证明 dry-run 全量汇总、逐项批准或“任一
  未处置项阻断整次 run”，也没有证明真实网络下的 ambiguous commit 恢复或迁移后删除/tombstone
  语义，不得据此授权生产 operator。

## P4C-LEARNING-004：`bank_<bank_id>_tags` namespace 转交 learning

- **Phase 1 历史：** compatibility namespace 初始归 `personalbank`，而物理源表
  `user_progress`、目标表 `user_question_tag_items` 均归 `learning`。
- **Phase 4C 有效所有权：** 仅将 `db_kv_namespace:bank_<bank_id>_tags` overlay 为
  `learning`；不改写 Phase 1 文件，不转移 `user_question_banks`、`user_bank_questions`
  或其他 `user_progress` namespace。
- **批准理由：** `personalbank` 不允许依赖 learning，反向让它读写 learning persistence 会破坏
  DAG。转交后，learning 可在本模块事务中迁移兼容状态，并通过
  `learning -> personalbank::api` 校验 bank/question membership。
- **生产边界：** personalbank 只公开 provider-owned immutable bank/question 事实，不暴露
  Entity、Repository、SQL row，也不查询收藏、错题、进度或标签表。

## P4C-LEARNING-005：跨模块读取使用有界多快照并在事实查询时复核权限

- **旧行为：** Flask 在一个共享 SQLAlchemy Session 中直接 join personalbank 与 learning 表；
  PostgreSQL `READ COMMITTED` 仍可能让不同 statement 看到不同已提交快照，但访问检查只发生一次。
- **Java 行为：** learning 编排不创建跨模块事务；每个模块只在自己的短只读事务中查询。
  personalbank 的聚合事实 API 接收当前 viewer，并在返回题库聚合前再次执行 owner/public/share
  访问检查。权限在初检后被撤销时，整个用例拒绝，不返回先前已读取的 learning 集合。
- **提前返回边界：** 在 tag 为空、tag 查询异常触发 fail-soft，或准备返回全零视图之前，learning
  必须先调用 personalbank 权限复核。personalbank access 或任一 facts 调用返回 `DENIED` 时都是
  terminal `DENIED`，必须丢弃已得到的部分结果；只有基础设施或查询异常才可按合同对相应可选字段
  fail-soft，权限拒绝不得伪装成空结果、零值或可选字段故障。
- **批准理由：** 模块 DAG 和事务所有权优先于伪造一个跨模块共享事务；最终事实复核关闭了初检与
  聚合之间的权限撤销窗口。查询总数增加必须有固定预算与 PG16/18 规模证据，禁止 N+1。
- **保持不变：** 正常稳定数据集上的 total/favorites/mistakes/types 与排序保持 golden 等价；
  仅并发权限撤销时从旧实现可能继续成功收敛为 fail closed。
- **切流门禁：** 15 万题、收藏/错题规模和 tag typed-array 必须重新捕获计划；不得把 900 个
  test-only tag 参数当成生产上限。

## P4C-LEARNING-006：共享题库授权关闭跨题库与非确定性绕过

- **冻结旧行为：** Phase 4B golden 记录了 `bank_shares.bank_id` 未与
  `bank_share_records.bank_id` 校验，以及无 `ORDER BY` 的 `fetchone()` 会让多条分享记录
  的结果依赖数据库返回顺序；固定夹具中的跨题库记录因此错误地授予访问权。
- **Java 行为：** `personalbank::api` 的访问查询必须同时绑定请求题库、分享记录题库和分享
  本体题库；只接受 `read`/`copy` 权限，未知或空权限 fail closed。对同一用户/题库的多条记录
  采用确定性排序后选择任一仍 active 且 `expires_at` 为 NULL 或严格晚于北京当前时刻的合法
  grant；不能因一条过期记录先出现而遮蔽后续合法 grant。到期时间等于当前时刻必须拒绝。
- **安全差异：** 跨题库夹具的目标结果由旧实现的 `200` 改为 `DENIED`；这是关闭越权而非
  静默改变普通 owner/public/share 正常语义。实现前必须以固定 unit、adapter 和 PG16/18
  夹具验证 join、权限、排序、到期边界及复核调用。
- **切流门禁：** 未通过这些固定安全测试前，不得实现 HTTP Controller、Security matcher、
  route/OpenAPI 或生产切流；read-contract 不得自行声明 operator 或全局迁移 preflight 已授权。

## P4C-LEARNING-007：显式 Bearer 选择不回退 Session，且拒绝文案去枚举化

- **旧行为：** API alias 接受 Session 或有效 legacy Bearer，Web alias 仅接受 Session；但旧
  `auth_required` 在显式 Authorization 无效时仍会回退到同一请求的有效 Session。旧凭据层还可按
  malformed、expired、stale、revoked 或 locked 结果暴露不同拒绝提示，而目标
  `LegacyCredentialAuthenticationApi` 的 `Optional` 边界不承诺这种枚举。
- **Java 目标行为：** 继承 `P3-AUTH-006`：一旦请求显式携带 Authorization，就只能走 Bearer
  分支；重复、畸形、签名错误、过期、version 过时、已撤销或账号锁定都 fail closed，禁止回退到
  目标或 Flask Session。API alias 仍接受权威 Session、经权威复核的旧 Flask Session 以及有效
  legacy Bearer；Web alias 只接受 Session，任何显式 Authorization（包括有效 Bearer 与 Session
  并存）都返回 `302 Location: /login`。
- **统一失败信封：** API alias 不向客户端区分上述 Bearer 拒绝原因，统一为
  `{"status":"unauthorized","message":"请先登录","status_code":401,"request_id":...}`；
  Web alias 统一为登录重定向。目标 Session 权威存储不可用仍是可区分的安全 503，不伪装成 401。
- **批准理由：** 禁止凭据混淆比保留可被用于账号状态枚举的细粒度文案更重要；这也与已实现的
  Phase 3 认证边界一致，不在本路由反向扩张 identity API。
- **保持/影响：** 有效凭据的 alias 选择、当前 `session_version`/锁定复核、请求 ID 与权限判定
  保持。依赖“旧 Bearer + 有效 Cookie”回退的调用方将改为 API 401 或 Web 302，且不再获得
  stale/locked 的特定文案。
- **强制测试：** 两个 alias 都要覆盖目标/legacy Session、Bearer-only、有效 Session + 冲突
  Bearer、重复头、malformed/expired/stale/revoked/locked 及权威存储不可用；断言失败前零
  learning 应用调用、零业务 SQL，并继续通过 `P3-AUTH-006` 的回归测试。
- **切流边界：** 当前只批准后续精确 Security matcher/error writer 的行为合同；在上述双 alias
  矩阵与 OpenAPI 差异 ID 入库前，不得登记 migrated 或切流。

## P4C-LEARNING-008：user-counts HTTP 不再写 `users.last_active`

- **旧行为：** 旧全局 Session 活动钩子会在 user-counts 业务结果之前尝试更新
  `users.last_active`；因此已认证 Session 的 GET/HEAD 即使最终是 403 或 500，也可能先留下
  identity DML。Bearer-only 与匿名请求不写，固定的匿名 CORS preflight/OPTIONS 观察也没有进入
  该写入。
- **Java 目标行为：** 两个 alias 的 GET、HEAD 和 OPTIONS，无论 2xx/3xx/4xx/5xx，都不得更新
  `users.last_active`，也不得新增 learning 到 identity persistence 的依赖。在线活动只允许由
  identity/session 层的既有 Redis Session 机制表示；Bearer 不伪造 Session，CORS preflight
  不创建、续期或刷新 presence。
- **批准理由：** learning-owned 读路由不应拥有 identity 写事务；为保留隐式 GET DML 而扩张
  API 会破坏模块 DAG，也会让失败请求产生不可预期副作用。
- **保持/影响：** 题库访问、计数、认证失效与 Redis Session 行为不变。但仅通过这两条 Java 路由
  活动的用户不再刷新旧关系列；仍读 `users.last_active` 的旧在线用户列表、后台页面与聊天排序
  可能暂时低估或后移这些用户。该影响必须在 Phase 7 的 identity-owned presence/online
  projection 迁移中消除，不得由 learning 反向补写。
- **强制测试：** 对 API/Web、GET/HEAD/OPTIONS、Session/Bearer/匿名及
  200/302/400/401/403/404/429/500/503 断言 identity 表指纹不变、`last_active` DML 为零；
  合法 preflight 还必须零 Session 副作用。
- **切流边界：** 切流前必须将旧在线/后台/聊天消费者的暂时可见性影响纳入 runbook 和监控，并
  追踪 Phase 7 presence 退出条件；本差异不授权修改 identity API/数据库。

## P4C-LEARNING-009：受保护限流按有效 actor 计费并在 Redis 故障时返回 503

- **旧行为：** 两条 alias 继承 Flask 全局 fixed-window 限流，基础配置为
  `10/second;500/hour;5000/day`；固定提交的 compose 生产默认再乘 100，为
  `1000/second;50000/hour;500000/day`，且可被环境显式覆盖。两个注册 endpoint 使用独立桶；
  但旧 key 优先选 Session，导致“Session owner + 冲突 Bearer actor”请求向 Session 桶计费，
  业务却以 Bearer actor 执行。旧 Redis 连接拒绝在 handler 前返回通用 500，不带限流头。
- **Java 目标行为：** 保留 10/500/5000 基础三窗口和生产默认 100 倍，两个 alias 使用彼此独立
  且与 public-bank 分离的 route namespace。先完成认证选择，再以同一个有效 principal 计费；
  无有效 principal 时才使用已信任的 client IP。显式 Bearer 与 Session 冲突时以 Bearer actor
  为准，Bearer 拒绝时不得偷用 Session actor 的桶。
- **Key 与故障边界：** actor/IP 在进入 Redis 前使用独立 secret 的 HMAC 假名，禁止写入 raw
  user ID、IP、Cookie 或 Bearer。任一窗口无法原子记录时 fail closed 为固定安全 503，不带
  Redis 地址/异常文本或伪造的限流头，也不得放行业务调用。
- **批准理由：** 有效 actor 必须与实际授权主体相同，否则可用冲突凭据消耗他人配额或规避自身
  配额。HMAC 避免 Redis key 成为身份目录；503 把配额存储故障与真正 429 分开，且在计数状态
  不可知时不默认放行。
- **保持/影响：** 保留 alias 独立、部署可覆盖的生产预算、API JSON 429、Web 默认 HTML/显式
  JSON 协商、`Retry-After` 与三个 `X-RateLimit-*` 头。可观察差异是冲突 Bearer 改向真正
  actor 计费、Redis 故障从 500 改为 503，以及 Redis key 不再可读原始身份。
- **强制测试：** 用可控时钟覆盖秒/时/日窗口、生产倍率和环境覆盖；覆盖 alias 互不泄漏、同
  actor 跨 IP、不同 actor 同 IP、匿名/IP 兜底、Session/Bearer 冲突、无原始 key、429
  信封/四个头以及 Redis 连接拒绝/中断的 503。
- **切流边界：** 禁止直接复用 public-bank limiter 的 route 枚举、bean 或 Redis namespace；
  必须先有真实 Redis 的多请求、隔离、故障恢复和多实例证据。当前固定旧栈捕获不是生产流量证明，
  也不单独授权实现或切流。

## P4C-LEARNING-010：CORS 只限 API alias，OPTIONS 在认证与业务前安全终止

- **旧行为：** Flask-CORS 作用于全局 `/api/*`，允许固定的 servicewechat origin、显式部署
  origin 与 debug localhost，配置方法是 GET/POST/PUT/DELETE/OPTIONS，允许头只有
  Content-Type/Authorization，`supports_credentials=false`。固定观察中，allowlisted API GET
  以 200 执行业务并回显 ACAO；非 allowlisted API GET 也以 200 执行业务，只是不发 ACAO。
  合法 API preflight 先被全局认证拒绝为 401，但仍带 ACAO、不包含 X-Request-ID 的 ACAH 及
  过宽的 ACAM；非法 origin 是无 CORS 头的 401，Web preflight 是 `/login` 302。
- **Java simple-request 行为：** CORS 只匹配精确 API alias，allowlist 是
  `https://servicewechat.com` 加显式部署配置，dev profile 才增加 localhost/127.0.0.1 的
  5000/3000 端口。无 Origin 的 GET/HEAD 正常进入 auth→user-count limiter→业务且不发
  `Access-Control-*`；allowlisted Origin 也走同一业务链，只精确回显单一 ACAO，绝不使用
  wildcard 或 ACA-Credentials，普通响应不发 ACAM/ACAH。非 allowlisted Origin 固定为 403
  空体，在 target auth、route limiter、Session、Controller、应用层与 SQL 前终止，无
  `Access-Control-*` 或 `Set-Cookie`。
- **合法 API preflight：** 仅当 OPTIONS 同时具备 allowlisted Origin、
  `Access-Control-Request-Method: GET|HEAD`，且 requested headers 是
  {Authorization, Content-Type, X-Request-ID} 的大小写不敏感子集时返回 204 空体。
  `Allow` 和 ACAM 集合均为 {GET, HEAD, OPTIONS}，ACAH 只列出请求中的允许子集，ACAO 精确
  回显 origin；不发 wildcard、ACA-Credentials 或未冻结的 Max-Age。`Vary` 必须合并
  {Origin, Access-Control-Request-Method, Access-Control-Request-Headers, Cookie}。
- **非法与普通 OPTIONS：** preflight 的 origin、method 或 header 任一不允许时固定 403 空体，
  无 `Access-Control-*`/`Set-Cookie`，但保留 `X-Request-ID`、安全头和同一组 `Vary` token。
  精确 converter-valid API alias 的 bare OPTIONS 固定为 204 空体，`Allow` 集合为
  {GET, HEAD, OPTIONS}，无 `Access-Control-*`，`Vary` 为 {Origin, Cookie}。合法、非法与
  bare OPTIONS 都必须为零 target auth、零 user-count rate acquire、零 Session
  create/refresh/invalidate、零 Controller/application/SQL。
- **Web alias：** Web 不是 CORS resource，任意 Origin 都不改变 GET/HEAD 的正常 Web 认证与
  业务状态，也绝不输出 `Access-Control-*`。精确 converter-valid Web alias 的 OPTIONS 固定
  204 空体，`Allow` 集合为 {GET, HEAD, OPTIONS}、`Vary: Cookie`，且同样零认证、限流、
  Session、应用调用、SQL 和 `Set-Cookie`。
- **批准理由：** 浏览器 preflight 不携带业务凭据，先要求登录会使合法跨域 API 读取不可用；
  同时精确路由、origin、方法和头白名单阻止预检豁免扩散成新的全局匿名面。主动拒绝非 allowlisted
  simple request 还避免服务端在明确不受信任的跨域意图下执行受保护业务。
- **保持/影响：** allowlisted API simple request 的认证、限流和业务不变；API 响应必须合并
  `Vary: Origin, Cookie`，Web 响应为 `Vary: Cookie`。可观察差异包括非 allowlisted API GET/HEAD
  从“执行后仅无 ACAO”改为前置 403、X-Request-ID 加入允许头、合法 preflight 从 401 改为 204、
  非法 preflight 从 401/302 改为 403，以及 Web/bare OPTIONS 收敛为无副作用 204。
- **强制测试：** 覆盖双 alias、无/允许/拒绝 Origin、GET/HEAD、requested headers 全子集和超集、
  method 越界、credentials/wildcard/Max-Age 缺失、`Allow`/`Vary`/Request ID，并在每个 204/403
  上断言 auth、限流、Session、Controller、learning/personalbank 调用、SQL 与 Set-Cookie 全为零。
- **切流边界：** 只允许后续新增路由级 CORS source，禁止用全局 `/**` permitAll 或改变其他 API。
  应用内测试客户端证据不等于浏览器 cookie enforcement 或反向代理 header-preservation 证据；
  完整链与部署证据未闭合前不得切流。

## P4C-LEARNING-011：保留 Unicode Nd 数字语义并安全收敛路径溢出与歧义

- **旧行为：** Werkzeug `<int:bank_id>` 接受前导零、Unicode `Nd` 与 percent-decoded ASCII
  数字；0 匹配后返回 403，负数/非数字/分号 matrix 不匹配为 404，encoded slash 观察为 308。
  Python `int` 无界，`2147483648` 在固定夹具中到达访问检查后为 403，而
  `9223372036854775808` 在数据库绑定前失败为安全 500。
- **规范化目标：** 必须先做严格 canonical percent decode；unreserved ASCII 数字与严格 UTF-8
  编码的 Unicode `Nd` 都进入同一解析器。复用 `LegacyDecimalPathInteger`，逐 Unicode code
  point 只接受 `Nd` 并按 digit value 规范化为 ASCII；去除前导零后按字符串 length/lexicographic
  比较边界，禁止先用 `int`、`long` 或 `BigInteger` 解析任意精度输入。
- **合法与零值：** ASCII、前导零、混合 Unicode `Nd`、percent-encoded ASCII/UTF-8 `Nd` 均保持
  converter-valid。任意全零表示 0，在有效认证和 alias 限流计费后固定返回 legacy
  “无权访问此题库”403，不调用 `LearningApplicationApi`、不发业务 SQL。规范化值
  1..2147483647 才构造 `PersonalBankUserCountsQuery` 并进入应用层。
- **Converter miss：** 负数、`+1`、小数、空 segment、字母/混合非数字、Unicode numeric 但非
  `Nd`、额外 segment 与 trailing slash 固定为 404，不扣 user-count route 额度、不进应用或业务
  SQL。既有全局 `TargetSessionAuthenticationFilter` 仍可能读取显式凭据/已有 Session；“404
  不扣额”不得被误写成“全局认证过滤器绝不运行”。
- **溢出与防火墙：** 规范化值只要大于 `Integer.MAX_VALUE`，无论是否超过 `Long.MAX_VALUE`，
  都在有效认证、alias 限流计费后固定为不泄漏输入或异常文本的安全 500，并且不构造 query、零
  应用调用、零业务 SQL；前导零不改变该边界。literal/encoded slash 和 literal/encoded semicolon
  中，literal slash 形成 extra segment 并按 converter miss 返回 404；encoded slash 以及
  literal/encoded semicolon 由 `StrictHttpFirewall`/保留字符 canonicalization 在 route authz、
  user-count limiter、MVC 与应用前固定拒绝为安全 400，不得先解码为可匹配路径。
- **批准理由：** 明确的字符串边界比较能在进入 Java `int` 业务边界前固定任意精度溢出结果，
  同时保留旧栈真正支持的国际化数字。将 encoded slash/semicolon 歧义提前拒绝，避免代理、
  Servlet、Security matcher 与 MVC 对同一 raw target 产生不同理解。
- **保持/影响：** 合法 ID、Unicode/leading-zero、0 和普通 converter 404 的相对顺序保持。差异是
  `2147483648` 从旧夹具 403 收敛为统一溢出 500，encoded slash 从 308、semicolon 从 404 收敛
  为 firewall 400。404 仍按 alias/Accept 走既定协商；overflow 500 为 API 固定安全 JSON、Web
  默认 HTML/显式 JSON，400 只承诺安全状态、无内部信息和 Request ID，不虚构 legacy JSON。
- **强制测试：** 双 alias 覆盖 ASCII/阿拉伯-印度/全角/混合 `Nd`、前导零、percent-encoded
  ASCII/UTF-8 `Nd`、0、负数、非 `Nd`、空/额外/trailing、encoded slash/semicolon、
  `Integer.MAX_VALUE`、max+1、`Long.MAX_VALUE` 与 long max+1；逐例断言
  firewall→route authz→limit→parse→application 的实际终止点、计费和 SQL 边界。
- **切流边界：** 必须有真实 Servlet HTTP 与入口代理 raw-target 测试，证明编码分隔符没有在上游
  被改写；在 400/404/500 发生层级、限流计费、错误协商和零业务 SQL 未固定前不得切流。

## P4C-LEARNING-012：HEAD 执行 GET 同等语义，但所有结果都是零字节响应体

- **旧行为：** Flask 的 GET 登记自动派生 HEAD；已认证 HEAD 会进入与 GET 相同的业务路径，再由
  HTTP 层剥离响应体。不同拒绝分散在认证、限流、converter 和异常处理，不能只用 200 用例推断
  所有 Spring filter/security writer 产生的 HEAD 都会自动空体。
- **Java 目标行为：** HEAD 与对应 GET 共用完全相同的 raw path 解析、alias 认证、有效 actor、
  限流桶/计费、参数规范化、learning/personalbank 调用、SQL 预算、状态码和语义响应头；唯一
  差别是实际响应体始终为零字节。`Content-Length` 可省略或表示对应 GET representation 的长度，
  不要求其值为 0，硬约束是网络响应体字节数为 0。
- **零体矩阵：** 200 成功、302 登录重定向、400 firewall、401 认证拒绝、403 题库拒绝、404
  converter miss、429 限流、500 业务故障/溢出和 503 权威或 Redis 不可用都不得写 JSON、HTML、
  重定向页或异常文本。`Location`、CORS、`Vary`、安全头、限流头、`X-Request-ID` 与对应 GET
  的 `Set-Cookie` 失效/刷新语义仍须保留。
- **执行顺序：** 业务 403 仍实际扣额并调用业务，path 0 的 403 则扣额但零应用调用；converter
  404 不扣 user-count 额度；429 实际 acquire 后拒绝并保留四个限流头；path overflow 在扣额后
  以零应用/SQL 返回 500。认证 authority 503 在 user-count limiter 前，无该 route 的限流头；
  rate-store 503 发生在认证后，但不能伪造完整限流 decision。
- **批准理由：** HEAD 是 GET 的元数据视图，不应成为绕过权限、限流或业务复核的第三条路由；
  同时由每个 writer 显式抑制 body，避免不同 Servlet/filter 终止点产生不一致结果。
- **保持/影响：** 除实际 body 字节外，不降级任何 GET 认证、Session 失效/刷新、限流、权限撤销
  复核、字段降级或 alias 错误协商语义。`users.last_active` 依
  `P4C-LEARNING-008` 始终零 DML，不因“与 GET 同等”而恢复旧身份写入。
- **强制测试：** 用同一夹具成对执行 GET/HEAD，比较双 alias 的路径分类、主体、限流计数、应用
  调用、SQL、状态码和语义头，并在上述每个状态断言实际 body length 为 0。必须直接覆盖
  Controller、Security error writer、rate filter、firewall、Session writer 与全局安全故障路径。
- **切流边界：** 不得用 MockMvc 的单一 200 结果替代真实 Servlet 容器完整链零体证据；任一
  filter/writer/异常分支在 HEAD 泄漏 body，都阻断 route/OpenAPI 登记与生产切流。
