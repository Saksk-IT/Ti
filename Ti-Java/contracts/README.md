# OpenAPI 契约基线

`openapi.json` 是阶段 1 的确定性 OpenAPI 3.1.2 初稿。它只读取 `Ti-Java/` 内已经冻结的路由矩阵、脱敏黄金样本和结构化人工 override，不导入或执行旧 Flask 项目，也不读取父目录运行时文件。

当前基线表达 592 条 Flask URL rule、611 个展开后的遗留 method，以及 610 个标准 OpenAPI Operation。差额是 `GET /profile` 的 1 个后注册遮蔽 Endpoint：有效 Operation 和不可达来源均在 `x-ti-shadowed-operations` 中固定，因此覆盖关系恒为 `610 + 1 = 611`，没有静默丢失。

每个 Operation 都包含：

- `x-ti-legacy`：旧 Endpoint、源码、注册方式和契约来源；
- `x-ti-migration`：目标模块、迁移状态，以及由 `targetOperationId + targetMethod + targetPath` 唯一标识的 Java 兼容接口；
- `x-ti-auth-semantics` 与标准 `security`：冻结的全局门禁、路由装饰器和角色语义；
- `x-ti-contract-maturity`：`observed`、`tested`、`manual`、`inferred` 或 `unknown`；
- `x-ti-contract`：schema 置信度、证据和仍未知的契约面。

当前 7 个黄金操作标为 `observed`，其余 603 个只标为 `inferred`。`inferred` 不能用于迁移完成判定；未证明的响应使用 `LegacyOpaquePayload` 并保留显式 unknown 标记。`openapi-manual-overrides.json` 固定 `/profile` 遮蔽决议、7 个黄金样本映射和 4 个经源码审计的请求/参数契约，任何未匹配 override 都会使生成或验证失败。

目标 `/api/v1` 的共享 schema 与兼容 Operation 分离：成功信封是 `success/data/meta`，错误信封是 `success/error/meta`，分页位于 `meta.pagination`。兼容 Operation 统一声明 `x-ti-envelope: legacy`，不会被目标信封强行改写；下载、上传和 SSE 仍须后续人工契约测试，不能根据路径名称猜测。

安全 scheme 中 `legacySessionCookie`、`legacyBearerJwt`、`recordToken` 和 `legacyXRequestedWith` 用于现有兼容路径；`csrfHeader` 与 `accessToken` 只描述目标认证形态，当前 610 个兼容 Operation 均不得引用。

从 `Ti-Java/` 目录运行：

```bash
python3 tools/generate_phase1_openapi.py
python3 tools/validate_phase1_openapi.py
python3 -m unittest discover -s tools -p 'test_phase1_openapi.py'
```

生成器不写入时间戳，输入 SHA-256、规则/Operation 数、成熟度分布和 override 使用情况都写入产物；验证器用 Python 标准库重生成两次并与已提交文件逐字节比较。

`@redocly/cli 2.39.0 --extends=minimal` 额外确认规范结构有效；当前 48 条 warning 被 `x-ti-known-lint-findings` 确定性解释为 30 组遗留静态/动态模板歧义、4 个遗留尾斜杠路径和 14 个尚未被兼容 Operation 使用的预声明组件。验证器会从实际 `paths/components` 重新计算具体证据，不能通过改计数掩盖新增警告，也不会为了消除 lint 而擅自改旧路径。
