# Phase 4C 已批准差异：learning 组合与个人题库标签迁移

## P4C-LEARNING-001：user-counts GET 不再执行标签 DDL/DML

- **旧行为意图：** 非空且非精确小写 `all` 的 tag 过滤会在请求线程尝试创建
  `user_question_tag_items` 及两个索引；目标 scope 为空时再读取
  `user_progress.bank_<bank_id>_tags`，尝试删除、重建并提交规范化行。
- **固定旧栈观察：** SQLAlchemy 2.0.51 下 raw string/qmark 参数在游标执行前失败，
  PostgreSQL 也不支持 `INSERT OR IGNORE`；legacy-only golden 因而返回全零，迁移 commit
  没有到达。该观察不能冒充成功迁移。
- **Java 行为：** HTTP GET 永远只读已规范化的 learning-owned 标签事实，不建表、不建索引、
  不回读兼容 JSON、不提交迁移。表或必要结构缺失时部署/readiness 失败，禁止请求自愈。
- **迁移替代：** compatibility namespace 只允许由显式 operator-only 任务迁移；默认 dry-run，
  apply 前必须完成全局 preflight。生产实现须在 dedicated connection 上取得 session-level advisory
  lock，并让该锁覆盖完整 preflight 与 apply；窗口内冻结 legacy source、normalized target 以及
  bank/question membership 写入，或捕获可比较的 version/digest 并在 apply 前复核。逐来源行仍需
  加锁，并在独立事务内只执行 `INSERT ... ON CONFLICT DO NOTHING`。由于源数据保留，operator
  还必须用持久 migration ledger/version 或等价 tombstone 区分“从未迁移”与“迁移后用户清空目标”；
  否则目标清空后重跑会复活旧标签。目标仍存在时的紧邻第二遍必须零 DML。
- **兼容输入边界：** 旧 JSON-array-string 与 CSV 语义仅在能够无损解析、规范化和复现时支持。
  单个 tag 保持旧 `normalize_tags` 的 20 Unicode code point 截断语义；不同原值在清洗或截断后
  碰撞、ID 规范化冲突、raw compatibility 非法形态，以及语义可识别但无法无损复现的形态都是
  blocker，禁止任意猜测或静默合并。
- **批准理由：** GET 不能拥有 schema 和迁移副作用；固定旧运行时本来也无法可靠完成该迁移。
  把错误的“请求时尽力迁移”改为可审计、可回滚、可阻断切流的显式步骤，才能保护现有数据。
- **切流门禁：** unresolved、conflict、orphan、invalid disposition 必须为零或有逐项批准；全局锁、
  写冻结或 version/digest 复核也必须闭合。当前 operator 实现和全局 preflight 证据均未闭合，
  schema/index 变更、真实数据 apply、operator 执行与 HTTP 切流均未获授权。

## P4C-LEARNING-002：可选统计采用独立本地事务实现字段级 fail-soft

- **旧行为意图：** total/access 失败向外传播；favorites 失败只回退 0，mistakes 失败只回退 0，
  types 失败只回退空列表。
- **PostgreSQL 实际边界：** 同一事务中的首个 SQL 错误会使后续语句进入 `25P02`，单纯
  `try/catch` 会把一个可选字段故障扩散到后续字段。
- **Java 行为：** access 与 total 保持硬失败；favorites、mistakes、types 的 learning 读取和
  personalbank 事实查询各自使用干净的模块本地只读事务。一个可选阶段失败只触发该阶段回退，
  后续阶段继续执行；禁止跨模块数据库事务。
- **批准理由：** 这实现了旧代码明确表达的字段级降级意图，同时消除 PostgreSQL poisoned
  transaction 的偶然级联。PG16/18 必须覆盖失败、回滚与后续可读性。
- **保持不变：** 四阶段顺序、source 为 favorites/mistakes 时的严格 total、types 映射、
  计数和 shuffle 语义保持 golden 兼容。

## P4C-LEARNING-003：非法 compatibility 数据显式阻断，不再静默吞弃

- **旧行为：** 非法 JSON、非法字段、题目 ID 解析失败和迁移异常多由宽泛异常捕获吞掉，
  tag 过滤随后表现为全零。
- **Java 迁移行为：** dry-run 对 raw compatibility 非法形态、非法 root/字段、规范化 ID 冲突、
  截断冲突、孤儿 bank/question 和目标分歧生成确定性 disposition；apply 不删除源、不自动 merge、
  不静默丢弃，任一未处置项阻断本次 run 和后续切流。
- **旧格式支持边界：** JSON-array-string 与 CSV 语义只有在能够无损还原题目 ID、标签、顺序无关
  集合语义和目标行时才可迁移；即使能识别旧格式，只要无法无损复现，仍必须报告 blocker。
- **目标优先：** 目标 scope 已有任意行时保持旧“目标整体优先”语义并零写入；源派生集合不是
  目标子集时报告 conflict，不复活用户已经删除或修改的标签。
- **批准理由：** 数据迁移的异常不能伪装成空业务结果。显式报告让人工修复或逐项差异批准成为
  可追踪决定，且源数据始终保留。
- **回滚：** 单来源行提交前故障会尝试回滚该行全部插入；只有回滚成功或 PostgreSQL 返回明确
  非歧义 SQLSTATE 时才能证明零提交，其中 `40001`/`40P01` 供未来 operator 有界重试。回滚失败
  且已经写入，或写入后的 SQLSTATE class 08、`40003`、缺失 SQLSTATE commit 异常，必须保持提交
  数未知。恢复 legacy 写入后禁止自动反向删除，只允许回滚流量并前向修复。
- **当前证据边界：** test-only fixture sweep 只证明逐来源行锁、回滚、仅插入与幂等原语；它会在
  同一 fixture 中分别观察 blocker 与可迁移行，且已固定严格 JSON、Python Unicode whitespace、
  非法字段/规范化冲突、目标真子集与 target-conflict、目标题目 membership、回滚失败及提交结果
  未知等逐行 disposition；它仍不是生产全局 apply，也没有证明 dry-run 全量汇总、逐项批准或“任一
  未处置项阻断整次 run”，也没有证明真实网络下的 ambiguous commit 恢复或迁移后删除/tombstone
  语义，不得据此授权生产 operator。

## P4C-LEARNING-004：`bank_<bank_id>_tags` namespace 转交 learning

- **Phase 1 历史：** compatibility namespace 初始归 `personalbank`，而物理源表
  `user_progress`、目标表 `user_question_tag_items` 均归 `learning`。
- **Phase 4C 有效所有权：** 仅将 `db_kv_namespace:bank_<bank_id>_tags` overlay 为
  `learning`；不改写 Phase 1 文件，不转移 `user_question_banks`、`user_bank_questions`
  或其他 `user_progress` namespace。
- **批准理由：** `personalbank` 不允许依赖 learning，反向让它读写 learning persistence 会破坏
  DAG。转交后，learning 可在本模块事务中迁移兼容状态，并通过
  `learning -> personalbank::api` 校验 bank/question membership。
- **生产边界：** personalbank 只公开 provider-owned immutable bank/question 事实，不暴露
  Entity、Repository、SQL row，也不查询收藏、错题、进度或标签表。

## P4C-LEARNING-005：跨模块读取使用有界多快照并在事实查询时复核权限

- **旧行为：** Flask 在一个共享 SQLAlchemy Session 中直接 join personalbank 与 learning 表；
  PostgreSQL `READ COMMITTED` 仍可能让不同 statement 看到不同已提交快照，但访问检查只发生一次。
- **Java 行为：** learning 编排不创建跨模块事务；每个模块只在自己的短只读事务中查询。
  personalbank 的聚合事实 API 接收当前 viewer，并在返回题库聚合前再次执行 owner/public/share
  访问检查。权限在初检后被撤销时，整个用例拒绝，不返回先前已读取的 learning 集合。
- **提前返回边界：** 在 tag 为空、tag 查询异常触发 fail-soft，或准备返回全零视图之前，learning
  必须先调用 personalbank 权限复核。personalbank access 或任一 facts 调用返回 `DENIED` 时都是
  terminal `DENIED`，必须丢弃已得到的部分结果；只有基础设施或查询异常才可按合同对相应可选字段
  fail-soft，权限拒绝不得伪装成空结果、零值或可选字段故障。
- **批准理由：** 模块 DAG 和事务所有权优先于伪造一个跨模块共享事务；最终事实复核关闭了初检与
  聚合之间的权限撤销窗口。查询总数增加必须有固定预算与 PG16/18 规模证据，禁止 N+1。
- **保持不变：** 正常稳定数据集上的 total/favorites/mistakes/types 与排序保持 golden 等价；
  仅并发权限撤销时从旧实现可能继续成功收敛为 fail closed。
- **切流门禁：** 15 万题、收藏/错题规模和 tag typed-array 必须重新捕获计划；不得把 900 个
  test-only tag 参数当成生产上限。

## P4C-LEARNING-006：共享题库授权关闭跨题库与非确定性绕过

- **冻结旧行为：** Phase 4B golden 记录了 `bank_shares.bank_id` 未与
  `bank_share_records.bank_id` 校验，以及无 `ORDER BY` 的 `fetchone()` 会让多条分享记录
  的结果依赖数据库返回顺序；固定夹具中的跨题库记录因此错误地授予访问权。
- **Java 行为：** `personalbank::api` 的访问查询必须同时绑定请求题库、分享记录题库和分享
  本体题库；只接受 `read`/`copy` 权限，未知或空权限 fail closed。对同一用户/题库的多条记录
  采用确定性排序后选择任一仍 active 且 `expires_at` 为 NULL 或严格晚于北京当前时刻的合法
  grant；不能因一条过期记录先出现而遮蔽后续合法 grant。到期时间等于当前时刻必须拒绝。
- **安全差异：** 跨题库夹具的目标结果由旧实现的 `200` 改为 `DENIED`；这是关闭越权而非
  静默改变普通 owner/public/share 正常语义。实现前必须以固定 unit、adapter 和 PG16/18
  夹具验证 join、权限、排序、到期边界及复核调用。
- **切流门禁：** 未通过这些固定安全测试前，不得实现 HTTP Controller、Security matcher、
  route/OpenAPI 或生产切流；read-contract 不得自行声明 operator 或全局迁移 preflight 已授权。
