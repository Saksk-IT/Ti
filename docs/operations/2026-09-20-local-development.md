# 2026-09-20 本机 Docker Compose 开发环境

本机使用当前仓库的 Flask 源码和开发模式，数据来自新生产服务器 `38.76.217.228` 的最新在线快照。未启动 Ti-Java。生产服务在导出期间保持运行，本机数据为独立副本，不自动同步生产后续改动。

## 访问与管理

- Web：<http://127.0.0.1:8000>，使用原生产账号的邮箱或手机号和密码登录。
- PostgreSQL：`127.0.0.1:55432`，数据库 `ti_db`；本机连接凭据保存在 `.env.local-restored`。
- Compose 项目：`ti-local-dev`。
- 源码目录 `app`、`static`、`templates`、`migrations` 和 `run.py` 挂载到容器；Flask 启用 DEBUG 和自动重载。

在仓库根目录启动或重新构建：

```sh
./scripts/start-local-dev.sh
```

该脚本构建开发镜像、启动数据库和 Redis、应用数据库迁移，然后启动 Web 和 Worker。它不会重新导入快照、创建演示账号或重置用户密码。

无需构建时，直接管理现有服务：

```sh
docker compose --env-file .env.local-restored -f compose.dev.yml -f compose.local.yml -f compose.restored.yml up -d --wait
docker compose --env-file .env.local-restored -f compose.dev.yml -f compose.local.yml -f compose.restored.yml ps
docker compose --env-file .env.local-restored -f compose.dev.yml -f compose.local.yml -f compose.restored.yml logs --tail 100 web
docker compose --env-file .env.local-restored -f compose.dev.yml -f compose.local.yml -f compose.restored.yml stop
```

Docker Desktop 运行时，服务采用 `unless-stopped` 重启策略。数据保存在以下独立命名卷中；原仓库 `var/` 中已有的数据保持不变：

- `ti-local-dev_local-postgres`
- `ti-local-dev_local-redis`
- `ti-local-dev_local-data`

不要使用 `down -v` 删除这些数据卷。

## 快照与验证

数据库快照时间为 **2026-09-20 21:26:57（北京时间）**。数据库导出与表内容摘要使用同一个 PostgreSQL 导出快照，做法参考 [PostgreSQL 16 的 pg_dump 官方说明](https://www.postgresql.org/docs/16/app-pgdump.html)。

恢复前后核对结果：

- 70 张表、35,293 条记录的行数及内容摘要全部一致。
- 66 个序列状态全部一致。
- 43 个用户、40 个个人题库、96 道公共题目、7,809 道个人题目均已保留。
- 数据库版本为 `f5b6c7d8e9f0`。
- Redis RDB 校验通过，恢复时载入 133 个有效键，转换为 AOF 并重启后仍为 133 个；过期键随后按原 TTL 自然失效。

- 导出包中的 11 个文件 SHA-256 全部一致；归档内 232 个上传文件及 28 个历史备份相关文件，共 260 个文件的大小与 SHA-256 全部一致。
- 上传、实例目录和日志已恢复到本机应用数据卷，完整历史备份同时保留在 `backups/local-dev-20260920/extracted/backups/`。
- Web、Worker、PostgreSQL、Redis 四个服务均已启动；深度健康检查中的数据库、Redis 和应用状态全部为 `true`。
- 使用原生产管理员账号和密码完成真实登录；首页、用户管理、科目管理、备份设置及登录方式接口均返回 HTTP 200。
- 通过登录会话访问全部 232 个上传文件：228 个可访问文件的响应 SHA-256 与磁盘文件一致，4 个聊天附件按原会话权限返回 HTTP 403，文件本体已通过归档 SHA-256 校验。
- Worker 仅监听本机专用 `ti-local-dev` 队列；默认服务列表中没有备份调度器。
- 触发 `app/__init__.py` 的文件时间变化后，Werkzeug 检测到变更并自动重载；重载后的深度健康检查继续通过。

这是在线开发快照，PostgreSQL、Redis 与文件系统不是跨系统的同一原子快照。上传、实例及历史备份在归档前后核对内容，确认导出期间未发生变化。

## 本机配置差异

- 保留生产应用签名密钥及加密密钥，确保原用户凭据、加密设置与数据可继续使用。
- PostgreSQL 使用单独生成的本机连接密码，应用仅连接 Compose 内部的 `postgres` 和 `redis`。
- 校验原始数据库内容后，仅在本机副本将 `mail_enabled`、`sms_enabled` 设为 `false`，将 `mail_console_output`、`sms_console_output` 设为 `true`。数据库中的配置优先于环境变量，因此同时设置本机数据库和私有环境文件。
- 本机 RQ 队列名为 `ti-local-dev`，不会消费快照中保留的生产队列任务；原开发配置的同步任务行为保持不变。
- 云备份调度器置于 `cloud-backup` profile，默认不启动；生产备份配置和历史记录完整保留。
- Web 和 PostgreSQL 仅绑定回环地址，Redis 不发布宿主机端口。

## 私有恢复资料

全部导出及验证资料保存在 Git 忽略的 `backups/local-dev-20260920/`，目录权限为 `0700`：

- `database.dump`：最新业务库完整逻辑备份。
- `postgres.dump`、`postgres-globals.sql`：默认数据库与全局角色资料；本机保留自己的数据库连接凭据。
- `redis.rdb`：完整在线 Redis 快照。
- `runtime-files.tar.gz`：上传、实例目录、应用日志及全部历史备份。
- `runtime-only.tar.gz`：从同一归档提取的应用运行文件，用于本机数据卷恢复。
- `source.env.production`、`runtime-secrets.json`：原生产配置和数据解密资料，仅供本机私有恢复使用。
- `MANIFEST.json`、`SHA256SUMS.json`、`metadata/`：快照范围、文件校验和逐表核对结果。

`.env.local-restored` 权限为 `0600`。私有环境文件、数据库、密钥和用户文件均不提交至 Git。
