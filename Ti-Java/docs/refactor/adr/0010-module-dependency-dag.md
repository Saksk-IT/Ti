# ADR-0010：固定模块公开接口与有向无环依赖

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：11 个业务模块、`sharedkernel`、Web 适配边界与跨模块事件

## 上下文

阶段 0 的目标图只是候选。阶段 1 结合真实权限代码和 `public_subject_users` 资源，证明 `catalog` 的目录可见性需要窄查询 `identity` 的账号/管理员状态，因此机器合同新增 `catalog → identity`。物理数据库还有 76 个跨 owner 外键 ID，但外键不应自动变成 Java 对象依赖。

若允许任意同步调用，`messaging`、`operations` 或 `sharedkernel` 很快会变成全能模块并形成环；如果完全禁止跨模块调用，又会迫使 Controller 直接拼 Repository。需要把允许边精确固化，并由 Spring Modulith 自动验证。

## 决策

`docs/refactor/phase1/module-contracts.json` 是模块 ID、公开应用 API、内部包、拥有资源和允许依赖的机器权威。Java 实现必须使用相同模块 ID 和根包 `io.saksk.ti`。允许依赖固定如下（箭头左侧为消费者）：

| 消费模块 | 允许依赖 |
| --- | --- |
| `identity` | `sharedkernel` |
| `catalog` | `sharedkernel`, `identity` |
| `personalbank` | `sharedkernel`, `identity`, `catalog` |
| `assessment` | `sharedkernel`, `identity`, `catalog`, `personalbank` |
| `learning` | `sharedkernel`, `identity`, `catalog`, `personalbank`, `assessment` |
| `community` | `sharedkernel`, `identity`, `catalog` |
| `campus` | `sharedkernel`, `identity` |
| `coding` | `sharedkernel`, `identity`, `catalog` |
| `intelligence` | `sharedkernel`, `identity`, `catalog`, `personalbank`, `coding` |
| `messaging` | `sharedkernel`, `identity`, `assessment`, `learning`, `community`, `campus`, `coding`, `intelligence` |
| `operations` | `sharedkernel` |
| `web`（适配边界） | `identity`, `catalog`, `personalbank`, `assessment`, `learning`, `community`, `campus`, `coding`, `intelligence`, `messaging`, `operations` 的公开 API |

边的语义进一步限制为：

1. 一般同步依赖只能指向 provider 的 `api` Named Interface，传递 typed ID 和 provider 定义的不可变 DTO。消费者不能导入 provider 的 application/domain/infrastructure。
2. `messaging` 对 `assessment`、`learning`、`community`、`campus`、`coding`、`intelligence` 的边只用于消费 provider-owned 公开事件；禁止从消息消费者同步回调生产者。`messaging → identity` 仅允许解析发送者/接收者的窄只读身份摘要。
3. `learning → assessment` 只消费考试公开结果/完成事件或调用机器合同列出的窄查询；`assessment` 不反向依赖 `learning`。
4. `catalog → identity` 仅用于主体存在性、管理员/科目可见性判定；`identity` 不依赖 `catalog`。`public_subject_users.user_id` 保持标量外部 ID。
5. `operations` 不集中实现各领域后台 CRUD。后台用户、题库、社区等 Controller 位于资源所有模块；`operations` 只拥有系统设置、备份、平台弹窗、审计/支付等平台能力。
6. 跨 owner 数据引用只保存标量 ID；禁止跨模块 JPA relationship、共享 Entity、共享 Repository 和一个事务直接写多个 owner 表。物理外键用于数据完整性，不授权 Java import。
7. `sharedkernel` 只含 typed scalar ID、时钟/Request ID、稳定错误/结果原语和 outbox envelope；不含 Entity、Repository、业务服务、模块 DTO 或可变聚合。
8. 未列出的依赖默认拒绝。新增边必须先更新机器合同、给出真实用例/替代方案/环检测证据，并修订本 ADR；不能通过反射、事件总线字符串或移动类到 sharedkernel 绕过。

该图按 consumer → provider 方向是 DAG。Web 是 HTTP 适配边界而不是拥有业务表的 Modulith 领域模块；Vue 浏览器应用不进入 Java compile-time DAG。

## 后果

正面后果：

- 跨模块调用范围可由编译和机器合同证明，后续执行者无需猜测依赖方向。
- 数据库物理外键与 Java 聚合边界解耦，资源仍保留完整性约束。
- `messaging` 可以消费事件而不迫使所有领域同步依赖消息模块。

代价与风险：

- 某些旧的跨模块 SQL 需要改为公开查询或事件，迁移工作量高于直接复用 Repository。
- 事件消费者在代码层依赖生产者公开事件包，事件变更必须版本化。
- 机器合同和 Java package-info 必须同步维护，否则门禁会失败。

## 拒绝的方案

- **允许任意模块互调：** 很快形成循环和内部实现泄漏，Modulith 只能成为文档工具。
- **让 `operations` 拥有全部后台写入：** 会跨越所有数据所有权并成为全能依赖中心。
- **让 `messaging` 被所有生产模块同步调用：** 与它消费生产者事件的边组合后形成双向依赖。
- **把共享 Entity 放 `sharedkernel`：** 物理表关系会扩散成全局对象图，所有者失效。
- **根据外键自动生成模块依赖：** 76 个跨 owner ID 会把数据库完整性误当业务调用方向。
- **用字符串事件/反射规避依赖检查：** 编译通过但契约不可发现、不可重构，也无法验证 payload。

## 实施与验证约束

每个模块的 `package-info.java` 使用 `@ApplicationModule(allowedDependencies = …)` 和 Named Interface 表达机器合同；测试必须调用：

```java
ApplicationModules.of(TiApplication.class).verify();
```

阶段 2 起门禁还必须验证：

- 11 个业务模块和 Web 适配边界恰好存在，允许边与 `module-contracts.json` 完全一致；
- 拓扑排序覆盖全部业务模块且无环；故意加入非法反向依赖的测试夹具必须失败；
- 只有公开 API/事件 Named Interface 可被跨模块引用，内部包、Entity、Repository 引用数为零；
- `sharedkernel` 不依赖任何业务模块，内容符合 allowlist；
- 所有 154 个阶段 0 资源只出现在一个模块合同中，表和非表资源均无遗漏/重复；
- Web Controller 只调用公开应用 API，不直接注入 Repository；
- 生成 Modulith 文档与机器合同 diff 为零，新增边没有 ADR 时构建失败。

## 事实证据

- 初始边界与候选图：[`../01-target-architecture.md`](../01-target-architecture.md) 第 4～6 节。
- 已接受机器合同：[`../phase1/module-contracts.json`](../phase1/module-contracts.json)。
- 数据资源与跨 owner ID：[`../03-data-ownership.csv`](../03-data-ownership.csv)。
- Spring Modulith 验证规则：<https://docs.spring.io/spring-modulith/reference/verification.html>
- Spring Modulith 应用模块基础：<https://docs.spring.io/spring-modulith/reference/fundamentals.html>
