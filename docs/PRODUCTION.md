# Docker 镜像发布与一键部署指南（Ti）

> 目标：应用镜像由开发者在本地构建并推送到 GitHub Container Registry（GHCR），服务器只负责拉取镜像、生成环境文件、启动 Docker Compose 栈，并按需配置宿主机 Nginx 与 HTTPS。

## 1. 部署架构

生产环境默认链路：

```text
公网 80/443
  -> 宿主机 Nginx + Certbot
  -> 127.0.0.1:8080
  -> Docker Compose 内 nginx
  -> web / worker / postgres / redis / backup
```

开发环境链路：

```text
127.0.0.1:8000
  -> Docker Compose web
  -> postgres / redis / worker / backup
```

注意：生产 Compose 内的 nginx 仍从服务器仓库目录读取 `./static`、`./docker/nginx.conf` 和 `./var/uploads`。因此服务器仍应保留与镜像同版本的仓库文件，镜像只承载应用运行环境和代码。

## 2. 开发者本地发布镜像

首次登录 GHCR：

```bash
export GHCR_USERNAME=你的GitHub用户名
export GHCR_TOKEN=你的GitHub PAT
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
```

Token 只需要按仓库权限授予发布所需权限；不要写进仓库、文档、截图或部署 env。

发布明确版本镜像：

```bash
TAG=2026.06.08-1 \
PUSH_LATEST=1 \
./scripts/publish_image.sh
```

常用参数：

```text
IMAGE_NAME=ghcr.io/saksk-it/ti   镜像名
TAG=<git短SHA>                   默认标签
PLATFORMS=linux/amd64            默认面向常见云服务器
PUSH_LATEST=1                    同时推送 latest
PUSH_DEV=1                       同时推送 dev
PUSH=0                           只本地构建，不推送
```

如果开发机是 Apple Silicon，而服务器是 x86_64，请保持 `PLATFORMS=linux/amd64`，或发布多架构镜像：

```bash
PLATFORMS=linux/amd64,linux/arm64 TAG=2026.06.08-1 PUSH_LATEST=1 ./scripts/publish_image.sh
```

生产部署建议使用明确版本 tag 或 digest，例如：

```text
ghcr.io/saksk-it/ti:2026.06.08-1
```

## 3. 服务器一键生产部署

准备 Ubuntu 24.04 LTS 服务器、域名 A 记录、80/443 端口和 sudo 权限。服务器上克隆仓库：

```bash
export APP_DIR=/opt/ti
sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"
git clone https://github.com/Saksk-IT/Ti.git "$APP_DIR"
cd "$APP_DIR"
```

公开镜像部署：

```bash
DOMAIN=saksk.top \
CERTBOT_EMAIL=admin@saksk.top \
TI_IMAGE=ghcr.io/saksk-it/ti:2026.06.08-1 \
./scripts/deploy_ubuntu24.sh
```

私有 GHCR 镜像部署：

```bash
DOMAIN=saksk.top \
CERTBOT_EMAIL=admin@saksk.top \
TI_IMAGE=ghcr.io/saksk-it/ti:2026.06.08-1 \
GHCR_USERNAME=你的GitHub用户名 \
GHCR_TOKEN=只读packages令牌 \
./scripts/deploy_ubuntu24.sh
```

脚本会自动完成：

- 安装系统依赖、Docker Engine、Docker Compose 插件、Nginx、Certbot；
- 创建 `var/postgres`、`var/redis`、`var/uploads`、`var/instance`、`var/logs`、`backups`；
- 生成最小化 `.env.production` 并设置 `600` 权限；
- 拉取 `TI_IMAGE` 与 Compose 依赖镜像；
- 启动生产容器并执行 `flask db upgrade`；
- 配置宿主机 Nginx 反代到 `127.0.0.1:8080`；
- 申请 HTTPS 证书并执行健康检查。

临时 HTTP / 内网部署：

```bash
DOMAIN=你的域名或内网主机名 \
SKIP_CERTBOT=1 \
TI_IMAGE=ghcr.io/saksk-it/ti:2026.06.08-1 \
./scripts/deploy_ubuntu24.sh
```

说明：`SESSION_COOKIE_SECURE=true` 是生产默认值，HTTP 模式下 Web Session Cookie 不会发送，这是安全取舍；正式小程序和公网部署仍应使用 HTTPS。

## 4. 服务器一键开发部署

开发环境也可从 GHCR 拉取镜像。默认只绑定本机端口，避免 PostgreSQL 暴露公网：

```bash
DEPLOY_ENV=development \
TI_IMAGE=ghcr.io/saksk-it/ti:dev \
./scripts/deploy_ubuntu24.sh
```

默认访问：

```text
http://127.0.0.1:8000
```

如需临时给内网访问：

```bash
DEPLOY_ENV=development \
WEB_BIND=0.0.0.0 \
POSTGRES_BIND=127.0.0.1 \
TI_IMAGE=ghcr.io/saksk-it/ti:dev \
./scripts/deploy_ubuntu24.sh
```

不要在公网服务器上开放 `POSTGRES_BIND=0.0.0.0`，除非已有防火墙和访问控制。

## 5. 手动部署命令

如果不使用一键脚本，可手动创建 `.env.production`：

```bash
cat > .env.production <<EOF
FLASK_ENV=production
TI_IMAGE=ghcr.io/saksk-it/ti:2026.06.08-1
TI_IMAGE_PULL_POLICY=always
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
POSTGRES_USER=studyuser
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
POSTGRES_DB=ti_db
PROXY_FIX_ENABLED=true
SESSION_COOKIE_SECURE=true
BACKUP_TZ=Asia/Shanghai
BACKUP_ANCHOR_TIME=04:00
BACKUP_INTERVAL=43200
BACKUP_CHECK_INTERVAL=60
BACKUP_RETENTION_DAYS=7
EOF
chmod 600 .env.production
```

启动：

```bash
mkdir -p var/postgres var/redis var/uploads var/instance var/logs backups
chmod 700 backups

docker pull ghcr.io/saksk-it/ti:2026.06.08-1
docker compose --env-file .env.production -f compose.prod.yml pull
docker compose --env-file .env.production -f compose.prod.yml up -d --remove-orphans
docker compose --env-file .env.production -f compose.prod.yml exec -T web flask db upgrade
```

验证：

```bash
docker compose --env-file .env.production -f compose.prod.yml ps
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

## 6. 更新部署

开发者先发布新镜像，例如：

```bash
TAG=2026.06.08-2 PUSH_LATEST=1 ./scripts/publish_image.sh
```

服务器同步同版本仓库文件并拉取新镜像：

```bash
cd /opt/ti
git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"

TI_IMAGE=ghcr.io/saksk-it/ti:2026.06.08-2 \
DOMAIN=saksk.top \
CERTBOT_EMAIL=admin@saksk.top \
./scripts/deploy_ubuntu24.sh
```

如果 `.env.production` 已存在，脚本会保留原文件。要改镜像 tag，可编辑 `.env.production` 中的 `TI_IMAGE`，或在命令行临时传入 `TI_IMAGE=...` 后重新运行脚本。

## 7. 日常运维

查看状态：

```bash
docker compose --env-file .env.production -f compose.prod.yml ps
```

查看日志：

```bash
docker compose --env-file .env.production -f compose.prod.yml logs -f web
docker compose --env-file .env.production -f compose.prod.yml logs -f nginx
docker compose --env-file .env.production -f compose.prod.yml logs -f backup
```

重启：

```bash
docker compose --env-file .env.production -f compose.prod.yml restart
```

手动备份：

```bash
./scripts/backup.sh
```

恢复备份：

```bash
./scripts/restore.sh backup_20260608_040000.tar.gz
```

备份包可能包含数据库、上传文件、日志和 `.env.production`，必须按密钥级别保护，不要提交到 Git。

## 8. 安全检查清单

- `.env.production` 权限为 `600`，`backups/` 权限不对同机普通用户开放；
- `POSTGRES_PASSWORD` 不是 `studypass`，`SECRET_KEY` 不是开发默认值；
- `docker compose --env-file .env.production -f compose.prod.yml config` 中没有 `build:`；
- 生产只对公网监听 `80/443`，`8080` 只绑定 `127.0.0.1`，PostgreSQL / Redis 不暴露公网；
- GHCR Token 只通过 `--password-stdin` 登录，不写入项目 env；
- 发布生产时优先使用明确 tag 或 digest，而不是只依赖 `latest`；
- 健康检查通过：

```bash
curl -fsS https://saksk.top/api/ping | python3 -m json.tool
curl -fsS "https://saksk.top/api/ping?deep=1" | python3 -m json.tool
```

## 9. 常见故障

### 镜像拉取失败

检查镜像名、tag、网络和 GHCR 权限：

```bash
docker pull ghcr.io/saksk-it/ti:2026.06.08-1
docker login ghcr.io
```

私有镜像需要 `GHCR_USERNAME` 和 `GHCR_TOKEN`，token 至少具备读取包权限。

### 数据库密码不匹配

如果 `var/postgres` 已存在，PostgreSQL 内部密码不会因为重新生成 env 自动变化。应恢复原 `.env.production`，或使用旧 `POSTGRES_PASSWORD` 重新部署。

### HTTPS 正常但静态资源异常

生产 nginx 从服务器 `./static` 目录读取静态资源。确认服务器仓库文件已同步到与镜像一致的版本：

```bash
git status --short
git rev-parse HEAD
docker inspect "$(docker compose --env-file .env.production -f compose.prod.yml ps -q web)" --format '{{.Config.Image}}'
```

### 应用容器启动失败

```bash
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 web
```

优先检查 `SECRET_KEY`、`POSTGRES_PASSWORD`、`REDIS_URL`、镜像 tag 和迁移日志。
