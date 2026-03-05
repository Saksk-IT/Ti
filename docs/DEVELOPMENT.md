# 开发环境配置说明

## 自动备份功能

开发环境已配置数据库自动备份服务。

### 配置参数

在 `.env` 文件中配置（可选）：

```ini
# 备份间隔（秒），默认 86400（24小时）
BACKUP_INTERVAL=86400

# 备份保留天数，默认 7 天
BACKUP_RETENTION_DAYS=7
```

### 备份行为

- **首次启动立即备份**：容器启动后立即执行一次备份
- **定时自动备份**：按照 `BACKUP_INTERVAL` 间隔自动备份
- **自动清理旧备份**：保留最近 `BACKUP_RETENTION_DAYS` 天的备份
- **备份文件格式**：`db_backup_YYYYMMDD_HHMMSS.sql.gz`
- **备份位置**：`./backups/` 目录

### 查看备份

```bash
# 查看备份文件
ls -lh backups/

# 查看备份服务日志
docker compose -f compose.dev.yml logs -f backup
```

### 手动触发备份

```bash
# 重启备份服务会立即执行一次备份
docker compose -f compose.dev.yml restart backup
```

### 恢复备份

```bash
# 解压备份文件
gunzip backups/db_backup_20260305_230000.sql.gz

# 恢复到数据库
docker compose -f compose.dev.yml exec -T postgres \
  psql -U studyuser -d ti_db < backups/db_backup_20260305_230000.sql
```

## 资源限制

所有服务已配置资源限制，防止开发环境占用过多资源：

| 服务 | CPU 限制 | 内存限制 | CPU 预留 | 内存预留 |
|------|----------|----------|----------|----------|
| web | 2.0 核 | 1G | 0.5 核 | 512M |
| worker | 1.0 核 | 512M | 0.25 核 | 256M |
| postgres | 2.0 核 | 512M | 0.5 核 | 256M |
| redis | 0.5 核 | 128M | 0.25 核 | 64M |
| backup | 0.25 核 | 128M | 0.1 核 | 64M |

### 查看资源使用

```bash
docker stats
```

## 日志管理

所有服务配置了日志轮转：
- 单个日志文件最大 10MB
- 保留最近 3 个日志文件
- 自动清理旧日志

### 查看日志

```bash
# 查看所有服务日志
docker compose -f compose.dev.yml logs -f

# 查看特定服务日志
docker compose -f compose.dev.yml logs -f web
docker compose -f compose.dev.yml logs -f backup
```

## 数据库性能参数

Postgres 已配置性能参数：
- `shared_buffers=128MB`
- `work_mem=4MB`
- `max_connections=50`

## Redis 内存限制

Redis 已配置内存限制：
- `maxmemory=64mb`
- `maxmemory-policy=allkeys-lru`

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

## 启动开发环境

```bash
# 启动所有服务（包括自动备份）
docker compose --env-file .env -f compose.dev.yml up -d

# 查看服务状态
docker compose -f compose.dev.yml ps

# 查看备份服务日志
docker compose -f compose.dev.yml logs -f backup
```

## 停止开发环境

```bash
# 停止所有服务
docker compose -f compose.dev.yml down

# 停止并删除数据（慎用！）
docker compose -f compose.dev.yml down -v
```

## 故障排查

### 备份服务无法启动

**问题 1：只读文件系统错误**

```
chmod: /backup-cron.sh: Read-only file system
```

**原因：** 备份脚本以只读方式挂载

**解决：** 已在最新版本修复，确保使用最新的 `compose.dev.yml`

**验证：**
```bash
# 检查挂载配置
grep -A 2 "backup-cron.sh" compose.dev.yml
# 应该看到：- ./scripts/backup-cron.sh:/backup-cron.sh（无 :ro 标志）
```

**问题 2：脚本无执行权限**

```bash
# 查看备份服务日志
docker compose -f compose.dev.yml logs backup

# 检查备份脚本权限
ls -la scripts/backup-cron.sh
# 应该显示 -rwxr-xr-x

# 如果没有执行权限，手动设置
chmod +x scripts/backup-cron.sh

# 重启备份服务
docker compose -f compose.dev.yml restart backup
```

**问题 3：数据库连接失败**

```bash
# 查看 postgres 服务状态
docker compose -f compose.dev.yml ps postgres

# 查看 postgres 日志
docker compose -f compose.dev.yml logs postgres

# 确保 postgres 健康检查通过
docker compose -f compose.dev.yml ps
# postgres 应该显示 (healthy)
```

### 备份文件过多占用磁盘

调整 `BACKUP_RETENTION_DAYS` 参数：

```ini
# .env 文件
BACKUP_RETENTION_DAYS=3  # 只保留 3 天
```

然后重启备份服务：

```bash
docker compose -f compose.dev.yml restart backup
```

### 手动清理旧备份

```bash
# 删除 7 天前的备份
find backups/ -name "db_backup_*.sql.gz" -mtime +7 -delete

# 查看剩余备份
ls -lh backups/
```

### 恢复备份失败

**问题：数据库正在使用中**

```bash
# 停止 web 和 worker 服务
docker compose -f compose.dev.yml stop web worker

# 恢复备份
gunzip backups/db_backup_20260306_000000.sql.gz
docker compose -f compose.dev.yml exec -T postgres \
  psql -U studyuser -d ti_db < backups/db_backup_20260306_000000.sql

# 重启服务
docker compose -f compose.dev.yml start web worker
```

## 首次启动指南

### 1. 克隆项目

```bash
git clone <仓库地址>
cd Ti-main
```

### 2. 创建环境变量文件

```bash
cp .env.example .env
vim .env
```

必填项：
```ini
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret
DASHSCOPE_API_KEY=your_api_key
```

可选项（备份配置）：
```ini
BACKUP_INTERVAL=86400          # 24小时
BACKUP_RETENTION_DAYS=7        # 保留7天
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker compose --env-file .env -f compose.dev.yml up -d

# 查看服务状态
docker compose -f compose.dev.yml ps

# 查看日志
docker compose -f compose.dev.yml logs -f
```

### 4. 初始化数据库

```bash
# 执行数据库迁移
docker compose -f compose.dev.yml exec web flask db upgrade

# 验证数据库
docker compose -f compose.dev.yml exec postgres \
  psql -U studyuser -d ti_db -c "\dt"
```

### 5. 验证备份服务

```bash
# 查看备份服务日志
docker compose -f compose.dev.yml logs backup

# 应该看到类似输出：
# === 数据库自动备份服务启动 ===
# 备份间隔: 86400 秒
# 保留天数: 7 天
# 2026-03-06 00:00:00 - 开始备份...
# 2026-03-06 00:00:05 - 备份完成: /backups/db_backup_20260306_000000.sql.gz

# 查看备份文件
ls -lh backups/
```

### 6. 访问应用

```bash
# Web 应用
open http://localhost:8000

# 健康检查
curl http://localhost:8000/api/ping
```

## 日常开发工作流

### 代码修改

代码修改后自动热重载，无需重启服务：

```bash
# 修改代码
vim app/modules/xxx/xxx.py

# Flask 自动检测并重载
# 查看重载日志
docker compose -f compose.dev.yml logs -f web
```

### 数据库迁移

```bash
# 创建迁移
docker compose -f compose.dev.yml exec web flask db migrate -m "描述"

# 应用迁移
docker compose -f compose.dev.yml exec web flask db upgrade

# 回滚迁移
docker compose -f compose.dev.yml exec web flask db downgrade
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
docker compose -f compose.dev.yml restart backup
```

### 停止服务

```bash
# 停止所有服务
docker compose -f compose.dev.yml down

# 停止并删除数据（慎用！）
docker compose -f compose.dev.yml down -v
```

## 性能监控

### 查看资源使用

```bash
# 实时监控
docker stats

# 查看特定服务
docker stats backup-1 web-1 postgres-1
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
