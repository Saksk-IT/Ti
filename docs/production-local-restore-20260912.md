# 生产快照本机恢复记录

2026-09-12 已将生产导出完整恢复为独立 Docker Compose 环境 `ti-production-restore`。

访问地址：<http://127.0.0.1:18080>。使用原生产账号的邮箱或手机号与密码登录，账号密码没有重置。
原有 `ti-local-demo` 环境继续使用原数据卷和端口。

## 恢复内容

| 项目 | 本机位置或结果 |
| --- | --- |
| PostgreSQL | `ti-production-restore_postgres` 数据卷；已恢复全局角色及 `ti_db`、`postgres` 数据库 |
| Redis | `ti-production-restore_redis` 数据卷；RDB 已载入并转换为 AOF |
| 完整项目 | `ti-production-restore_project` 数据卷内 `/opt/ti`；含源码、Git 历史、配置、静态资源、上传文件、日志和历史备份 |
| Linux 主机配置与证书 | `ti-production-restore_host-config` 数据卷，保留原目录结构供迁移使用 |
| 本地新生成的自动备份 | `ti-production-restore_local-backups` 数据卷；与导出的历史备份分别存放 |
| 运行镜像 | 使用归档中生产实际运行的四个镜像 ID，不自动拉取 `latest` |
| 本地配置及验证报告 | `D:\GitHub\Ti\backups\production-migration-20260912\local-restore\` |

六个服务均已启动：Nginx、Web、Worker、PostgreSQL、Redis、Backup。
Docker Desktop 运行时，容器按 `unless-stopped` 策略自动重启；持久数据不依赖临时容器。

## 验证结果

- 数据库恢复后、启动应用前逐表核对：67 张业务表、35,233 条记录与备份快照一致。
- 上传文件：219 个文件的大小及 SHA256 与备份完全一致；全部通过本地 HTTP 下载校验。
- 深度健康检查：数据库、Redis 均正常。
- 使用备份配置中的原管理员凭据完成真实密码登录，登录后首页返回 HTTP 200。
- Redis 载入 122 个有效键；8 个带绝对到期时间的键已自然过期。未改写快照中的到期时间。
- Worker 正常监听本地队列，Backup 已成功生成一份本地备份。

验证报告：`backups/production-migration-20260912/local-restore/LOCAL-RESTORE-VERIFIED.json`。

## 本机配置差异

仅在 `127.0.0.1:18080` 提供 HTTP，保留原生产 HTTPS 证书归档，不接管生产域名或 Windows 系统配置。
本地 HTTP 会话的 `SESSION_COOKIE_SECURE` 设为 `false`。

Web、Worker、数据库、Redis 和 Backup 位于禁止外网访问的 Docker 内部网络；Nginx 同时连接本机入口网络。
本地副本禁用邮件、短信和 Sentry 上报，因此依赖微信、短信、邮件或其他外部服务的功能不会向生产服务发送请求。
业务数据库内的原设置、账户信息及应用密钥保留在恢复数据和原始归档中。

初始化 PostgreSQL 使用的本地 `migration_restore_admin` 角色是系统对象所有者，恢复完成后已设为 `NOLOGIN`；应用使用原生产数据库账号。

## 启动与停止

在 PowerShell 中执行：

```powershell
Set-Location D:\GitHub\Ti
$restoreCompose = 'backups/production-migration-20260912/local-restore/compose.restore.json'
docker compose -p ti-production-restore -f $restoreCompose ps
docker compose -p ti-production-restore -f $restoreCompose up -d --pull never
docker compose -p ti-production-restore -f $restoreCompose stop
```

以上命令只管理本次恢复环境。不要删除 `ti-production-restore_*` 数据卷。
配置文件与归档含生产密钥，保存在 Git 忽略且限制访问权限的 `backups` 目录中。

本机恢复的是导出时的在线快照，不会自动同步旧服务器后续新增的数据。
