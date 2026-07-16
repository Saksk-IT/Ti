# Phase 3 认证格式兼容清单

> 本文是 ADR-0005 的 Phase 3 实施增量。它记录 Java 当前能严格解析、验证和在 kill switch 下接受的格式，不扩大为“所有历史数据均已盘点”或“兼容入口可以永久保留”。

## 1. 权威性原则

签名正确只证明凭据格式未被篡改，不能直接授予身份或角色。旧 JWT/Flask Session 通过格式验证后，还必须按 `users.id` 查询 PostgreSQL，并同时满足：

- 用户存在且未锁定；
- `session_version` 与当前行一致；
- JWT 经 Python-compatible strip 后的非空 `openid` 与当前同样规范化的绑定一致；规范化后为空保持旧非微信 Bearer 语义，不伪造绑定；
- username、管理员/科目管理员/通知管理员角色全部来自当前数据库行；
- 数据库异常、重复/缺失状态或任何歧义都返回拒绝。

Cookie/JWT 中的 `is_admin` 等字段永不成为授权输入，Redis 也不是角色和 `session_version` 的事实源。

## 2. 格式矩阵

| 格式 | 当前接受边界 | 拒绝边界 | 当前接入状态 |
| --- | --- | --- | --- |
| Werkzeug scrypt | 仅精确 `scrypt:32768:8:1$salt$lowercase_hex`，salt 为 1～64 个 ASCII 字母数字，64 字节摘要 | 其他参数、非规范 salt/hex、哈希超过 256 字符 | 已接入 `POST /api/login`，并作为 Flask/Java 并存期的目标格式；符合规范的现有值不重写 |
| Werkzeug PBKDF2 | 仅 `pbkdf2:sha256:<iterations>$salt$lowercase_hex`，iterations 为规范十进制且 50,000～1,000,000，32 字节摘要 | 其他 digest、前导零、越界 work factor、非规范 hex | 验证器、固定向量和 p3-009 公开夹具的实际 Java 登录升级已通过；生产存量是否存在仍 unknown |
| 过渡期目标密码 | 精确 Werkzeug `scrypt:32768:8:1`；Java 新生成 16 个 ASCII 字母数字 salt 和 64 字节小写 hex 摘要 | Spring 专有前缀、参数/长度漂移、非规范 salt/hex | PBKDF2 成功后只升级到 Flask/Java 都能读取的格式；Spring 专有格式推迟到旧栈永久退出后另行决策 |
| 旧 HS256 JWT | 三段规范 Base64URL，header 只能含 `alg=HS256` 与可选 `typ=JWT`；claims 恰好为 `user_id/openid/session_version/exp/iat/jti`；最大 4 KiB、寿命不超过 15 天、时钟偏差 60 秒、jti 为 32 位小写 hex | `alg=none`、额外角色 claim、缺失/额外字段、过期/未来 iat、超长寿命、错误 openid/version | kill switch 开启时 HTTP Bearer 可本地验证并回查 PostgreSQL，但只认证当前请求，不创建或续期目标 Session；默认关闭 |
| Flask timed Session | Flask 3.1/itsdangerous 2.2 URL-safe timed cookie；允许压缩；Cookie 最大 4 KiB、解压最大 8 KiB、最大 7 天；只接受平坦 JSON 安全标量和固定键 | 任意对象/标签反序列化、未知键、类型混淆、压缩炸弹、未来/过期 timestamp、错误签名 | kill switch 开启时旧 `session` Cookie 可本地验证、回查 PostgreSQL、换发目标 Session并过期旧 Cookie/CSRF；默认关闭 |
| 目标 Web Session | Spring Session Data Redis；只序列化 String/Long/Integer/Boolean，每属性最大 8 KiB；当前只写 identity id、session version、authenticated epoch、remember；hash immediate/on-set-attribute 持久化 | Java native serialization、多态 JSON、Cookie 角色、未知属性类型；同一身份超过 3 个活跃 Session 时最旧者被淘汰 | 密码登录/旧 Flask Cookie 转换共用签发器；每请求先检查 HMAC 身份索引再按 PostgreSQL 当前状态重授权，权威拒绝/索引淘汰时失效，权威源不可用时返回 503 并保留 Session；remember Cookie 滑动刷新 7 天 |

SHA-1 只存在于 Flask/itsdangerous 历史 HMAC 兼容边界，不作为新签名算法或通用密码算法。

## 3. 资源与拒绝服务边界

- 登录账号、密码最多各 1024 个 Java 字符；密码 UTF-8 最多 4096 字节。
- JWT/Cookie/Secret 均有固定字节上限；JSON 只接受平坦对象和受限字段/长度。
- 未知账号、未知哈希和目标哈希都执行受进程级公平 semaphore 约束的目标 KDF；最大并行数为 2，不在数据库事务/行锁内执行昂贵 KDF。
- Redis 登录限流按 global、HMAC-IP、HMAC-account 三维计数；匿名 CSRF/unsafe 前置按 global、HMAC-IP 计数；旧 Cookie 验证前按 global、HMAC-IP 计数，验证后用 HMAC credential/identity marker 防重放和限制兑换。所有假名共用独立的至少 32 字节 key Secret，原始值不进入 key，Secret 的 `toString` 和错误信息均脱敏。
- 限流 Redis、KDF capacity、数据库状态或格式解析异常均 fail closed；Controller 不返回堆栈、哈希、Cookie、JWT、openid 或 Secret。
- `POST /api/login` 在 JSON 解析前以有界流读取最多 16 KiB；即使缺少或伪造 Content-Length，实际超限也返回 413。无既有 Session 的 CSRF issuance/unsafe 前置限流发生在 CSRF token 创建之前，匿名 CSRF Session 默认 10 分钟。
- local Compose 与 Phase 3 Testcontainers Redis 使用 `noeviction`，避免限流、replay marker、Session 索引或 Session hash 被内存策略静默逐出；生产必须配置同策略并提供运行态证据。

## 4. 密码升级语义

旧密码正确且账号未锁定时，精确 Werkzeug scrypt 已视为过渡目标，不重复改写；受支持的 PBKDF2 则生成精确 `scrypt:32768:8:1`，并以“用户 ID + 已观察旧 hash” compare-and-set 更新 `password_hash` 和 `has_password_set=true`。失败密码、未知账号和锁定结果不升级。升级不改变 `session_version`、用户 ID、角色或 `last_active`，且过渡结果仍可由 Flask/Werkzeug 读取。

p3-009 在固定 legacy/Java 镜像和同源 70 表夹具上实际执行了上述升级：Java 生成值满足精确 method、16 字符 ASCII 字母数字 salt 和 64 字节小写十六进制摘要，`session_version`/`last_active` 保持不变；正式 `ROLLBACK rb001` 后，固定 Flask/Werkzeug 3.1.4 接受该公开夹具密码并保持目标 hash 不变。该证据只证明已登记公开格式的双向可读性，不得外推生产密码前缀分布。

重复邮箱不是可选中的“第一条”：查询最多两条，结果不是恰好一条即执行 dummy KDF 并拒绝。手机号沿用精确匹配。该策略避免历史脏数据导致非确定身份选择，但正式唯一约束治理仍属于 Phase 8。

## 5. 临时兼容窗口和 kill switch

`ti.security.legacy-auth.enabled` 默认 `false`。只有显式启用、提供 16～4096 字节受控 Secret，且 `accept-until` 严格位于当前时间之后、最多 366 天时，才创建旧 JWT/Flask Session 兼容服务。每次调用都重新检查截止时间并按 `format/outcome` 记录 Micrometer 计数；截止、配置错误、验证异常或数据库异常均拒绝。

`TargetSessionAuthenticationFilter` 始终处理目标 Session，但通过 `ObjectProvider` 只在 legacy bean 存在时尝试旧凭据转换：

- 只要请求显式提供 Authorization Header，它就优先于目标/Flask Cookie。唯一且长度受限的 `Bearer ` 验证成功后只安装本次请求身份，不创建或延长目标 Session；无效、重复或畸形 Authorization fail closed，也不回退到任何 Cookie。
- 没有 Authorization 时，目标 Session 必须同时含 Long identity ID 和 Integer `session_version`，并仍存在于每身份最多 3 个的 Redis 活跃索引；每个请求再通过 `SessionAuthorityApi` 回查 PostgreSQL。畸形、被淘汰、锁定、删除或 version 变化会使 Session 失效；权威数据库/Session 索引暂时不可用时返回 503 并保留 Session；用户名和角色只从本次数据库结果安装到当前请求 SecurityContext。remember=true 时在成功重授权后重新发出 Max-Age=7 天 Cookie，形成滑动窗口。
- 没有有效目标身份时才读取唯一的旧 `session` Cookie；已有匿名 CSRF Session 不会阻止转换。昂贵验签前先执行 global/HMAC-IP 尝试限流；成功验签和 PostgreSQL 权威核对后，再原子取得 HMAC credential 一次性 marker，并按 `identity_id + session_version` 最多允许 3 次兑换。成功后通过共享签发器轮换为目标 Redis Session、保留旧 remember 语义、清除服务端权威 CSRF token并过期旧 `session` Cookie；重放或超限不会产生新 Session。换发 Session 不保存角色或 username。
- 共享签发器依赖 Spring Session `flush-mode=immediate`/`save-mode=on-set-attribute`，使新 hash 在身份索引淘汰前存在；外层链尾协调过滤器在 Spring Session 保存之后再次检查索引，删除并发在途请求可能回写的已淘汰 hash，或清理无 hash 的孤立索引。
- `ti.security.legacy-auth.enabled=false` 时不存在 `LegacyCredentialAuthenticationApi` bean，filter 不接受旧 Bearer/Cookie；显式启用仍受 Secret、截止期和指标约束。
- 阶段 10 前必须删除旧 Secret 与兼容入口，不能只把截止时间无限延长。固定向量、filter 单测和本地端到端证据都要保留，但都不能改变这个退出条件。

## 6. 脱敏证据

固定向量位于 `server/src/test/resources/compat/legacy-auth-vectors.json`，仅包含合成账号、合成 Secret 产生的凭据和公开测试哈希。它不能证明生产/历史库只包含这些密码前缀。若未来脱敏清单出现新格式，必须先新增严格 parser、成本上限、跨语言向量和失败测试，再扩大接受面。
