#!/usr/bin/env bash

# Pull a consistent production snapshot from server 1 and restore it on server 2.

MIGRATOR_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATOR_REPO_DIR="$(cd "$MIGRATOR_SCRIPT_DIR/.." && pwd)"
MIGRATOR_COMMON_PATH="${MIGRATION_COMMON_PATH:-$MIGRATOR_SCRIPT_DIR/lib/production_migration_common.sh}"
# shellcheck source=scripts/lib/production_migration_common.sh
source "$MIGRATOR_COMMON_PATH"

MIGRATOR_SOURCE=""
MIGRATOR_SOURCE_DIR=""
MIGRATOR_SOURCE_PORT="22"
MIGRATOR_IDENTITY_FILE=""
MIGRATOR_KNOWN_HOSTS="${HOME}/.ssh/known_hosts"
MIGRATOR_TARGET_DIR="$MIGRATOR_REPO_DIR"
MIGRATOR_KEEP_BUNDLE=0
MIGRATOR_DRY_RUN=0
MIGRATOR_MIGRATION_ID=""
MIGRATOR_WORKSPACE=""
MIGRATOR_REMOTE_TEMP=""
MIGRATOR_SOURCE_FROZEN=0
MIGRATOR_TARGET_MUTATED=0
MIGRATOR_ROLLBACK_READY=0
MIGRATOR_FINISHED=0
MIGRATOR_ROLLBACK_ACTIVE=0
MIGRATOR_TARGET_CAPTURE_ACTIVE=0
MIGRATOR_TARGET_ROLLBACK_ID=""
MIGRATOR_TARGET_LOCK=""
MIGRATOR_TARGET_LOCK_HELD=0
MIGRATOR_COMMIT_STARTED=0
MIGRATOR_SOURCE_FACTS=""
MIGRATOR_TARGET_FACTS=""
MIGRATOR_SOURCE_BUNDLE=""
MIGRATOR_SOURCE_CHECKSUM=""
MIGRATOR_ROLLBACK_BUNDLE=""
MIGRATOR_ROLLBACK_CHECKSUM=""
declare -a MIGRATOR_SSH=()
declare -a MIGRATOR_SCP=()

migrator_usage() {
  cat <<'EOF'
用法:
  migrate_production_data.sh --source USER@HOST --source-dir ABSOLUTE_DIR [选项]

必填参数:
  --source USER@HOST       服务器 1 的 SSH 地址
  --source-dir PATH        服务器 1 的 Ti 生产部署目录

可选参数:
  --source-port PORT       SSH 端口，默认 22
  --identity-file PATH     专用 SSH 私钥
  --known-hosts PATH       已人工核验的 known_hosts 文件
  --target-dir PATH        服务器 2 部署目录，默认当前仓库根目录
  --keep-bundle            成功后保留服务器 2 上的含密钥迁移包
  --dry-run                仅执行两端预检，不停止服务或导出数据
  -h, --help               显示帮助
EOF
}

migrator_validate_remote_dir() {
  local path="$1"
  migration_validate_absolute_dir "$path" || return 1
  [[ "$path" =~ ^/[A-Za-z0-9._/-]+$ ]] \
    || { migration_fail "远端目录只能包含安全路径字符"; return 1; }
}

migrator_validate_file() {
  local path="$1"
  local label="$2"
  [[ "$path" == /* && -f "$path" && ! -L "$path" ]] \
    || { migration_fail "$label 必须是绝对路径指向的普通文件"; return 1; }
}

migrator_parse_args() {
  while (( $# > 0 )); do
    case "$1" in
      --source)
        (( $# >= 2 )) || { migration_fail "--source 缺少值"; return 2; }
        MIGRATOR_SOURCE="$2"; shift 2 ;;
      --source-dir)
        (( $# >= 2 )) || { migration_fail "--source-dir 缺少值"; return 2; }
        MIGRATOR_SOURCE_DIR="$2"; shift 2 ;;
      --source-port)
        (( $# >= 2 )) || { migration_fail "--source-port 缺少值"; return 2; }
        MIGRATOR_SOURCE_PORT="$2"; shift 2 ;;
      --identity-file)
        (( $# >= 2 )) || { migration_fail "--identity-file 缺少值"; return 2; }
        MIGRATOR_IDENTITY_FILE="$2"; shift 2 ;;
      --known-hosts)
        (( $# >= 2 )) || { migration_fail "--known-hosts 缺少值"; return 2; }
        MIGRATOR_KNOWN_HOSTS="$2"; shift 2 ;;
      --target-dir)
        (( $# >= 2 )) || { migration_fail "--target-dir 缺少值"; return 2; }
        MIGRATOR_TARGET_DIR="$2"; shift 2 ;;
      --keep-bundle) MIGRATOR_KEEP_BUNDLE=1; shift ;;
      --dry-run) MIGRATOR_DRY_RUN=1; shift ;;
      -h|--help) migrator_usage; return 10 ;;
      *) migration_fail "未知参数: $1"; return 2 ;;
    esac
  done
}

migrator_validate_args() {
  local required_command
  [[ -n "$MIGRATOR_SOURCE" && -n "$MIGRATOR_SOURCE_DIR" ]] \
    || { migration_fail "--source 和 --source-dir 为必填参数"; return 2; }
  migration_validate_ssh_target "$MIGRATOR_SOURCE" || return 2
  migration_validate_port "$MIGRATOR_SOURCE_PORT" || return 2
  migrator_validate_remote_dir "$MIGRATOR_SOURCE_DIR" || return 2
  migration_validate_absolute_dir "$MIGRATOR_TARGET_DIR" || return 2
  [[ "$MIGRATOR_TARGET_DIR" != "/" && -d "$MIGRATOR_TARGET_DIR" && ! -L "$MIGRATOR_TARGET_DIR" ]] \
    || { migration_fail "目标部署目录无效"; return 2; }
  migrator_validate_file "$MIGRATOR_KNOWN_HOSTS" "known_hosts" || return 2
  [[ -s "$MIGRATOR_KNOWN_HOSTS" ]] \
    || { migration_fail "known_hosts 不能为空"; return 2; }
  if [[ -n "$MIGRATOR_IDENTITY_FILE" ]]; then
    migrator_validate_file "$MIGRATOR_IDENTITY_FILE" "SSH 私钥" || return 2
  fi
  [[ -f "$MIGRATOR_TARGET_DIR/.env.production" ]] \
    || { migration_fail "目标缺少 .env.production"; return 2; }
  [[ -f "$MIGRATOR_TARGET_DIR/compose.prod.yml" ]] \
    || { migration_fail "目标缺少 compose.prod.yml"; return 2; }
  [[ -x "$MIGRATOR_SCRIPT_DIR/export_production_data.sh" ]] \
    || { migration_fail "源端导出 helper 不可执行"; return 2; }
  [[ -f "$MIGRATOR_SCRIPT_DIR/lib/validate_migration_archive.py" ]] \
    || { migration_fail "缺少归档校验 helper"; return 2; }
  [[ -f "$MIGRATOR_SCRIPT_DIR/lib/merge_production_env.py" ]] \
    || { migration_fail "缺少 env 合并 helper"; return 2; }
  for required_command in tar cmp awk tr hostname date rm cp "${MIGRATION_PYTHON_BIN:-python3}"; do
    migration_require_command "$required_command" || return 2
  done
}

migrator_build_transport() {
  local ssh_bin="${MIGRATION_SSH_BIN:-ssh}"
  local scp_bin="${MIGRATION_SCP_BIN:-scp}"
  migration_require_command "$ssh_bin" || return 1
  migration_require_command "$scp_bin" || return 1
  MIGRATOR_SSH=(
    "$ssh_bin" -p "$MIGRATOR_SOURCE_PORT"
    -o BatchMode=yes
    -o StrictHostKeyChecking=yes
    -o IdentitiesOnly=yes
    -o UpdateHostKeys=no
    -o "UserKnownHostsFile=$MIGRATOR_KNOWN_HOSTS"
  )
  MIGRATOR_SCP=(
    "$scp_bin" -P "$MIGRATOR_SOURCE_PORT"
    -o BatchMode=yes
    -o StrictHostKeyChecking=yes
    -o IdentitiesOnly=yes
    -o UpdateHostKeys=no
    -o "UserKnownHostsFile=$MIGRATOR_KNOWN_HOSTS"
  )
  if [[ -n "$MIGRATOR_IDENTITY_FILE" ]]; then
    MIGRATOR_SSH+=( -i "$MIGRATOR_IDENTITY_FILE" )
    MIGRATOR_SCP+=( -i "$MIGRATOR_IDENTITY_FILE" )
  fi
}

migrator_remote() {
  "${MIGRATOR_SSH[@]}" "$MIGRATOR_SOURCE" "$@"
}

migrator_remote_export() {
  local action="$1"
  migrator_remote bash "$MIGRATOR_REMOTE_TEMP/export_production_data.sh" \
    "$action" --source-dir "$MIGRATOR_SOURCE_DIR" --migration-id "$MIGRATOR_MIGRATION_ID"
}

migrator_upload_helpers() {
  local remote_temp
  remote_temp="$(migrator_remote mktemp -d /tmp/ti-production-migration.XXXXXX)" || return 1
  [[ "$remote_temp" =~ ^/tmp/ti-production-migration\.[A-Za-z0-9]+$ ]] \
    || { migration_fail "远端临时目录格式无效"; return 1; }
  MIGRATOR_REMOTE_TEMP="$remote_temp"
  migrator_remote mkdir -m 700 "$MIGRATOR_REMOTE_TEMP/lib" || return 1
  "${MIGRATOR_SCP[@]}" \
    "$MIGRATOR_SCRIPT_DIR/export_production_data.sh" \
    "$MIGRATOR_SOURCE:$MIGRATOR_REMOTE_TEMP/export_production_data.sh" || return 1
  "${MIGRATOR_SCP[@]}" \
    "$MIGRATOR_SCRIPT_DIR/lib/production_migration_common.sh" \
    "$MIGRATOR_SOURCE:$MIGRATOR_REMOTE_TEMP/lib/production_migration_common.sh" || return 1
  migrator_remote chmod 700 "$MIGRATOR_REMOTE_TEMP/export_production_data.sh" \
    "$MIGRATOR_REMOTE_TEMP/lib/production_migration_common.sh" || return 1
}

migrator_fact() {
  local facts="$1"
  local key="$2"
  [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] || return 1
  printf '%s\n' "$facts" | awk -v wanted="$key" '
    index($0, wanted "=") == 1 { print substr($0, length(wanted) + 2); exit }
  '
}

migrator_configure_target() {
  MIGRATION_ENV_FILE="$MIGRATOR_TARGET_DIR/.env.production"
  MIGRATION_COMPOSE_FILE="$MIGRATOR_TARGET_DIR/compose.prod.yml"
  MIGRATION_PROJECT_NAME="$(migration_project_name_from_dir "$MIGRATOR_TARGET_DIR")" || return 1
  export MIGRATION_ENV_FILE MIGRATION_COMPOSE_FILE MIGRATION_PROJECT_NAME
}

migrator_local_preflight() {
  bash "$MIGRATOR_SCRIPT_DIR/export_production_data.sh" preflight \
    --source-dir "$MIGRATOR_TARGET_DIR" --migration-id "$MIGRATOR_MIGRATION_ID"
}

migrator_compare_preflight() {
  local key source_value target_value source_size target_available required_target
  for key in POSTGRES_MAJOR REDIS_MAJOR WEB_IMAGE_DIGEST; do
    source_value="$(migrator_fact "$MIGRATOR_SOURCE_FACTS" "$key")" || return 1
    target_value="$(migrator_fact "$MIGRATOR_TARGET_FACTS" "$key")" || return 1
    [[ -n "$source_value" && "$source_value" == "$target_value" ]] \
      || { migration_fail "源、目标 $key 不兼容"; return 1; }
  done
  source_value="$(migrator_fact "$MIGRATOR_SOURCE_FACTS" SOURCE_MACHINE_ID)" || return 1
  target_value="$(migrator_fact "$MIGRATOR_TARGET_FACTS" SOURCE_MACHINE_ID)" || return 1
  [[ -n "$source_value" && "$source_value" != "$target_value" ]] \
    || { migration_fail "源服务器与目标服务器不能是同一台机器"; return 1; }
  source_size="$(migrator_fact "$MIGRATOR_SOURCE_FACTS" DATA_SIZE_KB)" || return 1
  target_available="$(migrator_fact "$MIGRATOR_TARGET_FACTS" AVAILABLE_KB)" || return 1
  [[ "$source_size" =~ ^[0-9]+$ && "$target_available" =~ ^[0-9]+$ ]] || return 1
  required_target=$((source_size * 6 + 1024))
  (( target_available >= required_target )) \
    || { migration_fail "目标服务器磁盘空间不足"; return 1; }
}

migrator_healthcheck() {
  local curl_bin="${MIGRATION_CURL_BIN:-curl}"
  local port
  migration_require_command "$curl_bin" || return 1
  port="$(migration_read_env_value "$MIGRATOR_TARGET_DIR/.env.production" HTTP_PORT)" || return 1
  port="${port:-8080}"
  migration_validate_port "$port" || return 1
  "$curl_bin" --fail --silent --show-error --max-time 15 \
    "http://127.0.0.1:$port/api/ping" >/dev/null || return 1
  "$curl_bin" --fail --silent --show-error --max-time 20 \
    "http://127.0.0.1:$port/api/ping?deep=1" >/dev/null || return 1
}

migrator_confirm() {
  local source_host target_host expected confirmation
  source_host="${MIGRATOR_SOURCE#*@}"
  target_host="$(hostname -f 2>/dev/null || hostname)" || return 1
  [[ "$target_host" =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] \
    || { migration_fail "目标主机名格式无效"; return 1; }
  expected="MIGRATE $source_host TO $target_host"
  printf '即将覆盖服务器 2 的生产数据。请输入：%s\n> ' "$expected" >&2
  IFS= read -r confirmation || return 1
  [[ "$confirmation" == "$expected" ]] \
    || { migration_fail "确认文本不匹配，迁移已取消"; return 1; }
}

migrator_copy_rollback_bundle() {
  local output bundle checksum copy_status resume_status rollback_id
  rollback_id="rollback-$MIGRATOR_MIGRATION_ID"
  MIGRATOR_TARGET_ROLLBACK_ID="$rollback_id"
  MIGRATOR_TARGET_CAPTURE_ACTIVE=1
  output="$(bash "$MIGRATOR_SCRIPT_DIR/export_production_data.sh" prepare \
    --source-dir "$MIGRATOR_TARGET_DIR" --migration-id "$rollback_id")" || return 1
  bundle="$(migrator_fact "$output" BUNDLE_PATH)"
  checksum="$(migrator_fact "$output" CHECKSUM_PATH)"
  copy_status=0
  MIGRATOR_ROLLBACK_BUNDLE="$MIGRATOR_WORKSPACE/$(basename "$bundle")"
  MIGRATOR_ROLLBACK_CHECKSUM="$MIGRATOR_ROLLBACK_BUNDLE.sha256"
  cp -p "$bundle" "$MIGRATOR_ROLLBACK_BUNDLE" || copy_status=1
  cp -p "$checksum" "$MIGRATOR_ROLLBACK_CHECKSUM" || copy_status=1
  bash "$MIGRATOR_SCRIPT_DIR/export_production_data.sh" resume \
    --source-dir "$MIGRATOR_TARGET_DIR" --migration-id "$rollback_id" >/dev/null
  resume_status=$?
  (( resume_status == 0 )) && MIGRATOR_TARGET_CAPTURE_ACTIVE=0
  (( copy_status == 0 && resume_status == 0 )) || return 1
  migrator_validate_and_extract \
    "$MIGRATOR_ROLLBACK_BUNDLE" "$MIGRATOR_ROLLBACK_CHECKSUM" rollback-check \
    >/dev/null || return 1
  rm -rf -- "$MIGRATOR_WORKSPACE/extracted-rollback-check" || return 1
  MIGRATOR_ROLLBACK_READY=1
}

migrator_expected_checksum() {
  local checksum_file="$1"
  local expected_name="$2"
  local digest name extra
  read -r digest name extra < "$checksum_file" || return 1
  [[ -z "${extra:-}" && "$digest" =~ ^[0-9A-Fa-f]{64}$ && "$name" == "$expected_name" ]] \
    || { migration_fail "外层校验文件格式无效"; return 1; }
  printf '%s\n' "$digest"
}

migrator_verify_outer_checksum() {
  local bundle="$1"
  local checksum_file="$2"
  local expected actual
  expected="$(migrator_expected_checksum "$checksum_file" "$(basename "$bundle")")" || return 1
  actual="$(migration_sha256 "$bundle")" || return 1
  [[ "$actual" == "$expected" ]] \
    || { migration_fail "迁移包 SHA-256 不匹配"; return 1; }
}

migrator_verify_internal_checksums() {
  local extract_dir="$1"
  local checksum_file="$extract_dir/checksums.sha256"
  local digest filename extra actual count=0 sequence=""
  while read -r digest filename extra; do
    [[ -z "${extra:-}" && "$digest" =~ ^[0-9A-Fa-f]{64}$ ]] \
      || { migration_fail "内部校验文件格式无效"; return 1; }
    case "$filename" in
      database.dump|database-summary.txt|redis.tar.gz|uploads.tar.gz|instance.tar.gz|source.env.production|manifest.txt) ;;
      *) migration_fail "内部校验文件包含意外路径"; return 1 ;;
    esac
    actual="$(migration_sha256 "$extract_dir/$filename")" || return 1
    [[ "$actual" == "$digest" ]] \
      || { migration_fail "内部文件 SHA-256 不匹配: $filename"; return 1; }
    count=$((count + 1))
    sequence="${sequence}${sequence:+,}${filename}"
  done < "$checksum_file"
  (( count == 7 )) || { migration_fail "内部校验项目数量无效"; return 1; }
  [[ "$sequence" == "database.dump,database-summary.txt,redis.tar.gz,uploads.tar.gz,instance.tar.gz,source.env.production,manifest.txt" ]] \
    || { migration_fail "内部校验项目集合或顺序无效"; return 1; }
}

migrator_validate_and_extract() {
  local bundle="$1"
  local checksum="$2"
  local label="$3"
  local extract_dir="$MIGRATOR_WORKSPACE/extracted-$label"
  local validator="$MIGRATOR_SCRIPT_DIR/lib/validate_migration_archive.py"
  local python_bin="${MIGRATION_PYTHON_BIN:-python3}"
  local profile
  migrator_verify_outer_checksum "$bundle" "$checksum" || return 1
  "$python_bin" "$validator" --archive "$bundle" --profile bundle || return 1
  rm -rf -- "$extract_dir" || return 1
  mkdir -m 700 "$extract_dir" || return 1
  COPYFILE_DISABLE=1 tar -xzf "$bundle" -C "$extract_dir" \
    --no-same-owner --no-same-permissions || return 1
  migrator_verify_internal_checksums "$extract_dir" || return 1
  for profile in redis uploads instance; do
    "$python_bin" "$validator" --archive "$extract_dir/$profile.tar.gz" \
      --profile "$profile" || return 1
    mkdir -m 700 "$extract_dir/$profile-extracted" || return 1
    COPYFILE_DISABLE=1 tar -xzf "$extract_dir/$profile.tar.gz" \
      -C "$extract_dir/$profile-extracted" \
      --no-same-owner --no-same-permissions || return 1
  done
  printf '%s\n' "$extract_dir"
}

migrator_manifest_value() {
  local manifest="$1"
  local key="$2"
  [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] || return 1
  awk -v wanted="$key" '
    index($0, wanted "=") == 1 { print substr($0, length(wanted) + 2); exit }
  ' "$manifest"
}

migrator_env_value_hash() {
  local env_file="$1"
  local key="$2"
  local python_bin="${MIGRATION_PYTHON_BIN:-python3}"
  [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || return 1
  "$python_bin" - "$MIGRATOR_SCRIPT_DIR/lib/merge_production_env.py" "$env_file" "$key" <<'PY'
import hashlib
import importlib.util
from pathlib import Path
import sys

helper_path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("migration_env_merge", helper_path)
if spec is None or spec.loader is None:
    raise SystemExit(1)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
values = module.parse_env_file(Path(sys.argv[2]))
value = values.get(sys.argv[3], "")
if not value:
    raise SystemExit(1)
print(hashlib.sha256(value.encode("utf-8")).hexdigest())
PY
}

migrator_restore_exact_service_set() {
  local manifest="$1"
  local services_csv service
  services_csv="$(migrator_manifest_value "$manifest" RUNNING_SERVICES)" || return 1
  [[ "$services_csv" =~ ^([A-Za-z0-9_-]+(,[A-Za-z0-9_-]+)*)?$ ]] || return 1
  for service in backup nginx worker web redis postgres; do
    case ",$services_csv," in
      *",$service,"*) ;;
      *) migration_root_compose stop "$service" || return 1 ;;
    esac
  done
}

migrator_wait_service() {
  local service="$1"
  local timeout_seconds="${2:-120}"
  local start now container status
  start="$(date +%s)"
  while true; do
    container="$(migration_root_compose ps -q "$service" 2>/dev/null)" || true
    if [[ -n "$container" ]]; then
      status="$(migration_root_docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null)" || true
      [[ "$status" == "healthy" || "$status" == "running" ]] && return 0
    fi
    now="$(date +%s)"
    (( now - start < timeout_seconds )) \
      || { migration_fail "等待服务 $service 健康超时"; return 1; }
    sleep 2
  done
}

migrator_replace_directory() {
  local staged="$1"
  local target="$2"
  local label="$3"
  local previous="${target}.migration-previous-$label"
  [[ -d "$staged" && ! -L "$staged" && -d "$target" && ! -L "$target" ]] || return 1
  migration_root rm -rf -- "$previous" || return 1
  migration_root mv -- "$target" "$previous" || return 1
  if ! migration_root mv -- "$staged" "$target"; then
    migration_root mv -- "$previous" "$target" || true
    return 1
  fi
}

migrator_restore_bundle() {
  local bundle="$1"
  local checksum="$2"
  local label="$3"
  local extract_dir manifest postgres_user postgres_db target_postgres_password_hash
  local source_secret_hash merged_secret_hash merged_postgres_password_hash expected actual profile stats
  local expected_count expected_bytes expected_tree actual_count actual_bytes actual_tree post_facts published
  local python_bin="${MIGRATION_PYTHON_BIN:-python3}"
  extract_dir="$(migrator_validate_and_extract "$bundle" "$checksum" "$label")" || return 1
  manifest="$extract_dir/manifest.txt"
  [[ "$(migrator_manifest_value "$manifest" FORMAT_VERSION)" == "1" ]] || return 1

  [[ "$label" == "rollback" ]] || MIGRATOR_TARGET_MUTATED=1
  migration_root_compose stop backup || return 1
  migration_root_compose stop nginx || return 1
  migration_root_compose stop web worker || return 1
  migration_root_compose stop redis || return 1
  postgres_user="$(migration_read_env_value "$MIGRATOR_TARGET_DIR/.env.production" POSTGRES_USER)" || return 1
  postgres_db="$(migration_read_env_value "$MIGRATOR_TARGET_DIR/.env.production" POSTGRES_DB)" || return 1
  target_postgres_password_hash="$(migrator_env_value_hash "$MIGRATOR_TARGET_DIR/.env.production" POSTGRES_PASSWORD)" || return 1
  source_secret_hash="$(migrator_env_value_hash "$extract_dir/source.env.production" SECRET_KEY)" || return 1
  postgres_user="${postgres_user:-studyuser}"
  postgres_db="${postgres_db:-ti_db}"
  [[ "$postgres_user" =~ ^[A-Za-z0-9_.-]+$ && "$postgres_db" =~ ^[A-Za-z0-9_.-]+$ ]] || return 1
  migration_root_compose exec -T postgres dropdb --if-exists --force \
    -U "$postgres_user" "$postgres_db" || return 1
  migration_root_compose exec -T postgres createdb -U "$postgres_user" "$postgres_db" || return 1
  migration_root_compose exec -T postgres pg_restore --exit-on-error --single-transaction \
    --no-owner --no-privileges -U "$postgres_user" -d "$postgres_db" \
    < "$extract_dir/database.dump" || return 1
  migration_database_row_summary "$postgres_user" "$postgres_db" \
    > "$extract_dir/database-summary-restored.txt" || return 1
  cmp -s "$extract_dir/database-summary.txt" "$extract_dir/database-summary-restored.txt" \
    || { migration_fail "数据库公共表行数摘要校验失败"; return 1; }

  for profile in redis uploads instance; do
    migrator_replace_directory "$extract_dir/$profile-extracted/$profile" \
      "$MIGRATOR_TARGET_DIR/var/$profile" "$label" || return 1
  done
  "$python_bin" "$MIGRATOR_SCRIPT_DIR/lib/merge_production_env.py" \
    --source "$extract_dir/source.env.production" \
    --target "$MIGRATOR_TARGET_DIR/.env.production" \
    --output "$MIGRATOR_TARGET_DIR/.env.production" || return 1
  merged_secret_hash="$(migrator_env_value_hash "$MIGRATOR_TARGET_DIR/.env.production" SECRET_KEY)" || return 1
  merged_postgres_password_hash="$(migrator_env_value_hash "$MIGRATOR_TARGET_DIR/.env.production" POSTGRES_PASSWORD)" || return 1
  [[ -n "$source_secret_hash" && "$merged_secret_hash" == "$source_secret_hash" ]] \
    || { migration_fail "SECRET_KEY 一致性校验失败"; return 1; }
  [[ -n "$target_postgres_password_hash" && "$merged_postgres_password_hash" == "$target_postgres_password_hash" ]] \
    || { migration_fail "目标 PostgreSQL 凭据保留校验失败"; return 1; }
  migrator_configure_target || return 1
  migration_root_compose run --rm --no-deps --user root redis \
    sh -c 'chown -R redis:redis /data' || return 1
  migration_root find "$MIGRATOR_TARGET_DIR/var/uploads" -type d -exec chmod 755 {} + || return 1
  migration_root find "$MIGRATOR_TARGET_DIR/var/uploads" -type f -exec chmod 644 {} + || return 1
  migration_root find "$MIGRATOR_TARGET_DIR/var/instance" -type d -exec chmod 700 {} + || return 1
  migration_root find "$MIGRATOR_TARGET_DIR/var/instance" -type f -exec chmod 600 {} + || return 1

  migration_root_compose up -d postgres redis || return 1
  migrator_wait_service postgres 120 || return 1
  migrator_wait_service redis 90 || return 1
  expected="$(migrator_manifest_value "$manifest" REDIS_DBSIZE)"
  actual="$(migration_root_compose exec -T redis redis-cli --raw DBSIZE)" || return 1
  [[ "$expected" =~ ^[0-9]+$ && "$actual" == "$expected" ]] \
    || { migration_fail "Redis key 数量校验失败"; return 1; }
  for profile in uploads instance; do
    expected_count="$(migrator_manifest_value "$manifest" "$(printf '%s' "$profile" | tr '[:lower:]' '[:upper:]')_FILE_COUNT")"
    expected_bytes="$(migrator_manifest_value "$manifest" "$(printf '%s' "$profile" | tr '[:lower:]' '[:upper:]')_TOTAL_BYTES")"
    expected_tree="$(migrator_manifest_value "$manifest" "$(printf '%s' "$profile" | tr '[:lower:]' '[:upper:]')_TREE_SHA256")"
    stats="$(migration_directory_file_stats "$MIGRATOR_TARGET_DIR/var/$profile")" || return 1
    read -r actual_count actual_bytes actual_tree <<< "$stats"
    [[ "$expected_count" =~ ^[0-9]+$ && "$actual_count" == "$expected_count" \
      && "$expected_bytes" =~ ^[0-9]+$ && "$actual_bytes" == "$expected_bytes" \
      && "$expected_tree" =~ ^[0-9a-f]{64}$ && "$actual_tree" == "$expected_tree" ]] \
      || { migration_fail "$profile 文件内容摘要校验失败"; return 1; }
  done
  actual="$(migration_root_compose exec -T postgres psql -At -U "$postgres_user" \
    -d "$postgres_db" -c 'SELECT version_num FROM alembic_version LIMIT 1;')" || return 1
  expected="$(migrator_manifest_value "$manifest" ALEMBIC_VERSION)"
  [[ -n "$actual" && "$actual" == "$expected" ]] \
    || { migration_fail "数据库迁移版本校验失败"; return 1; }

  migration_root_compose run --rm --no-deps \
    -e ENSURE_DEFAULT_ADMIN=0 -e RUN_MIGRATIONS=1 \
    web flask db upgrade || return 1
  migration_root_compose up -d --remove-orphans || return 1
  migrator_wait_service postgres 120 || return 1
  migrator_wait_service redis 90 || return 1
  migrator_wait_service web 180 || return 1
  migrator_wait_service worker 180 || return 1
  migrator_wait_service nginx 180 || return 1
  migrator_wait_service backup 180 || return 1
  migrator_healthcheck || return 1
  published="$(migration_root_compose port postgres 5432 2>/dev/null || true)"
  [[ -z "$published" ]] || { migration_fail "PostgreSQL 不应发布宿主机端口"; return 1; }
  published="$(migration_root_compose port redis 6379 2>/dev/null || true)"
  [[ -z "$published" ]] || { migration_fail "Redis 不应发布宿主机端口"; return 1; }
  post_facts="$(migrator_local_preflight)" || return 1
  expected="$(migrator_fact "$MIGRATOR_TARGET_FACTS" WEB_IMAGE_DIGEST)" || return 1
  actual="$(migrator_fact "$post_facts" WEB_IMAGE_DIGEST)" || return 1
  [[ -n "$expected" && "$actual" == "$expected" ]] \
    || { migration_fail "目标应用镜像 digest 发生变化"; return 1; }
  if [[ "$label" == "rollback" ]]; then
    migrator_restore_exact_service_set "$manifest" || return 1
  fi
}

migrator_remove_previous_directories() {
  local label="$1"
  local profile
  for profile in redis uploads instance; do
    migration_root rm -rf -- "$MIGRATOR_TARGET_DIR/var/$profile.migration-previous-$label" || return 1
  done
}

migrator_pull_source_bundle() {
  local output remote_bundle remote_checksum
  MIGRATOR_SOURCE_FROZEN=1
  output="$(migrator_remote_export prepare)" || return 1
  remote_bundle="$(migrator_fact "$output" BUNDLE_PATH)"
  remote_checksum="$(migrator_fact "$output" CHECKSUM_PATH)"
  [[ "$remote_bundle" == "$MIGRATOR_SOURCE_DIR/backups/migrations/$MIGRATOR_MIGRATION_ID/"* \
    && "$remote_checksum" == "$remote_bundle.sha256" ]] || return 1
  MIGRATOR_SOURCE_BUNDLE="$MIGRATOR_WORKSPACE/migration-$MIGRATOR_MIGRATION_ID.tar.gz"
  MIGRATOR_SOURCE_CHECKSUM="$MIGRATOR_SOURCE_BUNDLE.sha256"
  "${MIGRATOR_SCP[@]}" "$MIGRATOR_SOURCE:$remote_bundle" "$MIGRATOR_SOURCE_BUNDLE" || return 1
  "${MIGRATOR_SCP[@]}" "$MIGRATOR_SOURCE:$remote_checksum" "$MIGRATOR_SOURCE_CHECKSUM" || return 1
  chmod 600 "$MIGRATOR_SOURCE_BUNDLE" "$MIGRATOR_SOURCE_CHECKSUM" || return 1
}

migrator_cleanup_remote() {
  [[ -n "$MIGRATOR_REMOTE_TEMP" ]] || return 0
  migrator_remote rm -rf -- "$MIGRATOR_REMOTE_TEMP" || return 1
  MIGRATOR_REMOTE_TEMP=""
}

migrator_release_target_lock() {
  (( MIGRATOR_TARGET_LOCK_HELD == 1 )) || return 0
  migration_lock_release "$MIGRATOR_TARGET_LOCK" "$MIGRATOR_MIGRATION_ID" || return 1
  MIGRATOR_TARGET_LOCK_HELD=0
}

migrator_failure_handler() {
  local exit_status=$?
  local rollback_failed=0 source_resume_failed=0 target_resume_failed=0
  trap - EXIT HUP INT TERM
  if (( exit_status != 0 && MIGRATOR_FINISHED == 0 && MIGRATOR_COMMIT_STARTED == 1 )); then
    migration_log ERROR "目标已验证且源端提交结果不确定；为防止数据分叉，不回滚服务器 2，也不重启服务器 1"
    migration_log ERROR "请保留目标锁并人工确认源端 FINALIZED 状态"
  elif (( exit_status != 0 && MIGRATOR_FINISHED == 0 )); then
    if (( MIGRATOR_TARGET_CAPTURE_ACTIVE == 1 )); then
      migration_log ERROR "正在恢复服务器 2 创建回滚点前的服务状态"
      bash "$MIGRATOR_SCRIPT_DIR/export_production_data.sh" resume \
        --source-dir "$MIGRATOR_TARGET_DIR" \
        --migration-id "$MIGRATOR_TARGET_ROLLBACK_ID" >/dev/null \
        || target_resume_failed=1
    fi
    if (( MIGRATOR_TARGET_MUTATED == 1 && MIGRATOR_ROLLBACK_READY == 1 && MIGRATOR_ROLLBACK_ACTIVE == 0 )); then
      MIGRATOR_ROLLBACK_ACTIVE=1
      migration_log ERROR "目标恢复失败，正在恢复服务器 2 迁移前状态"
      migrator_restore_bundle "$MIGRATOR_ROLLBACK_BUNDLE" "$MIGRATOR_ROLLBACK_CHECKSUM" rollback \
        || rollback_failed=1
    fi
    if (( MIGRATOR_SOURCE_FROZEN == 1 )); then
      migration_log ERROR "正在恢复服务器 1 原运行服务"
      migrator_remote_export resume >/dev/null || source_resume_failed=1
    fi
  fi
  migrator_cleanup_remote || true
  if (( MIGRATOR_COMMIT_STARTED == 0 )); then
    migrator_release_target_lock || migration_log ERROR "释放服务器 2 迁移锁失败"
  fi
  if (( rollback_failed == 1 )); then
    migration_log ERROR "服务器 2 自动回滚未完全成功"
  fi
  if (( target_resume_failed == 1 )); then
    migration_log ERROR "服务器 2 回滚点创建后的服务恢复未完全成功"
  fi
  if (( source_resume_failed == 1 )); then
    migration_log ERROR "服务器 1 自动恢复未完全成功"
  fi
  exit "$exit_status"
}

migrator_run() {
  local status
  migrator_validate_args || return $?
  migrator_build_transport || return 1
  MIGRATOR_MIGRATION_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  migration_validate_id "$MIGRATOR_MIGRATION_ID" || return 1
  migrator_configure_target
  migration_log INFO "迁移 ID: $MIGRATOR_MIGRATION_ID"
  MIGRATOR_TARGET_LOCK="$MIGRATOR_TARGET_DIR/var/.production-data-migration.lock"
  migration_lock_acquire "$MIGRATOR_TARGET_LOCK" "$MIGRATOR_MIGRATION_ID" || return 1
  MIGRATOR_TARGET_LOCK_HELD=1

  migration_log INFO "上传临时源端 helper 并执行两端只读预检"
  migrator_upload_helpers || return 1
  MIGRATOR_TARGET_FACTS="$(migrator_local_preflight)" || return 1
  MIGRATOR_SOURCE_FACTS="$(migrator_remote_export preflight)" || return 1
  migrator_compare_preflight || return 1
  migrator_healthcheck || return 1
  if (( MIGRATOR_DRY_RUN == 1 )); then
    migrator_cleanup_remote || return 1
    migrator_release_target_lock || return 1
    MIGRATOR_FINISHED=1
    migration_log INFO "dry-run 预检通过，未停止服务、未创建迁移包"
    return 0
  fi
  migrator_confirm || return 1

  MIGRATOR_WORKSPACE="$MIGRATOR_TARGET_DIR/backups/migrations/target-$MIGRATOR_MIGRATION_ID"
  [[ ! -e "$MIGRATOR_WORKSPACE" ]] || return 1
  mkdir -p "$(dirname "$MIGRATOR_WORKSPACE")" || return 1
  mkdir -m 700 "$MIGRATOR_WORKSPACE" || return 1
  migration_log INFO "创建服务器 2 一致性回滚点"
  migrator_copy_rollback_bundle || return 1
  migration_log INFO "冻结服务器 1 并拉取最终迁移包"
  migrator_pull_source_bundle || return 1
  migration_log INFO "校验并恢复服务器 2"
  migrator_restore_bundle "$MIGRATOR_SOURCE_BUNDLE" "$MIGRATOR_SOURCE_CHECKSUM" source || return 1

  MIGRATOR_COMMIT_STARTED=1
  if ! migrator_remote_export finalize >/dev/null; then
    migration_log WARN "源端 finalize 首次确认失败，正在执行幂等重试"
    migrator_remote_export finalize >/dev/null || return 1
  fi
  MIGRATOR_SOURCE_FROZEN=0
  MIGRATOR_TARGET_MUTATED=0
  MIGRATOR_FINISHED=1
  migrator_cleanup_remote || migration_log WARN "迁移已提交，但远端 helper 清理失败"
  migrator_remove_previous_directories source || migration_log WARN "迁移已提交，但目标旧目录清理失败"
  migrator_remove_previous_directories rollback || migration_log WARN "迁移已提交，但目标回滚旧目录清理失败"
  if (( MIGRATOR_KEEP_BUNDLE == 0 )); then
    rm -rf -- "$MIGRATOR_WORKSPACE" || migration_log WARN "迁移已提交，但本地迁移包清理失败"
  fi
  migrator_release_target_lock || migration_log WARN "迁移已提交，但服务器 2 迁移锁清理失败"
  migration_log INFO "迁移完成；服务器 1 应用服务保持停止"
  printf '\n后续操作：\n'
  printf '1. 将 DNS A/AAAA 记录切换到服务器 2。\n'
  printf '2. 在服务器 2 重新运行部署脚本签发或恢复 HTTPS。\n'
  printf '3. 验证登录、上传、后台任务、第三方回调和外部 IP 白名单。\n'
}

migrator_main() {
  local parse_status
  migrator_parse_args "$@"
  parse_status=$?
  if (( parse_status == 10 )); then
    return 0
  fi
  (( parse_status == 0 )) || return "$parse_status"
  trap migrator_failure_handler EXIT
  trap 'exit 130' HUP INT TERM
  migrator_run
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -u -o pipefail
  migrator_main "$@"
fi
