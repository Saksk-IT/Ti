# 2026-09-20 main 同步与验收记录

本节点整合本机 Java 重构验收工作与远程旧业务更新，保留双方提交历史。代码同步不代表 Phase 4C 全量验收完成；权威路由状态仍为 **13 migrated / 598 pending / 0 production cutover**。

## 固定输入与整合方式

- 本机端点：`e17427515802ae22cde25475058d04cc510e0921`。
- 远程端点：`374bf3039d2f045f3e59a620a2c28e6f336ed4d8`。
- 共同祖先：`6ed81347467a4155887300b7e4ae36589204af79`。
- 使用普通 merge，未重写双方历史、未强制推送、未创建新分支。
- 合并前已创建并验证包含双方完整历史的仓库外 Git bundle。
- 两端服务器迁移文档补丁等价，文档保留一份内容。

唯一文本冲突位于 `Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.java`。解决时保留远程 full-parity anchor 与本机 source successor 两套承接能力。

新增 `learning-transaction-write-http-integration-successor-contract.json`，固定 28 个变化路径、57 个去重后的历史版本，以及各路径当前 SHA-256 和字节数。前驱版本逐项回放固定 Git blob 验证；普通 Python/Java 验收与独立夹具不依赖 Git 或父仓库。未知路径、未知前驱、变化后的当前字节、合同篡改及符号链接仍拒绝。

新合同通过追加方式承接远程进度文档变化及本机控制源码变化，历史 JSON、bootstrap snapshot、WORM 和 route delta 未覆盖。两端既有 JSON/CSV 共 293 次逐项比较均保持相同字节。Java 生产源码、Web 与 Java 小程序目录相对两端保持一致。

本节点新增的承接校验器仍明确自排除，不声明自身外锚完成，不授予路由晋级、生产 schema 执行或切流权限。

## 验证结果

| 范围 | 结果 |
| --- | --- |
| full-parity、source successor、anchor 与 integration 的 Python 定向检查 | 29/29 通过 |
| 同一组 Java 合同与 integration 定向测试 | 17/17 通过，包含在当前树完整 Surefire 执行中 |
| 旧小程序校园内容与课表运行时测试 | 24/24 通过 |
| Flask 教务与本地演示数据初始化回归 | 52/52 通过；使用仓库外独立测试数据库 |
| 扩展 Python 历史合同链 | 97/100 通过；3 个失败在合并前固定提交独立副本中全部复现 |
| 当前树 Maven `clean verify` | Surefire 执行 1,032 项，996 通过、36 失败、0 error、0 skipped；在该阶段停止，未进入 Failsafe |
| 合并前独立副本 Maven `clean verify` | Surefire 执行 1,023 项，987 通过、36 失败、0 error、0 skipped；与当前树的失败测试标识集合完全相同 |
| 历史证据与新合同端点 | 293 次历史 JSON/CSV 字节比较、28 个当前路径及 57 个前驱 blob 全部通过 |
| Git 差异检查 | 无未解决冲突或空白错误 |

定向 Java 首轮的一个负向测试已按组合后的校验顺序更新精确错误消息：被篡改的进度文档在 anchor 层即被拒绝；仍要求抛出 `AssertionError`，没有放宽为接受篡改内容。

扩展 Python 的 3 个既有失败为：

1. `Phase4cPersonalBankUserCountsCompositionContractTest.test_06_personalbank_never_reads_learning_relations`：历史无 migration 断言与已存在的事务幂等 migration 不一致。
2. `Phase4cTargetExecutionCheckedInContractTest.test_01_checked_in_contract_is_accepted_and_byte_deterministic`：历史目标执行合同与后继源码构建结果仍有字节差异。
3. `Phase4cTargetExecutionFixedRootsTest.test_05_physical_runtime_routes_ownership_and_worm_close`：仍将第九 WORM 的摘要与实际第十 WORM 比较。

Java 当前 36 个失败测试均在合并前本机固定提交的独立副本中复现。遗留问题主要涉及旧合同的源码/方法数量承接、Phase 6 及 typed-normalization 的独立夹具、catalog 应用边界中的中文显示字符串，以及旧负向断言。按失败测试标识比对，本次整合没有增加失败测试。本节点保留这些真实失败，不以跳过测试或修改历史合同冒充全量通过。

独立副本的文件权限按 Git 固定模式规范化为 `0644/0755`，避免 tar 解包附加组写入位造成无关的 runner mode 失败。

## 复现入口

在 `Ti-Java/` 下运行本次定向 Python 检查：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tools.test_phase4c_learning_transaction_write_http_full_parity_contract \
  tools.test_phase4c_learning_transaction_write_http_source_successor_contract \
  tools.test_phase4c_learning_transaction_write_http_full_parity_anchor_contract \
  tools.test_phase4c_learning_transaction_write_http_integration_successor
```

取得仓库外 `heavy-verify.lock` 后串行执行 Java 验证：

```sh
./infra/phase2/verify-in-maven-container.sh clean verify
```

本次使用项目固定的 Maven 3.9.16 / JDK 25 容器，Java 验证之间未并发。完整构建仍需后续重构工作修复上述遗留阻断；本记录不作为九条事务写路由晋级或生产切流依据。
