# Phase 4C：练习与学习记录

本目录保存 `learning` 垂直切片的实现前合同、HTTP-neutral read 后继合同、所有权 overlay、批准差异和可重复证据。
Phase 1/Phase 4A/Phase 4B 的历史基线保持不可变；Phase 4C 只能通过显式 successor
合同推进，不得把后续结论回写成早期事实。

Phase 4B 合同文档本身也保持 immutable。为维护 WORM 而调整的历史验收测试，只能接受
Phase 4C successor 合同中绑定的 accepted commit 与精确 source hash allowlist；不得按工作树、
HEAD 或任意新 source hash 动态放行，也不得据此改变 Phase 4B 的历史结论。

Phase 2 的历史 `local-reference-verification.json` 及 Phase 4B 副本同样保持字节不可变。
Phase 4C 使用版本化 successor 报告追加当前 build-context，由固定 allowlist gate 校验“Phase 4B 锚点 →
Phase 4C 入口 → Phase 4C HTTP-neutral read → access fail-closed hardening”的四节点连续链和唯一 tip；静态门禁不得扫描任意报告或接受调用方传入的报告路径，采集脚本也必须显式指定新路径、
拒绝任何已存在目标并以原子 no-clobber 方式发布。固定门禁同时绑定 canonical schema SHA，采集期间
Dockerfile/build-context 的前后摘要必须一致。

当前第一个有界切片是个人题库 `user-counts` 双 alias。Phase 4B 已冻结调用方、golden、
八个 SQL family 与 PostgreSQL 16/18 证据，并确认完整用例和未来 HTTP owner 为
`learning`。本目录首先闭合以下实现前门禁：

- `learning` 的完整 HTTP-neutral 请求、结果、查询顺序与失败边界；
- `personalbank::api` 只暴露访问判定和题目范围事实，禁止读取 learning persistence；
- 共享访问同时绑定请求题库、分享记录与分享本体，拒绝跨题库、未知权限和非确定性首行授权；
- `bank_<bank_id>_tags` compatibility namespace 的唯一 owner overlay；
- operator-only、幂等、逐来源行原子的显式迁移；
- GET 禁止 DDL/DML，生产 schema/index、Controller、OpenAPI、route delta 和切流继续为 0。

实现前合同已经由 `personal-bank-user-counts-read-contract.json` 的固定第二层后继承接。当前生产面只新增
17 个 `learning`/`personalbank` 主源码并修改 `LearningApplicationApi`，累计形成 27 个公开应用方法；
`learning` 以 `NOT_SUPPORTED` 编排，模块内查询与 personalbank facts 使用独立 `REQUIRES_NEW` 只读事务，
候选题使用单个 PostgreSQL `integer[]` 参数。每次 facts 调用重新鉴权，任何 `DENIED` 都终止并丢弃部分字段；
只有可选字段的基础设施/事务查询异常允许局部降级。第四个 WORM tip 固定当前 40 文件模块 manifest、
288 文件生产面与 Java build-context；前三个 WORM 报告保持字节不可变，最后一次追加专门绑定空/未知
分享权限 fail closed 与 optional 事务 25P02 故障不扩散的最终生产面。

当前测试证据同时闭合逐来源行事务原语、
严格兼容数据解析、目标真子集/冲突和提交结果未知的阻断表达；完整 operator 的全局
dry-run/preflight、全量 blocker 汇总与逐项批准仍未闭合。生产
operator 实现必须在 dedicated connection 上用 session-level advisory lock 覆盖整个 preflight 与 apply，并在窗口内
冻结 legacy source、normalized target 及 bank/question membership 写入，或记录可比较的 version/digest
并在 apply 前复核；还必须用持久 migration ledger/version 或等价 tombstone 防止目标被有意清空后
从保留的 legacy source 复活标签。因此完整迁移设计和生产执行器均尚未闭合。两条 HTTP alias 仍需独立的 Security、限流、
Controller、OpenAPI、双运行时对比与切流门禁。

## User-counts HTTP entry gate

HTTP 入口通过第三层显式 successor 承接已经实现的 HTTP-neutral read，而不改写历史合同。
`personal-bank-user-counts-read-contract.json` 的物理 SHA-256
`458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73`
保持不可变；HTTP entry gate 只能精确绑定它并记录后续 source allowlist，不能从当前工作树、HEAD
或任意新哈希反向放宽 predecessor。

固定旧提交的 HTTP boundary evidence 最终包含 62 个双 alias case，并额外执行 8 个
CORS/OPTIONS 运行时观察，覆盖 GET/HEAD/OPTIONS、API/Web 认证协商、首参数、路径整数、错误信封、
请求 ID、CORS 与无业务副作用边界。其 case payload SHA-256 为
`f577ff99a7f04030fd5f4dae0f95610351d4fcfff92de7e9ca0c406516725dbf`，document payload
SHA-256 为 `3e8f7c24548d979723d2601c11221b9e569de7b342e6c3c0d8daa25de74cdd2f`。
这只是固定旧栈观察，不代表 Java HTTP 已实现，也不替代浏览器、真实 Servlet、反向代理或生产流量证据。

独立 rate-limit evidence 固定 7 组旧栈事实：`10/second`、`500/hour`、`5000/day` 三个窗口，
两个注册 endpoint 的 alias scope，API/Web 429 内容协商，Session/Bearer/IP key 选择，以及 Redis
连接拒绝。`10/500/5000` 是旧 base 配置；固定生产部署默认乘数为 100，实际默认是
`1000/second;50000/hour;500000/day`，并可由部署环境显式覆盖。该证据不宣称真实生产吞吐、
多 worker 收敛、Redis 恢复连续性或可信代理地址链已验证。

`P4C-LEARNING-007` 至 `P4C-LEARNING-012` 是本入口的批准差异集合，依次固定：显式 Bearer
选择与统一拒绝、user-counts 不写 `users.last_active`、按有效 actor 的 HMAC 假名独立限流与 Redis
故障 503、仅 API alias 的 CORS 和无副作用 OPTIONS、Unicode `Nd`/溢出/防火墙路径边界，以及
HEAD 与 GET 同语义但所有状态零字节响应体。后续实现必须逐项携带差异 ID、强制测试和可观察影响，
不得把批准差异解释为绕过证据或切流门禁。

当前 entry gate 的状态是“只授权未来精确 HTTP slice，生产实现尚未开始”：公开应用方法仍为 27 个，
有效迁移状态仍为 **11 migrated、600 pending、0 production cutover**。相对 HTTP-neutral read
predecessor，`server/src/main`、`server/src/main/resources`、OpenAPI 和 route 状态均为零变更；两条
user-counts operation 仍未实现、未迁移、未切流。本门禁只允许下一步新增精确 Controller、
route-specific Security/error writer、独立 rate limiter、路由级 CORS、必要配置与 OpenAPI；
operator、schema/index、真实迁移、全局 preflight 和 production cutover 继续禁止。下一生产切片改变
main/resources/OpenAPI 后必须生成并验证新的追加式 WORM，当前 read WORM 不能为未来生产面背书。
