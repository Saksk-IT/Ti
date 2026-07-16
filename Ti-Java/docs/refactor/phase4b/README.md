# Phase 4B：个人题库

本目录保存 `personalbank` 的可执行契约、旧栈黄金样本和 PostgreSQL 查询证据。旧 Flask
仅是固定提交上的只读契约来源；Java 构建、测试和运行时不得读取父目录，也不得回调旧服务。

## 当前切片：分类列表内部读取

Phase 4A 最终合同只授权下列两条 alias 的实现与取证，不授权 HTTP 迁移：

- `19b37a262989|GET|/api/user/banks/api/categories`
- `e32aec766730|GET|/user/banks/api/categories`

Java 已新增 HTTP-neutral 的 `PersonalBankApplicationApi#listCategories`。该能力在只读事务中
执行一条固定 SQL，只读取 `personalbank` 自有的 `user_bank_categories` 与
`user_question_banks`：按当前身份过滤分类，以关联关系统计 `status = 1` 的题库，保留
跨 owner 关联，最后按 `sort_order ASC NULLS LAST, id ASC` 返回不可变结果。它没有新增
Controller、Security matcher、OpenAPI/route delta、缓存或生产切流。

两条 HTTP operation 仍是 **pending**；全局有效状态仍为 **11 migrated、600 pending、
0 production cutover**。旧 Flask 继续拥有 HTTP 和生产运行流量。

## 证据

- `application-api-shape-status.json`：在 Phase 4A 形状上新增一个 personalbank 内部公开方法；
  公开方法总数为 20，route-backed operation 仍为 11；
- `golden-personal-bank-category-reads.json`：固定旧提交完整 `app/` 归档的 22 个双 alias
  case，覆盖 Session/Bearer 分流、匿名、空表、Unicode、nullable 字段、跨 owner 计数、
  查询参数忽略、两种故障协商和 Session `last_active` 身份副作用；
- `personal-bank-category-query-plan-evidence.json`：从 Java adapter 导出的唯一运行时 SQL，
  在 PostgreSQL 18.4、5,003 个分类和 150,000 个题库的确定性合成夹具上执行一次；两张
  关系各扫描一次、最大 loops 为 1、TEMP 为 0。`PREPARE(bigint)` 证据只证明记录的
  PG18/int4 边界，不冒充 PG16 或 JDBC 执行，也不是生产延迟、容量或索引 SLA；
- `personal-bank-category-read-contract.json`：闭合旧来源、字段、null、状态、排序、owner、
  runtime SQL、PG16.14/18.4 JDBC 验证和禁止切流边界；
- `personal-bank-category-worm-evidence.json`：不可变绑定 build-context SHA-256
  `51d381c5b85885b9fe902d7afd20324a34525f3cbc97acde27673ea6a7a11154`，通过 PostgreSQL
  18.4、70 表/617 列、只读 ACL、Hibernate `validate`、启动与 readiness；
- `personal-bank-category-acceptance.json`：绑定 248/248 source tools、424+60 Maven、WORM、
  1,249 文件独立副本以及排除合同自身的 1,248 文件非递归最终清单。

## 明确延后

分类 alias 的 HTTP 适配仍需单独批准并证明 PostgreSQL 旧栈日期序列化、nullable key 保留、
双 alias 的全局鉴权门、Session `last_active`、安全故障投影和完整信封。当前内部 DTO 不应
直接当作兼容响应 DTO。

最终合同下一步只授权 shares 双 alias
`e817f8083d74|GET|/api/user/banks/api/<int:bank_id>/shares` 与
`c50102968322|GET|/user/banks/api/<int:bank_id>/shares` 的调用方闭合、golden/查询证据和
HTTP-neutral 实现。进入实现前必须分别固定两条顺序 SQL 的故障边界、PG16.14/18.4
JDBC/计划及 DESC NULL 排序/方言；不得合并成 JOIN，也不得扩大到 route/OpenAPI、创建、
删除、记录、统计、缓存、index/schema 或生产切流。
