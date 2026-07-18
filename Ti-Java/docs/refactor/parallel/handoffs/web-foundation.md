# Web Foundation Lane Handoff

## 身份与固定集成输入

- lane：`web-foundation`
- Worker 代号：`WEB-FND`
- Worker 分支：`codex/parallel-web-foundation`
- `BASE_SHA`：`765e4470f1ddb60f0ce6f23227d6303961f47fcf`
- 唯一实现所有权：`Ti-Java/web/**`
- 唯一额外交接写入：`Ti-Java/docs/refactor/parallel/handoffs/web-foundation.md`
- 实现 commit SHA：`c7fd40dad2340c320c31281e29608f33d0ee26fe`
- 推荐集成 SHA：`c7fd40dad2340c320c31281e29608f33d0ee26fe`
- 集成约束：INT 应按上述固定 SHA 审核和集成，不以 Worker 分支浮动 tip 作为输入；本 handoff 后续单独提交，仅承载交接元数据。

## 交付结果

Phase 6 Web Foundation 已在独立 Vue 3/Vite 应用中建立，当前只覆盖 Phase 4A 已授权的公共题库只读面：

- 保留旧 Web 的页面信息架构、桌面/移动布局、侧栏与顶栏模式、题库广场列表形态、题库详情形态、主题样式矩阵和原有本地存储键。
- 提供 `/public/banks` 与 `/public/banks/card/{system|user}/{bankId}`；站内跳转只由经过校验的 `source_type + id` 构造，不信任服务端返回的深链 URL。
- 服务端状态统一由 TanStack Query 管理；Pinia 仅承载认证/UI 客户端状态。
- API 只从已固定的 Phase 3、Phase 4A Subject Directory、Phase 4A Public Bank OpenAPI 来源生成；运行时只允许五个已核定 GET operation。
- 同源 `/api`、same-origin credentials、`X-Request-ID`、请求取消与超时边界已落地。
- boards、hot、summary 独立呈现错误、重试与 Request ID，未把失败伪装为空状态。
- 加入题库、个人/已加入题库及练习深链保持显式未晋级；未声明生产 cutover，`productionCutover` 保持 `false`。
- Web 页面实现以仓库内实际旧模板和 CSS 为权威；概念图仅作辅助，存在差异时服从旧页面样式与交互模式。

## `git diff --name-status BASE_SHA...SHA` 路径清单

命令：

```text
git diff --name-status 765e4470f1ddb60f0ce6f23227d6303961f47fcf...c7fd40dad2340c320c31281e29608f33d0ee26fe
```

结果：

```text
A	Ti-Java/web/.gitignore
A	Ti-Java/web/README.md
A	Ti-Java/web/e2e/public-bank-smoke.spec.ts
A	Ti-Java/web/eslint.config.js
A	Ti-Java/web/index.html
A	Ti-Java/web/openapi-ts.config.ts
A	Ti-Java/web/package-lock.json
A	Ti-Java/web/package.json
A	Ti-Java/web/playwright.config.ts
A	Ti-Java/web/scripts/apiSources.mjs
A	Ti-Java/web/scripts/check-generated.mjs
A	Ti-Java/web/scripts/verify-openapi-boundaries.mjs
A	Ti-Java/web/src/App.vue
A	Ti-Java/web/src/api/contracts/sourceManifest.ts
A	Ti-Java/web/src/api/contracts/sourceTypes.ts
A	Ti-Java/web/src/api/facade/publicBankFacade.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/client.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/client/client.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/client/index.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/client/types.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/client/utils.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/auth.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/bodySerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/params.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/pathSerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/queryKeySerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/serverSentEvents.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/types.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/core/utils.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/index.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/sdk.gen.ts
A	Ti-Java/web/src/api/generated/phase3Authentication/types.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/client.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/client/client.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/client/index.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/client/types.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/client/utils.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/auth.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/bodySerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/params.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/pathSerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/queryKeySerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/serverSentEvents.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/types.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/core/utils.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/index.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/sdk.gen.ts
A	Ti-Java/web/src/api/generated/phase4aPublicBank/types.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/client.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/client/client.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/client/index.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/client/types.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/client/utils.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/auth.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/bodySerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/params.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/pathSerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/queryKeySerializer.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/serverSentEvents.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/types.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/core/utils.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/index.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/sdk.gen.ts
A	Ti-Java/web/src/api/generated/phase4aSubjectDirectory/types.gen.ts
A	Ti-Java/web/src/api/transport/apiProblem.ts
A	Ti-Java/web/src/api/transport/configureGeneratedClients.ts
A	Ti-Java/web/src/api/transport/requestId.ts
A	Ti-Java/web/src/components/AppShell.vue
A	Ti-Java/web/src/components/AppSidebar.vue
A	Ti-Java/web/src/components/AppTopbar.vue
A	Ti-Java/web/src/components/AsyncState.vue
A	Ti-Java/web/src/components/HighlightedText.vue
A	Ti-Java/web/src/components/RequestIdNote.vue
A	Ti-Java/web/src/components/ScopeNotice.vue
A	Ti-Java/web/src/components/ThemeMenu.vue
A	Ti-Java/web/src/env.d.ts
A	Ti-Java/web/src/features/public-bank/components/DefaultBankCover.vue
A	Ti-Java/web/src/features/public-bank/components/PlazaSidebar.vue
A	Ti-Java/web/src/features/public-bank/components/PublicBankListItem.vue
A	Ti-Java/web/src/features/public-bank/pages/PublicBankDetailPage.vue
A	Ti-Java/web/src/features/public-bank/pages/PublicBankListPage.vue
A	Ti-Java/web/src/features/public-bank/queries.ts
A	Ti-Java/web/src/main.ts
A	Ti-Java/web/src/pages/FeatureBoundaryPage.vue
A	Ti-Java/web/src/pages/NotFoundPage.vue
A	Ti-Java/web/src/router/index.ts
A	Ti-Java/web/src/stores/auth.ts
A	Ti-Java/web/src/stores/ui.ts
A	Ti-Java/web/src/styles/base.css
A	Ti-Java/web/src/styles/detail.css
A	Ti-Java/web/src/styles/plaza.css
A	Ti-Java/web/src/styles/tokens.css
A	Ti-Java/web/src/testing/publicBankFixtures.ts
A	Ti-Java/web/tests/unit/publicBankFacade.spec.ts
A	Ti-Java/web/tests/unit/publicBankListItem.spec.ts
A	Ti-Java/web/tests/unit/routerBoundaries.spec.ts
A	Ti-Java/web/tests/unit/setup.ts
A	Ti-Java/web/tests/unit/uiStore.spec.ts
A	Ti-Java/web/tsconfig.app.json
A	Ti-Java/web/tsconfig.json
A	Ti-Java/web/tsconfig.node.json
A	Ti-Java/web/vite.config.ts
```

## 验证证据

以下命令均在 `Ti-Java/web` 执行：

| 验证 | 结果 |
| --- | --- |
| `npm run generate:api:check` | 通过；精确匹配 Phase 3/4A 来源、五个 GET runtime operation，生成物确定且当前，生产 cutover 禁用 |
| `npm run lint` | 通过 |
| `npm run typecheck` | 通过 |
| `npm run test:unit` | 通过；4 个 spec 文件、7 个测试 |
| `npm run build` | 通过；Vite 转换 160 个模块 |
| `npm run test:e2e` | 通过；3/3 Playwright 场景 |
| `npm audit --audit-level=high` | 通过；0 vulnerabilities |

Playwright 已覆盖公共题库桌面列表、详情、主题/错误态与移动端单列/双抽屉行为。浏览器插件启动两次均被插件运行时的 `Cannot redefine property: process` 阻断，因此视觉核验改用仓库固定的 Playwright；这是验证工具限制，不是产品运行错误。

## 并行锁记录

- `main-write.lock`：未取得；未写入、暂存、提交或推送 `main`。
- `authority-chain.lock`：未取得；未编辑中央权威链。
- `heavy-verify.lock`：`not acquired / not run`。
- Maven、Testcontainers、Docker、Compose：均未运行；本 lane 的验证仅使用 npm/Vite/Vitest/Playwright。

## 已知边界与依赖

- 当前是公共题库只读 foundation，不代表生产路由切换；生产配置与路由晋级必须由 INT 串行决定。
- 登录写操作、加入题库、个人/已加入题库、练习流仍为明确 blocker，不能从本提交推导为已迁移。
- Playwright 使用固定网络 fixture 验证前端合同与页面状态；连接真实后端环境的集成验收仍需在 INT 取得相应锁并选择时机后执行。
- TypeScript 保持 `strict: true` 和 `noUncheckedIndexedAccess: true`；`exactOptionalPropertyTypes` 暂为 `false`，原因是当前 HeyAPI 生成代码不兼容该选项。
- 若要在中央进度、route parity matrix/delta、acceptance/successor 或全局配置中记录本 lane，必须由 INT 以追加式合同链完成；Worker 未请求也未执行任何 route 状态晋级。

## 权限与资产声明

- 未修改任何中央权威文件，包括 `Ti-Java/README.md`、`docs/refactor/05-progress.md`、route parity matrix/delta、data ownership、全局 OpenAPI、WORM/contract builder/acceptance/parity/successor、`server/pom.xml`、Compose、全局配置、`SecurityConfiguration` 与共享认证过滤器。
- 未覆盖历史合同或 WORM，未改变任何 route 状态。
- 除本 handoff 例外外，实现提交的全部路径都位于唯一所有权目录 `Ti-Java/web/**`。
- 根目录用户资产保持原状且未暂存：`AGENTS.md`（既有修改）、`CLAUDE.md`（既有删除）、`.playwright-cli/`、`miniprogram-1/.gitignore`、`output/`。
