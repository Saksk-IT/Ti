#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DEPLOY_ENV="${DEPLOY_ENV:-production}"
case "$DEPLOY_ENV" in
  production|development) ;;
  *)
    echo "错误：DEPLOY_ENV 只能是 production 或 development，当前值：${DEPLOY_ENV}"
    exit 1
    ;;
esac

if [[ "$DEPLOY_ENV" == "production" ]]; then
  DEFAULT_ENV_FILE="$ROOT_DIR/.env.production"
  DEFAULT_COMPOSE_FILE="$ROOT_DIR/compose.prod.yml"
  DEFAULT_TI_IMAGE="ghcr.io/saksk-it/ti:latest"
else
  DEFAULT_ENV_FILE="$ROOT_DIR/.env.development"
  DEFAULT_COMPOSE_FILE="$ROOT_DIR/compose.dev.yml"
  DEFAULT_TI_IMAGE="ghcr.io/saksk-it/ti:latest"
fi

REQUESTED_ENABLE_HTTPS="${ENABLE_HTTPS-}"
ENABLE_HTTPS="${ENABLE_HTTPS:-0}"
case "$ENABLE_HTTPS" in
  0|1) ;;
  *)
    echo "错误：ENABLE_HTTPS 只能是 0 或 1，当前值：${ENABLE_HTTPS}"
    exit 1
    ;;
esac

if [[ "$ENABLE_HTTPS" == "1" && "$DEPLOY_ENV" != "production" ]]; then
  echo "错误：ENABLE_HTTPS=1 仅支持生产环境。"
  exit 1
fi

APP_DOMAIN="${DOMAIN:-}"
EXTRA_DOMAINS="${EXTRA_DOMAINS:-}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
APP_DIR="${APP_DIR:-$ROOT_DIR}"
ENV_FILE="${ENV_FILE:-$DEFAULT_ENV_FILE}"
COMPOSE_FILE="${COMPOSE_FILE:-$DEFAULT_COMPOSE_FILE}"
REQUESTED_DOMAIN="${DOMAIN-}"
REQUESTED_EXTRA_DOMAINS="${EXTRA_DOMAINS-}"
REQUESTED_CERTBOT_EMAIL="${CERTBOT_EMAIL-}"
REQUESTED_TI_IMAGE="${TI_IMAGE-}"
REQUESTED_TI_IMAGE_PULL_POLICY="${TI_IMAGE_PULL_POLICY-}"
REQUESTED_HTTP_BIND="${HTTP_BIND-}"
REQUESTED_HTTP_PORT="${HTTP_PORT-}"
REQUESTED_SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE-}"
TI_IMAGE="${TI_IMAGE:-$DEFAULT_TI_IMAGE}"
TI_IMAGE_PULL_POLICY="${TI_IMAGE_PULL_POLICY:-always}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
ENSURE_DEFAULT_ADMIN="${ENSURE_DEFAULT_ADMIN:-1}"
RESTART_INTERNAL_NGINX="${RESTART_INTERNAL_NGINX:-1}"
ALLOW_INSECURE_DEFAULTS="${ALLOW_INSECURE_DEFAULTS:-0}"
POSTGRES_DB="${POSTGRES_DB:-ti_db}"
POSTGRES_USER="${POSTGRES_USER:-studyuser}"
DEFAULT_ADMIN_USERNAME="${DEFAULT_ADMIN_USERNAME:-admin}"
DEFAULT_ADMIN_PHONE="${DEFAULT_ADMIN_PHONE:-}"
DEFAULT_ADMIN_EMAIL="${DEFAULT_ADMIN_EMAIL:-admin@ti.local}"
DEFAULT_ADMIN_RESET_PASSWORD="${DEFAULT_ADMIN_RESET_PASSWORD:-0}"
DEFAULT_ADMIN_PASSWORD="${DEFAULT_ADMIN_PASSWORD:-}"
RATELIMIT_LIMIT_MULTIPLIER="${RATELIMIT_LIMIT_MULTIPLIER:-100}"
HTTP_BIND="${HTTP_BIND:-$([[ "$ENABLE_HTTPS" == "1" ]] && printf '127.0.0.1' || printf '0.0.0.0')}"
HTTP_PORT="${HTTP_PORT:-8080}"
SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-$([[ "$ENABLE_HTTPS" == "1" ]] && printf 'true' || printf 'false')}"
APP_DOMAINS=""
HOST_NGINX_CONFIG_PATH="${HOST_NGINX_CONFIG_PATH:-/etc/nginx/sites-available/ti.conf}"
HOST_NGINX_ENABLED_PATH="${HOST_NGINX_ENABLED_PATH:-/etc/nginx/sites-enabled/ti.conf}"

if ! command -v sudo >/dev/null 2>&1 && [[ "$(id -u)" -ne 0 ]]; then
  echo "错误：当前用户不是 root，且系统中没有 sudo。"
  exit 1
fi

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

COMPOSE=($SUDO docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  echo "错误：$*" >&2
  exit 1
}

append_app_domain() {
  local domain="$1"
  [[ -n "$domain" ]] || return

  if [[ ! "$domain" =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$ ]]; then
    fail "域名格式不合法：${domain}"
  fi

  case " ${APP_DOMAINS} " in
    *" ${domain} "*) return ;;
  esac

  APP_DOMAINS="${APP_DOMAINS:+${APP_DOMAINS} }${domain}"
}

build_app_domains() {
  local raw_extra_domains domain
  APP_DOMAINS=""
  append_app_domain "$APP_DOMAIN"

  raw_extra_domains="${EXTRA_DOMAINS//,/ }"
  for domain in $raw_extra_domains; do
    append_app_domain "$domain"
  done
}

random_secret() {
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
    return
  fi

  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n'
    printf '\n'
    return
  fi

  fail "无法生成随机密钥：缺少 python3 和 openssl"
}

random_password() {
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import secrets
import string

alphabet = string.ascii_letters + string.digits
password = [
    secrets.choice(string.ascii_lowercase),
    secrets.choice(string.ascii_uppercase),
    secrets.choice(string.digits),
]
password.extend(secrets.choice(alphabet) for _ in range(21))
secrets.SystemRandom().shuffle(password)
print("".join(password))
PY
    return
  fi

  local raw
  raw="$(random_secret | tr -cd 'A-Za-z0-9' | head -c 24)"
  printf 'A1%s\n' "$raw"
}

postgres_has_existing_data() {
  [[ -s "$ROOT_DIR/var/postgres/PG_VERSION" || -d "$ROOT_DIR/var/postgres/base" ]]
}

load_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
  fi

  if [[ -n "$REQUESTED_ENABLE_HTTPS" ]]; then
    ENABLE_HTTPS="$REQUESTED_ENABLE_HTTPS"
  fi

  if [[ -n "$REQUESTED_DOMAIN" ]]; then
    APP_DOMAIN="$REQUESTED_DOMAIN"
  else
    APP_DOMAIN="${DOMAIN:-$APP_DOMAIN}"
  fi
  if [[ -n "$REQUESTED_EXTRA_DOMAINS" ]]; then
    EXTRA_DOMAINS="$REQUESTED_EXTRA_DOMAINS"
  fi
  if [[ -n "$REQUESTED_CERTBOT_EMAIL" ]]; then
    CERTBOT_EMAIL="$REQUESTED_CERTBOT_EMAIL"
  else
    CERTBOT_EMAIL="${CERTBOT_EMAIL:-$CERTBOT_EMAIL}"
  fi

  if [[ "$DEPLOY_ENV" == "production" && -z "$REQUESTED_ENABLE_HTTPS" ]]; then
    if [[ "${ENABLE_HTTPS:-0}" == "1" ]]; then
      ENABLE_HTTPS="1"
    elif [[ -n "$APP_DOMAIN" && -n "$CERTBOT_EMAIL" ]]; then
      ENABLE_HTTPS="1"
    elif [[ "${HTTP_BIND:-}" == "127.0.0.1" && "${SESSION_COOKIE_SECURE:-}" == "true" ]]; then
      ENABLE_HTTPS="1"
    else
      ENABLE_HTTPS="0"
    fi
  fi

  case "$ENABLE_HTTPS" in
    0|1) ;;
    *)
      echo "错误：ENABLE_HTTPS 只能是 0 或 1，当前值：${ENABLE_HTTPS}"
      exit 1
      ;;
  esac
  if [[ "$ENABLE_HTTPS" == "1" && "$DEPLOY_ENV" != "production" ]]; then
    echo "错误：ENABLE_HTTPS=1 仅支持生产环境。"
    exit 1
  fi

  if [[ -n "$REQUESTED_TI_IMAGE" ]]; then
    TI_IMAGE="$REQUESTED_TI_IMAGE"
  else
    TI_IMAGE="$DEFAULT_TI_IMAGE"
  fi
  if [[ -n "$REQUESTED_TI_IMAGE_PULL_POLICY" ]]; then
    TI_IMAGE_PULL_POLICY="$REQUESTED_TI_IMAGE_PULL_POLICY"
  else
    TI_IMAGE_PULL_POLICY="always"
  fi
  if [[ -n "$REQUESTED_HTTP_BIND" ]]; then
    HTTP_BIND="$REQUESTED_HTTP_BIND"
  elif [[ "$ENABLE_HTTPS" == "1" ]]; then
    HTTP_BIND="127.0.0.1"
  else
    HTTP_BIND="0.0.0.0"
  fi
  if [[ -n "$REQUESTED_HTTP_PORT" ]]; then
    HTTP_PORT="$REQUESTED_HTTP_PORT"
  else
    HTTP_PORT="8080"
  fi
  if [[ -n "$REQUESTED_SESSION_COOKIE_SECURE" ]]; then
    SESSION_COOKIE_SECURE="$REQUESTED_SESSION_COOKIE_SECURE"
  elif [[ "$ENABLE_HTTPS" == "1" ]]; then
    SESSION_COOKIE_SECURE="true"
  else
    SESSION_COOKIE_SECURE="false"
  fi
  export TI_IMAGE TI_IMAGE_PULL_POLICY HTTP_BIND HTTP_PORT SESSION_COOKIE_SECURE
  POSTGRES_USER="${POSTGRES_USER:-studyuser}"
  POSTGRES_DB="${POSTGRES_DB:-ti_db}"
  DEFAULT_ADMIN_USERNAME="${DEFAULT_ADMIN_USERNAME:-admin}"
  DEFAULT_ADMIN_PHONE="${DEFAULT_ADMIN_PHONE:-}"
  DEFAULT_ADMIN_EMAIL="${DEFAULT_ADMIN_EMAIL:-admin@ti.local}"
  DEFAULT_ADMIN_RESET_PASSWORD="${DEFAULT_ADMIN_RESET_PASSWORD:-0}"
  if [[ -z "${DEFAULT_ADMIN_PASSWORD:-}" ]]; then
    DEFAULT_ADMIN_PASSWORD="$(random_password)"
  fi
}

upsert_env_value() {
  local key="$1"
  local value="$2"
  local tmp_file
  tmp_file="$(mktemp)"

  if [[ -f "$ENV_FILE" ]] && grep -q "^${key}=" "$ENV_FILE"; then
    awk -v key="$key" -v value="$value" '
      index($0, key "=") == 1 { print key "=" value; next }
      { print }
    ' "$ENV_FILE" > "$tmp_file"
  else
    if [[ -f "$ENV_FILE" ]]; then
      cat "$ENV_FILE" > "$tmp_file"
      printf '%s=%s\n' "$key" "$value" >> "$tmp_file"
    else
      printf '%s=%s\n' "$key" "$value" > "$tmp_file"
    fi
  fi

  cat "$tmp_file" > "$ENV_FILE"
  rm -f "$tmp_file"
}

install_base_packages() {
  log "安装系统依赖"
  $SUDO apt-get update
  $SUDO apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    openssl \
    python3 \
    git
}

install_https_packages() {
  if [[ "$ENABLE_HTTPS" != "1" ]]; then
    return
  fi

  log "安装 HTTPS 后续配置依赖"
  $SUDO apt-get install -y \
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

write_production_env() {
  local secret_key postgres_password default_admin_password
  secret_key="${SECRET_KEY:-$(random_secret)}"
  postgres_password="${POSTGRES_PASSWORD:-$(random_secret)}"
  default_admin_password="${DEFAULT_ADMIN_PASSWORD:-$(random_password)}"

  cat > "$ENV_FILE" <<EOF
FLASK_ENV=production
TI_IMAGE=${TI_IMAGE}
TI_IMAGE_PULL_POLICY=${TI_IMAGE_PULL_POLICY}
SECRET_KEY=${secret_key}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${postgres_password}
POSTGRES_DB=${POSTGRES_DB}
DEFAULT_ADMIN_USERNAME=${DEFAULT_ADMIN_USERNAME}
DEFAULT_ADMIN_PASSWORD=${default_admin_password}
DEFAULT_ADMIN_PHONE=${DEFAULT_ADMIN_PHONE}
DEFAULT_ADMIN_EMAIL=${DEFAULT_ADMIN_EMAIL}
DEFAULT_ADMIN_RESET_PASSWORD=${DEFAULT_ADMIN_RESET_PASSWORD}
RATELIMIT_LIMIT_MULTIPLIER=${RATELIMIT_LIMIT_MULTIPLIER}
PROXY_FIX_ENABLED=true
SESSION_COOKIE_SECURE=${SESSION_COOKIE_SECURE}
HTTP_BIND=${HTTP_BIND}
HTTP_PORT=${HTTP_PORT}
ENABLE_HTTPS=${ENABLE_HTTPS}
BACKUP_TZ=Asia/Shanghai
BACKUP_ANCHOR_TIME=04:00
BACKUP_INTERVAL=43200
BACKUP_CHECK_INTERVAL=60
BACKUP_RETENTION_DAYS=7
EOF
}

write_development_env() {
  cat > "$ENV_FILE" <<EOF
FLASK_ENV=development
TI_IMAGE=${TI_IMAGE}
TI_IMAGE_PULL_POLICY=${TI_IMAGE_PULL_POLICY}
WEB_BIND=${WEB_BIND:-127.0.0.1}
WEB_PORT=${WEB_PORT:-8000}
POSTGRES_BIND=${POSTGRES_BIND:-127.0.0.1}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
SECRET_KEY=${SECRET_KEY:-dev-secret-key}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-studypass}
POSTGRES_DB=${POSTGRES_DB}
DEFAULT_ADMIN_USERNAME=${DEFAULT_ADMIN_USERNAME}
DEFAULT_ADMIN_PASSWORD=${DEFAULT_ADMIN_PASSWORD:-$(random_password)}
DEFAULT_ADMIN_PHONE=${DEFAULT_ADMIN_PHONE}
DEFAULT_ADMIN_EMAIL=${DEFAULT_ADMIN_EMAIL}
DEFAULT_ADMIN_RESET_PASSWORD=${DEFAULT_ADMIN_RESET_PASSWORD}
MAIL_ENABLED=true
MAIL_CONSOLE_OUTPUT=true
SMS_ENABLED=true
SMS_CONSOLE_OUTPUT=true
BACKUP_TZ=Asia/Shanghai
BACKUP_ANCHOR_TIME=04:00
BACKUP_INTERVAL=43200
BACKUP_CHECK_INTERVAL=60
BACKUP_RETENTION_DAYS=3
EOF
}

prepare_runtime_files() {
  log "创建运行目录"
  mkdir -p \
    "$ROOT_DIR/var/postgres" \
    "$ROOT_DIR/var/redis" \
    "$ROOT_DIR/var/uploads" \
    "$ROOT_DIR/var/instance" \
    "$ROOT_DIR/var/logs" \
    "$ROOT_DIR/backups"
  chmod 700 "$ROOT_DIR/backups"

  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ "$DEPLOY_ENV" == "production" && -z "${POSTGRES_PASSWORD:-}" ]] && postgres_has_existing_data; then
      fail "检测到已有 PostgreSQL 数据目录，但 ${ENV_FILE} 不存在且未传入 POSTGRES_PASSWORD；请恢复原 env 或显式传入旧密码后再部署"
    fi

    log "生成 ${ENV_FILE}"
    if [[ "$DEPLOY_ENV" == "production" ]]; then
      write_production_env
    else
      write_development_env
    fi
  else
    log "检测到已有环境文件，保留：${ENV_FILE}"
  fi

  chmod 600 "$ENV_FILE"
  load_env_file
  upsert_env_value "TI_IMAGE" "$TI_IMAGE"
  upsert_env_value "TI_IMAGE_PULL_POLICY" "$TI_IMAGE_PULL_POLICY"
  upsert_env_value "DEFAULT_ADMIN_USERNAME" "$DEFAULT_ADMIN_USERNAME"
  upsert_env_value "DEFAULT_ADMIN_PHONE" "$DEFAULT_ADMIN_PHONE"
  upsert_env_value "DEFAULT_ADMIN_EMAIL" "$DEFAULT_ADMIN_EMAIL"
  upsert_env_value "DEFAULT_ADMIN_PASSWORD" "$DEFAULT_ADMIN_PASSWORD"
  upsert_env_value "DEFAULT_ADMIN_RESET_PASSWORD" "$DEFAULT_ADMIN_RESET_PASSWORD"
  upsert_env_value "RATELIMIT_LIMIT_MULTIPLIER" "$RATELIMIT_LIMIT_MULTIPLIER"
  if [[ "$DEPLOY_ENV" == "production" ]]; then
    upsert_env_value "ENABLE_HTTPS" "$ENABLE_HTTPS"
    upsert_env_value "HTTP_BIND" "$HTTP_BIND"
    upsert_env_value "HTTP_PORT" "$HTTP_PORT"
    upsert_env_value "SESSION_COOKIE_SECURE" "$SESSION_COOKIE_SECURE"
    if [[ "$ENABLE_HTTPS" == "1" ]]; then
      [[ -n "$APP_DOMAIN" ]] && upsert_env_value "DOMAIN" "$APP_DOMAIN"
      upsert_env_value "EXTRA_DOMAINS" "$EXTRA_DOMAINS"
      [[ -n "$CERTBOT_EMAIL" ]] && upsert_env_value "CERTBOT_EMAIL" "$CERTBOT_EMAIL"
    fi
  fi
  chmod 600 "$ENV_FILE"
}

validate_env() {
  if [[ "$DEPLOY_ENV" != "production" ]]; then
    return
  fi

  [[ -n "${SECRET_KEY:-}" ]] || fail "${ENV_FILE} 缺少 SECRET_KEY"
  [[ -n "${POSTGRES_PASSWORD:-}" ]] || fail "${ENV_FILE} 缺少 POSTGRES_PASSWORD"
  [[ -n "${DEFAULT_ADMIN_USERNAME:-}" ]] || fail "${ENV_FILE} 缺少 DEFAULT_ADMIN_USERNAME"
  [[ -n "${DEFAULT_ADMIN_PASSWORD:-}" ]] || fail "${ENV_FILE} 缺少 DEFAULT_ADMIN_PASSWORD"
  [[ -n "${DEFAULT_ADMIN_PHONE:-}${DEFAULT_ADMIN_EMAIL:-}" ]] || fail "${ENV_FILE} 必须配置 DEFAULT_ADMIN_PHONE 或 DEFAULT_ADMIN_EMAIL"

  if [[ "$ALLOW_INSECURE_DEFAULTS" != "1" ]]; then
    [[ "$POSTGRES_PASSWORD" != "studypass" ]] || fail "生产环境禁止使用默认数据库密码 studypass"
    [[ "$SECRET_KEY" != "dev-secret-key" && "$SECRET_KEY" != "dev-secret-key-change-in-production" ]] || fail "生产环境禁止使用开发 SECRET_KEY"
  fi

  if [[ "$ENABLE_HTTPS" == "1" ]]; then
    [[ -n "$APP_DOMAIN" ]] || fail "ENABLE_HTTPS=1 时必须设置 DOMAIN"
    build_app_domains
    [[ -n "$APP_DOMAINS" ]] || fail "ENABLE_HTTPS=1 时至少需要一个域名"
    if [[ -z "$CERTBOT_EMAIL" ]] && ! certificate_covers_all_domains; then
      fail "ENABLE_HTTPS=1 且证书未覆盖全部域名时必须设置 CERTBOT_EMAIL"
    fi
    [[ "$SESSION_COOKIE_SECURE" == "true" ]] || fail "ENABLE_HTTPS=1 时 SESSION_COOKIE_SECURE 必须为 true"
  fi
}

login_registry_if_needed() {
  if [[ -z "${GHCR_TOKEN:-}" && -z "${GHCR_USERNAME:-}" ]]; then
    return
  fi

  [[ -n "${GHCR_TOKEN:-}" && -n "${GHCR_USERNAME:-}" ]] || fail "GHCR_USERNAME 与 GHCR_TOKEN 必须同时设置"
  log "登录 GitHub Container Registry"
  printf '%s' "$GHCR_TOKEN" | $SUDO docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
}

print_service_health_log() {
  local service_name="$1"
  local container_id
  container_id="$("${COMPOSE[@]}" ps -q "$service_name" 2>/dev/null || true)"

  if [[ -z "$container_id" ]]; then
    return
  fi

  printf '\n--- %s container state ---\n' "$service_name" >&2
  $SUDO docker inspect "$container_id" \
    --format 'name={{.Name}} status={{.State.Status}} running={{.State.Running}} exit={{.State.ExitCode}} health={{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} oom={{.State.OOMKilled}} error={{.State.Error}}' \
    >&2 || true

  printf '\n--- %s healthcheck log ---\n' "$service_name" >&2
  $SUDO docker inspect "$container_id" \
    --format '{{if .State.Health}}{{range .State.Health.Log}}{{println .End "exit=" .ExitCode .Output}}{{end}}{{else}}no healthcheck{{end}}' \
    >&2 || true
}

print_deploy_diagnostics() {
  log "采集部署失败诊断信息"

  "${COMPOSE[@]}" ps >&2 || true

  print_service_health_log web
  print_service_health_log nginx
  print_service_health_log postgres
  print_service_health_log redis

  printf '\n--- web logs ---\n' >&2
  "${COMPOSE[@]}" logs --tail=200 web >&2 || true

  printf '\n--- web app.log ---\n' >&2
  "${COMPOSE[@]}" exec -T web sh -c 'test -f /data/logs/app.log && tail -200 /data/logs/app.log || true' >&2 || true

  printf '\n--- nginx logs ---\n' >&2
  "${COMPOSE[@]}" logs --tail=120 nginx >&2 || true

  printf '\n--- redis logs ---\n' >&2
  "${COMPOSE[@]}" logs --tail=80 redis >&2 || true
}

run_web_flask() {
  "${COMPOSE[@]}" run --rm --no-deps web flask "$@"
}

wait_for_service_healthy() {
  local service_name="$1"
  local timeout_seconds="${2:-90}"
  local start_ts now_ts container_id health_status state_status

  start_ts="$(date +%s)"
  while true; do
    container_id="$("${COMPOSE[@]}" ps -q "$service_name" 2>/dev/null || true)"
    if [[ -n "$container_id" ]]; then
      health_status="$($SUDO docker inspect "$container_id" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' 2>/dev/null || true)"
      state_status="$($SUDO docker inspect "$container_id" --format '{{.State.Status}}' 2>/dev/null || true)"
      if [[ "$health_status" == "healthy" ]]; then
        return
      fi
      if [[ "$state_status" == "running" && "$health_status" == "running" ]]; then
        return
      fi
    fi

    now_ts="$(date +%s)"
    if (( now_ts - start_ts >= timeout_seconds )); then
      print_service_health_log "$service_name"
      fail "${service_name} 未在 ${timeout_seconds}s 内变为 healthy"
    fi
    sleep 2
  done
}

assert_web_cli_command() {
  local command_name="$1"
  local help_err
  help_err="$(mktemp)"

  if run_web_flask --help 2>"$help_err" | grep -Eq "^[[:space:]]+${command_name}([[:space:]]|$)"; then
    rm -f "$help_err"
    return
  fi

  local image_id image_revision
  image_id="$($SUDO docker image inspect "$TI_IMAGE" --format '{{.Id}}' 2>/dev/null || true)"
  image_revision="$($SUDO docker image inspect "$TI_IMAGE" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' 2>/dev/null || true)"

  if [[ -s "$help_err" ]]; then
    cat "$help_err" >&2
  fi
  rm -f "$help_err"

  echo "当前镜像：${TI_IMAGE}" >&2
  if [[ -n "$image_id" ]]; then
    echo "镜像 ID：${image_id}" >&2
  fi
  if [[ -n "$image_revision" && "$image_revision" != "<no value>" ]]; then
    echo "镜像 revision：${image_revision}" >&2
  fi
  fail "当前 web 镜像未提供 flask ${command_name} 命令。请先发布包含该命令的新 ${TI_IMAGE}，再在服务器执行 git pull --ff-only 与 ./scripts/deploy_ubuntu24.sh。"
}

certificate_files_exist() {
  $SUDO test -f "/etc/letsencrypt/live/${APP_DOMAIN}/fullchain.pem" \
    && $SUDO test -f "/etc/letsencrypt/live/${APP_DOMAIN}/privkey.pem"
}

certificate_covers_all_domains() {
  local certificate_path certificate_text domain

  certificate_path="/etc/letsencrypt/live/${APP_DOMAIN}/fullchain.pem"
  if ! certificate_files_exist; then
    return 1
  fi

  certificate_text="$($SUDO openssl x509 -in "$certificate_path" -noout -text 2>/dev/null)" || return 1
  for domain in $APP_DOMAINS; do
    if ! grep -Fq "DNS:${domain}" <<<"$certificate_text"; then
      return 1
    fi
  done
}

deploy_stack() {
  log "拉取应用镜像：${TI_IMAGE}"
  $SUDO docker pull "$TI_IMAGE"

  log "拉取 Compose 服务镜像"
  "${COMPOSE[@]}" pull

  log "启动基础依赖容器"
  if ! "${COMPOSE[@]}" up -d postgres redis; then
    print_deploy_diagnostics
    fail "基础依赖容器启动失败"
  fi
  wait_for_service_healthy postgres 120
  wait_for_service_healthy redis 60

  if [[ "$RUN_MIGRATIONS" == "1" ]]; then
    log "执行数据库迁移"
    if ! run_web_flask db upgrade; then
      print_deploy_diagnostics
      fail "数据库迁移失败"
    fi
  else
    log "已设置 RUN_MIGRATIONS=0，跳过数据库迁移"
  fi

  if [[ "$ENSURE_DEFAULT_ADMIN" == "1" ]]; then
    log "确保默认管理员账号"
    assert_web_cli_command "ensure-default-admin"
    if ! run_web_flask ensure-default-admin; then
      print_deploy_diagnostics
      fail "默认管理员初始化失败"
    fi
  else
    log "已设置 ENSURE_DEFAULT_ADMIN=0，跳过默认管理员初始化"
  fi

  log "启动 ${DEPLOY_ENV} 容器"
  if ! "${COMPOSE[@]}" up -d --remove-orphans; then
    print_deploy_diagnostics
    fail "${DEPLOY_ENV} 容器启动失败"
  fi
}

restart_internal_nginx() {
  if [[ "$DEPLOY_ENV" != "production" || "$RESTART_INTERNAL_NGINX" != "1" ]]; then
    return
  fi

  log "重启 Docker 内 nginx，刷新 upstream 连接"
  "${COMPOSE[@]}" restart nginx
}

configure_host_nginx() {
  if [[ "$ENABLE_HTTPS" != "1" ]]; then
    log "跳过宿主机 Nginx 配置"
    return
  fi

  build_app_domains
  log "配置宿主机 Nginx 反向代理"
  write_host_nginx_config
  reload_host_nginx
}

write_host_nginx_config() {
  local server_names
  server_names="$APP_DOMAINS"

  if certificate_files_exist; then
    $SUDO tee "$HOST_NGINX_CONFIG_PATH" > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${server_names};

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${server_names};

    ssl_certificate /etc/letsencrypt/live/${APP_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${APP_DOMAIN}/privkey.pem;

    client_max_body_size 10m;

    location /sse/ {
        proxy_pass http://127.0.0.1:${HTTP_PORT};
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
        proxy_pass http://127.0.0.1:${HTTP_PORT};
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
  else
    $SUDO tee "$HOST_NGINX_CONFIG_PATH" > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${server_names};

    client_max_body_size 10m;

    location /sse/ {
        proxy_pass http://127.0.0.1:${HTTP_PORT};
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
        proxy_pass http://127.0.0.1:${HTTP_PORT};
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
  fi
}

reload_host_nginx() {
  $SUDO ln -sf "$HOST_NGINX_CONFIG_PATH" "$HOST_NGINX_ENABLED_PATH"
  $SUDO nginx -t
  $SUDO systemctl reload nginx
}

configure_firewall() {
  if [[ "$ENABLE_HTTPS" != "1" ]]; then
    log "跳过防火墙配置"
    return
  fi

  log "配置防火墙"
  $SUDO ufw allow OpenSSH
  $SUDO ufw allow 'Nginx Full'
  $SUDO ufw --force enable
}

install_certbot() {
  if [[ "$ENABLE_HTTPS" != "1" ]]; then
    log "跳过 HTTPS 证书签发"
    return
  fi

  if ! command -v certbot >/dev/null 2>&1; then
    log "安装 Certbot"
    $SUDO snap install core
    $SUDO snap refresh core
    $SUDO snap install --classic certbot
    $SUDO ln -sf /snap/bin/certbot /usr/bin/certbot
  else
    log "Certbot 已安装，跳过"
  fi

  build_app_domains
  if certificate_covers_all_domains; then
    log "检测到 ${APP_DOMAINS} 证书已覆盖全部域名，跳过签发"
  else
    local -a certbot_domain_args=()
    local -a certbot_common_args=("--nginx" "--cert-name" "$APP_DOMAIN")
    local domain
    for domain in $APP_DOMAINS; do
      certbot_domain_args+=(-d "$domain")
    done

    log "申请 HTTPS 证书"
    if certificate_files_exist; then
      certbot_common_args+=(--expand)
    fi

    $SUDO certbot certonly \
      "${certbot_common_args[@]}" \
      "${certbot_domain_args[@]}" \
      -m "$CERTBOT_EMAIL" \
      --agree-tos \
      --no-eff-email
  fi

  configure_host_nginx
}

probe_json() {
  local url="$1"
  curl --retry 10 --retry-delay 3 --retry-all-errors -fsS "$url" | python3 -m json.tool
}

probe_json_with_internal_nginx_recovery() {
  local url="$1"

  if probe_json "$url"; then
    return
  fi

  restart_internal_nginx
  probe_json "$url"
}

validate_deploy() {
  log "校验容器状态"
  "${COMPOSE[@]}" ps

  log "校验健康检查"
  if [[ "$DEPLOY_ENV" == "production" ]]; then
    probe_json_with_internal_nginx_recovery "http://127.0.0.1:${HTTP_PORT}/api/ping"

    if [[ "$ENABLE_HTTPS" == "1" ]]; then
      local domain
      for domain in $APP_DOMAINS; do
        curl -I "https://${domain}" || true
        probe_json_with_internal_nginx_recovery "https://${domain}/api/ping"
      done
    fi
  else
    probe_json "http://127.0.0.1:${WEB_PORT:-8000}/api/ping"
  fi
}

print_summary() {
  log "部署完成"
  cat <<EOF
环境：${DEPLOY_ENV}
镜像：${TI_IMAGE}
项目目录：${APP_DIR}
Compose：${COMPOSE_FILE}
环境文件：${ENV_FILE}
生产 HTTP 绑定：${HTTP_BIND:-未设置}:${HTTP_PORT:-未设置}
HTTPS 后续配置：$([[ "$ENABLE_HTTPS" == "1" ]] && printf '已启用，域名 %s' "$APP_DOMAINS" || printf '未启用')

常用命令：
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" logs -f web
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T web flask ensure-default-admin

说明：
  - 本脚本只拉取镜像，不在服务器构建应用镜像；
  - 私有 GHCR 镜像请通过 GHCR_USERNAME / GHCR_TOKEN 临时登录；
  - 默认管理员账号配置保存在环境文件 DEFAULT_ADMIN_* 中，生产密码请按密钥级别保管；
  - 生产备份包可能包含 env 配置，请按密钥级别保护 backups/。
EOF
}

if [[ "${DEPLOY_UBUNTU24_TEST_HELPERS:-0}" == "1" ]]; then
  return 0 2>/dev/null || exit 0
fi

install_base_packages
install_docker
prepare_runtime_files
validate_env
install_https_packages
login_registry_if_needed
deploy_stack
restart_internal_nginx
configure_host_nginx
configure_firewall
install_certbot
validate_deploy
print_summary
