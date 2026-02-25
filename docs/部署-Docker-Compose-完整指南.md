# Ti 项目 — Docker Compose 部署完整指南

> Flask + Gunicorn + PostgreSQL + Redis + RQ Worker
> 全量 SQLAlchemy ORM，PostgreSQL 为唯一数据库后端。

---

## 目录

1. [架构概览](#1-架构概览)
2. [服务器准备](#2-服务器准备)
3. [放置项目代码](#3-放置项目代码)
4. [生产环境配置](#4-生产环境配置)
5. [构建与启动](#5-构建与启动)
6. [数据库初始化与迁移](#6-数据库初始化与迁移)
7. [Nginx + HTTPS](#7-nginx--https)
8. [小程序侧配置](#8-小程序侧配置)
9. [运维常用命令](#9-运维常用命令)
10. [备份与恢复](#10-备份与恢复)
11. [常见故障排查](#11-常见故障排查)
12. [安全提醒](#12-安全提醒)

---

## 1. 架构概览

本项目后端由 4 个服务组成：

| 服务 | 镜像 | 说明 |
|------|------|------|
| `web` | saksk-ti:latest | Flask + Gunicorn（Web 页面与 API） |
| `worker` | saksk-ti:latest | RQ Worker（异步任务，如 AI 解析） |
| `postgres` | postgres:16-alpine | PostgreSQL 数据库 |
| `redis` | redis:7-alpine | 队列/缓存/限流共享存储 |

访问形态：

- Web 页面：`https://<域名>/...`
- API：`https://<域名>/api/...`
- 健康检查：`GET /api/ping`

> 容器内 Gunicorn 监听 `8000`，通过 Nginx 反代对外提供 HTTPS 服务。

### 数据持久化

| 数据 | 容器内路径 | 宿主机存储 |
|------|-----------|-----------|
| PostgreSQL 数据 | `/var/lib/postgresql/data` | Docker volume `postgres_data` |
| 上传文件 | `/data/uploads/` | `./var/uploads/` |
| 日志 | `/data/logs/` | `./var/logs/` |
| Redis 数据 | `/data` | Docker volume `redis_data` |

---

## 2. 服务器准备

### 2.1 目录

```bash
sudo mkdir -p /opt/saksk-ti
sudo mkdir -p /opt/saksk-ti/var/{logs,uploads}
sudo chown -R $USER:$USER /opt/saksk-ti
```

### 2.2 安装 Docker 与 Compose

按服务器发行版的官方说明安装，安装后确认：

```bash
docker version
docker compose version
```

#### 国内镜像加速（可选）

如果拉取 `postgres:16-alpine`、`redis:7-alpine` 超时：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<JSON
{
  "registry-mirrors": [
    "https://<你的加速器地址>"
  ]
}
JSON
sudo systemctl daemon-reload
sudo systemctl restart docker
```

> 阿里云 ECS 用户：控制台 -> 容器镜像服务 -> 镜像工具 -> 镜像加速器。

### 2.3 防火墙

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

> 不要对公网开放 `8000` 和 `5432`。`8000` 仅绑定 `127.0.0.1`，公网经由 Nginx 443 访问。

---

## 3. 放置项目代码

### 方式 A：git clone

```bash
cd /opt/saksk-ti
git clone <仓库地址> .
```

### 方式 B：上传压缩包

本地打包：

```bash
tar -czf saksk-ti.tar.gz   compose.prod.yml docker/Dockerfile requirements.txt run.py .dockerignore   app static docs migrations
```

上传并解压：

```bash
rsync -avP saksk-ti.tar.gz user@server:/opt/saksk-ti/
ssh user@server "cd /opt/saksk-ti && tar -xzf saksk-ti.tar.gz"
```

#### 服务器最小文件清单

```
/opt/saksk-ti/
├── compose.prod.yml         # 生产 compose 配置
├── docker/Dockerfile        # 镜像构建文件
├── requirements.txt         # Python 依赖
├── run.py                   # 应用入口
├── .dockerignore            # 构建排除
├── .env.production          # 环境变量（不入库）
├── app/                     # 后端代码
├── static/                  # 静态资源
├── migrations/              # Alembic 迁移脚本
└── var/                     # 运行时数据
    ├── uploads/
    └── logs/
```

> `miniprogram-1/` 是小程序工程，不需要部署到服务器。

---

## 4. 生产环境配置

### 4.1 创建 .env.production

```bash
cat > /opt/saksk-ti/.env.production << 'ENVEOF'
FLASK_ENV=production

# 密钥（必须替换为强随机字符串）
# 生成方式: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=替换为强随机字符串

# PostgreSQL（compose 内部服务，通常不需要修改）
POSTGRES_USER=studyuser
POSTGRES_PASSWORD=替换为强密码
POSTGRES_DB=ti_db

# 连接池（可选调优）
# DB_POOL_SIZE=10
# DB_MAX_OVERFLOW=20
# DB_POOL_RECYCLE=300

# 微信小程序
WECHAT_APPID=你的AppID
WECHAT_SECRET=你的AppSecret

# AI 解析（可选）
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_API_KEY=你的DashScope密钥

# Nginx 反代
PROXY_FIX_ENABLED=true
SESSION_COOKIE_SECURE=true
ENVEOF
```

> `DATABASE_URL` 不需要在 `.env.production` 中设置——`compose.prod.yml` 会自动从 `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` 拼接。

### 4.2 compose.prod.yml 说明

`compose.prod.yml` 已包含完整的 4 服务定义：

- `web`：依赖 postgres（healthcheck 通过后启动）和 redis
- `worker`：同上
- `postgres`：postgres:16-alpine，数据持久化到 `postgres_data` volume
- `redis`：redis:7-alpine，AOF 持久化到 `redis_data` volume

`DATABASE_URL` 在 compose 中自动拼接为：

```
postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

---

## 5. 构建与启动

### 5.1 方式 A：服务器构建（推荐首次部署）

```bash
cd /opt/saksk-ti

# 构建镜像并启动
docker compose --env-file .env.production -f compose.prod.yml build
docker compose --env-file .env.production -f compose.prod.yml up -d

# 查看状态
docker compose --env-file .env.production -f compose.prod.yml ps
```

### 5.2 方式 B：本地构建上传镜像

本地构建（PowerShell）：

```powershell
cd E:\Project\Ti

# 清理旧镜像
docker rmi saksk-ti:latest 2>$null; $null
docker builder prune -a -f

# 构建
docker build --no-cache -t saksk-ti:latest -f docker/Dockerfile .

# 导出
docker save saksk-ti:latest -o saksk-ti-latest.tar
gzip saksk-ti-latest.tar
```

上传到服务器：

```bash
rsync -avP saksk-ti-latest.tar.gz user@server:/opt/saksk-ti/
```

服务器加载：

```bash
cd /opt/saksk-ti
gunzip saksk-ti-latest.tar.gz
docker load -i saksk-ti-latest.tar

docker compose --env-file .env.production -f compose.prod.yml up -d --force-recreate
rm saksk-ti-latest.tar
```

### 5.3 验证启动

```bash
# 检查所有服务状态
docker compose --env-file .env.production -f compose.prod.yml ps

# 本机连通测试
curl -sS http://127.0.0.1:8000/api/ping
# 期望: {"status":"success","data":{"pong":true}}

# 查看日志
docker compose --env-file .env.production -f compose.prod.yml logs -f web
```

---

## 6. 数据库初始化与迁移

### 6.1 首次部署（空数据库）

PostgreSQL 容器启动后会自动创建数据库。需要运行 Alembic 迁移建表：

```bash
cd /opt/saksk-ti
DC="docker compose --env-file .env.production -f compose.prod.yml"

# 运行迁移（在 web 容器内执行）
$DC exec web flask db upgrade

# 验证表已创建
$DC exec postgres psql -U studyuser -d ti_db -c "\dt"
```

### 6.2 从 SQLite 迁移数据（可选）

如果需要从旧的 SQLite 数据库迁移数据，参考 `docs/PostgreSQL切换教程.md`。

### 6.3 后续模型变更

```bash
# 生成迁移脚本
$DC exec web flask db migrate -m "描述变更内容"

# 检查生成的迁移文件后执行
$DC exec web flask db upgrade
```

---

## 7. Nginx + HTTPS

微信小程序生产环境要求 HTTPS。推荐 Nginx 终止 TLS，反代到 `127.0.0.1:8000`。

### 7.1 安装

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 7.2 签发证书

```bash
# 准备 ACME 目录
sudo mkdir -p /var/www/certbot

# 临时 80 站点（用于 Let's Encrypt 校验）
sudo tee /etc/nginx/sites-available/saksk.top.conf >/dev/null << 'NGINX'
server {
    listen 80;
    server_name saksk.top;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 "ok"; }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/saksk.top.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl enable --now nginx

# 签发证书
sudo certbot certonly --webroot -w /var/www/certbot -d saksk.top
```

### 7.3 站点配置

证书签发成功后，替换为完整配置：

```nginx
# /etc/nginx/sites-available/saksk.top.conf
server {
    listen 80;
    server_name saksk.top;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name saksk.top;

    ssl_certificate     /etc/letsencrypt/live/saksk.top/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/saksk.top/privkey.pem;

    client_max_body_size 20m;

    # 静态文件直出
    location /uploads/ {
        alias /opt/saksk-ti/var/uploads/;
        add_header Cache-Control "public, max-age=604800";
        try_files $uri =404;
    }

    location /static/ {
        alias /opt/saksk-ti/static/;
        add_header Cache-Control "public, max-age=604800";
        try_files $uri =404;
    }

    # 反代到后端
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_buffering off;
        proxy_read_timeout 300;
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx

# 验证
curl -sS https://saksk.top/api/ping
```

### 7.4 证书自动续期

```bash
# 测试续期
sudo certbot renew --dry-run
# certbot 安装时已自动配置 systemd timer
```

---

## 8. 小程序侧配置

### 8.1 API 地址

`miniprogram-1/miniprogram/utils/config.ts` 中设置：

```ts
const PROD_API_BASE_URL = "https://saksk.top/api";
```

### 8.2 微信后台域名白名单

微信公众平台 -> 小程序 -> 开发管理 -> 开发设置：

- request 合法域名：`https://saksk.top`
- uploadFile 合法域名：`https://saksk.top`
- downloadFile 合法域名：`https://saksk.top`
- 业务域名（web-view）：`https://saksk.top`

---

## 9. 运维常用命令

以下命令均在 `/opt/saksk-ti` 目录下执行。为简洁，用 `DC` 代替公共前缀：

```bash
DC="docker compose --env-file .env.production -f compose.prod.yml"
```

### 服务管理

```bash
$DC ps                          # 查看状态
$DC logs -f web                 # 实时日志
$DC logs --tail=200 web         # 最近 200 行
$DC restart web worker          # 重启 web 和 worker
$DC down                        # 停止并删除容器
$DC up -d                       # 启动
```

### 更新部署

```bash
# git 方式
git pull
$DC build web worker
$DC up -d --force-recreate web worker

# 本地镜像方式
docker load -i saksk-ti-latest.tar
$DC up -d --force-recreate web worker
```

### 数据库操作

```bash
# 进入 psql
$DC exec postgres psql -U studyuser -d ti_db

# 常用查询
$DC exec postgres psql -U studyuser -d ti_db -c "SELECT count(*) FROM users;"
$DC exec postgres psql -U studyuser -d ti_db -c "\dt"
$DC exec postgres psql -U studyuser -d ti_db -c "\d users"

# 运行迁移
$DC exec web flask db upgrade
```

### 磁盘清理

```bash
docker system df                # 查看占用
docker image prune -f           # 清理悬空镜像
docker system prune -f          # 清理未使用资源
docker builder prune -a -f      # 清理构建缓存
```

### 快捷别名（可选）

添加到 `~/.bashrc`：

```bash
alias saksk-ps="docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml ps"
alias saksk-logs="docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml logs -f"
alias saksk-restart="docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml restart"
alias saksk-up="docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml up -d"
alias saksk-down="docker compose --env-file .env.production -f /opt/saksk-ti/compose.prod.yml down"
```

---

## 10. 备份与恢复

### 10.1 备份

```bash
cd /opt/saksk-ti
DC="docker compose --env-file .env.production -f compose.prod.yml"

# PostgreSQL 数据库备份
$DC exec -T postgres pg_dump -U studyuser -d ti_db > backup-$(date +%%F).sql

# 上传文件备份
tar -czf uploads-backup-$(date +%%F).tar.gz var/uploads/

# 完整备份（数据库 + 上传文件）
$DC exec -T postgres pg_dump -U studyuser -d ti_db | gzip > var/backup-db-$(date +%%F).sql.gz
tar -czf backup-full-$(date +%%F).tar.gz var/backup-db-*.sql.gz var/uploads/
```

### 10.2 恢复

```bash
# 恢复数据库
$DC exec -T postgres psql -U studyuser -d ti_db < backup-2026-02-25.sql

# 恢复上传文件
tar -xzf uploads-backup-2026-02-25.tar.gz
```

### 10.3 定期备份（cron）

```bash
crontab -e
```

添加：

```cron
# 每天凌晨 3 点备份 PostgreSQL
0 3 * * * cd /opt/saksk-ti && docker compose --env-file .env.production -f compose.prod.yml exec -T postgres pg_dump -U studyuser -d ti_db | gzip > /opt/saksk-ti/var/backup-$(date +\%%F).sql.gz

# 保留最近 30 天备份
0 4 * * * find /opt/saksk-ti/var/backup-*.sql.gz -mtime +30 -delete
```

---

## 11. 常见故障排查

### 11.1 502/504（Nginx 反代失败）

```bash
curl http://127.0.0.1:8000/api/ping    # 后端是否通
$DC ps                                  # web 是否在跑
$DC logs -f web                         # Gunicorn 日志
sudo nginx -t                           # Nginx 配置
```

### 11.2 web 启动失败：数据库连接拒绝

```bash
# 检查 postgres 是否健康
$DC ps postgres
$DC logs postgres

# 手动测试连接
$DC exec postgres psql -U studyuser -d ti_db -c "SELECT 1;"
```

常见原因：
- postgres 容器未启动或 healthcheck 未通过
- `.env.production` 中 `POSTGRES_PASSWORD` 与已有数据卷中的密码不一致（首次创建后密码写入 volume，后续修改 env 不会生效）

解决密码不一致：

```bash
# 方式 1：删除 volume 重建（会丢失数据，仅首次部署可用）
$DC down -v
$DC up -d

# 方式 2：进入容器修改密码
$DC exec postgres psql -U studyuser -c "ALTER USER studyuser PASSWORD '新密码';"
```

### 11.3 413（上传太大）

Nginx 配置 `client_max_body_size 20m;`（第 7.3 节已包含）。

### 11.4 小程序提示域名不合法

- 检查微信后台域名白名单（第 8.2 节）
- 确认 HTTPS 证书链完整

### 11.5 拉取镜像超时

参考第 2.2 节配置镜像加速器。

### 11.6 端口 8000 被占用

```bash
sudo ss -ltnp | grep ':8000'
```

如果是其他容器占用，停止后重启；或修改 `compose.prod.yml` 端口映射为 `127.0.0.1:8001:8000`，同步修改 Nginx upstream。

### 11.7 Alembic 迁移报错

```bash
# 查看当前迁移版本
$DC exec web flask db current

# 标记为最新（跳过迁移）
$DC exec web flask db stamp head

# 回滚一个版本
$DC exec web flask db downgrade -1
```

---

## 12. 安全提醒

- `SECRET_KEY` 必须是强随机字符串，只存在服务器 `.env.production` 中
- `POSTGRES_PASSWORD` 使用强密码，不要用默认值
- 仓库/历史中出现过的密钥，立即去对应平台重置
- 对公网只开放 `80/443`，不暴露 `8000` 和 `5432`
- `.env.production` 不入库（已在 `.gitignore` 中排除）
- 定期备份数据库和上传文件
