# Phase 3 认证兼容的批准差异与开放缺口

> 本文补充 ADR-0005 与 ADR-0006。只有列在“批准差异”中的变化可被 OpenAPI 的 `x-ti-approved-differences` 引用；“开放缺口”不是批准差异，也不能用于放行生产。

## 1. 批准差异

| ID | 旧行为 | Phase 3 Java 行为 | 安全理由与兼容处置 |
| --- | --- | --- | --- |
| `P3-AUTH-001` | `/api/login` 是匿名白名单写请求，旧全局规则不要求目标 SPA CSRF token | 仍允许未登录调用，但必须先从 `GET /api/csrf` 获取 Cookie mirror，并在 `X-CSRF-TOKEN` 回传；真正权威 token 绑定服务端 Session，复制 Cookie 不能建立权限 | 防止 login CSRF；新 Vue 必须先初始化 token。缺 token 的 403 使用 Spring Security 安全错误信封，不伪装成密码错误 |
| `P3-AUTH-002` | Flask 把用户、角色和 version 标量签入名为 `session` 的客户端 Cookie | Java 使用 Redis 服务端 Session，浏览器仅持目标随机 ID；本地 `ti_dev_session`，生产 `__Host-ti_session`，成功登录清除旧 `session` | 避免角色快照成为授权源，支持服务端失效；旧 Cookie 名只用于迁出，不继续签发 |
| `P3-AUTH-003` | 旧登录直接回显请求的 redirect 或 `/` | Java 只回显单斜杠开头的安全相对路径；绝对 URI、`//`、反斜杠、控制字符和编码绕过回退 `/` | 阻断 open redirect/响应拆分；客户端仍得到同字段与站内默认路径 |
| `P3-AUTH-004` | 成功登录继续保留旧 Werkzeug hash，并按登录前 `has_password_set` 决定 `needs_password_set` | 精确 Werkzeug scrypt 已视为过渡目标；成功验证受支持 PBKDF2 后 compare-and-set 升级为固定 `scrypt:32768:8:1`，置 `has_password_set=true`，成功信封返回 `needs_password_set=false` | 不要求用户重置密码；ID、角色、`session_version`、`last_active` 不变。CAS 冲突后仅在重新读取确认同一账号仍可用、version 未变且赢家写入的目标 hash 仍匹配本次密码时恢复成功；锁定、version/密码变化或无法确认一律 fail closed。过渡目标保持 Flask/Java 双兼容；Spring 专有格式推迟到旧栈永久退出后 |
| `P3-AUTH-005` | 历史服务层对重复邮箱的选择语义没有唯一约束保证 | Java 查询最多两条；不是恰好一条即执行 dummy KDF 并返回统一无效凭据 | 避免脏数据导致登录到不确定账号；不修改生产数据，唯一约束治理留到 Phase 8 |
| `P3-AUTH-006` | 旧 `auth_required` 遇到无效 Authorization 时仍会回退到已有 Web Session | 只要显式提供 Authorization，就把它视为调用方选择的凭据；有效旧 Bearer 只认证当前请求且不创建/续期 Session，无效、重复或畸形 Header fail closed，不回退到目标或 Flask Cookie | 避免 Cookie 用户与 Bearer 用户身份混淆，也不把临近 `exp` 的 JWT 延寿为 7 天 Session；客户端不得同时发送陈旧/重复 Authorization 与 Cookie 来依赖回退 |

以下是已实现的安全边界，但不属于客户端可观察的行为差异 ID：

- 账号/密码 1024 字符、密码 4096 UTF-8 字节、登录 JSON 实际输入流 16 KiB、JWT/Cookie 4 KiB、Session 属性 8 KiB 的上限；登录体超限返回安全 413，其余输入超限 fail closed。redirect 超过 2048 字符时不执行跳转，安全回退 `/`。
- 登录限流使用 Redis Lua 的 global + HMAC-IP + HMAC-account 三维原子分钟桶；无 Session 的 `GET`/框架派生 `HEAD /api/csrf` 和所有 unsafe 方法还在 CSRF/匿名 Session 前经过 global + HMAC-IP 桶，匿名 Session 默认 10 分钟。Redis 不可用返回 503，而不是绕过限流。
- 旧 Flask Cookie 在昂贵验签前经过 global + HMAC-IP 桶；验签和数据库权威核对后，HMAC credential marker 拒绝同一 Cookie 重放，`identity_id + session_version` 最多兑换 3 次。原始 IP、账号、Cookie 和身份 ID 不进入 Redis key。
- 目标 Session 不存 username/roles；后续受保护路由必须从 PostgreSQL 获取当前值。
- 密码登录与旧 Cookie 兑换共用签发器和每身份 3 个目标 Session 的硬上限；Session hash immediate 持久化后才登记/淘汰，链尾协调过滤器删除在途请求回写的失效 hash。remember Cookie 在每次成功权威重授权后滑动刷新 7 天；Bearer request-only 路径不读写该续期逻辑。
- 旧 `POST /api/login` 没有持久失败次数或自动锁定写入；Java 不虚构这类数据库写，只读取既有 `is_locked`。暴力破解控制由 5/min 旧契约和新的外层/KDF 容量边界承担。

## 2. 非差异的兼容要求

- 保留路径、POST、匿名可发起、JSON 媒体类型、Pydantic 已观察布尔强制集合和未知字段忽略语义。
- 保留账号/密码为空、用户名登录、无效凭据、锁定账号、成功结果的状态码和中文消息。
- 保留成功信封中的 `status`、`redirect`、`remember`、`needs_password_set`、`message`、`data` 与 `request_id`；动态 Request ID 只能按已登记规则归一化。
- `GET /api/auth/login-methods` 无批准差异：状态码、信封、布尔解析、默认模式和无副作用均须对齐。

## 3. 开放缺口，不得作为批准差异

1. 旧 JWT 的 HTTP 当前请求认证、Flask Session 的目标 Session 换发，以及目标 Session 每请求 PostgreSQL 重授权已经实现；当前两条迁移路由都是匿名，首个受保护业务路由仍须补完整权限矩阵、authority unavailable 保留 Session 与端到端失效证据。
2. legacy kill switch 默认关闭；未来临时启用必须同时配置受控 Secret 与未来且不超过 366 天的截止时间、监控 format/outcome 指标，并在阶段 10 删除 Secret、bean 与兼容入口。默认关闭不能替代移除计划。
3. Session Cookie 滑动刷新、每身份上限、immediate 持久化、链尾协调和并发密码升级/锁定竞态已实现；local/Testcontainers Redis 使用 `noeviction`。完整 Maven 208+22、Phase 3 Python 29+59、最终 WORM 与独立抽取均已通过；生产 Redis `noeviction`/至少 32 字节 HMAC Secret 的运行态证据仍须在获批环境补齐。
4. p3-009 已完成真实 Flask/Java 暖 GET 零差异报告、登录隔离写双库终态报告、固定镜像切换/回滚和公开 PBKDF2 实际升级后的 Flask/Werkzeug 3.1.4 接受性证明。冷 GET 首次创建的 1 个排除 Flask-Limiter 运行时 Key 不是业务或持久副作用，但必须保留为预期失败报告，不能宣称绝对零 Redis 写入。生产/历史密码前缀分布仍 unknown，留待获批盘点。

任何新增行为差异必须新增稳定 ID、旧/新证据、客户端影响和回退策略；不能只在测试里放宽断言。
