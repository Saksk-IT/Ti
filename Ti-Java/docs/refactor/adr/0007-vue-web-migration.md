# ADR-0007：Web 采用 Vue 3 渐进垂直迁移且不回退旧 Jinja

- 状态：已接受
- 日期：2026-07-16
- 决策阶段：阶段 1（架构决策与契约固化）
- 适用范围：`Ti-Java/web/`、Web 路由、客户端状态、SEO 决策和页面验收

## 上下文

旧 Web 有 309 个 HTML 模板、104 处 `render_template` 调用和大量原生 JavaScript；阶段 0 把 Web/小程序入口归并为 14 条关键旅程。一次性重做全部页面既难证明行为等价，也会把架构迁移与视觉重设计混在一起。另一方面，新项目最终必须脱离旧 Jinja 和 Flask，运行时把“尚未迁移”页面代理回旧系统会形成永久的双后端依赖。

当前盘点能证明公共题库、广场和论坛存在公开页面，但尚无搜索抓取、自然流量或服务端渲染的量化证据，不能仅凭页面公开就把整个 Web 改为 Nuxt/SSR。

## 决策

1. 在 `Ti-Java/web/` 创建独立 Vue 3 + TypeScript strict + Vite 应用，使用 Vue Router；生产产物是独立静态资源，不复制 Jinja 作为永久实现。
2. API 类型和调用只来自 ADR-0006 的 OpenAPI 生成客户端。生成层负责信封、错误、Request ID、CSRF 与兼容适配；页面不得再手写 endpoint 字符串和 response interface。
3. Pinia 只保存当前身份摘要、客户端权限/UI 偏好和跨页面 UI 状态。服务端资源使用查询缓存方案（初始采用 TanStack Vue Query）或组件局部请求状态；题库、帖子、考试结果等不得复制成长期 Pinia 事实源。
4. 迁移顺序固定为：应用壳/公共浏览 → 登录与账号 → 题库 → 练习 → 考试 → 学习数据 → 社区/消息 → 校园 → 编程/智能 → 后台。每批必须是“路由 + API + 权限 + 加载/空/错误态 + E2E”的完整垂直切片。
5. 新 Vue 路由只能调用 Java。未迁移页面在开发/测试环境显示带矩阵状态的明确阻断页，在生产验收中视为失败；不得 iframe、302、反向代理或深链回旧 Jinja。
6. 第一轮保持现有信息架构、视觉语言、桌面/移动关键布局与交互语义，不同时做全站品牌重设计。视觉升级另立需求与回归基线。
7. 当前采用 SPA/静态托管。若真实指标证明公开题库或论坛需要可索引首屏，再提交单独 ADR，按页面评估预渲染或 Nuxt；没有证据时不把登录、后台和全部应用改成 SSR。
8. Web 认证遵守 ADR-0005：安全 HttpOnly Cookie 保存 Session，SPA 按 Spring Security 规则获取/轮换 CSRF token；长期 Access Token 不进入 localStorage/sessionStorage/Pinia。
9. 可访问性至少满足语义结构、键盘操作、焦点管理、表单错误关联、颜色对比和 reduced-motion；迁移矩阵未覆盖这些状态时不能标记页面完成。

## 后果

正面后果：

- 页面可按真实旅程逐批完成并与旧行为对比，失败范围可控。
- Vue 与 Java 共享 OpenAPI 类型，服务端状态不会在多个客户端 store 中漂移。
- 新项目从第一批页面起就没有运行时旧 Jinja 回退，独立性可持续验证。

代价与风险：

- 迁移期间旧 Web 和新 Web 是两个独立制品，需要明确入口和测试环境，不能把半成品当生产替代品。
- 保持视觉等价会暂缓部分 UI 改善。
- SPA 对公开内容的 SEO 能力有限；若后续出现量化需求，需要追加预渲染/SSR 工作而不是提前建设。

## 拒绝的方案

- **一次性重做全部页面：** 无法按旅程定位兼容回归，且会把 UI 设计变化混入后端迁移。
- **运行时回退旧 Jinja/Flask：** 违反 Ti-Java 独立运行和整体切换要求。
- **复制旧 Jinja 到 Java 模板：** 只是移动旧实现，不能形成 Vue 类型安全客户端。
- **把所有 API 数据放 Pinia：** 容易产生缓存失效、并发更新和重复事实源。
- **现在把整站改 Nuxt/SSR：** 阶段 0 没有全站 SEO/SSR 证据，会增加认证和部署复杂度。
- **在 localStorage 保存长期 token：** 与目标安全模型冲突，XSS 后可直接窃取凭据。

## 实施与验证约束

阶段 6 每批页面至少运行：

```bash
cd Ti-Java/web
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm playwright test
```

门禁必须断言：

- TypeScript `strict` 开启且 `vue-tsc` 零错误；API 业务类型只从生成目录导入；
- 生成客户端与 OpenAPI 无漂移，兼容/新版信封按 `api-contract-conventions.md` 解析；
- 每条关键旅程覆盖桌面、移动、键盘、深链接、刷新、权限不足、登录过期、网络失败、加载、空状态和服务端校验错误；
- 构建产物和生产配置中没有旧 Flask host、Jinja URL、父目录路径或跨站 iframe；
- 未迁移路由在矩阵中保持 pending，不能因阻断页而标记完成；
- 视觉对比工件使用固定 viewport、字体和数据夹具，不把动态时间/随机内容当布局差异；
- 若引入预渲染/SSR，必须先有搜索/性能指标、缓存/认证边界和独立部署验证的新 ADR。

## 事实证据

- 旧模板、页面与旅程数量：[`../00-current-state.md`](../00-current-state.md) 第 2、9 节及 [`../09-surface-inventory.json`](../09-surface-inventory.json)。
- 目标 Web 与独立运行约束：[`../01-target-architecture.md`](../01-target-architecture.md) 第 3、8 节。
- API 约定：[`../phase1/api-contract-conventions.md`](../phase1/api-contract-conventions.md) 与 ADR-0006。
- Vue 官方 Vite/TypeScript/Vitest 工具建议：<https://vuejs.org/guide/scaling-up/tooling.html>
- Vue TypeScript：<https://vuejs.org/guide/typescript/overview.html>
