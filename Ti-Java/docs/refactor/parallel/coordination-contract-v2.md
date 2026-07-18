# Ti-Java 并行重构协调合同 v2

## 1. 追加式地位与目的

本文件是 `coordination-contract.md` 的追加式 successor。v1 字节保持不变；v2 只强化新波次的机器可验证边界，不改写任何业务合同、WORM、route delta 或历史验收结果。冲突时，新波次采用 v2 的更严格规则。

v2 的目标是允许多个 Codex Worker 在独立 worktree 中并行建设 HTTP 入口之前的模块内部能力，同时让 `INT` 能以固定证据拒绝越权、交叉覆盖、伪造交接和权威状态冒进。控制面本身不授权业务实现、路由迁移、schema/index、数据迁移、网关或生产切流。

当前业务权威状态固定为 **13 migrated / 598 pending / 0 production cutover**。建立或执行 v2 wave 不改变这些数字。

## 2. 单一主线写入者

- `INT` 仍是 `main`、主工作树、主索引、`origin/main`、中央权威文件和 route/acceptance/successor/WORM 链的唯一写入者。
- Worker 必须从 assignment 的精确 `BASE_SHA` 创建独立 Codex Worktree，并使用 assignment 固定的 `codex/parallel-<lane>` 分支。
- Worker 禁止检出、修改或推送 `main`，禁止向 `origin/main` 推送，禁止自行合并、变基到更新后的主线或改变固定基线。
- `INT` 一次只验证和集成一个固定实现 SHA。handoff-only 提交只承载交接证据，不进入主线。

## 3. 仓库外不可变 wave assignment

每个并行波次由 `INT` 在主线控制面提交并推送后生成一个仓库外 assignment：

`/Users/sak/.codex/coordination/ti-java/waves/<wave-id>/assignment.json`

assignment 必须满足：

1. 是无符号链接的普通文件，使用 canonical JSON（UTF-8、键排序、两空格缩进、单个结尾换行），权限移除全部写位；
2. 固定 `BASE_SHA`、base tree、v2 合同 SHA-256、验证器 SHA-256、route 状态、中央禁区、lane、分支、handoff 路径、lane 类型、HTTP-neutral 标志和全部 `ownership_targets`；
3. assignment 自身以原始字节 SHA-256 进入每份 handoff；Worker 不得复制后修改、重生成或使用聊天中的近似版本；
4. 所有授权布尔值必须为 `false`。assignment 只授予文件边界，不授予 main、authority、route、合同、schema、迁移、网关或 cutover 权限；
5. 任意目标和禁区的匹配都按完整路径段计算，不能用字符串公共前缀规避。

assignment 发布后不可原地修改。任何 lane、基线、所有权或禁区变化都要求 `INT` 生成新的 wave-id 和新 assignment。

## 4. 多目标 ownership 与中央禁区

v2 的 `ownership_targets` 是带 `kind` 的仓库相对路径数组：`prefix` 授权路径本身及其按 `/` 分段的后代，`exact` 只授权一个精确文件。一个 lane 可拥有多个互不重叠的模块内目标，以便同一垂直能力同时包含 production 与对应测试；数组之外一律无权写入。

所有权规则：

- 路径必须使用 ASCII 且规范化，不得为绝对路径，不得包含空段、`.`、`..`、反斜杠、NUL、控制字符或 `.git` 路径段；大小写折叠后的碰撞同样拒绝；
- 同 lane 和跨 lane 的目标不得相等，也不得互为祖先/后代；
- ownership 与任一中央 exact/prefix 禁区不得重叠；中央禁区优先级永久高于 ownership；
- rename/copy 的旧端和新端分别验权。只拥有目标端不能读取后复制或移动未授权源；
- 实现提交中的新增、修改、删除、rename/copy 每个端点都必须落在当前 lane 的 ownership 内；
- 只允许 Git mode `100644` 的普通 blob；可执行 mode、symlink、gitlink/submodule、二进制或无法 UTF-8 解码的新增/修改内容均拒绝。

中央禁区至少包括：根目录用户资产、两级 `AGENTS.md`、Ti-Java 总览/连续进度、全部 refactor 文档与 handoff 以外元数据、tools、contracts/OpenAPI、infra/Compose、pom/build versions、main resources/schema、共享 Web/security/config、architecture/integration/support 测试和共享/generated Web 边界。assignment 可以收紧，不能放宽此基线。

## 5. HTTP-neutral Worker

后端并行 lane 只建设 application/domain/infrastructure persistence 及其封闭测试，不建设 HTTP 入口。其实现差异会执行大小写无关的路径与内容 token 扫描，至少拒绝：Spring Web/Servlet 类型、Controller/Mapping 注解、SecurityFilterChain、OpenAPI、route-parity 和显式 API 路径标记。

候选 route 只用于说明未来中央串行切片的业务目标，始终保持 `pending-analysis-only`。Worker 不得创建 controller、过滤器、安全配置、全局错误信封、OpenAPI、route delta、HTTP golden、真实 cutover 或“已迁移”声明。

Web lane 只能消费已经 migrated 的已生成 client/facade 边界；不得生成或修改 API client、全局 transport/contract、共享 router/shell/config，新增接线由 `INT` 在串行集成阶段处理。

## 6. 两提交交接协议

每个 Worker 最终必须把工作压缩为严格的两提交链：

```text
BASE_SHA <- implementation SHA <- handoff-only SHA (branch tip)
```

- implementation commit 必须只有一个 parent，且 parent 精确等于 `BASE_SHA`；不得为 merge commit。
- implementation diff 只能修改 ownership；不得包含 handoff。
- handoff-only commit 必须只有一个 parent，且精确等于 implementation SHA；其唯一差异必须是 assignment 固定的新增 handoff JSON。
- handoff JSON 必须使用 canonical JSON，并固定 assignment 原始字节 SHA-256、lane、branch、base、implementation SHA、13/598/0 route 状态、ownership、机器重算的完整 diff、验证记录、heavy lock 记录、风险和中央请求。
- handoff 中 main/authority/route/delta/contract/schema/migration/gateway/cutover 授权必须全部为 `false`；受保护资产与历史证据未触碰声明必须为 `true`。
- 分支本地或远程固定 ref 必须指向 handoff-only SHA。浮动 tip、stash、未提交工作树和聊天摘要不是集成输入。

`INT` 只集成 implementation SHA；handoff-only SHA 永不 cherry-pick 到 `main`。若 Worker 产生了更多实现提交，必须在交接前从原 `BASE_SHA` 重建/压缩成上述两提交链，不得要求 `INT` 猜测提交范围。

## 7. 机器验证器

固定入口：

```bash
python3 Ti-Java/tools/validate_parallel_worker_handoff.py \
  --repository-root /absolute/path/to/worktree \
  --assignment /Users/sak/.codex/coordination/ti-java/waves/<wave-id>/assignment.json \
  --assignment-sha256 <INT-published-raw-file-sha256> \
  --lane <lane> \
  --handoff-sha <full-commit-sha>
```

验证器 fail-closed 检查 assignment schema/权限/命令行固定摘要、固定 base Git 对象、控制面 blob、route 状态、跨 lane ownership、中央禁区、分支 ref、两提交图、差异端点、Git mode、HTTP-neutral token、handoff schema和声明。任何不认识的字段、status、mode 或差异类型都拒绝。`INT` 可在集成前传 `--integration-head <current-main>` 证明目标仍与 BASE 相同，并在 cherry-pick 后传 `--post-integration-head <new-main>` 证明目标字节精确等于 implementation tree。

Worker 和 `INT` 必须分别在自己的 worktree/对象库执行同一固定验证器。通过只证明该 handoff 满足控制面边界，不等价于业务、HTTP、性能、数据、生产或完整 DoD 验收。

## 8. 重型验证与锁

v1 的三把仓库外锁和顺序继续有效：

`main-write.lock` → `authority-chain.lock` → `heavy-verify.lock`

任何 Maven（含定向测试）、Testcontainers、Docker 或 Compose 都必须先原子取得唯一 `heavy-verify.lock`，并在子进程与容器清理完成后释放。Worker 没有取得锁时可以运行纯 Git、Python 静态门禁或 lane 明确允许的非重型前端检查，但必须在 handoff 记录 `not_acquired / not_run`，不得声称执行了重型验证。

## 9. INT 串行集成与拒绝条件

`INT` 对每个 lane：

1. 核对 assignment 原始摘要、`BASE_SHA` 和 `origin/main` 祖先关系；
2. 获取 Worker 分支对象，以 handoff-only SHA 运行固定验证器；
3. 以当前 main 作为 `--integration-head`，确认该 lane 的全部目标仍与 BASE 相同；审阅业务语义与测试，不用机器边界验证代替代码评审；
4. 只 cherry-pick 固定 implementation SHA；一次只处理一个 lane；随后以新 main 作为 `--post-integration-head`，确认目标字节精确复现 Worker implementation tree；
5. 如需接线、API、route、合同或全量验证，由 `INT` 在中央锁下另建追加式提交；
6. 验证并推送 `main`，再为后续波次发布新 `BASE_SHA`。

出现下列任一情况立即拒绝：assignment 可写/漂移、base 不匹配、分支名或 ref 不匹配、提交图不是精确两提交、ownership/禁区冲突、rename/copy 任一端越权、symlink/gitlink/二进制、HTTP-neutral token、handoff 不是唯一新增文件、摘要/差异/声明不一致、重型验证无锁记录，或任何 route/cutover/authority 冒进。

## 10. 阶段含义

本 wave 完成后，最多表示 Phase 4 的多个业务模块取得 HTTP 入口前的并行基础，以及 Phase 6 在已迁移 API 上取得额外页面能力。它不会自动完成 Phase 4D/4E/4F/4G，也不会让 route 数字从 13/598/0 前进。每条候选 route 的黄金映射、真实认证/网络/Redis/PostgreSQL 等价、OpenAPI、route delta、外部锚定和生产切流仍由 `INT` 后续逐条串行闭合。
