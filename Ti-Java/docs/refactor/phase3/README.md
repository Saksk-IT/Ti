# Phase 3：对比工具与认证兼容增量

> 状态：两条 Phase 3 operation 的 Java 实现、p3-009 同快照读写比较、本地切换/回滚、最终 WORM 与独立抽取验收均已完成；生产切换仍为 0，其余 609 个 operation 仍 pending，不能把本阶段增量写成整个重构完成。

## 1. 冻结基线与覆盖规则

Phase 0～2 的事实与机器合同保持不可变：

- `../02-route-parity-matrix.csv` 仍是 Phase 0 冻结的 592 条 Flask 规则、展开后 611 个 `path + method`；其 SHA-256 由 `effective-route-parity-status.json` 固定。
- `../../../contracts/openapi.json` 仍是 Phase 1 的 OpenAPI 3.1.2 初稿，不因阶段 3 的局部迁移重生成。
- `../phase2/application-api-shape-status.json` 仍准确描述 Phase 2 的“0 路由、0 公开操作”。

Phase 3 使用显式覆盖层，而不是改写历史事实：

| 增量 | 作用 |
| --- | --- |
| `route-parity-delta.csv` | 以 `route_id + path + method` 覆盖恰好两条 operation 的 owner 和迁移状态 |
| `effective-route-parity-status.json` | 物化“基线 611、migrated 2、pending 609、生产切换 0”的有效视图 |
| `application-api-shape-status.json` | 固定 2 个路由操作、5 个公开应用方法，以及其他九个模块仍为空的公开形状 |
| `../../../openapi/phase3-authentication.openapi.json` | 两条 operation 的自包含 OAS 3.1.2 增量；未命中 operation 保留 Phase 1 基线 |

覆盖层遇到未知 key、重复 key、基线字段不匹配或超过两条 operation 必须失败；不得通过把基线重新生成成“当前事实”来抹去阶段历史。

`GET /api/csrf` 是目标安全辅助端点，不是旧 Flask 迁移路由，因此不进入两条 delta operation 或 migrated 计数；OpenAPI 顶层 `x-ti-supporting-security-endpoints` 明确登记其用途和后续目标安全 API 契约状态，避免把引用它的登录流程误解为未声明的旧路由迁移。

`migrated` 在本层表示 Java 已有真实 Controller、应用 API 和所列 Java 契约/集成证据；这两条 operation 还各自绑定了 p3-009 的真实 Flask/Java 同快照报告。它仍不表示生产流量已切换；有效视图保持 `production_cutover=false`，未命中的 609 个 operation 继续 pending。

## 2. 当前两条 Java operation

### `GET /api/auth/login-methods`

- HTTP 适配器调用 `operations` 的 `OperationsApplicationApi#getLoginMethods`；旧矩阵最初按 legacy auth 包推到 `identity`，Phase 3 依据 `system_config` 所有权把目标 owner 校正为 `operations`。
- 返回旧信封完整键集合：`status=success`、`code=0`、`message=""`、动态 `request_id`，`data` 仅含 `phone_login_enabled`、`wechat_login_enabled`、`default_mode`；固定 `X-Request-ID` 必须在响应头和正文中原样回显。
- 旧端安全元数据也进入黄金契约：`Vary: Origin, Cookie`、`X-Content-Type-Options: nosniff`、`X-Frame-Options: SAMEORIGIN`，且该公开 GET 不产生 Spring 默认缓存禁止头。Content-Type 按 HTTP 媒体类型语义严格比较，OWS/大小写不构成差异，但 charset 缺失、不同或额外参数仍失败。
- PostgreSQL `system_config` 值优先，空/缺失时使用与旧服务一致的环境回退和默认开启语义；`default_mode` 按 phone → qr → password 决定。
- 集成测试在 GET 前后核对 PostgreSQL 与 Redis 指纹，证明该 Java 读取没有持久副作用。
- p3-009 冷请求按设计观察到旧 Flask 新建 1 个明确排除的 Flask-Limiter 可重建运行时 Key，因此冷报告以唯一差异 `/legacy/redis/excluded_runtime_key_count` 失败；这不是业务事实或持久文件副作用。预热后重采样，旧/新 auditor 均 before=after，暖报告零差异通过，双方规范化正文 SHA-256 同为 `5c0c83dfdf82832fd41c1a737a23142647554dfd665daee02e22fde414584571`。

### `POST /api/login`

- HTTP 适配器调用 `identity` 的 `IdentityApplicationApi#authenticate`，仅接受绑定邮箱或大陆手机号加密码。
- 请求解析保留已观察到的 Pydantic 布尔输入集合，忽略未知字段；账号和密码各限制 1024 个字符，密码 UTF-8 编码再限制 4096 字节，redirect 限制 2048 字符。
- 重复邮箱查询最多读取两条并 fail closed；账号不存在也执行目标 KDF dummy work；账号已锁定在正确密码后返回旧 403 语义。
- 精确 Werkzeug scrypt 已是过渡目标；成功验证受支持 PBKDF2 时才以 compare-and-set 升级到 Flask/Java 双兼容的 `scrypt:32768:8:1`，并把 `has_password_set` 置真；不改变 `session_version` 或 `last_active`。
- 成功后通过与旧 Cookie 兑换共用的 `TargetSessionIssuer` 使既有目标 Session 失效，创建 Redis 服务端 Session，只写 `identity_id`、`session_version`、`authenticated_at`、`remember` 四个安全标量；角色和用户名不从 Cookie/Redis 授权。Session hash 采用 immediate/on-set-attribute 持久化，按 HMAC 身份索引最多保留 3 个，超出时淘汰最旧 Session；位于 Spring Session 外层的链尾协调过滤器清理由在途旧请求回写的已淘汰 hash。
- 本地 Cookie 为 `ti_dev_session`/`ti_dev_csrf`，生产为 `__Host-ti_session`/`__Host-ti_csrf`；旧 `session` Cookie 被过期。remember=true 时目标 Session Cookie 最长 7 天。
- 登录 Redis 限流使用 Lua 原子维护 global、HMAC-IP、HMAC-account 三维固定分钟桶，默认每 IP/账号 5 次、global 100 次；Redis 异常返回 503。KDF 使用进程级两个公平 permit，容量不足同样 fail closed 为 503。登录 JSON 在 Controller 解析前按真实输入流限制为 16 KiB，声明长度或实际内容超限都返回安全 413。
- 无既有 Session 时，`GET`/框架派生 `HEAD /api/csrf` 与所有 unsafe 方法在 CSRF 处理前先经过 global + HMAC-IP 分钟桶；随后生成的匿名 CSRF Session 默认 10 分钟。现有 Session 不重复消耗匿名 issuance 桶。
- Java 集成测试覆盖成功、错误密码、锁定、重复邮箱、缺 CSRF、哈希升级、Session 安全属性和无意外数据库变化。p3-009 又从同一快照恢复两套隔离资源，按 legacy 完整执行后再执行 Java 的顺序各发送一次登录；最终 HTTP、数据库、Session 和 Redis 语义报告零差异通过，没有共享写目标或双写。

## 3. 认证格式兼容与安全差异

- [`adr-amendment-0005-0006.md`](adr-amendment-0005-0006.md) 记录冻结 ADR 的 Phase 3 实施增量，不回写 Phase 1 历史。
- [`authentication-compatibility.md`](authentication-compatibility.md) 固定旧 JWT、Flask Session、Werkzeug 密码和目标 Session 的接受边界、kill switch 窗口，以及 Bearer 当前请求认证与 Flask Cookie 换发行为。
- [`approved-authentication-differences.md`](approved-authentication-differences.md) 记录 CSRF、Cookie/服务端 Session、安全 redirect、双兼容目标哈希升级、重复邮箱 fail closed，以及显式 Bearer 不回退等有意差异。
- 这些差异是 Phase 3 的 ADR-0005/0006 实施补充，不回写阶段 1 的已接受历史文本。

## 4. 双栈与切换证据边界

[`dual-stack-and-cutover-evidence.md`](dual-stack-and-cutover-evidence.md) 区分三类证据：比较器黑盒自测、Java/Testcontainers 行为证据、真实 Flask/Java 同快照运行报告。前两类不能替代第三类。

`infra/phase3/` 是 local/test 工具，不进入 Java 运行依赖；生产配置不得出现 Flask upstream、父目录挂载、introspection、影子请求或双写入口。

## 5. 可重复验证

从 `Ti-Java/` 运行：

```bash
./infra/phase3/verify-static.sh
./infra/phase3/topology/verify-static.sh
./infra/phase2/verify-in-maven-container.sh \
  -Dtest=io.saksk.ti.architecture.ModuleContractParityTest test
```

契约测试必须证明：

1. 冻结 route/OpenAPI 的 SHA-256 未漂移；
2. delta 恰好命中基线中的两个 operation，目标模块、旧状态与新状态完全匹配；
3. 有效状态为 migrated 2、pending 609、生产切换 0；
4. OpenAPI delta 只有这两条 operation，`x-ti-route-id` 与 route delta 一致；
5. 2 个路由操作与 identity/operations 的 5 个 Java 公开应用方法逐个匹配，其他模块仍没有虚构方法；
6. Phase 5 以前没有公开事件载荷。

## 6. p3-009 已完成证据与开放边界

- 固定制品为 legacy `sha256:324b50f5ac0b5daa4d0e96cd6c495221e241b4fb0df90efe4de94a73387fb1b4` 与 Java `sha256:1dfca1d79f5b6fe8fa40ec9958028f14ee6c68db5371ac6c331231bf6a4c6077`；Java 镜像为 arm64，revision label 是 `d988922-phase3-working-tree-p3-009`。证据以不可变镜像摘要为准。
- `CUTOVER initial` 报告 SHA-256 为 `ece1199c3e0bd3ca90df4756cc6709c1d211e03a621d2dce6cad5e5ebcf89091`。快照 `auth-parity-p3-009-cutover-initial` 的 payload/manifest/canonical SQL SHA-256 分别为 `de861dc2e975bcf5e18fffafe35c4751b6f876533e156f68012c5325e4564886`、`78ea4191b81cc286bdcf60eabf2fa8f7a31bfd407b8513de194cd9c213e157e1`、`d89272babf9b8b078f66d6b11418b40791eb1d5ee04852cc4fdf59dd6ca6870b`；来源停止后才捕获，目标使用全新卷，没有双写。
- 冷 `READ_COMPARE` 报告 SHA-256 为 `d733dc7f62c7b86dd185d0f2c731069cad6a2d2b82926d346ef2fd4ff8c275c2`，其预期失败只有上述 Flask-Limiter 运行时 Key 计数；暖报告 SHA-256 为 `37128ff0786211474f84f60a131934ebcbaac4c8cc0fa02bd5299f46a19590aa`，零差异且双方无采样期状态变化。
- `ISOLATED_WRITE_COMPARE` 报告 SHA-256 为 `3dc21a524bfae335d763ac49d4f480962c536ec5c99af021ac27b583ae9c40f5`。两侧初始/最终业务数据库分别精确等价，唯一批准的数据库迁移是公开夹具的 `has_password_set: false → true`；Session/Redis 语义等价且未知 Key 为 0。队列、对象存储和外部 sink 在该夹具中明确未配置，`runtime_observation_performed=false`，因此这里只证明配置边界等价，不把“未配置”写成运行态零写入观察。
- `ROLLBACK rb001` 报告 SHA-256 为 `3fca94f6841ade5a26f0f53669026a04ee7c5293616a5754ab20c745d9c6fc1a`。回滚快照 `auth-parity-p3-009-rollback-rb001` 的 payload/manifest/canonical SQL SHA-256 分别为 `48abf7e5cdcdc0832f1e0fff9f8ade1ac25e5723ab6318e311d7e116b0eac423`、`1dc6da935444ebeb39b82721aa279a2926415bd28184969625ac2fc7df9b7691`、`ae62f4c578b6d40446b4789de6800aa58a8cc1b070ba78cfc8e8d8115fb9a908`；Java 先停止，旧栈恢复到新 generation 卷，没有把旧卷重新挂回。
- 公开 PBKDF2 夹具已由 Java 实际登录升级为精确 Werkzeug `scrypt:32768:8:1`，`session_version` 与 `last_active` 不变；固定 Flask/Werkzeug 3.1.4 在 rollback 后接受该目标 hash 且不改写。该结论只覆盖公开测试夹具，生产/历史密码前缀清单仍 unknown。
- 完整 Maven 为 208 个 surefire + 22 个 failsafe，Phase 3 Python 门禁为 29 项比较器测试 + 59 项拓扑/审计/写证据测试，均为 0 failure/error/skip。
- 最终 WORM 使用临时生成且只读 configtree 挂载的登录限流 HMAC Secret，完成 PostgreSQL 18.4、70 表/617 列的 schema-only 隔离恢复、数据库 ACL、Hibernate `validate` 与 readiness；Secret 和临时恢复资源均已清理，结构报告不保存 dump。
- 仅复制当前 `Ti-Java/` 的独立目录已重新通过 Phase 1、Phase 2/3 静态门禁、Phase 3 数据面、完整 Maven 208+22、镜像构建和 Compose 健康检查。运行态审计在等价归一化 Docker Desktop `/host_mnt` 前缀后证明所有 bind source 都位于独立副本内且不引用原仓库，结束后临时目录、容器、网络和卷均无残留。
- 旧 JWT 的 HTTP 当前请求认证、Flask Session 的目标 Session 换发，以及目标 Session 每请求 PostgreSQL 重授权已经实现；仍需在真实启用 kill switch 的独立运行环境保存端到端证据，并在阶段 10 删除兼容 Secret/入口。默认关闭不是无限期保留的理由。
- 当前两条迁移路由均为匿名；后续首个受保护业务路由迁移时，必须把已实现的锁定、`session_version`、角色重授权纳入该路由的 HTTP 权限矩阵。
- local/Testcontainers Redis 已固定 `noeviction`；生产 Redis 策略与至少 32 字节 HMAC Secret 仍须在获批环境留运行态证据。以上本地证据不授权生产停服、数据迁移、DNS 或 Secret 操作，`production_cutover` 必须保持 `false`。
