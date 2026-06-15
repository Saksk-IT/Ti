#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SCRIPT_PATH="$ROOT_DIR/scripts/update_production.sh"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.production}"
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  echo "错误：$*" >&2
  exit 1
}

read_env_value() {
  local key="$1"

  if [[ ! -f "$ENV_FILE" ]]; then
    return
  fi

  awk -v key="$key" '
    index($0, key "=") == 1 {
      sub("^[^=]*=", "")
      print
      exit
    }
  ' "$ENV_FILE"
}

file_signature() {
  if command -v cksum >/dev/null 2>&1; then
    cksum "$1" | awk '{ print $1 ":" $2 }'
    return
  fi

  wc -c "$1" | awk '{ print $1 }'
}

maybe_reexec_after_pull() {
  local before_signature="$1"
  local after_signature
  after_signature="$(file_signature "$SCRIPT_PATH")"

  if [[ "$before_signature" != "$after_signature" && "${TI_UPDATE_PRODUCTION_REEXECED:-0}" != "1" ]]; then
    log "检测到更新入口脚本已随代码更新，重新执行最新脚本"
    exec env TI_UPDATE_PRODUCTION_REEXECED=1 "$SCRIPT_PATH" "$BRANCH"
  fi
}

resolve_https_env() {
  local saved_enable_https saved_domain saved_extra_domains saved_certbot_email saved_http_bind saved_secure_cookie
  saved_enable_https="$(read_env_value ENABLE_HTTPS)"
  saved_domain="$(read_env_value DOMAIN)"
  saved_extra_domains="$(read_env_value EXTRA_DOMAINS)"
  saved_certbot_email="$(read_env_value CERTBOT_EMAIL)"
  saved_http_bind="$(read_env_value HTTP_BIND)"
  saved_secure_cookie="$(read_env_value SESSION_COOKIE_SECURE)"

  if [[ -z "${ENABLE_HTTPS:-}" ]]; then
    if [[ "$saved_enable_https" == "1" ]]; then
      ENABLE_HTTPS="1"
    elif [[ -n "$saved_domain" && -n "$saved_certbot_email" ]]; then
      ENABLE_HTTPS="1"
    elif [[ "$saved_http_bind" == "127.0.0.1" && "$saved_secure_cookie" == "true" ]]; then
      ENABLE_HTTPS="1"
    else
      ENABLE_HTTPS="0"
    fi
  fi

  case "$ENABLE_HTTPS" in
    0|1) ;;
    *) fail "ENABLE_HTTPS 只能是 0 或 1，当前值：${ENABLE_HTTPS}" ;;
  esac

  export ENABLE_HTTPS

  if [[ "$ENABLE_HTTPS" != "1" ]]; then
    return
  fi

  DOMAIN="${DOMAIN:-$saved_domain}"
  EXTRA_DOMAINS="${EXTRA_DOMAINS:-$saved_extra_domains}"
  CERTBOT_EMAIL="${CERTBOT_EMAIL:-$saved_certbot_email}"

  [[ -n "$DOMAIN" ]] || fail "已启用 HTTPS 更新，但 ${ENV_FILE} 缺少 DOMAIN；请临时传入 DOMAIN=域名 后重试"

  export DOMAIN EXTRA_DOMAINS CERTBOT_EMAIL
  log "检测到生产 HTTPS：${DOMAIN}${EXTRA_DOMAINS:+ ${EXTRA_DOMAINS}}"
}

script_signature_before_pull="$(file_signature "$SCRIPT_PATH")"

log "拉取最新代码：origin/${BRANCH}"
git pull --ff-only origin "$BRANCH"
maybe_reexec_after_pull "$script_signature_before_pull"

resolve_https_env

log "执行生产部署更新"
DEPLOY_ENV=production ./scripts/deploy_ubuntu24.sh
