#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-compose.dev.yml}"
SERVICE_NAME="${SERVICE_NAME:-web}"
TARGET_PATH="/app/scripts/reset_dev_data.py"
SOURCE_PATH="$ROOT_DIR/scripts/reset_dev_data.py"

cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "错误: 未安装 docker"
  exit 1
fi

if [ ! -f "$SOURCE_PATH" ]; then
  echo "错误: 未找到脚本文件: $SOURCE_PATH"
  exit 1
fi

CONTAINER_ID="$(docker compose -f "$COMPOSE_FILE" ps -q "$SERVICE_NAME" | tr -d '\r')"
if [ -z "$CONTAINER_ID" ]; then
  echo "错误: 未找到 $SERVICE_NAME 容器，请先启动开发环境: docker compose -f $COMPOSE_FILE up -d"
  exit 1
fi

echo "==> 同步严格版初始化脚本到容器"
docker exec "$CONTAINER_ID" mkdir -p /app/scripts
docker cp "$SOURCE_PATH" "$CONTAINER_ID:$TARGET_PATH"

echo "==> 在容器内执行开发数据初始化"
docker exec "$CONTAINER_ID" python "$TARGET_PATH"

echo "==> 完成"
echo "可重复执行命令: ./scripts/dev_reset_data.sh"
