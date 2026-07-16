# Phase 4A：目录与公共题库

本目录保存 Phase 4A 的可执行契约、黄金样本、差异报告和性能证据。旧 Flask
只作为测试期契约来源；Java 生产运行时不得读取父目录或回调 Flask。

受保护科目目录与公共题库 7 条 GET 的 Java shadow 切片均已实现。当前有效状态为
**11 migrated、600 pending、0 production cutover**，有效资源为 **159 个且全部唯一 owner**；
旧 Flask 仍是生产运行所有者，Phase 4A 后续切片和整个长期重构目标都尚未完成。

## 垂直切片顺序

1. `GET /api/quiz/subjects` 与 `GET /api/quiz/subjects/meta`：受保护科目目录读取，已实现；
2. 公共题库广场 search/list、summary、hot、boards、detail、card 共 7 条 GET：已实现
   complete snapshot 只读边界，并隔离旧实现 GET 中的惰性刷新写入；
3. 题目元数据与公共题库剩余读取：下一项，先确定真实 Flask 路由选择并冻结 golden；
4. 在 4C 由 `learning` 组合 `GET /api/quiz/subjects/{subject}/info` 中的作答、错题和收藏统计。

切片 1 不越权读取 `identity.user_subjects`：`catalog` 通过 `identity::api` 获取用户黑名单，
再在内存中与目录自有读取结果求差。它也不读取 `learning` 所有的 `user_answers`、
`mistakes` 或 `favorites`。

## 当前证据

- `golden-subject-reads.json`：7 个隔离 Flask 请求，覆盖普通用户、管理员、未认证、
  第 61 次请求限流、锁定科目、受限科目、空题量和稳定 ID 排序；
- `subject-read-contract.json`：字段、鉴权、排序、空值、查询预算和模块边界；
- `business-invariants.json`：可由 Java 单元/集成测试逐项证明的不变量。
- `data-ownership-delta.csv`：新增可重建 Redis 限流运行时键的唯一 owner 和生命周期；
- `subject-query-plan.json`：PostgreSQL 18 上 5,000 科目、50,000 题目和 50,000
  条限制关系的单次隔离 `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` 观测；它不是
  生产延迟承诺。
- `golden-public-bank-reads.json`：固定旧提交
  `700006dfdfa063deb4387be572911e782bcea0d9` 的 46-case 完整应用归档，覆盖匿名/可选
  身份、Unicode `Nd`（含阿拉伯-印度数字与全角数字）、任意精度路径/查询整数和错误形状；
  SHA-256 为 `a63240ac2d22b0faff6daa143782eaa748bb54cda60b6c7ec9843a959eb486b5`；
- `public-bank-read-contract.json` 与 `public-bank-rate-limit-contract.json`：固定 7 条 GET
  的字段、路径转换器、分页/排序/筛选、身份关系、错误信封与限流语义；
- `public-bank-metrics-snapshot-decision.md`：固定原子 complete snapshot、300/900 秒
  freshness、fail-closed readiness、PostgreSQL 最终单写者锁和 Redis 降级/过期接管边界；
- `public-bank-query-plan-evidence.json`：从 Java adapter 导出的精确运行时 SQL，在
  PostgreSQL 18.4 的 50,000 条 metrics 与 100,000 条 viewer state 上固定 7 条查询、
  无 N+1；SHA-256 为
  `570e471e85374f32f3d50c33b9b4d199a3230f17c2893c37a2fcf7469e1f2476`，不是生产延迟 SLA；
- `effective-route-parity-status.json` 与 `effective-data-ownership-status.json`：物化
  11/600/0 路由状态和 159/159 唯一资源 owner，不把 `migrated` 等同于生产切流。

Java 迁移路由不启用应用数据缓存；身份策略与目录两条业务查询读取同一只读、可重复读事务中的当前数据库状态；这是
`approved-differences.md` 中批准的过渡差异。业务用例是身份策略与目录各一条 SELECT，HTTP
认证权威边界再使用一条 SELECT，因此正常成功请求总计三条。

成功认证请求会原子写入按身份和精确路由隔离的 Redis 分钟/小时限流计数键；
身份键段使用域分离 HMAC 伪名，不包含原始用户 ID。
Bearer 不创建目标 Session；已有目标 Session 请求可刷新 Session 访问元数据并校验注册索引；
首次 Flask Session 兼容交换还会写入有界的交换/防重放键、新目标 Session 及其注册索引。
这些均是可重建的认证/限流运行态，不属于业务状态或响应缓存。

公共广场旧 GET 会在指标缺失或过期时取得 Redis 锁并重建数据库读模型，因此不能把
冷启动请求误称为无副作用读取。当前 Java GET 已改为只读原子发布的 complete snapshot：
`<= 300s` 正常服务，`300–900s` 服务最后完整快照并记录 stale，`> 900s`、冷启动或
结构不一致稳定返回 503，readiness fail closed。Snapshot maintenance 已在 PostgreSQL
16.14/18.4 证明失败回滚、原子发布与 advisory-lock 单写者；Redis 已证明真实过期后新 owner
接管且旧 token 不能删除新 token。

当前定向结果为 HTTP CatalogIT 7/7、Unicode/控制器/限流/黄金 24/24、Coordinator 6/6、
Redis 3/3、PostgreSQL 16/18 maintenance 2/2；本切片后的完整 `clean verify` 为 323 个
surefire + 44 个 failsafe，0 failure/error/skip。当前 build-context 的 WORM 证据和 Phase 2
静态门禁也已重新通过；只含 1,091 个受控源文件的独立 `Ti-Java/` 副本也已通过
Phase 1、Phase 2/3、323+44 Maven 和 PostgreSQL/Redis 数据面门禁，清理后无临时资源残留。旧 Flask
写路径的即时撤回事件、生产刷新调度、真实数据、Redis/HMAC
配置和入口切换仍未完成或获批，因此这 7 条 GET 必须保持 `production cutover=0`。
