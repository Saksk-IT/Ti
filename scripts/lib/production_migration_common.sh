#!/usr/bin/env bash

# Shared primitives for production migration scripts. This file is sourced.
umask 077

migration_fail() {
  printf '错误: %s\n' "$*" >&2
  return 1
}

migration_log() {
  local level="${1:-INFO}"
  shift || true
  local message="$*"
  local variable_name secret_value temporary_value
  local -a secret_values=()
  local index other_index longest_index

  while IFS= read -r variable_name; do
    case "$variable_name" in
      *SECRET*|*PASSWORD*|*TOKEN*|*DSN*|*KEY*|*CREDENTIAL*|*AUTH*)
        secret_value="${!variable_name-}"
        if [[ -n "$secret_value" ]]; then
          secret_values[${#secret_values[@]}]="$secret_value"
        fi
        ;;
    esac
  done < <(compgen -v)

  for (( index = 0; index < ${#secret_values[@]}; index++ )); do
    longest_index="$index"
    for (( other_index = index + 1; other_index < ${#secret_values[@]}; other_index++ )); do
      if (( ${#secret_values[$other_index]} > ${#secret_values[$longest_index]} )); then
        longest_index="$other_index"
      fi
    done
    if (( longest_index != index )); then
      temporary_value="${secret_values[$index]}"
      secret_values[$index]="${secret_values[$longest_index]}"
      secret_values[$longest_index]="$temporary_value"
    fi
  done

  for secret_value in "${secret_values[@]}"; do
    message="${message//"$secret_value"/[REDACTED]}"
  done

  printf '[%s] %s\n' "$level" "$message" >&2
}

migration_require_command() {
  command -v "$1" >/dev/null 2>&1 \
    || migration_fail "缺少必需命令: $1"
}

migration_validate_ssh_target() {
  local target="${1:-}"
  if [[ ! "$target" =~ ^[A-Za-z_][A-Za-z0-9_.-]*@[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ ]]; then
    migration_fail "SSH 目标格式无效"
    return 1
  fi
  if [[ "$target" == *".."* ]]; then
    migration_fail "SSH 目标格式无效"
    return 1
  fi
}

migration_validate_port() {
  local port="${1:-}"
  local port_number
  if [[ ! "$port" =~ ^[0-9]+$ ]]; then
    migration_fail "端口必须是整数"
    return 1
  fi
  if (( ${#port} > 5 )); then
    migration_fail "端口超出范围"
    return 1
  fi
  port_number=$((10#$port))
  if (( port_number < 1 || port_number > 65535 )); then
    migration_fail "端口超出范围"
    return 1
  fi
}

migration_validate_absolute_dir() {
  local path="${1:-}"
  if [[ "$path" != /* ]]; then
    migration_fail "目录必须是绝对路径"
    return 1
  fi
  if [[ "$path" =~ [[:cntrl:]] ]]; then
    migration_fail "目录包含控制字符"
    return 1
  fi
  case "/${path#/}/" in
    */../*|*/./*) migration_fail "目录不能包含 . 或 .. 路径段"; return 1 ;;
  esac
}

migration_validate_id() {
  local migration_id="${1:-}"
  [[ "$migration_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] \
    || migration_fail "迁移 ID 格式无效"
}

migration_read_env_value() {
  local env_file="$1"
  local key="$2"
  if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    migration_fail "env 键名无效"
    return 1
  fi
  if [[ ! -f "$env_file" ]]; then
    migration_fail "env 文件不存在"
    return 1
  fi

  awk -v wanted="$key" '
    {
      line = $0
      sub(/^[[:space:]]*export[[:space:]]+/, "", line)
      if (index(line, wanted "=") != 1) next
      value = substr(line, length(wanted) + 2)
      if (value ~ /^".*"$/ || value ~ /^\047.*\047$/) {
        value = substr(value, 2, length(value) - 2)
      }
      print value
      exit
    }
  ' "$env_file"
}

migration_sha256() {
  local path="$1"
  local sha256sum_bin="${MIGRATION_SHA256SUM_BIN:-sha256sum}"
  local shasum_bin="${MIGRATION_SHASUM_BIN:-shasum}"
  local checksum_output digest
  if command -v "$sha256sum_bin" >/dev/null 2>&1; then
    if ! checksum_output="$("$sha256sum_bin" "$path")"; then
      migration_fail "SHA-256 计算失败"
      return 1
    fi
  elif command -v "$shasum_bin" >/dev/null 2>&1; then
    if ! checksum_output="$("$shasum_bin" -a 256 "$path")"; then
      migration_fail "SHA-256 计算失败"
      return 1
    fi
  else
    migration_fail "缺少 sha256sum 或 shasum"
    return 1
  fi
  digest="${checksum_output%%[[:space:]]*}"
  [[ "$digest" =~ ^[0-9A-Fa-f]{64}$ ]] \
    || { migration_fail "SHA-256 输出格式无效"; return 1; }
  printf '%s\n' "$digest"
}

migration_root() {
  local sudo_bin="${MIGRATION_SUDO_BIN:-sudo}"
  if [[ "$(id -u)" == "0" ]]; then
    "$@"
    return
  fi
  if ! "$sudo_bin" -n true >/dev/null 2>&1; then
    migration_fail "non-interactive sudo is required"
    return 1
  fi
  "$sudo_bin" -n "$@"
}

migration_docker() {
  local docker_bin="${MIGRATION_DOCKER_BIN:-docker}"
  "$docker_bin" "$@"
}

migration_root_docker() {
  local docker_bin="${MIGRATION_DOCKER_BIN:-docker}"
  migration_root "$docker_bin" "$@"
}

migration_compose() {
  local env_file="${MIGRATION_ENV_FILE:-.env.production}"
  local compose_file="${MIGRATION_COMPOSE_FILE:-compose.prod.yml}"
  local project_name="${MIGRATION_PROJECT_NAME:-}"
  if [[ -n "$project_name" ]]; then
    migration_docker compose --project-name "$project_name" \
      --env-file "$env_file" -f "$compose_file" "$@"
  else
    migration_docker compose --env-file "$env_file" -f "$compose_file" "$@"
  fi
}

migration_root_compose() {
  local env_file="${MIGRATION_ENV_FILE:-.env.production}"
  local compose_file="${MIGRATION_COMPOSE_FILE:-compose.prod.yml}"
  local project_name="${MIGRATION_PROJECT_NAME:-}"
  if [[ -n "$project_name" ]]; then
    migration_root_docker compose --project-name "$project_name" \
      --env-file "$env_file" -f "$compose_file" "$@"
  else
    migration_root_docker compose --env-file "$env_file" -f "$compose_file" "$@"
  fi
}

migration_project_name_from_dir() {
  local directory="$1"
  local name
  name="$(basename "$directory" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')" || return 1
  [[ "$name" =~ ^[a-z0-9][a-z0-9_-]*$ ]] \
    || { migration_fail "无法从部署目录确定 Compose 项目名"; return 1; }
  printf '%s\n' "$name"
}

migration_lock_acquire() {
  local lock_dir="$1"
  local owner="${2:-${MIGRATION_LOCK_OWNER:-$$}}"
  local owner_file="$lock_dir/owner"
  if ! mkdir "$lock_dir" 2>/dev/null; then
    migration_fail "迁移锁已存在: $lock_dir"
    return 1
  fi
  if ! chmod 700 "$lock_dir" \
    || ! printf '%s\n' "$owner" > "$owner_file" \
    || ! chmod 600 "$owner_file"; then
    rm -rf -- "$lock_dir"
    migration_fail "无法初始化迁移锁"
    return 1
  fi
}

migration_lock_release() {
  local lock_dir="$1"
  local owner="${2:-${MIGRATION_LOCK_OWNER:-$$}}"
  [[ -d "$lock_dir" ]] || return 0
  migration_lock_assert_owner "$lock_dir" "$owner" || return 1
  rm -rf -- "$lock_dir"
}

migration_lock_assert_owner() {
  local lock_dir="$1"
  local owner="${2:-${MIGRATION_LOCK_OWNER:-$$}}"
  local recorded_owner
  [[ -d "$lock_dir" ]] || { migration_fail "迁移锁不存在"; return 1; }
  if [[ ! -f "$lock_dir/owner" ]]; then
    migration_fail "迁移锁缺少所有者"
    return 1
  fi
  recorded_owner="$(cat "$lock_dir/owner")" || return 1
  if [[ "$recorded_owner" != "$owner" ]]; then
    migration_fail "迁移锁所有者不匹配"
    return 1
  fi
}

migration_state_write() {
  local state_file="$1"
  shift
  if (( $# == 0 || $# % 2 != 0 )); then
    migration_fail "状态写入参数必须是 KEY VALUE 对"
    return 1
  fi

  local state_dir temp_file key value working_file
  state_dir="$(dirname "$state_file")" || return 1
  if [[ ! -d "$state_dir" ]]; then
    if ! mkdir -p "$state_dir" || ! chmod 700 "$state_dir"; then
      migration_fail "无法创建状态目录"
      return 1
    fi
  fi
  if ! temp_file="$(mktemp "${state_dir}/.$(basename "$state_file").tmp.XXXXXX")"; then
    migration_fail "无法创建状态临时文件"
    return 1
  fi
  if ! chmod 600 "$temp_file"; then
    rm -f "$temp_file"
    migration_fail "无法设置状态临时文件权限"
    return 1
  fi
  if [[ -f "$state_file" ]]; then
    if ! cat "$state_file" > "$temp_file"; then
      rm -f "$temp_file"
      migration_fail "无法读取原状态文件"
      return 1
    fi
  fi

  while (( $# > 0 )); do
    key="$1"
    value="$2"
    shift 2
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] \
      || { rm -f "$temp_file"; migration_fail "状态键名无效"; return 1; }
    [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *\\* ]] \
      || { rm -f "$temp_file"; migration_fail "状态值包含不安全字符"; return 1; }
    working_file="${temp_file}.next"
    if ! awk -v wanted="$key" -v replacement="$value" '
      BEGIN { found = 0 }
      index($0, wanted "=") == 1 { print wanted "=" replacement; found = 1; next }
      { print }
      END { if (!found) print wanted "=" replacement }
    ' "$temp_file" > "$working_file"; then
      rm -f "$working_file" "$temp_file"
      migration_fail "无法更新状态文件"
      return 1
    fi
    if ! chmod 600 "$working_file" || ! mv -f "$working_file" "$temp_file"; then
      rm -f "$working_file" "$temp_file"
      migration_fail "无法替换状态临时文件"
      return 1
    fi
  done

  if ! chmod 600 "$temp_file" || ! mv -f "$temp_file" "$state_file"; then
    rm -f "$temp_file"
    migration_fail "无法原子替换状态文件"
    return 1
  fi
  chmod 600 "$state_file" || { migration_fail "无法设置状态文件权限"; return 1; }
  migration_fsync_path "$state_file" || return 1
}

migration_state_read() {
  local state_file="$1"
  local key="$2"
  [[ -f "$state_file" ]] || return 1
  awk -v wanted="$key" '
    index($0, wanted "=") == 1 {
      print substr($0, length(wanted) + 2)
      exit
    }
  ' "$state_file"
}

migration_fsync_path() {
  local path="$1"
  local python_bin="${MIGRATION_PYTHON_BIN:-python3}"
  "$python_bin" - "$path" <<'PY'
import os
from pathlib import Path
import sys

path = Path(sys.argv[1])
with path.open("rb") as stream:
    os.fsync(stream.fileno())
directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
try:
    os.fsync(directory_fd)
finally:
    os.close(directory_fd)
PY
}

migration_capture_running_services() {
  migration_compose ps --services --filter status=running
}

migration_database_row_summary() {
  local postgres_user="$1"
  local postgres_db="$2"
  [[ "$postgres_user" =~ ^[A-Za-z0-9_.-]+$ && "$postgres_db" =~ ^[A-Za-z0-9_.-]+$ ]] \
    || { migration_fail "PostgreSQL 用户名或数据库名格式无效"; return 1; }
  migration_root_compose exec -T postgres \
    psql -X -qAt -v ON_ERROR_STOP=1 -U "$postgres_user" -d "$postgres_db" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
CREATE TEMP TABLE migration_row_counts (
  table_name text PRIMARY KEY,
  row_count bigint NOT NULL
) ON COMMIT DROP;
DO $migration_summary$
DECLARE
  item record;
  counted bigint;
BEGIN
  FOR item IN
    SELECT schemaname, tablename
    FROM pg_catalog.pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename
  LOOP
    EXECUTE format('SELECT count(*) FROM %I.%I', item.schemaname, item.tablename)
      INTO counted;
    INSERT INTO migration_row_counts(table_name, row_count)
      VALUES (item.tablename, counted);
  END LOOP;
END
$migration_summary$;
COPY (
  SELECT table_name || E'\t' || row_count::text
  FROM migration_row_counts
  ORDER BY table_name
) TO STDOUT;
ROLLBACK;
SQL
}

migration_directory_file_stats() {
  local directory="$1"
  local python_bin="${MIGRATION_PYTHON_BIN:-python3}"
  migration_root "$python_bin" - "$directory" <<'PY'
import hashlib
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
root_stat = root.lstat()
if not stat.S_ISDIR(root_stat.st_mode) or root.is_symlink():
    raise SystemExit("unsafe root directory")

digest = hashlib.sha256()
file_count = 0
total_bytes = 0
for current, directories, files in os.walk(root, topdown=True, followlinks=False):
    current_path = Path(current)
    directories.sort()
    files.sort()
    for directory_name in directories:
        child = current_path / directory_name
        if child.is_symlink() or not stat.S_ISDIR(child.lstat().st_mode):
            raise SystemExit("unsafe directory member")
    for file_name in files:
        child = current_path / file_name
        child_stat = child.lstat()
        if not stat.S_ISREG(child_stat.st_mode):
            raise SystemExit("unsafe file member")
        relative = os.fsencode(child.relative_to(root).as_posix())
        digest.update(b"F")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(child_stat.st_size.to_bytes(8, "big"))
        with child.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        file_count += 1
        total_bytes += child_stat.st_size
print(file_count, total_bytes, digest.hexdigest())
PY
}

migration_wait_compose_service() {
  local service="$1"
  local timeout_seconds="${2:-120}"
  local start_time now container_id service_status
  [[ "$service" =~ ^[A-Za-z0-9_-]+$ && "$timeout_seconds" =~ ^[0-9]+$ ]] || return 1
  start_time="$(date +%s)"
  while true; do
    container_id="$(migration_root_compose ps -q "$service" 2>/dev/null)" || true
    if [[ -n "$container_id" ]]; then
      service_status="$(migration_root_docker inspect \
        --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
        "$container_id" 2>/dev/null)" || true
      [[ "$service_status" == "healthy" || "$service_status" == "running" ]] && return 0
    fi
    now="$(date +%s)"
    (( now - start_time < timeout_seconds )) \
      || { migration_fail "等待服务 $service 健康超时"; return 1; }
    sleep 2
  done
}
