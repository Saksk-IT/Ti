# Phase 6 Web Foundation

本目录记录 Phase 6 第一条只读垂直切片的 INT 验收。固定 Worker 实现提交为
`c7fd40dad2340c320c31281e29608f33d0ee26fe`，其唯一父提交是申报 BASE
`765e4470f1ddb60f0ce6f23227d6303961f47fcf`，全部 102 个新增文件均位于
`Ti-Java/web/**`。handoff 提交 `528ccb759d269fb1a2655e9c14838dc1b621c863`
只用于审计，没有合入 main。

当前 foundation 只提供 `/public/banks` 与
`/public/banks/card/{system|user}/{bankId}` 两个 Vue SPA 读取页面。运行时调用仅限
Phase 4A 公共题库 OpenAPI 的五个 GET；使用同源 `/api`、same-origin credentials、
`X-Request-ID`、12 秒读取超时与 TanStack Vue Query。Pinia 不保存服务端题库事实。

`web-foundation-acceptance.json` 固定实现来源、102 文件/558,898 字节的 Gitless 内容摘要、
三份 OpenAPI 物理摘要、五个 runtime operation、验证计数和禁止边界。可重复门禁：

```bash
python3 docs/refactor/phase6/verify_web_foundation_acceptance.py
cd web
npm ci
npm run generate:api:check
npm run lint
npm run typecheck
npm run test:unit
npm run build
npm run test:e2e
npm audit --audit-level=high
```

`foundation_complete=true` 不等于 Phase 6 全部完成。加入题库、个人题库、练习、
user-counts 和全部写操作继续显示显式阻断页；`/search` 与
`/subjects/<int:subject_id>` 也尚未形成垂直切片。四条 Phase 6 旧页面 operation 均保持
pending，当前有效 route 状态仍是 13 migrated / 598 pending / 0 production cutover。
本节点不创建 route delta，不授权 operator、schema/index、真实数据迁移、网关或生产切流。

## Source-successor chain

Web foundation 进入 `main` 后对三个中央说明文件产生了合法字节漂移。提交
`40a27ffdd83ecf240e17f4a5f69106906faaef35` 先以
`web-foundation-source-successor-contract.json` 承接历史 typed-anchor；随后
`web-foundation-source-successor-anchor-contract.json` 固定该提交的父提交、树、11 条
精确差异、2,297/28 行 numstat、blob 字节和九项显式源码后继。链路不使用动态文件发现，
也不把工作树 HEAD 当作证据。

可重复验证：

```bash
python3 tools/build_phase6_web_foundation_source_successor_anchor_contract.py \
  --repository-root .. --check
python3 tools/phase6_web_foundation_source_successor_anchor_acceptance.py \
  --repository-root ..
python3 -m unittest \
  tools.test_phase6_web_foundation_source_successor_anchor_contract
```

外部锚点只证明已推送的前驱检查点；本节点自身六个控制源继续明确自排除，等待后续已推送
Git 节点承接。因此它没有改变 Phase 6 完成度，也没有改变 13 / 598 / 0 的路由权威。
