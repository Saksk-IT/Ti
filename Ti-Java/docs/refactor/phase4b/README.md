# Phase 4B：个人题库

本目录保存 `personalbank` 的可执行契约、旧栈黄金样本和 PostgreSQL 查询证据。旧 Flask
仅是固定提交上的只读契约来源；Java 构建、测试和运行时不得读取父目录，也不得回调旧服务。

## 已完成切片：分类列表内部读取

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

## 已通过入口门禁：分享列表（implementation not started）

分类最终合同授权的下一组候选仍只有下列两条 GET alias：

- `e817f8083d74|GET|/api/user/banks/api/<int:bank_id>/shares`
- `c50102968322|GET|/user/banks/api/<int:bank_id>/shares`

实现前入口证据已经物化：

- `personal-bank-share-list-callers.json` 在固定提交上完成全仓调用方闭合，确认活跃 Web 管理页、
  活跃小程序 `bank-detail` 调用、可外部直达但仓内无导航的小程序 `bank-share` 页面，并把孤儿模板、
  生成 JS 与同路径 POST/子路径 DELETE 测试分开记账；
- `golden-personal-bank-share-list-reads.json` 保存双 alias 共 40 个隔离 case，固定认证分流、owner/status
  probe 的短路与独立故障边界、11 个原始 nullable 字段、无过滤列表、两条查询顺序、响应信封、
  Session `last_active` 身份副作用及查询参数忽略；
- `personal-bank-share-list-query-plan-evidence.json` 与 `src/test` 下的 preimplementation SQL 证据在
  PostgreSQL 16.14/18.4 上固定两条顺序查询：先校验 owner + `status = 1`，命中后再按
  `created_at DESC NULLS FIRST` 读取列表；禁止 JOIN、禁止增加 `id` tie-breaker。5,005 个题库、
  150,003 条分享的合成夹具只记录当前无索引风险，不授权 schema/index 变更或生产 SLA；
- `personal-bank-share-list-entry-contract.json` 绑定分类最终验收、冻结 shape/API、调用方、golden、
  双版本 JDBC/计划、Phase 1 OpenAPI 与全部生成工具哈希，确认四项实现前先决条件均已满足；它还
  固定 `viewer long → JDBC bigint → legacy int4`，并用 `Optional<PersonalBankShareListView>` 区分
  owner/status probe 无行与合法空列表；
- 三组入口证据工具测试共 22/22、入口合同 parity 7/7、全部 source tools 277/277 通过；
  入口检查点的完整 `clean verify` 也以 429 个 surefire + 62 个 failsafe、0
  failure/error/skip 通过。

当前状态明确为 **implementation not started**：生产源码中没有分享列表 DTO、应用方法、service、
port 或 JDBC adapter，API shape 也未变化；现有 SQL 类仅位于 `src/test`，不能冒充实现。入口合同
与跨文件 parity 已通过，因此下一步只授权 HTTP-neutral 的内部读取实现；该门禁本身仍不改变
**11 migrated、600 pending、0 production cutover**。

下一步只允许新增 `personalbank` 内 HTTP-neutral 的内部读取能力，并严格复现上述两条顺序 SQL、
短路、null、原始字段与排序语义。仍不授权 Controller、Security
matcher、route/OpenAPI delta、创建/删除/记录/统计、缓存、schema/index 或生产切流。

## 明确延后

分类 alias 的 HTTP 适配仍需单独批准并证明 PostgreSQL 旧栈日期序列化、nullable key 保留、
双 alias 的全局鉴权门、Session `last_active`、安全故障投影和完整信封。当前内部 DTO 不应
直接当作兼容响应 DTO。

分享列表入口合同不接受两条 HTTP operation 已迁移，也不接受生产实现已开始；它只把
HTTP-neutral 内部实现放入下一步授权范围。HTTP 适配与其余分享用例继续明确延后。
