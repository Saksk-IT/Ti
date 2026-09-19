# 2026-09-20 生产服务器迁移记录

本次迁移以旧服务器实际运行的 Flask 生产镜像为准，不构建或运行 Ti-Java 重构版本，也不部署本机工作区中的开发改动。

## 迁移范围

| 项目 | 配置 |
| --- | --- |
| 旧服务器 | `154.64.252.241` |
| 新服务器 | `38.76.217.228` |
| 部署目录 | `/opt/ti` |
| Compose 项目 | `ti`，配置为 `compose.prod.yml` |
| 生产代码提交 | `9e4dccd` |
| 应用镜像 | `ghcr.io/saksk-it/ti:9e4dccd-final` |
| 应用镜像 ID | `sha256:2fcbd1a5f5318848df8755639638b803d4630a7f093117cc4b6d2a068b0a52c1` |
| 服务 | Nginx、Web、RQ Worker、PostgreSQL、Redis、备份调度器 |
| 数据 | PostgreSQL 全集群、Redis RDB/AOF、上传、实例目录、应用日志、历史备份 |
| 宿主机配置 | Nginx、HTTPS 证书及续期配置；新机配置 Docker 自启动、时间同步、防火墙和 2 GiB swap |

生产 `.env.production` 和加密所需密钥通过 SSH 原样迁移，未写入本记录。数据库、Redis 和应用镜像均直接从旧机导出，以镜像 ID 和文件摘要验证，避免可变标签指向其他版本。

## 一致性与切换方式

1. 旧服务运行时预复制镜像、配置、静态文件及历史备份。
2. 将旧入口置为维护状态，停止 Web、Worker、备份调度器和容器 Nginx。
3. 导出 PostgreSQL 逻辑备份、全表内容摘要、序列状态及 Redis 键摘要。
4. 正常关闭 PostgreSQL 与 Redis，确认 PostgreSQL 集群状态为 `shut down`，再复制完整持久化目录。
5. 在新机启动前核对文件 SHA-256；先启动数据库和 Redis，核对恢复后的数据，再启动业务容器。
6. 新机验证通过后，将旧宿主机 Nginx 改为通过验证证书的 HTTPS 转发到新机。旧机业务容器保持停止，避免两台服务器分别写入数据。

文件级数据库备份遵循 [PostgreSQL 16 官方备份说明](https://www.postgresql.org/docs/16/backup-file.html)：正常停止数据库后复制完整集群，同时保留逻辑备份作为独立恢复手段。

## 验证结果

迁移已完成，新机为唯一生产写入端。以下时间均为北京时间（UTC+8）：

| 阶段 | 时间 |
| --- | --- |
| 旧入口进入维护、开始停写 | 2026-09-20 03:40:26 |
| 完成一致性快照 | 2026-09-20 03:42:08 |
| 新机数据与内部服务验收通过 | 2026-09-20 03:45:09 |
| 旧入口转发到新机并恢复访问 | 2026-09-20 03:51:38 |

| 检查项 | 结果 |
| --- | --- |
| 镜像 | 应用、PostgreSQL、Redis、Nginx 四个实际镜像 ID 与旧机完全相同 |
| 运行配置 | 六个容器的环境变量摘要、命令、入口和挂载与旧机一致 |
| 持久化与部署文件 | 启动前核对 3,530 个 SHA-256，全部一致；包括完整数据库持久化目录、上传及历史备份 |
| PostgreSQL | 70 张表的行数及全表内容摘要、66 个序列状态全部一致；版本为 16.14 |
| 关键数据计数 | 43 个用户、40 个个人题库、96 道公共题目、7,809 道个人题目 |
| 数据库迁移版本 | `f5b6c7d8e9f0` |
| Redis | 版本为 7.4.9；冻结时 94 个键，恢复时 93 个键，1 个按原 TTL 自然过期，其余内容及过期时间一致 |
| HTTP / HTTPS | 新机直连、旧机转发、Cloudflare 公网三条路径的五个路由状态全部符合迁移前基线，共 15 项 |
| 深度健康检查 | `/api/ping?deep=1` 中 `db`、`redis`、`pong` 均为 `true` |
| 静态及上传文件 | 六个样本分别通过三条路径访问，共 18 次校验，响应内容 SHA-256 与磁盘原文件全部一致 |
| 后台服务 | RQ Worker 已监听原队列，备份调度器运行；验收时六个容器日志均未发现 ERROR、FATAL 或 Traceback |
| 服务恢复能力 | Docker、宿主机 Nginx 和 Certbot timer 已启用自启动；六个容器均为 `unless-stopped`，验收时重启次数为 0 |
| 主机配置 | 时间同步成功；UFW 仅开放 SSH、HTTP、HTTPS；应用容器入口仅绑定 `127.0.0.1:8080`；数据库及 Redis 不向公网发布端口 |
| 旧服务器 | 六个业务容器均正常退出（退出码 0），仅宿主机 Nginx 提供临时转发 |

验证路由为 `/`（302），以及 `/login`、`/api/ping`、`/api/ping?deep=1`、`/api/auth/login-methods`（均为 200）。HTTPS 检查正常校验证书。旧机反向代理使用 TLS、SNI 和上游证书校验，证书链校验深度设为 3。

迁移期间新机首次 Nginx reload 后的即时探测曾读到旧维护配置；随后旧机上游证书链校验深度不足导致短暂 502。修复并复测通过后于上述时间恢复入口，未重新开启旧数据库写入。

## 证书与续期

- 主域名 `saksk.top` 使用单独签发的证书，路径为 `/etc/letsencrypt/live/saksk.top-primary/`，到期时间为 `2026-12-18 18:58:10 UTC`。
- 主域名通过 webroot 完成 HTTP-01 验证；挑战目录为 `/var/lib/letsencrypt`，新机 HTTP 和 HTTPS 均提供挑战文件。
- `certbot renew --cert-name saksk.top-primary --dry-run --run-deploy-hooks` 已成功完成，包含 Nginx 配置检查及 reload hook；`certbot.timer` 已启用并运行。
- 备用域名 `dljrze.cc.cd` 的 Nginx 配置和原证书保留，证书有效期至 2026-11-20；指定新机 IP 的 HTTPS 深度健康检查通过。
- 备用域名当前缺少 DNS 解析，原双域名证书的续期配置已归档到 `/root/ti-migration-20260920/saksk.top.legacy-renewal.conf`，避免影响主域名续期。备用域名恢复 DNS 后，需要为其单独签发证书并更新对应 Nginx 证书路径。
- 旧机证书续期定时器已停用。跨机迁移临时 SSH 授权及新机专用私钥均已删除。

## DNS 交接

按照用户要求，Cloudflare DNS 由用户手动切换。将 `saksk.top` 使用的源站 A 记录指向 `38.76.217.228`，保留现有代理和 TLS 设置。若存在直接指向旧服务器的其他 A/AAAA 记录，也应核对。

**请在旧服务器到期前完成 DNS 切换。** DNS 切换前，旧服务器的临时反向代理仍依赖旧服务器在线。确认 Cloudflare 已使用新源站、实际业务正常后，再停用旧服务器。切换期间各入口均访问同一份新机数据。

备用域名 `dljrze.cc.cd` 在迁移前没有可用的 A 记录；两台公共解析器均返回空答案。其 DNS 恢复由域名管理方处理。

## 恢复资料

迁移资料保存在两台服务器的 `/root/ti-migration-20260920/`，目录仅 root 可访问。主要文件：

- `images.tar.gz`：本次实际运行镜像及独立校验文件。
- `host-config.tar.gz`：原 Nginx 和 Let’s Encrypt 配置。
- `database.dump`、`database-globals.sql`：停写后的 PostgreSQL 逻辑备份。
- `runtime-snapshot.tar.gz`：正常停机后的完整 `var` 快照。
- `db-frozen.txt`、`redis-frozen.json`、`source-files.sha256`：数据与文件校验依据。
- `ti.conf.original`：旧服务器原入口配置。

新机另保留 `host-config-final.tar.gz` 及 SHA-256、`ti.conf.final`、`db-restored.txt`、`redis-verification.json`、`runtime-config-verification.json`、`routes-final.json`、`assets-final.json` 和 `certificate-renewal-test.log`，用于核对最终配置及验收结果。历史备份保留在原 `/opt/ti/var/` 持久化目录中，现有备份调度器已迁移运行。

**新机接收生产写入后，不能直接启动旧数据库回退。** 必须先停止新机写入，将最新数据反向同步到旧机并验证，再切回入口。`rollback-before-cutover.sh` 仅用于首次切换前，切换完成标记会阻止直接运行。

服务器密码、SSH 私钥、业务密钥、数据库备份和用户文件不得提交到 Git。

## 日常检查

```sh
cd /opt/ti
docker compose --env-file .env.production -f compose.prod.yml ps
curl --resolve saksk.top:443:127.0.0.1 'https://saksk.top/api/ping?deep=1'
systemctl status nginx docker certbot.timer --no-pager
```

本次仅同步迁移报告到 Git 主分支；服务器继续运行原生产镜像与原生产代码提交。
