#!/bin/bash
# 生产环境数据恢复脚本
# 使用方式: ./scripts/restore.sh backup_20260305_230000.tar.gz

set -e

if [ -z "$1" ]; then
  echo "错误: 请指定备份文件"
  echo "使用方式: ./scripts/restore.sh backup_20260305_230000.tar.gz"
  exit 1
fi

BACKUP_FILE="$1"
BACKUP_DIR="./backups"
TEMP_DIR="${BACKUP_DIR}/temp_restore"

if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
  echo "错误: 备份文件不存在: ${BACKUP_DIR}/${BACKUP_FILE}"
  exit 1
fi

echo "=== 开始恢复 ==="
echo "恢复时间: $(date)"
echo "备份文件: ${BACKUP_FILE}"
echo ""
read -p "警告: 此操作将覆盖当前数据，是否继续？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "恢复已取消"
  exit 0
fi

# 1. 解压备份
echo "正在解压备份..."
mkdir -p "${TEMP_DIR}"
tar -xzf "${BACKUP_DIR}/${BACKUP_FILE}" -C "${TEMP_DIR}"
BACKUP_NAME=$(basename "${BACKUP_FILE}" .tar.gz)
echo "✓ 备份解压完成"

# 2. 停止服务
echo "正在停止服务..."
docker compose -f compose.prod.yml stop web worker
echo "✓ 服务已停止"

# 3. 恢复数据库
echo "正在恢复数据库..."
docker compose -f compose.prod.yml exec -T postgres psql -U studyuser -d ti_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose -f compose.prod.yml exec -T postgres psql -U studyuser -d ti_db < "${TEMP_DIR}/${BACKUP_NAME}/database.sql"
echo "✓ 数据库恢复完成"

# 4. 恢复 Redis
echo "正在恢复 Redis..."
docker compose -f compose.prod.yml stop redis
rm -rf ./var/redis/*
cp -r "${TEMP_DIR}/${BACKUP_NAME}/redis/"* ./var/redis/
docker compose -f compose.prod.yml start redis
echo "✓ Redis 恢复完成"

# 5. 恢复上传文件
echo "正在恢复上传文件..."
rm -rf ./var/uploads/*
cp -r "${TEMP_DIR}/${BACKUP_NAME}/uploads/"* ./var/uploads/
echo "✓ 上传文件恢复完成"

# 6. 清理临时文件
echo "正在清理临时文件..."
rm -rf "${TEMP_DIR}"
echo "✓ 临时文件清理完成"

# 7. 启动服务
echo "正在启动服务..."
docker compose -f compose.prod.yml start web worker
echo "✓ 服务已启动"

echo "=== 恢复完成 ==="
echo "请检查服务状态: docker compose -f compose.prod.yml ps"
