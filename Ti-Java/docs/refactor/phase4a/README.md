# Phase 4A：目录与公共题库

本目录保存 Phase 4A 的可执行契约、黄金样本、差异报告和性能证据。旧 Flask
只作为测试期契约来源；Java 生产运行时不得读取父目录或回调 Flask。

## 垂直切片顺序

1. `GET /api/quiz/subjects` 与 `GET /api/quiz/subjects/meta`：受保护科目目录读取；
2. 公共题库广场 summary/board/list/card/detail：先固定新鲜
   `public_bank_plaza_metrics` 快照，隔离旧实现 GET 中的惰性刷新写入；
3. 题目元数据与公共题库剩余读取；
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

Java 迁移路由不启用应用数据缓存；身份策略与目录两条业务查询读取同一只读、可重复读事务中的当前数据库状态；这是
`approved-differences.md` 中批准的过渡差异。业务用例是身份策略与目录各一条 SELECT，HTTP
认证权威边界再使用一条 SELECT，因此正常成功请求总计三条。

成功认证请求会原子写入按身份和精确路由隔离的 Redis 分钟/小时限流计数键；
身份键段使用域分离 HMAC 伪名，不包含原始用户 ID。
Bearer 不创建目标 Session；已有目标 Session 请求可刷新 Session 访问元数据并校验注册索引；
首次 Flask Session 兼容交换还会写入有界的交换/防重放键、新目标 Session 及其注册索引。
这些均是可重建的认证/限流运行态，不属于业务状态或响应缓存。

公共广场旧 GET 会在指标缺失或过期时取得 Redis 锁并重建数据库读模型，因此不能把
冷启动请求误称为无副作用读取。后续对比会预热并冻结两套独立数据库中的指标快照，
同时单独保留冷启动写行为作为迁移契约。
