# Ti-Java 并行重构协调合同

## 1. 目的与适用范围

本合同只建立 Ti-Java 模块化单体重构的并行协作控制面，不授权任何业务实现、路由晋级、数据迁移、schema/index、客户端、网关或生产切流。本合同适用于主线集成会话 `INT` 和所有 Worker。Wang 的当前指令优先；在 `Ti-Java/` 范围内，`Ti-Java/AGENTS.md` 对根目录旧 main 工作规则的显式调整优先于该旧规则，根目录其余规则继续继承，本合同负责细化执行方式。

采用单一主线写入者、独立 Git worktree/分支、互斥 ownership、不可变交接 SHA 和串行集成。Git worktree 只隔离工作树与分支，不构成文件所有权或验证资源隔离；所有权和重型验证仍由本合同单独约束。

## 2. 角色与不变量

### 2.1 INT

`INT` 是以下对象的唯一写入者：

- `main` 分支、主工作树和主索引；
- `origin/main`；
- 本合同第 4 节定义的中央权威文件；
- authority/acceptance/parity/successor/WORM 链及 route 晋级决定。

只有 `INT` 可以在 `main` 执行会改变状态的 Git 操作，包括暂存、提交、合并、拣选、变基、回退和推送。`INT` 一次只集成一个 lane，并在每个 lane 后重新核对主线状态。

### 2.2 Worker

Worker 必须：

1. 从 `INT` 发布的精确 `BASE_SHA` 创建独立 Codex Worktree。
2. 使用唯一分支 `codex/parallel-<lane>`；`<lane>` 必须匹配 `[a-z0-9][a-z0-9-]*`。
3. 只修改本合同第 3 节登记的 ownership target，以及自己的 handoff 文件。
4. 在自己的分支提交并可推送该分支；不得修改、检出或推送 `main`，不得推送到 `origin/main`。
5. 以固定 commit SHA 交付，不把未提交内容、stash、浮动分支名或聊天上下文作为交付物。

任何分支权限都不能扩大目录权限；任何目录权限都不能覆盖中央权威文件禁区。

## 3. Lane ownership 合同

每个 Worker 同一时刻只能拥有一个明确目标，二选一：

- 一个由 `INT` 明确登记的、边界封闭且与其他 lane 不重叠的目录；或
- 一个在 `BASE_SHA` 中不存在的唯一新增测试类的精确路径。

ownership target 必须用仓库相对路径记录在 handoff 中。目录 ownership 不自动包含目录外的调用方、共享测试夹具、配置、合同或生成物。唯一新增测试类不得替换、重命名或拆分现有类，也不得借由同名资源文件扩大范围。

每个 lane 唯一的附加可写路径是：

`Ti-Java/docs/refactor/parallel/handoffs/<lane>.md`

handoff 例外只用于交接元数据，不构成第二个开发目录。Worker 不得写入其他 lane 的 handoff，也不得编辑本合同、两级 `AGENTS.md` 或 handoff 目录中的中央模板/索引。

若任务需要第二个目录、现有共享类、中央权威文件或与其他 lane 重叠，Worker 必须停止并交回 `INT` 重新切分；不得自行扩权。

## 4. 中央权威文件：仅 INT

下列文件或类别只归 `INT`。路径模式是最低禁区；名称变化、移动或新建的等价权威文件同样属于禁区。

| 类别 | 中央权威路径或模式 |
| --- | --- |
| 总览与恢复入口 | `Ti-Java/README.md`、`Ti-Java/docs/refactor/05-progress.md` |
| 协作规则 | `Ti-Java/AGENTS.md`、`Ti-Java/docs/refactor/parallel/coordination-contract.md`；handoff 仅按第 3 节例外开放 |
| Route 权威 | `Ti-Java/docs/refactor/02-route-parity-matrix.csv`、任意 `docs/refactor/**/route-parity-delta.csv`、任意有效 route parity status/matrix/successor |
| 数据所有权 | `Ti-Java/docs/refactor/03-data-ownership.csv`、任意 `docs/refactor/**/data-ownership-delta.csv`、任意有效 data ownership status/overlay/successor |
| 全局 OpenAPI | `Ti-Java/contracts/**`、`Ti-Java/openapi/**` 及其生成、覆盖、聚合和晋级元数据 |
| 合同与验收链 | 任意 WORM；历史或当前 contract；contract builder；acceptance、parity、successor、anchor、closure、effective-status 及相应 Python/Java 门禁和测试 |
| 构建与运行拓扑 | `Ti-Java/server/pom.xml`、`Ti-Java/**/compose*.yml`、`Ti-Java/.env*`、`Ti-Java/server/build-versions.properties` |
| 全局配置 | `Ti-Java/server/src/main/resources/application*.yml`、`application*.yaml`、`application*.properties` 及共享运行配置 |
| 共享安全边界 | 任意 `SecurityConfiguration`、`Ti-Java/server/src/main/java/io/saksk/ti/web/security/*AuthenticationFilter.java` 及等价共享认证过滤器 |

Worker 若发现自己的 ownership target 内包含上述类别，中央权威禁区优先；该文件必须从 Worker 范围剔除并由 `INT` 串行处理。

## 5. Handoff 合同

Worker 必须新建且只编辑自己的 `docs/refactor/parallel/handoffs/<lane>.md`。handoff 至少包含：

- lane、Worker 代号、分支名；
- `BASE_SHA`；
- 精确 ownership target；
- 实现 commit SHA 清单和推荐集成 SHA；
- `git diff --name-status <BASE_SHA>...<SHA>` 的路径清单；
- 已执行验证、结果及未执行原因；
- heavy lock 的取得/释放记录，若未运行重型验证则明确写 `not acquired / not run`；
- 已知风险、与其他 lane 的依赖、需要 `INT` 完成的中央文件变化；
- 明确声明未修改中央权威文件、历史合同/WORM 和 root 用户资产。

为避免 commit 自引用，先提交实现，再在 handoff 中记录实现 commit SHA；handoff 可作为后续仅交接提交。`INT` 只接受 handoff 中固定的实现 SHA，并以对象内容和 `BASE_SHA...SHA` 差异复核，不以分支当前 tip 替代。

Worker 完成后推送 `codex/parallel-<lane>`，把 handoff 路径和 commit SHA 交给 `INT`。聊天摘要不能替代 handoff 文件。

## 6. 仓库外并行锁

锁命名空间固定为 `/Users/sak/.codex/coordination/ti-java/`。以下三个精确路径是本机排他锁目录：

| 锁 | 作用 | 可取得者 |
| --- | --- | --- |
| `/Users/sak/.codex/coordination/ti-java/main-write.lock` | 保护主工作树、主索引、`main` ref、主线提交和 `origin/main` 推送 | 仅 `INT` |
| `/Users/sak/.codex/coordination/ti-java/authority-chain.lock` | 保护第 4 节中央权威文件、合同/WORM/acceptance/parity/successor 构建及 route 晋级 | 仅 `INT` |
| `/Users/sak/.codex/coordination/ti-java/heavy-verify.lock` | 串行 Maven、Testcontainers、Docker 和 Compose | `INT` 或一个 Worker |

锁协议：

1. 通过对精确 `.lock` 路径执行原子 `mkdir` 取得锁；路径已存在即取得失败，必须等待或退出，禁止绕过。
2. 持有者在锁目录记录 owner、lane、branch、worktree、开始时间和计划命令，并在整个子进程及其容器清理期间持续持锁。
3. 只有原持有者可正常释放。疑似陈旧锁不得由 Worker 删除或抢占；由 `INT` 核对 owner、进程、worktree 和外部资源后清理。
4. 同时需要多个锁时，固定顺序为 `main-write` → `authority-chain` → `heavy-verify`，逆序取得被禁止；释放使用逆序。
5. 锁只协调本机并发，不替代 Git 状态、ownership、测试隔离、容器命名空间或验收合同。

任何 Maven 命令（包括定向 unit test）、任何会启动 Testcontainers 的测试、任何 `docker`/`docker compose` 命令，以及包装这些命令的脚本，都必须先取得 `heavy-verify.lock`。所有 worktree 共用这一把锁；禁止并发 Maven，也禁止 Maven 与 Docker/Compose 重型验证重叠执行。

## 7. 不可变合同与追加式状态

- 历史 contract、WORM、acceptance 报告、golden ledger、manifest、route delta 和已固定证据保持字节不可变；禁止覆盖、原地修订、重格式化或用当前工作树重新生成后替换。
- 新事实只能通过新的、显式绑定固定前驱 SHA/物理摘要的 successor 或 delta 追加。
- route 状态只能由 `INT` 在取得 `authority-chain.lock` 后，通过新的追加式 route successor/delta 改变；Worker 不得把 `pending` 改为 `migrated`，不得声明 cutover 或回写历史矩阵。
- 若旧证据有误，保留旧字节并由新 successor 明确记录 supersede/approved difference；不得伪装为历史事实从未存在。

## 8. INT 串行集成流程

`INT` 对每个 lane 依次执行：

1. 取得 `main-write.lock`，核对 `HEAD`、`origin/main`、主工作树和受保护资产。
2. 读取 handoff，验证分支名、`BASE_SHA`、固定 commit SHA、ownership 和路径差异。
3. 拒绝中央权威文件、ownership 越界、交叉 lane 重叠、未提交内容或历史证据改写。
4. 只把审核通过的固定 commit 集成到 `main`；一次只处理一个 lane。
5. 如需中央链变更，由 `INT` 再取得 `authority-chain.lock`，以新 successor/delta 追加并串行验证。
6. 如需 Maven/Testcontainers/Docker/Compose，再取得 `heavy-verify.lock`；完整执行并清理后释放。
7. 只暂存当前集成相关的 `Ti-Java/` 文件，提交并推送 `origin/main`；随后发布新的 `BASE_SHA`。

以下任一情况必须拒绝 handoff：分支命名不合规、基线不明、SHA 不可解析、目标不唯一、修改中央权威文件、改写历史合同/WORM/route delta、越过 ownership、缺少 handoff、声称执行重型验证却无锁记录，或会覆盖根目录用户资产。

## 9. 根目录用户资产保护

以下根目录既有用户资产始终在本控制面的写入范围之外：

- `AGENTS.md`
- `CLAUDE.md`
- `.playwright-cli/`
- `miniprogram-1/.gitignore`
- `output/`

`INT` 和 Worker 均不得暂存、清理、还原、覆盖或以格式化/生成工具触碰这些资产。主线提交必须用显式 `Ti-Java/...` 路径暂存，并在提交前后复核这些资产状态保持不变。

## 10. 当前控制面恢复点

本合同建立时的业务权威状态仍由当前 Phase 4C typed-normalization external anchor 描述：**11 migrated、600 pending、0 production cutover**。本控制面不改变该状态，也不创建新的业务 successor。后续 Worker 必须从 `INT` 在本控制面提交并推送后公布的新 `BASE_SHA` 开始。
