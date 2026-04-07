#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_DOMAIN="${DOMAIN:-saksk.top}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
APP_DIR="${APP_DIR:-$ROOT_DIR}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.production}"
SKIP_CERTBOT="${SKIP_CERTBOT:-0}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-mirrors.aliyun.com}"
PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"
PIP_RETRIES="${PIP_RETRIES:-10}"
POSTGRES_DB="${POSTGRES_DB:-ti_db}"
POSTGRES_USER="${POSTGRES_USER:-studyuser}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)}"
SECRET_KEY="${SECRET_KEY:-$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)}"

if [[ "$SKIP_CERTBOT" != "1" && -z "$CERTBOT_EMAIL" ]]; then
  echo "错误：未设置 CERTBOT_EMAIL。"
  echo "示例：DOMAIN=saksk.top CERTBOT_EMAIL=admin@saksk.top ./scripts/deploy_ubuntu24.sh"
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1 && [[ "$(id -u)" -ne 0 ]]; then
  echo "错误：当前用户不是 root，且系统中没有 sudo。"
  exit 1
fi

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

install_base_packages() {
  log "安装系统依赖"
  $SUDO apt-get update
  $SUDO apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    openssl \
    git \
    nginx \
    snapd \
    ufw \
    dnsutils
  $SUDO systemctl enable --now nginx
  $SUDO systemctl enable --now snapd
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker 与 Compose 已安装，跳过"
    return
  fi

  log "安装 Docker Engine 与 Compose 插件"
  $SUDO install -m 0755 -d /etc/apt/keyrings
  $SUDO curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  $SUDO chmod a+r /etc/apt/keyrings/docker.asc

  $SUDO tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

  $SUDO apt-get update
  $SUDO apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
  $SUDO systemctl enable --now docker
}

prepare_runtime_files() {
  log "创建数据目录"
  mkdir -p \
    "$ROOT_DIR/var/postgres" \
    "$ROOT_DIR/var/redis" \
    "$ROOT_DIR/var/uploads" \
    "$ROOT_DIR/var/instance" \
    "$ROOT_DIR/var/logs" \
    "$ROOT_DIR/backups"

  if [[ ! -f "$ENV_FILE" ]]; then
    log "生成最小化 .env.production（邮件 / AI / 短信 改为后台设置）"
    cat > "$ENV_FILE" <<EOF
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
PROXY_FIX_ENABLED=true
SESSION_COOKIE_SECURE=true
BACKUP_TZ=Asia/Shanghai
BACKUP_ANCHOR_TIME=04:00
BACKUP_INTERVAL=43200
BACKUP_CHECK_INTERVAL=60
BACKUP_RETENTION_DAYS=7
EOF
  else
    log "检测到已有 .env.production，保留现有内容"
  fi

  log "使用 compose.prod.yml 内置的 127.0.0.1:8080 端口映射"
}

deploy_stack() {
  log "构建镜像（PyPI 镜像: ${PIP_INDEX_URL}）"
  $SUDO docker build \
    --build-arg PIP_INDEX_URL="$PIP_INDEX_URL" \
    --build-arg PIP_TRUSTED_HOST="$PIP_TRUSTED_HOST" \
    --build-arg PIP_DEFAULT_TIMEOUT="$PIP_DEFAULT_TIMEOUT" \
    --build-arg PIP_RETRIES="$PIP_RETRIES" \
    -t saksk-ti:latest \
    -f "$ROOT_DIR/docker/Dockerfile" \
    "$ROOT_DIR"

  log "启动生产容器"
  $SUDO docker compose \
    --env-file "$ENV_FILE" \
    -f "$ROOT_DIR/compose.prod.yml" \
    up -d

  log "执行数据库迁移"
  $SUDO docker compose \
    --env-file "$ENV_FILE" \
    -f "$ROOT_DIR/compose.prod.yml" \
    exec web flask db upgrade
}

configure_host_nginx() {
  log "配置宿主机 Nginx 反向代理"
  $SUDO tee /etc/nginx/sites-available/ti.conf > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${APP_DOMAIN};

    client_max_body_size 10m;

    location /sse/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding off;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Request-ID \$request_id;
        proxy_connect_timeout 10s;
        proxy_read_timeout 65s;
        proxy_send_timeout 65s;
    }
}
EOF

  $SUDO ln -sf /etc/nginx/sites-available/ti.conf /etc/nginx/sites-enabled/ti.conf
  $SUDO nginx -t
  $SUDO systemctl reload nginx
}

configure_firewall() {
  log "配置防火墙"
  $SUDO ufw allow OpenSSH
  $SUDO ufw allow 'Nginx Full'
  $SUDO ufw --force enable
}

install_certbot() {
  if [[ "$SKIP_CERTBOT" == "1" ]]; then
    log "已设置 SKIP_CERTBOT=1，跳过 HTTPS 证书签发"
    return
  fi

  log "安装 Certbot"
  $SUDO snap install core
  $SUDO snap refresh core
  $SUDO snap install --classic certbot
  $SUDO ln -sf /snap/bin/certbot /usr/bin/certbot

  if [[ ! -d "/etc/letsencrypt/live/${APP_DOMAIN}" ]]; then
    log "申请 HTTPS 证书"
    $SUDO certbot --nginx \
      -d "$APP_DOMAIN" \
      --redirect \
      -m "$CERTBOT_EMAIL" \
      --agree-tos \
      --no-eff-email
  else
    log "检测到 ${APP_DOMAIN} 证书已存在，跳过首次签发"
  fi
}

validate_deploy() {
  log "校验容器状态"
  $SUDO docker compose \
    --env-file "$ENV_FILE" \
    -f "$ROOT_DIR/compose.prod.yml" \
    ps

  log "校验健康检查"
  curl -fsS http://127.0.0.1:8080/api/ping | python3 -m json.tool

  if [[ "$SKIP_CERTBOT" == "1" ]]; then
    curl -I "http://${APP_DOMAIN}" || true
  else
    curl -I "https://${APP_DOMAIN}" || true
    curl -fsS "https://${APP_DOMAIN}/api/ping" | python3 -m json.tool
  fi
}

print_summary() {
  log "部署完成"
  cat <<EOF
域名：${APP_DOMAIN}
项目目录：${APP_DIR}
环境文件：${ENV_FILE}

后续首次登录后台后，请到以下页面补齐运行时配置：
  - /admin/settings/mail
  - /admin/settings/sms
  - /admin/settings/ai

说明：
  - 邮件、AI、短信配置已支持优先从后台系统设置读取；
  - 本脚本生成的是最小化 .env.production，不再要求你在 env 中填写这些服务密钥。
EOF
}

install_base_packages
install_docker
prepare_runtime_files
deploy_stack
configure_host_nginx
configure_firewall
install_certbot
validate_deploy
print_summary
