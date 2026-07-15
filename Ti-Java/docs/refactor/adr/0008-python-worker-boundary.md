# ADR-0008：默认不创建 Python 服务，仅为证据充分的隔离任务保留边界

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：`Ti-Java/services/`、后台任务、模型调用、导入导出和代码执行

## 上下文

旧系统使用 Python Flask 和 RQ，`saksk` 队列承载 AI 解析、邮件和短信，`default` 队列还存在无人消费的聊天音频转码风险。它们是“当前由 Python 执行”的事实，但不等于“只能由 Python 可靠实现”。阶段 0 记录的普通 OpenAI 兼容 API、SMTP、短信、微信、教务、支付和对象存储都是 HTTP/SDK 集成，没有证明必须保留 Python 数据生态。

目标契约只允许在 Pandas/NumPy/文档解析等 Python 专属流水线、需单独 CPU/内存隔离的执行/推理/大型导入导出，或 Java 无法以同等可靠性和维护成本实现时保留 Python Worker。

## 决策

阶段 2 不创建 `services/ai-worker/`，现有 AI 对话/解析、邮件、短信、微信、教务、支付、对象存储和备份能力默认由拥有模块的 Java 端口与同制品 Worker 实现。名称中含有 `AI`、`task`、`worker` 或旧代码使用 RQ，都不是保留 Python 的理由。

以下现有工作负载当前均**未获批**成为 Python 服务：

- OpenAI-compatible `/models`、`/chat/completions`、`/responses` 和流式响应；
- 邮件、阿里云短信、微信及教务 HTTP 调用；
- AI explain 的排队/缓存逻辑；
- 聊天音频转码（可用受限 Java Worker 调用经过允许的媒体工具）；
- 普通 CSV/Excel/PDF 导入导出和备份编排；
- 编程题判题（需要沙箱隔离，但沙箱技术选择与 Python 语言不是同一决定）。

只有候选任务同时提交以下证据并新增/修订 ADR 后，才可创建 Python Worker：

1. 真实脱敏夹具、输入规模和旧实现基准；
2. Python 专属依赖或资源隔离的不可替代原因；
3. Java 方案的可复现失败/成本比较，而不是团队偏好；
4. CPU、内存、时限、并发、临时磁盘和网络出站上限；
5. 带版本的输入/输出 Schema、稳定任务 ID/幂等键、取消和超时语义；
6. 进程崩溃、重复投递和结果回放的恢复测试；
7. 镜像、依赖锁、SBOM、安全扫描和独立目录构建证据。

若获批，Python Worker 是窄任务适配器而不是第二业务后端：

- 调用方模块在 PostgreSQL 中拥有命令、业务状态和幂等事实；Worker 不直接修改其他模块表，也不共享 Java JPA 事务。
- Worker 只接收最小、版本化、脱敏任务载荷，通过受控对象引用读取大文件；不接收数据库超级用户或 Web Session/JWT。
- 输出是带任务 ID、Schema 版本、内容摘要和安全错误码的结果命令；Java 所有者在本地事务校验并提交业务结果。
- Worker 不导入根目录 `app/`、不启动 Flask、不读取父目录、不调用旧运行时，不成为同步 HTTP 请求的必需在线链路。
- Python 依赖和解释器精确锁定，容器以非 root、只读文件系统、临时目录配额、网络 allowlist 和资源限制运行。

## 后果

正面后果：

- 避免因为历史语言选择继续维护第二套通用业务运行时。
- 普通外部 HTTP 和事务状态留在 Java 模块内，认证、日志和幂等模型一致。
- 真正需要 Python 时已有明确、可审查的隔离接口，不会侵蚀模块所有权。

代价与风险：

- 某些文档/数据任务可能在后期证明 Java 成本过高，需要追加一个受控部署单元。
- 原 RQ 任务不能原样复制，必须先建立可靠命令和存量任务处置。
- 媒体/代码执行仍可能需要原生工具或沙箱，不能因此在 Java API 进程中无隔离运行。

## 拒绝的方案

- **保留整个 Flask/RQ 作为“AI 服务”：** 新 Java 会继续依赖旧运行时代码与数据边界，违反独立化目标。
- **所有异步任务都用 Python：** 异步语义不等于语言边界，会产生第二套认证、配置和可观测性。
- **Java 在请求线程直接执行 Python 脚本：** 不可恢复、难限权，且创建父目录/本机环境依赖。
- **Python Worker 直接写多个业务模块表：** 绕过公开应用 API和单写者事务所有权。
- **仅因 Pandas 更熟悉就拆服务：** 缺少可复现的依赖/成本证据。

## 实施与验证约束

在 Python Worker 尚未获批时，门禁应确认生产 Compose、Java 配置和关键旅程不要求 Python/Flask 容器。每个旧 RQ 任务必须在迁移矩阵中映射到 Java 后台命令、明确取消，或关联新的 Python ADR，未知项为零。

获批后的专属门禁至少包括：

- 同一任务并发/重复投递只产生一个业务结果，Worker 崩溃后可从 PostgreSQL 命令状态恢复；
- 超时、取消、OOM、坏文件、恶意压缩包、路径穿越和外部服务失败不会造成部分业务写入；
- Java 与 Python 的契约测试使用固定 JSON Schema/Protobuf 版本及黄金向量；
- Secret/用户凭据/完整敏感提示词不进入任务载荷、日志和死信；
- 资源/网络策略在容器测试中实际拒绝越界；
- 从只含 `Ti-Java/` 的目录能构建 Worker，源码中不存在 `../app`、父目录挂载或 Flask import。

## 事实证据

- 旧 RQ、队列和外部资源：[`../00-current-state.md`](../00-current-state.md) 第 4 节及 [`../03-data-ownership.csv`](../03-data-ownership.csv)。
- 目标 Python 证据门槛：[`../01-target-architecture.md`](../01-target-architecture.md) 第 9 节。
- 单写者与任务切换：[`../04-migration-runbook.md`](../04-migration-runbook.md) 第 5～8 节。
