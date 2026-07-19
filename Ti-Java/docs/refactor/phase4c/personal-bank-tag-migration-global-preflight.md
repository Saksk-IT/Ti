# Phase 4C 个人题库标签迁移：全局只读预检证据

## 结论

本节点只关闭 `migration_global_preflight_evidence_closed=true`。它证明固定本地夹具在 PostgreSQL 16.14 与 18.4 上可以进行全局、只读、all-or-block 的预检；它不是生产迁移 Operator，不包含 apply 路径，也不授权 Schema、索引、真实数据迁移或生产切流。

当前路由权威保持 `13 migrated / 598 pending / 0 production cutover`。

## 固定权威链

- 语义组合合同物理 SHA-256：`ba900795d92046693617d92f4de7599d604e389e7b60e1cc145d08a737518f6b`。
- 当前路由提升合同物理 SHA-256：`e5bc53bb8c011c5cf2f08447543aa3e5dd2a045b6226f064c6594a3639d7b5c9`。
- 当前 `approved-differences.md` 物理 SHA-256：`921d6626ab11d59a9667e1942953807b0aa1a81c06c01094cc109312f9d6b300`。迁移语义只承接 `P4C-LEARNING-001` 至 `P4C-LEARNING-006`；同一物理文件中的 `007` 至 `012` 仍属于 HTTP 后继差异，不能被本节点重新解释。
- `bank_<bank_id>_tags` 的唯一有效 owner 仍为 `learning`，ownership cutover 仍为 `false`。
- 历史逐行事务 primitive 仅作为前驱证据；它会写测试夹具，不能重新命名或冒充全局 dry-run。

合同 builder 只接受代码内固定的 path → SHA-256 → byte count 清单。绝对路径、`..`、任意路径段软链接、未知来源和 builder/acceptance/test/合同/本说明等控制文件均拒绝。控制文件不进入自身权威，历史合同和证据不覆盖。

为承接本节点修改前已经由 typed-normalization 与 Phase 6 Git checkpoint 固定的控制面字节，合同另固定四十二条单向 source-successor transition：十二条基础桥（四条 Phase 2、四条 Phase 6 typed bridge、两条连续进度文档与两条 Phase 6 bootstrap）、二十六条语义消费者桥、两条 post-push bridge 与两条 typed-normalization bridge。每条 transition 同时绑定 accepted SHA/bytes、当前 successor SHA/bytes 和 accepted authority；未知路径、软链接、动态目录扫描与 live `HEAD` 均拒绝。历史 acceptance 只在它们各自固定路径的 accepted 字节不再匹配时惰性委托本 Node A acceptance，不形成反向 builder import；builder 仍只调用独立的 `validate_fixed_chain`。

这四十条 transition 只是合同固定的本地 successor，不是外部 Git 锚。`source_successor_external_git_anchor_complete=false`。本节点十一个 bootstrap control source（含 Node A 自有七个控制工件、被修改的 Phase 6 Python/Java delegate implementation 与其 Python/Java anchor test）继续自排除，`bootstrap_control_sources_external_git_anchor_complete=false`、`control_sources_external_git_anchor_complete=false`，必须由后续追加的 post-push Git anchor 闭合，禁止回写本合同或冒充已经外锚。

为使历史 acceptance 在不回写旧合同的前提下识别当前物理工作树，Node A 还固定两组语义 successor。production runtime 只接受历史 297 文件清单 `d327a5ef…`，并只允许新增 GlobalPreflight、PreflightParser、PreflightReport 三个固定主源码，得到 300 文件清单 `8d28a382…`；其中 learning/personalbank main 子视图精确从 40 文件 `d20c124c…` 变为 43 文件 `2cc85505…`，changed/deleted 必须为空。WORM successor 只接受第五节点 `7b863dd3…` 与 build-context `27322797…`，验证第六节点 `283d63d5…` 后到第七节点 `93d2c377…`，并以物理 hasher 复核当前 `a23335b5…`。未知 accepted pair、额外文件、修改/删除、软链接与未知视图全部拒绝；历史合同字段保持不变，`semantic_successor_external_git_anchor_complete=false`。

## 本节点证明的范围

全局预检使用专用连接，在完整 sweep 期间持有 session-level PostgreSQL advisory lock，并以 `read-only + SERIALIZABLE + DEFERRABLE` 运行。混合夹具用于证明：

- 严格 namespace 与 bank ID round trip；严格 JSON、Unicode whitespace、20 Unicode code point 截断和碰撞判定；保留大小写以及 NFC/NFD 等不同 Unicode 序列，不做隐式规范化；
- 单 payload 在 JSON 解析前执行 `1 MiB` UTF-8 上限；SQL 先计算 octet length，仅物化未超限 payload，超限行不读取 target 或 membership；完整 sweep 另有 `100,000` 行和 `256 MiB` 总量上限；
- PostgreSQL text 必须无 NUL、无孤立 surrogate；合法 surrogate pair 原样保留，无法无损表示的标签以 `TAG_NOT_LOSSLESS` 失败关闭；
- bank 存在性、正 question ID membership 与规范 digest；
- 合法 source plan 之后才允许评估 target precedence，source 必须是 target 的子集，禁止自动 merge；
- 全量扫描使用实际 planner disposition 聚合所有 blocker 后作出 all-or-block 结论；组合合同中的十二种 row outcome 与五个 reporting group 只作为后续 apply/逐行事务前驱词汇继承，dry-run 不伪造 `MIGRATED` 或事务失败结果；
- advisory lock 竞争失败关闭，持锁连接关闭后锁释放；
- source、target、schema 与 index 的前后指纹相同，mutation statement 列表为空；
- 报告仅保留 ID、长度、hash、count、membership/target/plan digest 和 failure code，不输出原始 JSON、标签、凭据或生产身份信息。

实际 dry-run planner 固定为十一种 disposition：`MIGRATABLE`、`EMPTY_NOOP`、`TARGET_ALREADY_PRESENT`、`TARGET_CONFLICT`、`NORMALIZED_BANK_COLLISION`、`TARGET_INVALID`、`INVALID_KEY`、`INVALID_DATA`、`BANK_MISSING`、`ORPHAN_QUESTION`、`MEMBERSHIP_UNAVAILABLE`。它们分别聚合到 `ELIGIBLE`、`CONFLICT`、`INVALID`、`UNRESOLVED`；连接、事务、锁与清理失败单独进入 `GLOBAL_FAILURE`，不伪造为逐行 disposition。固定 mixed fixture 有 16 个 candidate，group count 为 `4/5/4/3/0`。

证据只来自本地 Testcontainers 固定夹具。没有连接生产数据库，没有读取生产凭据，没有读取或修改生产数据。

## 保持关闭的边界

以下状态必须保持 `false`：

- `migration_design_closed`；
- `operator_migration_implementation`；
- `production_schema_or_index`；
- `real_data_migration_execution`；
- `production_cutover`。

production apply 必须 fail closed，且 `production_apply_authorized=false`。planner 报告中的 clean-fixture eligibility 只是数据预检判断，不是生产授权。尚未闭合项包括：获批的 durable migration ledger/version/tombstone；source/target/membership write freeze 或共同 version/digest recheck；SQLSTATE `40001`/`40P01` 有界重试；逐项 disposition approval、备份与回滚、生产数据清洁度/规模和生产凭据。不得用 `user_progress` 特殊行、`question_id=0`、Redis 或本地文件伪造 durable marker。

## WORM 第六初始节点与第七 hardening 节点

本节点新增 parser、全局 dry-run 与脱敏 report 三个 `src/main` 类型，因此 Java build context 已改变。这三个类型没有 Spring component/runner/scheduler/HTTP 注册，也没有 apply statement 或 Operator 入口。旧实现 WORM 物理 tip `7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39` 只作为 immutable predecessor，没有复用为当前 build context 的权威。

固定链第六个初始物理节点保持不可变：

- 报告：`docs/refactor/phase4c/personal-bank-tag-global-preflight-worm-evidence.json`；
- 报告 SHA-256：`283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72`；
- Java build-context SHA-256：`2b2f2b9956a9188a81606b50405ac82ded0253bbe2539d6fb841575b4c21dcf9`；
- Dockerfile SHA-256：`bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499`；
- predecessor SHA-256：`7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39`；
- 当时固定节点数：`6`。

bounded payload 与 Unicode lossless 加固改变 parser 与 global-preflight main bytes 后，固定链只做 append，新增第七节点：

- 报告：`docs/refactor/phase4c/personal-bank-tag-global-preflight-hardening-worm-evidence.json`；
- 报告 SHA-256：`93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344`；
- Java build-context SHA-256：`a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17`；
- Dockerfile SHA-256：`bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499`；
- predecessor SHA-256：`283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72`；
- 当前固定节点数：`7`。

Node A builder 直接调用 Phase 2 的 `validate_fixed_chain`，先精确核对不可变第六节点，再核对七个物理 WORM、PostgreSQL 18.4、70/617、canonical schema、完整 read-role ACL、敏感信息边界以及第七 tip 的全部字段；静态聚合验收再惰性加载 Node A acceptance。固定合同声明 `initial_worm_successor_appended=true`、`current_build_context_changed=true`、`new_worm_successor_was_required=true`、`new_worm_successor_appended=true`、`new_build_context_worm_closed=true`，同时保持 `new_worm_successor_required=false`、`initial_worm_tip_reused_as_current=false`、`historical_worm_chain_overwritten=false`。

WORM 闭合只证明当前 Java build context 的本地验证，不授权 durable schema、Operator、真实 apply 或 production cutover。

## 执行顺序

1. 固定并验收本全局只读预检合同、第六初始 WORM 与第七 hardening WORM；本步骤已闭合。
2. 单独设计并授权 durable ledger/schema；未授权前 apply 必须失败关闭。
3. 实现 production Operator，默认仍为 dry-run，并补齐 freeze/recheck、bounded retry、逐项审批、备份和回滚证据。
4. 只有用户在当次任务中明确授权后，才可使用脱敏演练数据或生产流程执行 apply；Schema、真实数据与切流分别授权。

## README 交接小节

> **Phase 4C tag migration global preflight** — PostgreSQL 16.14/18.4 固定夹具的全局只读预检以及 bounded payload/Unicode lossless 加固证据已闭合；唯一新增 gate 仍为 `migration_global_preflight_evidence_closed=true`。第六初始 WORM 保持不可变，当前 Java build context 由第七 hardening WORM 闭合。Operator、durable ledger/schema、真实数据 apply 和 production cutover 仍关闭；路由保持 `13/598/0`。

本小节可在集成提交时复制到 Phase 4C README；历史 WORM 报告与前六个固定节点保持不可变。
