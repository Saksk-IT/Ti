# Phase 4C：练习与学习记录

本目录保存 `learning` 垂直切片的实现前合同、所有权 overlay、批准差异和可重复证据。
Phase 1/Phase 4A/Phase 4B 的历史基线保持不可变；Phase 4C 只能通过显式 successor
合同推进，不得把后续结论回写成早期事实。

Phase 4B 合同文档本身也保持 immutable。为维护 WORM 而调整的历史验收测试，只能接受
Phase 4C successor 合同中绑定的 accepted commit 与精确 source hash allowlist；不得按工作树、
HEAD 或任意新 source hash 动态放行，也不得据此改变 Phase 4B 的历史结论。

Phase 2 的历史 `local-reference-verification.json` 及 Phase 4B 副本同样保持字节不可变。
Phase 4C 使用版本化 successor 报告追加当前 build-context，由固定 allowlist gate 校验连续锚点和
唯一 tip；静态门禁不得扫描任意报告或接受调用方传入的报告路径，采集脚本也必须显式指定新路径、
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

合同通过只授权下一检查点实现 HTTP-neutral Java 能力。当前测试证据闭合逐来源行事务原语、
严格兼容数据解析、目标真子集/冲突和提交结果未知的阻断表达；完整 operator 的全局
dry-run/preflight、全量 blocker 汇总与逐项批准仍未闭合。生产
operator 实现必须在 dedicated connection 上用 session-level advisory lock 覆盖整个 preflight 与 apply，并在窗口内
冻结 legacy source、normalized target 及 bank/question membership 写入，或记录可比较的 version/digest
并在 apply 前复核；还必须用持久 migration ledger/version 或等价 tombstone 防止目标被有意清空后
从保留的 legacy source 复活标签。因此完整迁移设计和生产执行器均尚未闭合。两条 HTTP alias 仍需独立的 Security、限流、
Controller、OpenAPI、双运行时对比与切流门禁。
