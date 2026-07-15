# Phase 2 Java 基础骨架验收记录

> 状态：阶段 2 实现与验收门禁已通过；绿色提交由 `../05-progress.md` 记录。本文只记录可复现证据和边界，不把 Java 骨架描述为旧 Flask 的替代实现。

## 实现范围

- 运行基线：Java 25、Maven Wrapper 3.9.16、Spring Boot 4.1.0、Spring MVC、Spring Modulith 2.1.0。
- 模块边界：11 个业务模块（`identity`、`catalog`、`personalbank`、`learning`、`assessment`、`community`、`messaging`、`campus`、`coding`、`intelligence`、`operations`）加 `sharedkernel`、`web`；模块 DAG、公开命名接口和非法依赖负例由测试约束。
- Web 基础：Request ID、统一成功/错误信封、分页与 UTC 时间约定、默认拒绝的安全策略、脱敏结构化日志、`/livez`、`/readyz` 和 Micrometer/Prometheus。
- 数据基础：PostgreSQL 作为事实源，Redis 作为可重建辅助设施；Hibernate 使用 `ddl-auto=validate` 和 `generate-ddl=false`。
- 兼容探针：只在 `catalog` 内部映射旧 `subjects` 的 9 列及其 `plaza_boards` 外键，并通过只读端口读取；不提供 HTTP 路由，不提供写接口。
- 可重复运行：`server/Dockerfile`、`compose.dev.yml`、PostgreSQL/Redis/Testcontainers 夹具和验证脚本均位于本目录内；构建与运行不应读取父目录。

`application-api-shape-status.json` 明确记录：迁移路由数为 **0**，已实现公开业务操作数为 **0**。公开 API 形状、事件负载和业务实现仍属于后续阶段。

## 当前可核验证据

| 门禁 | 当前证据 | 结论 |
| --- | --- | --- |
| Maven `clean verify` | 固定 Java 25 / Maven 3.9.16 容器中有 36 个单元/架构/模块上下文测试与 4 个 Testcontainers 集成测试，共 40 个；failure、error、skip 均为 0；可执行 JAR 不含撤销的 `ActorId` 或事件载荷 class | 已在原目录与独立抽取目录各通过一次 |
| 最小 PostgreSQL/Redis 夹具 | PostgreSQL 18.4 主夹具、PostgreSQL 16.14 兼容夹具、Redis 7.4.7；验证 Hibernate schema、`subjects` 全字段读取、只读角色拒绝 DML/DDL/TEMP，以及 Redis set/get/delete | 已包含在上述 4 个集成测试中 |
| 静态门禁 | `./infra/phase2/verify-static.sh` 严格解析镜像 digest、Compose 拓扑、只读 ACL 与 wormhole 报告新鲜度 | 已通过 |
| 完整本地参考结构 wormhole | `infra/phase2/local-reference-verification.json` 记录获准本地开发实例为 PostgreSQL 18.4、70 表/617 列；隔离恢复、完整只读 ACL、Hibernate validate 与 readiness 通过，Dockerfile 与 Java build-context 哈希均和当前源码一致 | 已通过；生产版本仍为 unknown |
| Docker/Compose 运行态 | 空卷构建后三容器 healthy；`18080` 的 live/readiness 为 200、未声明路由为安全 401、业务端口 metrics 为 404；内部 `9090` 含 `jvm_info`；`25432` 可达，Redis/9090 无宿主映射；API 为 UID 10001、只读根、`cap_drop=ALL`、`no-new-privileges`，重启后恢复健康 | 已通过 |
| 独立抽取 | 仅复制本目录到临时目录，在独立项目名和端口 `18181`/`25533` 下执行静态门禁、`clean verify`、Dockerfile check、镜像构建、Compose 启动与健康/端口检查，结束后清理目录、容器、网络和卷 | 已通过 |

以上结论来自实际命令、测试报告与结构化 wormhole 报告，不以“脚本存在”代替“门禁通过”。阶段绿色提交与下一阶段入口同步写入 `docs/refactor/05-progress.md`。

## 四类验证的区别

1. **静态门禁**检查固定版本、模块/API 合同、配置、Docker/Compose 安全边界和禁止项；它不启动数据库，也不证明运行时可用。
2. **最小夹具测试**使用两张确定性测试表：`subjects` 9 列和仅含主键的 `plaza_boards`。它适合每次 `clean verify`，但不代表完整旧库兼容，更不是 Flyway baseline。
3. **70 表 wormhole**只对显式指定、获准读取的本地非生产参考容器做 schema-only 导出，并恢复到隔离的固定 PostgreSQL 镜像；仓库只保留无 schema、DSN、Secret 的结构化报告。它证明一次本地参考结构兼容，不证明生产结构或版本。
4. **独立抽取验证**只复制本目录后重新构建、测试和启动，用来证明没有软链接、父目录挂载、父目录文件读取或旧 Flask 运行依赖；它不能由原仓库内一次成功构建替代。

Compose 运行态验证是第五个独立门禁：它验证镜像用户、只读根文件系统、健康检查、网络与端口，而不是替代以上任何一项。

wormhole 还执行了三类失败路径：`--report ../AGENTS.md` 被物理路径边界拒绝且原文件哈希不变；源容器名与计划资源冲突时脚本退出且源容器继续运行；验证失败时已有报告不会被提前删除或覆盖。

## 可重复命令

从本目录执行：

```bash
# 不需要本机 JDK
./infra/phase2/verify-static.sh
./infra/phase2/verify-in-maven-container.sh clean verify

# 显式授权的本地参考结构；禁止指向生产
./infra/phase2/verify-local-reference-wormhole.sh \
  --source-container ti-postgres-1 \
  --source-user studyuser \
  --source-db ti_db

# 独立阶段 2 Compose
cp .env.example .env
docker compose --env-file .env -f compose.dev.yml config --quiet
docker compose --env-file .env -f compose.dev.yml up --build -d
curl --fail http://127.0.0.1:18080/livez
curl --fail http://127.0.0.1:18080/readyz
```

固定 Maven 容器验证和 wormhole 都会使用 Docker socket；Docker socket 近似授予执行环境主机 root 控制能力，只能运行受信仓库代码。不得在不受信 CI、共享主机或指向生产容器的上下文中运行这些脚本。

## Compose 网络与端口

- API：宿主机 `127.0.0.1:18080` → 容器 `8080`。
- PostgreSQL：宿主机 `127.0.0.1:25432` → 容器 `5432`。
- Redis：默认只在内部网络监听，不发布宿主端口；`infra/phase2/compose.redis-port.yml` 仅用于显式本地诊断，会发布 `127.0.0.1:26379`。
- Metrics：API 容器内部管理端口 `9090` 的 `/actuator/prometheus`，只 `expose` 给 Compose 内部网络，不映射到宿主机，也不通过 `18080` 提供。
- PostgreSQL、Redis、Maven 构建镜像和 Java 运行时镜像均按 digest 固定；Dockerfile frontend 同样固定 digest。

## 明确未完成

- 生产 PostgreSQL 版本与完整生产 schema 均为 **unknown**；阶段 2 不连接生产，也不能用本地 70 表报告推断生产状态。
- 阶段 2 没有创建 Flyway baseline；正式迁移链属于阶段 8。
- 没有迁移任何业务路由、写命令、认证兼容或业务事务；`subjects` 只是只读内部探针。
- Vue Web 尚未创建，小程序仍是阶段 0 的受控基线；关键用户旅程没有因本阶段而完成。
- Java 骨架与旧 Flask 可以使用不同端口独立运行，但不得共享可写数据库、卷或 Redis，也不存在双写授权。

因此，本阶段的绿色结果只表示“Java 基础骨架可重复验证并可独立启动”，不表示“Ti-Java 已经替代旧系统”。

## 已知非阻断风险

Mockito/Byte Buddy 在 Java 25 测试进程中仍会发出动态 attach 警告；本轮测试结果未受影响，但 JDK 未来默认禁用动态 agent 前必须按 Mockito 官方方案改为显式 `-javaagent`。Maven Wrapper/Jansi 与 Testcontainers/JNA 也会提示未来需显式 native access；这些是后续工具链升级项，不得通过隐藏警告来冒充修复。
