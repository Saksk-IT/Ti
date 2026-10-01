# Ti-Java Codex 执行计划（2026-10）

> 本文件是 Codex Worker 的执行入口，描述当前需要完成的所有工作。
> 历史证据、WORM 与旧 phase 合同保持原位不动，本文件只是操作层规划。
> 每完成一个阶段，更新 `docs/refactor/05-progress.md`，然后提交。

## 当前快照（2026-10-01）

| 项目 | 状态 |
|---|---|
| 路由迁移 | **13 migrated / 598 pending / 0 production cutover** |
| 生产 owner | 旧 Flask（未切换） |
| 全量 Maven verify | **阻断中**（见阶段 A） |
| catalog 读取 | 完成（Phase 4A） |
| personalbank 内部读取 | 完成（Phase 4B，HTTP 层待开） |
| 事务写业务逻辑 | 完成（9 条，HTTP 层待开） |
| Vue Web | 2 页（公共题库列表 + 只读名片） |

---

## 执行约束（必读）

- 每个子任务完成后立即运行相关测试，确保 0 failure/error/skip 后再提交
- 历史合同、WORM、route delta CSV **禁止改写**；route 晋级只能追加新 delta 行
- 每个 HTTP operation 必须先有 OpenAPI overlay 和集成测试，再有 Controller 实现
- 所有提交推送到 `main`，不新建分支
- commit 格式：`feat(java): <简述>` / `fix(java): <简述>` / `test(java): <简述>`
- route delta 晋级必须在全量 Maven verify 0 failure 后才能追加

---

## 阶段 A：解除全量 Maven verify 阻断（最高优先级）

### A1 修复 catalog 边界字面量

**问题：** `LegacyQuestionEditNormalizer.java` 含硬编码中文展示字符串，导致 `CatalogPublicBoundaryNeutralityTest` 失败。

**操作：**
1. 读取 `LegacyQuestionEditNormalizer.java`，定位中文字面量
2. 将字面量移出 catalog 边界（提取到 `operations` 模块或由调用方传入）
3. 补充追加式 successor 合同，让 `CatalogPublicBoundaryNeutralityTest` 接受新字节

**验证：** `./mvnw -pl server test -Dtest=CatalogPublicBoundaryNeutralityTest` 通过

---

### A2 SecurityConfiguration successor

**问题：** `SecurityConfiguration.java` 当前字节未被 tag-preflight successor 接受，导致 `ModuleContractParityTest` 失败。

**操作：**
1. 读取最新 `SecurityConfiguration.java` 字节
2. 在 `docs/refactor/phase4c/` 建立追加式 successor 外锚文件，登记当前 SHA-256
3. 更新 tag-preflight 相关 parity test 的 expected source set

**验证：** `./mvnw -pl server test -Dtest=ModuleContractParityTest` 通过

---

### A3 修复 application shape 差异

**问题：** shape 合同期望 23 个公开应用方法，当前实际为 24。

**操作：**
1. 运行 `./mvnw -pl server test -Dtest=PersonalBankUsageStatsContractParityTest`，找到具体失败断言
2. 确认是多了一个方法还是合同数字过时
3. 若多出了不应公开的方法，将其改为 package-private；若合同数字过时，追加 successor 合同更新期望值

**验证：** 所有 `*ContractParityTest` 通过

---

### A4 pom.xml 和 phase2 runner 的 successor 外锚

**问题：** `server/pom.xml` 和 `infra/phase2/verify-local-reference-wormhole.sh` 缺少指向当前字节的 successor 外锚。

**操作：**
1. 计算两个文件的当前 SHA-256
2. 在 `docs/refactor/phase4c/` 建立追加式外锚文件，登记精确路径与 SHA-256
3. 更新对应 parity test 使其接受新锚点

**验证：** `./mvnw -pl server test -Dtest=Phase4cPersonalBankUserCountsHttpImplementationContractParityTest` 通过

---

### A5 全量 Maven verify

**操作：**
```bash
cd Ti-Java
./mvnw clean verify -T1
```

**目标：** surefire + failsafe 总计 0 failure/0 error/0 skip

生成本次 checkpoint 记录（不需要新 WORM，记录结果到 `05-progress.md` 即可）。

---

## 阶段 B：Phase 4C 九条事务写 HTTP 层

> 前提：阶段 A 全量 verify 通过

业务逻辑已在 `learning` 和 `catalog` 模块实现。本阶段只需为每条 operation 补充 HTTP 适配层。

每条 operation 标准步骤：
1. OpenAPI overlay（追加到 `openapi/phase4c-write-operations.openapi.json`）
2. Controller + DTO（在对应模块的 `web` 子包）
3. Security/CORS 配置（在 `SecurityConfiguration.java` 添加路由规则）
4. Redis 限流配置
5. MockMvc 单元测试 + 真实 PG/Redis/Tomcat 集成测试
6. 局部 Maven verify 通过后提交

### B1 record-result（2 条 alias）

```
POST /api/record_result
POST /api/quiz/record_result
```

- 认证：Session + Bearer 双模式
- 幂等：`Idempotency-Key` header（已有业务层支持）
- 限流：actor HMAC Redis 三窗口

### B2 study-learn-record

```
POST /api/user/study/learn   （或对应旧栈路径）
```

### B3 study-review-record

```
POST /api/user/study/review
```

### B4 study-review-master

```
POST /api/user/study/master
```

### B5 checkin

```
POST /api/user/checkin
```

### B6 question-edit

```
PUT /api/quiz/questions/{questionId}
```

- 认证：管理员 / 科目管理员

### B7 favorite（2 条 alias）

```
POST /api/user/favorite
POST /api/quiz/favorite   （或等价路径，核查旧栈路由）
```

### B 完成门禁

```bash
./mvnw clean verify -T1   # 0 failure
```

追加 route promotion delta CSV（+9 migrated）。更新 `05-progress.md`。

预期新状态：**22 migrated / 589 pending / 0 cutover**

---

## 阶段 C：Phase 4B 个人题库 HTTP 层

> 前提：阶段 B 完成

内部读取实现已在 `personalbank` 模块。本阶段补 HTTP 层。

### C1 分类列表 HTTP（2 alias）

```
GET /api/user/bank/categories
GET /api/quiz/bank/categories   （核查旧栈路径）
```

- 认证：Session + Bearer
- 响应信封：统一错误格式
- Session `last_active` 写入

### C2 分享列表 HTTP（2 alias）

```
GET /api/user/bank/{bankId}/shares
GET /api/quiz/bank/{bankId}/shares
```

- Owner 鉴权（非 owner 返回 403）

### C3 全部分享 HTTP（2 alias）

```
GET /api/user/bank/shares
GET /api/quiz/bank/shares
```

### C4 使用统计 HTTP（2 alias）

```
GET /api/user/bank/usage-stats
GET /api/quiz/bank/usage-stats
```

### C5 user-counts（确认已就绪）

两条 alias Controller 在 Phase 4C 已物化，核查是否还有 HTTP 层工作，若无则只追加 route delta。

### C 完成门禁

```bash
./mvnw clean verify -T1
```

追加 route promotion delta（+~10）。

---

## 阶段 D：Operations 模块 HTTP（后台管理端点）

> 前提：阶段 C 完成

### D1 后台题目导出（2 alias）

```
GET /admin/api/questions/export
GET /admin/questions/export
```

- 认证：后台管理员
- 返回：题目列表 JSON（与旧栈格式兼容）

### D2 后台题目摘要列表（2 alias）

```
GET /admin/api/questions
GET /admin/questions
```

- 可选参数：`subjectId`, `questionType`

### D3 后台题目详情（2 alias）

```
GET /admin/api/questions/{question_id}
GET /admin/questions/{question_id}
```

### D4 后台科目列表

```
GET /admin/api/subjects
```

### D5 后台科目上下文

```
GET /admin/subjects/{subject_id}/questions
GET /admin/subjects/{subject_id}/duplicate-check
```

### D6 后台题型枚举 HTTP（2 alias）

```
GET /admin/api/types
GET /admin/types
```

每批完成后运行局部 verify 并提交。D 全部完成后全量 verify，追加 route delta。

---

## 阶段 E：Learning 模块剩余读取 HTTP

### E1 错题列表

```
GET /api/user/mistakes
GET /api/quiz/mistakes
```

### E2 用户答题历史 / 学习统计

```
GET /api/user/study/stats
GET /api/user/study/history
```

### E3 签到历史

```
GET /api/user/checkin/history
```

### E4 收藏列表

```
GET /api/user/favorites
GET /api/quiz/favorites
```

---

## 阶段 F：Identity 模块扩展

### F1 用户注册

```
POST /api/user/register
```

### F2 用户资料

```
GET  /api/user/profile
PUT  /api/user/profile
```

### F3 密码修改 / 找回

```
POST /api/user/change-password
POST /api/user/reset-password
```

---

## 阶段 G：Vue Web 页面补全

> 依赖对应后端 HTTP 层就绪后逐页开发

| 页面 | 依赖 |
|---|---|
| 登录 / 注册 | F1 |
| 练习 / 学习 | B 系列 |
| 错题本 | E1 |
| 学习统计 | E2 |
| 签到 | B5 / E3 |
| 个人题库 | C 系列 |
| 收藏 | E4 |
| 后台管理 | D 系列 |

每页标准流程：
1. OpenAPI 生成 TypeScript 客户端
2. TanStack Vue Query hook
3. 页面组件（Vue 3 + TypeScript strict）
4. Playwright E2E（新增场景）
5. `npm run build` lint + typecheck + audit 通过

---

## 阶段 H：Assessment 模块

> 前提：catalog + learning HTTP 稳定

- 考试创建、题目抽取、答题、自动评分、成绩查询
- 需要新建 `assessment` 模块完整实现（当前只有空 context test）

---

## 阶段 I：Community / Messaging / Campus 模块

> 这三个模块当前全部 pending，需要从数据模型开始完整实现

按旧栈路由盘点文件逐条实现，优先级：Community > Campus > Messaging

---

## 阶段 J：微信小程序迁移

- 核查 `Ti-Java/miniprogram/` 当前 API 调用地址
- 将已迁移的路由切换到 Java 地址（`BASELINE.md` 中有记录的端点）
- 新功能使用 Java API；旧兼容路径保持双运行
- 通过 36 个现有小程序测试

---

## 阶段 K：生产切流

> 前提：598 pending 路由全部 migrated，或经过评估可接受的部分切流

1. 完整全量 Maven verify（预计 800+ surefire + 200+ failsafe）
2. 独立 Gitless 副本验收（独立 PG/Redis，空 Maven 缓存，0 残留）
3. Schema/index diff 脚本：Flask 历史迁移 → Java Hibernate validate 等价验证
4. 双栈并行只读观察（Java 读取同一 PG，对比响应，持续 ≥ 7 天）
5. Nginx canary 切流（1% → 10% → 50% → 100%）
6. Flask 下线

---

## 快速参考

```bash
# 局部测试（快）
cd Ti-Java && ./mvnw -pl server test -Dtest=<TestClassName>

# 全量验证（慢，每阶段末运行一次）
cd Ti-Java && ./mvnw clean verify -T1

# Vue 开发验证
cd Ti-Java/web && npm run build && npm run test:unit && npx playwright test

# 查看路由状态
grep -c ",migrated," Ti-Java/docs/refactor/phase4c/effective-route-parity-successor-status.json
```
