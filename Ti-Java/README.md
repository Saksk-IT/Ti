# Ti-Java

Ti-Java 是 Ti 的独立重构项目，目标是以 Java 25、Spring Boot 4.1、Spring MVC 和 Spring Modulith 重新实现现有业务，并逐步加入 Vue 3 + TypeScript Web 与项目自有的小程序。

阶段 0 事实基线与阶段 1 架构/契约已经固化；阶段 2 的 Java 基础骨架、测试与本地运行设施已通过本阶段验收，后续从阶段 3 的对比工具与认证兼容继续。当前仍是迁移骨架：**已迁移路由数为 0，已实现公开业务操作数为 0**，不能替代旧 Flask 项目，也不代表完整重构已经完成。

## 当前技术与边界

- `server/` 固定使用 Java 25、Maven Wrapper 3.9.16、Spring Boot 4.1.0 和 Spring Modulith 2.1.0；默认采用 Spring MVC，不引入 WebFlux、R2DBC 或阶段 8 之前的 Flyway。
- 模块化单体包含 `identity`、`catalog`、`personalbank`、`learning`、`assessment`、`community`、`messaging`、`campus`、`coding`、`intelligence`、`operations` 11 个业务模块，以及 `sharedkernel`、`web` 两个支撑模块。
- 11 个业务模块目前只有经过架构测试约束的公开命名接口；具体命令、DTO、事件负载和兼容路由要在后续阶段依据旧系统证据实现，不能从占位名称推断为已迁移能力。
- PostgreSQL 是唯一业务事实源；Redis 只用于可重建的辅助状态。Hibernate 始终使用 `ddl-auto=validate`，禁止 ORM 自动建表或改表。
- `catalog` 内的 `subjects` 映射只是内部只读兼容探针，不是公开 API，也不拥有写入权。

## 目录

- `server/`：Java 模块化单体、Maven Wrapper、架构/单元/集成测试和多阶段 Dockerfile。
- `infra/phase2/`：阶段 2 静态门禁、固定构建环境、PostgreSQL/Redis 夹具和本地参考结构验证工具。
- `compose.dev.yml`：与旧项目隔离的阶段 2 本地 Compose。
- `docs/refactor/phase2/`：阶段 2 范围、证据和未完成边界。
- `contracts/`：确定性生成的 OpenAPI 3.1.2 初稿与人工证据 override。
- `docs/refactor/adr/`：已接受的架构决策。
- `docs/refactor/phase1/`：API 约定、模块合同、关键不变量和对比/切换协议。
- `docs/refactor/`：事实盘点、迁移矩阵、数据所有权、运行手册与连续进度。
- `tools/`：迁移期盘点和黄金样本工具；不是生产运行依赖。
- `miniprogram/`：阶段 0 从旧项目受版本控制源码复制的新项目小程序基线。
- `web/`：计划在阶段 6 创建，目前尚未创建。
- `services/`：只有后续证明确需 Python 独立工作负载时才创建。

## Phase 2 验证

从本目录运行固定镜像构建的完整验证：

```bash
./infra/phase2/verify-static.sh
./infra/phase2/verify-in-maven-container.sh clean verify
```

第二条命令把本目录挂载到固定 Maven/Temurin 25 容器，并挂载 Docker socket 供 Testcontainers 启动固定 digest 的 PostgreSQL 与 Redis。**Docker socket 近似授予容器主机 root 控制能力，只能对受信代码运行。** 若本机已经安装匹配的 Java 25 和 Maven 3.9.16，也可以运行：

```bash
cd server
./mvnw clean verify
```

当前测试证据、最小夹具与完整 70 表本地参考结构验证的适用范围见 [`docs/refactor/phase2/README.md`](docs/refactor/phase2/README.md)。

## 启动独立开发 Compose

```bash
cp .env.example .env
docker compose --env-file .env -f compose.dev.yml config --quiet
docker compose --env-file .env -f compose.dev.yml up --build -d
curl --fail http://127.0.0.1:18080/livez
curl --fail http://127.0.0.1:18080/readyz
```

默认只向宿主机发布 Java API `127.0.0.1:18080` 和 PostgreSQL `127.0.0.1:25432`；二者同时连接专用宿主接入网与内部后端网，Redis 只连接内部后端网且不发布宿主端口。Prometheus 端点只监听容器管理端口 `9090`，不映射到宿主机，也不经 `18080` 暴露。镜像基础版本均在 `server/Dockerfile` 与 `compose.dev.yml` 中按 digest 固定。

此 Compose 只承载阶段 2 最小只读结构，不得连接生产数据库，也不得与旧 Flask 共享可写数据库、卷或 Redis。

## 阶段 0/1 可重复命令

从仓库根目录运行：

```bash
.venv/bin/python Ti-Java/tools/inventory_legacy.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor

.venv/bin/python Ti-Java/tools/capture_golden_samples.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor/golden-samples

.venv/bin/python Ti-Java/tools/measure_legacy_baseline.py \
  --legacy-root . \
  --output Ti-Java/docs/refactor/legacy-performance-sample.json \
  --samples 5

.venv/bin/python Ti-Java/tools/inventory_surfaces.py \
  --legacy-root . \
  --miniprogram-root Ti-Java/miniprogram \
  --output Ti-Java/docs/refactor/09-surface-inventory.json

node --test Ti-Java/miniprogram/tests/*.test.js
python3 Ti-Java/tools/validate_phase0.py --legacy-root .

python3 Ti-Java/tools/generate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_boundaries.py
python3 Ti-Java/tools/validate_phase1.py
```

阶段 0 工具只读取旧代码，并在临时测试数据库中构造脱敏样本；阶段 1 生成器只读取已冻结在本目录内的矩阵、黄金样本和人工 override。它们均不是新项目生产运行依赖。

## 进度入口

继续实施前先阅读 [`docs/refactor/05-progress.md`](docs/refactor/05-progress.md)。只有迁移计划的最终完成定义全部满足，才能宣告 Ti-Java 具备替代旧项目的条件。
