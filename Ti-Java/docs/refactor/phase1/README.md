# 阶段 1：架构决策与契约固化

## 状态

阶段 1 已完成设计与机器门禁，尚未迁移任何旧路由、数据写所有权或生产流量。下一阶段应按已接受 ADR 创建 Java 基础骨架，不得把本目录中的目标合同解释为已经实现的运行能力。

## 权威产物

| 产物 | 作用 | 当前证据 |
| --- | --- | --- |
| `../adr/0001`～`0010` | 版本、架构、MVC、数据库、认证、API、Vue、Python、可靠事件和 DAG 决策 | 10/10 已接受，结构与相对链接通过聚合门禁 |
| `../../contracts/openapi.json` | 旧 HTTP 行为的 OpenAPI 3.1.2 初稿及目标共享 schema | 592 条规则、611 个旧方法；610 个目标 operation + 1 个显式遮蔽来源 |
| `../../contracts/openapi-manual-overrides.json` | 路由冲突、黄金样本 pin 和源码审计 override | 未匹配、重复或未使用的 override 会失败 |
| `api-contract-conventions.md` | 信封、错误、分页、时间、精度、空值、枚举、安全和幂等约定 | 与 ADR-0006 和 OpenAPI components 交叉校验 |
| `module-contracts.json` | 模块公开 API、内部包、资源所有权和允许依赖 | 11 个业务模块 + Web；70 张表和 84 类非表资源唯一归属；DAG 无环 |
| `business-invariants.json` | 账号锁定、题库权限、答题幂等、单次交卷、评分和教务快照规则 | 6/6 必需不变量具备事务、并发、失败和验证场景 |
| `comparison-cutover-protocol.md` | 只读对比、隔离写对比、停写、整体切换及写前/写后回滚 | 禁止双写、逐路由/比例拆流和 shadow write；写后优先保留新写入 |

## 契约成熟度与已知限制

- 7 个黄金样本 operation 为 `observed`；其余 603 个为 `inferred`。`inferred` 只证明来源、目标接口、路径、方法和安全证据已闭环，不能据此把对应路由标记为迁移完成。
- `GET /profile` 的第二个 Flask Handler 被注册顺序遮蔽，OpenAPI 保留真实生效 operation，并在结构化 shadow 记录中保存另一个来源。
- Redocly CLI 2.39.0 minimal lint 判定规范有效、0 error；48 个 warning 已在 `x-ti-known-lint-findings` 中逐项解释：30 个旧静态/动态路径潜在歧义、4 个必须保留的尾斜杠路径、14 个阶段 1 预声明但尚未被旧 operation 使用的目标 components。不得为了消除提示而修改旧路径。
- 金额和分数在目标 API 使用精确十进制；旧兼容字段的 scale、舍入和 JSON number/string 形状仍须逐 operation 取证，未知时禁止切换写流量。
- 本阶段没有创建 Java Server、Flyway baseline、生产切换脚本，也没有连接生产环境。

## 可重复门禁

从仓库根目录运行：

```bash
python3 Ti-Java/tools/generate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_boundaries.py
python3 Ti-Java/tools/validate_phase1.py
```

`validate_phase1.py` 会串联 10 份 ADR、文档交叉引用、可移植性/敏感信息扫描、OpenAPI 确定性重生成、611 项覆盖、154 项所有权、DAG、不变量、切换协议和全部负向单元测试。
