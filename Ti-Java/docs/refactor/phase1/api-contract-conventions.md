# HTTP API 契约约定

## 1. 状态与适用范围

- 状态：阶段 1 已接受，实现期间变更须同步 OpenAPI、ADR 和兼容测试。
- 适用范围：Java 兼容 Controller、新 `/api/v1` 契约、Vue 生成客户端与小程序适配。
- 基线来源：`02-route-parity-matrix.csv`、旧测试、页面/小程序调用、黄金样本与真实 Handler。
- 规范版本：OpenAPI `3.1.2`。用户目标限定 3.1 特性线，因此不升到 3.2；[OpenAPI 官方目录](https://spec.openapis.org/oas/) 说明同一 3.1 minor 的 schema 适用于其所有 patch 版本。

本文的“统一”指新版 API 和 Java 内部类型具有统一规则，不授权改变旧路径的响应形状。迁移矩阵未完成前，兼容 Controller 必须原样保留旧状态码、字段、空值、顺序和信封；不得为追求形式统一而破坏已发布客户端。

## 2. 契约权威与成熟度

单个操作的事实优先级为：

1. 可重复的运行时请求、数据库后置条件和现有测试；
2. 黄金样本和 Web/小程序实际消费行为；
3. Handler/schema/model 实现；
4. 路由矩阵与 OpenAPI 生成产物；
5. 仅用于说明意图的旧文档。

OpenAPI 中每个 operation 必须通过 `x-ti-contract-maturity` 标记契约成熟度，禁止把未知字段伪造成精确 schema：

| 值 | 含义 | 可以用于迁移完成判定 |
| --- | --- | --- |
| `observed` | 状态、内容类型和 schema 由真实请求/黄金样本及后置条件证明 | 是，但仍须权限/边界用例 |
| `tested` | 现有测试证明请求和响应 | 是，需确认测试覆盖边界 |
| `manual` | 因下载、SSE、动态表单等无法安全推导，用结构化 override 与手工契约测试固定 | 是，须有测试引用 |
| `inferred` | 仅从路由、认证或静态消费者推导 | 否 |
| `unknown` | 仍无足够证据 | 否 |

## 3. 路径、操作与版本

- 旧路径、HTTP method 与 Flask converter 语义原样保留；`<int:id>` 在 OpenAPI 中表达为必需 `integer/int64` path parameter。
- OpenAPI path template 中每个 `{name}` 都必须有 `required: true` 的 path parameter，符合[OpenAPI 3.1.2 Path Templating](https://spec.openapis.org/oas/v3.1.2.html#path-templating)。
- `operationId` 在整份描述中唯一且稳定，不以 Java 方法重命名随意改动。
- OpenAPI 无法在同一 path/method 表达两个 Handler。旧 `GET /profile` 必须把真正匹配的 Endpoint 作为 operation，把遮蔽 Endpoint 放入 `x-ti-shadowed-operations`；两个来源都计入覆盖门禁。
- 新 API 可使用 `/api/v1`，但不代替兼容路径；删除旧路径必须先完成 Web/小程序迁移、发布窗口和废弃 ADR。

## 4. 响应信封

### 4.1 兼容路径

兼容路径的信封以每个 operation 已观测行为为准。它可能是原始数组、HTML、二进制文件或 `{success, data, message}` 的某种组合。OpenAPI 必须通过 `x-ti-envelope: legacy` 及具体响应 schema/content type 记录，未观测时使用 `LegacyOpaquePayload` 并标为 `inferred`，不得冒充统一形状。

### 4.2 新 `/api/v1` 成功信封

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "01J..."
  }
}
```

- `success` 恒为 `true`。
- `data` 是 operation 的显式 schema；无返回数据的成功命令使用 HTTP 204 且无 body，不返回伪造的空对象。
- `meta` 只放通用元数据；分页位于 `meta.pagination`。
- `X-Request-ID` 响应头是跨层关联的权威值，body 中的 `meta.request_id` 如存在必须与其一致。

### 4.3 新 `/api/v1` 错误信封

```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "资源不存在",
    "details": []
  },
  "meta": {
    "request_id": "01J..."
  }
}
```

- `error.code` 是稳定、大写下划线的机器码；展示文案可变，客户端不得用 `message` 分支。
- `details` 是脱敏的结构化校验信息，可缺省；不包含堆栈、SQL、密钥、Cookie、上游原始响应或完整敏感提示词。
- 同一业务原因在所有新版 operation 使用同一 `code`；兼容路径仍保留旧 code/body。

## 5. HTTP 状态与错误码

| 状态 | 新版语义 | 典型错误码 |
| --- | --- | --- |
| 400 | 语法、类型或必需参数错误 | `INVALID_REQUEST` |
| 401 | 未登录、令牌过期/无效 | `AUTHENTICATION_REQUIRED`、`TOKEN_EXPIRED` |
| 403 | 已识别身份但无权，或 CSRF 失败 | `FORBIDDEN`、`CSRF_INVALID` |
| 404 | 资源不存在或按授权策略隐藏 | `RESOURCE_NOT_FOUND` |
| 409 | 版本/唯一性/幂等键冲突 | `CONFLICT`、`IDEMPOTENCY_CONFLICT` |
| 422 | 请求形状正确但违反业务规则 | `BUSINESS_RULE_VIOLATION` |
| 429 | 限流 | `RATE_LIMITED`，保留 `Retry-After` |
| 500 | 未分类内部错误 | `INTERNAL_ERROR` |
| 502/503/504 | 上游失败、暂时不可用或超时 | `UPSTREAM_FAILURE`、`SERVICE_UNAVAILABLE`、`UPSTREAM_TIMEOUT` |

表中是新版默认，不覆盖兼容 operation 的已观测状态。例如旧小程序忘记密码写请求当前被全局门禁拒绝为 403，在产品语义被 ADR 批准修正前必须如实记录。

## 6. 分页、排序与过滤

- 新版页码从 1 开始：`page >= 1`，`page_size` 默认 20、最大 100；更大上限必须由 operation 明确证明。
- 兼容路径保留 `per_page`、`limit/offset`、cursor 或无信封列表等现有语义。
- 新版分页元数据固定为 `page`、`page_size`、`total_items`、`total_pages`、`has_next`、`has_previous`。空结果也返回完整元数据。
- 每个列表 operation 必须定义稳定的默认排序及唯一 tie-breaker，通常是业务字段后再按 ID；禁止依赖数据库未指定顺序。
- 未提供过滤值与显式空字符串不默认等价；具体 operation 必须按旧行为固定。

## 7. 时间与时区

- 新版时间点使用 RFC 3339 `date-time`，对外默认 UTC `Z`；Java 使用 `Instant`/`OffsetDateTime`。
- 只表示日期的值使用 `YYYY-MM-DD` 与 `LocalDate`；不伪造时区。
- 课表节次、学期和校园日期的解释时区是 `Asia/Shanghai`；原始上游字符串与规范化时间分字段保存。
- 兼容路径保留旧时间字符串、精度和空值；对比器只归一化已明确列为非契约的运行时值。

## 8. 金额、分数与数值精度

- Java 业务计算禁止使用 `float`/`double` 表达金额或需精确对比的分数，使用 `BigDecimal`。
- 新版金额使用十进制字符串（例如 `"12.30"`）并显式携币种；禁止由 JavaScript 二进制浮点推测金额。若上游使用最小币种单位，对应 operation 可改用带单位后缀的整数字段。
- 考试单题分值的旧 UI 允许 `0.5` 步长，旧库为 float；迁移前须用固定数据证明单题、总分、平均分和正确率的 scale/舍入。未证明前不得自行选定全局舍入模式。
- 每个数值字段在 OpenAPI 中必须有单位、范围、scale 和舍入证据，或显式标记 `x-ti-precision-status: unknown`。
- 兼容路径保留旧 JSON number/string 形状，即使 Java 内部已改用 `BigDecimal`。

## 9. 空值、缺失字段和枚举

- OpenAPI 3.1 用 JSON Schema 联合类型表达可空，例如 `"type": ["string", "null"]`；`required` 与可空是两个独立维度。
- “字段缺失”、`null`、空字符串、空数组和 0 不得互换；兼容 operation 按样本/测试分别固定。
- 新版可选列表默认使用空数组而非 `null`，但只在新版 schema 适用；不回填旧字段。
- 枚举 wire value 是稳定小写字符串。新增值是兼容性变更而非当然安全，生成客户端必须有未知值防护；不得把未知值静默映射为某个现有业务值。

## 10. 认证、CSRF 与授权

OpenAPI 定义下列 security schemes，operation 按 `auth_semantics` 选择，不根据 URL 名称猜测：

| scheme | 用途 |
| --- | --- |
| `legacySessionCookie` | 兼容 Web/Session 和过渡期安全 Cookie |
| `legacyBearerJwt` | 现有小程序 JWT/Authorization |
| `recordToken` | 仅记录类特定兼容接口 |
| `legacyXRequestedWith` | 旧 Cookie 写请求实际使用的 `X-Requested-With: XMLHttpRequest` 门禁；它必须与 Session 同时满足，本身不是身份认证 |
| `csrfHeader` | Cookie 写请求的 CSRF Header，与 Session 同时满足 |
| `accessToken` | 最终小程序短期 Access Token |

`legacySessionCookie`、`legacyBearerJwt`、`recordToken` 和 `legacyXRequestedWith` 用于描述当前兼容 operation；`csrfHeader` 与 `accessToken` 是目标 `/api/v1` 方案，阶段 1 可在 components 中预声明，但 610 个旧兼容 operation 不得引用。旧 `X-Requested-With` 门禁不是目标 CSRF 设计，也不得被文档包装成等价安全保证。

- OpenAPI `security` 数组的多个对象表示“或”，同一对象内多 scheme 表示“且”；匿名可用 operation 明确使用空数组。
- `route_auth:none` 只表示没有路由装饰器，不表示匿名；生成器必须保留全局门禁、Admin hook、CSRF 和内联证据。
- 新 Web 的 Cookie 使用 `HttpOnly`/`Secure`/`SameSite`；SPA 写请求使用可轮换 CSRF token Header。[Spring Security SPA CSRF 文档](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html#csrf-integration-javascript-spa) 明确指出 SPA 的 BREACH 保护与延迟 token 需要专门配置。
- 登录和登出也是 CSRF 保护的写操作；禁止通过 GET 登出。兼容期若旧路径不同，必须用 ADR 和客户端迁移计划收口。

## 11. 幂等、并发与重试

- 考试交卷、答案写入、支付回调、教务刷新、导入导出与外部通知等必须定义稳定幂等键。
- 新版通用 Header 为 `Idempotency-Key`；相同身份 + operation + key + 请求摘要重放返回同一业务结果。
- 相同 key 但不同请求摘要返回 409 `IDEMPOTENCY_CONFLICT`，不执行业务写入。
- 幂等记录和业务事实在同一本地事务提交；超时后客户端可用同一 key 安全重试。
- 乐观锁/版本冲突返回 409，响应不泄漏当前数据中的敏感字段。

## 12. 下载、上传与 SSE

- 文件下载必须在 OpenAPI 中指定真实 media type、`Content-Disposition` 与 binary schema；不使用 JSON 信封包装文件流。
- 上传使用 `multipart/form-data`，显式限制大小、类型、文件数、扩展名与内容校验；临时文件在成功/失败路径都清理。
- SSE 使用 `text/event-stream`，每个事件定义 `event`、`id`、`data` schema、重连与心跳语义；断线不能改变 PostgreSQL 中的最终事实。
- 这三类接口默认标记 `manual`，必须关联手工契约测试，不由路由名自动猜测。

## 13. 兼容性分类与变更流程

| 变更 | 默认分类 |
| --- | --- |
| 改路径/method/status/Content-Type/字段类型/空值/排序 | 破坏性 |
| 删字段、字段由可空改必需、收紧枚举或范围 | 破坏性 |
| 在客户端宽松解析已证明的对象中增加可选字段 | 需生成客户端回归，不自动判定安全 |
| 新增枚举值 | 对闭合生成客户端可能破坏 |
| 只改文案且客户端不依赖 | 非破坏性，仍需错误码不变 |

流程：先更新证据/黄金样本和 ADR，再更新 manual overrides/OpenAPI，重生成 TypeScript 客户端并运行契约/E2E，最后更新路由矩阵。任一兼容差异没有已接受 ADR 和客户端证据时，矩阵不得标记完成。

## 14. 阶段门禁

1. OpenAPI JSON 可确定性重生成，且通过 3.1 schema/结构校验。
2. 592 条旧 URL rule、611 个展开 method 均有契约表达；遮蔽/冲突不静默丢失。
3. 每个 operation 有唯一 `operationId`、目标模块、旧 Endpoint/来源、认证语义、迁移状态和契约成熟度。
4. 所有 path template 参数均有必需 schema；安全 scheme 引用都已定义。
5. `manual` 操作都有结构化 override 和契约测试；`inferred/unknown` 不能用于迁移完成判定。
6. 新增共享 schema 不能改变兼容路径的旧信封。
7. 契约产物、生成脚本、manual overrides 和测试不读取真实 Secret，也不包含机器绝对路径。
