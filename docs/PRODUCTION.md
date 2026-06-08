# Docker 镜像发布与一键部署指南（Ti）

> 目标：开发者本地构建并推送 `ghcr.io/saksk-it/ti:latest`，服务器部署脚本默认拉取最新镜像，并自动完成环境文件、Docker Compose、Nginx、HTTPS、迁移和健康检查。

## 1. 部署架构

生产环境默认链路：

```text
公网 80/443
  -> 宿主机 Nginx + Certbot
  -> 127.0.0.1:8080
  -> Docker Compose 内 nginx
  -> web / worker / postgres / redis / backup
```

开发环境默认链路：

```text
127.0.0.1:8000
  -> Docker Compose web
  -> postgres / redis / worker / backup
```

生产 Compose 内的 nginx 会读取服务器仓库目录的 `./static`、`./docker/nginx.conf` 和 `./var/uploads`。因此服务器仍应保留仓库文件；应用镜像负责承载运行环境和代码。

## 2. 开发者发布最新镜像

复制整段命令运行，按提示输入 GitHub 用户名和 PAT。脚本默认会同时推送当前提交短 SHA 标签和 `latest` 标签。

```bash
cd /Users/sak/Documents/GitHub/Ti

read -r -p "GitHub 用户名: " GHCR_USERNAME
read -r -s -p "GitHub PAT: " GHCR_TOKEN
printf '\n'

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

PLATFORMS=linux/amd64 \
./scripts/publish_image.sh

docker pull ghcr.io/saksk-it/ti:latest
docker image inspect ghcr.io/saksk-it/ti:latest --format '{{.RepoTags}} {{.Id}}'

unset GHCR_TOKEN
```

如果需要同时发布 amd64 和 arm64，复制整段运行：

```bash
cd /Users/sak/Documents/GitHub/Ti

read -r -p "GitHub 用户名: " GHCR_USERNAME
read -r -s -p "GitHub PAT: " GHCR_TOKEN
printf '\n'

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

PLATFORMS=linux/amd64,linux/arm64 \
./scripts/publish_image.sh

unset GHCR_TOKEN
```

安全要求：

- 不要把真实 `GHCR_TOKEN` 写进仓库、文档、截图或 `.env.production`；
- 生产发布完成后，服务器默认拉取 `ghcr.io/saksk-it/ti:latest`；
- 如需回滚或灰度，可额外用 `TAG=xxx ./scripts/publish_image.sh` 发布明确标签，但默认教程统一使用 `latest`。

## 3. 服务器一键生产部署

复制整段命令在 Ubuntu 24.04 LTS 服务器运行，按提示输入域名和证书邮箱：

```bash
read -r -p "部署目录 [/opt/ti]: " APP_DIR
APP_DIR="${APP_DIR:-/opt/ti}"
read -r -p "域名 [saksk.top]: " DOMAIN
DOMAIN="${DOMAIN:-saksk.top}"
read -r -p "Certbot 邮箱: " CERTBOT_EMAIL
REPO_URL="https://github.com/Saksk-IT/Ti.git"

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

DOMAIN="$DOMAIN" \
CERTBOT_EMAIL="$CERTBOT_EMAIL" \
./scripts/deploy_ubuntu24.sh
```

脚本默认拉取：

```text
ghcr.io/saksk-it/ti:latest
```

脚本会自动完成：

- 安装系统依赖、Docker Engine、Docker Compose 插件、Nginx、Certbot；
- 创建 `var/postgres`、`var/redis`、`var/uploads`、`var/instance`、`var/logs`、`backups`；
- 生成最小化 `.env.production` 并设置 `600` 权限；
- 拉取最新应用镜像与 Compose 依赖镜像；
- 启动生产容器并执行 `flask db upgrade`；
- 配置宿主机 Nginx 反代到 `127.0.0.1:8080`；
- 申请 HTTPS 证书并执行健康检查。

## 4. 私有 GHCR 镜像部署

如果 GitHub Packages 是私有可见性，复制整段命令运行，按提示输入 GHCR 只读凭据：

```bash
read -r -p "部署目录 [/opt/ti]: " APP_DIR
APP_DIR="${APP_DIR:-/opt/ti}"
read -r -p "域名 [saksk.top]: " DOMAIN
DOMAIN="${DOMAIN:-saksk.top}"
read -r -p "Certbot 邮箱: " CERTBOT_EMAIL
read -r -p "GitHub 用户名: " GHCR_USERNAME
read -r -s -p "GHCR 只读 Token: " GHCR_TOKEN
printf '\n'
REPO_URL="https://github.com/Saksk-IT/Ti.git"

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

DOMAIN="$DOMAIN" \
CERTBOT_EMAIL="$CERTBOT_EMAIL" \
GHCR_USERNAME="$GHCR_USERNAME" \
GHCR_TOKEN="$GHCR_TOKEN" \
./scripts/deploy_ubuntu24.sh

unset GHCR_TOKEN
```

## 5. 临时 HTTP / 内网部署

不申请 HTTPS 证书时使用下面命令。生产默认 `SESSION_COOKIE_SECURE=true`，HTTP 下 Web Session Cookie 不会发送；公网和小程序正式环境应使用 HTTPS。

```bash
read -r -p "部署目录 [/opt/ti]: " APP_DIR
APP_DIR="${APP_DIR:-/opt/ti}"
read -r -p "域名或内网主机名 [127.0.0.1]: " DOMAIN
DOMAIN="${DOMAIN:-127.0.0.1}"
REPO_URL="https://github.com/Saksk-IT/Ti.git"

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

DOMAIN="$DOMAIN" \
SKIP_CERTBOT=1 \
./scripts/deploy_ubuntu24.sh
```

## 6. 服务器一键开发部署

开发环境同样默认拉取 `ghcr.io/saksk-it/ti:latest`。端口默认只绑定本机，避免数据库暴露公网。

```bash
read -r -p "开发部署目录 [/opt/ti-dev]: " APP_DIR
APP_DIR="${APP_DIR:-/opt/ti-dev}"
REPO_URL="https://github.com/Saksk-IT/Ti.git"

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

DEPLOY_ENV=development \
./scripts/deploy_ubuntu24.sh
```

默认访问：

```text
http://127.0.0.1:8000
```

如需临时开放 Web 给内网访问，同时保持 PostgreSQL 只绑定本机：

```bash
cd /opt/ti-dev

DEPLOY_ENV=development \
WEB_BIND=0.0.0.0 \
POSTGRES_BIND=127.0.0.1 \
./scripts/deploy_ubuntu24.sh
```

## 7. 完整命令式部署

不使用一键脚本时，下面命令会自动生成 `.env.production`：

```bash
read -r -p "部署目录 [/opt/ti]: " APP_DIR
APP_DIR="${APP_DIR:-/opt/ti}"
REPO_URL="https://github.com/Saksk-IT/Ti.git"

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR"

cat > .env.production <<EOF
FLASK_ENV=production
TI_IMAGE=ghcr.io/saksk-it/ti:latest
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
mkdir -p var/postgres var/redis var/uploads var/instance var/logs backups
chmod 700 backups

docker pull ghcr.io/saksk-it/ti:latest
docker compose --env-file .env.production -f compose.prod.yml pull
docker compose --env-file .env.production -f compose.prod.yml up -d --remove-orphans
docker compose --env-file .env.production -f compose.prod.yml exec -T web flask db upgrade

docker compose --env-file .env.production -f compose.prod.yml ps
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

## 8. 更新部署

开发者先发布最新镜像：

```bash
cd /Users/sak/Documents/GitHub/Ti

read -r -p "GitHub 用户名: " GHCR_USERNAME
read -r -s -p "GitHub PAT: " GHCR_TOKEN
printf '\n'

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

PLATFORMS=linux/amd64 \
./scripts/publish_image.sh

unset GHCR_TOKEN
```

服务器拉取最新代码配置和最新镜像：

```bash
cd /opt/ti

read -r -p "域名 [saksk.top]: " DOMAIN
DOMAIN="${DOMAIN:-saksk.top}"
read -r -p "Certbot 邮箱: " CERTBOT_EMAIL

git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"

DOMAIN="$DOMAIN" \
CERTBOT_EMAIL="$CERTBOT_EMAIL" \
./scripts/deploy_ubuntu24.sh
```

## 9. 日常运维完整命令

查看状态：

```bash
cd /opt/ti
docker compose --env-file .env.production -f compose.prod.yml ps
```

查看日志：

```bash
cd /opt/ti
docker compose --env-file .env.production -f compose.prod.yml logs -f web
```

重启：

```bash
cd /opt/ti
docker compose --env-file .env.production -f compose.prod.yml restart
```

手动备份：

```bash
cd /opt/ti
./scripts/backup.sh
ls -lh backups/
```

恢复备份：

```bash
cd /opt/ti
read -r -p "备份文件名: " BACKUP_FILE
./scripts/restore.sh "$BACKUP_FILE"
```

备份包可能包含数据库、上传文件、日志和 `.env.production`，必须按密钥级别保护，不要提交到 Git。

## 10. 安全检查完整命令

```bash
cd /opt/ti

stat -c '%a %n' .env.production backups

docker compose --env-file .env.production -f compose.prod.yml config > /tmp/ti-compose-check.yml
if grep -q 'build:' /tmp/ti-compose-check.yml; then
  echo '错误：生产 Compose 不应包含 build 配置'
  exit 1
fi

grep -E '^TI_IMAGE=ghcr.io/saksk-it/ti:latest$' .env.production
grep -E '^SESSION_COOKIE_SECURE=true$' .env.production

if grep -E '^POSTGRES_PASSWORD=studypass$|^SECRET_KEY=dev-secret-key' .env.production; then
  echo '错误：生产环境不能使用开发默认密钥或密码'
  exit 1
fi

ss -tlnp | grep -E ':80|:443|:8080' || true
curl -fsS "https://$(grep -E '^DOMAIN=' .env.production 2>/dev/null | cut -d= -f2- || echo saksk.top)/api/ping" | python3 -m json.tool || true
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

## 11. 常见故障完整命令

镜像拉取失败：

```bash
docker pull ghcr.io/saksk-it/ti:latest
docker login ghcr.io
```

数据库密码不匹配：

```bash
cd /opt/ti
test -f .env.production && stat -c '%a %n' .env.production
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 postgres
```

如果 `var/postgres` 已存在，PostgreSQL 内部密码不会因为重新生成 env 自动变化。应恢复原 `.env.production`，或使用旧 `POSTGRES_PASSWORD` 重新部署。

HTTPS 正常但静态资源异常：

```bash
cd /opt/ti
git status --short
git rev-parse HEAD
docker inspect "$(docker compose --env-file .env.production -f compose.prod.yml ps -q web)" --format '{{.Config.Image}}'
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 nginx
```

应用容器启动失败：

```bash
cd /opt/ti
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 web
```
