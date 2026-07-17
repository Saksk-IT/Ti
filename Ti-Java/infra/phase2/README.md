# Phase 2 独立运行设施

本目录只服务于 `Ti-Java/` 的阶段 2 骨架，不引用根目录旧 Compose、旧容器、旧端口、旧卷或 Flask 入口。基础 Compose 默认发布：

- Java API：`127.0.0.1:18080`；
- PostgreSQL：`127.0.0.1:25432`；
- Redis：不发布到主机，仅在内部网络可见。

确需从主机诊断 Redis 时，显式叠加 `compose.redis-port.yml`，发布到 `127.0.0.1:26379`：

```bash
docker compose --env-file .env \
  -f compose.dev.yml \
  -f infra/phase2/compose.redis-port.yml up -d
```

## 安全边界

`.env.example` 和 `secrets/*.example` 只含明确标记的非生产占位值。私有本地值应复制为去掉 `.example` 后缀的文件；`Ti-Java/.gitignore` 会忽略这些文件。Compose 通过 `/run/secrets` configtree 把数据库、Redis 密码和登录限流 HMAC key 交给应用，不把这些值放进环境变量或命令行参数，也不跨阶段复用 Secret 文件。

API、PostgreSQL 和 Redis 均启用只读根文件系统、临时目录、`cap_drop: ALL`、`no-new-privileges`、PID/内存边界及日志轮转。PostgreSQL 应用角色只有 `SELECT` 与连接权限；建表角色只在初始化容器内部使用。

三个服务的服务间流量只走 internal `backend` 网络。API 与 PostgreSQL 额外挂载独立的非 internal `host_access` bridge，使其绑定到回环地址的宿主端口在 Docker Desktop 上可达；Redis 不加入该 bridge，也不发布宿主端口。

## 最小 schema 的含义

`server/src/test/resources/db/phase2/minimal-reference-schema.sql` 仅复刻当前 `subjects` 的 9 列，并补一个只含主键的 `plaza_boards` FK 目标。它不是 Flyway baseline、不是生产迁移，也不证明生产 PostgreSQL 版本。

`reference-drift-manifest.json` 记录 2026-07-16 对获准本地开发参考实例的只读观察：运行时为 PostgreSQL 18.4 / `180004`、`public` 为 70 表/617 列；仓库旧声明仍是 `postgres:16-alpine`。生产版本保持未知。阶段 2 同时跑 18.4 主夹具和 16.14 兼容夹具，但绝不假设 18 的 dump 能恢复到 16。

## 验证

静态门禁不需要本机 JDK：

```bash
./infra/phase2/verify-static.sh
```

完整 Maven 验证也不需要本机 JDK：

```bash
./infra/phase2/verify-in-maven-container.sh clean verify
```

该脚本固定 Maven/Temurin 25 镜像，把整个 `Ti-Java/` 以同一个绝对路径挂载进构建容器，并挂载 Docker socket 供 Testcontainers 创建兄弟容器。Docker socket 具有近似 root 的主机控制能力；只可运行受信仓库代码。脚本不关闭 Ryuk、不启用复用，也不会在无 Docker 时跳过集成测试。Docker Desktop 下自动使用 `host.docker.internal` 访问随机映射端口。

### 本地参考结构 wormhole

2 表夹具负责快速、确定性的日常测试；完整结构兼容性通过显式授权的本地非生产参考容器按需验证，不把 70 表 dump 提交进仓库：

```bash
./infra/phase2/verify-local-reference-wormhole.sh \
  --source-container ti-postgres-1 \
  --source-user studyuser \
  --source-db ti_db \
  --report docs/refactor/phase4c/next-slice-worm-evidence.json
```

脚本只接受显式源参数，不接受或搜寻源密码，也不读取 `Ti-Java/` 父目录。`--report` 必填，且必须指向 `Ti-Java/` 内父目录已存在的全新版本化文件；任何已存在文件、符号链接或目录都会被拒绝，最终报告以同目录 hard-link 原子 no-clobber 发布。它执行 `schema-only`、`no-owner`、`no-acl` 导出，恢复到 digest 固定的隔离 PostgreSQL 18.4，验证 70 表/617 列、固定 canonical schema SHA 和服务端版本；随后创建只读角色，主动关闭该会话的默认只读开关，仍要求 DML、普通 DDL 和 TEMP DDL 全部被 ACL 拒绝。最后用 Dockerfile 构建的 Java 镜像连接恢复副本，以 `ddl-auto=validate` 启动并通过 readiness；构建前与 readiness 后的 Dockerfile/build-context SHA 必须完全一致。

schema dump、随机 Secret、容器、网络、卷和临时 Java 镜像会在退出时清理。仓库只保留不含 schema、DSN 或 Secret 的版本化报告；[`local-reference-verification.json`](local-reference-verification.json) 是不可变历史锚点，后续报告必须由 [`phase2_wormhole_successor_acceptance.py`](../../tools/phase2_wormhole_successor_acceptance.py) 以固定路径、报告 SHA、前驱 SHA、Dockerfile SHA 和 Java build-context SHA 显式加入后继链。当前固定链为 Phase 4B 锚点 → Phase 4C user-counts 入口 → Phase 4C HTTP-neutral read → Phase 4C HTTP-neutral read access，最后一个 tip 是 `personal-bank-user-counts-read-access-worm-evidence.json`，绑定 Java build-context `935e6a95a33621b01e1e04d752a09513c8037cffe807a73fa1ce9850fb5912f0`。静态门禁只接受固定链的最后一个 tip，不扫描目录，也不接受任意报告路径。所有报告仍仅代表获准本地开发参考实例，不确认生产版本，也不创建 Flyway baseline。

## 启动开发 Compose

```bash
cp .env.example .env
docker compose --env-file .env -f compose.dev.yml config --quiet
docker compose --env-file .env -f compose.dev.yml up --build -d
curl --fail http://127.0.0.1:18080/readyz
```

Prometheus 仅监听 Compose 内部网络的 API 管理端口 `9090`，不发布到宿主机；
未来采集器使用 `http://api:9090/actuator/prometheus`。应用端口 `18080`
不会暴露该 Actuator 路径。

阶段 2 初始化卷只承载最小 schema。更新夹具后必须显式销毁该阶段卷再重建；`down --volumes` 会删除阶段 2 本地数据，执行前应人工确认项目名确为 `ti-java-phase2`。
