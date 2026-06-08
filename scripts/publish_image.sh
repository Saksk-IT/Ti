#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-ghcr.io/saksk-it/ti}"
TAG="${TAG:-$(git rev-parse --short=12 HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"
PLATFORMS="${PLATFORMS:-linux/amd64}"
PUSH_LATEST="${PUSH_LATEST:-1}"
PUSH_DEV="${PUSH_DEV:-0}"
PUSH="${PUSH:-1}"
BUILDER_NAME="${BUILDER_NAME:-ti-builder}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-mirrors.aliyun.com}"
PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"
PIP_RETRIES="${PIP_RETRIES:-10}"
SOURCE_URL="${SOURCE_URL:-https://github.com/Saksk-IT/Ti}"
REVISION="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
CREATED="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

tags=(-t "${IMAGE_NAME}:${TAG}")
if [[ "$PUSH_LATEST" == "1" ]]; then
  tags+=(-t "${IMAGE_NAME}:latest")
fi
if [[ "$PUSH_DEV" == "1" ]]; then
  tags+=(-t "${IMAGE_NAME}:dev")
fi

if [[ -n "${GHCR_USERNAME:-}" || -n "${GHCR_TOKEN:-}" ]]; then
  if [[ -z "${GHCR_USERNAME:-}" || -z "${GHCR_TOKEN:-}" ]]; then
    echo "错误：GHCR_USERNAME 与 GHCR_TOKEN 必须同时设置"
    exit 1
  fi
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
fi

if ! docker buildx inspect "$BUILDER_NAME" >/dev/null 2>&1; then
  docker buildx create --name "$BUILDER_NAME" --use >/dev/null
else
  docker buildx use "$BUILDER_NAME" >/dev/null
fi

output_flag=(--push)
if [[ "$PUSH" != "1" ]]; then
  output_flag=(--load)
fi

echo "构建镜像：${IMAGE_NAME}:${TAG}"
echo "平台：${PLATFORMS}"

docker buildx build \
  --platform "$PLATFORMS" \
  --build-arg PIP_INDEX_URL="$PIP_INDEX_URL" \
  --build-arg PIP_TRUSTED_HOST="$PIP_TRUSTED_HOST" \
  --build-arg PIP_DEFAULT_TIMEOUT="$PIP_DEFAULT_TIMEOUT" \
  --build-arg PIP_RETRIES="$PIP_RETRIES" \
  --label "org.opencontainers.image.source=${SOURCE_URL}" \
  --label "org.opencontainers.image.revision=${REVISION}" \
  --label "org.opencontainers.image.created=${CREATED}" \
  "${tags[@]}" \
  "${output_flag[@]}" \
  -f "$ROOT_DIR/docker/Dockerfile" \
  "$ROOT_DIR"

cat <<EOF

镜像发布完成：
  ${IMAGE_NAME}:${TAG}
  ${IMAGE_NAME}:latest

服务器默认部署会拉取：
  ${IMAGE_NAME}:latest
EOF
