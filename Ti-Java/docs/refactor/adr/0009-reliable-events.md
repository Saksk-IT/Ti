# ADR-0009：使用 PostgreSQL 持久化的 Spring Modulith 可靠事件发布

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：跨模块后续动作、后台命令、重试、Outbox 与 RQ 迁移

## 上下文

旧系统依赖 RQ、Redis Pub/Sub、daemon thread 和请求内副作用。阶段 0 发现 `default` 队列无人消费、教务任务的进程内凭据在重启后不可恢复、SSE 内存队列可能丢事件。新系统要求“模块内事务 + 领域事件 + Transactional Outbox/可靠发布”，但不需要 Kafka、分布式事务或一个包办所有语义的通用队列。

Spring Modulith 2.1.0 的 Event Publication Registry 会在原业务事务中为事务监听器保存发布记录；成功后标记完成，失败记录可查询和重投。它适合当前 PostgreSQL 单事实源与模块化单体，但默认 Schema 自动创建和无界保留都不符合本项目的迁移治理。

## 决策

1. 初始可靠发布实现采用 Spring Modulith 2.1.0 JDBC Event Publication Registry，存储在目标 PostgreSQL；不自研通用消息总线，也不引入 Kafka/RabbitMQ。
2. 聚合状态、业务幂等记录和事件 publication 在拥有模块的同一本地事务提交。事务回滚时三者都不存在；外部邮件、短信、模型、对象存储和通知发送不得发生在主事务提交前。
3. 禁止 Modulith 在运行时自动建表：JDBC schema initialization 关闭。阶段 5 在隔离测试数据库使用受控测试 Schema；正式 publication/幂等表只在阶段 8 通过审查后的 Flyway additive migration 进入恢复库。
4. 领域事件由生产模块拥有、不可变、版本化，只含 typed ID、发生时间、command/request ID 和最小业务快照，不含 JPA Entity、Secret 或完整敏感内容。消费者只能依赖公开事件 Named Interface。
5. 区分四类消息：
   - **领域事件：** 已发生的模块内事实；
   - **集成事件：** 经过稳定化、供跨模块/外部边界消费的事实；
   - **后台命令：** 需要执行并有状态、重试/取消/超时的工作；
   - **定时任务：** 只负责发现/提交幂等命令，不直接承载业务终态。
6. 消费者使用稳定幂等键和数据库唯一约束记录处理结果。Publication “已完成”不等于外部业务恰好一次；每个邮件、短信、AI、导入导出、通知和音频任务还要以 provider request ID/业务键防重复副作用。
7. 失败 publication 显式进入可观察状态，按事件类型配置有上限的指数退避、最大尝试、最后错误安全摘要和人工重投。未知异常不能无限热循环；失败不能被自动删除。
8. 完成记录默认保留 14 天后由受监控维护任务分批清理；失败/处理中记录不按完成保留策略删除。事件量和保留期在阶段 9按真实规模复核。
9. API 与 Worker 初期使用同一制品、不同 Profile。Worker 通过数据库争抢/锁机制领取任务，优雅停机等待有界时间；超时后任务可由其他实例按幂等协议接管。
10. RQ 切换必须先停止生产者、排空或按稳定键接管存量、记录最终处置，再启用 Java 生产者/消费者；Redis 队列不能作为迁移事实源。

SSE 只是 `messaging`/`intelligence` 的投递适配器：publication 成功与消息事实提交不依赖客户端在线。断线重连可重复收到事件，客户端/服务端按事件 ID 去重。

## 后果

正面后果：

- 业务状态和“必须发生的后续动作”在一次 PostgreSQL 事务中留下恢复证据。
- 进程崩溃、监听器失败和重复投递可观测、可重试，不依赖 Redis 持久性。
- 不增加消息 broker 运维单元，符合当前规模与部署约束。

代价与风险：

- Publication 表会增加事务写和清理成本，需要索引、容量与保留治理。
- “至少一次投递”要求每个消费者自行实现业务幂等，不能靠框架宣称恰好一次。
- 阶段 8 Flyway baseline 前只能在隔离测试 Schema 验证，不能提前把测试 DDL 当生产迁移。

## 拒绝的方案

- **事务提交后直接内存发布：** 进程在提交与发布之间崩溃会静默丢失后续动作。
- **所有事情放一个 Redis/RQ 队列：** Redis 可淘汰、队列语义混杂，旧系统已有无人消费任务证据。
- **现在引入 Kafka/RabbitMQ：** 没有吞吐或跨服务隔离测量，增加部署和一致性复杂度。
- **让 Modulith 自动初始化生产 Schema：** 绕过 Flyway、审查和恢复演练。
- **把 Entity 序列化为事件：** 泄漏内部模型，回放会受懒加载和 Schema 演进影响。
- **把重试当恰好一次：** 外部调用可能成功但响应丢失，必须依赖稳定幂等键/查询确认。

## 实施与验证约束

必须进行故障注入和并发测试：

- 主事务在 publication 写入前/后失败，验证业务事实与 publication 同生共死；
- Listener 在外部调用前、调用成功后但完成标记前、结果事务中崩溃，重启后业务结果不重复；
- 两个 Worker 并发领取、租约过期、时钟偏差和优雅停机不造成双执行终态；
- Redis/邮件/短信/模型/对象存储不可用时，主事实仍提交且 publication 可观察；
- poison event 达最大次数后停止热重试，保留脱敏错误与 Request ID，可人工重投；
- 完成记录清理不触碰失败/处理中记录，批量清理不长时间锁业务表；
- Modulith 测试验证事件只能经公开接口消费，DAG 不因监听器产生反向同步调用；
- 切换报告对旧 RQ 每个 job 给出完成、接管、取消或失败状态，未知数为零。

## 事实证据

- 旧队列、后台线程和 SSE 风险：[`../00-current-state.md`](../00-current-state.md) 第 4 节及 [`../03-data-ownership.csv`](../03-data-ownership.csv)。
- 目标事务与可靠发布：[`../01-target-architecture.md`](../01-target-architecture.md) 第 7 节。
- 任务切换/回滚：[`../04-migration-runbook.md`](../04-migration-runbook.md)。
- Spring Modulith 事件发布注册表：<https://docs.spring.io/spring-modulith/reference/events.html>
- Spring Modulith 2.1.0 EventPublicationRegistry API：<https://docs.spring.io/spring-modulith/docs/current/api/org/springframework/modulith/events/core/EventPublicationRegistry.html>
