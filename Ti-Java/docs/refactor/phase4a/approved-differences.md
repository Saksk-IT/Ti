# Phase 4A 已批准差异：目录与公共题库读取

## P4A-CATALOG-001：迁移窗口内保持 always-fresh

- **旧行为：** Flask 默认可把科目列表和科目元信息放入 Redis 60 秒；缓存键包含用户、
  科目和题目版本。
- **Java 行为：** 不写应用数据缓存，每次在只读、可重复读事务中读取当前身份限制和目录。
- **批准理由：** 科目、题目和用户可见性写路径尚未全部迁移，现阶段无法证明所有提交后
  失效点完整。提前复制缓存会引入比短期额外查询更危险的越权或陈旧计数风险。
- **保持不变：** HTTP 状态、JSON 字段、排序、可见性、空值和限流响应保持金样兼容；
  Redis 不写应用数据缓存，仅写认证凭证所需的 Session/交换运行态与短期限流键。
- **风险与观测：** 每个成功请求的业务用例固定两条 SELECT，认证权威边界再固定一条，
  正常 HTTP 路径总计三条。`subject-query-plan.json` 只固化两条业务查询在规模化合成数据上的计划，
  不把单次观测冒充生产 SLA。
- **回滚/退出：** Java 尚未生产切流，可直接停止双运行。只有 catalog 与 identity 的全部
  相关写入均具备 after-commit 版本失效测试后，才允许增加缓存并关闭本差异。

## P4A-CATALOG-002：限流存储故障时返回稳定 503

- **旧行为：** Flask-Limiter 的 Redis 故障可能由扩展传播为不稳定 5xx。
- **Java 行为：** 限流计数不能原子完成时 fail closed，返回不含内部异常的稳定 503。
- **批准理由：** 不能在无法确认预算时绕过受保护读取限流，也不能泄漏 Redis 连接细节。
- **回滚/退出：** 修复 Redis 后请求自动恢复；该行为由过滤器单测和 HTTP 集成测试约束。

## P4A-CATALOG-003：读取异常不回显内部错误文本

- **旧行为：** 两个 Flask 处理器会把捕获到的异常文本直接放进 500 `message`。
- **Java 行为：** 保留列表 `subjects: []`、元信息空 `data`、`status_code` 与 Request ID
  的路由专属兼容形状，但把消息固定为“服务暂时不可用”；服务端日志只记录异常类型。
- **批准理由：** 数据库、SQL 或连接异常可能携带内部地址和凭据，不能作为兼容负担公开。
- **回滚/退出：** 该安全收敛作为永久差异保留；控制器测试约束两条路由的字段与脱敏。

## P4A-CATALOG-004：公共题库 GET 不再同步刷新

- **旧行为：** 七条 `/api/public/banks*` GET 在指标缺失或过期时由请求线程取得刷新锁，
  聚合跨 owner 源表并 `DELETE`/`INSERT`/`COMMIT` 整张指标表；冷请求可等待最多 8 秒。
- **Java 行为：** GET 永远只读取 catalog 自有的最后一次 complete 投影，不取得刷新锁、不排队
  刷新，也不写 PostgreSQL 或 catalog Redis；Cold 或 age `> 900s` 时返回固定安全 503。
- **批准理由：** HTTP GET 不应承担写入、分布式锁竞争和跨模块聚合。把刷新移出请求路径同时消除
  partial refresh 暴露与不可控尾延迟。
- **风险与观测：** complete snapshot 缺失或 hard-expired 会显式降低可用性，而不是偷偷回源；
  readiness、`snapshot.unavailable` 和刷新成功/失败指标用于告警。
- **回滚/退出：** 生产切流仍为 0，可停止 Java shadow。启用切流前必须先运行显式 bootstrap/projector。

## P4A-CATALOG-005：原子完整投影与 300/900 秒状态机

- **旧行为：** 只用 `MAX(public_bank_plaza_metrics.updated_at)` 推断新鲜度；部分行、混合代次、
  撤回后遗留行和成功的空结果均无法被可靠区分。
- **Java 行为：** metrics、viewer state、规范化 SHA-256 digest、代次、行数、source 分解、
  projector schema 与 source high-watermark 在 PostgreSQL 单写事务中完成；`<=300s` 为 Fresh，
  `300s < age <= 900s` 继续服务最后 complete 代次，其他状态固定 503。
- **完整性边界：** projector 在写事务结束前全量验证计数、代次与 digest；投影表的任何非维护
  变更都会在同一数据库事务中使 complete marker 失效。GET 因而只做常量级 marker/索引样本
  检查，不在每个匿名请求上全扫投影表。
- **批准理由：** 完整性必须属于一次原子提交，而不是任意一行的时间戳；同时不能把完整性校验
  放大为每次 GET 的 O(N) 工作。
- **回滚/退出：** 失败刷新回滚并保留上一 complete 代次；写侧可见性事件未全部桥接前保持
  `production_cutover=false`。

## P4A-CATALOG-006：两个“7 天”字段修复为真实滚动窗口

- **旧行为：** `new_banks_7d` 与 `active_users_7d` 实际共用北京时间当天 00:00 的 cutoff，
  名义上的七天字段只统计当天。
- **Java 行为：** 两个字段均使用统一服务器 Clock 的 `now - 7 days`；无时区列按
  `Asia/Shanghai` 本地时间比较，带时区活动列按同一 Instant 比较，边界包含 cutoff。
- **批准理由：** 字段名已经承诺滚动七天，继续复制当天统计会永久化已确认的业务缺陷。
- **风险与观测：** 数值会与旧实现不同；隔离 golden 明确只豁免这两个字段，PG16/18 测试覆盖
  cutoff 前一微秒、恰好 cutoff 与后一微秒。
- **回滚/退出：** 如业务方要求保留旧口径，可仅回退 cutoff 策略；响应字段和投影结构不变。

## P4A-CATALOG-007：公共题库异常固定为安全 500 文案

- **旧行为：** GET 内刷新、数据库和映射异常可能沿不同路径形成不稳定 5xx，并可能携带内部文本。
- **Java 行为：** 保留 legacy `status/code/message/status_code/request_id` 外形，500 消息固定为
  “服务暂时不可用”，日志只记录异常类型，不把 SQL、连接地址或凭据带回客户端。
- **超范围路径 ID：** Flask/Werkzeug `<int:...>` 会匹配任意精度的 Unicode 十进制数字
  （通用类别 `Nd`，包括 ASCII、阿拉伯-印度与全角数字）；Java 先按数字值归一化，超过
  `Long.MAX_VALUE` 的匹配请求完成公共限流后以同一固定安全 500 收敛，且不进入 catalog SQL。
  负数、非十进制整数以及 `Nd` 之外的数字字符仍在限流前走 converter 404。
- **批准理由：** 内部异常文本不是应被迁移的业务契约。
- **回滚/退出：** 该安全收敛永久保留；控制器测试禁止异常文本出现在响应中。

## P4A-CATALOG-008：公共读取限流存储故障时稳定失败关闭

- **旧行为：** 七条公共 GET 继承 Flask 全局按 endpoint、用户优先/IP 兜底的
  `10/second;500/hour;5000/day` fixed-window 限流；Redis 故障可能传播为不稳定 5xx。
- **Java 行为：** 保持三档预算、endpoint 隔离、actor 选择、四个限流头、429 信封和 converter
  404 不扣额度的可观测契约；任何一个 Redis 原子窗口无法记录时返回固定安全 503。
- **批准理由：** 不能在预算状态未知时悄悄放行，也不能泄漏 Redis 客户端或地址信息。
- **回滚/退出：** Redis 恢复后自动恢复请求；生产倍率仍由部署环境显式配置，Java shadow
  证据使用倍率 1。

## P4A-CATALOG-009：拒绝分号矩阵参数歧义路径

- **旧行为：** Werkzeug 不把分号当作路径参数分隔符，带 `;...` 的公共题库变体通常落入统一
  404；它们不属于七条登记路由。
- **Java 行为：** Spring Security `StrictHttpFirewall` 在 MVC 路由和公共限流前统一拒绝分号
  路径并返回安全 400；公共路由 resolver 也 fail closed，不把它误判为匿名详情。
- **批准理由：** Spring MVC 默认会移除 matrix parameter 后再做 PathPattern 匹配。若仅比较
  controller 字符串，未来的 `/joined` 等受保护路由可能被歧义路径错误归入匿名规则。
- **保持不变：** 七条合法路径、`<int:bank_id>` converter 404、业务 404 和限流计数语义均不变。
- **回滚/退出：** 永久保留该防歧义规则；完整 SecurityFilterChain HTTP 测试约束 400 发生在
  controller 与限流器之前。
