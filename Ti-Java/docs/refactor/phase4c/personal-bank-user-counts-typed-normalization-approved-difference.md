# P4C-LEARNING-013：offset-aware 字符串按 PostgreSQL 无时区墙钟规范化

## 决策

个人题库 `user-counts` 的 `bank_shares.expires_at` 生产数据域继续使用
`timestamp without time zone`，业务解释继续使用北京时间的无 `tzinfo` 墙钟值。旧夹具中的
字符串 `2026-07-17T13:00:00+08:00` 进入该列时，固定规范值是
`2026-07-17 13:00:00`：保留年月日时分秒，丢弃来源 offset。Java/JDBC 必须以
`LocalDateTime` 读取它，禁止把它重新解释为 UTC `05:00` 或按数据库 Session 时区换算。

## 固定旧栈事实

Phase 4B golden 在临时 SQLite 中通过未声明类型的文本 bind 保存了原始字符串。旧 Flask
随后执行 `datetime.fromisoformat(str(expires_at)) > now_bj()`，把 aware datetime 与 naive
北京时间比较并触发 Python `TypeError`，因此该捕获用例返回 500。这个 500 是 SQLite
raw-string 夹具与 Python 对象类型偶合的结果，不是 PostgreSQL 生产列能够保持的合法状态。

## 目标行为

- PostgreSQL 16.14 与 18.4 必须在同一绿色 leaf 中接收相同的 Java `String` bind；
  `+08:00` 与 `-05:00` 输入在 `UTC`、`America/Los_Angeles` 两种 Session 时区下均须
  生成相同的无时区墙钟 `2026-07-17 13:00:00`。不能偷换为 Python `datetime`、Java
  `OffsetDateTime` 或其他会先按 instant 适配的对象。
- PG18.4 完整 HTTP 执行所消费的 `bank_shares` 行必须在请求追踪和九表指纹之前，由 Java
  `String` 参数通过显式 `CAST(? AS timestamp without time zone)` 创建；初始化 SQL 不得预置
  该行或用 SQL 字面量冒充 JDBC bind 证据。PG16.14 在同一 leaf 中负责 typed CAST 兼容证明，
  不冒充第二套完整 HTTP 运行时。
- 在固定的北京 12:00 语义下，规范化后的 13:00 严格晚于当前时刻，因此 coherent、active、
  `read` 分享授权有效。`access-shared-aware-expiry-type-error` 的目标结果为 HTTP 200，数据为
  `total=9`、`favorites=0`、`mistakes=0`，题型序列与普通 future-share 用例一致。
- 目标 GET 继续满足 `P4C-LEARNING-008`：在 fixture 和 Session exchange 完成后开始的请求
  区间内，九表指纹不变、`users.last_active` 与所有写 DML 为零。该执行是完整生产过滤链
  MockMvc + 真实 PG18.4/Redis 7.4.7；它不是随机端口 Tomcat 网络证据，也不把 fixture DML
  误写为整个测试生命周期零写入。

## 与 malformed/empty 的边界

- `malformed-expiry` 不能进入 PostgreSQL typed 数据域，写入固定以 SQLSTATE `22007` 拒绝；
  它继续是唯一 `EXECUTED_TYPED_REJECTION`。插入失败后因“没有 share row”得到的 403 不得
  冒充 malformed HTTP 语义。
- 旧空字符串继续按已经批准的 typed 表示映射为 SQL `NULL`，不受本决策改变。

## 有效账本覆盖

不可改写的历史账本仍保留 aware 的 `EXECUTED_TYPED_COLLAPSE` 物理证明。successor 账本只对
该一个逻辑 disposition 做显式覆盖：新 HTTP leaf 取代旧 typed-collapse leaf 成为有效证明；
旧 leaf 仅作为 superseded historical representation evidence 保留。因此有效 59 个
disposition 收敛为 58 个 HTTP + 1 个 typed rejection，而物理 JUnit 证据为历史 60 leaves
加新 1 leaf，共 61 leaves。

## 授权边界

本差异只批准测试数据的 typed 规范化、目标执行归类与相应证据合同，不授权生产 schema、
生产数据修复、operator、客户端或路由切流。PG16/18 前置终止指纹、真实 Tomcat 全响应头矩阵、
同服务 Redis 拒绝/中断/恢复仍未闭合；两条 GET 继续 pending，路由总数保持
`11 migrated / 600 pending / 0 cutover`。
