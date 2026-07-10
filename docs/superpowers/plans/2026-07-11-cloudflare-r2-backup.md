# Cloudflare R2 数据备份 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Ti 后台增加安全的 Cloudflare R2 完整业务数据备份管理能力和教程弹窗。

**Architecture:** Web 端保存加密配置并创建 `BackupJob`；独立 Python Sidecar 原子认领任务、生成 PostgreSQL + uploads + instance 归档并上传 R2。后台提供状态、下载、删除和 CLI 恢复教程，不在 Web 内执行高权限恢复。

**Tech Stack:** Flask 3、SQLAlchemy/Alembic、PostgreSQL、boto3、croniter、Jinja2、pytest、Docker Compose。

---

### Task 1: 设计文档、数据模型与配置服务

**Files:**
- Create: `app/models/backup.py`
- Create: `migrations/versions/e1f2a3b4c5d6_add_backup_jobs.py`
- Create: `app/modules/admin/services/backup_config_service.py`
- Modify: `app/models/__init__.py`
- Modify: `app/modules/admin/services/system_config_service.py`
- Test: `tests/test_backup_config_service.py`

- [ ] 先写配置校验、加密/脱敏、模型序列化和敏感配置过滤测试。
- [ ] 运行测试并确认因功能缺失而失败。
- [ ] 实现最小模型、迁移和配置服务。
- [ ] 运行测试至通过并重构。

### Task 2: R2 存储、归档和任务服务

**Files:**
- Create: `app/modules/admin/services/backup_storage_service.py`
- Create: `app/modules/admin/services/backup_archive_service.py`
- Create: `app/modules/admin/services/backup_job_service.py`
- Test: `tests/test_backup_services.py`

- [ ] 先写 Endpoint/对象边界、测试连接、下载、删除、归档内容和任务状态测试。
- [ ] 运行测试并确认 RED。
- [ ] 使用依赖注入实现 boto3 操作、受控 `pg_dump`、安全归档和任务服务。
- [ ] 运行测试至 GREEN，检查临时文件和错误路径。

### Task 3: 管理 API 与安全边界

**Files:**
- Create: `app/modules/admin/routes/api_components/backup_settings.py`
- Modify: `app/modules/admin/routes/api.py`
- Modify: `app/__init__.py`
- Test: `tests/test_admin_backup_api.py`

- [ ] 先写权限、安全标头、保存/测试/创建/列表/下载/删除 API 测试。
- [ ] 运行测试并确认 RED。
- [ ] 实现 API、限流、同源/XHR 防护和安全错误响应。
- [ ] 运行测试至 GREEN。

### Task 4: 独立调度 Sidecar 与部署配置

**Files:**
- Create: `app/tasks/backup_scheduler.py`
- Modify: `requirements.txt`
- Modify: `docker/Dockerfile`
- Modify: `compose.dev.yml`
- Modify: `compose.prod.yml`
- Modify: `.env.example`
- Modify: `docs/PRODUCTION.md`
- Test: `tests/test_backup_scheduler.py`
- Test: `tests/test_deploy_healthcheck.py`

- [ ] 先写到期时间槽、原子认领、单任务执行和 Compose 断言测试。
- [ ] 运行测试并确认 RED。
- [ ] 实现 Sidecar 轮询/调度并更新镜像依赖和挂载。
- [ ] 运行测试、Compose config 和编译检查至通过。

### Task 5: 后台页面与教程弹窗

**Files:**
- Create: `app/modules/admin/templates/admin/settings/backup.html`
- Modify: `app/modules/admin/templates/admin/settings/index.html`
- Modify: `app/modules/admin/routes/pages.py`
- Test: `tests/test_admin_backup_page.py`

- [ ] 先写页面入口、字段、操作、教程内容、ARIA 和移动端断言测试。
- [ ] 运行测试并确认 RED。
- [ ] 实现响应式页面、状态轮询和两个教程弹窗。
- [ ] 运行测试至 GREEN。

### Task 6: 集成验证、审查、提交与推送

**Files:**
- Modify only files required by review findings.

- [ ] 运行全部定向测试、覆盖率、Python 编译、迁移检查和 Compose config。
- [ ] 启动本地应用，使用 Browser 验证桌面/移动端、教程弹窗与目标交互。
- [ ] 完成规格审查、代码质量审查和安全复查，修复 CRITICAL/HIGH/MEDIUM。
- [ ] 确认不包含 `miniprogram-1/.gitignore` 等无关改动。
- [ ] 按约定式提交信息提交并推送 `main`。

