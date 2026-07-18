# Ti-Java 补充工程规则

本目录继承仓库根目录 `AGENTS.md` 的全部规则，并增加以下约束：

- `Ti-Java/` 必须能够在未来被独立抽取；生产运行时、构建和测试不得读取父目录文件。
- 根目录旧 Flask、Jinja、静态资源、`miniprogram-1/`、Alembic 与 Compose 只作只读契约参考。
- 旧项目盘点工具必须显式接收 `--legacy-root`，不得成为 Java/Web/小程序的运行时依赖。
- 后端按业务模块组织；禁止建立全局 `controller/service/repository/model` 技术层目录。
- 每个阶段先补契约和测试，再实现；不得以空实现、跳过测试或放宽断言通过验收。
- PostgreSQL 是业务事实源；Redis 仅用于可重建的缓存、限流、会话辅助与短期协调。
- Hibernate 只允许 schema 校验，不允许自动创建或修改业务表。
- `docs/refactor/05-progress.md` 是连续执行的唯一恢复入口，每次提交前后必须更新。
- 每次提交只暂存本阶段在 `Ti-Java/` 中产生的文件；不得暂存根目录既有脏工作区。

## 并行协作与主线集成

本节是 Wang 对根目录旧“所有任务都直接在 `main` 工作”规则的显式调整；在 `Ti-Java/` 并行重构期间，以本节和 `docs/refactor/parallel/coordination-contract.md` 为准：

- `INT` 是 `main`、主工作树、主索引及 `origin/main` 的唯一写入者；只有 `INT` 可以在 `main` 暂存、提交、合并/拣选和推送。
- Worker 必须使用独立 Codex Worktree 和 `codex/parallel-<lane>` 分支；不得检出、修改或推送 `main`。
- 每个 Worker 同一时刻只可拥有一个由 `INT` 明确分配且互不重叠的目录，或一个在 `BASE_SHA` 不存在的唯一新增测试类。其唯一额外可写路径是 `docs/refactor/parallel/handoffs/<lane>.md`。
- Worker 禁止编辑中央权威文件、历史合同或 WORM；不得自行推进 route 状态。合同链、路由晋级、主线集成和全量验证由 `INT` 串行执行。
- Worker 必须以独立 handoff 文件和已提交的 commit SHA 交接；未提交的工作树内容、仅聊天说明或浮动分支头不能作为集成输入。
- Maven、Testcontainers、Docker 和 Compose 必须先取得仓库外的 `heavy-verify.lock`，并全局串行执行；禁止并发 Maven。
- 历史合同、WORM 和既有 route delta 不得覆盖、改写或重生成；route 状态只能由 `INT` 通过新的追加式 successor/delta 改变。
- `docs/refactor/05-progress.md` 继续是业务重构与权威合同链的恢复入口；不改变业务/路由/所有权/验收状态的纯并行控制面提交记录在 coordination contract，不为此改写当前 Phase 4C 锚点。

完整中央文件清单、lane/handoff 合同、锁路径、锁顺序和集成拒绝条件见 `docs/refactor/parallel/coordination-contract.md`。
