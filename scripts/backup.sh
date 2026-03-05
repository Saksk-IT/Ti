#!/bin/bash
# 生产环境数据备份脚本
# 使用方式: ./scripts/backup.sh

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"

echo "=== 开始备份 ==="
echo "备份时间: $(date)"
echo "备份目录: ${BACKUP_DIR}/${BACKUP_NAME}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# 1. 备份数据库
echo "正在备份数据库..."
docker compose -f compose.prod.yml exec -T postgres pg_dump -U studyuser ti_db > "${BACKUP_DIR}/${BACKUP_NAME}/database.sql"
echo "✓ 数据库备份完成"

# 2. 备份 Redis 数据
echo "正在备份 Redis..."
docker compose -f compose.prod.yml exec -T redis redis-cli SAVE
cp -r ./var/redis "${BACKUP_DIR}/${BACKUP_NAME}/redis"
echo "✓ Redis 备份完成"

# 3. 备份上传文件
echo "正在备份上传文件..."
cp -r ./var/uploads "${BACKUP_DIR}/${BACKUP_NAME}/uploads"
echo "✓ 上传文件备份完成"

# 4. 备份配置文件
echo "正在备份配置文件..."
cp .env.production "${BACKUP_DIR}/${BACKUP_NAME}/.env.production" 2>/dev/null || echo "警告: .env.production 不存在"
cp compose.prod.yml "${BACKUP_DIR}/${BACKUP_NAME}/compose.prod.yml"
echo "✓ 配置文件备份完成"

# 5. 压缩备份
echo "正在压缩备份..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"
cd ..
echo "✓ 备份压缩完成"

# 6. 清理旧备份（保留最近 7 天）
echo "正在清理旧备份..."
find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +7 -delete
echo "✓ 旧备份清理完成"

echo "=== 备份完成 ==="
echo "备份文件: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "备份大小: $(du -h ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz | cut -f1)"
