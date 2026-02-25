# Ti 项目 — SQLite → PostgreSQL 完整迁移教程

> 本项目已完成全量 ORM 迁移，所有模块均使用 SQLAlchemy ORM + PostgreSQL，不再依赖 SQLite 直连层。

---

## 目录

1. [前提条件](#前提条件)
2. [安装 Python 驱动](#第一步安装-python-驱动)
3. [创建 PostgreSQL 数据库](#第二步创建-postgresql-数据库)
4. [配置 .env](#第三步配置-env)
5. [初始化 Alembic 迁移](#第四步初始化-alembic-迁移)
6. [迁移 SQLite 数据](#第五步迁移-sqlite-数据)
7. [标记迁移状态](#第六步标记迁移状态)
8. [验证](#第七步验证)
9. [清理旧 SQLite 文件](#第八步清理旧-sqlite-文件)
10. [日常使用](#日常使用)
11. [回滚方案](#回滚方案)
12. [注意事项](#注意事项)

---

## 前提条件

- Docker 已安装并运行
- 项目虚拟环境在 `.venv/`
- 已有 Docker 容器 `study-pg`（postgres:16-alpine，端口 5432）
  - 用户：`studyuser`
  - 密码：`studypass`
  - 已有数据库：`study_db`（另一个项目）

> 两个项目各用各的数据库（`study_db` / `ti_db`），同一个 PostgreSQL 实例，数据完全隔离。

如果还没有 PostgreSQL 容器，先创建：

```bash
docker run -d \
  --name study-pg \
  -e POSTGRES_USER=studyuser \
  -e POSTGRES_PASSWORD=studypass \
  -e POSTGRES_DB=study_db \
  -p 5432:5432 \
  --restart unless-stopped \
  postgres:16-alpine
```

---

## 第一步：安装 Python 驱动

```bash
# 激活虚拟环境后执行
.venv/Scripts/python.exe -m pip install psycopg2-binary
```

---

## 第二步：创建 PostgreSQL 数据库

```bash
docker exec study-pg psql -U studyuser -d study_db -c "CREATE DATABASE ti_db OWNER studyuser;"
```

验证：

```bash
docker exec study-pg psql -U studyuser -d ti_db -c "SELECT 1;"
```

---

## 第三步：配置 .env

编辑项目根目录 `.env`，添加或修改：

```env
DATABASE_URL=postgresql://studyuser:studypass@localhost:5432/ti_db
```

其余配置保持不变。完整配置参考 `.env.example`。

> **重要**：`DATABASE_URL` 必须设置，否则 config.py 会回退到 SQLite（仅作为开发兜底，不推荐）。

---

## 第四步：初始化 Alembic 迁移

```bash
# 如果 migrations/ 目录已存在，先删除
rmdir /s /q migrations      # Windows
# rm -rf migrations          # Linux/macOS

# 初始化迁移目录
.venv/Scripts/python.exe -m flask db init

# 根据 ORM 模型自动生成迁移脚本
.venv/Scripts/python.exe -m flask db migrate -m "initial schema"
```

检查 `migrations/versions/` 下生成的 `.py` 文件，确认表结构无误后执行：

```bash
# 在 PostgreSQL 中建表
.venv/Scripts/python.exe -m flask db upgrade
```

---

## 第五步：迁移 SQLite 数据

项目根目录已有 `migrate_data.py` 脚本，直接执行：

```bash
.venv/Scripts/python.exe migrate_data.py
```

脚本会自动：
- 读取 `var/instance/submissions.db` 中所有表
- 逐表插入到 PostgreSQL
- 修复自增序列（`setval` 同步 max id）

如果某些表因唯一约束冲突报错，脚本会跳过并提示，不影响其他表。

---

## 第六步：标记迁移状态

```bash
# 告诉 Alembic 当前数据库已是最新版本
.venv/Scripts/python.exe -m flask db stamp head
```

---

## 第七步：验证

```bash
# 启动应用
.venv/Scripts/python.exe -m flask run
```

验证数据：

```bash
# 查询用户数
docker exec study-pg psql -U studyuser -d ti_db -c "SELECT count(*) FROM users;"

# 查询科目数
docker exec study-pg psql -U studyuser -d ti_db -c "SELECT count(*) FROM subjects;"

# 查询题目数
docker exec study-pg psql -U studyuser -d ti_db -c "SELECT count(*) FROM questions;"
```

也可以通过 Web 管理工具查看数据库：

```bash
# 安装 pgAdmin（可选）
docker run -d \
  --name pgadmin \
  -e PGADMIN_DEFAULT_EMAIL=admin@admin.com \
  -e PGADMIN_DEFAULT_PASSWORD=admin \
  -p 5050:80 \
  --restart unless-stopped \
  dpage/pgadmin4

# 浏览器访问 http://localhost:5050
# 添加服务器：主机 host.docker.internal，端口 5432，用户 studyuser，密码 studypass
```

---

## 第八步：清理旧 SQLite 文件

确认 PostgreSQL 数据完整且应用运行正常后，可以清理旧文件：

### 1. 备份 SQLite（以防万一）

```bash
# 复制到安全位置
copy var\instance\submissions.db var\instance\submissions.db.bak
```

### 2. 删除 SQLite 数据库文件

```bash
del var\instance\submissions.db
del var\instance\test.db
```

### 3. 已删除的旧代码文件（ORM 迁移中已自动清理）

以下文件在 ORM 迁移过程中已被删除，无需手动处理：

| 文件 | 说明 |
|------|------|
| `app/core/utils/database.py` | SQLite 直连层（get_db/close_db/init_db/safe_in_clause） |
| `app/core/utils/db_tables.py` | SQLite 建表脚本 |
| `app/core/utils/db_indexes.py` | SQLite 索引脚本 |
| `app/core/utils/migrations.py` | SQLite 迁移脚本 |

### 4. 可选清理

```bash
# 迁移脚本（一次性使用）
del migrate_data.py
```

---

## 日常使用

### 模型变更后

```bash
# 生成迁移脚本
.venv/Scripts/python.exe -m flask db migrate -m "描述变更内容"

# 检查生成的迁移文件，确认无误后执行
.venv/Scripts/python.exe -m flask db upgrade
```

### 确保 Docker 容器运行

```bash
# 查看状态
docker ps -a --filter name=study-pg

# 启动（如已停止）
docker start study-pg
```

### 常用 psql 命令

```bash
# 进入交互式 psql
docker exec -it study-pg psql -U studyuser -d ti_db

# 查看所有表
\dt

# 查看表结构
\d users

# 查询数据
SELECT * FROM users LIMIT 5;

# 退出
\q
```

---

## 回滚方案

如果迁移后遇到严重问题需要回退：

1. 停止应用
2. 恢复 SQLite 备份：`copy var\instance\submissions.db.bak var\instance\submissions.db`
3. 在 `.env` 中注释掉 `DATABASE_URL`（回退到 SQLite）
4. 恢复旧代码：`git checkout <迁移前的commit> -- app/core/utils/database.py app/core/utils/db_tables.py app/core/utils/db_indexes.py app/core/utils/migrations.py app/__init__.py app/core/utils/__init__.py`
5. 重启应用

> **注意**：回滚需要同时恢复代码和数据库文件，仅恢复其中一个会导致不一致。建议在迁移前打一个 git tag 作为回滚点。

---

## 注意事项

1. **全量 ORM 迁移已完成** — 所有模块（auth、chat、user、exam、quiz、coding、admin、main、user_bank、notifications、popups）均已迁移到 SQLAlchemy ORM，不再使用 `get_db()` 直连
2. **数据库管理方式** — PostgreSQL + Alembic 是唯一的 schema 管理方式，旧的 `init_db()` 建表/迁移逻辑已移除
3. **布尔值差异** — SQLite 用 `0/1`，PostgreSQL 用 `true/false`，ORM 层已统一处理
4. **时间函数差异** — SQLite 的 `datetime('now', '+8 hours')` 已替换为 Python `datetime` + `timedelta`
5. **字符串聚合** — SQLite 的 `GROUP_CONCAT` 已替换为 PostgreSQL 的 `string_agg`
6. **自增主键** — SQLite 的 `cursor.lastrowid` 已替换为 `INSERT ... RETURNING id`
7. **生产环境** — 将 `.env` 中的 `DATABASE_URL` 指向生产 PostgreSQL 实例，并配置连接池参数（参考 `.env.example` 中 `[PROD]` 标记项）
8. **连接池推荐配置**（生产环境）：
   ```env
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=20
   DB_POOL_RECYCLE=300
   ```
