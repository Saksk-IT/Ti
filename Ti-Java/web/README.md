# Ti Java Web foundation

本目录是 Phase 6 Web 的独立 Vue 3/Vite 基础。当前范围只包含已迁移公共题库读取能力，不声明生产切流，也不改变生产 API 地址。

## 当前页面范围

- `/public/banks`：沿用旧 SAK 应用壳和论坛式题库广场；支持板块、关键词、最新/热门/活跃/精华排序与追加加载。
- `/public/banks/card/{system|user}/{bankId}`：沿用旧题库名片布局，仅提供只读详情。
- 加入、练习、个人题库、用户统计和全部写入操作均进入 Vue Router 内的显式阻断页；不会回退到旧模板页面。

页面保留旧应用的 200/64px 侧栏、56px 顶栏、移动双抽屉、浅色/深色模式，以及默认、薄雾、沙丘、松林、青瓷五种风格。偏好继续使用 `theme`、`app_theme_style_v1`、`sidebar_collapsed` 三个 localStorage 键，并在 Vue 挂载前恢复，避免主题闪烁。

## API 与状态边界

生成客户端按来源物理隔离：

- `phase3Authentication`
- `phase4aSubjectDirectory`
- `phase4aPublicBank`

运行时公共题库只允许以下五个 Phase 4A GET：

- `legacy_b7e49e77a026_get`：列表
- `legacy_db1ac691d6fb_get`：板块
- `legacy_a473896ff467_get`：热门
- `legacy_f3644c1474f3_get`：统计
- `legacy_8cfb837021af_get`：名片详情

边界脚本固定源文件 SHA-256、完整 operation 集、`migrated`、`productionCutover=false`、GET 只读属性和 facade 唯一 SDK 入口。页面不会使用响应中的 `detail_url` 或 `practice_url`，而是按已验证的 `source_type + id` 构造旧 IA 形状的 Vue 路由。

TanStack Query 负责全部服务端状态、取消信号、12 秒读取超时和可重试错误；Pinia 只保存认证反射和 UI 偏好。所有客户端使用同源相对 `/api/**`、`credentials: same-origin` 和 `X-Request-ID`。生产构建不写入后端地址；开发模式可用 `TI_JAVA_DEV_ORIGIN` 覆盖本地代理目标。

## 开发与验证

```bash
npm ci
npm run dev            # 代理到现有本地后端，默认 127.0.0.1:18080
npm run dev:mock       # 使用只读公共题库浏览器夹具
npm run generate:api
npm run generate:api:check
npm run lint
npm run typecheck
npm run test:unit
npm run test:e2e
npm run build
```

Playwright smoke 覆盖桌面列表、筛选、追加加载、详情禁用操作、主题持久化、错误 Request ID、三个侧栏切片错误态，以及移动端应用导航/题库筛选双抽屉。
