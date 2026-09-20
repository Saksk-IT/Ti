# 生产快照覆盖本机 8000 环境

2026-09-12 已把生产快照直接恢复到现有 `ti-local-demo` 环境，覆盖原演示数据。
访问地址：<http://127.0.0.1:8000>。选择密码登录，使用原生产账号的邮箱或手机号与密码。
用于验证的 `ti-production-restore` 环境已关闭并移除容器，不再提供 `18080` 入口。

## 恢复内容

| 项目 | 本机位置或结果 |
| --- | --- |
| PostgreSQL | 原 `ti-local-demo_local-postgres` 数据卷内的 `ti_demo` 数据库 |
| Redis | 原 `ti-local-demo_local-redis` 数据卷，快照已转换为 AOF |
| 上传文件、实例数据和日志 | 原 `ti-local-demo_local-data` 数据卷，应用挂载到 `/data` |
| 私有启动配置 | `D:\GitHub\Ti\.env.local-restored`，Git 已忽略并限制本机文件访问权限 |
| 生产源码、历史备份、证书和系统配置 | 仍完整保存在 `backups/production-migration-20260912/` 的导出归档中 |

现有五个服务均已启动：Web、Worker、PostgreSQL、Redis、Backup。
Docker Desktop 运行时，容器按 `unless-stopped` 策略自动重启；持久数据不依赖临时容器。
保留当前本地代码、原数据卷名称和 Web 8000、PostgreSQL 55432 端口。

## 验证结果

- 覆盖后、迁移前逐表核对：67 张表、35,233 条记录与生产快照一致。
- 已执行当前本地代码需要的四步迁移，数据库版本为 `f5b6c7d8e9f0`，当前共 70 张表。
- 219 个生产上传文件大小和 SHA256 全部一致；215 个通过登录后 HTTP 下载校验，4 个聊天附件按会话成员权限返回 403，文件本体完整。
- 深度健康检查：数据库、Redis 均正常。
- 保留 41 个生产用户；使用原管理员凭据完成真实密码登录，登录后首页返回 HTTP 200。
- Redis 载入 122 个有效键并启用 AOF，已过期的键按原时间戳自然失效。

验证报告：`backups/production-migration-20260912/LOCAL-8000-VERIFIED.json`。

## 本机配置差异

本地数据库继续使用原 `studyuser` 角色和本地连接密码；业务用户密码、应用签名密钥来自生产备份。
本地仍禁用短信和邮件，没有导入生产外部服务凭据。生产归档中的完整配置保留，未覆盖 Windows 系统配置。

## 覆盖前备份

原本地数据备份位于 `backups/production-migration-20260912/before-overwrite-8000/`：

- `ti_demo.dump`、`globals.sql`：覆盖前数据库及全局角色。
- `data.tar.gz`、`postgres.tar.gz`、`redis.tar.gz`：停止服务后三个原数据卷的完整备份。
- `containers.private.json`、`SHA256SUMS`：原容器配置及文件校验清单。

冷备压缩包已完成完整性检查，可用于回退覆盖操作。

## 启动与停止

原启动脚本自动优先读取 `.env.local-restored`，在该配置存在时跳过演示数据填充和演示账号验证：

```powershell
Set-Location D:\GitHub\Ti
.\scripts\start-local-demo.ps1
```

无需重新构建时，可以直接管理现有服务：

```powershell
docker compose --env-file .env.local-restored -f compose.dev.yml -f compose.local.yml up -d --wait
docker compose --env-file .env.local-restored -f compose.dev.yml -f compose.local.yml ps
docker compose --env-file .env.local-restored -f compose.dev.yml -f compose.local.yml stop
```

配置文件与归档含生产密钥，不提交至 Git。不要删除现有 `ti-local-demo_local-*` 数据卷。

本机恢复的是导出时的在线快照，不会自动同步旧服务器后续新增的数据。
