# Phase 4C Redis 故障恢复 Worker handoff

## 交接标识

- lane：`p4c-redis`
- Worker：`Codex Worker / p4c-redis`
- 分支：`codex/parallel-p4c-redis`
- BASE_SHA：`765e4470f1ddb60f0ce6f23227d6303961f47fcf`
- 实现 commit SHA：`ad4d90b30cc5d244983fe759199f77ddeacdfc52`
- 推荐集成 SHA：`ad4d90b30cc5d244983fe759199f77ddeacdfc52`

## Ownership

唯一主目标：

`Ti-Java/server/src/test/java/io/saksk/ti/web/security/Phase4cUserCountsRedisOutageRecoveryIT.java`

Wang 在本 lane 明确授权的专用、非共享测试支持：

`Ti-Java/server/src/test/java/io/saksk/ti/web/security/support/Phase4cRedisNetworkGate.java`

本 handoff 使用协调合同唯一允许的附加写路径：

`Ti-Java/docs/refactor/parallel/handoffs/p4c-redis.md`

## 实现摘要

- 启动第一个随机端口 Tomcat 时，Redis 稳定端口没有 listener；先证明真实
  `ConnectException`，再证明服务上下文仍已启动且 API alias 返回安全 503。
- 专用 TCP gate 在运行时撤销 listener 并关闭全部已接受连接，恢复时在同一端口重新
  bind；状态检查和连接注册与关门操作互斥，不使用 Redis/网络 mock。
- 同一 Spring context、同一 Tomcat port、同一实例标识在 gate 恢复后重新返回 200；
  随后真实触发 429、等待 second key 自然过期并再次返回 200，排除永久 fail-open 和
  fail-closed。
- 通过生产 `RedisPersonalBankUserCountsReadRateLimiter`、生产
  `PersonalBankUserCountsReadRateLimitFilter` 和生产
  `LegacyPersonalBankUserCountsSecurityErrorWriter` 验证 second/hour/day 计数、首击 TTL
  不刷新、较短窗口拒绝不扣减较长窗口，以及 API/Web alias 隔离。
- 对 API JSON、Web 默认 HTML、Web `Accept: application/json` 三种 Redis 故障响应分别
  固定 503 body、Content-Type、Vary、Request-ID、安全头及无伪造 rate-limit headers。
- 以独立 HMAC 计算固定 `api|web`、`identity:v1|ip:v1` key，验证 raw identity/IP 不进入
  Redis key。
- 启动第二个独立随机端口 Tomcat/Spring context 和独立 Lettuce connection factory；
  两实例交替请求并在共享 Redis hour 窗口收敛为 `second=1/hour=4/day=3`。

## BASE 到实现 SHA 的路径差异

`git diff --name-status 765e4470f1ddb60f0ce6f23227d6303961f47fcf...ad4d90b30cc5d244983fe759199f77ddeacdfc52`

```text
A  Ti-Java/server/src/test/java/io/saksk/ti/web/security/Phase4cUserCountsRedisOutageRecoveryIT.java
A  Ti-Java/server/src/test/java/io/saksk/ti/web/security/support/Phase4cRedisNetworkGate.java
```

## 验证证据

最终定向验证：

```text
./infra/phase2/verify-in-maven-container.sh \
  -DargLine=-javaagent:/root/.m2/repository/org/mockito/mockito-core/5.23.0/mockito-core-5.23.0.jar \
  -Dit.test=Phase4cUserCountsRedisOutageRecoveryIT \
  test-compile failsafe:integration-test failsafe:verify
```

结果：`BUILD SUCCESS`；Failsafe `1` 个，failure/error/skip 均为 `0`；真实 Redis
Testcontainer、两个随机端口 Tomcat、真实运行时 `Connection refused` 均进入测试链。

最终标准验证：

```text
./infra/phase2/verify-in-maven-container.sh \
  -DargLine=-javaagent:/root/.m2/repository/org/mockito/mockito-core/5.23.0/mockito-core-5.23.0.jar \
  -Dit.test=Phase4cUserCountsRedisOutageRecoveryIT verify
```

结果：`BUILD SUCCESS`；Surefire `709` 个、Failsafe `1` 个，failure/error/skip 均为 `0`；
Spring Boot repackage 和脚本的可执行 JAR stale-class 门禁通过，总用时 `01:34`。

轻量验证：两个新增文件均通过 `git diff --check`；实现提交前 staged path 审计仅包含上述
两个实现文件。前置诊断轮曾分别暴露测试安全链 header writer 顺序和一个裸 TCP 竞态探针，
均已在最终证据轮前修正；这些失败轮不作为完成证据。

## Heavy lock 记录

- `2026-07-18T13:06:44Z` 原子取得
  `/Users/sak/.codex/coordination/ti-java/heavy-verify.lock`；完成初始诊断、Maven 子进程和
  Testcontainers 清理审计后，于 `2026-07-18T13:13:26Z` 随即释放。
- 等待 `p4c-pg` lane 正常使用并释放同一把锁，期间未运行 Maven/Docker/Testcontainers。
- `2026-07-18T13:21:02Z` 再次原子取得该锁；完成最终定向、标准 verify、Redis/Ryuk 清理
  审计后释放，`2026-07-18T13:24:31Z` 已确认锁不再由本 lane 持有。
- 未取得或触碰 `main-write.lock`、`authority-chain.lock`。

## 风险、依赖与 INT 后续

- 无生产缺陷；未请求修改生产 limiter、SecurityConfiguration、Controller 或全局配置。
- 多实例证据是同一测试 JVM 内两个完全独立的 Spring/Tomcat/Lettuce application
  instance，不是两个 OS JVM。若后续 acceptance 明确要求进程级隔离，需由 INT 另行追加
  进程级 successor/门禁；当前证据已覆盖独立 connector、context、connection factory 和共享
  Redis 原子收敛。
- 本测试用 test-only identity fixture 和最小 Security chain 只隔离 Redis 恢复变量；生产
  limiter/filter/error writer 均为真实实现。完整生产认证优先级继续由既有 Phase 4C HTTP/
  network 合同测试负责。
- second 窗口用 barrier 同时释放三个本地 HTTP 请求；极端 CPU starvation 仍可能跨越
  1 秒，但两轮最终目标执行均绿色，hour/day 与多实例证据已改为不依赖该时序。
- INT 如接受本 lane，应只集成固定实现 SHA
  `ad4d90b30cc5d244983fe759199f77ddeacdfc52`；任何 acceptance、successor、parity、WORM 或
  progress 追加均继续由 INT 串行完成。

## 保护声明

- 未修改任何中央权威文件、历史 contract、WORM、acceptance、parity、successor、route
  matrix/delta、data ownership、OpenAPI、`server/pom.xml`、Compose、全局配置、
  `SecurityConfiguration` 或共享认证过滤器。
- 未修改现有 `RedisPersonalBankUserCountsReadRateLimiterIT`。
- 根目录既有用户资产保持原样且从未暂存：继承的 `AGENTS.md` modified、`CLAUDE.md`
  deleted、`.playwright-cli/` untracked、`miniprogram-1/.gitignore` untracked、`output/`
  untracked；本 lane 未编辑、清理、覆盖或提交它们。
- 未检出、修改或推送 `main`，也未推送 `origin/main`。
