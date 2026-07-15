# ADR-0006：以 OpenAPI 3.1.2 固化兼容契约与新 API 规范

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：Java HTTP API、Vue 客户端、小程序兼容接口和契约测试

## 上下文

阶段 0 运行时盘点得到 611 个 `path + method` 组合，且旧请求经过全局 CSRF/匿名门禁、Admin 钩子、路由装饰器和 Handler 内联检查。响应中还存在页面、JSON、下载、SSE、重定向与历史错误差异。仅从 Flask 函数签名生成 Schema 会遗漏这些真实行为；对所有旧响应强行包一层“统一信封”又会破坏现有 Web 和小程序。

目标 Web 必须从 OpenAPI 生成唯一的 TypeScript API 类型，阶段 1 同时要求明确统一信封、错误码、分页、时间、精度、空值和枚举策略。因此必须把“兼容接口保持旧行为”与“新 `/api/v1` 使用统一规范”明确分层。

## 决策

### 契约权威与覆盖

1. OpenAPI 文档使用稳定的 OAS `3.1.2`。仓库内审查过的 OpenAPI 文件是 HTTP Schema 与 Vue 生成客户端的唯一类型来源。
2. `02-route-parity-matrix.csv` 是覆盖索引，不是单独的行为真相。每个 API operation 必须关联稳定 `route_id`、旧 endpoint、目标模块、认证/CSRF、契约来源和迁移状态。
3. 契约来源按强度组合：运行时 URL map、现有测试、脱敏黄金请求/响应、客户端调用、模型约束和 Handler 实现。无法从事实推导的字段先写手工契约测试，不能猜默认值。
4. HTML 页面、静态资源、重定向、下载、multipart 和 SSE 即使不使用 JSON 信封，也必须进入路由覆盖/媒体类型契约；不能因 OpenAPI 工具不便而静默漏掉。
5. Security Scheme 使用阶段 1 约定的 `legacySessionCookie`、`legacyBearerJwt`、`recordToken`、`legacyXRequestedWith`、`csrfHeader` 与 `accessToken`。`legacyXRequestedWith` 记录旧 Cookie 写路由真实的 `X-Requested-With` 兼容门禁；`csrfHeader` 与 `accessToken` 只属于目标认证，610 个 legacy operations 不得引用它们来改写旧行为。

### 兼容接口

现有路径在矩阵标记完成前，逐 operation 保持旧 HTTP 方法、状态码、Content-Type、Header、响应形状、分页、字段缺失与 `null`、枚举、认证和错误语义。Java 内部兼容 Controller 直接实现，不代理 Flask。

兼容路径不得为了“统一”批量改信封。已知旧异常（例如两个匿名找回密码接口被门禁为 403）先作为 `legacy-baseline` 保存；修复必须是有关联 ADR、客户端影响和回退方案的 `approved-difference`。

### 新 `/api/v1` 规范

JSON 成功信封固定为：

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "01..."
  }
}
```

错误信封固定为：

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "资源不存在",
    "details": []
  },
  "meta": {
    "request_id": "01..."
  }
}
```

- `success` 是布尔常量。无返回数据的成功命令使用 HTTP 204 且无 body，不返回伪造空对象。
- `error.code` 是稳定的大写下划线机器码；`error.message` 可本地化且不能被客户端用于分支。`error.details` 只含字段级安全摘要，不返回堆栈、SQL 或上游凭据。
- `X-Request-ID` 响应头是跨层关联权威值；body 中 `meta.request_id` 如存在必须与其一致。
- 分页列表本身位于 `data`，通用分页元数据固定在 `meta.pagination`：`page`（从 1 开始）、`page_size`、`total_items`、`total_pages`、`has_next`、`has_previous`；排序规则与最大页大小在 operation 中显式声明。游标接口若以后出现，使用独立 Schema，不伪装为页码分页。
- 时间点用 UTC RFC 3339 字符串并带 `Z`；纯日期用 `YYYY-MM-DD`；学期/周次等业务值使用领域 Schema，不能假装时间点。服务内部注入 `Clock`，禁止在序列化时偷偷使用本机时区。
- 金额内部使用 `BigDecimal`，v1 以带币种和固定 scale 的十进制字符串表达，禁止 binary float。分数计算也使用 `BigDecimal` 和 operation 明示的 scale/舍入规则；兼容路径保持旧 JSON 类型，新 v1 的 Schema 明示字符串或有界数值，不能由生成器自行转 double。
- 可选字段未提供时缺失；“字段存在但当前无值”才为 `null`。每个 Schema 用 `required` 与 `type: [T, "null"]` 明确区分，不用 Java 默认序列化行为决定。
- 枚举使用稳定字符串值并在 Schema 封闭列举。未知数据库值是契约错误并记录指标，不能静默映射成第一个枚举；只有明确设计 `UNKNOWN` 时才接受它。
- 下载、图片、multipart、重定向和 `text/event-stream` 使用各自媒体类型，不套 JSON 信封。错误仍按 operation 声明的 JSON/重定向兼容行为返回。

### 生成与变更

Vue 只能导入由固定生成器版本从审查后 OpenAPI 生成的客户端；禁止手写第二套 DTO。小程序在兼容路径迁移期间可以保留现有类型，但新 v1 接口必须逐步使用同一 Schema 生成/派生类型。OpenAPI diff 将删除 operation、收紧输入、修改状态码/字段类型/枚举视为破坏性变更并阻断构建。

## 后果

正面后果：

- 旧客户端不会因为“统一改造”在迁移中途失效，新客户端又有一致的类型与错误处理。
- 每个 operation 都能追溯到矩阵和行为证据，生成代码变化可审查。
- 时间、十进制和 null 不再由语言默认值偶然决定。

代价与风险：

- 兼容 Controller 需要维护历史上不一致的信封，直到对应客户端完成迁移。
- OAS 无法自动表达所有业务不变量，仍需手工契约和数据库终态测试。
- 精确十进制字符串会要求 Vue 在展示/计算时使用明确的解析策略。

## 拒绝的方案

- **只从 Controller 注解实时生成 OpenAPI：** 会把实现缺陷当成契约，也无法证明旧客户端行为来源。
- **所有旧路径立即套统一信封：** 破坏 Web/小程序字段和错误分支。
- **TypeScript 手写 DTO：** 会与 Java/OpenAPI 漂移，违反唯一类型源。
- **金额/分数统一用 `double`：** 无法保证评分和支付精度。
- **忽略“缺失”和 `null` 差异：** 旧客户端可能对二者有不同分支。
- **只记录 2xx Schema：** 鉴权、校验、限流、下载和错误状态同样是公开契约。

## 实施与验证约束

阶段 1/2 起门禁必须包括：

- 路由矩阵中的每条 API 记录恰好映射到一个 OpenAPI operation 或带原因的非 API 媒体契约，未知/遗漏数为零；
- legacy operation 的 security scheme 与真实门禁一致，且对 `csrfHeader`/`accessToken` 的引用数为零；
- OpenAPI 3.1.2 Schema 校验、引用解析、operationId 唯一性和无循环资源耗尽风险通过；
- 生成客户端后工作树无未提交漂移，Web 业务源码不声明重复的 API response interface；
- 黄金样本对状态码、Header、字段类型、顺序、分页、null 和错误逐字段比较；
- 使用属性/边界测试覆盖 page=1、空页、最大页、时区边界、Decimal 舍入、未知枚举和 validation details 脱敏；
- OpenAPI breaking-change 检查阻止删除/改类型/收紧枚举，批准差异必须关联 ADR；
- `request_id` 从入口贯穿 Java、Worker 和外部调用，客户端错误页可显示但日志不泄漏请求体 Secret。

## 事实证据

- 路由、认证顺序与客户端覆盖：[`../00-current-state.md`](../00-current-state.md) 第 3 节和 [`../02-route-parity-matrix.csv`](../02-route-parity-matrix.csv)。
- 脱敏样本：[`../golden-samples/manifest.json`](../golden-samples/manifest.json) 与 [`../08-golden-samples.md`](../08-golden-samples.md)。
- 阶段 1 统一约定：[`../phase1/api-contract-conventions.md`](../phase1/api-contract-conventions.md)。
- 只读/写比较要求：[`../04-migration-runbook.md`](../04-migration-runbook.md) 第 4、5 节。
- OpenAPI 3.1.2 规范：<https://spec.openapis.org/oas/v3.1.2.html>
