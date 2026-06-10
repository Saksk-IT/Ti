# Docker 镜像发布与一键部署指南（Ti）

> 目标：开发者在本地构建并推送 `ghcr.io/saksk-it/ti:latest`；服务器脚本默认只拉取最新镜像并启动 Docker 栈，达到 `http://服务器IP:8080` 可访问。域名与 HTTPS 单独作为生产环境后续配置。

## 1. 部署边界

默认生产部署链路：

```text
服务器 IP:8080
  -> Docker Compose 内 nginx
  -> web / worker / postgres / redis / backup
```

默认开发部署链路：

```text
127.0.0.1:8000
  -> Docker Compose web
  -> postgres / redis / worker / backup
```

默认生产部署不配置域名、不申请 HTTPS、不占用宿主机 80/443。生产 Compose 内的 nginx 会读取服务器仓库目录的 `./static`、`./docker/nginx.conf` 和 `./var/uploads`，因此服务器仍应保留仓库文件；应用运行代码由镜像提供。

## 2. 开发者发布 latest 镜像

复制整段命令在开发者本机运行。脚本默认会同时推送当前提交短 SHA 标签和 `latest` 标签，服务器部署默认只拉取 `latest`。

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

如果服务器包含 amd64 和 arm64，复制整段运行：

```bash
cd /Users/sak/Documents/GitHub/Ti

read -r -p "GitHub 用户名: " GHCR_USERNAME
read -r -s -p "GitHub PAT: " GHCR_TOKEN
printf '\n'

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

PLATFORMS=linux/amd64,linux/arm64 \
./scripts/publish_image.sh

docker pull ghcr.io/saksk-it/ti:latest
docker image inspect ghcr.io/saksk-it/ti:latest --format '{{.RepoTags}} {{.Id}}'

unset GHCR_TOKEN
```

安全要求：

- 不要把真实 `GHCR_TOKEN` 写进仓库、文档、截图或 `.env.production`。
- 默认发布和默认部署统一使用 `ghcr.io/saksk-it/ti:latest`。
- 如需回滚，可额外用 `TAG=xxx ./scripts/publish_image.sh` 发布明确标签；常规部署教程仍以 `latest` 为准。

## 3. 服务器一键生产部署

复制整段命令在 Ubuntu 24.04 LTS 服务器运行。完成后访问 `http://服务器IP:8080`。

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

./scripts/deploy_ubuntu24.sh
```

脚本默认写入并拉取：

```text
TI_IMAGE=ghcr.io/saksk-it/ti:latest
TI_IMAGE_PULL_POLICY=always
HTTP_BIND=0.0.0.0
HTTP_PORT=8080
SESSION_COOKIE_SECURE=false
```

脚本会自动完成：

- 安装基础依赖、Docker Engine、Docker Compose 插件；
- 创建 `var/postgres`、`var/redis`、`var/uploads`、`var/instance`、`var/logs`、`backups`；
- 生成最小化 `.env.production` 并设置 `600` 权限；
- 拉取最新应用镜像与 Compose 依赖镜像；
- 启动生产容器并执行 `flask db upgrade`；
- 校验 `http://127.0.0.1:8080/api/ping`。

如果服务器启用了本机防火墙，复制运行：

```bash
sudo ufw allow 8080/tcp
sudo ufw status
```

云服务器还需要在云厂商安全组放行入站 TCP `8080`。验证命令：

```bash
SERVER_IP="$(curl -fsS https://api.ipify.org || hostname -I | awk '{print $1}')"
printf '访问地址：http://%s:8080\n' "$SERVER_IP"

curl -fsS "http://127.0.0.1:8080/api/ping" | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

## 4. 私有 GHCR 镜像生产部署

如果 GitHub Packages 是私有可见性，复制整段命令运行，按提示输入 GHCR 只读凭据。Token 只临时进入当前 shell，不写入仓库文件。

```bash
read -r -p "部署目录 [/opt/ti]: " APP_DIR
APP_DIR="${APP_DIR:-/opt/ti}"
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

GHCR_USERNAME="$GHCR_USERNAME" \
GHCR_TOKEN="$GHCR_TOKEN" \
./scripts/deploy_ubuntu24.sh

unset GHCR_TOKEN
```

## 5. 服务器一键开发部署

开发环境同样默认拉取 `ghcr.io/saksk-it/ti:latest`。默认只绑定本机，避免开发服务和数据库直接暴露公网。

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

如需临时开放 Web 给内网访问，同时保持 PostgreSQL 只绑定本机，复制运行：

```bash
cd /opt/ti-dev

DEPLOY_ENV=development \
WEB_BIND=0.0.0.0 \
POSTGRES_BIND=127.0.0.1 \
./scripts/deploy_ubuntu24.sh
```

## 6. 生产环境域名与 HTTPS 后续配置

这一节只适用于生产环境。先完成第 3 节，确认 `http://服务器IP:8080` 可访问，并确保 DNS 已经解析到服务器 IP。

```bash
cd /opt/ti

read -r -p "域名: " DOMAIN

dig +short "$DOMAIN"
curl -I "http://$DOMAIN" || true
```

确认解析正确后执行下面命令。脚本会把 Docker 内 nginx 改为只绑定 `127.0.0.1:8080`，宿主机 Nginx 接管 80/443，并将 `DOMAIN`、`CERTBOT_EMAIL`、`SESSION_COOKIE_SECURE=true` 写回 `.env.production`。

```bash
cd /opt/ti

read -r -p "域名: " DOMAIN
read -r -p "Certbot 邮箱: " CERTBOT_EMAIL

ENABLE_HTTPS=1 \
DOMAIN="$DOMAIN" \
CERTBOT_EMAIL="$CERTBOT_EMAIL" \
./scripts/deploy_ubuntu24.sh
```

执行后验证：

```bash
cd /opt/ti

grep -E '^(HTTP_BIND|HTTP_PORT|SESSION_COOKIE_SECURE)=' .env.production
DOMAIN="$(grep -E '^DOMAIN=' .env.production | cut -d= -f2-)"
curl -fsS "https://$DOMAIN/api/ping" | python3 -m json.tool
```

## 7. 完整命令式生产部署

不使用一键脚本时，复制整段运行。该流程仍然只拉取镜像，不在服务器构建镜像。

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
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=$(python3 -c "import secrets, string; alphabet=string.ascii_letters+string.digits; password=[secrets.choice(string.ascii_lowercase), secrets.choice(string.ascii_uppercase), secrets.choice(string.digits)]; password.extend(secrets.choice(alphabet) for _ in range(21)); secrets.SystemRandom().shuffle(password); print(''.join(password))")
DEFAULT_ADMIN_PHONE=
DEFAULT_ADMIN_EMAIL=admin@ti.local
DEFAULT_ADMIN_RESET_PASSWORD=0
PROXY_FIX_ENABLED=true
HTTP_BIND=0.0.0.0
HTTP_PORT=8080
SESSION_COOKIE_SECURE=false
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
docker compose --env-file .env.production -f compose.prod.yml exec -T web flask ensure-default-admin

docker compose --env-file .env.production -f compose.prod.yml ps
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

## 8. 更新部署

开发者先发布 latest 镜像：

```bash
cd /Users/sak/Documents/GitHub/Ti

read -r -p "GitHub 用户名: " GHCR_USERNAME
read -r -s -p "GitHub PAT: " GHCR_TOKEN
printf '\n'

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

PLATFORMS=linux/amd64 \
./scripts/publish_image.sh

docker image inspect ghcr.io/saksk-it/ti:latest --format '{{.RepoTags}} {{.Id}}'

unset GHCR_TOKEN
```

服务器拉取最新代码配置和 latest 镜像：

```bash
cd /opt/ti

git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"
./scripts/deploy_ubuntu24.sh
```

如果已启用生产 HTTPS，更新时继续显式传入 HTTPS 参数：

```bash
cd /opt/ti

read -r -p "域名: " DOMAIN
read -r -p "Certbot 邮箱: " CERTBOT_EMAIL

git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD)"

ENABLE_HTTPS=1 \
DOMAIN="$DOMAIN" \
CERTBOT_EMAIL="$CERTBOT_EMAIL" \
./scripts/deploy_ubuntu24.sh
```

如果更新后脚本停在健康检查并返回 `502`，但 `docker compose ps` 显示 `ti-web-1` 为 `healthy`，通常是 Docker 内 nginx 在 web 容器更新后仍缓存旧 upstream 地址。先不要重置数据库或删除 `var/`，复制下面命令重启 Docker 内 nginx 后再验证：

```bash
cd /opt/ti

docker compose --env-file .env.production -f compose.prod.yml ps
docker compose --env-file .env.production -f compose.prod.yml restart nginx

curl --retry 10 --retry-delay 3 --retry-all-errors -fsS \
  "http://127.0.0.1:8080/api/ping" | python3 -m json.tool

DOMAIN="$(grep -E '^DOMAIN=' .env.production | cut -d= -f2-)"
curl --retry 10 --retry-delay 3 --retry-all-errors -fsS \
  "https://$DOMAIN/api/ping" | python3 -m json.tool
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

默认 IP 部署检查：

```bash
cd /opt/ti

stat -c '%a %n' .env.production backups

docker compose --env-file .env.production -f compose.prod.yml config > /tmp/ti-compose-check.yml
if grep -q 'build:' /tmp/ti-compose-check.yml; then
  echo '错误：生产 Compose 不应包含 build 配置'
  exit 1
fi

grep -E '^TI_IMAGE=ghcr.io/saksk-it/ti:latest$' .env.production
grep -E '^TI_IMAGE_PULL_POLICY=always$' .env.production
grep -E '^HTTP_BIND=0.0.0.0$' .env.production
grep -E '^HTTP_PORT=8080$' .env.production
grep -E '^SESSION_COOKIE_SECURE=false$' .env.production

if grep -E '^POSTGRES_PASSWORD=studypass$|^SECRET_KEY=dev-secret-key' .env.production; then
  echo '错误：生产环境不能使用开发默认密钥或密码'
  exit 1
fi

ss -tlnp | grep -E ':8080' || true
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

启用 HTTPS 后追加检查：

```bash
cd /opt/ti

grep -E '^HTTP_BIND=127.0.0.1$' .env.production
grep -E '^SESSION_COOKIE_SECURE=true$' .env.production
ss -tlnp | grep -E ':80|:443|:8080' || true

read -r -p "域名: " DOMAIN
curl -fsS "https://$DOMAIN/api/ping" | python3 -m json.tool
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

IP 无法访问但本机健康检查正常：

```bash
cd /opt/ti
grep -E '^(HTTP_BIND|HTTP_PORT)=' .env.production
ss -tlnp | grep ':8080' || true
sudo ufw status || true
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
```

应用容器启动失败：

```bash
cd /opt/ti
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 web
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 nginx
```

HTTPS 部署或更新后健康检查返回 `502`：

```bash
cd /opt/ti

docker compose --env-file .env.production -f compose.prod.yml ps
docker compose --env-file .env.production -f compose.prod.yml restart nginx

curl --retry 10 --retry-delay 3 --retry-all-errors -fsS \
  "http://127.0.0.1:8080/api/ping" | python3 -m json.tool

DOMAIN="$(grep -E '^DOMAIN=' .env.production | cut -d= -f2-)"
curl --retry 10 --retry-delay 3 --retry-all-errors -fsS \
  "https://$DOMAIN/api/ping" | python3 -m json.tool
```

如果重启 Docker 内 nginx 后仍然是 `502`，继续收集反代链路日志：

```bash
cd /opt/ti

docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 nginx
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 web
sudo nginx -t
sudo journalctl -u nginx -n 100 --no-pager
```
