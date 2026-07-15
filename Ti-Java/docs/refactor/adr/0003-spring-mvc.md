# ADR-0003：HTTP 栈统一采用 Spring MVC

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：HTTP API、文件传输、SSE、外部 HTTP 调用和请求线程模型

## 上下文

旧 Ti 的核心数据访问是 PostgreSQL/SQLAlchemy，目标实现将使用 Spring Data JPA、JDBC、事务和阻塞式外部集成。当前路由既有普通 JSON/HTML 请求，也有文件上传下载、教务和模型 HTTP 调用、SSE 流。把阻塞式 JPA 包装进 WebFlux 不会得到端到端非阻塞收益，反而会同时维护 Servlet 与 Reactor 两套上下文、异常和安全模型。

Spring 官方将 Spring MVC 定义为基于 Servlet API 的原始 Web 框架，并与 WebFlux 明确区分。目标契约也明确要求 Spring MVC，不允许用 WebFlux 包装阻塞 JPA。

## 决策

1. Java API 只引入 `spring-boot-starter-web`，使用 Spring MVC annotated controller、Jakarta Validation、Servlet Filter 与 Spring Security Servlet 支持。
2. 事务数据访问使用 JPA/JDBC 的同步 API；请求级外部 HTTP 默认使用 Spring `RestClient` 或受控同步客户端，必须设置连接、读取、总调用超时。
3. 兼容 SSE 由 `messaging` 模块的 MVC 输出适配器实现，可使用 `SseEmitter`；连接在线与否不影响 PostgreSQL 中消息/通知事实。心跳、断线、重复事件和降级轮询均需契约测试。
4. 受控下载可使用 `Resource`/`StreamingResponseBody`；大文件导入导出、模型解析、音频转码和脆弱教务查询不得长期占用请求线程，改为提交带幂等键的后台命令并返回既有兼容状态。
5. API 请求线程池、数据库连接池、外部客户端连接池必须分别有上限，不能依赖无界队列。Java 虚拟线程初始不默认启用；只有阶段 9 在目标资源与真实阻塞模型上测得收益，并证明连接池、ThreadLocal、安全上下文和可观测性正确后，才能用修订 ADR 开启。
6. 一个应用不并存 MVC Controller 与 WebFlux Handler。若未来某个独立部署单元确实需要反应式流，该单元必须有单独证据和 ADR，不得把 Reactor 类型泄漏进领域 API。
7. HTTP Controller 只负责协议适配和授权入口；业务事务由模块 application 用例拥有，不能在 Filter、序列化器或异步回调中隐式写业务表。

## 后果

正面后果：

- Servlet 安全、过滤器、事务和阻塞数据访问模型一致，迁移团队只需维护一套请求上下文。
- 文件、表单和旧 API 兼容行为可直接用 MockMvc/Testcontainers 验证。
- 长任务被迫显式进入后台命令，避免以“异步 Controller”掩盖不可恢复任务。

代价与风险：

- 每个阻塞调用都消耗请求线程，必须严格限制外部调用超时和并发。
- SSE 长连接需要独立容量规划，不能与普通 API 使用无界执行器。
- 若未来出现真正的高并发流式负载，可能需要独立部署单元，而不是在现有单体内混栈。

## 拒绝的方案

- **WebFlux + JPA：** 底层仍阻塞，会把阻塞工作搬到其他线程池并增加上下文传播复杂度。
- **MVC 与 WebFlux 同时启用：** 自动配置、安全链、异常格式和测试栈容易产生歧义。
- **在 Controller 内启动裸线程：** 进程重启不可恢复，无法观察幂等、重试和最终状态；旧教务 daemon thread 已是明确风险。
- **所有任务同步等待完成：** 导入导出、AI、音频和教务上游会放大超时与资源耗尽。
- **一开始启用虚拟线程：** 目前没有目标资源下的测量证据，且不能增加数据库/上游实际并发容量。

## 实施与验证约束

阶段 2 和后续门禁必须包括：

- Maven 依赖树中没有 `spring-boot-starter-webflux`，业务源码不引用 `reactor.core`、`WebClient`、`Mono` 或 `Flux`；
- MockMvc 覆盖状态码、Content-Type、表单、multipart、下载 Header、异常信封和鉴权顺序；
- Testcontainers 验证 Controller → application → JPA/JDBC 的事务提交与回滚；
- 外部 HTTP WireMock/等价 stub 验证连接超时、读取超时、重试上限、Request ID 与脱敏日志；
- SSE 测试覆盖连接、心跳、重连、重复事件、Redis 不可用和 PostgreSQL 事实可重建；
- 负载测试记录请求线程、连接池、SSE 连接数、p50/p95、超时与内存，不以提高线程数隐藏慢查询；
- 生产配置扫描不得出现无界 `Executor`，不得在 request handler 中创建 daemon thread。

## 事实证据

- 旧部署与 SSE/RQ 事实：[`../00-current-state.md`](../00-current-state.md) 第 4、5 节。
- 目标运行单元与阻塞访问约束：[`../01-target-architecture.md`](../01-target-architecture.md) 第 2、3、7 节。
- 旧教务任务与 SSE 资源记录：[`../03-data-ownership.csv`](../03-data-ownership.csv) 中 `scheduled_or_background_task` 与 `realtime_channel` 条目。
- Spring MVC 官方说明：<https://docs.spring.io/spring-framework/reference/web/webmvc.html>
- Spring MVC Servlet 栈：<https://docs.spring.io/spring-framework/reference/web.html>
