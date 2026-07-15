# ADR-0002：采用领域模块化单体与轻量六边形边界

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：Java 后端代码结构、模块通信、事务和部署单元

## 上下文

旧系统已有 13 个已注册 Flask 业务模块，但路由、SQLAlchemy 模型、原生 SQL、共享数据库会话和服务相互穿透。阶段 0 盘点得到 592 条运行时 URL 规则、611 个 `path + method` 组合和 154 类持久化资源；这说明 Ti 是一个业务面广、事务关联多的系统，但没有证据表明需要用网络边界拆成大量服务。

本次重构首先要解决的是类型安全、资源唯一所有权、事务边界和可测试性。若直接按 `controller/service/repository/model` 技术层翻译，旧耦合会换一种语言继续存在；若直接拆微服务，则认证、考试、学习、通知等跨域行为会被迫引入远程一致性和运维复杂度。

## 决策

后端采用一个 Maven 应用、一个 Spring Boot 可执行制品，通过 Spring Modulith 和 Java package 表达领域模块。顶层包固定为 `io.saksk.ti`，业务模块固定为：

`identity`、`catalog`、`personalbank`、`learning`、`assessment`、`community`、`messaging`、`campus`、`coding`、`intelligence`、`operations`，另有极小的 `sharedkernel`。

每个业务模块遵守以下边界：

1. 代码先按业务模块分包，再按需要使用 `api`、`application`、`domain`、`infrastructure`；简单 CRUD 可以合并空层，但不能隐藏事务和基础设施访问。
2. `api` 暴露 HTTP DTO、公开应用 API 和已版本化事件；需要额外公开的包必须用 Modulith Named Interface 显式声明。
3. `application`、`domain`、`infrastructure` 默认为模块内部。JPA Entity、Spring Data Repository、数据库适配器和外部客户端实现绝不公开。
4. 每张表和每类持久化资源只有一个写入模块。跨模块对象只保存稳定 ID，不建立跨模块 JPA 关联，也不共享 Entity 或 Repository。
5. 当前请求必须立即获得结果时，调用对方公开应用 API；非关键后续动作发布领域事件。不能以共享数据库会话绕过模块 API。
6. 同一模块内的聚合变更和可靠事件记录使用一个本地 PostgreSQL 事务；不引入分布式事务。
7. `sharedkernel` 仅允许稳定 ID、时钟抽象、分页值对象、错误信封和 Request ID 等无业务所有权类型。它不得包含 Repository、HTTP 客户端、业务服务或“万能 utils”。
8. API 和 Worker 初期使用同一个 Java 制品、不同 Spring Profile；只有构建时间、独立发布或资源隔离出现可重复测量证据时，才评估 Maven 子模块或新部署单元。

模块的允许依赖由 ADR-0010 和机器可读模块合同共同定义；未列出的依赖一律禁止。后台 HTTP 适配器归资源所有模块，`operations` 不能成为可越权修改所有实体的“后台总模块”。

## 后果

正面后果：

- 单进程内保留必要的事务一致性，同时能用编译和 Modulith 测试阻止边界穿透。
- 每个领域可按垂直切片独立迁移、测试和回滚，不需要在早期处理服务发现、网络重试和分布式事务。
- 一个制品可降低目标 2C/4G 环境的部署与内存成本。

代价与风险：

- 单体仍需严格治理；若放宽包可见性，模块边界会退化为目录命名。
- 公开 API 变更需要协调调用方，领域事件需要版本与幂等策略。
- 极少数需要资源隔离的任务不能在 API 请求线程执行，应转入同制品 Worker 或满足 ADR-0008 后的 Python Worker。

## 拒绝的方案

- **立即拆微服务：** 当前无吞吐、团队或独立发布证据，反而会提前引入网络故障和数据一致性问题。
- **全局技术层目录：** 无法表达业务所有权，Repository 和 Entity 会自然成为全局共享对象。
- **为每个领域建立 Maven 子模块：** 当前没有构建隔离收益证据，先使用 package + Modulith 的可执行边界。
- **保留共享 SQLAlchemy 式数据库会话思路：** 让一个模块直接改另一模块表会破坏唯一所有者和事务可追踪性。
- **建立通用 `common` 服务层：** 会把旧耦合集中到新垃圾场；共享内核必须保持无业务能力。

## 实施与验证约束

阶段 2 起必须具备以下自动化门禁：

```java
ApplicationModules.of(TiApplication.class).verify();
```

并补充 ArchUnit/编译测试断言：

- 所有 11 个业务模块均被识别，依赖无环；
- 只有显式 API/Named Interface 可跨模块访问；
- 任何模块都不能引用另一模块的 `..domain..`、`..infrastructure..`、Entity 或 Repository；
- `sharedkernel` 不依赖业务模块和 Spring 基础设施；
- 每个模块至少有一个 `@ApplicationModuleTest`，默认以 `STANDALONE` 或显式依赖模式启动；
- 模块合同中的资源与 `03-data-ownership.csv` 一一对应且无重复所有者；
- 从临时独立目录运行 `./mvnw verify` 时，不访问父目录旧 Flask 源码。

任何“临时”跨模块内部引用都必须先使架构测试失败，再通过修改公开合同或本 ADR 解决；禁止增加忽略规则让流水线变绿。

## 事实证据

- 旧系统规模与耦合：[`../00-current-state.md`](../00-current-state.md) 第 2～4 节。
- 初始领域边界与部署单元：[`../01-target-architecture.md`](../01-target-architecture.md) 第 3～6 节。
- 唯一资源所有权：[`../03-data-ownership.csv`](../03-data-ownership.csv)。
- Spring Modulith 模块能力：<https://spring.io/projects/spring-modulith/>
- Spring Modulith 结构验证规则：<https://docs.spring.io/spring-modulith/reference/verification.html>
- Spring Modulith 模块集成测试：<https://docs.spring.io/spring-modulith/reference/testing.html>
