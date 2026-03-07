#!/bin/bash
# 生产环境完整数据备份脚本
# 使用方式: ./scripts/backup.sh

set -e

BACKUP_TZ=${BACKUP_TZ:-Asia/Shanghai}
export TZ="${BACKUP_TZ}"

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_${TIMESTAMP}"

echo "=== 开始完整备份 ==="
echo "备份时区: ${BACKUP_TZ}"
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
if [ -d "./var/uploads" ]; then
    cp -r ./var/uploads "${BACKUP_DIR}/${BACKUP_NAME}/uploads"
    echo "✓ 上传文件备份完成"
else
    echo "⚠ 上传目录不存在，跳过"
fi

# 4. 备份实例数据
echo "正在备份实例数据..."
if [ -d "./var/instance" ]; then
    cp -r ./var/instance "${BACKUP_DIR}/${BACKUP_NAME}/instance"
    echo "✓ 实例数据备份完成"
else
    echo "⚠ 实例目录不存在，跳过"
fi

# 5. 备份日志（最近7天）
echo "正在备份日志文件..."
if [ -d "./var/logs" ]; then
    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/logs"
    find ./var/logs -name "*.log" -mtime -7 -exec cp {} "${BACKUP_DIR}/${BACKUP_NAME}/logs/" \; 2>/dev/null || true
    echo "✓ 日志文件备份完成"
else
    echo "⚠ 日志目录不存在，跳过"
fi

# 6. 备份配置文件
echo "正在备份配置文件..."
cp .env.production "${BACKUP_DIR}/${BACKUP_NAME}/.env.production" 2>/dev/null || echo "警告: .env.production 不存在"
cp compose.prod.yml "${BACKUP_DIR}/${BACKUP_NAME}/compose.prod.yml"
echo "✓ 配置文件备份完成"

# 7. 创建备份清单
echo "正在创建备份清单..."
cat > "${BACKUP_DIR}/${BACKUP_NAME}/MANIFEST.txt" <<EOF
备份时间: $(date '+%Y-%m-%d %H:%M:%S %Z')
备份时区: ${BACKUP_TZ}
备份内容:
- 数据库: ti_db
- Redis 数据: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}/redis 2>/dev/null | cut -f1 || echo "无")
- 上传文件: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}/uploads 2>/dev/null | cut -f1 || echo "无")
- 实例数据: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}/instance 2>/dev/null | cut -f1 || echo "无")
- 日志文件: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}/logs 2>/dev/null | cut -f1 || echo "无")
- 配置文件: compose.prod.yml, .env.production

文件列表:
$(find ${BACKUP_DIR}/${BACKUP_NAME} -type f | sed "s|${BACKUP_DIR}/${BACKUP_NAME}/||" | sort)
EOF
echo "✓ 备份清单创建完成"

# 8. 压缩备份
echo "正在压缩备份..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"
cd ..
echo "✓ 备份压缩完成"

# 9. 清理旧备份（保留最近 7 天）
echo "正在清理旧备份..."
find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +7 -delete
echo "✓ 旧备份清理完成"

echo "=== 备份完成 ==="
echo "备份文件: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "备份大小: $(du -h ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz | cut -f1)"
echo ""
echo "备份内容清单:"
tar -tzf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | head -20
echo "..."
