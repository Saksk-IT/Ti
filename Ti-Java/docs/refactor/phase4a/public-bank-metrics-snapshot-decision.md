# Phase 4A 公共题库完整快照决策（Accepted）

- **状态：** Accepted（shadow 实现完成，production cutover 仍为 0）
- **范围：** 7 条匿名可读、可选登录身份丰富的 `/api/public/banks*` GET
- **决策 owner：** `catalog`
- **批准状态：** `P4A-CATALOG-004` 至 `P4A-CATALOG-007` 已纳入
  `approved-differences.md`；限流与路径防歧义的 `P4A-CATALOG-008/009` 也已在同一批准记录中固化。

## 背景

旧实现的公共题库查询不是纯读取。每个 summary、board、hot、list、card 和 detail
用例都会先调用 `ensure_plaza_metrics()`。当 `public_bank_plaza_metrics` 为空或被判定
过期时，请求线程会执行源表聚合，随后 `DELETE`、`INSERT` 并 `COMMIT` 整张指标表。
因此，旧 cold GET 的真实契约包含数据库写入、Redis 锁竞争和最多 8 秒等待，不能把
预热后的观察误称为所有 GET 都无副作用。

旧查询还直接联查 `user_question_banks` 与 `users`，用源表覆盖快照中可能陈旧的封面、
加入方式、复制权限和头像。这证明当前指标表只是 partial snapshot，而不是能独立支持
7 条 GET 的完整 catalog 投影。Java 不能把这种跨 owner 联查复制进 `catalog`。

## 已确认的旧缺陷

### 1. 冷读取写数据库

`ensure_plaza_metrics()` 由 GET 同步触发。慢聚合、锁等待或刷新失败直接进入用户请求
延迟和错误路径，也破坏 HTTP GET 的只读属性。

### 2. Redis 锁不是完整的单写者证明

旧锁使用 `SET NX EX 30`，但释放先 `GET` token 再 `DELETE`，不是一个原子 compare-and-delete。
锁没有续期或 fencing token；刷新超过 30 秒后，另一个实例可以获得新锁。Redis 不可用时
退回进程内 `threading.Lock`，它只能协调单个进程，不能协调多实例。

### 3. 两个“7 天”汇总字段实际只统计当天

旧 `new_banks_7d` 与 `active_users_7d` 共用的 cutoff 是北京时间当天 `00:00:00`，
并非 `now - 7 days`。字段名称与计算语义不一致。目标是否修复为真实滚动 7 天属于响应语义差异，必须经
`P4A-CATALOG-006` 单独批准，不能在实现中静默改变。

### 4. `MAX(updated_at)` 可把 partial snapshot 判为新鲜

旧新鲜度只读取 `MAX(public_bank_plaza_metrics.updated_at)`。以下状态都可能被误判：

- 只有部分 source row 被写入，但其中一行很新；
- 某一 source type 整体缺失；
- 行数据来自不同刷新批次；
- 源事实已撤回，但陈旧 snapshot row 仍存在；
- 空快照没有独立的“成功生成了 0 行”证明。

目标必须使用独立的完成标记、行数和摘要证明完整性，不能再从普通业务行推导刷新是否成功。

## 决策

目标建立 catalog 自有的完整读模型。7 条 GET 只读取该读模型，不读取源 owner 表，
不刷新、不排队刷新、不取得 refresh lock，也不写 PostgreSQL 或 catalog Redis 状态。

### 投影组成

#### `public_bank_plaza_metrics`

保留既有 owner 与统计字段，并补齐 GET 当前从源表临时取得的字段：

- `owner_id`
- `owner_avatar`
- `join_mode`
- `join_note`
- `allow_copy`
- `share_count`

每行继续以 `(source_type, source_id)` 唯一标识一个公开系统题库或用户公开题库。
公开状态、锁定状态与有效状态通过“是否存在投影行”表达；撤回时应删除或 tombstone，
不能在 GET 中回查源表确认。

#### `public_bank_plaza_viewer_state`

新增 catalog-owned rebuildable projection：

| 字段 | 含义 |
|---|---|
| `identity_id` | 服务端认证身份 ID，只用于内部关系与去重 |
| `source_type` / `source_id` | 对应投影题库 |
| `has_public` | 通过公开关系加入 |
| `has_shared` | 通过分享关系加入 |
| `last_activity_at` | 用于 `active_users_7d` 的最近活动时间 |
| `updated_at` | viewer row 的投影更新时间 |

唯一键为 `(identity_id, source_type, source_id)`。列表与详情在同一 SQL 中按可选 viewer
LEFT JOIN，得到 `none/public/shared/both`，不会产生逐题库查询。summary 在过滤后的 bank
集合上 `COUNT(DISTINCT identity_id)`，同一用户活跃于多个题库仍只计一次。

#### `public_bank_plaza_snapshot_state`

新增 singleton 完整性记录，至少包含：

- `last_success_at`
- metrics row count
- viewer-state row count
- system/user-public source row count
- 规范化 projection digest
- projector schema version
- 源 high-watermark 或等价的可审计版本信息
- 完成状态

metrics、viewer state 与 snapshot state 必须在一次后台单写事务内提交。GET 只有在状态为
complete、计数/摘要一致且未 hard-expire 时才能读取。一个成功生成的 0 行快照也有明确
complete marker。

### 后台单写者

刷新只能由显式 bootstrap、定时 projector 或提交后事件处理器发起：

1. Redis token lock 用于降低重复工作；
2. 释放使用 Lua 原子 compare-and-delete；
3. TTL 必须覆盖或续期超过实测 refresh p99；
4. PostgreSQL transaction advisory lock 是最终单写者边界；投影 Supplier 只有在
   `REPEATABLE_READ` 写事务取得该锁后才加载源快照，不能在锁外预取陈旧或并发交叠的数据；
   `pg_advisory_xact_lock` 的等待可能让首个 `REPEATABLE_READ` 尝试保留等待前快照，因此
   `40001`（serialization failure）和 `40P01`（deadlock detected）最多尝试 3 次（最多重试 2 次），且每次都在
   独立的 `REQUIRES_NEW` 事务中重新取得锁并重新调用 Supplier；其他异常立即抛出。Supplier
   必须是纯源读取器，不得执行外部不可回滚副作用，也不得依赖“只调用一次”的语义；
5. Redis 故障时可依靠 PostgreSQL 锁安全降级，但必须记录 degraded 指标；
6. 一个事务建立一致源快照、更新全部投影并最后写 complete state；
7. 失败事务回滚，继续保留上一个 complete snapshot。

当前 shadow 配置把 Redis lease TTL 固定为 15 分钟，且尚未实现续期；这不是 refresh p99 证明。
在 `production_cutover` 从 0 提升前，必须先对真实规模的 projector 测量 p99，并证明 15 分钟有足够
裕量，或实现 token-owned 续期/更强 fencing。即使 Redis lease 过期，PostgreSQL transaction advisory
lock 仍是最终单写者边界，因此当前 shadow 演练不会把 Redis TTL 当作正确性保证。

GET 与后台刷新并发时，只能看到旧 complete snapshot 或新 complete snapshot，不能看到
删除一半、只插入某一 source type 或新 metrics 配旧 viewer state 的组合。

当前 shadow 实现还把 `plaza_boards` 的任何语句级变更纳入 complete marker 失效触发器；
批量更新只执行一次失效，事务回滚会连同失效一起回滚。Redis lease 的真实过期与新 owner
接管由集成测试覆盖，旧 token 的 Lua compare-and-delete 不能删除新 token；即使发生接管，
两个 Supplier 仍由 PostgreSQL transaction advisory lock 串行化。

### 新鲜度状态机

| 状态 | 条件 | GET 行为 | Readiness |
|---|---|---|---|
| Fresh | complete snapshot age `<= 300s` | 正常返回 | UP |
| Soft stale | `300s < age <= 900s` | 返回最后 complete snapshot；只记内部 stale 指标 | UP |
| Hard expired | `age > 900s` | 稳定 503 | 非 UP |
| Cold | 无 complete marker | 稳定 503 | 非 UP |
| Partial | marker/行数/摘要不一致 | 稳定 503 | 非 UP |

Soft stale 不在兼容 JSON 中增加字段或改变 Content-Type。状态通过 Micrometer 指标、日志和
readiness 暴露。建议指标至少包括：

- `ti.catalog.public_bank.snapshot.age.seconds`
- `ti.catalog.public_bank.snapshot.refresh.success`
- `ti.catalog.public_bank.snapshot.refresh.failure`
- `ti.catalog.public_bank.snapshot.refresh.duration`（成功、失败和 Redis 降级路径；被抑制的
  重复请求不计入刷新时长）
- `ti.catalog.public_bank.snapshot.served_stale`
- `ti.catalog.public_bank.snapshot.unavailable`
- `ti.catalog.public_bank.snapshot.lock.degraded`

Readiness 不暴露内部异常、地址或凭据，只使用 `cold`、`partial`、`hard_expired`、
`clock_skew`、`inspection_unavailable`、`inspection_failed` 六个固定低基数原因计数；只有
hard-expired 保留可信的非负 snapshot age，其余不可测状态把 age gauge 置为 `-1`。

### 可见性事件优先于周期刷新

300/900 秒只适用于热度、题量、头像、封面等普通陈旧度。以下事件可能继续暴露已撤回内容，
必须在源事务提交后立即更新或 tombstone 投影：

- 用户题库取消公开、删除或状态关闭；
- 系统科目锁定、删除；
- 其他使题库不再公开可见的策略变化。

在旧 Flask 写路径尚不能发布或桥接这些事件时，Java GET 只能保持 shadow/migrated，
`cutover=0`。不能用定时轮询的 900 秒 hard window 代替可见性撤回保证。

## GET 事务与 SQL 预算

- `/api/public/banks` 与 `/api/public/banks/list`：一条 total SELECT，加一条有序 page SELECT；
- `/boards`、`/hot`、`/summary`、两条 detail：各一条业务 SELECT；
- snapshot state 检查折叠进上述查询，不额外增加 SELECT；
- optional viewer relation 折叠进 page/detail 查询，不额外增加 SELECT；
- 有效可选凭证由 HTTP 安全层额外执行一条 identity authority SELECT；
- 查询数不随返回行数增长，禁止 N+1；
- 两条分页查询运行于只读 `REPEATABLE_READ` 事务，保证 total 与 page 一致。

不得为了把分页压缩为一条 SQL 就强制 materialize 大型过滤 CTE。是否采用 window、lateral
或两条查询由 PostgreSQL 16/18 的真实计划证据决定；当前决策固定的是查询上限与一致性，
不是某个未经规模测试的 SQL 技巧。

## PostgreSQL 16/18 兼容边界

同一个 JDBC adapter contract suite 必须同时运行于 PostgreSQL 16.14 与 18.4，至少证明：

- 五种排序及 source ID tie-breaker；
- board/source/keyword 过滤；
- 正常页、越界页、空但 complete 的快照；
- system/user detail 与 404；
- 匿名和登录 viewer relation；
- 跨多个 bank 的 active identity 精确去重；
- Fresh、Soft stale、Hard expired、Cold、Partial；
- refresh 提交前后没有 partial visibility；
- 20k–50k metrics 与大规模 viewer-state 夹具的 JSON query plan。

关键词 `%contains%` 在没有证据前不依赖 `pg_trgm` 或其他扩展。索引是否使用是机器门禁，
单次容器耗时只作为观测，不声称为生产 SLA。

## 兼容与已批准差异

以下差异已经合并进 `approved-differences.md`。它们只授权当前 shadow 读取实现；写路径事件覆盖、
bootstrap/projector 演练和生产切换仍受独立门禁约束：

### P4A-CATALOG-004（accepted）：GET 不刷新；Cold/Hard expired 返回 503

- **Legacy：** cold GET 同步刷新、写库并等待 Redis 锁。
- **Target：** GET 永远只读；没有 complete snapshot 或 age 超过 900 秒时返回固定安全 503。
- **理由：** 消除读请求写入、不可控锁等待和 partial refresh 暴露。

### P4A-CATALOG-005（accepted）：完整 snapshot 与 300/900 秒状态机

- **Legacy：** 只看 `MAX(updated_at)`，无法证明行集完整。
- **Target：** metrics、viewer state、row counts、digest 和 complete marker 原子提交；
  300–900 秒只服务最后一次 complete snapshot。
- **理由：** 新鲜度必须描述一个完整代次，而不是任意一行的时间戳。

### P4A-CATALOG-006（accepted）：两个汇总字段修复为真实滚动 7 天

- **Legacy：** `new_banks_7d` 与 `active_users_7d` 实际 cutoff 为当天零点，只统计当天。
- **Target：** 两者均使用服务器统一 Clock 的 `now - 7 days`，保留字段名但修复语义。
- **风险：** 这是可见数值差异；若未批准，Java 必须先复刻旧当天语义并把缺陷保留在契约中。

### P4A-CATALOG-007（accepted）：异常固定为安全 500 文案

- **Legacy：** GET 内刷新或 SQL 异常可能沿不同路径形成不稳定 5xx。
- **Target：** 保留 legacy `status/code/message` 形状，消息固定为“服务暂时不可用”，不回显异常文本。
- **理由：** 数据库、Redis 与内部地址不能成为兼容输出。

## 验证与退出条件

1. 隔离 Flask goldens 把 hot response parity 与 cold side effect 分开记录；
2. 每条 Java GET 的 PostgreSQL/Redis 前后指纹证明 0 catalog business mutation；
3. Redis key allowlist 证明 GET 不创建 `plaza:metrics:refresh:lock` 或数据缓存；
4. 通过故障注入证明 refresh 失败保留旧 complete snapshot；
5. 并发 refresh 只能有一个 PostgreSQL writer；
6. 可见性 tombstone 在源提交后立即生效；
7. PG16.14/18.4 同套测试与计划证据通过；
8. Spring Modulith 和 SQL ownership scan 证明 catalog GET 不依赖其他模块内部实现或源表；
9. 已批准差异并更新 OpenAPI、route/data-owner delta 与机器哈希后，才可把 7 route 标为 migrated；
10. 写路径事件覆盖完成前保持 `cutover=0`。
