# ADR-0005：认证采用限时本地兼容并最终切换到 Spring Security

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：Web、微信小程序、后台、密码与会话失效

## 上下文

旧系统同时使用 Flask 签名 Session 与 HS256 JWT。旧 JWT 包含 `user_id`、`openid`、`session_version`、`exp`、`iat`、`jti`，默认有效期 15 天；Web Session 默认 7 天，Cookie 为 Secure、HttpOnly、SameSite=Lax。请求可能先尝试 Bearer token，再尝试 Session。用户锁定、密码修改、解绑微信等通过 PostgreSQL `users.session_version` 和用户状态校验使会话失效，Redis `auth:user_state:*` 只是默认 20 秒缓存。

当前 Werkzeug 3.1.4 新生成密码为 `scrypt:32768:8:1`，但现有数据库可能含更早 Werkzeug 版本产生的哈希，不能用“当前默认算法”推断全部存量。迁移既不能要求所有用户重置密码，也不能让新 Java 在运行时回调 Flask 做 token introspection。

## 决策

### 权威身份与授权

1. `identity` 模块拥有用户、密码哈希、角色、微信绑定、账号锁定和 `session_version`。PostgreSQL 是权威源；Cookie、JWT、Redis 和请求 Header 不能直接授予角色。
2. 使用 Spring Security Servlet 栈和显式授权策略。默认拒绝未声明路由，按 `02-route-parity-matrix.csv` 逐操作复现“全局门禁 → Admin 钩子 → 路由规则 → Handler 内联检查”的最终结果，而不是照搬装饰器结构。
3. `is_admin`、科目管理员等角色从权威用户状态解析；禁止信任 `X-User-Id`、`X-Role` 或客户端提交的用户 ID。
4. 锁定、密码修改、封禁、角色提升/撤销和微信解绑必须在同一事务更新状态并提升 `session_version`，随后删除目标 Session/Refresh Token 和缓存。高风险操作直接核对 PostgreSQL，不因缓存而延迟撤销。

### 密码兼容

Java 提供只验证、不反序列化的 legacy `PasswordEncoder`，支持经脱敏哈希清单和固定向量证明仍存在的 Werkzeug `scrypt`/历史 PBKDF2 格式。首次成功验证后，在同一事务升级为目标 Spring Security 编码格式并保留 `session_version` 语义；失败登录绝不改写哈希。空哈希且 `has_password_set=false` 的微信用户保持“未设置密码”，不能生成可预测占位密码。

Spring Security 版本由 Boot 4.1.0 BOM 管理，不独立覆盖。目标新哈希参数必须通过安全基准测试确定，并以 `{id}` 前缀或等价元数据支持未来渐进升级。

### 过渡期兼容

1. Java 在本进程内实现旧 HS256 JWT 的严格验证，只允许固定 `alg=HS256`，校验 `exp`、`iat`、`jti`、`user_id`、`openid` 和 `session_version`；旧 Secret 只从受控 Secret 注入，不写入仓库或日志。
2. Java 在本进程内实现 Flask Cookie Session 的签名/时间/JSON 字段兼容，仅接受契约测试覆盖的安全标量，不执行任意对象反序列化。成功验证后立即查询当前用户状态，签发新的目标 Session 并清除旧 Cookie。
3. 兼容验证器必须有 `accept-until` 截止时间、指标和 kill switch。它不访问 Flask、旧 Redis 或父目录文件；所有客户端迁移并完成主动失效后，从生产 Profile 删除兼容密钥与过滤器。
4. 阶段 3 可验证旧 Session/JWT；阶段 7 完成最终认证切换；阶段 10 生产运行时不得再接受旧格式。若脱敏向量证明某种旧 Session 无法安全解码，唯一允许的批准差异是切换时使该 Web Session 重新登录，不能降低签名验证。

### 目标 Web 与小程序会话

- Web 使用服务端 Session，浏览器只持有 `__Host-ti_session` 类的不可猜测 Cookie：Secure、HttpOnly、SameSite=Lax、Path=/、无 Domain。Redis 可保存可丢失的 Session 辅助数据，但 `session_version` 和角色仍以 PostgreSQL 为准。
- Vue SPA 使用 Spring Security CSRF 保护；JavaScript 可读的 CSRF Cookie 与请求 Header 配对，登录和登出都必须是受 CSRF 保护的写请求。认证成功和登出清理旧 token 后，客户端必须获取新 CSRF token。
- 小程序兼容期接受旧 15 天 JWT；目标协议改为 15 分钟 Access Token + 最长 30 天、逐次轮换的一次性 Refresh Token。Access Token 包含 `sub`、`session_version`、`device_id`、`jti`、`iat`、`exp`、`iss`、`aud`；Refresh Token 使用至少 256 bit 随机值，只在 PostgreSQL 保存哈希、设备、到期、轮换链和撤销状态。
- Token 重放、旧 refresh reuse、`session_version` 不匹配、用户锁定或微信绑定变化都返回确定的 401 错误码并撤销相关 token family。

## 后果

正面后果：

- 旧用户无需重置密码，切换期间小程序和 Web 会话可受控迁移。
- Java 可独立验证身份，不需要旧 Flask 在线。
- 最终 Web 与小程序采用不同、适合各自威胁模型的凭据，同时共享同一撤销事实。

代价与风险：

- 旧 Cookie 签名兼容必须经过跨语言固定向量验证；实现错误会造成越权或大量掉线。
- 过渡期同时维护旧/新 token，必须严格限制时间和指标，否则兼容层会永久存在。
- Refresh Token 需要新增持久化结构和并发轮换不变量，正式表迁移只能经阶段 8 Flyway。

## 拒绝的方案

- **Java 每次回调 Flask introspection：** 违反独立运行目标，并把旧系统变成新认证单点故障。
- **切换时重置所有密码：** 破坏现有用户数据兼容和最终验收要求。
- **长期 Access Token 存 localStorage：** XSS 可直接窃取长期凭据；Web 统一使用安全 Cookie。
- **信任 Session/JWT 内角色不再查状态：** 封禁、降权和 `session_version` 无法及时生效。
- **全局关闭 CSRF：** Web Cookie 自动随请求发送，登录和登出同样需要防伪造。
- **无限期接受旧 token：** 阻止阶段 10 删除兼容密钥与旧认证桥。

## 实施与验证约束

必须建立跨语言脱敏固定向量，覆盖有效、篡改、错误算法、过期、未来 `iat`、空/错 `jti`、错 `openid`、错 `session_version`、锁定/删除用户、Cookie 压缩和非法 JSON。密码向量覆盖所有实际前缀、正确/错误密码、首次升级原子性和并发登录。

安全测试至少覆盖：

- 未登录/已登录、Web Session/旧 JWT/新 Access Token 的 611 行路由权限矩阵；
- CSRF 缺失、错 token、登录、登出、multipart、跨域与 SameSite；
- refresh 轮换、并发刷新、已用 token 重放、设备撤销、全端失效；
- 伪造身份 Header、角色、用户 ID 和 JWT `alg=none`/算法混淆均失败；
- 日志、指标和错误响应不包含密码、Cookie、JWT、Refresh Token、微信 openid 或 Secret；
- 阶段 10 的生产依赖扫描确认无 legacy verifier、旧 Secret、Flask upstream 和父目录访问。

## 事实证据

- 旧认证层级与路由证据：[`../00-current-state.md`](../00-current-state.md) 第 3 节及 [`../02-route-parity-matrix.csv`](../02-route-parity-matrix.csv)。
- 用户、认证缓存与外部身份资源：[`../03-data-ownership.csv`](../03-data-ownership.csv) 中 `identity` 条目。
- 目标认证方向：[`../01-target-architecture.md`](../01-target-architecture.md) 第 8 节。
- Spring Security 密码存储：<https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html>
- Spring Security Servlet 授权：<https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html>
- Spring Security CSRF 与 SPA/登录/登出：<https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html>
