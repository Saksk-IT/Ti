# 阶段 0 验证证据

## 复现环境

- 根提交：`700006dfdfa063deb4387be572911e782bcea0d9`
- macOS arm64
- Python `.venv` 3.11.15
- Node 26.0.0
- pnpm 11.7.0
- Docker Engine 29.4.1 / Compose 5.1.3
- 本机无 JDK/Maven

## 安全的旧测试命令

```bash
baseline_tmp="$(mktemp -d)"

PYTHONDONTWRITEBYTECODE=1 \
DATA_DIR="$baseline_tmp/data" \
RATELIMIT_STORAGE_URI=memory:// \
RATELIMIT_STORAGE_URL=memory:// \
  .venv/bin/python -m pytest -q -p no:cacheprovider

PYTHONPYCACHEPREFIX="$baseline_tmp/pycache" \
  .venv/bin/python -m compileall -q app tests

node --test miniprogram-1/tests/*.test.js
node scripts/check_miniprogram_runtime_deps.js
./miniprogram-1/node_modules/.bin/tsc \
  -p miniprogram-1/tsconfig.json --noEmit --pretty false

docker compose --env-file .env -f compose.dev.yml config --quiet
docker compose --env-file .env.production -f compose.prod.yml config --quiet
```

临时目录用完后删除；不要让旧测试默认访问仓库的 `var/instance/test.db`。

## 结果

- pytest：收集 659 项，`654 passed + 2 failed + 3 skipped`；同一代码的隔离执行已观察到 364–366 warnings 波动，首次基线总耗时 70.33s。
- compileall：通过。
- 小程序 Node：36/36 通过。
- `Ti-Java/miniprogram` 自有副本 Node：36/36 通过；清单共 613 个文件，其中 611 个来源文件逐个与固定 Git blob 的 SHA-256 一致，另 2 个为 Ti-Java 边界说明/忽略文件。
- 小程序运行依赖检查：通过。
- TypeScript：旧树 392 个、受控副本 386 个既有错误，退出码均为 2；差异恰为已排除 `_archived/` 的 6 个 `TS2393`，其余错误多重集合一致。
- 开发 Compose：通过。
- 生产 Compose：因本机生产环境缺少 `BACKUP_CREDENTIAL_SECRET` 未通过；未打开或复制真实配置。

两个既有失败已在 `legacy-test-baseline.json` 形成精确 nodeid 白名单：

1. `tests/test_rate_limit_policy.py::test_production_policy_expands_decorator_and_manual_limits`：完整套件中的关键断言为 `'3/minute;10 per hour' == '300/minute;1000 per hour'`，而该节点在新的临时 `DATA_DIR` 中单独执行通过，归类为 session Flask app testing Profile 的套件上下文耦合。
2. `tests/test_user_bank_document_export.py::test_export_pdf_returns_pdf_download`：断言 `response.status_code == 200` 时实际为 500，关键宿主错误为 `cannot load library 'libpango-1.0-0'`；容器镜像包含相关系统库。

以下命令会真正执行完整 659 项套件，并拒绝计数变化、额外失败或失败 nodeid 漂移；warning 数在同一代码的三次隔离执行中观察到 364–366 的插件级波动，单独限定为该闭区间：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python Ti-Java/tools/verify_legacy_test_baseline.py \
  --legacy-root .
```

小程序 TypeScript 既有失败也由结构化基线区分；下列命令同时执行旧树和受控副本，要求分别保持 392/386 个错误，且差异只能是 6 个归档 `TS2393`：

```bash
PYTHONDONTWRITEBYTECODE=1 \
  python3 Ti-Java/tools/verify_miniprogram_type_baseline.py \
  --legacy-root .
```

## 阶段 0 生成器

```bash
PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python Ti-Java/tools/inventory_legacy.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor

PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python Ti-Java/tools/capture_golden_samples.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor/golden-samples

PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python Ti-Java/tools/measure_legacy_baseline.py \
  --legacy-root . \
  --output Ti-Java/docs/refactor/legacy-performance-sample.json \
  --samples 5
```

预期：592 条 URL 规则、611 个展开的 `path + method`、116 次小程序请求表达式、113 个唯一调用签名、102 条被小程序命中的注册规则、69 张应用表加 `alembic_version`、154 个数据/外部资源，以及 7/7 HTTP 200 且不含动态请求标识的黄金响应；练习样本还必须证明 `POST /api/record_result` 成功写入 `user_answers` 且正确答案不留错题。

阶段 0 统一门禁：

```bash
python3 Ti-Java/tools/validate_phase0.py --legacy-root .
```

隔离性能/SQL 样本全部返回 HTTP 200：公共题库摘要 7 条 SQL、题目计数 1 条、`/hub` 2 条、浅健康 0 条；本次旧模块导入加应用创建为 875.873 ms，RSS 增量约 144.829 MiB。它使用空 SQLite，只作为回归方向证据。

## 正式性能基线待办

正式数据需要从同一脱敏快照创建独立 PostgreSQL/Redis，分别测量：

- 10 次预热后，`n=200`、`c=1/8` 的 HTTP p50/p95/吞吐/错误率；
- 冷/暖页面 TTFB、DOMContentLoaded、load、LCP；
- SQLAlchemy 事件监听器统计每请求 SQL 数、DB 总耗时和最慢语句；
- 从进程启动到深健康 200 的耗时及稳定 RSS。

任何报告都必须记录提交、镜像 digest、数据行数级别、资源限制、并发、样本数与缓存状态。
