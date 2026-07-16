# Phase 3 双栈比较与切换证据状态

## 1. 证据等级

| 等级 | 能证明什么 | 当前状态 |
| --- | --- | --- |
| A：工具与机械切换 | 比较器/拓扑门禁能拒绝同端口、同资源、非回环、生产标识、覆盖报告和共享卷；结构化差异不泄漏原值；隔离容器可以机械 stop/restore/start/rollback | 29 项 READ_COMPARE/ISOLATED_WRITE_COMPARE 与 59 项 topology/auditor/write-capture 门禁通过；p3-009 的真实本地 CUTOVER/ROLLBACK 和 PG18.4/Redis 数据面验证通过 |
| B：单运行时与关键路径 | Java 在 Testcontainers PostgreSQL/Redis 上的路由、哈希升级、Session、错误和副作用行为；固定旧 Flask 对 Java 目标 hash 的实际接受行为 | 完整 Maven 为 208 个 surefire + 22 个 failsafe；公开 PBKDF2 夹具已实际升级到双兼容 scrypt，并在 rollback 后由固定 Flask/Werkzeug 3.1.4 接受且不改写 |
| C：真实双运行时 | 同一脱敏快照恢复到两套独立资源，真实 Flask/Java 进程分别执行相同请求，保存结构化 HTTP/终态报告 | p3-009 已为本阶段两条 operation 完成：暖 GET 零差异报告与隔离登录写终态零差异报告均通过；不扩展到其余 609 个 operation 或生产切换 |

只有 C 级可以支持“Java/Flask 对同一黄金请求一致”的结论。p3-009 的 C 级结论严格限定为 `GET /api/auth/login-methods` 和 `POST /api/login` 两条 operation；它不把 `production_cutover` 改为 true，也不证明其余路由完成。

## 2. `READ_COMPARE` 当前边界

`infra/phase3/read_compare.py` 只接受 local/test、GET/HEAD、带显式不同端口的回环 HTTP origin；两边数据库、Redis、卷的六个身份指纹必须全部非空且两两不同。每次请求前后由独立 auditor 提供状态摘要，数据库、Redis、卷、队列、对象存储或外部写计数任一变化即失败。

规范化规则按 operation 精确白名单；数组默认有序，missing 与 null 不合并。报告只保存状态、Content-Type、安全 header、长度、摘要和差异值摘要，不保存原始正文、请求头、Cookie、JWT、openid 或差异原值。

`normalization-rules.v1.json` 已精确登记真实 route id `88d7dc05cdbb`，没有忽略正文指针、数组或响应头。冷报告 SHA-256 为 `d733dc7f62c7b86dd185d0f2c731069cad6a2d2b82926d346ef2fd4ff8c275c2`：旧 Flask 首次请求创建 1 个明确排除的 Flask-Limiter 可重建运行时 Key，因此只在 `/legacy/redis/excluded_runtime_key_count` 出现预期差异；这不是业务事实或持久文件副作用。暖报告 SHA-256 为 `37128ff0786211474f84f60a131934ebcbaac4c8cc0fa02bd5299f46a19590aa`，差异数为 0，双侧 before/after 均相等，规范化正文 SHA-256 同为 `5c0c83dfdf82832fd41c1a737a23142647554dfd665daee02e22fde414584571`。工具 stub 仍不能冒充这组业务证据。

## 3. 写比较不是双写

`POST /api/login` 的最终比较必须：

1. 从一个带 SHA-256 的脱敏静止快照恢复 `legacy-write` 和 `java-write` 两套全新 PostgreSQL；
2. 两边使用不同角色、端口、Redis、Session namespace 和卷；
3. Flask 只向 legacy-write 发一次命令，Java 只向 java-write 发等价命令；
4. 比较 HTTP、`users.password_hash/has_password_set/session_version/last_active`、Session/限流 Redis 摘要和非预期写入；
5. 明确批准双兼容过渡 hash、Session 存储和 Cookie 差异，其余业务事实须相等；
6. 批次完成后销毁两套环境并从快照恢复，禁止清表复用。

任何生产请求复制、一个进程连接两边写库、共享 Redis 或把执行中增量同步到另一边都属于禁止的 dual write/shadow write。

## 4. stop/restore/start 与 rollback

`infra/phase3/topology/` 将本地演练固定为：先确认目标不存在 → 停来源 API → 捕获并校验 snapshot → 恢复到全新目标 PG/Redis/卷 → 比较规范化 SQL fingerprint → 启目标 API。反向 rollback 同样先停 Java，并为旧运行时分配新的 generation 卷；不把旧卷重新挂回，不允许两边同时运行写入。

脚本只接受固定 Compose、本机 Unix Docker socket、local/test 环境和 digest 固定镜像。它不读取父目录 Flask 源码、根 Compose 或既有数据卷。

p3-009 固定 legacy 镜像为 `sha256:324b50f5ac0b5daa4d0e96cd6c495221e241b4fb0df90efe4de94a73387fb1b4`，固定 Java 镜像为 `sha256:1dfca1d79f5b6fe8fa40ec9958028f14ee6c68db5371ac6c331231bf6a4c6077`。`CUTOVER initial` 报告 SHA-256 为 `ece1199c3e0bd3ca90df4756cc6709c1d211e03a621d2dce6cad5e5ebcf89091`；来源 API 先停止，来源卷保留，目标从全新卷启动且未观察到双写。

切换快照 `auth-parity-p3-009-cutover-initial` 的 payload/manifest/canonical SQL SHA-256 分别为 `de861dc2e975bcf5e18fffafe35c4751b6f876533e156f68012c5325e4564886`、`78ea4191b81cc286bdcf60eabf2fa8f7a31bfd407b8513de194cd9c213e157e1`、`d89272babf9b8b078f66d6b11418b40791eb1d5ee04852cc4fdf59dd6ca6870b`。同源隔离登录写报告 SHA-256 为 `3dc21a524bfae335d763ac49d4f480962c536ec5c99af021ac27b583ae9c40f5`，HTTP、最终业务数据库、Session 与 Redis 语义均等价；队列、对象存储和外部 sink 明确未配置且没有执行运行态观察，因此只证明配置边界等价。

Java 实际把公开 PBKDF2 夹具升级为精确 `scrypt:32768:8:1` 后执行正式 `ROLLBACK rb001`。报告 SHA-256 为 `3fca94f6841ade5a26f0f53669026a04ee7c5293616a5754ab20c745d9c6fc1a`；回滚快照 `auth-parity-p3-009-rollback-rb001` 的 payload/manifest/canonical SQL SHA-256 分别为 `48abf7e5cdcdc0832f1e0fff9f8ade1ac25e5723ab6318e311d7e116b0eac423`、`1dc6da935444ebeb39b82721aa279a2926415bd28184969625ac2fc7df9b7691`、`ae62f4c578b6d40446b4789de6800aa58a8cc1b070ba78cfc8e8d8115fb9a908`。固定 Flask/Werkzeug 3.1.4 随后接受该目标 hash 且保持其不变；该公开夹具结论不能推断生产/历史密码前缀分布。

因此，`04-migration-runbook.md` 中的生产模板仍只是未来授权后的协议；本地成功不授权生产停服、DNS、数据库或 Secret 操作。快照含敏感数据库内容，原始快照、请求、响应和凭据工件不得提交；仓库文档只记录不可逆摘要。

## 5. 生产依赖否定清单

阶段 3/10 门禁必须静态和运行态确认生产制品没有：

- Flask upstream、introspection URL 或父目录相对读取；
- 旧代码目录/容器/卷挂载；
- comparator、影子请求或双写代理；
- 用 Cookie/JWT role claim 直接授权；
- 默认启用且无截止时间的 legacy verifier；
- 真实 Secret、DSN、Cookie、Token 或脱敏快照工件。
