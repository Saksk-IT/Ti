# Ti 生产数据迁移设计

**状态：** 已确认
**日期：** 2026-07-11
**目标：** 服务器 2 先通过现有 `scripts/deploy_ubuntu24.sh` 完成全新生产部署，再从服务器 2 执行一个入口命令，从服务器 1 拉取完整活动数据与可迁移业务配置并恢复。

## 1. 背景与设计原则

当前生产环境由 `compose.prod.yml` 编排 `nginx`、`web`、`worker`、`postgres`、`redis`、`backup` 六个服务。活动持久化状态位于 PostgreSQL、Redis、`var/uploads`、`var/instance` 与 `.env.production`。

本设计把“部署新服务器”和“迁移旧服务器数据”彻底分开：

1. 服务器 2 使用现有一键部署脚本建立全新的、可独立验证的生产环境。
2. 新增的数据迁移入口只负责从服务器 1 导出、传输、恢复和校验生产数据。
3. 迁移动作是最终切换动作。开始最终快照后，服务器 1 不再接受新写入，避免两台服务器产生数据分叉。
4. PostgreSQL 使用逻辑备份，不复制运行中的物理数据目录。
5. Redis 在应用写入冻结后执行持久化并停止服务，再归档完整 Redis 数据目录。
6. 所有归档、配置和临时文件按密钥处理，不在日志中输出真实配置值。

参考依据：

- PostgreSQL `pg_dump`：<https://www.postgresql.org/docs/16/app-pgdump.html>
- Redis 持久化：<https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/>
- Docker 数据卷备份与迁移：<https://docs.docker.com/engine/storage/volumes/#back-up-restore-or-migrate-data-volumes>

## 2. 用户操作入口

### 2.1 服务器 2 全新部署

服务器 2 先按现有生产部署文档执行：

```bash
cd /opt/ti
./scripts/deploy_ubuntu24.sh
```

迁移开始前，服务器 2 必须满足：

- `/opt/ti` 是完整 Git 仓库；
- `.env.production` 已生成且权限为 `600`；
- Compose 六个服务能够启动；
- `http://127.0.0.1:8080/api/ping?deep=1` 正常；
- 已配置从服务器 2 到服务器 1 的 SSH 密钥登录；
- SSH 主机密钥已由管理员核验并写入可信 `known_hosts`；
- 两端当前用户为 root，或 `sudo -n true` 可成功执行；迁移过程不能交互输入 sudo 密码；
- 私有 GHCR 场景下，服务器 2 已独立完成只读登录。

建议新部署阶段仅使用 IP/HTTP 验证。DNS 和 HTTPS 在数据迁移成功后切换。

### 2.2 一键数据迁移

在服务器 2 执行：

```bash
cd /opt/ti

./scripts/migrate_production_data.sh \
  --source ubuntu@服务器1IP \
  --source-dir /opt/ti
```

可选参数：

- `--source-port PORT`：服务器 1 SSH 端口，默认 `22`；
- `--identity-file PATH`：专用 SSH 私钥；
- `--known-hosts PATH`：已核验的 SSH 主机密钥文件；
- `--target-dir PATH`：服务器 2 部署目录，默认脚本所在仓库根目录；
- `--keep-bundle`：验证成功后保留本地迁移包，默认安全删除；
- `--dry-run`：只执行本地和远端预检，不停止服务、不导出数据。

正常模式要求用户输入同时包含源主机与目标主机名的确认文本。不能用简单 `yes` 绕过目标覆盖确认。

## 3. 方案对比与选择

### 3.1 采用：服务器 2 拉取并恢复

服务器 2 作为唯一编排入口，通过 SSH 在服务器 1 临时执行只读预检和受控导出，然后把迁移包拉回服务器 2 恢复。

优点：

- 服务器 1 不需要保存服务器 2 的 SSH 私钥；
- 用户最终只执行一个迁移入口；
- 可在服务器 1 停写前完成全部目标预检；
- 目标恢复失败时，入口可以自动恢复服务器 1 原服务；
- 新服务器部署逻辑继续由现有部署脚本维护。

### 3.2 不采用：手工导出、`scp`、手工恢复

该方案实现较简单，但需要多条人工命令，容易传错归档或遗漏校验，不满足一键迁移目标。

### 3.3 不采用：直接串联现有 `backup.sh` 与 `restore.sh`

现有脚本没有跨存储停写快照、独立 SHA-256 校验、安全归档提取、配置合并、失败恢复和迁移后数据对比，不能直接承担跨服务器最终迁移。

## 4. 组件边界

计划新增以下组件：

### 4.1 `scripts/migrate_production_data.sh`

服务器 2 的用户入口，职责包括：

- 参数与 SSH 信任校验；
- 本地和远端预检；
- 创建目标回滚点；
- 把导出 helper 临时发送到服务器 1；
- 启动源端停写和打包；
- 拉取迁移包与独立校验文件；
- 安全检查、恢复、验证；
- 成功确认或失败回滚。

### 4.2 `scripts/export_production_data.sh`

由服务器 2 通过 SSH 临时调用的服务器 1 helper，职责包括：

- 记录源端迁移状态和原始服务状态；
- 停止入口与写服务；
- 导出 PostgreSQL；
- 固化并停止 Redis 后归档 Redis 数据；
- 归档上传、实例和源配置；
- 生成统计、manifest 与校验和；
- 支持 `prepare`、`resume`、`finalize` 三种动作。

该 helper 不要求服务器 1 预先更新 Git；服务器 2 会把当前已验证版本的 helper 临时传输过去执行。

### 4.3 `scripts/lib/production_migration_common.sh`

共享 Shell 函数，职责包括：

- 严格参数校验；
- 安全临时目录和权限；
- Compose 命令构造；
- SHA-256 兼容封装；
- 固定格式日志；
- 迁移锁与状态文件；
- 固定白名单归档成员校验；
- 失败清理。

### 4.4 `scripts/lib/merge_production_env.py`

把源 `.env.production` 作为数据解析，禁止把远端配置直接 `source` 执行。输出采用“源配置为基础、目标部署键覆盖”的新文件，并使用原子替换写入目标 `.env.production`。

### 4.5 `tests/test_production_data_migration.py`

使用临时目录和 fake `ssh`、`scp`、`docker`、`curl` 命令验证编排顺序、安全边界、配置合并和回滚行为，不依赖真实生产服务器。

## 5. 迁移数据范围

### 5.1 默认迁移

- PostgreSQL 全库逻辑备份；
- Redis RDB/AOF 持久化目录；
- `var/uploads` 全部用户上传文件；
- `var/instance` 实例数据；
- 源 `.env.production` 配置快照；
- 源数据库版本、Redis key 数量、文件清单；
- 源 Git 提交、Compose 文件哈希、应用和基础服务镜像信息；
- 迁移包 manifest 与逐文件 SHA-256。

### 5.2 默认不迁移

- `var/logs` 历史日志；
- `backups/` 历史备份包与调度标记；
- `/etc/letsencrypt` 证书和私钥；
- Docker/GHCR 登录凭据；
- 宿主机完整 `/etc/nginx`；
- UFW 和云厂商安全组状态。

这些内容不属于恢复应用活动状态所必需的数据。域名、HTTPS、防火墙和外部平台 IP 白名单在迁移成功后按服务器 2 的部署环境重新配置。

## 6. 配置合并规则

服务器 2 全新部署会生成新的数据库密码和部署参数，但服务器 1 的 `SECRET_KEY` 可能参与数据库中既有教务凭据的加解密。因此不能完全保留服务器 2 的新 env，也不能直接用服务器 1 的 env 覆盖目标基础设施配置。

恢复算法：

1. 读取源配置快照，作为输出基础；
2. 从目标现有 `.env.production` 读取部署本地键，并保留源配置中尚不存在的目标新版本键，保证新部署版本向前兼容；
3. 同名业务键以源值为准，下列部署本地键始终用目标值覆盖；
4. 写入同目录临时文件；
5. 校验必需键后以原子替换更新 `.env.production`；
6. 设置权限 `600`。

目标值优先的部署本地键：

```text
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
TI_IMAGE
TI_IMAGE_PULL_POLICY
HTTP_BIND
HTTP_PORT
ENABLE_HTTPS
DOMAIN
EXTRA_DOMAINS
CERTBOT_EMAIL
SESSION_COOKIE_SECURE
```

包括 `SECRET_KEY`、默认管理员配置、微信、AI、邮件、短信、Sentry、限流、SSE 和备份策略在内的其他源配置随服务器 1 迁移。

GHCR Token 不属于 `.env.production` 的迁移内容，服务器 2 必须独立登录。

即使源 env 意外包含 `GHCR_TOKEN`、`GHCR_USERNAME` 或 `DOCKER_AUTH_CONFIG`，合并器也必须显式删除这些容器仓库认证键，不得写入服务器 2 的 `.env.production`。

## 7. 完整执行流程

### 7.1 停写前预检

所有可能失败的廉价检查必须在停止服务器 1 服务之前完成：

1. 校验源地址、端口、用户和目录格式；
2. 使用数组构造 SSH 参数，禁止 `eval`；
3. 强制 `BatchMode=yes`、`StrictHostKeyChecking=yes`、`IdentitiesOnly=yes`；
4. 校验源、目标不是同一台机器；
5. 校验两端部署目录、env、Compose 和 Docker 可用；
6. 校验 PostgreSQL 与 Redis 主版本兼容；
7. 校验两端生产 Compose 配置可解析；
8. 校验服务器 2 当前健康；
9. 估算源数据大小和目标剩余磁盘空间；
10. 取得源、目标迁移锁；
11. 记录源 Git、镜像、数据库迁移版本和服务状态；
12. 创建服务器 2 当前状态的回滚包。

应用镜像实际 digest 不一致时默认拒绝正式迁移，要求先让服务器 1 和服务器 2 运行同一镜像版本；`--dry-run` 会提前报告该问题。

### 7.2 服务器 1 冻结与导出

1. 停止 `backup`，防止并发备份；
2. 停止 `nginx`，阻断新请求；
3. 优雅停止 `web` 与 `worker`；
4. 确认应用写服务已停止；
5. 执行 `pg_dump -Fc --no-owner --no-acl`；
6. 使用 `pg_restore --list` 校验 PostgreSQL 归档；
7. 记录 Redis `DBSIZE`，执行同步持久化；
8. 停止 Redis，确保 AOF/RDB 不再变化；
9. 归档 Redis、uploads、instance 和源 env；
10. 生成固定格式 manifest 和逐文件 SHA-256；
11. 创建权限为 `600` 的最终迁移包及独立总 SHA-256 文件。

PostgreSQL 保持运行以完成逻辑导出，但服务器 1 的入口、应用、worker、backup 与 Redis在最终切换阶段保持停止。

### 7.3 传输与安全检查

1. 迁移包通过已验证的 SSH 会话拉取到服务器 2 的权限 `700` 临时目录；
2. 独立传输总 SHA-256，并在服务器 2 比对；
3. 解压前列出全部归档成员；
4. 拒绝绝对路径、`..`、符号链接、硬链接、设备、FIFO、socket；
5. 拒绝固定白名单之外的任何顶层成员；
6. 解压时不信任归档声明的 owner 和权限；
7. 校验内部逐文件 SHA-256 后才允许进入恢复阶段。

### 7.4 服务器 2 恢复

1. 停止目标 `nginx`、`web`、`worker`、`backup` 和 Redis；
2. 保持目标 PostgreSQL 运行；
3. 删除并重新创建目标业务数据库；
4. 使用 `pg_restore --exit-on-error --no-owner --no-privileges` 恢复；
5. 清空目标 Redis 目录，包括隐藏成员；
6. 恢复源 Redis 数据并修正为目标 Redis 容器用户所有；
7. 原子替换 `var/uploads` 与 `var/instance`；
8. 按第 6 节规则合并 `.env.production`；
9. 启动 PostgreSQL 与 Redis并等待健康；
10. 使用 `RUN_MIGRATIONS=1 ENSURE_DEFAULT_ADMIN=0` 执行数据库迁移；
11. 启动全部目标服务；
12. 在启动 `web`/`worker` 前比较 PostgreSQL、Redis 和文件摘要，避免应用启动产生的新缓存或队列 key 干扰迁移一致性判断；
13. 启动 `web`、`worker`、`nginx` 和 `backup`；
14. 执行运行态迁移后验证。

目标恢复不调用默认管理员重置逻辑，避免覆盖服务器 1 已有管理员凭据。

### 7.5 成功提交与失败回滚

成功条件全部满足后：

- 删除源端临时迁移包和临时 helper；
- 保留服务器 1 原始数据库和文件；
- 保持服务器 1 应用服务停止；
- 输出 DNS/HTTPS 后续命令；
- 默认删除服务器 2 的含密钥迁移包，除非使用 `--keep-bundle`。

任一步失败时：

- 停止服务器 2 的不完整服务；
- 从目标回滚包恢复服务器 2 迁移前状态；
- 通过源端 `resume` 动作恢复迁移前原本运行的服务器 1 服务；
- 清理两端临时文件；
- 不修改 DNS；
- 返回非零退出码并打印失败阶段，不打印密钥。

服务器 1 的原始数据不会被脚本删除。切换完成后至少保留 24 至 72 小时再人工下线。

## 8. 迁移后验证

自动验证至少覆盖：

- 目标 Compose 中带 healthcheck 的服务必须为 `healthy`，其余服务必须为 `running`；
- `/api/ping` 与 `/api/ping?deep=1`；
- PostgreSQL `alembic_version`；
- 源、目标数据库公共表行数摘要；
- 源、目标 Redis `DBSIZE`；
- uploads 与 instance 文件数、总大小及逐文件 SHA-256；
- 目标 `.env.production` 权限为 `600`；
- `SECRET_KEY` 哈希与源一致，但日志中不显示实际值；
- 目标 PostgreSQL 凭据哈希与迁移前目标一致；
- 目标应用镜像 digest 与预检记录一致；
- PostgreSQL 与 Redis 未暴露到公网。

验证完成后输出人工切换清单：

1. 将 DNS A/AAAA 记录指向服务器 2；
2. 在服务器 2 使用现有部署脚本启用或恢复 HTTPS；
3. 验证域名 `/api/ping?deep=1`；
4. 验证登录、上传读取、后台任务及第三方回调；
5. 检查微信、短信、邮件、AI 上游等外部 IP 白名单。

## 9. 测试策略

实现遵循 RED → GREEN → REFACTOR：

1. 先为参数、配置合并和归档边界编写失败测试；
2. 确认测试因功能缺失而失败；
3. 编写最小实现；
4. 运行聚焦测试；
5. 增加编排顺序和失败注入测试；
6. 完成 Shell 语法、现有部署测试和 Compose 配置验证。

必须覆盖：

- 非法源地址、端口和目录在 SSH 前失败；
- SSH 主机密钥不可信时在停写前失败；
- 源、目标为同一主机时失败；
- 镜像或主版本不兼容时在停写前失败；
- 目标覆盖确认文本错误时失败；
- 源端停写发生在 PostgreSQL/Redis/文件快照之前；
- 校验和不一致时不进入恢复；
- 恶意归档成员全部被拒绝；
- 配置合并保留目标部署键并迁移源 `SECRET_KEY`；
- 数据库、Redis、文件和健康检查任一阶段失败都会恢复服务器 1；
- 成功后不会重新启动服务器 1；
- 日志不包含密码、Token、DSN 和 env 原文；
- 重复运行不会静默覆盖未完成状态。

计划验证命令：

```bash
bash -n \
  scripts/migrate_production_data.sh \
  scripts/export_production_data.sh \
  scripts/lib/production_migration_common.sh

pytest -q tests/test_production_data_migration.py
pytest -q tests/test_deploy_healthcheck.py

docker compose --env-file .env.production -f compose.prod.yml config >/tmp/ti-compose-check.yml
git diff --check
```

## 10. 验收标准

实现完成需同时满足：

1. 服务器 2 使用现有脚本全新部署，不修改部署职责边界；
2. 数据迁移只需在服务器 2 执行一个入口命令；
3. 服务器 1 无需预装新迁移脚本；
4. PostgreSQL、Redis、uploads、instance 和必要源配置完整恢复；
5. 目标数据库凭据和服务器本地网络/HTTPS配置不被源 env 覆盖；
6. `SECRET_KEY` 等数据解密必需配置来自服务器 1；
7. 迁移包经过独立和内部双重校验；
8. 失败能够自动恢复服务器 1，成功后服务器 1 保持停止；
9. DNS 和 TLS 私钥不由数据脚本自动迁移；
10. 自动测试、现有部署回归测试、Shell 语法和 Compose 配置验证通过；
11. 文档包含服务器 2 部署、SSH 准备、一键迁移、DNS/HTTPS 切换和回滚步骤。
