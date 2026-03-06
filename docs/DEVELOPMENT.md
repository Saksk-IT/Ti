# 开发环境配置说明

本项目使用 Docker Compose 进行本地开发，提供完整的开发环境和自动备份功能。

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <仓库地址>
cd Ti

# 复制环境变量文件
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件，配置必填项：

```ini
# 微信小程序（必填）
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret

# AI 服务（必填）
DASHSCOPE_API_KEY=your_api_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen-plus

# 备份配置（可选）
BACKUP_INTERVAL=86400          # 备份间隔（秒），默认 24 小时
BACKUP_RETENTION_DAYS=7        # 保留天数，默认 7 天
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker compose -f compose.dev.yml up -d

# 查看服务状态
docker compose -f compose.dev.yml ps

# 查看日志
docker compose -f compose.dev.yml logs -f
```

### 4. 初始化数据库

```bash
# 进入 web 容器
docker compose -f compose.dev.yml exec web bash

# 运行数据库迁移
flask db upgrade

# 退出容器
exit
```

### 5. 访问应用

- Web 应用: http://localhost:8000
- 健康检查: http://localhost:8000/api/ping
- PostgreSQL: localhost:5432 (studyuser/studypass/ti_db)

## 服务架构

### 服务列表

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| web | saksk-ti:dev | 8000 | Flask Web 应用（热重载） |
| worker | saksk-ti:dev | - | RQ 后台任务队列 |
| postgres | postgres:16-alpine | 5432 | PostgreSQL 数据库 |
| redis | redis:7-alpine | - | Redis 缓存/队列 |
| backup | postgres:16-alpine | - | 自动备份服务 |

### 资源限制

| 服务 | CPU 限制 | 内存限制 | CPU 预留 | 内存预留 |
|------|----------|----------|----------|----------|
| web | 2.0 核 | 1G | 0.5 核 | 512M |
| worker | 1.0 核 | 512M | 0.25 核 | 256M |
| postgres | 2.0 核 | 512M | 0.5 核 | 256M |
| redis | 0.5 核 | 128M | 0.25 核 | 64M |
| backup | 0.25 核 | 128M | 0.1 核 | 64M |

### 数据持久化

所有数据挂载到宿主机 `./var/` 目录：

```
./var/
├── postgres/          # PostgreSQL 数据文件
├── redis/             # Redis 持久化文件
├── uploads/           # 用户上传文件
│   ├── avatars/      # 用户头像
│   ├── forum/        # 论坛图片
│   ├── question_images/  # 题目图片
│   └── chat/         # 聊天文件
├── instance/          # Flask 实例数据
└── logs/              # 应用日志
```

## 日常开发工作流

### 代码修改

代码修改后自动热重载，无需重启：

```bash
# 修改代码
vim app/modules/xxx/xxx.py

# Flask 自动检测并重载
# 查看重载日志
docker compose -f compose.dev.yml logs -f web
```

### 数据库迁移

```bash
# 进入容器
docker compose -f compose.dev.yml exec web bash

# 创建迁移
flask db migrate -m "描述"

# 应用迁移
flask db upgrade

# 回滚迁移
flask db downgrade

# 退出容器
exit
```

### 查看日志

```bash
# 所有服务
docker compose -f compose.dev.yml logs -f

# 特定服务
docker compose -f compose.dev.yml logs -f web
docker compose -f compose.dev.yml logs -f worker
docker compose -f compose.dev.yml logs -f postgres
docker compose -f compose.dev.yml logs -f backup
```

### 重启服务

```bash
# 重启所有服务
docker compose -f compose.dev.yml restart

# 重启特定服务
docker compose -f compose.dev.yml restart web
docker compose -f compose.dev.yml restart worker
```

### 停止服务

```bash
# 停止所有服务
docker compose -f compose.dev.yml down

# 停止并删除数据（慎用！）
docker compose -f compose.dev.yml down -v
```

### 重建镜像

代码依赖变更后需要重建镜像：

```bash
# 重建并启动
docker compose -f compose.dev.yml up -d --build

# 仅重建不启动
docker compose -f compose.dev.yml build
```

## 自动备份功能

### 备份内容

- ✅ **数据库**：完整的 PostgreSQL 数据库
- ✅ **上传文件**：用户头像、题目图片、论坛图片等
- ✅ **实例数据**：Flask 实例配置和数据
- ✅ **日志文件**：最近 7 天的应用日志
- ✅ **备份清单**：详细的备份内容清单

### 备份行为

- **首次启动立即备份**：容器启动后立即执行一次完整备份
- **定时自动备份**：按照 `BACKUP_INTERVAL` 间隔自动备份（默认 24 小时）
- **自动清理旧备份**：保留最近 `BACKUP_RETENTION_DAYS` 天的备份（默认 7 天）
- **备份文件格式**：`backup_YYYYMMDD_HHMMSS.tar.gz`
- **备份位置**：`./backups/` 目录

### 备份文件结构

```
backup_20260306_120000.tar.gz
├── database.sql              # 数据库备份
├── uploads/                  # 上传文件
│   ├── avatars/             # 用户头像
│   ├── forum/               # 论坛图片
│   └── question_images/     # 题目图片
├── instance/                 # 实例数据
├── logs/                     # 日志文件（最近7天）
└── MANIFEST.txt             # 备份清单
```

### 查看备份

```bash
# 查看备份文件
ls -lh backups/

# 查看备份服务日志
docker compose -f compose.dev.yml logs -f backup

# 查看备份内容清单
tar -tzf backups/backup_20260306_120000.tar.gz

# 查看备份清单文件
tar -xzf backups/backup_20260306_120000.tar.gz backup_20260306_120000/MANIFEST.txt -O
```

### 手动触发备份

```bash
# 重启备份服务会立即执行一次备份
docker compose -f compose.dev.yml restart backup

# 查看备份日志
docker compose -f compose.dev.yml logs -f backup
```

### 恢复备份

```bash
# 1. 解压备份文件
tar -xzf backups/backup_20260306_120000.tar.gz

# 2. 停止服务
docker compose -f compose.dev.yml stop web worker

# 3. 恢复数据库
docker compose -f compose.dev.yml exec -T postgres \
  psql -U studyuser -d ti_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose -f compose.dev.yml exec -T postgres \
  psql -U studyuser -d ti_db < backup_20260306_120000/database.sql

# 4. 恢复上传文件
rm -rf var/uploads/*
cp -r backup_20260306_120000/uploads/* var/uploads/

# 5. 恢复实例数据
rm -rf var/instance/*
cp -r backup_20260306_120000/instance/* var/instance/

# 6. 重启服务
docker compose -f compose.dev.yml start web worker

# 7. 清理临时文件
rm -rf backup_20260306_120000
```

## 性能监控

### 查看资源使用

```bash
# 实时监控所有容器
docker stats

# 查看特定服务
docker stats ti-web-1 ti-postgres-1 ti-backup-1
```

### 查看磁盘使用

```bash
# 数据目录
du -sh var/*

# 备份目录
du -sh backups/

# Docker 占用
docker system df
```

### 查看数据库连接

```bash
docker compose -f compose.dev.yml exec postgres \
  psql -U studyuser -d ti_db -c "SELECT count(*) FROM pg_stat_activity;"
```

### 查看 Redis 内存

```bash
docker compose -f compose.dev.yml exec redis redis-cli info memory
```

## 数据库管理

### 连接数据库

```bash
# 使用 psql 连接
docker compose -f compose.dev.yml exec postgres \
  psql -U studyuser -d ti_db

# 查看所有表
docker compose -f compose.dev.yml exec postgres \
  psql -U studyuser -d ti_db -c "\dt"

# 执行 SQL 查询
docker compose -f compose.dev.yml exec postgres \
  psql -U studyuser -d ti_db -c "SELECT * FROM users LIMIT 10;"
```

### 数据库性能参数

PostgreSQL 已配置性能参数：
- `shared_buffers=128MB`
- `work_mem=4MB`
- `max_connections=50`

### Redis 配置

Redis 已配置内存限制：
- `maxmemory=64mb`
- `maxmemory-policy=allkeys-lru`
- `appendonly=yes`（持久化）

## 日志管理

### 日志轮转

所有服务配置了日志轮转：
- 单个日志文件最大 10MB
- 保留最近 3 个日志文件
- 自动清理旧日志

### 查看容器日志

**Linux/macOS:**
```bash
# 实时查看所有日志
docker compose -f compose.dev.yml logs -f

# 查看最近 100 行
docker compose -f compose.dev.yml logs --tail=100

# 查看特定时间范围
docker compose -f compose.dev.yml logs --since 2h

# 筛选关键词
docker compose -f compose.dev.yml logs -f web | grep -E "error|warning"
```

**Windows PowerShell:**
```powershell
# 实时查看所有日志
docker compose -f compose.dev.yml logs -f

# 查看最近 100 行
docker compose -f compose.dev.yml logs --tail=100

# 查看特定时间范围
docker compose -f compose.dev.yml logs --since 2h

# 筛选关键词
docker compose -f compose.dev.yml logs -f web | Select-String -Pattern "error|warning"
```

### 查看应用日志

**Linux/macOS:**
```bash
# 应用日志位于 var/logs/
ls -lh var/logs/

# 查看最新日志
tail -f var/logs/app.log

# 筛选错误日志
grep -i error var/logs/app.log
```

**Windows PowerShell:**
```powershell
# 应用日志位于 var/logs/
Get-ChildItem var/logs/

# 查看最新日志
Get-Content var/logs/app.log -Wait -Tail 50

# 筛选错误日志
Select-String -Path var/logs/app.log -Pattern "error" -CaseSensitive:$false
```

## 故障排查

### 服务无法启动

**Linux/macOS:**
```bash
# 查看服务状态
docker compose -f compose.dev.yml ps

# 查看服务日志
docker compose -f compose.dev.yml logs <service_name>

# 检查端口占用
netstat -ano | grep :8000
netstat -ano | grep :5432
```

**Windows PowerShell:**
```powershell
# 查看服务状态
docker compose -f compose.dev.yml ps

# 查看服务日志
docker compose -f compose.dev.yml logs <service_name>

# 检查端口占用
netstat -ano | Select-String ":8000"
netstat -ano | Select-String ":5432"
```

### 数据库连接失败

```bash
# 检查 postgres 健康状态
docker compose -f compose.dev.yml ps postgres
# 应该显示 (healthy)

# 查看 postgres 日志
docker compose -f compose.dev.yml logs postgres

# 测试连接
docker compose -f compose.dev.yml exec postgres \
  pg_isready -U studyuser -d ti_db
```

### 备份服务无法启动

```bash
# 查看备份服务日志
docker compose -f compose.dev.yml logs backup

# 检查备份脚本权限
ls -la scripts/backup-cron.sh
# 应该显示 -rwxr-xr-x

# 如果没有执行权限
chmod +x scripts/backup-cron.sh

# 重启备份服务
docker compose -f compose.dev.yml restart backup
```

### 热重载不工作

```bash
# 检查代码挂载
docker compose -f compose.dev.yml exec web ls -la /app/app

# 重启 web 服务
docker compose -f compose.dev.yml restart web

# 查看重载日志
docker compose -f compose.dev.yml logs -f web
```

### 磁盘空间不足

**Linux/macOS:**
```bash
# 清理旧备份（保留最近 3 天）
find backups/ -name "backup_*.tar.gz" -mtime +3 -delete

# 清理 Docker 缓存
docker system prune -a

# 清理日志
docker compose -f compose.dev.yml logs --tail=0
```

**Windows PowerShell:**
```powershell
# 清理旧备份（保留最近 3 天）
Get-ChildItem backups/ -Filter "backup_*.tar.gz" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-3) } | Remove-Item

# 清理 Docker 缓存
docker system prune -a

# 清理日志
docker compose -f compose.dev.yml logs --tail=0
```

## 环境变量说明

### 必填变量

```ini
WECHAT_APPID=your_appid              # 微信小程序 AppID
WECHAT_SECRET=your_secret            # 微信小程序 Secret
DASHSCOPE_API_KEY=your_api_key       # 阿里云百炼 API Key
```

### 可选变量

```ini
# 备份配置
BACKUP_INTERVAL=86400                # 备份间隔（秒）
BACKUP_RETENTION_DAYS=7              # 备份保留天数

# AI 配置
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_TIMEOUT=25

# 邮件配置
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_password
MAIL_ENABLED=true
MAIL_CONSOLE_OUTPUT=true             # 开发环境输出到控制台

# 短信配置
ALIYUN_ACCESS_KEY_ID=your_key
ALIYUN_ACCESS_KEY_SECRET=your_secret
SMS_ENABLED=true
SMS_CONSOLE_OUTPUT=false
```

## 与生产环境的差异

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| 数据持久化 | bind mount | bind mount |
| 资源限制 | ✅ 已配置 | ✅ 已配置 |
| 日志管理 | ✅ 已配置 | ✅ 已配置 |
| 自动备份 | ✅ 已配置 | 需手动配置 cron |
| 代码挂载 | ✅ 实时同步 | ❌ 打包到镜像 |
| 热重载 | ✅ 启用 | ❌ 禁用 |
| Nginx | ❌ 无 | ✅ 有 |
| DEBUG 模式 | ✅ 启用 | ❌ 禁用 |

## 常用命令速查

### Linux/macOS

```bash
# 启动服务
docker compose -f compose.dev.yml up -d

# 停止服务
docker compose -f compose.dev.yml down

# 重启服务
docker compose -f compose.dev.yml restart

# 查看状态
docker compose -f compose.dev.yml ps

# 查看日志
docker compose -f compose.dev.yml logs -f

# 查看日志（筛选关键词）
docker compose -f compose.dev.yml logs -f web | grep -E "forum_uploads|迁移"

# 进入容器
docker compose -f compose.dev.yml exec web bash

# 数据库迁移
docker compose -f compose.dev.yml exec web flask db upgrade

# 重建镜像
docker compose -f compose.dev.yml up -d --build

# 查看资源
docker stats

# 清理系统
docker system prune -a
```

### Windows PowerShell

```powershell
# 启动服务
docker compose -f compose.dev.yml up -d

# 停止服务
docker compose -f compose.dev.yml down

# 重启服务
docker compose -f compose.dev.yml restart

# 查看状态
docker compose -f compose.dev.yml ps

# 查看日志
docker compose -f compose.dev.yml logs -f

# 查看日志（筛选关键词）
docker compose -f compose.dev.yml logs -f web | Select-String -Pattern "forum_uploads|迁移"

# 进入容器
docker compose -f compose.dev.yml exec web bash

# 数据库迁移
docker compose -f compose.dev.yml exec web flask db upgrade

# 重建镜像
docker compose -f compose.dev.yml up -d --build

# 查看资源
docker stats

# 清理系统
docker system prune -a
```

## 技术栈

- **Web 框架**: Flask 3.x
- **数据库**: PostgreSQL 16
- **缓存/队列**: Redis 7
- **任务队列**: RQ (Redis Queue)
- **Python**: 3.11
- **容器**: Docker + Docker Compose
