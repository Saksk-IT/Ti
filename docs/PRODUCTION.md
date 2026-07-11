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

同一台开发机只需要登录一次 GHCR。Docker Desktop 会把登录态保存到系统凭据管理器；后续发布直接运行发布脚本，不需要重复输入用户名和 PAT。

首次登录时复制运行：

```bash
cd /Users/sak/Documents/GitHub/Ti

printf 'GitHub 用户名: '
IFS= read -r GHCR_USERNAME
printf 'GitHub PAT（需要 write:packages）: '
IFS= read -r -s GHCR_TOKEN
printf '\n'

printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

unset GHCR_TOKEN
```

日常发布 amd64 镜像时复制运行。脚本默认会同时推送当前提交短 SHA 标签和 `latest` 标签，服务器部署默认只拉取 `latest`。

```bash
cd /Users/sak/Documents/GitHub/Ti

PLATFORMS=linux/amd64 \
./scripts/publish_image.sh

docker pull ghcr.io/saksk-it/ti:latest
docker image inspect ghcr.io/saksk-it/ti:latest --format '{{.RepoTags}} {{.Id}}'
```

如果服务器包含 amd64 和 arm64，日常发布改用：

```bash
cd /Users/sak/Documents/GitHub/Ti

PLATFORMS=linux/amd64,linux/arm64 \
./scripts/publish_image.sh

docker pull ghcr.io/saksk-it/ti:latest
docker image inspect ghcr.io/saksk-it/ti:latest --format '{{.RepoTags}} {{.Id}}'
```

安全要求：

- 不要把真实 `GHCR_TOKEN` 写进仓库、文档、截图或 `.env.production`。
- 开发者发布镜像的 PAT 至少需要 `write:packages` 权限；服务器只拉取私有镜像时使用只读 Token，至少需要 `read:packages` 权限。
- 只有在新机器首次发布、执行过 `docker logout ghcr.io`、PAT 过期或权限被撤销时，才需要重新登录。
- 默认发布和默认部署统一使用 `ghcr.io/saksk-it/ti:latest`。
- 如需回滚，可额外用 `TAG=xxx ./scripts/publish_image.sh` 发布明确标签；常规部署教程仍以 `latest` 为准。

## 3. 服务器一键生产部署

复制整段命令在 Ubuntu 24.04 LTS 服务器运行。完成后访问 `http://服务器IP:8080`。

```bash
printf '部署目录 [/opt/ti]: '
IFS= read -r APP_DIR
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

如果 GitHub Packages 是私有可见性，服务器也只需要登录一次 GHCR。因为部署脚本使用 `sudo docker`，登录命令也要用 `sudo docker login`，这样后续常规部署不需要重复传只读 Token。

```bash
printf 'GitHub 用户名: '
IFS= read -r GHCR_USERNAME
printf 'GHCR 只读 Token（需要 read:packages）: '
IFS= read -r -s GHCR_TOKEN
printf '\n'

printf '%s' "$GHCR_TOKEN" | sudo docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin

unset GHCR_TOKEN
```

登录完成后，按第 3 节的一键生产部署命令执行即可。若不想在服务器保存 Docker 登录态，也可以临时传入只读 Token：

```bash
printf '部署目录 [/opt/ti]: '
IFS= read -r APP_DIR
APP_DIR="${APP_DIR:-/opt/ti}"
printf 'GitHub 用户名: '
IFS= read -r GHCR_USERNAME
printf 'GHCR 只读 Token（需要 read:packages）: '
IFS= read -r -s GHCR_TOKEN
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
printf '开发部署目录 [/opt/ti-dev]: '
IFS= read -r APP_DIR
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

这一节只适用于生产环境。先完成第 3 节，确认 `http://服务器IP:8080` 可访问，并确保所有域名的 DNS 都已经解析到服务器 IP。主域名写入 `DOMAIN`，额外域名写入 `EXTRA_DOMAINS`，多个额外域名用空格或逗号分隔。

```bash
cd /opt/ti

printf '主域名 [saksk.top]: '
IFS= read -r DOMAIN
DOMAIN="${DOMAIN:-saksk.top}"
printf '额外域名 [ti.saksk.top]: '
IFS= read -r EXTRA_DOMAINS
EXTRA_DOMAINS="${EXTRA_DOMAINS:-ti.saksk.top}"

for name in $DOMAIN ${EXTRA_DOMAINS//,/ }; do
  echo "== $name =="
  dig +short "$name"
  curl -I "http://$name" || true
done
```

确认解析正确后执行下面命令。脚本会把 Docker 内 nginx 改为只绑定 `127.0.0.1:8080`，宿主机 Nginx 接管 80/443，为 `DOMAIN` 和 `EXTRA_DOMAINS` 申请或扩展同一张证书，并将 `ENABLE_HTTPS=1`、`DOMAIN`、`EXTRA_DOMAINS`、`CERTBOT_EMAIL`、`SESSION_COOKIE_SECURE=true` 写回 `.env.production`。

```bash
cd /opt/ti

printf '主域名 [saksk.top]: '
IFS= read -r DOMAIN
DOMAIN="${DOMAIN:-saksk.top}"
printf '额外域名 [ti.saksk.top]: '
IFS= read -r EXTRA_DOMAINS
EXTRA_DOMAINS="${EXTRA_DOMAINS:-ti.saksk.top}"
printf 'Certbot 邮箱: '
IFS= read -r CERTBOT_EMAIL

ENABLE_HTTPS=1 \
DOMAIN="$DOMAIN" \
EXTRA_DOMAINS="$EXTRA_DOMAINS" \
CERTBOT_EMAIL="$CERTBOT_EMAIL" \
./scripts/deploy_ubuntu24.sh
```

执行后验证：

```bash
cd /opt/ti

grep -E '^(DOMAIN|EXTRA_DOMAINS|HTTP_BIND|HTTP_PORT|SESSION_COOKIE_SECURE)=' .env.production
DOMAIN="$(grep -E '^DOMAIN=' .env.production | cut -d= -f2-)"
EXTRA_DOMAINS="$(grep -E '^EXTRA_DOMAINS=' .env.production | cut -d= -f2-)"
for name in $DOMAIN ${EXTRA_DOMAINS//,/ }; do
  curl -fsS "https://$name/api/ping" | python3 -m json.tool
done
```

## 7. 完整命令式生产部署

不使用一键脚本时，复制整段运行。该流程仍然只拉取镜像，不在服务器构建镜像。

```bash
printf '部署目录 [/opt/ti]: '
IFS= read -r APP_DIR
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
RATELIMIT_LIMIT_MULTIPLIER=100
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
docker compose --env-file .env.production -f compose.prod.yml up -d postgres redis
docker compose --env-file .env.production -f compose.prod.yml run --rm --no-deps web flask db upgrade
docker compose --env-file .env.production -f compose.prod.yml run --rm --no-deps web flask ensure-default-admin
docker compose --env-file .env.production -f compose.prod.yml up -d --remove-orphans

docker compose --env-file .env.production -f compose.prod.yml ps
curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool
curl -fsS "http://127.0.0.1:8080/api/ping?deep=1" | python3 -m json.tool
```

## 8. 更新部署

开发者先发布 latest 镜像：

```bash
cd /Users/sak/Documents/GitHub/Ti

PLATFORMS=linux/amd64 \
./scripts/publish_image.sh

docker image inspect ghcr.io/saksk-it/ti:latest --format '{{.RepoTags}} {{.Id}}'
```

服务器拉取最新代码配置和 latest 镜像。日常更新优先使用这个入口，它会自动执行 `git pull --ff-only`，然后调用生产部署脚本：

```bash
cd /opt/ti

./scripts/update_production.sh
```

如果已启用生产 HTTPS，`.env.production` 中保存了 `ENABLE_HTTPS=1`、`DOMAIN`、`EXTRA_DOMAINS` 和 `CERTBOT_EMAIL` 后，日常更新仍然只需要执行：

```bash
cd /opt/ti

./scripts/update_production.sh
```

这个入口会在生产更新后默认重启 Docker 内 nginx，刷新 web 容器更新后的 upstream 连接；如果健康检查首次失败，也会再重启 Docker 内 nginx 后重试。它还会在证书已存在时重新写入宿主机 443 SSL 反代配置，因此通常不需要再手动执行“重启 Docker 内 nginx”和“重新配置 HTTPS”两段命令。

如果 `.env.production` 还没有保存 HTTPS 参数，或者是首次启用 HTTPS / 新增额外域名，显式传入一次：

```bash
cd /opt/ti

printf '主域名 [saksk.top]: '
IFS= read -r DOMAIN
DOMAIN="${DOMAIN:-saksk.top}"
printf '额外域名 [ti.saksk.top]: '
IFS= read -r EXTRA_DOMAINS
EXTRA_DOMAINS="${EXTRA_DOMAINS:-ti.saksk.top}"
printf 'Certbot 邮箱: '
IFS= read -r CERTBOT_EMAIL

ENABLE_HTTPS=1 \
DOMAIN="$DOMAIN" \
EXTRA_DOMAINS="$EXTRA_DOMAINS" \
CERTBOT_EMAIL="$CERTBOT_EMAIL" \
./scripts/update_production.sh
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
printf '备份文件名: '
IFS= read -r BACKUP_FILE
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
grep -E '^RATELIMIT_LIMIT_MULTIPLIER=100$' .env.production

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

printf '域名: '
IFS= read -r DOMAIN
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

HTTPS 部署或更新后健康检查返回 `502` 时，优先重新运行一次完善后的生产更新入口。脚本会自动拉取当前分支、重启 Docker 内 nginx 并重试健康检查：

```bash
cd /opt/ti

./scripts/update_production.sh
```

如果仍然失败，再手动确认容器状态和反代链路：

```bash
cd /opt/ti

docker compose --env-file .env.production -f compose.prod.yml ps
docker compose --env-file .env.production -f compose.prod.yml restart nginx

curl --retry 10 --retry-delay 3 --retry-all-errors -fsS \
  "http://127.0.0.1:8080/api/ping" | python3 -m json.tool

DOMAIN="$(grep -E '^DOMAIN=' .env.production | cut -d= -f2-)"
EXTRA_DOMAINS="$(grep -E '^EXTRA_DOMAINS=' .env.production | cut -d= -f2-)"
for name in $DOMAIN ${EXTRA_DOMAINS//,/ }; do
  curl --retry 10 --retry-delay 3 --retry-all-errors -fsS \
    "https://$name/api/ping" | python3 -m json.tool
done
```

如果重启 Docker 内 nginx 后仍然是 `502`，继续收集反代链路日志：

```bash
cd /opt/ti

docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 nginx
docker compose --env-file .env.production -f compose.prod.yml logs --tail=200 web
sudo nginx -t
sudo journalctl -u nginx -n 100 --no-pager
```

HTTP 正常但 HTTPS 握手失败时，先用生产更新入口重新写入宿主机 443 SSL 配置：

```bash
cd /opt/ti

curl -I "http://saksk.top" || true
curl -k -I "https://saksk.top" || true
curl -I "http://ti.saksk.top" || true
curl -k -I "https://ti.saksk.top" || true
sudo nginx -T | sed -n '/server_name saksk.top ti.saksk.top/,+80p'

./scripts/update_production.sh
```
## 12. 两台服务器一键迁移生产数据

本流程适用于服务器 1 已通过一键部署脚本运行完整生产环境、服务器 2 使用相同 Ubuntu 24.04 系统的场景。执行入口位于服务器 2：它从服务器 1 拉取 PostgreSQL、Redis、`var/uploads`、`var/instance` 和必要业务配置，并在失败时恢复两端。

### 12.1 服务器 2 全新部署

先在服务器 2 完成本章第 3 节的一键生产部署。私有 GHCR 镜像还必须先按第 4 节在服务器 2 独立完成只读登录；迁移不会复制服务器 1 的 Docker 登录凭据。

```bash
cd /opt/ti
./scripts/deploy_ubuntu24.sh

curl -fsS 'http://127.0.0.1:8080/api/ping' | python3 -m json.tool
curl -fsS 'http://127.0.0.1:8080/api/ping?deep=1' | python3 -m json.tool
```

此时先使用服务器 IP 和 HTTP 验证，不要提前切换 DNS，也不要复制服务器 1 的 TLS 证书。

### 12.2 准备专用 SSH 密钥和可信主机指纹

在服务器 2 创建专用密钥，并把公钥加入服务器 1 对应用户的 `~/.ssh/authorized_keys`：

```bash
install -d -m 700 ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/ti-production-migration -C ti-production-migration
ssh-copy-id -i ~/.ssh/ti-production-migration.pub ubuntu@服务器1IP
```

`ssh-keyscan` 取得的内容本身未经认证。先生成待核验文件，再用云厂商控制台、服务器 1 本地控制台或其他可信通道取得真实 SSH 指纹，进行人工核验；只有完全一致才能启用：

```bash
ssh-keyscan -p 22 -t ed25519 服务器1IP \
  > ~/.ssh/ti-production-migration.known_hosts.pending

ssh-keygen -lf ~/.ssh/ti-production-migration.known_hosts.pending
# 与服务器 1 可信控制台执行下列命令的结果逐字比较：
# sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub

mv ~/.ssh/ti-production-migration.known_hosts.pending \
  ~/.ssh/ti-production-migration.known_hosts
chmod 600 ~/.ssh/ti-production-migration.known_hosts

ssh -i ~/.ssh/ti-production-migration \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  ubuntu@服务器1IP 'sudo -n true && echo READY'
```

两端当前用户必须是 root，或 `sudo -n true` 能够成功；正式迁移期间不会交互读取 sudo 密码。

### 12.3 先执行 dry-run

dry-run 会校验两端部署目录、Docker Compose、机器身份、磁盘空间、PostgreSQL/Redis 主版本、应用镜像 digest、SSH 信任和服务器 2 健康状态，但不会停止服务、创建迁移包或覆盖数据。

```bash
cd /opt/ti

./scripts/migrate_production_data.sh \
  --source ubuntu@服务器1IP \
  --source-dir /opt/ti \
  --identity-file "$HOME/.ssh/ti-production-migration" \
  --known-hosts "$HOME/.ssh/ti-production-migration.known_hosts" \
  --dry-run
```

必须先处理 dry-run 报告的镜像 digest、版本、磁盘或健康检查差异，再进入最终迁移。

### 12.4 执行最终迁移

选择低峰维护窗口，在服务器 2 运行：

```bash
cd /opt/ti

./scripts/migrate_production_data.sh \
  --source ubuntu@服务器1IP \
  --source-dir /opt/ti \
  --identity-file "$HOME/.ssh/ti-production-migration" \
  --known-hosts "$HOME/.ssh/ti-production-migration.known_hosts"
```

脚本会显示包含源主机和目标主机名的唯一确认文本，例如：

```text
MIGRATE 192.0.2.10 TO ti-new.example.internal
```

必须原样输入；`yes` 不会绕过覆盖确认。确认后脚本先创建服务器 2 的一致性回滚包，再停止服务器 1 的入口、Web、worker、backup 和 Redis，导出并校验最终快照。因此实际停机窗口从服务器 1 冻结开始，持续到服务器 2 完成恢复和深度健康检查。

迁移包与校验文件包含配置和业务数据，默认在成功后删除。仅在受控排障时增加 `--keep-bundle`，并确保目录权限为 `700`、文件权限为 `600`，使用完立即安全删除。

### 12.5 成功、失败与人工恢复

成功后服务器 1 保持停止，防止两端继续写入造成数据分叉；服务器 1 的原始数据库和文件不会删除。至少保留服务器 1 **24～72 小时**，完成业务验收后再人工下线。

任一校验、数据库恢复、Redis 恢复、文件替换、迁移或健康检查失败时，脚本会执行失败自动回滚：恢复服务器 2 的迁移前快照，并让服务器 1 只恢复迁移前原本运行的服务。两个恢复动作相互独立，一个失败不会阻止另一个继续尝试。

如果日志提示“目标已验证且源端提交结果不确定”，说明服务器 2 已通过完整验证，但 SSH 未能确认服务器 1 的 `finalize` 应答。为避免数据分叉，脚本会保留服务器 2 的新数据、保持服务器 1 停止并保留目标迁移锁；此时不要执行 `resume` 或删除目标锁，应先重新上传 helper，以同一迁移 ID 幂等执行 `finalize`，确认 `STATUS=FINALIZED` 后再人工清理锁和临时文件。

若日志明确提示服务器 1 自动恢复未完全成功，先停止切换操作。在服务器 2 重新上传当前 helper，并使用日志中的迁移 ID 手工执行 `resume`：

```bash
MIGRATION_ID='替换为失败日志中的迁移ID'
REMOTE_TMP="$(ssh -i ~/.ssh/ti-production-migration \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  ubuntu@服务器1IP 'mktemp -d /tmp/ti-production-migration.XXXXXX')"

ssh -i ~/.ssh/ti-production-migration \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  ubuntu@服务器1IP "mkdir -m 700 '$REMOTE_TMP/lib'"

scp -i ~/.ssh/ti-production-migration \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  scripts/export_production_data.sh \
  "ubuntu@服务器1IP:$REMOTE_TMP/export_production_data.sh"
scp -i ~/.ssh/ti-production-migration \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  scripts/lib/production_migration_common.sh \
  "ubuntu@服务器1IP:$REMOTE_TMP/lib/production_migration_common.sh"

ssh -i ~/.ssh/ti-production-migration \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  ubuntu@服务器1IP \
  "bash '$REMOTE_TMP/export_production_data.sh' resume --source-dir /opt/ti --migration-id '$MIGRATION_ID'; rm -rf -- '$REMOTE_TMP'"
```

对于前述“源端提交结果不确定”场景，完成同样的 helper 上传后，**不要执行上面的 `resume`**，改为幂等重试 `finalize`。只有收到 `STATUS=FINALIZED` 后，才能删除服务器 2 上由同一迁移 ID 持有的目标锁：

```bash
ssh -i ~/.ssh/ti-production-migration \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  ubuntu@服务器1IP \
  "bash '$REMOTE_TMP/export_production_data.sh' finalize --source-dir /opt/ti --migration-id '$MIGRATION_ID'"

TARGET_LOCK='/opt/ti/var/.production-data-migration.lock'
if sudo test "$(sudo cat "$TARGET_LOCK/owner")" = "$MIGRATION_ID"; then
  sudo rm -rf -- "$TARGET_LOCK"
else
  echo '目标锁 owner 不匹配，拒绝删除' >&2
  exit 1
fi

ssh -i ~/.ssh/ti-production-migration \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$HOME/.ssh/ti-production-migration.known_hosts" \
  ubuntu@服务器1IP "rm -rf -- '$REMOTE_TMP'"
```

### 12.6 DNS、HTTPS 与业务切换

自动迁移全部成功后再执行：

1. 将 DNS A/AAAA 记录指向服务器 2，并移除不再使用的旧地址；
2. 在服务器 2 按第 6 节重新运行 `deploy_ubuntu24.sh`，签发服务器 2 自己的 HTTPS 证书；
3. 验证域名的 `/api/ping` 与 `/api/ping?deep=1`；
4. 验证管理员和普通用户登录、上传文件读取、后台任务与定时备份；
5. 更新微信、短信、邮件、AI 上游、对象存储等第三方平台的源 IP 白名单与回调配置；
6. 观察服务器 2 日志和资源使用情况，确认稳定后再安排服务器 1 下线。
