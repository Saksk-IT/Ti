# Ti 题库系统 — 生产环境部署指南

> 适用版本：2026-03（安全加固版）
> 操作系统：Ubuntu 24.04 LTS
> 架构：Nginx + gunicorn (4w×4t) + Flask + PostgreSQL + Redis
> 部署方式：Docker Compose 一键部署
> 数据持久化：宿主机 bind mount（防止数据丢失）

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
13. [安全加固说明](#13-安全加固说明)

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
| redis | redis:7-alpine | 缓存 + 限流 + SSE Pub/Sub + RQ 队列（64MB 上限） |

---

## 2. 服务器要求

| 项目 | 最低配置（2核2G） | 推荐配置（4核4G） |
|------|------------------|------------------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 20 GB SSD | 40 GB SSD |
| 系统 | **Ubuntu 24.04 LTS** | 同左 |
| Docker | 26.0+ | 同左 |
| Docker Compose | v2.24+ | 同左 |

### Ubuntu 24.04 特性

- 内核版本：6.8+
- 默认 Python：3.12
- 默认 Docker：通过 apt 安装即可
- 长期支持：至 2029 年 4 月

### 资源限制（已配置）

所有服务已配置资源限制，防止单个服务占用过多资源：

| 服务 | CPU 限制 | 内存限制 | CPU 预留 | 内存预留 |
|------|----------|----------|----------|----------|
| nginx | 0.5 核 | 128M | 0.25 核 | 64M |
| web | 2.0 核 | 1G | 0.5 核 | 512M |
| worker | 1.0 核 | 512M | 0.25 核 | 256M |
| postgres | 2.0 核 | 512M | 0.5 核 | 256M |
| redis | 0.5 核 | 128M | 0.25 核 | 64M |

### 2核2G 内存分配

```
总内存 2048MB
├── PostgreSQL    ~400MB（shared_buffers 128MB + 工作内存）
├── Redis           64MB（maxmemory）
├── Web (2w×4t)   ~600MB（gunicorn 2 workers）
├── Worker (RQ)   ~200MB
├── Nginx          ~30MB
└── 系统预留      ~750MB
```

---

## 3. 准备工作

### 3.1 安装 Docker（Ubuntu 24.04）

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker（官方脚本）
curl -fsSL https://get.docker.com | sudo sh

# 将当前用户加入 docker 组
sudo usermod -aG docker $USER

# 重新登录使 docker 组生效
exit
# 重新 SSH 登录

# 验证安装
docker --version
docker compose version
```

### 3.2 克隆项目

```bash
# 克隆到 /opt/ti 目录
sudo mkdir -p /opt/ti
sudo chown $USER:$USER /opt/ti
git clone <你的仓库地址> /opt/ti
cd /opt/ti
```

### 3.3 创建数据目录

```bash
# 创建所有必要的数据目录
mkdir -p var/postgres var/redis var/uploads/avatars var/uploads/question_images var/logs var/instance backups

# 设置权限
chmod 700 var/postgres var/redis
chmod 755 var/uploads var/logs backups
```

**重要：** 所有生产数据存储在 `./var/` 目录，使用 bind mount 方式挂载，确保数据安全。

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

| 服务器 | WORKERS | THREADS | DB_POOL_SIZE | DB_MAX_OVERFLOW | Redis 内存 | PG shared_buffers | 并发 | DB连接 |
|--------|---------|---------|-------------|-----------------|-----------|-------------------|------|--------|
| 2核 2G（默认） | 2 | 4 | 3 | 5 | 64MB | 128MB | 8 | 16 |
| 4核 4G | 4 | 4 | 5 | 10 | 128MB | 256MB | 16 | 60 |
| 8核 8G | 8 | 4 | 3 | 7 | 256MB | 512MB | 32 | 80 |

当前默认配置已针对 2核2G 优化。如需扩容，在 `.env.production` 中覆盖：

```ini
# 4核4G 示例
GUNICORN_WORKERS=4
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

Redis 和 PostgreSQL 参数需修改 `compose.prod.yml` 中对应的 command。

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

### 11.1 自动备份服务（推荐）

生产环境的 `compose.prod.yml` 已内置 `backup` 服务，默认按北京时间每天 `04:00` / `16:00` 自动备份到 `./backups/`：

```bash
# 启动生产服务（会同时启动 backup 服务）
docker compose --env-file .env.production -f compose.prod.yml up -d

# 查看自动备份日志
docker compose --env-file .env.production -f compose.prod.yml logs -f backup

# 查看备份文件
ls -lh backups/
```

默认备份内容：
- 数据库完整备份（pg_dump）
- Redis 持久化目录
- 上传文件
- 实例数据
- 最近 7 天日志
- `.env.production` 与 `compose.prod.yml`

### 11.2 恢复数据

```bash
# 从备份恢复
./scripts/restore.sh backup_20260305_230000.tar.gz

# 恢复过程：
# 1. 停止 web 和 worker 服务
# 2. 恢复数据库
# 3. 恢复 Redis 数据
# 4. 恢复上传文件
# 5. 重启服务
```

### 11.3 手动立即备份

如需不等自动窗口，仍可手动执行一次完整备份：

```bash
./scripts/backup.sh
```

### 11.4 手动备份（备选方案）

#### 数据库备份

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

#### 上传文件备份

```bash
tar czf backups/uploads-$(date +%Y%m%d).tar.gz var/uploads/
```

### 11.5 数据持久化说明

所有生产数据存储在宿主机 `./var/` 目录：

```
./var/
├── postgres/      # PostgreSQL 数据库文件（bind mount）
├── redis/         # Redis 持久化数据（bind mount）
├── uploads/       # 用户上传文件
├── instance/      # Flask 实例数据
└── logs/          # 应用日志
```

**重要：**
- 使用 bind mount 而非 Docker volume，防止 `docker system prune` 导致数据丢失
- 定期备份 `./var/` 目录
- 备份文件异地存储（如阿里云 OSS）

### 11.6 异地备份（推荐）

```bash
# 安装阿里云 OSS 工具
wget http://gosspublic.alicdn.com/ossutil/1.7.15/ossutil64
chmod +x ossutil64
sudo mv ossutil64 /usr/local/bin/ossutil

# 配置 OSS
ossutil config

# 上传备份到 OSS
ossutil cp backups/backup_*.tar.gz oss://your-bucket/ti-backups/
```

---

## 12. HTTPS 配置

### 方案 A：阿里云 ALB 负载均衡器（推荐）

SSL 在 ALB 层终止，服务器只跑 HTTP 80，compose.prod.yml 不用改。

```
用户 ──443/HTTPS──▶ 阿里云 ALB ──80/HTTP──▶ ECS (Docker)
                    (SSL 终止)              (compose 不变)
```

#### A1. 申请 SSL 证书

1. 进入 [阿里云数字证书管理](https://yundun.console.aliyun.com/?p=cas)
2. 免费证书 → 创建证书 → 填写你的域名
3. 按提示做 DNS 验证（添加一条 CNAME 或 TXT 记录）
4. 等待签发（通常几分钟）

#### A2. 创建 ALB 实例

1. 进入 [应用型负载均衡 ALB 控制台](https://slb.console.aliyun.com/alb)
2. 创建实例：
   - 网络类型：公网
   - 地域/可用区：和你的 ECS 一致
   - 规格：基础版（日活 1000 足够）

#### A3. 配置监听

**HTTPS 监听（443）：**

1. 添加监听 → 协议 HTTPS → 端口 443
2. SSL 证书：选择 A1 步骤申请的证书
3. 后端服务器组：
   - 添加你的 ECS 实例
   - 后端端口填 `80`（Nginx 监听的端口）
   - 协议：HTTP
4. 健康检查：
   - 路径：`/api/ping`
   - 预期状态码：200

**HTTP 监听（80）— 自动跳转 HTTPS：**

1. 添加监听 → 协议 HTTP → 端口 80
2. 默认动作：重定向到 HTTPS 443

#### A4. DNS 解析

1. 进入 [云解析 DNS](https://dns.console.aliyun.com)
2. 添加记录：
   - 类型：A（指向 ALB 公网 IP）或 CNAME（指向 ALB 域名）
   - 主机记录：你的域名前缀（如 `www` 或 `@`）

#### A5. ECS 安全组

- 入方向放行 80 端口，来源限制为 ALB 所在 VPC 网段
- 关闭公网直接访问 80（所有流量走 ALB）

#### A6. 调整 .env.production

```ini
SESSION_COOKIE_SECURE=true
```

#### A7. 验证

```bash
# HTTPS 访问
curl https://你的域名/api/ping
# {"status":"success","data":{"pong":true}}

# HTTP 自动跳转
curl -I http://你的域名/
# HTTP/1.1 301 → Location: https://你的域名/
```

#### 费用参考

- 免费 SSL 证书：0 元（每年续签）
- ALB 基础版：约 15-30 元/月（按量计费更便宜）

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

---

## 13. 安全加固说明

### 13.1 数据持久化改进

**问题：** 旧版本使用 Docker 匿名 volume，执行 `docker system prune --volumes` 会导致生产数据永久丢失。

**解决：** 2026-03 版本已改为 bind mount：

```yaml
# 旧配置（危险）
volumes:
  - postgres_data:/var/lib/postgresql/data  # 匿名 volume

# 新配置（安全）
volumes:
  - ./var/postgres:/var/lib/postgresql/data  # bind mount
```

**验证：**
```bash
# 检查数据目录
ls -la var/postgres/
ls -la var/redis/

# 数据文件应该在宿主机可见
```

### 13.2 资源限制

所有服务已配置资源限制，防止单个服务占用过多资源导致系统崩溃。

**查看资源使用：**
```bash
docker stats
```

### 13.3 日志管理

所有服务配置了日志轮转：
- 单个日志文件最大 10MB
- 保留最近 3 个日志文件
- 自动清理旧日志

**查看日志配置：**
```bash
docker inspect <容器ID> | grep -A 5 LogConfig
```

### 13.4 健康检查优化

- postgres 健康检查间隔从 5s 改为 10s
- 添加启动宽限期 10s，避免启动阶段误判
- 减少重试次数，快速失败而不是长时间阻塞

### 13.5 安全检查清单

部署前检查：

- [ ] `.env.production` 中的 `SECRET_KEY` 已修改为随机字符串
- [ ] `POSTGRES_PASSWORD` 已修改为强密码
- [ ] 所有敏感信息未提交到 Git
- [ ] 防火墙已配置（只开放必要端口）
- [ ] SSH 密钥登录已启用，密码登录已禁用
- [ ] 定时备份已配置
- [ ] 备份文件已异地存储
- [ ] 监控告警已配置（可选）

### 13.6 防火墙配置（Ubuntu 24.04）

```bash
# 启用 UFW
sudo ufw enable

# 允许 SSH
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 查看状态
sudo ufw status
```

### 13.7 定期维护

**每周：**
- 检查磁盘空间：`df -h`
- 检查备份是否正常：`ls -lh backups/`
- 查看错误日志：`docker compose -f compose.prod.yml logs --tail=100 | grep ERROR`

**每月：**
- 更新系统：`sudo apt update && sudo apt upgrade -y`
- 清理 Docker 缓存：`docker system prune -a`（不会删除数据）
- 检查资源使用：`docker stats`

**每季度：**
- 测试备份恢复流程
- 更新 Docker 镜像
- 审查安全日志

---

## 附录：快速命令参考

### 服务管理

```bash
# 启动所有服务
docker compose --env-file .env.production -f compose.prod.yml up -d

# 停止所有服务
docker compose -f compose.prod.yml down

# 重启单个服务
docker compose -f compose.prod.yml restart web

# 查看服务状态
docker compose -f compose.prod.yml ps

# 查看日志
docker compose -f compose.prod.yml logs -f web
```

### 数据库操作

```bash
# 进入数据库
docker compose -f compose.prod.yml exec postgres psql -U studyuser -d ti_db

# 执行迁移
docker compose -f compose.prod.yml exec web flask db upgrade

# 查看连接数
docker compose -f compose.prod.yml exec postgres \
  psql -U studyuser -d ti_db -c "SELECT count(*) FROM pg_stat_activity;"
```

### 备份恢复

```bash
# 备份
./scripts/backup.sh

# 恢复
./scripts/restore.sh backup_20260305_230000.tar.gz

# 查看备份
ls -lh backups/
```

### 监控

```bash
# 资源使用
docker stats

# 磁盘空间
df -h
du -sh var/*

# 系统负载
top
htop
```

---

## 技术支持

- 项目文档：`docs/PRODUCTION.md`
- 问题反馈：GitHub Issues
- 紧急联系：查看项目 README
