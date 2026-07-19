# Phase 4C 个人题库标签迁移：耐久账本与冻结协议设计证据

## 结论

本节点唯一新增的关闭项是
`migration_durable_ledger_freeze_design_evidence_closed=true`。它只证明一个 test-only
PostgreSQL 夹具中的账本、收据、CAS、重试、权限与歧义恢复设计可以在 PostgreSQL 16.14
和 18.4 上成立；它不创建生产表或 Flyway，不实现 Operator，不停止任何真实进程，不读取或
迁移真实数据，也不授权 production cutover。

Node A 的 `migration_global_preflight_evidence_closed=true` 继续继承。路由权威保持
**13 migrated / 598 pending / 0 production cutover**，旧 Flask 仍是生产 owner。

## 固定前驱与 Git 权威

Node B 普通 build/load 只读取一个固定前驱：

- `personal-bank-tag-migration-global-preflight-post-push-anchor-contract.json`；
- 物理 SHA-256 `66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3`；
- 载荷 SHA-256 `85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e`；
- 物理长度 66,318 bytes。

该前驱继续固定 Node A 主合同的物理 SHA-256 `65803c1a…c598e`、载荷 SHA-256
`c7a94e88…1159e` 和 102,931 bytes；Node A 实现 checkpoint 为
`256d5b347e2e5266eef084221807337427ceb16f`，唯一 parent 为
`08328c3fe18e074f581bb9e782ee4ae86cf46c53`，精确 63 路径（17 A、46 M、0 D）。

Node A 外锚本身由提交 `345deff63d2d3e867926f1e0d05d5e6d90885c4a` 固定，唯一 parent
为 `256d5b3…16f`。新 builder 使用六个显式 path/blob/SHA/byte 常量进行只读 Git replay，
固定 root、`Ti-Java`、server、`src/main`、web tree、raw delta 与 numstat；不调用旧
post-push acceptance 为它自己的六个 control source 授权。普通合同构建和加载不需要
`.git`、live `HEAD` 或任何 ref。

本节点八个新增文件是精确 control allowlist，全部从自身 source authority 中排除；它们要由
后继外锚承接，不能自签名、自授权或动态扫描目录。

## 耐久账本状态机

设计状态为：

```text
PLANNED(v0) -> FROZEN(v1) -> APPLYING(v2) -> APPLIED(v3)
     |              |               |
     +-----------> BLOCKED <--------+
```

`APPLIED` 与 `BLOCKED` 是终态。每次合法迁移必须在同一 UPDATE 中同时匹配并推进
`state/version`；migration ID 使用 PostgreSQL `uuid`，不能承载任意文本。CAS 谓词还必须精确匹配
该 UUID、一次性 run UUID、备份 manifest
摘要、cluster/database identity 摘要、组合 run identity 摘要，以及 preflight、source、
plan、target、membership 五个摘要；首次冻结后还要匹配 source/target/membership 三枚 writer
stop receipt 与 restored-backup 摘要。数据库 trigger 拒绝跳级、同版本更新、终态更新和 identity/
digest 改写。并发使用同一 expected state/version 时只能一胜一败，失败者不得继续执行。

`APPLYING -> APPLIED` 自身既有即时 trigger guard，也有 ledger UPDATE 触发的 deferred
commit guard；即使事务没有插入任何 receipt/target，也不能绕过。两道 guard 都要求冻结 source
集合非空、每个 source 恰有一条完整 disposition receipt、receipt/target count 一致且规范目标摘要
与 ledger/全部 receipts 一致。

所有 test-only relation 都以 `phase4c_tag_migration_design_` 开头。它们不是候选生产表名，
没有出现在 `src/main`、Flyway 或 Compose 中。

## 收据优先、事务原子与零 DML 重放

每个 source 的收据主键为 `(migration_id, source_row_id)`，只允许 INSERT。数据库 trigger
拒绝 UPDATE/DELETE，受限角色也没有这两项权限。target fixture 通过外键依赖对应收据，因此
同一事务必须先写收据，再写目标，最后 CAS `APPLYING(v2) -> APPLIED(v3)`。任一语句失败或
调用方回滚时，收据、目标和账本状态一起回滚。

本夹具把两个 source 行都纳入冻结集合：普通行以 `MIGRATED` disposition 写一条 target；含敏感
canary 的 source 仍必须写显式 `EMPTY_NOOP` receipt，且 target count 必须为 0。`MIGRATED` 与
`TARGET_ALREADY_PRESENT` 必须有正数 target。这样 canary 原文无需离开 source 表，也不存在
“忽略某个 source 后直接 APPLIED”的空洞。

target 表不接受任何调用方提供的 fact digest。PostgreSQL 与 Java recovery 都从 distinct
`(question_id, tag)` 集合重算 SHA-256：按 question ID 与 C collation tag 排序，使用
`ti:phase4c:tag-migration:canonical-target-facts:v1` domain，并对每个 UTF-8 字段做字节长度前缀。
数据库在 APPLIED transition 对 ledger 与全部 receipts 比对；Java recovery 独立读取规范事实集
重算。错误 tag 即使伴随声称正确的 receipt/ledger digest 也会失败关闭，并以
`TARGET_MISMATCH` 进入 `BLOCKED`。

重放必须先读收据。只有收据完整匹配、账本为 `APPLIED`、fresh recovery identity 与账本/
收据三方一致且目标摘要一致时，才返回已提交；此路径业务 DML 必须为 0。无收据、部分收据、
摘要不一致、不同数据库或非 `APPLIED` 一律阻断。Redis、本地文件、`user_progress` 特殊行或
`question_id=0` 都不能充当 durable marker。

## 恢复实例 identity

Node A 的 database/user 摘要不足以区分恢复实例，所以 Node B 使用两个 domain：

1. `ti:phase4c:tag-migration:cluster-database:v1` 绑定真实 PostgreSQL
   `pg_control_system().system_identifier`、database OID、server version/address/port，并只保存
   SHA-256，不保存 system identifier、OID、数据库名或数据库用户原文；
2. `ti:phase4c:tag-migration:run-identity:v1` 再绑定固定备份 manifest SHA-256、一次性
   migration/run UUID 和上一步 cluster/database 摘要。

ledger 与 receipt 同时保存 run UUID、backup/cluster/run identity 摘要；fresh recovery 重新
计算并要求三方完全相等。该设计防止“相同业务摘要但连接到错误恢复库”被误判为已提交。

## 全停机冻结协议

真实 apply 的顺序必须是：

1. Node A 全局预检通过且逐项 disposition 已批准；
2. 停止旧/新 Web、Worker、Scheduler 的全部入口；
3. drain 或 terminate 所有既有数据库连接，并在冻结期拒绝新连接；
4. 将已批准备份恢复到一个新的隔离目标数据库；
5. 在恢复库重新计算 database identity、全局 preflight、source/target/membership digest；
6. 将 source/target/membership writer stop receipt 与 backup manifest 绑定到账本 CAS；
7. 进入 `APPLYING` 后永远禁止恢复旧 Flask 运行时。

旧 `GET` 标签 fallback 在目标为空时会写 target 并 commit；通用 `/api/progress` 可以 POST 或
DELETE 任意 `p_key`。两者都不取得 Java advisory lock。因此 advisory lock 只能协调遵守协议
的新代码，不能证明旧 Web、Worker、Scheduler 或旧连接已经冻结。本节点没有执行上述真实
冻结，source、target、membership 三类生产 freeze evidence 仍全部为 `false`。

## 有界重试与提交歧义

只允许 SQLSTATE `40001`（serialization failure）与 `40P01`（deadlock detected）重试；
最大 3 attempts、2 retries，每次使用全新事务。其他 SQLSTATE、null/unknown SQLSTATE
第一次即失败关闭。PG16.14/18.4 夹具让数据库真实产生两种错误；两种真实 SQLSTATE 都进入
同一有界重试循环，并分别证明第一次回滚、第二次使用全新 backend PID 与 transaction ID
成功。classifier 只接受这两项。

提交歧义使用 test-only `ack-discard-after-commit` fixture：数据库 commit 已完成后，调用方
丢弃 ACK 并抛出异常。它不是网络故障，也不冒充 real network commit-response loss。恢复只能
走 receipt-first 零 DML 确认；必须匹配一次性 run UUID、backup manifest、cluster/database
identity、组合 run identity、完整收据、目标摘要和 `APPLIED` 状态。真实网络中断/ACK 丢失
证据仍为 `false`。

## ACL 与敏感信息

临时角色 `ti_phase4c_tag_design_operator` 为 `NOLOGIN/NOSUPERUSER/NOCREATEDB/NOCREATEROLE/
NOINHERIT/NOREPLICATION/NOBYPASSRLS`，没有 PASSWORD 或直接 CONNECT grant。夹具还显式从
disposable database 的 `PUBLIC` 撤销 CONNECT，测试 `has_database_privilege` 证明该角色的
有效 CONNECT 权限为 false。Java 只通过 owner
fixture connection 后 `SET ROLE` 验证 ACL，不创建第二套凭据。该角色不能创建 schema/table，source/membership 仅 SELECT；ledger 仅
SELECT/INSERT/UPDATE；receipt/target 仅 SELECT/INSERT；mutation audit 不可见。fixture 中放入
敏感 canary，测试证明它只存在于 source fixture，不进入 ledger、receipt、mutation audit 或
合同 JSON；把 canary 直接当 migration ID 会因 UUID 类型以 `22P02` 拒绝，audit 的 migration
ID 列本身也是 UUID。账本与收据只持有 ID、状态、版本、UUID、稳定 code、count 与
domain-separated digest。

## 保持关闭的边界

以下均保持 `false`：完整 migration design、生产 durable ledger/tombstone、三类生产 write
freeze、连接 drain、生产 bounded retry 实现、Operator、生产 schema/index、Flyway baseline、
备份/回滚证据、真实 apply、旧运行时永久下线、route/OpenAPI/client/gateway delta 和
production cutover。

下一节点必须取得明确授权后，才可实现生产 ledger/schema 与 Operator，并分别证明真实全进程
停机、连接排空、恢复备份 identity、重试、备份/回滚和 apply。Node B 的设计/test-only 绿色
结果本身绝不是 apply authorization。
