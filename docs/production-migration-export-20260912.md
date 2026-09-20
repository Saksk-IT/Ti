# 2026-09-12 生产数据迁移导出

本次采用在线导出，旧服务器继续提供服务。归档代表导出时的数据，正式切换前需要停止业务写入并补做最终同步。

## 交付位置与内容

本地备份位于 Git 忽略的 `backups/production-migration-20260912/`。
归档文件为 `ti-migration-20260912.tar`，解包后根目录为 `ti-migration-20260912/`。
备份包含业务数据、环境变量、数据库角色密码哈希和 HTTPS 私钥，应按生产密钥文件保管。
这些数据文件不提交至 Git。

| 文件 | 内容 |
| --- | --- |
| `ti_db.dump` | PostgreSQL 16 业务数据库，自定义格式，包含建库信息 |
| `postgres.dump` | PostgreSQL 默认数据库 |
| `postgres-globals.sql` | 数据库角色、权限和全局对象 |
| `redis.rdb` | Redis 7 在线复制快照，已通过 `redis-check-rdb` |
| `project.tar.gz` | `/opt/ti` 项目目录，包含源码、Git 历史、生产环境配置、上传文件、实例目录、日志和历史备份 |
| `host-config.tar.gz` | Nginx、Let's Encrypt 证书及续期配置、systemd、定时任务、防火墙、Docker 配置等存在的相关目录 |
| `docker-images.tar.gz` | 当前生产容器使用的四个精确镜像 |
| `metadata/` | 容器和镜像详情、解析后的 Compose 配置、系统信息、逐表行数、上传文件校验清单 |
| `RESTORE-VERIFIED.json` | 隔离容器中的数据库恢复验证结果 |
| `MANIFEST.json`、`SHA256SUMS` | 导出范围和各文件 SHA256 |

运行中的 PostgreSQL 数据目录和 Redis AOF 目录没有直接复制；它们分别由一致性逻辑备份和 Redis RDB 快照替代。不要把归档中的历史备份当成本次数据库快照。

生产源码提交为 `ae70f84f626c3890c8c296797a514269e495c721`。恢复时以归档中的生产源码、Compose 文件、环境配置和镜像为准。

## 已执行的数据库验证

使用业务数据库的同一个 PostgreSQL 导出快照，执行 `pg_dump` 并记录逐表行数。
随后在无网络、无宿主机端口、使用临时内存数据目录的 PostgreSQL 容器中恢复全局角色和两个数据库。
业务库 67 张表、35,233 条记录逐表一致。验证容器已移除，生产数据库没有执行恢复操作。

上传文件和实例目录在打包前后分别计算哈希，并确认无变化。
Redis 快照与数据库、文件系统不是同一原子快照，不能将本次在线导出当成停写后的最终切换备份。

## 新服务器恢复顺序

1. 验证外层归档 SHA256，解包后在归档根目录执行 `sha256sum -c SHA256SUMS`。
2. 准备 Ubuntu 24.04、Docker 和 Compose。在新的空目录中解包 `project.tar.gz`，保留 Linux 权限。
3. 执行 `gzip -dc docker-images.tar.gz | docker image load`，依据 `metadata/images.json` 的 `RepoTags` 为载入的镜像恢复标签。启动 Compose 时使用 `--pull never`，避免 `latest` 标签引入其他版本。
4. 在空的 PostgreSQL 数据目录中，以临时管理员角色启动同版本隔离恢复容器，恢复 `postgres-globals.sql`；使用 `pg_restore --exit-on-error --create` 恢复业务库，另行恢复默认数据库。核对逐表行数后，关闭临时容器，让生产 Compose 挂载该数据目录。
5. 将 `redis.rdb` 作为 `dump.rdb` 放入空的 Redis 数据目录。先以 `appendonly no` 载入 RDB，再开启 AOF 并等待重写成功。确认键数据后关闭临时 Redis，再让生产 Compose 接管。不要直接把 RDB 放到带有旧 AOF 的目录中，AOF 的加载优先级更高。
6. 保留原生产 `SECRET_KEY` 及其他应用密钥，检查上传目录权限、数据库连接、域名和端口。按需恢复 Nginx 与证书配置，不要整体覆盖新服务器的 systemd 或防火墙配置。
7. 启动应用，检查健康状态、登录、题库、课表、上传文件和后台任务。切换 DNS 前停写并完成最终同步；确认新端业务正确后再停用旧服务器。

这是迁移专用归档，不符合现有 `scripts/restore.sh` 的 `database.sql` 目录格式，不能直接交给该脚本恢复。
