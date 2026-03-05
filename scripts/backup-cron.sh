#!/bin/sh
# 数据库自动备份脚本（用于 Docker 容器内）
# 环境变量：
# - POSTGRES_USER: 数据库用户
# - POSTGRES_PASSWORD: 数据库密码
# - POSTGRES_DB: 数据库名称
# - BACKUP_INTERVAL: 备份间隔（秒），默认 86400（24小时）
# - BACKUP_RETENTION_DAYS: 保留天数，默认 7 天

set -e

BACKUP_DIR="/backups"
BACKUP_INTERVAL=${BACKUP_INTERVAL:-86400}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}
POSTGRES_HOST="postgres"

echo "=== 数据库自动备份服务启动 ==="
echo "备份间隔: ${BACKUP_INTERVAL} 秒"
echo "保留天数: ${BACKUP_RETENTION_DAYS} 天"
echo "备份目录: ${BACKUP_DIR}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 备份函数
do_backup() {
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始备份..."

    # 等待数据库就绪
    until PGPASSWORD="${POSTGRES_PASSWORD}" pg_isready -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > /dev/null 2>&1; do
        echo "等待数据库就绪..."
        sleep 5
    done

    # 执行备份
    if PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" > "${BACKUP_FILE}"; then
        # 压缩备份
        gzip "${BACKUP_FILE}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份完成: ${BACKUP_FILE}.gz"

        # 清理旧备份
        find "${BACKUP_DIR}" -name "db_backup_*.sql.gz" -mtime +${BACKUP_RETENTION_DAYS} -delete
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 已清理 ${BACKUP_RETENTION_DAYS} 天前的旧备份"

        # 显示当前备份列表
        echo "当前备份文件:"
        ls -lh "${BACKUP_DIR}"/db_backup_*.sql.gz 2>/dev/null || echo "  无备份文件"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 备份失败！"
        rm -f "${BACKUP_FILE}"
    fi
}

# 首次启动立即备份
do_backup

# 定时备份循环
while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 等待 ${BACKUP_INTERVAL} 秒后执行下次备份..."
    sleep "${BACKUP_INTERVAL}"
    do_backup
done
