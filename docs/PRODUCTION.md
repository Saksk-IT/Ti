# 生产环境部署与备份指南

## 数据持久化

所有生产数据存储在宿主机 `./var/` 目录：

```
./var/
├── postgres/      # PostgreSQL 数据库文件
├── redis/         # Redis 持久化数据
├── uploads/       # 用户上传文件
├── instance/      # Flask 实例数据
└── logs/          # 应用日志
```

**重要：** 定期备份 `./var/` 目录以防数据丢失。

## 备份与恢复

### 自动备份

使用提供的备份脚本：

```bash
# 执行备份
./scripts/backup.sh

# 备份文件保存在 ./backups/ 目录
# 自动保留最近 7 天的备份
```

### 恢复数据

```bash
# 从备份恢复
./scripts/restore.sh backup_20260305_230000.tar.gz
```

### 定时备份（推荐）

添加到 crontab：

```bash
# 每天凌晨 2 点自动备份
0 2 * * * cd /path/to/Ti-main && ./scripts/backup.sh >> ./var/logs/backup.log 2>&1
```

## 资源限制

所有服务已配置资源限制，防止单个服务占用过多资源：

| 服务 | CPU 限制 | 内存限制 | CPU 预留 | 内存预留 |
|------|----------|----------|----------|----------|
| nginx | 0.5 核 | 128M | 0.25 核 | 64M |
| web | 2.0 核 | 1G | 0.5 核 | 512M |
| worker | 1.0 核 | 512M | 0.25 核 | 256M |
| postgres | 2.0 核 | 512M | 0.5 核 | 256M |
| redis | 0.5 核 | 128M | 0.25 核 | 64M |

## 日志管理

所有服务配置了日志轮转：
- 单个日志文件最大 10MB
- 保留最近 3 个日志文件
- 自动清理旧日志

查看日志：

```bash
# 查看所有服务日志
docker compose -f compose.prod.yml logs -f

# 查看特定服务日志
docker compose -f compose.prod.yml logs -f web
```

## 健康检查

- **postgres**: 每 10 秒检查一次，启动宽限期 10 秒
- **web**: 每 15 秒检查一次，启动宽限期 30 秒
- **redis**: 无健康检查（启动即可用）

## 部署流程

### 首次部署

```bash
# 1. 创建数据目录
mkdir -p var/postgres var/redis

# 2. 配置环境变量
cp .env.example .env.production
vim .env.production  # 修改生产配置

# 3. 构建镜像
docker build -t saksk-ti:latest -f docker/Dockerfile .

# 4. 启动服务
docker compose --env-file .env.production -f compose.prod.yml up -d

# 5. 初始化数据库
docker compose -f compose.prod.yml exec web flask db upgrade

# 6. 检查服务状态
docker compose -f compose.prod.yml ps
```

### 更新部署

```bash
# 1. 备份数据
./scripts/backup.sh

# 2. 拉取最新代码
git pull

# 3. 重新构建镜像
docker build -t saksk-ti:latest -f docker/Dockerfile .

# 4. 重启服务
docker compose --env-file .env.production -f compose.prod.yml up -d --force-recreate

# 5. 执行数据库迁移
docker compose -f compose.prod.yml exec web flask db upgrade
```

## 监控

### 检查服务状态

```bash
docker compose -f compose.prod.yml ps
```

### 检查资源使用

```bash
docker stats
```

### 检查磁盘空间

```bash
du -sh var/*
```

## 故障排查

### 服务无法启动

```bash
# 查看日志
docker compose -f compose.prod.yml logs web

# 检查健康状态
docker compose -f compose.prod.yml ps
```

### 数据库连接失败

```bash
# 检查 postgres 健康状态
docker compose -f compose.prod.yml exec postgres pg_isready -U studyuser

# 查看 postgres 日志
docker compose -f compose.prod.yml logs postgres
```

### 磁盘空间不足

```bash
# 清理 Docker 缓存（不会删除数据）
docker system prune -a

# 清理旧日志
find var/logs -name "*.log" -mtime +30 -delete

# 清理旧备份
find backups -name "backup_*.tar.gz" -mtime +30 -delete
```

## 安全建议

1. **定期备份**：每天自动备份，异地存储
2. **监控磁盘空间**：确保 `./var/` 目录有足够空间
3. **更新镜像**：定期更新基础镜像和依赖
4. **日志审计**：定期检查应用日志
5. **资源监控**：使用 Prometheus + Grafana 监控资源使用

## 迁移到新服务器

```bash
# 旧服务器
./scripts/backup.sh
scp backups/backup_*.tar.gz user@new-server:/path/to/Ti-main/backups/

# 新服务器
git clone <repository>
cd Ti-main
./scripts/restore.sh backup_*.tar.gz
docker compose --env-file .env.production -f compose.prod.yml up -d
```
