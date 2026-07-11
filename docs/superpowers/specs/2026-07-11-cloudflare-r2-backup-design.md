# Cloudflare R2 数据备份设计

## 目标

在后台管理系统的“系统设置”中增加 Cloudflare R2 数据备份页面，支持 R2 配置、连接测试、手动备份、定时备份、保留策略、记录下载/删除，以及配置和恢复教程弹窗。

## 已确认范围

- 备份内容：PostgreSQL、`var/uploads`、`var/instance`。
- 明确排除：Redis、日志、`.env.production`、Compose 文件和其他部署配置。
- 备份目标：仅支持 Cloudflare R2，不开放任意 S3 Endpoint。
- 恢复方式：后台不直接执行恢复；“恢复”按钮展示与当前备份关联的服务器 CLI 教程。
- 执行方式：使用独立 Python Sidecar，不在 Flask/Gunicorn 进程内调度。

## 架构

### 配置

R2 和调度配置保存在 `system_config`。`Secret Access Key` 使用独立 `BACKUP_CREDENTIAL_SECRET`（未设置时回退 `SECRET_KEY`）派生的 Fernet 密钥加密后存储。专用配置 API 只返回脱敏值和 `secret_configured`，通用配置列表也必须过滤该密钥。

配置字段：

- Endpoint：仅允许 Cloudflare R2 官方 HTTPS Endpoint。
- Bucket：3-63 位小写字母、数字和连字符。
- Key 前缀：默认 `backups/`，禁止绝对路径、反斜杠、`..` 和控制字符。
- Access Key ID / Secret Access Key。
- 定时开关、5 段 Cron（默认 `0 2 * * *`）、过期天数（默认 14）、最大保留份数（默认 3）。

### 任务与 Sidecar

新增 `BackupJob` 表，记录 `queued/running/completed/failed/deleting` 状态、触发方式、文件名、对象 Key、大小、SHA-256、错误摘要和关键时间。内部使用唯一活动槽、Cron 时间槽、Worker 所有权令牌与续租时间实现并发隔离和崩溃恢复，这些字段不进入管理端 DTO。

Web 端只创建任务。独立 Sidecar：

1. 原子认领一条排队任务；
2. 使用数据库唯一活动槽、原子认领和带 fencing token 的续租防止并发；
3. 通过 `pg_dump` 生成数据库文件，并复制上传/实例目录；
4. 写入清单并创建权限为 `0600` 的 `tar.gz`；
5. 上传 R2，使用 `head_object` 核对大小；
6. 更新任务状态；
7. 上传成功后按过期天数和最大份数清理当前前缀下的旧对象；
8. 无论成功或失败都清理临时目录。

定时任务由 Sidecar 依据保存的 Cron 判断是否到期，并通过幂等时间槽创建任务，避免多次触发。

### API

- `GET /admin/api/settings/backup`
- `POST /admin/api/settings/backup`
- `POST /admin/api/settings/backup/test`
- `GET /admin/api/backups`
- `POST /admin/api/backups`
- `GET /admin/api/backups/<id>/download`
- `DELETE /admin/api/backups/<id>`

所有写接口要求管理员 Session、同源请求和 `X-Requested-With: XMLHttpRequest`，并使用限流。接口只接收任务 ID，不接收任意文件路径或对象 Key。

### 页面

页面沿用现有后台玻璃卡片和表单风格，避免多层容器：

1. R2 存储配置：Endpoint、Bucket、前缀、Access Key、Secret，以及“教程”“测试连接”“保存配置”。
2. 定时备份：开关、Cron、过期天数、最大保留份数。
3. 备份记录：状态、文件名、大小、触发方式、时间与下载/恢复/删除操作。

教程弹窗使用 `role="dialog"`、`aria-modal="true"`，支持 Escape、遮罩关闭、初始焦点和关闭后焦点恢复。移动端表单改单列，操作按钮可换行且触控尺寸不少于 44px。

## Cloudflare 教程内容

1. 在 R2 创建私有 Bucket。
2. 创建 `Object Read & Write` Token，并限制到该 Bucket。
3. 复制只显示一次的 Access Key ID 和 Secret Access Key。
4. 填写 `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`，Region 由系统固定为 `auto`。
5. 保存并测试连接，再开启定时备份。
6. 离线保存 R2 凭据和 `BACKUP_CREDENTIAL_SECRET`，否则灾难恢复时无法读取已保存凭据。

## 恢复教程

恢复按钮展示：下载备份到服务器的建议目录、校验页面显示的 SHA-256、进入维护窗口、执行 `scripts/restore.sh <文件名>`、检查 Compose 服务与健康端点。后台页面本身不停止服务、不挂载 Docker Socket。

## 错误处理与安全

- Endpoint 严格校验，阻止 SSRF。
- Secret、数据库密码、签名 Header 和预签名 URL不写日志。
- `pg_dump` 使用参数数组、`shell=False`、超时和受控环境变量。
- 连接测试在固定测试前缀写入随机小对象，并在 `finally` 删除。
- 失败信息面向用户返回安全摘要，详细上下文只写服务器日志。
- 删除和留存仅处理数据库记录反查出的当前 Bucket/前缀对象。

## 测试与验收

- 配置校验、加密、脱敏、保留旧 Secret。
- Endpoint、Bucket、Prefix、Cron、留存边界。
- 管理员权限与后台写请求安全标头。
- R2 测试连接、预签名下载、删除限定对象。
- 任务创建、并发去重、状态流转和留存规则。
- 归档生成不包含 Redis、日志或部署配置。
- 页面入口、教程文案、弹窗无障碍与移动端 CSS。
- Compose Sidecar 配置、Python 编译、定向 pytest、桌面和移动端浏览器交互。
