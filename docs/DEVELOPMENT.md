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

```bash
# 查看备份服务日志
docker compose -f compose.dev.yml logs backup

# 检查备份脚本权限
ls -la scripts/backup-cron.sh

# 检查备份目录权限
ls -la backups/
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
