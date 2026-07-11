#!/usr/bin/env bash

# Export a consistent production snapshot on the source server.

EXPORTER_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXPORTER_COMMON_PATH="${MIGRATION_COMMON_PATH:-${EXPORTER_SCRIPT_DIR}/lib/production_migration_common.sh}"
# shellcheck source=scripts/lib/production_migration_common.sh
source "$EXPORTER_COMMON_PATH"

EXPORTER_PREPARE_COMPLETE=0
EXPORTER_PREPARE_OWNS_LOCK=0
EXPORTER_SOURCE_DIR=""
EXPORTER_MIGRATION_ID=""

exporter_usage() {
  cat <<'EOF'
用法:
  export_production_data.sh preflight --source-dir ABSOLUTE_DIR --migration-id ID
  export_production_data.sh prepare   --source-dir ABSOLUTE_DIR --migration-id ID
  export_production_data.sh resume    --source-dir ABSOLUTE_DIR --migration-id ID
  export_production_data.sh finalize  --source-dir ABSOLUTE_DIR --migration-id ID
EOF
}

exporter_validate_source_dir() {
  local source_dir="$1"
  migration_validate_absolute_dir "$source_dir" || return 1
  if [[ "$source_dir" == "/" || ! -d "$source_dir" || -L "$source_dir" ]]; then
    migration_fail "源部署目录无效"
    return 1
  fi
}

exporter_configure_context() {
  local source_dir="$1"
  MIGRATION_ENV_FILE="$source_dir/.env.production"
  MIGRATION_COMPOSE_FILE="$source_dir/compose.prod.yml"
  MIGRATION_PROJECT_NAME="$(migration_project_name_from_dir "$source_dir")" || return 1
  export MIGRATION_ENV_FILE MIGRATION_COMPOSE_FILE MIGRATION_PROJECT_NAME
}

exporter_workspace_path() {
  printf '%s/backups/migrations/%s\n' "$1" "$2"
}

exporter_lock_path() {
  printf '%s/var/.production-migration.lock\n' "$1"
}

exporter_validate_deployment() {
  local source_dir="$1"
  local required_dir required_command
  for required_command in awk sed find du df tar cat "${MIGRATION_PYTHON_BIN:-python3}"; do
    migration_require_command "$required_command" || return 1
  done
  [[ -f "$source_dir/.env.production" ]] \
    || { migration_fail "缺少 .env.production"; return 1; }
  [[ -f "$source_dir/compose.prod.yml" ]] \
    || { migration_fail "缺少 compose.prod.yml"; return 1; }
  for required_dir in postgres redis uploads instance; do
    [[ -d "$source_dir/var/$required_dir" && ! -L "$source_dir/var/$required_dir" ]] \
      || { migration_fail "缺少安全的数据目录: var/$required_dir"; return 1; }
  done
}

exporter_normalize_services() {
  local raw_services="$1"
  local service
  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    [[ "$service" =~ ^[A-Za-z0-9_-]+$ ]] \
      || { migration_fail "Compose 服务名无效"; return 1; }
  done <<< "$raw_services"
  printf '%s\n' "$raw_services" | awk 'NF { if (seen++) printf ","; printf "%s", $0 } END { print "" }'
}

exporter_collect_facts() {
  local source_dir="$1"
  local raw_services image_id postgres_version redis_version machine_id_file git_bin
  local postgres_user postgres_db required_space_kb

  migration_root true || return 1
  migration_root_compose config >/dev/null || return 1

  raw_services="$(migration_root_compose ps --services --filter status=running)" || return 1
  EXPORTER_RUNNING_SERVICES="$(exporter_normalize_services "$raw_services")" || return 1

  postgres_version="$(migration_root_compose exec -T postgres postgres --version)" || return 1
  redis_version="$(migration_root_compose exec -T redis redis-server --version)" || return 1
  EXPORTER_POSTGRES_VERSION="$postgres_version"
  EXPORTER_REDIS_VERSION="$redis_version"
  EXPORTER_POSTGRES_MAJOR="$(printf '%s\n' "$postgres_version" | sed -n 's/.*PostgreSQL) \([0-9][0-9]*\).*/\1/p')"
  EXPORTER_REDIS_MAJOR="$(printf '%s\n' "$redis_version" | sed -n 's/.* v=\([0-9][0-9]*\).*/\1/p')"
  [[ -n "$EXPORTER_POSTGRES_MAJOR" && -n "$EXPORTER_REDIS_MAJOR" ]] \
    || { migration_fail "无法解析 PostgreSQL 或 Redis 版本"; return 1; }

  image_id="$(migration_root_compose ps -q web)" || return 1
  [[ -n "$image_id" ]] || { migration_fail "web 容器未运行"; return 1; }
  EXPORTER_WEB_IMAGE_ID="$(migration_root_docker inspect --format='{{.Image}}' "$image_id")" || return 1
  EXPORTER_WEB_IMAGE_DIGEST="$(migration_root_docker image inspect --format='{{index .RepoDigests 0}}' "$EXPORTER_WEB_IMAGE_ID")" || return 1
  [[ "$EXPORTER_WEB_IMAGE_DIGEST" == *@sha256:* ]] \
    || { migration_fail "无法取得 web 镜像 digest"; return 1; }

  machine_id_file="${MIGRATION_MACHINE_ID_FILE:-/etc/machine-id}"
  [[ -f "$machine_id_file" ]] || { migration_fail "缺少 machine-id"; return 1; }
  EXPORTER_MACHINE_ID="$(cat "$machine_id_file")" || return 1
  [[ "$EXPORTER_MACHINE_ID" =~ ^[A-Za-z0-9._-]+$ ]] \
    || { migration_fail "machine-id 格式无效"; return 1; }

  git_bin="${MIGRATION_GIT_BIN:-git}"
  migration_require_command "$git_bin" || return 1
  EXPORTER_GIT_COMMIT="$("$git_bin" -C "$source_dir" rev-parse HEAD)" || return 1
  [[ "$EXPORTER_GIT_COMMIT" =~ ^[0-9A-Fa-f]{40}$ ]] \
    || { migration_fail "Git 提交格式无效"; return 1; }

  EXPORTER_DATA_SIZE_KB="$(
    migration_root du -sk \
      "$source_dir/var/postgres" \
      "$source_dir/var/redis" \
      "$source_dir/var/uploads" \
      "$source_dir/var/instance" \
      | awk '{ total += $1 } END { print total + 0 }'
  )" || return 1
  [[ "$EXPORTER_DATA_SIZE_KB" =~ ^[0-9]+$ ]] \
    || { migration_fail "无法统计源数据大小"; return 1; }
  EXPORTER_AVAILABLE_KB="$(
    migration_root df -Pk "$source_dir/backups" | awk 'NR == 2 { print $4 }'
  )" || return 1
  [[ "$EXPORTER_AVAILABLE_KB" =~ ^[0-9]+$ ]] \
    || { migration_fail "无法统计源磁盘空间"; return 1; }
  required_space_kb=$((EXPORTER_DATA_SIZE_KB * 2 + 1024))
  (( EXPORTER_AVAILABLE_KB >= required_space_kb )) \
    || { migration_fail "源服务器剩余空间不足以生成迁移包"; return 1; }

  EXPORTER_COMPOSE_SHA256="$(migration_sha256 "$source_dir/compose.prod.yml")" || return 1
  postgres_user="$(migration_read_env_value "$source_dir/.env.production" POSTGRES_USER)" || return 1
  postgres_db="$(migration_read_env_value "$source_dir/.env.production" POSTGRES_DB)" || return 1
  postgres_user="${postgres_user:-studyuser}"
  postgres_db="${postgres_db:-ti_db}"
  [[ "$postgres_user" =~ ^[A-Za-z0-9_.-]+$ && "$postgres_db" =~ ^[A-Za-z0-9_.-]+$ ]] \
    || { migration_fail "PostgreSQL 用户名或数据库名格式无效"; return 1; }
  EXPORTER_ALEMBIC_VERSION="$(
    migration_root_compose exec -T postgres psql -At \
      -U "$postgres_user" -d "$postgres_db" \
      -c 'SELECT version_num FROM alembic_version LIMIT 1;'
  )" || return 1
  [[ "$EXPORTER_ALEMBIC_VERSION" =~ ^[A-Za-z0-9_-]+$ ]] \
    || { migration_fail "数据库迁移版本格式无效"; return 1; }
  EXPORTER_UPLOADS_FILE_COUNT="$(migration_root find "$source_dir/var/uploads" -type f -print | awk 'END { print NR + 0 }')" || return 1
  EXPORTER_INSTANCE_FILE_COUNT="$(migration_root find "$source_dir/var/instance" -type f -print | awk 'END { print NR + 0 }')" || return 1
}

exporter_print_facts() {
  printf 'SOURCE_MACHINE_ID=%s\n' "$EXPORTER_MACHINE_ID"
  printf 'SOURCE_GIT_COMMIT=%s\n' "$EXPORTER_GIT_COMMIT"
  printf 'RUNNING_SERVICES=%s\n' "$EXPORTER_RUNNING_SERVICES"
  printf 'POSTGRES_MAJOR=%s\n' "$EXPORTER_POSTGRES_MAJOR"
  printf 'REDIS_MAJOR=%s\n' "$EXPORTER_REDIS_MAJOR"
  printf 'WEB_IMAGE_ID=%s\n' "$EXPORTER_WEB_IMAGE_ID"
  printf 'WEB_IMAGE_DIGEST=%s\n' "$EXPORTER_WEB_IMAGE_DIGEST"
  printf 'DATA_SIZE_KB=%s\n' "$EXPORTER_DATA_SIZE_KB"
  printf 'AVAILABLE_KB=%s\n' "$EXPORTER_AVAILABLE_KB"
  printf 'COMPOSE_SHA256=%s\n' "$EXPORTER_COMPOSE_SHA256"
  printf 'ALEMBIC_VERSION=%s\n' "$EXPORTER_ALEMBIC_VERSION"
  printf 'UPLOADS_FILE_COUNT=%s\n' "$EXPORTER_UPLOADS_FILE_COUNT"
  printf 'INSTANCE_FILE_COUNT=%s\n' "$EXPORTER_INSTANCE_FILE_COUNT"
}

exporter_collect_frozen_file_stats() {
  local source_dir="$1"
  local stats
  stats="$(migration_directory_file_stats "$source_dir/var/uploads")" || return 1
  read -r EXPORTER_UPLOADS_FILE_COUNT EXPORTER_UPLOADS_TOTAL_BYTES EXPORTER_UPLOADS_TREE_SHA256 <<< "$stats"
  stats="$(migration_directory_file_stats "$source_dir/var/instance")" || return 1
  read -r EXPORTER_INSTANCE_FILE_COUNT EXPORTER_INSTANCE_TOTAL_BYTES EXPORTER_INSTANCE_TREE_SHA256 <<< "$stats"
  [[ "$EXPORTER_UPLOADS_FILE_COUNT" =~ ^[0-9]+$ \
    && "$EXPORTER_UPLOADS_TOTAL_BYTES" =~ ^[0-9]+$ \
    && "$EXPORTER_UPLOADS_TREE_SHA256" =~ ^[0-9a-f]{64}$ \
    && "$EXPORTER_INSTANCE_FILE_COUNT" =~ ^[0-9]+$ \
    && "$EXPORTER_INSTANCE_TOTAL_BYTES" =~ ^[0-9]+$ \
    && "$EXPORTER_INSTANCE_TREE_SHA256" =~ ^[0-9a-f]{64}$ ]] \
    || { migration_fail "冻结后的文件摘要格式无效"; return 1; }
}

exporter_preflight() {
  local source_dir="$1"
  exporter_validate_deployment "$source_dir" || return 1
  exporter_collect_facts "$source_dir" || return 1
  exporter_print_facts
}

exporter_state_has_service() {
  local services_csv="$1"
  local service="$2"
  case ",$services_csv," in
    *",$service,"*) return 0 ;;
    *) return 1 ;;
  esac
}

exporter_remove_payloads() {
  local workspace="$1"
  local path
  for path in \
    database.dump database-summary.txt redis.tar.gz uploads.tar.gz instance.tar.gz source.env.production \
    manifest.txt checksums.sha256 migration-*.tar.gz migration-*.tar.gz.sha256; do
    rm -f -- "$workspace"/$path || return 1
  done
}

exporter_resume_internal() {
  local source_dir="$1"
  local migration_id="$2"
  local workspace state_file lock_dir status services_csv service failed
  workspace="$(exporter_workspace_path "$source_dir" "$migration_id")"
  state_file="$workspace/state"
  lock_dir="$(exporter_lock_path "$source_dir")"

  if [[ ! -f "$state_file" ]]; then
    if [[ -d "$lock_dir" ]]; then
      migration_lock_assert_owner "$lock_dir" "$migration_id" || return 1
      migration_lock_release "$lock_dir" "$migration_id" || return 1
    fi
    printf 'STATUS=RESUMED\n'
    return 0
  fi
  status="$(migration_state_read "$state_file" STATUS)" || return 1
  [[ "$(migration_state_read "$state_file" MIGRATION_ID)" == "$migration_id" ]] \
    || { migration_fail "迁移状态 ID 不匹配"; return 1; }
  if [[ "$status" == "RESUMED" ]]; then
    if [[ -d "$lock_dir" ]]; then
      migration_lock_release "$lock_dir" "$migration_id" || return 1
    fi
    printf 'STATUS=RESUMED\n'
    return 0
  fi
  migration_lock_assert_owner "$lock_dir" "$migration_id" || return 1
  if [[ "$status" != "PREPARING" && "$status" != "FROZEN" ]]; then
    migration_fail "当前状态不允许恢复源服务: $status"
    return 1
  fi
  services_csv="$(migration_state_read "$state_file" RUNNING_SERVICES)" || return 1
  [[ "$services_csv" =~ ^([A-Za-z0-9_-]+(,[A-Za-z0-9_-]+)*)?$ ]] \
    || { migration_fail "状态中的服务列表无效"; return 1; }

  failed=0
  for service in redis web worker nginx backup; do
    if exporter_state_has_service "$services_csv" "$service"; then
      migration_root_compose start "$service" || failed=1
    fi
  done
  (( failed == 0 )) || { migration_fail "恢复源服务失败"; return 1; }
  for service in redis web worker nginx backup; do
    if exporter_state_has_service "$services_csv" "$service"; then
      migration_wait_compose_service "$service" 180 || return 1
    fi
  done

  migration_state_write "$state_file" STATUS RESUMED || return 1
  exporter_remove_payloads "$workspace" || return 1
  migration_lock_release "$lock_dir" "$migration_id" || return 1
  printf 'STATUS=RESUMED\n'
}

exporter_prepare_exit_trap() {
  local exit_status=$?
  trap - EXIT
  if [[ "$EXPORTER_PREPARE_COMPLETE" != "1" && "$EXPORTER_PREPARE_OWNS_LOCK" == "1" ]]; then
    migration_log ERROR "源端导出失败，自动恢复原运行服务"
    exporter_resume_internal "$EXPORTER_SOURCE_DIR" "$EXPORTER_MIGRATION_ID" >/dev/null \
      || migration_log ERROR "源端自动恢复未完全成功"
  fi
  exit "$exit_status"
}

exporter_write_manifest() {
  local path="$1"
  local migration_id="$2"
  local redis_dbsize="$3"
  {
    printf 'FORMAT_VERSION=1\n'
    printf 'MIGRATION_ID=%s\n' "$migration_id"
    printf 'SOURCE_MACHINE_ID=%s\n' "$EXPORTER_MACHINE_ID"
    printf 'SOURCE_GIT_COMMIT=%s\n' "$EXPORTER_GIT_COMMIT"
    printf 'RUNNING_SERVICES=%s\n' "$EXPORTER_RUNNING_SERVICES"
    printf 'POSTGRES_MAJOR=%s\n' "$EXPORTER_POSTGRES_MAJOR"
    printf 'REDIS_MAJOR=%s\n' "$EXPORTER_REDIS_MAJOR"
    printf 'WEB_IMAGE_ID=%s\n' "$EXPORTER_WEB_IMAGE_ID"
    printf 'WEB_IMAGE_DIGEST=%s\n' "$EXPORTER_WEB_IMAGE_DIGEST"
    printf 'DATA_SIZE_KB=%s\n' "$EXPORTER_DATA_SIZE_KB"
    printf 'REDIS_DBSIZE=%s\n' "$redis_dbsize"
    printf 'COMPOSE_SHA256=%s\n' "$EXPORTER_COMPOSE_SHA256"
    printf 'ALEMBIC_VERSION=%s\n' "$EXPORTER_ALEMBIC_VERSION"
    printf 'UPLOADS_FILE_COUNT=%s\n' "$EXPORTER_UPLOADS_FILE_COUNT"
    printf 'UPLOADS_TOTAL_BYTES=%s\n' "$EXPORTER_UPLOADS_TOTAL_BYTES"
    printf 'UPLOADS_TREE_SHA256=%s\n' "$EXPORTER_UPLOADS_TREE_SHA256"
    printf 'INSTANCE_FILE_COUNT=%s\n' "$EXPORTER_INSTANCE_FILE_COUNT"
    printf 'INSTANCE_TOTAL_BYTES=%s\n' "$EXPORTER_INSTANCE_TOTAL_BYTES"
    printf 'INSTANCE_TREE_SHA256=%s\n' "$EXPORTER_INSTANCE_TREE_SHA256"
  } > "$path"
  chmod 600 "$path"
}

exporter_write_checksums() {
  local workspace="$1"
  shift
  local filename digest checksum_file
  checksum_file="$workspace/checksums.sha256"
  : > "$checksum_file" || return 1
  chmod 600 "$checksum_file" || return 1
  for filename in "$@"; do
    digest="$(migration_sha256 "$workspace/$filename")" || return 1
    printf '%s  %s\n' "$digest" "$filename" >> "$checksum_file" || return 1
  done
}

exporter_prepare() {
  local source_dir="$1"
  local migration_id="$2"
  local workspace state_file lock_dir postgres_user postgres_db redis_dbsize
  local bundle bundle_temp bundle_checksum bundle_digest filename redis_save running_writers
  local -a payload_files

  workspace="$(exporter_workspace_path "$source_dir" "$migration_id")"
  state_file="$workspace/state"
  lock_dir="$(exporter_lock_path "$source_dir")"
  if [[ -e "$workspace" ]]; then
    migration_fail "检测到未完成的迁移目录: $workspace"
    return 1
  fi

  exporter_validate_deployment "$source_dir" || return 1
  exporter_collect_facts "$source_dir" || return 1
  migration_lock_acquire "$lock_dir" "$migration_id" || return 1
  EXPORTER_PREPARE_OWNS_LOCK=1
  mkdir -p "$(dirname "$workspace")" || return 1
  mkdir "$workspace" || return 1
  chmod 700 "$workspace" || return 1
  migration_state_write "$state_file" \
    STATUS PREPARING \
    MIGRATION_ID "$migration_id" \
    RUNNING_SERVICES "$EXPORTER_RUNNING_SERVICES" || return 1

  migration_root_compose stop backup || return 1
  migration_root_compose stop nginx || return 1
  migration_root_compose stop web worker || return 1
  running_writers="$(migration_root_compose ps --services --filter status=running web worker nginx backup)" || return 1
  [[ -z "$running_writers" ]] \
    || { migration_fail "写服务未完全停止"; return 1; }
  exporter_collect_frozen_file_stats "$source_dir" || return 1

  postgres_user="$(migration_read_env_value "$source_dir/.env.production" POSTGRES_USER)" || return 1
  postgres_db="$(migration_read_env_value "$source_dir/.env.production" POSTGRES_DB)" || return 1
  postgres_user="${postgres_user:-studyuser}"
  postgres_db="${postgres_db:-ti_db}"
  [[ "$postgres_user" =~ ^[A-Za-z0-9_.-]+$ && "$postgres_db" =~ ^[A-Za-z0-9_.-]+$ ]] \
    || { migration_fail "PostgreSQL 用户名或数据库名格式无效"; return 1; }

  migration_root_compose exec -T postgres \
    pg_dump -Fc -Z6 --no-owner --no-acl -U "$postgres_user" -d "$postgres_db" \
    > "$workspace/database.dump" || return 1
  chmod 600 "$workspace/database.dump" || return 1
  migration_root_compose exec -T postgres pg_restore --list \
    < "$workspace/database.dump" >/dev/null || return 1
  migration_database_row_summary "$postgres_user" "$postgres_db" \
    > "$workspace/database-summary.txt" || return 1
  chmod 600 "$workspace/database-summary.txt" || return 1

  redis_dbsize="$(migration_root_compose exec -T redis redis-cli --raw DBSIZE)" || return 1
  [[ "$redis_dbsize" =~ ^[0-9]+$ ]] \
    || { migration_fail "Redis DBSIZE 输出无效"; return 1; }
  redis_save="$(migration_root_compose exec -T redis redis-cli --raw SAVE)" || return 1
  [[ "$redis_save" == "OK" ]] \
    || { migration_fail "Redis SAVE 未返回 OK"; return 1; }
  migration_root_compose stop redis || return 1

  migration_root env COPYFILE_DISABLE=1 tar -C "$source_dir/var" -czf - redis > "$workspace/redis.tar.gz" || return 1
  migration_root env COPYFILE_DISABLE=1 tar -C "$source_dir/var" -czf - uploads > "$workspace/uploads.tar.gz" || return 1
  migration_root env COPYFILE_DISABLE=1 tar -C "$source_dir/var" -czf - instance > "$workspace/instance.tar.gz" || return 1
  migration_root cat "$source_dir/.env.production" > "$workspace/source.env.production" || return 1
  chmod 600 \
    "$workspace/redis.tar.gz" "$workspace/uploads.tar.gz" "$workspace/instance.tar.gz" \
    "$workspace/source.env.production" || return 1

  exporter_write_manifest "$workspace/manifest.txt" "$migration_id" "$redis_dbsize" || return 1
  payload_files=(
    database.dump database-summary.txt redis.tar.gz uploads.tar.gz instance.tar.gz source.env.production manifest.txt
  )
  exporter_write_checksums "$workspace" "${payload_files[@]}" || return 1

  bundle="$workspace/migration-$migration_id.tar.gz"
  bundle_temp="$bundle.tmp"
  COPYFILE_DISABLE=1 tar -C "$workspace" -czf "$bundle_temp" \
    "${payload_files[@]}" checksums.sha256 || return 1
  chmod 600 "$bundle_temp" || return 1
  mv -f "$bundle_temp" "$bundle" || return 1
  bundle_digest="$(migration_sha256 "$bundle")" || return 1
  bundle_checksum="$bundle.sha256"
  filename="$(basename "$bundle")"
  printf '%s  %s\n' "$bundle_digest" "$filename" > "$bundle_checksum" || return 1
  chmod 600 "$bundle_checksum" || return 1

  migration_state_write "$state_file" \
    STATUS FROZEN \
    BUNDLE_PATH "$bundle" \
    CHECKSUM_PATH "$bundle_checksum" || return 1
  printf 'BUNDLE_PATH=%s\n' "$bundle"
  printf 'CHECKSUM_PATH=%s\n' "$bundle_checksum"
}

exporter_finalize() {
  local source_dir="$1"
  local migration_id="$2"
  local workspace state_file lock_dir status finalized_marker
  workspace="$(exporter_workspace_path "$source_dir" "$migration_id")"
  state_file="$workspace/state"
  lock_dir="$(exporter_lock_path "$source_dir")"
  finalized_marker="$(dirname "$workspace")/.finalized-$migration_id"

  if [[ ! -e "$workspace" ]]; then
    [[ -f "$finalized_marker" ]] \
      || { migration_fail "迁移目录与 FINALIZED 状态均缺失"; return 1; }
    if [[ -e "$lock_dir" ]]; then
      migration_lock_release "$lock_dir" "$migration_id" || return 1
    fi
    printf 'STATUS=FINALIZED\n'
    return 0
  fi
  [[ -f "$state_file" ]] || { migration_fail "迁移状态缺失"; return 1; }
  status="$(migration_state_read "$state_file" STATUS)" || return 1
  [[ "$(migration_state_read "$state_file" MIGRATION_ID)" == "$migration_id" ]] \
    || { migration_fail "迁移状态 ID 不匹配"; return 1; }
  [[ "$status" == "FROZEN" ]] \
    || { migration_fail "仅 FROZEN 状态允许 finalize"; return 1; }
  migration_lock_assert_owner "$lock_dir" "$migration_id" || return 1
  migration_state_write "$finalized_marker" STATUS FINALIZED MIGRATION_ID "$migration_id" || return 1
  rm -rf -- "$workspace" || return 1
  migration_lock_release "$lock_dir" "$migration_id" || return 1
  printf 'STATUS=FINALIZED\n'
}

exporter_main() {
  local action="${1:-}"
  local source_dir=""
  local migration_id=""
  [[ -n "$action" ]] || { exporter_usage >&2; return 2; }
  shift || true
  case "$action" in
    preflight|prepare|resume|finalize) ;;
    -h|--help) exporter_usage; return 0 ;;
    *) migration_fail "未知动作: $action"; return 2 ;;
  esac
  while (( $# > 0 )); do
    case "$1" in
      --source-dir)
        (( $# >= 2 )) || { migration_fail "--source-dir 缺少值"; return 2; }
        source_dir="$2"
        shift 2
        ;;
      --migration-id)
        (( $# >= 2 )) || { migration_fail "--migration-id 缺少值"; return 2; }
        migration_id="$2"
        shift 2
        ;;
      -h|--help) exporter_usage; return 0 ;;
      *) migration_fail "未知参数: $1"; return 2 ;;
    esac
  done
  [[ -n "$source_dir" && -n "$migration_id" ]] \
    || { migration_fail "--source-dir 和 --migration-id 为必填参数"; return 2; }
  exporter_validate_source_dir "$source_dir" || return 2
  migration_validate_id "$migration_id" || return 2
  exporter_configure_context "$source_dir" || return 2

  case "$action" in
    preflight) exporter_preflight "$source_dir" ;;
    prepare)
      local prepare_status
      EXPORTER_SOURCE_DIR="$source_dir"
      EXPORTER_MIGRATION_ID="$migration_id"
      trap exporter_prepare_exit_trap EXIT
      trap 'exit 130' HUP INT TERM
      if exporter_prepare "$source_dir" "$migration_id"; then
        EXPORTER_PREPARE_COMPLETE=1
        trap - EXIT HUP INT TERM
        return 0
      else
        prepare_status=$?
        return "$prepare_status"
      fi
      ;;
    resume) exporter_resume_internal "$source_dir" "$migration_id" ;;
    finalize) exporter_finalize "$source_dir" "$migration_id" ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  set -u -o pipefail
  exporter_main "$@"
fi
