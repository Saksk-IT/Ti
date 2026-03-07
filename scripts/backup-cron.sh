#!/bin/sh
# 完整数据备份脚本（用于 Docker 容器内）
# 环境变量：
# - POSTGRES_USER: 数据库用户
# - POSTGRES_PASSWORD: 数据库密码
# - POSTGRES_DB: 数据库名称
# - BACKUP_TZ: 备份时区，默认 Asia/Shanghai
# - BACKUP_ANCHOR_TIME: 每日首个备份时间（HH:MM），默认 04:00
# - BACKUP_INTERVAL: 备份间隔（秒），默认 43200（12小时）
# - BACKUP_CHECK_INTERVAL: 调度轮询间隔（秒），默认 60
# - BACKUP_RETENTION_DAYS: 保留天数，默认 7 天
# - BACKUP_INCLUDE_REDIS: 是否备份 Redis 持久化目录（true/false）
# - BACKUP_INCLUDE_CONFIG: 是否备份部署配置文件（true/false）
# - BACKUP_ENV_FILE_PATH: 需要打包的环境变量文件路径（可选）
# - BACKUP_COMPOSE_FILE_PATH: 需要打包的 compose 文件路径（可选）

set -e

BACKUP_DIR="/backups"
DATA_DIR="/data"
POSTGRES_HOST="postgres"
BACKUP_TZ=${BACKUP_TZ:-Asia/Shanghai}
BACKUP_ANCHOR_TIME=${BACKUP_ANCHOR_TIME:-04:00}
BACKUP_INTERVAL=${BACKUP_INTERVAL:-43200}
BACKUP_CHECK_INTERVAL=${BACKUP_CHECK_INTERVAL:-60}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
BACKUP_INCLUDE_REDIS=${BACKUP_INCLUDE_REDIS:-false}
BACKUP_INCLUDE_CONFIG=${BACKUP_INCLUDE_CONFIG:-false}
BACKUP_ENV_FILE_PATH=${BACKUP_ENV_FILE_PATH:-}
BACKUP_COMPOSE_FILE_PATH=${BACKUP_COMPOSE_FILE_PATH:-}
LAST_SLOT_FILE="${BACKUP_DIR}/.last_backup_slot"

export TZ="${BACKUP_TZ}"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*"
}

validate_number() {
    case "$1" in
        ''|*[!0-9]*)
            return 1
            ;;
        *)
            return 0
            ;;
    esac
}

is_enabled() {
    case "$1" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

parse_anchor_time() {
    anchor_hour=${BACKUP_ANCHOR_TIME%%:*}
    anchor_minute=${BACKUP_ANCHOR_TIME#*:}

    if [ "${anchor_hour}" = "${BACKUP_ANCHOR_TIME}" ] || [ -z "${anchor_minute}" ]; then
        echo "错误: BACKUP_ANCHOR_TIME 必须是 HH:MM 格式，当前值: ${BACKUP_ANCHOR_TIME}" >&2
        exit 1
    fi

    if ! validate_number "${anchor_hour}" || ! validate_number "${anchor_minute}"; then
        echo "错误: BACKUP_ANCHOR_TIME 只能包含数字，当前值: ${BACKUP_ANCHOR_TIME}" >&2
        exit 1
    fi

    anchor_hour_num=$((10#${anchor_hour}))
    anchor_minute_num=$((10#${anchor_minute}))

    if [ "${anchor_hour_num}" -gt 23 ] || [ "${anchor_minute_num}" -gt 59 ]; then
        echo "错误: BACKUP_ANCHOR_TIME 超出有效范围，当前值: ${BACKUP_ANCHOR_TIME}" >&2
        exit 1
    fi

    ANCHOR_SECONDS=$((anchor_hour_num * 3600 + anchor_minute_num * 60))
}

validate_scheduler_config() {
    if ! validate_number "${BACKUP_INTERVAL}" || [ "${BACKUP_INTERVAL}" -le 0 ]; then
        echo "错误: BACKUP_INTERVAL 必须是正整数秒，当前值: ${BACKUP_INTERVAL}" >&2
        exit 1
    fi

    if ! validate_number "${BACKUP_CHECK_INTERVAL}" || [ "${BACKUP_CHECK_INTERVAL}" -le 0 ]; then
        echo "错误: BACKUP_CHECK_INTERVAL 必须是正整数秒，当前值: ${BACKUP_CHECK_INTERVAL}" >&2
        exit 1
    fi

    if ! validate_number "${BACKUP_RETENTION_DAYS}" || [ "${BACKUP_RETENTION_DAYS}" -lt 0 ]; then
        echo "错误: BACKUP_RETENTION_DAYS 必须是非负整数，当前值: ${BACKUP_RETENTION_DAYS}" >&2
        exit 1
    fi

    if [ $((86400 % BACKUP_INTERVAL)) -ne 0 ]; then
        echo "错误: BACKUP_INTERVAL 必须能整除 86400，当前值: ${BACKUP_INTERVAL}" >&2
        exit 1
    fi
}

get_last_slot_epoch() {
    if [ -f "${LAST_SLOT_FILE}" ]; then
        last_slot=$(tr -d '[:space:]' < "${LAST_SLOT_FILE}")
        if validate_number "${last_slot}"; then
            printf '%s\n' "${last_slot}"
            return 0
        fi
    fi

    printf '0\n'
}

get_due_slot_epoch() {
    now_epoch=$(date +%s)
    current_hour=$((10#$(date +%H)))
    current_minute=$((10#$(date +%M)))
    current_second=$((10#$(date +%S)))
    current_seconds=$((current_hour * 3600 + current_minute * 60 + current_second))
    offset_since_anchor=$(((current_seconds - ANCHOR_SECONDS + 86400) % 86400))
    delta_since_latest_slot=$((offset_since_anchor % BACKUP_INTERVAL))
    printf '%s\n' "$((now_epoch - delta_since_latest_slot))"
}

copy_config_file() {
    source_path="$1"
    target_dir="$2"

    if [ -z "${source_path}" ] || [ ! -f "${source_path}" ]; then
        return 1
    fi

    cp "${source_path}" "${target_dir}/$(basename "${source_path}")"
    return 0
}

# 备份函数
do_backup() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_NAME="backup_${TIMESTAMP}"
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
    REDIS_SIZE="未启用"
    CONFIG_SUMMARY="未启用"

    log "开始完整备份..."

    # 等待数据库就绪
    until PGPASSWORD="${POSTGRES_PASSWORD}" pg_isready -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null 2>&1; do
        log "等待数据库就绪..."
        sleep 5
    done

    # 创建临时备份目录
    mkdir -p "${BACKUP_PATH}"

    # 1. 备份数据库
    log "备份数据库..."
    if PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > "${BACKUP_PATH}/database.sql"; then
        echo "  ✓ 数据库备份完成"
    else
        echo "  ✗ 数据库备份失败！"
        rm -rf "${BACKUP_PATH}"
        return 1
    fi

    # 2. 备份 Redis 持久化目录（可选）
    if is_enabled "${BACKUP_INCLUDE_REDIS}"; then
        if [ -d "${DATA_DIR}/redis" ]; then
            log "备份 Redis 持久化数据..."
            cp -r "${DATA_DIR}/redis" "${BACKUP_PATH}/redis"
            REDIS_SIZE=$(du -sh "${BACKUP_PATH}/redis" 2>/dev/null | cut -f1 || echo "无")
            echo "  ✓ Redis 持久化数据备份完成"
        else
            REDIS_SIZE="无"
            echo "  ⚠ Redis 数据目录不存在，跳过"
        fi
    fi

    # 3. 备份上传文件
    if [ -d "${DATA_DIR}/uploads" ]; then
        log "备份上传文件..."
        cp -r "${DATA_DIR}/uploads" "${BACKUP_PATH}/uploads"
        echo "  ✓ 上传文件备份完成"
    else
        echo "  ⚠ 上传目录不存在，跳过"
    fi

    # 4. 备份实例数据
    if [ -d "${DATA_DIR}/instance" ]; then
        log "备份实例数据..."
        cp -r "${DATA_DIR}/instance" "${BACKUP_PATH}/instance"
        echo "  ✓ 实例数据备份完成"
    else
        echo "  ⚠ 实例目录不存在，跳过"
    fi

    # 5. 备份日志（最近7天）
    if [ -d "${DATA_DIR}/logs" ]; then
        log "备份日志文件..."
        mkdir -p "${BACKUP_PATH}/logs"
        find "${DATA_DIR}/logs" -name "*.log" -mtime -7 -exec cp {} "${BACKUP_PATH}/logs/" \; 2>/dev/null || true
        echo "  ✓ 日志文件备份完成"
    else
        echo "  ⚠ 日志目录不存在，跳过"
    fi

    # 6. 备份部署配置（可选）
    if is_enabled "${BACKUP_INCLUDE_CONFIG}"; then
        log "备份部署配置..."
        mkdir -p "${BACKUP_PATH}/config"
        CONFIG_SUMMARY=""

        if copy_config_file "${BACKUP_ENV_FILE_PATH}" "${BACKUP_PATH}/config"; then
            CONFIG_SUMMARY="$(basename "${BACKUP_ENV_FILE_PATH}")"
        else
            echo "  ⚠ 环境配置文件不存在，跳过"
        fi

        if copy_config_file "${BACKUP_COMPOSE_FILE_PATH}" "${BACKUP_PATH}/config"; then
            if [ -n "${CONFIG_SUMMARY}" ]; then
                CONFIG_SUMMARY="${CONFIG_SUMMARY}, $(basename "${BACKUP_COMPOSE_FILE_PATH}")"
            else
                CONFIG_SUMMARY="$(basename "${BACKUP_COMPOSE_FILE_PATH}")"
            fi
        else
            echo "  ⚠ Compose 配置文件不存在，跳过"
        fi

        if [ -n "${CONFIG_SUMMARY}" ]; then
            echo "  ✓ 部署配置备份完成"
        else
            CONFIG_SUMMARY="无"
            rmdir "${BACKUP_PATH}/config" 2>/dev/null || true
        fi
    fi

    # 7. 创建备份清单
    log "创建备份清单..."
    cat > "${BACKUP_PATH}/MANIFEST.txt" <<MANIFEST
备份时间: $(date '+%Y-%m-%d %H:%M:%S %Z')
备份时区: ${BACKUP_TZ}
备份内容:
- 数据库: ${POSTGRES_DB}
- Redis 数据: ${REDIS_SIZE}
- 上传文件: $(du -sh ${BACKUP_PATH}/uploads 2>/dev/null | cut -f1 || echo "无")
- 实例数据: $(du -sh ${BACKUP_PATH}/instance 2>/dev/null | cut -f1 || echo "无")
- 日志文件: $(du -sh ${BACKUP_PATH}/logs 2>/dev/null | cut -f1 || echo "无")
- 配置文件: ${CONFIG_SUMMARY}

文件列表:
$(find ${BACKUP_PATH} -type f | sed "s|${BACKUP_PATH}/||" | sort)
MANIFEST

    # 8. 压缩备份
    log "压缩备份..."
    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    rm -rf "${BACKUP_NAME}"

    BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
    log "备份完成: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"

    # 9. 清理旧备份
    find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +${BACKUP_RETENTION_DAYS} -delete
    log "已清理 ${BACKUP_RETENTION_DAYS} 天前的旧备份"

    # 10. 显示当前备份列表
    echo "当前备份文件:"
    ls -lh "${BACKUP_DIR}"/backup_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  无备份文件"
}

maybe_run_due_backup() {
    due_slot_epoch=$(get_due_slot_epoch)
    last_slot_epoch=$(get_last_slot_epoch)

    if [ "${due_slot_epoch}" -le "${last_slot_epoch}" ]; then
        return 0
    fi

    log "检测到到期备份窗口（slot_epoch=${due_slot_epoch}），开始执行备份"
    do_backup
    printf '%s\n' "${due_slot_epoch}" > "${LAST_SLOT_FILE}"
    log "已记录最近一次完成的备份窗口（slot_epoch=${due_slot_epoch}）"
}

mkdir -p "${BACKUP_DIR}"
parse_anchor_time
validate_scheduler_config

echo "=== 完整数据备份服务启动 ==="
echo "备份时区: ${BACKUP_TZ}"
echo "备份锚点时间: ${BACKUP_ANCHOR_TIME}"
echo "备份间隔: ${BACKUP_INTERVAL} 秒"
echo "调度轮询间隔: ${BACKUP_CHECK_INTERVAL} 秒"
echo "保留天数: ${BACKUP_RETENTION_DAYS} 天"
echo "包含 Redis 持久化目录: ${BACKUP_INCLUDE_REDIS}"
echo "包含部署配置文件: ${BACKUP_INCLUDE_CONFIG}"
echo "备份目录: ${BACKUP_DIR}"
echo "数据目录: ${DATA_DIR}"

maybe_run_due_backup

while true; do
    sleep "${BACKUP_CHECK_INTERVAL}"
    maybe_run_due_backup
done
