# Ti 题库系统 — 生产环境部署指南

> 适用版本：高并发优化后（2026-02）
> 架构：Nginx + gunicorn (4w×4t) + Flask + PostgreSQL + Redis
> 部署方式：Docker Compose 一键部署

---

## 目录

1. [架构总览](#1-架构总览)
2. [服务器要求](#2-服务器要求)
3. [准备工作](#3-准备工作)
4. [环境变量配置](#4-环境变量配置)
5. [构建与启动](#5-构建与启动)
6. [数据库迁移](#6-数据库迁移)
7. [健康检查与验证](#7-健康检查与验证)
8. [日常运维](#8-日常运维)
9. [性能调优参数](#9-性能调优参数)
10. [故障排查](#10-故障排查)
11. [备份与恢复](#11-备份与恢复)
12. [HTTPS 配置](#12-https-配置)

---

## 1. 架构总览

```
                    ┌──────────┐
    用户请求 ──80──▶│  Nginx   │
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         /static/    /sse/stream   其他
         直接返回    proxy_pass    proxy_pass
         (30d缓存)  (无缓冲)     (gzip)
                         │          │
                    ┌────▼──────────▼────┐
                    │   gunicorn:8000    │
                    │  4 workers × 4 t  │
                    │  (gthread 模式)    │
                    └──┬─────┬─────┬────┘
                       │     │     │
                  ┌────▼┐ ┌─▼──┐ ┌▼────┐
                  │ PG  │ │Redis│ │ RQ  │
                  │:5432│ │:6379│ │worker│
                  └─────┘ └────┘ └─────┘
```

| 服务 | 镜像 | 作用 |
|------|------|------|
| nginx | nginx:1.25-alpine | 反向代理、静态资源、gzip 压缩、SSE 透传 |
| web | saksk-ti:latest | Flask 应用（gunicorn 4w×4t = 16 并发槽位） |
| worker | saksk-ti:latest | RQ 异步任务（AI 判题、查重等耗时操作） |
| postgres | postgres:16-alpine | 主数据库 |
| redis | redis:7-alpine | 缓存 + 限流 + SSE Pub/Sub + RQ 队列（128MB 上限） |

---

## 2. 服务器要求

| 项目 | 最低配置 | 推荐配置（日活 1000） |
|------|---------|---------------------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 20 GB SSD | 40 GB SSD |
| 系统 | Ubuntu 22.04+ / Debian 12+ | 同左 |
| Docker | 24.0+ | 同左 |
| Docker Compose | v2.20+ | 同左 |

---

## 3. 准备工作

### 3.1 安装 Docker

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录使 docker 组生效
```

### 3.2 克隆项目

```bash
git clone <你的仓库地址> /opt/ti
cd /opt/ti
```

### 3.3 创建数据目录

```bash
mkdir -p var/uploads/avatars var/uploads/question_images var/logs
```

---

## 4. 环境变量配置

创建 `.env.production` 文件：

```bash
nano .env.production
```

### 必填项

```ini
FLASK_ENV=production

# 应用密钥（必须修改！）
# 生成方式: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=<替换为随机字符串>

# 数据库凭据
POSTGRES_USER=studyuser
POSTGRES_PASSWORD=<替换为强密码>
POSTGRES_DB=ti_db

# 微信小程序（如不使用可留空）
WECHAT_APPID=
WECHAT_SECRET=

# AI 判题（DashScope）
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=<你的 API Key>
```

### 可选调优项

```ini
# gunicorn 并发（默认 4w×4t，2核机器建议 2w×4t）
GUNICORN_WORKERS=4
GUNICORN_THREADS=4

# 数据库连接池
# 总连接 = WORKERS × (POOL_SIZE + MAX_OVERFLOW)
# 默认: 4 × (5 + 10) = 60，需 < PostgreSQL max_connections(100)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=300

# Sentry 错误监控（可选，免费 tier 足够日活 1000）
SENTRY_DSN=

# Session Cookie（HTTPS 环境设 true）
SESSION_COOKIE_SECURE=true
```

> `.env.production` 已被 `.gitignore` 排除，绝不要提交到 Git。

---

## 5. 构建与启动

### 5.1 构建镜像

```bash
cd /opt/ti
docker build -t saksk-ti:latest -f docker/Dockerfile .
```

### 5.2 启动全部服务

```bash
docker compose --env-file .env.production -f compose.prod.yml up -d
```

### 5.3 确认启动成功

```bash
# 查看服务状态（web 应显示 healthy）
docker compose -f compose.prod.yml ps

# 确认 4 个 worker 启动
docker compose -f compose.prod.yml logs web | grep "Booting worker"
# 预期输出 4 行: [INFO] Booting worker with pid: ...

# 实时日志
docker compose -f compose.prod.yml logs -f
```

---

## 6. 数据库迁移

首次部署或代码更新后执行：

```bash
docker compose -f compose.prod.yml exec web flask db upgrade
```

验证索引：

```bash
docker compose -f compose.prod.yml exec postgres \
  psql -U studyuser -d ti_db -c "\di"
```

---

## 7. 健康检查与验证

### 7.1 基础检查

```bash
curl http://localhost/api/ping
# {"status":"success","data":{"pong":true}}
```

### 7.2 深度检查（DB + Redis 连通性）

```bash
curl http://localhost/api/ping?deep=1
# 正常: {"status":"success","data":{"pong":true,"db":true,"redis":true}}
# 异常: {"status":"degraded",...} + HTTP 503
```

### 7.3 Nginx 静态资源

```bash
curl -I http://localhost/static/css/style.css
# 预期: Server: nginx, Cache-Control: public, immutable, Expires: 30天后
```

### 7.4 限流验证

快速连续请求同一接口，确认跨 worker 计数一致（Redis 共享存储）。

---

## 8. 日常运维

### 8.1 更新部署

```bash
cd /opt/ti
git pull origin main
docker build -t saksk-ti:latest -f docker/Dockerfile .
docker compose --env-file .env.production -f compose.prod.yml up -d
docker compose -f compose.prod.yml exec web flask db upgrade
```

### 8.2 查看日志

```bash
# 实时日志
docker compose -f compose.prod.yml logs -f web

# 慢请求（>1s 自动记录 WARNING）
docker compose -f compose.prod.yml logs web | grep "SLOW REQUEST"

# 应用持久化日志
tail -f var/logs/app.log
```

### 8.3 Redis 监控

```bash
# 内存使用（应 < 128MB）
docker compose -f compose.prod.yml exec redis redis-cli info memory

# 连接数
docker compose -f compose.prod.yml exec redis redis-cli info clients
```

### 8.4 PostgreSQL 监控

```bash
# 当前连接数（应 < 100）
docker compose -f compose.prod.yml exec postgres \
  psql -U studyuser -d ti_db -c "SELECT count(*) FROM pg_stat_activity;"
```

### 8.5 服务管理

```bash
# 停止所有服务
docker compose -f compose.prod.yml down

# 重启单个服务
docker compose -f compose.prod.yml restart web
docker compose -f compose.prod.yml restart worker
```

---

## 9. 性能调优参数

### 9.1 并发能力公式

```
并发槽位 = GUNICORN_WORKERS × GUNICORN_THREADS
DB 连接数 = WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

### 9.2 按服务器规格推荐

| 服务器 | WORKERS | THREADS | DB_POOL_SIZE | DB_MAX_OVERFLOW | 并发 | DB连接 |
|--------|---------|---------|-------------|-----------------|------|--------|
| 2核 2G | 2 | 4 | 5 | 10 | 8 | 30 |
| 4核 4G | 4 | 4 | 5 | 10 | 16 | 60 |
| 8核 8G | 8 | 4 | 3 | 7 | 32 | 80 |

### 9.3 SSE 连接参数

可在 compose.prod.yml 的 web environment 中添加：

```yaml
SSE_MAX_TOTAL_CONNECTIONS: "200"
SSE_MAX_CONNECTION_DURATION_SECONDS: "600"
SSE_HEARTBEAT_INTERVAL_SECONDS: "15"
```

### 9.4 缓存 TTL

```yaml
QUIZ_CACHE_TTL_SUBJECTS_SECONDS: "300"
QUIZ_CACHE_TTL_SUBJECTS_META_SECONDS: "300"
QUIZ_CACHE_TTL_COUNTS_SECONDS: "120"
```

---

## 10. 故障排查

### web 容器启动失败

```bash
docker compose -f compose.prod.yml logs web
```

| 错误信息 | 原因 | 解决 |
|---------|------|------|
| `SECRET_KEY 未设置` | .env.production 缺少 SECRET_KEY | 添加 SECRET_KEY |
| `REDIS_URL 未设置` | 未通过 compose 启动或 env-file 参数缺失 | 检查启动命令的 --env-file 参数 |
| `Connection refused :5432` | PostgreSQL 未就绪 | 等待 healthcheck 通过，检查 postgres 日志 |

### Nginx 502 Bad Gateway

web 容器未启动完成或 healthcheck 未通过：

```bash
docker compose -f compose.prod.yml ps web
docker compose -f compose.prod.yml logs --tail=50 web
```

### 深度健康检查返回 503

```bash
curl http://localhost/api/ping?deep=1
```

检查返回的 `db_error` 或 `redis_error` 字段，针对性排查对应服务。

### SSE 返回 503（连接数已满）

全局上限默认 200。检查是否有客户端未正确断开。可临时调大 `SSE_MAX_TOTAL_CONNECTIONS`。

### 限流各 worker 独立计数

确认 `REDIS_URL` 已正确配置且 Redis 服务正常运行。

---

## 11. 备份与恢复

### 数据库备份

```bash
# 备份
docker compose -f compose.prod.yml exec postgres \
  pg_dump -U studyuser -d ti_db --format=custom -f /tmp/backup.dump
docker compose -f compose.prod.yml cp postgres:/tmp/backup.dump ./backups/

# 恢复
docker compose -f compose.prod.yml cp ./backups/backup.dump postgres:/tmp/
docker compose -f compose.prod.yml exec postgres \
  pg_restore -U studyuser -d ti_db --clean --if-exists /tmp/backup.dump
```

### 上传文件备份

```bash
tar czf backups/uploads-$(date +%Y%m%d).tar.gz var/uploads/
```

### 定时备份（crontab）

```bash
# 每天凌晨 3 点备份数据库
0 3 * * * cd /opt/ti && docker compose -f compose.prod.yml exec -T postgres \
  pg_dump -U studyuser -d ti_db --format=custom > backups/db-$(date +\%Y\%m\%d).dump
```

---

## 12. HTTPS 配置

### 方案 A：云厂商负载均衡器（推荐）

在 SLB / CLB 层终止 SSL，compose 保持 80 端口，最简单。

### 方案 B：Nginx 直接 SSL

1. 证书放到 `docker/ssl/` 目录
2. 修改 `docker/nginx.conf` 添加 443 监听和证书路径
3. 修改 `compose.prod.yml` nginx 端口映射为 `"443:443"`
4. 设置 `SESSION_COOKIE_SECURE=true`

### 方案 C：Certbot 自动证书

```bash
apt install certbot
certbot certonly --standalone -d your-domain.com
# 将证书目录挂载到 nginx 容器
```
