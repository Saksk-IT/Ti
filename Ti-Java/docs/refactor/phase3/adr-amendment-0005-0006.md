# ADR-0005/0006 Phase 3 实施补充：认证兼容边界

- 状态：Phase 3 实施补充；Java 代码与 p3-009 两条 operation 的本地双运行时验收已落地，生产切换未完成
- 日期：2026-07-16
- 上位决策：[`../adr/0005-authentication-transition.md`](../adr/0005-authentication-transition.md)、[`../adr/0006-api-contract.md`](../adr/0006-api-contract.md)
- 适用 operation：`POST /api/login`、`GET /api/auth/login-methods`

## 决策增量

1. Phase 0～2 机器合同是历史快照，不回写。Phase 3 通过 route/OpenAPI/application-API delta 覆盖恰好两条 operation；`migrated` 与生产切换、真实双运行时报告分别记账。
2. 登录保持旧路径和信封，但目标写请求强制服务端 Session 权威 CSRF token 与 Cookie mirror/`X-CSRF-TOKEN` 配对；单独复制 Cookie 无效。公开 GET 不需要 CSRF 且必须通过副作用 fingerprint。
3. Web 登录成功只签发 Redis 服务端目标 Session。目标 Cookie 使用独立名称并清除旧 `session`；Session 仅保存身份 ID、version、认证时间和 remember，角色/用户名留在 PostgreSQL 权威源。
4. 只接受固定向量和严格 parser 证明的 Werkzeug/Flask/JWT 格式。精确 Werkzeug scrypt 已是并存期目标，PBKDF2 成功后只 CAS 升级到 Flask/Java 双兼容的 `scrypt:32768:8:1`；Spring 专有格式推迟到旧栈永久退出后。旧凭据兼容服务默认关闭、具有最长 366 天窗口和指标，不回调 Flask。
5. 安全相对 redirect、重复邮箱 fail closed、显式 Bearer 不回退、16 KiB 登录体、输入/解压/KDF 边界和 Redis 限流是明确安全收紧。登录使用 global + HMAC-IP + HMAC-account；无 Session 的 CSRF issuance/unsafe 前置使用 global + HMAC-IP；旧 Cookie 兑换在验证前使用 global + HMAC-IP，验证后使用 HMAC credential replay marker 与每身份 3 次上限。逐项兼容处置由 `approved-authentication-differences.md` 固定。
6. `TargetSessionAuthenticationFilter` 对每个目标 Session 先检查每身份最多 3 个的 Redis 活跃索引，再按 ID/version 回查 PostgreSQL，并只从当前数据库状态安装角色；过期、锁定、version 不一致、被淘汰或畸形 Session 立即失效，权威源暂时不可用则返回 503 并保留 Session。密码登录与旧 Cookie 兑换共用 immediate 持久化的签发器，链尾协调过滤器删除在途请求对已淘汰 Session 的回写；remember Cookie 每次成功权威重授权后滑动刷新 7 天。只有 kill switch 显式开启且截止期有效时，filter 才本地验证旧凭据：显式 Bearer 优先且只认证当前请求，不创建、刷新或续期 Session；旧 Flask Cookie 才轮换为只含安全标量的目标 Session、保留 remember，并清除旧 Flask Cookie/CSRF 状态。
7. 兼容 HTTP 路径已实现不等于可以无限期启用：默认没有 legacy verifier bean；启用需要 Secret、未来且最多 366 天的 `accept-until`，阶段 10 必须删除兼容 Secret 与入口。
8. HMAC-IP/account/credential/identity Redis key 共用独立的至少 32 字节 key Secret，原始身份值不进入 key；生产缺少 Secret 必须启动失败。承载这些计数、replay marker、Session 索引和 Session hash 的 Redis 必须使用 `noeviction`；local Compose 与 Phase 3 Testcontainers 已固定，生产仍需运行态证明。

## 未选择

- 不修改 Phase 1 OpenAPI 来伪装历史已经包含当前实现。
- 不在 Java 运行时代理或 introspect Flask。
- 不让 Flask/Java 向同一数据库或 Redis 执行影子/双写。
- 不信任 Cookie/JWT 的角色字段，也不把 Redis 变成账号状态事实源。
- 不因旧登录缺少失败计数就临时修改生产 schema；只保留已观察的锁定读取和限流语义。

## 证据与退出条件

当前代码/测试证据、p3-009 C 级双运行时摘要与剩余生产/受保护路由边界分别见：

- [`authentication-compatibility.md`](authentication-compatibility.md)
- [`approved-authentication-differences.md`](approved-authentication-differences.md)
- [`dual-stack-and-cutover-evidence.md`](dual-stack-and-cutover-evidence.md)
- [`effective-route-parity-status.json`](effective-route-parity-status.json)

p3-009 已完成真实 GET 冷/暖比较、登录隔离写终态、固定镜像切换/回滚和公开 PBKDF2 实际升级后的 Flask 接受性证明；这些报告已与完整 Maven、静态门禁、最终 WORM 及独立抽取共同验收，但仍不能授权生产认证切换。启用窗口下的旧凭据换发仍需独立 HTTP 证据；首个受保护业务路由还必须单独证明目标 Session 的锁定/version/角色权限矩阵。
