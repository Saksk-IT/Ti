#!/usr/bin/env bash
# 启动使用生产数据副本的本机 Flask 开发环境，不导入数据或重置账号。
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$project_dir/.env.local-restored"

if [[ ! -f "$env_file" ]]; then
  printf '缺少 %s；请先完成服务器数据的本机恢复。\n' "$env_file" >&2
  exit 1
fi

compose=(docker compose --env-file "$env_file"
  -f "$project_dir/compose.dev.yml"
  -f "$project_dir/compose.local.yml"
  -f "$project_dir/compose.restored.yml")

"${compose[@]}" config --quiet
"${compose[@]}" build web
"${compose[@]}" up -d --wait --wait-timeout 120 postgres redis
"${compose[@]}" run --rm --no-deps web flask db upgrade
"${compose[@]}" up -d --wait --wait-timeout 180 web worker
"${compose[@]}" ps
