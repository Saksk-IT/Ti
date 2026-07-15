# 新旧对比、停写切换与整套回滚协议

状态：Phase 1 设计契约。本文只定义后续实现、演练与审批门禁，不授权执行生产切换。

基线：`700006dfdfa063deb4387be572911e782bcea0d9`

配套权威手册：`../04-migration-runbook.md`。若两者发生冲突，先停止执行并在同一变更中收口两份文档；尤其不得改变其“整体部署切换”和“写后优先前向修复、其次第三套库反向迁移、最后才可经批准丢弃窗口写入”的顺序。

<!-- phase1-protocol-markers
READ_COMPARE
ISOLATED_WRITE_COMPARE
SELECT_ONLY
NO_DUAL_WRITE
FREEZE
CUTOVER
ROLLBACK_PRE_WRITE
ROLLBACK_POST_WRITE
-->

## 1. 不可违反的安全边界

1. 任一时刻每份业务数据只有一个运行时 writer。Python 和 Java 不得写同一数据库、Redis、对象前缀、队列或外部副作用目标。
2. 对比环境由同一受控快照恢复出两个独立副本；旧运行时只写 legacy 副本，Java 只写 java 副本。禁止通过“双写后观察结果”验证兼容性。
3. 只读对比账号必须是数据库 `SELECT_ONLY` 角色；被测 GET 还要用数据库审计证明没有 DML、任务入队、对象写入或外部副作用。
4. 最终切换必须先 `FREEZE` 并撤销旧 writer，再授予新 writer；回滚同样先停写。流量开关不能代替数据库权限隔离。
5. Redis 是缓存、协调或临时投递设施，不是恢复业务事实的来源。切换可丢弃可重建缓存，但不得把 Redis dump 当作 PostgreSQL 快照。
6. 所有快照、恢复、迁移和校验命令只接受显式环境标识、主机与数据库名；脚本必须拒绝空变量、生产默认值和来源/目标相同。
7. 任何未解释的状态码、授权、排序、空值、精度、数据库后置条件或事件差异都阻断切换；不得用宽泛忽略规则掩盖。

`NO_DUAL_WRITE` 的具体含义：允许两个运行时同时启动做只读对比，也允许它们分别写各自隔离副本；绝不允许同一个用户命令同时作用于同一套生产事实，亦不允许 Java 在生产路径回调 Flask 完成写入。

## 2. 状态机与批准点

| 状态 | writer | 允许动作 | 进入条件 | 退出/回退 |
| --- | --- | --- | --- | --- |
| `LEGACY_ACTIVE` | Python | 正常业务、离线对比 | 当前稳定态 | 进入 `FREEZE_REQUESTED` |
| `FREEZE_REQUESTED` | Python，随后归零 | 停新写、排空、备份 | 变更批准、值守人员到位 | 未撤销旧 writer 前可取消 |
| `FROZEN` | 无 | 快照、校验、必要的受控迁移 | 入口停写、任务排空、DB writer 已撤销 | `LEGACY_ACTIVE` 或 `JAVA_STARTING` |
| `JAVA_STARTING` | 无，健康检查后 Java | schema 校验、只读 smoke、再授写 | 快照可恢复、门禁全绿 | 写前回滚或进入观察 |
| `JAVA_ACTIVE_OBSERVE` | Java | 受控写、监控、验证 | Java writer 唯一且 smoke 通过 | `JAVA_ACTIVE` 或停写回滚 |
| `JAVA_ACTIVE` | Java | 正常业务 | 观察窗批准 | 任何回滚都先进入 `FROZEN` |
| `ROLLBACK_FROZEN` | 无 | 事故快照、恢复冻结点、校验 | 入口和所有 writer 已停止 | Python 恢复后回到 `LEGACY_ACTIVE` |

状态变化由一名执行者发起、一名复核者确认，并在变更记录中写入 UTC 时间、Git SHA、镜像摘要、数据库快照 ID、schema 版本、writer 角色和流量开关版本。禁止只凭聊天消息宣布完成。

## 3. 共同前置条件

- 路由矩阵中的被测 operation 已有契约来源、目标模块、认证语义和黄金样本；`inferred/unknown` 不计通过。
- `module-contracts.json`、`business-invariants.json` 及其校验器通过；Spring Modulith 后续须验证 DAG、公开接口和 allowedDependencies。
- 两个运行时、数据库、Redis、对象存储前缀、队列、端口和凭据全部独立；比较器不是生产依赖。
- 快照来自同一一致性点，包含 schema、数据、sequence/identity、扩展和必要的大对象；生成日志无 warning，恢复已在空目标验证。
- 时间、随机数、上游响应、文件与消息投递使用固定时钟/种子和可审计 fake；不能安全重放的真实外部副作用一律禁用。
- 每个写用例都有规范化数据库比较器。它按表主键稳定排序，区分缺失、`null`、空值和零；仅忽略逐字段登记的非业务值，如独立生成但已证明无语义的 request ID。
- Secret、Cookie、教务凭据、完整敏感提示词和用户私密数据不进入差异报告；fixture 必须脱敏。

## 4. `READ_COMPARE`：无副作用读取对比

### 4.1 建立环境

1. 从快照 `S0` 恢复 `legacy_read_db` 与 `java_read_db`，完成 row count、关键约束和抽样 checksum 校验。
2. 为两库创建只具 `SELECT` 的运行账号；开启 SQL 审计或事务级写保护。两个运行时分别使用独立、可丢弃 Redis。
3. 固定请求时钟、身份、角色、locale、时区、分页、排序、feature flag 和上游 replay fixture。匿名请求也要显式记录匿名主体。
4. 在请求前记录两库 fingerprint、队列深度、对象前缀清单和外部 fake 调用计数。

### 4.2 执行与比较

1. 先运行探针证明写 SQL、任务入队和外部写会被拒绝；探针失败则不执行批次。
2. 向 Flask 与 Java 发送语义相同的请求，保存原始 status、headers、content type、body bytes、耗时和 request ID 关联。
3. 先比较未规范化输出，再按 operation 白名单规范化明确的动态字段。数组只有在契约声明无序时才可排序；数据库默认顺序不能被比较器“修好”。
4. 比较状态码、认证/授权、信封、字段类型、缺失/空值、枚举、时间、数值精度、分页、排序、下载字节或 SSE 事件序列。
5. 请求后再次取数据库 fingerprint、队列、对象和 fake 调用计数。任何变化都把该 GET 标为有副作用并失败。

### 4.3 通过产物

每个 operation 输出机器可读报告，至少含 fixture ID、两个镜像摘要、快照 ID、原始响应摘要、规范化规则版本、差异列表和副作用证明。通过条件是零未批准差异；批准差异必须引用已接受 ADR，不能只写“预期不同”。

## 5. `ISOLATED_WRITE_COMPARE`：隔离数据库写入对比

### 5.1 建立双副本

1. 从同一快照 `S0` 恢复 `legacy_write_db` 与 `java_write_db`；分别创建仅能写本副本的运行账号。
2. 为每边分配独立 Redis、对象前缀、队列和 fake 外部端点。基础设施防火墙/ACL 必须让两个账号无法访问对方资源。
3. 记录执行前 schema fingerprint、所有受影响表的规范化数据摘要、sequence 值和外部 fake 状态。

### 5.2 用例矩阵

每个写 operation 至少执行：首次成功、同幂等键重放、同键不同摘要、并发竞争、授权失败、边界值、事务中点故障、超时后重试。考试还覆盖超时交卷、`pending_review` 和重新评分；答题覆盖统计/错题原子性；教务覆盖 Redis 不可用和部分 term 失败。

Python 命令只发送给 legacy 环境，Java 命令只发送给 java 环境。外部 fake 可以返回同一录制响应，但每边有独立状态和调用计数。执行次序、并发 barrier、故障注入点和重试 key 必须相同。

### 5.3 比较最终事实

1. 比较 HTTP 结果及幂等重放结果；不以“首个响应相同”代替状态比较。
2. 导出本 operation 拥有表的规范化最终状态、受影响 row count、唯一/外键/check 约束、sequence、outbox 和审计事实。
3. 跨模块只比较标量 ID 和公开事件 payload，不遍历或共享另一模块实体。
4. 比较对象内容摘要、队列/fake 调用次数和敏感数据泄漏扫描；缓存只验证可重建，不要求内部 key 完全相同。
5. 对合法实现差异建立显式语义映射，例如新 outbox 表可额外存在，但业务事实、对外事件和次数必须等价。
6. 保存报告后销毁双副本；禁止把比较副本提升为生产数据库。

通过条件：所有不变量成立、最终业务事实语义等价、外部副作用次数等价且零未批准差异。数据库状态无法规范化或写入触达共享目标时直接失败。

## 6. `FREEZE`：最终停写与一致性快照

### 6.1 冻结前门禁

- 指定切换负责人、数据库负责人、应用负责人、复核人和回滚决策人；确认维护窗口、用户提示与支持渠道。
- 最近一次全量备份已做空环境恢复演练；记录恢复耗时并确认满足 RTO/RPO。
- Java 镜像、配置、schema 校验、健康检查、只读 smoke、关键写 smoke 和回滚镜像均固定摘要；依赖外部可变 tag 不通过。
- 所有 additive schema 迁移已在克隆数据验证；破坏性 drop/rename/收窄不与运行时切换同窗执行。
- 队列、定时任务、SSE 发布、导入导出、考试、教务刷新和 AI 调用都有停止接单与排空办法。

### 6.2 冻结顺序

1. 网关进入维护/只读模式，拒绝新业务写；保留健康检查和明确允许的静态读取。
2. 停止调度器和 consumer 接新任务，等待在途事务/外部调用排空至批准阈值。无法安全完成的任务按其幂等协议取消，记录 task ID。
3. 停止 Python 应用写实例；在数据库侧撤销 Python writer 权限并终止遗留写会话。用审计窗口证明活跃业务 writer 为零。
4. 记录最终 WAL/LSN、最大业务时间戳、关键表 row count/约束、outbox/队列状态和对象清单；创建冻结快照 `SF` 与校验清单。
5. 在空的隔离目标执行 `SF` 恢复 smoke，至少证明备份可读、schema/扩展齐全和关键 checksum 相符。恢复验证失败不得继续。
6. 仅在批准清单内执行必要的 additive 迁移，再次记录 schema fingerprint。此时 Java 仍无写权限。

冻结不是“暂停前端按钮”：数据库侧 writer 撤销、任务排空证据和可恢复快照三项缺一不可。

## 7. `CUTOVER`：Java 单 writer 启动

1. Java 使用独立部署、独立运行凭据和明确生产配置启动；首先只授 `SELECT_ONLY`，执行 schema、模块边界、配置和只读 smoke。
2. 确认生产配置不含 Flask upstream、父目录挂载、旧项目运行时读取、共享可写 Redis 或旧 writer 凭据。
3. 数据库复核人确认 Python writer 已撤销后，才授予 Java writer；记录 grant 时间和连接身份。任一时刻不得同时存在两个 writer 角色。
4. 执行最小、可识别且可回滚的写 smoke，检查业务事实、幂等记录、outbox、审计、日志脱敏和可观测指标。
5. 在 Java 仍受只读/维护限制时，一次性把完整入口整体指向 Java；旧 Flask 保持离线且无写权。确认入口、健康检查和只读 smoke 后，由唯一变更负责人一次性解除 Java 写限制并进入 `JAVA_ACTIVE_OBSERVE`。禁止 route split、percentage split、按用户灰度、shadow write 或任何让新旧后端同时承接业务写的策略。观察错误率、延迟、连接池、锁等待、唯一冲突、队列积压、事件重复、授权拒绝率和关键业务不变量。
6. 观察窗内达到停止阈值立即关闭写入口并进入回滚判断；禁止边承受新写边“试修”。全部门禁满足且复核签字后才进入 `JAVA_ACTIVE`。

## 8. `ROLLBACK_PRE_WRITE`：Java 尚未产生业务写入

适用条件必须由数据库审计、幂等表、业务表、outbox、对象清单和外部 fake/真实调用记录共同证明：Java 自冻结点后没有任何已提交业务写或不可逆外部副作用。

1. 关闭网关写流量，撤销 Java writer（即使理论上尚未授予），停止 Java。
2. 校验当前数据库仍与 `SF` 的业务 fingerprint 一致；若仅有 additive schema，可保留但必须证明 Python 兼容，否则恢复 `SF`。
3. 以旧镜像和旧配置启动 Python，先授 `SELECT_ONLY` 做 smoke；确认后授唯一 writer。
4. 开放流量并验证关键读写、队列和监控；记录回滚完成状态。

因为没有 Java 业务写，该路径不需要合并数据；一旦证据不完整，必须按写后回滚处理。

## 9. `ROLLBACK_POST_WRITE`：Java 已产生或可能产生业务写入

禁止直接把网关切回 Python，也禁止默认恢复 `SF` 丢弃窗口写入：旧代码可能无法解释 Java 新状态，而未审计的数据回退会静默丢失用户数据。

1. 立即关闭业务写入口，停止 scheduler/consumer，撤销 Java writer，排空或隔离在途连接，进入 `ROLLBACK_FROZEN`。
2. 创建故障现场快照 `SI`，保存 WAL/LSN、审计、outbox、队列、对象清单和 Java 写入纪元范围；不得覆盖 `SF`。`SI` 是前向修复或提取窗口增量做反向迁移的权威输入，不只是事后补偿工件。
3. 由变更负责人按以下固定优先级选择并批准处置：
   - **前向修复（默认优先）**：在 `SI` 的隔离副本验证代码/配置修复与数据完整性，通过后在当前 Java 数据上受控修复并重新开放 Java；保留已接受的窗口写入。
   - **反向迁移**：若无法安全前向修复，从 `SF` 建立第三套隔离回滚库，用受审、可重复、带幂等与校验的脚本把 `SI` 中 Java 写入纪元增量转换进去；旧 Flask 只连接该回滚库做完整读写验证。
   - **恢复冻结备份并丢弃窗口写入（最后手段）**：只有业务负责人明确接受并记录数据损失，且证据证明前向修复和反向迁移均不可行时才允许。不得因时间压力把它变成默认回滚。
4. 反向迁移必须在第三套隔离数据库完成；旧 Flask 与 Java 仍不得同时写。迁移报告逐模块列出输入范围、转换、幂等键、拒绝项和 checksum，禁止维护窗口临时拼 SQL。
5. 对候选 Java 修复库或 Flask 回滚库执行与切换前等价的 schema、完整性、身份、文件、任务、不变量和契约校验；失败则保持维护模式并回到决策步骤。
6. 若选择反向迁移，停止 Java，启动旧部署并仅连接已验证的第三套回滚库；先 `SELECT_ONLY` smoke，再授唯一 writer，整体一次性切换入口后开放写入。禁止 route/percentage split。
7. 若最终批准丢弃窗口写入，才可从 `SF` 恢复 Python 兼容库并执行同等校验；变更记录必须列明受影响时间、命令/用户范围、通知和补偿方案。

即使 Flyway 变化保持向前兼容，也不能未经演练就让旧 Flask 直接连接 Java 目标库。“保留 Java 写入”不是例外路径，而是前向修复或经第三套库验证的反向迁移必须优先追求的结果。

## 10. 立即停止/回滚触发器

- 发现 Python 与 Java 同时拥有生产写权限或写入同一外部副作用目标。
- 账号锁定、题库权限、答题幂等、单次交卷、十进制评分或快照批次不变量任一失败。
- 出现无法解释的数据差异、schema drift、恢复校验失败、旧凭据不可解密或关键表约束缺失。
- 5xx、延迟、数据库锁等待、连接耗尽、队列积压或错误预算超过变更单预先批准阈值。
- 日志/报告泄漏 Secret 或个人敏感数据，或观测链路无法关联 request/command ID。

数值阈值由每次变更单依据基线流量填写；空阈值、执行时临时口头决定或“先观察看看”均不允许开始切换。

## 11. 必留证据与演练频率

每轮演练/切换保留：批准单、状态时间线、Git SHA/镜像摘要、配置摘要、快照与恢复日志、schema/data fingerprint、writer grant/revoke 审计、读写差异报告、smoke 结果、监控截图/导出、异常与回滚决定。报告只保存脱敏摘要，不保存 Secret。

在首次生产切换前，至少完整演练一次写前回滚和一次写后恢复；随后每次改变迁移方式、数据库主版本、关键 schema、备份工具或部署拓扑都要重演。恢复演练必须实际启动旧运行时读取恢复库，不能只验证备份文件存在。

## 12. 采用的工程依据

- Spring Modulith 的模块验证会检查无环依赖、只访问公开 API 及显式 allowed dependencies：<https://docs.spring.io/spring-modulith/reference/verification.html>
- PostgreSQL `pg_dump` 生成事务一致快照，但仍必须检查 warning 并做真实恢复验证：<https://www.postgresql.org/docs/current/app-pgdump.html>
- PostgreSQL 官方备份与恢复章节用于选择逻辑备份、文件级备份或 PITR，不能把不同方式的恢复保证混为一谈：<https://www.postgresql.org/docs/current/backup.html>
