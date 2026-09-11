# 本机 Docker Compose 演示

## Windows 启动

先安装并启动 Docker Desktop，启用 WSL 2 引擎。首次启用 Windows 的
`VirtualMachinePlatform` 功能后需要重启电脑。

在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-demo.ps1
```

脚本使用当前源码构建镜像，启动 PostgreSQL 和 Redis，执行数据库迁移，
初始化演示数据，再启动 Web、Worker 和备份调度服务，并验证管理员登录。
首次构建需要联网下载基础镜像及 Python 依赖。

默认访问地址：<http://localhost:8000>。端口被占用时可指定：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-demo.ps1 -Port 8001 -PostgresPort 55433
```

## 演示账号

| 角色 | 登录邮箱 | 手机号 | 密码 |
| --- | --- | --- | --- |
| 超级管理员 | admin@example.dev | 13900000001 | DevPass123! |
| 科目管理员 | subject_admin@example.dev | 13900000002 | DevPass123! |
| 通知管理员 | notification_admin@example.dev | 13900000003 | DevPass123! |
| 教师 | teacher@example.dev | 13900000004 | DevPass123! |
| 学生 A | student_a@example.dev | 13900000005 | DevPass123! |
| 学生 B | student_b@example.dev | 13900000006 | DevPass123! |

登录时填写邮箱或手机号。另有 `locked_user@example.dev` 用于演示锁定状态，不能正常登录。
这些是公开的本机演示凭据，仅用于绑定 `127.0.0.1` 的演示环境。

演示内容包含两个公共科目及四道题、七个用户、九个个人题库及十八道题，
以及论坛帖子与互动、私信、刷题记录、考试记录、通知和关注关系。

## 数据与维护

`compose.local.yml` 叠加在现有开发编排上，`local-demo.env.example` 提供演示配置。
独立的 `ti-local-demo` Compose 项目使用命名数据卷，不使用现有 `var/` 数据目录。
已有 `.env` 不需要修改。

初始化使用 `--empty-only`：已有初始化标记时直接跳过；已有用户但没有标记时终止，
避免清空已有数据。请勿直接执行不带该参数的开发重置脚本。

查看状态或停止容器（保留数据）：

```powershell
docker compose --env-file local-demo.env.example -f compose.dev.yml -f compose.local.yml ps
docker compose --env-file local-demo.env.example -f compose.dev.yml -f compose.local.yml down
```

使用自定义端口后，再执行维护命令时应先设置同样的 `WEB_PORT` 和 `POSTGRES_PORT` 环境变量。
