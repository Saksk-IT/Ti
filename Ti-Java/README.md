# Ti-Java

Ti-Java 是 Ti 的独立 Java 模块化单体重构项目。目标运行形态是 Java 25、Spring Boot 4.1、Spring Modulith 2.1、Vue 3 + TypeScript，以及项目自有的微信原生 TypeScript 小程序。

阶段 0 事实基线与阶段 1 架构/契约已经固化，当前准备进入阶段 2 Java 基础骨架。本目录已经建立独立边界、旧小程序受控副本、正式 ADR、模块/不变量合同和覆盖 592 条旧规则的 OpenAPI 3.1.2 初稿；Java Server 与 Vue Web 尚未创建，当前状态不代表已经具备替代旧 Flask 项目的条件。

## 目录

- `contracts/`：确定性生成的 OpenAPI 3.1.2 初稿与人工证据 override。
- `docs/refactor/adr/`：阶段 1 已接受的架构决策。
- `docs/refactor/phase1/`：API 约定、模块合同、关键不变量和对比/切换协议。
- `docs/refactor/`：事实盘点、迁移矩阵、数据所有权、运行手册与连续进度。
- `tools/`：仅用于迁移期读取旧仓库的盘点和黄金样本工具。
- `miniprogram/`：从旧项目受版本控制源码复制的新项目小程序基线。
- `server/`：阶段 2 创建的 Java 模块化单体（尚未创建）。
- `web/`：阶段 6 创建的 Vue Web（尚未创建）。
- `infra/`：阶段 3 起创建的本地对比与部署设施（尚未创建）。

## 阶段 0/1 可重复命令

从仓库根目录运行：

```bash
.venv/bin/python Ti-Java/tools/inventory_legacy.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor

.venv/bin/python Ti-Java/tools/capture_golden_samples.py \
  --legacy-root . \
  --output-dir Ti-Java/docs/refactor/golden-samples

.venv/bin/python Ti-Java/tools/measure_legacy_baseline.py \
  --legacy-root . \
  --output Ti-Java/docs/refactor/legacy-performance-sample.json \
  --samples 5

.venv/bin/python Ti-Java/tools/inventory_surfaces.py \
  --legacy-root . \
  --miniprogram-root Ti-Java/miniprogram \
  --output Ti-Java/docs/refactor/09-surface-inventory.json

node --test Ti-Java/miniprogram/tests/*.test.js
python3 Ti-Java/tools/validate_phase0.py --legacy-root .

python3 Ti-Java/tools/generate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_openapi.py
python3 Ti-Java/tools/validate_phase1_boundaries.py
python3 Ti-Java/tools/validate_phase1.py
```

阶段 0 工具只读取旧代码，并在临时测试数据库中构造脱敏样本；阶段 1 生成器只读取已经冻结在 `Ti-Java/` 内的矩阵、黄金样本和人工 override。它们均不是新项目生产运行依赖。

## 进度入口

继续实施前先阅读 [`docs/refactor/05-progress.md`](docs/refactor/05-progress.md)。
