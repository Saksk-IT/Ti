# Personal-bank legacy tag 迁移执行协议（Node D）

## 结论

Node D 只把已经外锚的 Node A/B/C 能力组合为一个**显式、逐阶段、默认不可达**的库协议：

- `TagMigrationPlanCandidateFactory` 在内存中验证完整且 data-eligible 的全局 preflight，并生成不可伪造的 redacted candidate；
- `Ed25519TagMigrationEvidenceVerifier` 对四个 purpose 使用固定 canonical binary wire、固定域隔离和显式注入的 trust snapshot；
- `LegacyPersonalBankTagMigrationExecutionProtocol` 逐次执行 `prepare`、`freeze`、`apply` 或 `recover`，每次只允许推进一个阶段；
- PostgreSQL 16.14/18.4 的 078/079 fixture 仅用于 disposable 本地备份/恢复与协议演练。

本节点没有 Spring Bean、Runner、Scheduler、HTTP、CLI、环境变量、文件、Redis、KMS 或网络密钥发现，也没有 `executeAll`、force、reset、skip 或 rollback 入口。它不创建生产 schema/Flyway，不执行真实数据迁移，不签发真实停写收据，不永久关闭旧运行时，也不修改 route、OpenAPI、gateway 或 production cutover。

## 固定前驱

Node C 的功能、独立验收与 Git 外锚已经依次固定。Node D 的唯一语义前驱是 Node C 的 post-push anchor：

- commit：`4c47d1ea220ae9e310338bbf23b74d87d477e20f`；
- contract SHA-256：`0c7041de3dff57ccaadcb995447b4ae10342ce39dd31e03291eecc916a95d936`；
- document payload SHA-256：`fb82185d0b87b19df4ef3fb6b9e95636731f33b5da6d21e6e2287471996a4e64`；
- contract bytes：`84461`；
- Node 8 WORM SHA-256：`db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f`。

普通加载和验收不读取 live `HEAD`、`main` 或 `origin/main`。固定 Git 重放只用于证明已提交的 Node C 外锚身份；Node D 自身必须在后继提交中另行独立外锚。

## Candidate 边界

Candidate 是外层操作意图，不是数据库快照、签名或 apply 授权。Factory 要求：

1. `migrationId` 与 `migrationRunUuid` 均非 nil；
2. preflight 为 `COMPLETED`、full sweep、非空、零 blocker、零 near-miss/规范化冲突；
3. 每一行均为 canonical 且属于 `MIGRATABLE`、`TARGET_ALREADY_PRESENT` 或 `EMPTY_NOOP`；
4. 重新计算的 aggregate digest 与报告及 `RunBinding.preflightDigestSha256` 完全一致；
5. source ID 严格递增、唯一；三类 disposition 数之和等于 source count。

Candidate SHA-256 使用固定域、两个 UUID 和 `RunBinding` 九项原始 SHA-256 字节按固定顺序计算。公开构造器不存在；`toString` 只暴露 UUID、candidate digest 与计数。最终数据库事实仍由 Node C Core 在事务内重新读取、构造 manifest 并执行 `requireBinding`，调用方不能用 candidate 替代该检查。

## Ed25519 证据边界

Verifier 是无状态、不可变的 public-key trust snapshot。它只接受：

- 四个由被调用方法选择的 purpose：`PREPARE`、`FREEZE`、`APPLY`、`RECOVERY`；
- 固定版本、固定字段顺序、无 optional/重复/未知/尾随字段的 canonical binary payload；
- 精确匹配的 ASCII issuer 与 key ID；
- 每个 key ID 仅一个 purpose、32-byte full-order Ed25519 public key、显式有效期和硬撤销状态；
- 恰好 64-byte 的 pure Ed25519 signature；
- 有界 clock skew、exclusive expiry、受限最大 lifetime；
- 与方法参数完全相同的 migration/run UUID、九项 binding 和由它们重算的 candidate digest；
- purpose 对应的固定 receipt 槽位。

PREPARE receipt 和 APPLY authorization receipt 由已验证的完整签名信封作域隔离 SHA-256 推导，签发者不能自报本信封摘要。freeze 的 source/target/membership writer-stop、connection drain/rejection、restored backup，以及 apply/recovery 的 legacy-runtime-disabled 等摘要均按语义槽签名；writer-stop 摘要不得折叠。

wire 不携带算法名、OID 或 provider；不接受 JSON/JWT、Java serialization、DER/SPKI 输入、Ed448/X25519、Ed25519ph/ctx 或动态算法分派。未知 key、错误 purpose/issuer/UUID、非规范 payload、时间或 key 状态异常、签名失败及普通运行时异常全部折叠为无 cause、无细节的 `EvidenceRejectedException`，且在取得 JDBC 连接前终止。

相同 run、相同 phase、完全相同 envelope 必须允许幂等重放，否则会破坏 Node C 的 ACK-discard 与 zero-DML recovery。Node D 没有 durable evidence UUID journal，不能宣称全局 single-use 或持久防重放已经闭合。

## 显式状态机

```text
CANDIDATE_READY
  -> prepare -> PLANNED/v0
  -> freeze  -> FROZEN/v1
  -> apply   -> APPLYING/v2 -> APPLIED/v3
  -> recover -> 读取 durable truth，并只做 receipt-first 前滚恢复
```

Protocol 的每个方法都先用同一个 Ed25519 verifier 预验证，再把同一 verifier 和同一证据交给 Core 二次验证。预验证返回的 binding 必须与 candidate binding 完全一致；失败返回 `BLOCKED / UNAVAILABLE / -1 / EVIDENCE_REJECTED`，数据库与 membership provider 调用数为零。Core 结果原样返回，Protocol 不重新解释 durable state。

`FROZEN -> APPLYING` 成功提交是不可逆边界。协议设计要求该边界之后不得恢复旧 Flask runtime；但 Node D 只验证签名声明，并没有真实停机或永久禁用实现，所以对应生产 gate 仍为 `false`。

## Test-only 078/079 与恢复演练

078/079 严格叠加在 076/077 之后，只创建隔离的 `phase4c_tag_execution_fixture` 和 public deterministic canary。它们不改写 `ti_migration`、不追加 operator 对既有业务表的授权、不进入 `src/main/resources`，也不保存私钥、密码、签名原文、原始 tag 或真实业务值。

本地双版本演练在 disposable PostgreSQL 中验证：

- 六类 writer 会话的显式关闭、新连接拒绝与零残留；
- source freeze fingerprint、真实本地 dump artifact SHA 与独立 canonical manifest SHA；
- 恢复到全新数据库后的不同 database identity 与相同 schema/ACL/business fingerprints；
- fresh preflight 后逐次签发并执行四阶段 evidence；
- 完整重放零业务 DML、损坏 artifact/manifest/identity/schema/ACL/signature fail closed；
- disposable target 损坏后的本地快照可恢复性及源库事实不变；
- dump、数据库、动态角色、连接与私钥引用最终清理为零。

这只关闭 `local_test_backup_restore_execution_rehearsal_closed`，不得称为生产备份、生产 rollback、真实 writer freeze 或真实迁移证据。

## 仍然关闭

Node D 只允许关闭执行协议、canonical candidate、密码学 verifier 和本地演练证据。以下状态继续为 `false` 或未授权：

- 生产 schema/index、Flyway baseline/migration 与 durable ledger 部署；
- 生产 source/target/membership writer freeze、连接 drain/rejection 与 receipt issuer；
- 生产备份恢复、rollback、真实数据 apply；
- production trust roots、key rotation/revocation audit、durable nonce journal 与 operator wiring；
- 旧 Web/Worker/Scheduler/Flask 永久禁用；
- route/OpenAPI/client/gateway/proxy delta 与 production cutover；
- candidate/membership 与 Core SERIALIZABLE transaction 的同连接绑定。

有效路由继续是 **13 migrated / 598 pending / 0 production cutover**。Node D 功能提交推送后，必须由独立后继 runner 复验，再由第二个后继提交固定 commit/tree/delta 与全部控制源；在此之前不得把本节点自解释为外部锚定。
