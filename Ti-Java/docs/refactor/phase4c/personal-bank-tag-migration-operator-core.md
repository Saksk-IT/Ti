# Phase 4C 个人题库标签迁移：Node C Operator Core

## 当前结论

Node C 已物化一个可显式调用、默认不可达的标签迁移 Operator Core，并取得当前工作树上的
定向绿色证据。它承接 Node A 的全局只读预检和 Node B 已外锚的耐久账本/冻结协议设计，提供
`prepare`、`freeze`、`apply`、`recover` 四个直接调用阶段；但它不是可部署的迁移任务，也没有
任何自动启动或生产接线。

本节点的授权上限只允许关闭三类事实：Operator Core 证据、有界 SQL 重试实现和 Operator Core
实现。固定合同与 Python/Java 验收桥、最终完整静态与 Maven 门禁均已绿色；但功能提交和后继
Git 外锚尚未完成，因此当前控制源仍不能自授权。路由权威保持
**13 migrated / 598 pending / 0 production cutover**，旧 Flask 仍是生产 owner。

## 调用与部署边界

`LegacyPersonalBankTagMigrationOperatorCore` 是普通 final Java 类型，只能由持有 operator
`DataSource`、`PersonalBankQuestionFactsApi` 与显式 `EvidenceVerifier` 的调用方直接构造并调用。
它没有 Spring stereotype、`@Bean`、Runner、Scheduler、HTTP/Controller、环境变量、文件或
Redis 接线，也不读取命令行参数或在应用启动时自动执行。签名证据由调用方传入并先经 verifier
验证；Core 不从环境或文件自行发现授权。Node C 只提供该外部注入接口；当前
`FixedEvidenceVerifier` 与 `RejectingEvidenceVerifier` 仅定义在 PostgreSQL IT 中，不是生产
签名验证实现，也不存在 Spring、文件、环境或其他自动发现接线。

数据库结构仅存在于测试资源：

- `076-legacy-personal-bank-tag-operator-core-schema.sql`：Node C test-only schema、角色、ACL、
  trigger 与函数；
- `077-legacy-personal-bank-tag-operator-core-seed.sql`：隔离的 disposable fixture 数据。

两者只由 Testcontainers 装载，不在生产 Flyway、`src/main/resources`、Compose 或启动路径中。
本节点没有创建生产 schema/index、Flyway baseline 或 DDL 执行入口。

## 状态机、收据与恢复

Core 只推进 Node B 已批准设计中的
`PLANNED(v0) -> FROZEN(v1) -> APPLYING(v2) -> APPLIED(v3)`。受支持的 source、target 与
membership durable drift 会失败关闭到 `BLOCKED`；schema、ACL、identity 或 evidence 等前置
拒绝保持 `UNAVAILABLE` 且不产生业务 DML。运行身份同时绑定 migration/run UUID、备份
manifest、cluster/database identity、
preflight/source/plan/target/membership 摘要和逐阶段签名收据；CAS 谓词要求全部事实、状态和版本
匹配，并发 stale writer 只能一胜一败。freeze、apply 与 recovery 必须分别携带 source、target、
membership 三个 writer-stop receipt 字段；任一缺失、互换或漂移都会失败关闭，单一字段不得
替代三类证明。底层制品签名、签发者 purpose 与三个域的真实性仍属于尚未实现的生产 verifier
边界。

每个来源在独立原子事务中先写 append-only receipt，再写规范化 target；数据库 guard 阻止没有
对应 receipt 的 target 和 receipt 不完整的 `APPLIED`。恢复严格 receipt-first：按
`source_row_id` 排序的 receipts 必须是 manifest 的严格前缀，前 N 个来源逐项为 FINAL，剩余来源
必须仍保持 PREAPPLY；任意稀疏 receipt、跳过较早来源、摘要/identity/disposition 不一致都会以
`RECEIPT_MISMATCH` 或更具体的稳定 failure code 失败关闭。只有完整收据、终态与重算目标摘要
一致时才返回零 DML 的已提交结果。

提交结果未知不会盲目重试。双版本测试使用代理让数据库真实 `commit` 后丢弃调用方看到的 ACK，
随后以新连接走 receipt-first recovery，确认已持久化事务且不重复插入。该测试是明确标注的
commit-ACK-discard 模拟，不冒充真实网络断连或生产故障演练。

## 有界 SQL 重试与固定超时

每个事务 attempt 使用全新 JDBC connection、backend PID 和 transaction ID；最多 3 attempts、
2 retries。只有数据库真实返回的根 SQLSTATE `40001` 和 `40P01` 可以在回滚成功后重试，连接
获取、连接设置、rollback、commit 结果未知和 close 失败均为终止错误。PG16.14/18.4 都覆盖
两种真实错误的成功重试与耗尽路径；deferred foreign-key violation `23503` 在 commit 阶段
失败且不重试。

所有事务，包括 session 建立时的 schema/identity 检查与只读恢复，都在执行可能阻塞的 SQL 前
设置固定事务局部上限：

- `SET LOCAL statement_timeout = '30s'`；
- `SET LOCAL lock_timeout = '5s'`；
- `SET LOCAL idle_in_transaction_session_timeout = '60s'`。

双版本锁阻塞用例证明 setup 与 recovery 都在 4–9 秒内以稳定 `SQL_FAILURE` 返回，释放阻塞后同一
功能可以继续使用，期间 schema/业务指纹不变。

## Schema、ACL 与 hostile search_path

每次 Operator session 和 recovery session 在业务读写前都执行 fail-closed schema verifier。
它闭合 metadata、relation、column、trigger、sequence、函数定义/owner/security 属性、角色属性、
角色 membership、schema/table/column/database 权限与全局 ACL/function closure。额外授权、列级
敏感权限、角色继承、意外函数、函数安全属性或 trigger 漂移都会在业务 DML 前拒绝。

所有生产 SQL 使用显式 schema qualification；在调用方预先设置 hostile
`search_path = pg_temp, pg_catalog` 时，验证、状态推进与恢复仍只命中固定对象。PG16.14 与
18.4 的 canonical catalog facts 和 schema fingerprint 完全一致，测试结束后也再次证明
fingerprint 恢复为规范值。

## 输入上限与敏感信息

Node C 在 apply 前重新读取并复核 source、target 与 membership，不信任 Node A 报告的旧快照。
双版本负向矩阵覆盖四个精确越界探针：

- `1 MiB + 1 byte` 单来源 payload；
- `100001` 个 reserved source；
- `84-byte` tag（21 个四字节 code point，超过 20 code point 上限）；
- `200001` 个 target rows。

四种越界均在 receipt/target 写入前失败关闭，业务事实和 schema fingerprint 不变。fixture 中的
raw sensitive canary 只用于证明解析与持久化边界；它不进入 run、manifest、receipt、audit 或
结构化返回，合法规范化后的目标 tag 仍按既定 Python 兼容语义写入。

## 当前验证与下一步

当前定向结果为：

- unit：83/83；
- PostgreSQL 16.14/18.4 Operator IT：3/3；
- PostgreSQL 16.14/18.4 bounded-retry IT：2/2；
- Node C 固定合同链 Python：66/66；
- Node A/Node C Java acceptance/parity：16/16；
- 历史传播矩阵 Java：64/64；
- 完整 source discovery：771/771；
- Phase 1/2/3/topology、小程序与 Phase 6 acceptance：全部绿色；
- UTC `clean verify`：860 Surefire + 176 Failsafe；
- failure/error/skip：0。

这些结果覆盖 happy path、零 DML 重放、真实 40001/40P01、耗尽、deferred 23503、严格前缀
receipt、commit ACK discard、超时、ACL/schema/function closure、hostile search path、输入上限、
敏感 canary 与数据库指纹。固定合同、专项验收、完整静态与 `clean verify` 已在同一最终工作树
通过；这些证据仍不替代功能提交后的独立 Git 外锚。

下一顺序固定为：Node C 功能提交并推送 → 独立后继 Git 外锚 → Node D 整体执行协议。外锚完成
前不得把 Node C 控制源解释为外部锚定；Node D 之前以及
Node D 本身均不得隐式打开生产 schema/Flyway、真实数据迁移、旧运行时永久下线或
gateway/cutover。

## 明确保持关闭

以下状态继续为 `false` 或未授权：

- 生产 schema/index 与 Flyway baseline/migration；
- 真实数据迁移、真实备份恢复和生产连接 drain；
- 旧 Flask/Web/Worker/Scheduler 永久禁用；
- Runner、Scheduler、HTTP、环境变量、文件或 Redis 自动执行入口；
- route/OpenAPI/client/gateway delta 与 production cutover；
- Node C 合同控制源的独立外部 Git anchor。
