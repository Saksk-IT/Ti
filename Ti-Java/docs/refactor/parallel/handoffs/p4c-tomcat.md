# P4C-TOMCAT Worker Handoff

## 交接身份

- lane：`p4c-tomcat`
- Worker 代号：`P4C-TOMCAT`
- 分支：`codex/parallel-p4c-tomcat`
- `BASE_SHA`：`765e4470f1ddb60f0ce6f23227d6303961f47fcf`
- 唯一 ownership target：
  `Ti-Java/server/src/test/java/io/saksk/ti/integration/LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT.java`
- 本文件是协调合同允许的 lane 专属 handoff 例外，不扩大实现 ownership。

## 固定实现提交

- implementation commit：`cd7eba9bbee4edcb6a0e14fec5fdfdf613d2ea70`
- 推荐 INT 集成 SHA：`cd7eba9bbee4edcb6a0e14fec5fdfdf613d2ea70`

`git diff --name-status 765e4470f1ddb60f0ce6f23227d6303961f47fcf...cd7eba9bbee4edcb6a0e14fec5fdfdf613d2ea70`：

```text
A	Ti-Java/server/src/test/java/io/saksk/ti/integration/LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT.java
```

## 实现事实

新增的唯一 IT：

- 以 `TiApplication` 和 `RANDOM_PORT` 启动完整 Spring Boot/Tomcat；通过真实
  `java.net.http.HttpClient` 访问连接器，不使用 MockMvc。
- 使用固定摘要的 PostgreSQL 18.4 与 Redis 7.4.7 Testcontainers；真实业务服务访问
  PostgreSQL，真实 Session、交换守卫和三窗口限流器访问 Redis。
- 运行时断言生产实现类为 `PersonalBankUserCountsService`、
  `SessionAuthorityApplicationService`、`LegacyAuthenticationCompatibilityService`、
  `RedisLegacySessionExchangeGuard`、`RedisTargetSessionRegistry`、
  `TargetSessionIssuer` 和 `RedisPersonalBankUserCountsReadRateLimiter`。
- 200 先通过真实 Flask Session 交换签发 remembered Target Session，再让 GET/HEAD
  通过真实 Session authority、限流器与业务 JDBC；没有 mock application/auth/session/limiter port。
- 429 先通过一次真实 HTTP 请求创建限流三窗口，再把该真实 identity/hour Redis key
  置于 500 次边界；GET/HEAD 均由生产 Lua 限流路径产生 429 和完整限流头。
- 503 在持有重验证锁时暂停真实 Redis 容器，由生产限流器失败关闭为 503；随后恢复容器并
  等待 PONG，仅作为本 IT 的安全清理，不声明独立的
  `same_service_redis_outage_and_recovery_complete` 门已完成。
- GET 与 HEAD 分别从等价的 route quota fixture 状态开始，成对覆盖
  `200/302/400/401/403/404/429/500/503`；HEAD 状态与相关头等于 GET，响应体为 0 字节。
- 成对比较 `Content-Type`、`Location`、`Vary`、全部 CORS 响应头、三项安全头、
  `X-Request-ID`、规范化后的完整 `Set-Cookie` 语义，以及
  `X-RateLimit-Limit`、`X-RateLimit-Remaining`、`X-RateLimit-Reset`、`Retry-After`。

没有发现需要 Worker 越权修复的生产行为缺陷。

## 验证结果

取得 `heavy-verify.lock` 后执行：

```text
./infra/phase2/verify-in-maven-container.sh \
  -DargLine=-javaagent:/root/.m2/repository/org/mockito/mockito-core/5.23.0/mockito-core-5.23.0.jar \
  -Dit.test=LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT \
  test-compile failsafe:integration-test failsafe:verify
```

结果：

- Java 25 / Maven 3.9.16 工具链门通过。
- 编译 275 个主源码和 236 个测试源码。
- `LegacyPersonalBankUserCountsRealTomcatHeaderMatrixIT`：10 tests，0 failures，
  0 errors，0 skipped，38.79 秒。
- Maven：`BUILD SUCCESS`，总用时 01:02。
- Failsafe 物理用例包含基础设施/生产 bean 断言和九组状态矩阵用例。
- 本轮 Redis、PostgreSQL、Ryuk 三个容器 ID 在退出后经 `docker ps -a` 核对均无残留。
- `git diff --check -- Ti-Java/` 通过。
- 未运行全仓 `clean verify`；定向命令已编译全部主/测试源码并只执行本 lane 的 10 个
  Failsafe 用例，避免占用串行重验证资源做无关全量轮。

## Heavy lock 记录

- 先等待合法持有者 `p4c-redis` 与 `p4c-pg` 依次释放，期间未启动 Maven/Docker。
- 通过原子 `mkdir` 取得
  `/Users/sak/.codex/coordination/ti-java/heavy-verify.lock`。
- owner 元数据：lane `p4c-tomcat`，branch `codex/parallel-p4c-tomcat`，
  当前 worktree，开始时间 `2026-07-18T13:18:42Z`，以及上方精确计划命令。
- Failsafe 报告和容器清理核对完成后，由本持有者删除 owner 并 `rmdir` 正常释放；
  后续 `p4c-redis` 于 `2026-07-18T13:21:02Z` 成功重新取得同一路径，证明本 lane 已释放。

## 风险、依赖与 INT 后续

- GET/HEAD 的限流头等价比较依赖测试夹具在两种方法前仅清除本 IT 专属 route-rate
  namespace；不会清除 Target Session，也不改变生产实现。
- 429 使用真实 Redis 和生产 Lua，但通过测试代码把已创建的 hour counter 置于边界，
  这是为了确定性构造长窗口拒绝，不是生产数据迁移。
- 503 覆盖真实 Redis 不可用时的完整响应头矩阵；独立的启动拒绝、中途断线、同实例恢复门
  仍由 `p4c-redis` lane 单独交接，INT 不应由本提交推导该中央授权位。
- 本提交复用既有 Phase 3/4B/4C schema 与 seed 资源且不修改其历史字节。
- INT 集成固定实现 SHA 后，如需推进
  `real_tomcat_complete_response_header_matrix_complete`，必须在取得
  `authority-chain.lock` 后新增追加式 successor/delta/acceptance，并按需串行更新
  README、`05-progress.md` 等中央文件；不得原地改写历史合同或 WORM。
- 与 `p4c-pg`、`p4c-redis` 无代码路径重叠；三 lane 的 main 集成和中央合同链仍须由 INT 串行完成。

## 边界声明

- 未修改 `main`，未提交或推送 `origin/main`。
- 未修改现有 `LegacyPersonalBankUserCountsNetworkIT`。
- 未修改 `SecurityConfiguration`、共享认证过滤器、Controller、限流器或任何生产代码。
- 未修改 README、`05-progress.md`、route/data ownership、OpenAPI、WORM、contract builder、
  acceptance、parity、successor、anchor、全局配置、Compose 或 `server/pom.xml`。
- 未覆盖或重生成任何历史合同、WORM、golden ledger 或 manifest。
- 根目录用户资产保持进入本 lane 时的既有状态且从未暂存：`AGENTS.md` 为 modified、
  `CLAUDE.md` 为 deleted，`.playwright-cli/`、`miniprogram-1/.gitignore`、`output/`
  为 untracked。
