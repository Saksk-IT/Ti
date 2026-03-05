#!/bin/bash
# 生产环境完整数据恢复脚本
# 使用方式: ./scripts/restore.sh backup_20260306_230000.tar.gz

set -e

if [ -z "$1" ]; then
  echo "错误: 请指定备份文件"
  echo "使用方式: ./scripts/restore.sh backup_20260306_230000.tar.gz"
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

# 显示备份内容
echo "备份内容:"
tar -tzf "${BACKUP_DIR}/${BACKUP_FILE}" | head -20
echo "..."
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

# 显示备份清单
if [ -f "${TEMP_DIR}/${BACKUP_NAME}/MANIFEST.txt" ]; then
  echo ""
  echo "备份清单:"
  cat "${TEMP_DIR}/${BACKUP_NAME}/MANIFEST.txt"
  echo ""
fi

# 2. 停止服务
echo "正在停止服务..."
docker compose -f compose.prod.yml stop web worker
echo "✓ 服务已停止"

# 3. 恢复数据库
if [ -f "${TEMP_DIR}/${BACKUP_NAME}/database.sql" ]; then
  echo "正在恢复数据库..."
  docker compose -f compose.prod.yml exec -T postgres psql -U studyuser -d ti_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
  docker compose -f compose.prod.yml exec -T postgres psql -U studyuser -d ti_db < "${TEMP_DIR}/${BACKUP_NAME}/database.sql"
  echo "✓ 数据库恢复完成"
else
  echo "⚠ 数据库备份文件不存在，跳过"
fi

# 4. 恢复 Redis
if [ -d "${TEMP_DIR}/${BACKUP_NAME}/redis" ]; then
  echo "正在恢复 Redis..."
  docker compose -f compose.prod.yml stop redis
  rm -rf ./var/redis/*
  cp -r "${TEMP_DIR}/${BACKUP_NAME}/redis/"* ./var/redis/
  docker compose -f compose.prod.yml start redis
  echo "✓ Redis 恢复完成"
else
  echo "⚠ Redis 备份不存在，跳过"
fi

# 5. 恢复上传文件
if [ -d "${TEMP_DIR}/${BACKUP_NAME}/uploads" ]; then
  echo "正在恢复上传文件..."
  rm -rf ./var/uploads/*
  cp -r "${TEMP_DIR}/${BACKUP_NAME}/uploads/"* ./var/uploads/
  echo "✓ 上传文件恢复完成"
else
  echo "⚠ 上传文件备份不存在，跳过"
fi

# 6. 恢复实例数据
if [ -d "${TEMP_DIR}/${BACKUP_NAME}/instance" ]; then
  echo "正在恢复实例数据..."
  rm -rf ./var/instance/*
  cp -r "${TEMP_DIR}/${BACKUP_NAME}/instance/"* ./var/instance/
  echo "✓ 实例数据恢复完成"
else
  echo "⚠ 实例数据备份不存在，跳过"
fi

# 7. 恢复日志（可选）
if [ -d "${TEMP_DIR}/${BACKUP_NAME}/logs" ]; then
  read -p "是否恢复日志文件？(yes/no): " restore_logs
  if [ "$restore_logs" = "yes" ]; then
    echo "正在恢复日志文件..."
    mkdir -p ./var/logs
    cp -r "${TEMP_DIR}/${BACKUP_NAME}/logs/"* ./var/logs/
    echo "✓ 日志文件恢复完成"
  else
    echo "⊘ 跳过日志恢复"
  fi
else
  echo "⚠ 日志备份不存在，跳过"
fi

# 8. 清理临时文件
echo "正在清理临时文件..."
rm -rf "${TEMP_DIR}"
echo "✓ 临时文件清理完成"

# 9. 启动服务
echo "正在启动服务..."
docker compose -f compose.prod.yml start web worker
echo "✓ 服务已启动"

echo "=== 恢复完成 ==="
echo "请检查服务状态: docker compose -f compose.prod.yml ps"
echo "请检查应用日志: docker compose -f compose.prod.yml logs -f web"
