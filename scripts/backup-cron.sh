#!/bin/sh
# 完整数据备份脚本（用于 Docker 容器内）
# 环境变量：
# - POSTGRES_USER: 数据库用户
# - POSTGRES_PASSWORD: 数据库密码
# - POSTGRES_DB: 数据库名称
# - BACKUP_INTERVAL: 备份间隔（秒），默认 86400（24小时）
# - BACKUP_RETENTION_DAYS: 保留天数，默认 7 天

set -e

BACKUP_DIR="/backups"
DATA_DIR="/data"
BACKUP_INTERVAL=${BACKUP_INTERVAL:-86400}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
POSTGRES_HOST="postgres"

echo "=== 完整数据备份服务启动 ==="
echo "备份间隔: ${BACKUP_INTERVAL} 秒"
echo "保留天数: ${BACKUP_RETENTION_DAYS} 天"
echo "备份目录: ${BACKUP_DIR}"
echo "数据目录: ${DATA_DIR}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 备份函数
do_backup() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_NAME="backup_${TIMESTAMP}"
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始完整备份..."

    # 等待数据库就绪
    until PGPASSWORD="${POSTGRES_PASSWORD}" pg_isready -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null 2>&1; do
        echo "等待数据库就绪..."
        sleep 5
    done

    # 创建临时备份目录
    mkdir -p "${BACKUP_PATH}"

    # 1. 备份数据库
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份数据库..."
    if PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > "${BACKUP_PATH}/database.sql"; then
        echo "  ✓ 数据库备份完成"
    else
        echo "  ✗ 数据库备份失败！"
        rm -rf "${BACKUP_PATH}"
        return 1
    fi

    # 2. 备份上传文件
    if [ -d "${DATA_DIR}/uploads" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份上传文件..."
        cp -r "${DATA_DIR}/uploads" "${BACKUP_PATH}/uploads"
        echo "  ✓ 上传文件备份完成"
    else
        echo "  ⚠ 上传目录不存在，跳过"
    fi

    # 3. 备份实例数据
    if [ -d "${DATA_DIR}/instance" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份实例数据..."
        cp -r "${DATA_DIR}/instance" "${BACKUP_PATH}/instance"
        echo "  ✓ 实例数据备份完成"
    else
        echo "  ⚠ 实例目录不存在，跳过"
    fi

    # 4. 备份日志（最近7天）
    if [ -d "${DATA_DIR}/logs" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份日志文件..."
        mkdir -p "${BACKUP_PATH}/logs"
        find "${DATA_DIR}/logs" -name "*.log" -mtime -7 -exec cp {} "${BACKUP_PATH}/logs/" \; 2>/dev/null || true
        echo "  ✓ 日志文件备份完成"
    else
        echo "  ⚠ 日志目录不存在，跳过"
    fi

    # 5. 创建备份清单
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 创建备份清单..."
    cat > "${BACKUP_PATH}/MANIFEST.txt" <<EOF
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
备份内容:
- 数据库: ${POSTGRES_DB}
- 上传文件: $(du -sh ${BACKUP_PATH}/uploads 2>/dev/null | cut -f1 || echo "无")
- 实例数据: $(du -sh ${BACKUP_PATH}/instance 2>/dev/null | cut -f1 || echo "无")
- 日志文件: $(du -sh ${BACKUP_PATH}/logs 2>/dev/null | cut -f1 || echo "无")

文件列表:
$(find ${BACKUP_PATH} -type f | sed "s|${BACKUP_PATH}/||" | sort)
EOF

    # 6. 压缩备份
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 压缩备份..."
    cd "${BACKUP_DIR}"
    tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    rm -rf "${BACKUP_NAME}"

    BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份完成: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"

    # 7. 清理旧备份
    find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +${BACKUP_RETENTION_DAYS} -delete
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 已清理 ${BACKUP_RETENTION_DAYS} 天前的旧备份"

    # 8. 显示当前备份列表
    echo "当前备份文件:"
    ls -lh "${BACKUP_DIR}"/backup_*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  无备份文件"
}

# 首次启动立即备份
do_backup

# 定时备份循环
while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 等待 ${BACKUP_INTERVAL} 秒后执行下次备份..."
    sleep "${BACKUP_INTERVAL}"
    do_backup
done
