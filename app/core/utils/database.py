# -*- coding: utf-8 -*-
"""
数据库工具函数
"""
import sqlite3
import threading
import time
from flask import g, current_app


_SCHEMA_CACHE_LOCK = threading.Lock()
_TABLE_COLUMNS_CACHE = {}


def _monotonic() -> float:
    return time.monotonic()


def get_table_columns(table_name: str, conn: sqlite3.Connection = None):
    """获取表字段列表（带短 TTL 缓存，减少频繁 PRAGMA 开销）。

    说明：
    - 主要用于 request 级别频繁调用的兼容检查（例如 before_request / JWT 校验）。
    - TTL 可通过配置 `DB_SCHEMA_CACHE_TTL_SECONDS` 调整；设为 0 可禁用缓存。
    """
    name = str(table_name or '').strip()
    if not name:
        return set()

    ttl = current_app.config.get('DB_SCHEMA_CACHE_TTL_SECONDS', 60)
    try:
        ttl = int(ttl)
    except Exception:
        ttl = 60
    if ttl < 0:
        ttl = 0

    now = _monotonic()
    if ttl > 0:
        with _SCHEMA_CACHE_LOCK:
            item = _TABLE_COLUMNS_CACHE.get(name)
            if item:
                exp_at, cols = item
                if exp_at >= now:
                    return set(cols)
                _TABLE_COLUMNS_CACHE.pop(name, None)

    c = conn or get_db()
    try:
        rows = c.execute(f"PRAGMA table_info({name})").fetchall()
        cols = {r['name'] for r in rows} if rows else set()
    except Exception:
        cols = set()

    if ttl > 0:
        with _SCHEMA_CACHE_LOCK:
            _TABLE_COLUMNS_CACHE[name] = (now + float(ttl), frozenset(cols))
    return set(cols)


def invalidate_schema_cache(table_name: str = None) -> None:
    """清理表结构缓存。"""
    with _SCHEMA_CACHE_LOCK:
        if table_name:
            _TABLE_COLUMNS_CACHE.pop(str(table_name).strip(), None)
        else:
            _TABLE_COLUMNS_CACHE.clear()


def _configure_sqlite_connection(conn: sqlite3.Connection) -> None:
    """为 SQLite 连接设置项目级并发/一致性参数。

    目标：在不引入外部数据库的前提下，尽量降低并发写入时的 `database is locked` 概率。
    """
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')

    journal_mode = str(current_app.config.get('SQLITE_JOURNAL_MODE', 'WAL') or 'WAL').strip().upper()
    if journal_mode not in {'WAL', 'DELETE', 'TRUNCATE', 'PERSIST', 'MEMORY', 'OFF'}:
        journal_mode = 'WAL'

    synchronous = str(current_app.config.get('SQLITE_SYNCHRONOUS', 'NORMAL') or 'NORMAL').strip().upper()
    if synchronous not in {'OFF', 'NORMAL', 'FULL', 'EXTRA'}:
        synchronous = 'NORMAL'

    busy_timeout_ms = current_app.config.get('SQLITE_BUSY_TIMEOUT_MS', 5000)
    try:
        busy_timeout_ms = int(busy_timeout_ms)
    except Exception:
        busy_timeout_ms = 5000
    if busy_timeout_ms < 0:
        busy_timeout_ms = 0

    try:
        conn.execute(f'PRAGMA journal_mode = {journal_mode}')
    except Exception:
        pass

    try:
        conn.execute(f'PRAGMA synchronous = {synchronous}')
    except Exception:
        pass

    try:
        conn.execute(f'PRAGMA busy_timeout = {busy_timeout_ms}')
    except Exception:
        pass


def connect_db() -> sqlite3.Connection:
    """创建一个新的数据库连接（带统一 PRAGMA）。"""
    timeout = current_app.config.get('SQLITE_TIMEOUT', 15)
    try:
        timeout = float(timeout)
    except Exception:
        timeout = 15.0
    if timeout <= 0:
        timeout = 15.0

    conn = sqlite3.connect(current_app.config['DATABASE_PATH'], timeout=timeout)
    _configure_sqlite_connection(conn)
    return conn


def get_db():
    """获取数据库连接（使用Flask g对象实现连接池）"""
    if 'db' not in g:
        g.db = connect_db()
    return g.db


def close_db(error=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库（创建表和索引）"""
    conn = connect_db()
    
    try:
        # 创建表
        _create_tables(conn)
        # 运行数据迁移
        _run_migrations(conn)
        # 创建索引（放在迁移之后，避免重建表导致索引丢失）
        _create_indexes(conn)
        conn.commit()
        print('[OK] 数据库初始化完成')
    except Exception as e:
        print(f'[ERROR] 数据库初始化失败: {str(e)}')
        conn.rollback()
    finally:
        conn.close()


def _run_migrations(conn):
    """运行数据库迁移（带版本表，可重复启动不重复执行）"""
    schema_ok = True
    try:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id TEXT PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
    except Exception as e:
        schema_ok = False
        print(f'[WARN] 创建 schema_migrations 失败: {e}')

    def _is_applied(migration_id: str) -> bool:
        if not schema_ok:
            return False
        try:
            row = conn.execute(
                'SELECT 1 FROM schema_migrations WHERE id = ? LIMIT 1',
                (str(migration_id),),
            ).fetchone()
            return row is not None
        except Exception:
            return False

    def _mark_applied(migration_id: str) -> None:
        if not schema_ok:
            return
        try:
            conn.execute(
                'INSERT OR IGNORE INTO schema_migrations (id) VALUES (?)',
                (str(migration_id),),
            )
        except Exception as e:
            print(f'[WARN] 记录迁移 {migration_id} 失败: {e}')

    def _run_once(migration_id: str, fn) -> None:
        if _is_applied(migration_id):
            return
        try:
            fn()
        except Exception as e:
            print(f'[WARN] 迁移 {migration_id} 失败: {e}')
            return
        _mark_applied(migration_id)

    def _migrate_users_has_password_set_backfill() -> None:
        # 检查has_password_set字段是否存在
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'has_password_set' not in cols:
            return

        # 字段存在，检查是否有需要更新的老用户
        # 更新所有有password_hash但没有email的老用户（has_password_set=0或NULL）
        result = conn.execute(
            '''
            UPDATE users
            SET has_password_set = 1
            WHERE password_hash IS NOT NULL
              AND password_hash != ''
              AND (email IS NULL OR email = '')
              AND (has_password_set = 0 OR has_password_set IS NULL)
            '''
        )
        updated_count = result.rowcount
        if updated_count > 0:
            print(f'[迁移] 已为 {updated_count} 个老用户更新 has_password_set=1')

    def _migrate_mistakes_columns_compat() -> None:
        # mistakes 表字段兼容：历史版本可能使用 last_updated；新版本统一 created_at/updated_at
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(mistakes)").fetchall()]
        if not cols:
            return

        colset = set(cols)

        def _add_column(def_sql: str) -> None:
            try:
                conn.execute(f"ALTER TABLE mistakes ADD COLUMN {def_sql}")
            except Exception as e:
                # 兼容并发启动/重复执行：可能已被其他进程添加
                if 'duplicate column name' in str(e).lower():
                    return
                raise

        if 'wrong_count' not in colset:
            _add_column('wrong_count INTEGER DEFAULT 1')
        conn.execute("UPDATE mistakes SET wrong_count = 1 WHERE wrong_count IS NULL")

        if 'created_at' not in colset:
            _add_column('created_at DATETIME')

        if 'last_updated' in colset:
            conn.execute("UPDATE mistakes SET created_at = last_updated WHERE created_at IS NULL")
        elif 'updated_at' in colset:
            conn.execute("UPDATE mistakes SET created_at = updated_at WHERE created_at IS NULL")
        else:
            conn.execute("UPDATE mistakes SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")

        if 'updated_at' not in colset:
            _add_column('updated_at DATETIME')
        if 'last_updated' in colset:
            conn.execute("UPDATE mistakes SET updated_at = last_updated WHERE updated_at IS NULL")
        else:
            conn.execute("UPDATE mistakes SET updated_at = created_at WHERE updated_at IS NULL")

        if 'last_updated' not in colset:
            _add_column('last_updated DATETIME')
        conn.execute("UPDATE mistakes SET last_updated = updated_at WHERE last_updated IS NULL")

    def _migrate_portable_columns_questions() -> None:
        """为 questions 表增加 Portable Question Format 的结构化存储列，并回填。"""
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()]
        if not cols:
            return
        colset = set(cols)

        # 已升级到 PQF 新表结构（type/content/options/answer/...），无需再添加 portable_* 列
        if "type" in colset and "q_type" not in colset:
            return

        def _add_column(def_sql: str) -> None:
            try:
                conn.execute(f"ALTER TABLE questions ADD COLUMN {def_sql}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    return
                raise

        # 兼容：确保管理端常用字段存在（新库/旧库差异）
        if "tags" not in colset:
            _add_column("tags TEXT DEFAULT ''")
        if "source" not in colset:
            _add_column("source TEXT")
        if "created_by" not in colset:
            _add_column("created_by INTEGER")
        if "updated_by" not in colset:
            _add_column("updated_by INTEGER")
        if "updated_at" not in colset:
            _add_column("updated_at DATETIME")

        # Portable 结构化列（不影响现有逻辑，供统一 JSON 导入/导出与未来升级使用）
        if "portable_type" not in colset:
            _add_column("portable_type TEXT")
        if "portable_content" not in colset:
            _add_column("portable_content TEXT")
        if "portable_options" not in colset:
            _add_column("portable_options TEXT")
        if "portable_answer" not in colset:
            _add_column("portable_answer TEXT")
        if "portable_tags" not in colset:
            _add_column("portable_tags TEXT")
        if "portable_version" not in colset:
            _add_column("portable_version INTEGER DEFAULT 1")

        # 刷新列集合
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()]
        colset = set(cols)

        # 兜底填充 updated_at/tags
        if "updated_at" in colset:
            if "created_at" in colset:
                conn.execute(
                    "UPDATE questions SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)"
                )
            else:
                conn.execute("UPDATE questions SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)")
        if "tags" in colset:
            conn.execute("UPDATE questions SET tags = '' WHERE tags IS NULL OR tags IN ('[]', '[ ]')")

        # 回填 Portable 列
        import json as _json
        from app.core.utils.portable_question_format import internal_question_to_portable

        select_cols = ["id", "q_type", "content", "options", "answer", "explanation"]
        if "difficulty" in colset:
            select_cols.append("difficulty")
        if "tags" in colset:
            select_cols.append("tags")

        rows = conn.execute(
            f"SELECT {', '.join(select_cols)} FROM questions WHERE portable_type IS NULL OR portable_type = ''"
        ).fetchall()
        for r in rows:
            try:
                qid = int(r["id"])
                portable = internal_question_to_portable(
                    q_id=qid,
                    q_type=r["q_type"],
                    content=r["content"],
                    options=r["options"],
                    answer=r["answer"],
                    explanation=r["explanation"],
                    difficulty=r["difficulty"] if "difficulty" in colset else 1,
                    tags=r["tags"] if "tags" in colset else None,
                )
                conn.execute(
                    """
                    UPDATE questions
                    SET portable_type=?,
                        portable_content=?,
                        portable_options=?,
                        portable_answer=?,
                        portable_tags=?,
                        portable_version=1
                    WHERE id=?
                    """,
                    (
                        portable.get("type") or "",
                        portable.get("content") or "",
                        _json.dumps(portable.get("options") or [], ensure_ascii=False),
                        _json.dumps(
                            portable.get("answer") if portable.get("answer") is not None else [],
                            ensure_ascii=False,
                        ),
                        _json.dumps(portable.get("tags") or [], ensure_ascii=False),
                        qid,
                    ),
                )
            except Exception:
                continue

    def _migrate_portable_columns_user_bank_questions() -> None:
        """为 user_bank_questions 表增加 Portable Question Format 的结构化存储列，并回填。"""
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(user_bank_questions)").fetchall()]
        if not cols:
            return
        colset = set(cols)

        # 已升级到 PQF 新表结构（type/content/options/answer/...），无需再添加 portable_* 列
        if "type" in colset and "q_type" not in colset:
            return

        def _add_column(def_sql: str) -> None:
            try:
                conn.execute(f"ALTER TABLE user_bank_questions ADD COLUMN {def_sql}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    return
                raise

        if "portable_type" not in colset:
            _add_column("portable_type TEXT")
        if "portable_content" not in colset:
            _add_column("portable_content TEXT")
        if "portable_options" not in colset:
            _add_column("portable_options TEXT")
        if "portable_answer" not in colset:
            _add_column("portable_answer TEXT")
        if "portable_version" not in colset:
            _add_column("portable_version INTEGER DEFAULT 1")

        # 刷新列集合
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(user_bank_questions)").fetchall()]
        colset = set(cols)

        import json as _json
        from app.core.utils.portable_question_format import internal_question_to_portable

        select_cols = ["id", "q_type", "content", "options", "answer", "explanation"]
        if "difficulty" in colset:
            select_cols.append("difficulty")

        rows = conn.execute(
            f"SELECT {', '.join(select_cols)} FROM user_bank_questions WHERE portable_type IS NULL OR portable_type = ''"
        ).fetchall()
        for r in rows:
            try:
                qid = int(r["id"])
                portable = internal_question_to_portable(
                    q_id=qid,
                    q_type=r["q_type"],
                    content=r["content"],
                    options=r["options"],
                    answer=r["answer"],
                    explanation=r["explanation"],
                    difficulty=r["difficulty"] if "difficulty" in colset else 1,
                    tags=None,
                )
                conn.execute(
                    """
                    UPDATE user_bank_questions
                    SET portable_type=?,
                        portable_content=?,
                        portable_options=?,
                        portable_answer=?,
                        portable_version=1
                    WHERE id=?
                    """,
                    (
                        portable.get("type") or "",
                        portable.get("content") or "",
                        _json.dumps(portable.get("options") or [], ensure_ascii=False),
                        _json.dumps(
                            portable.get("answer") if portable.get("answer") is not None else [],
                            ensure_ascii=False,
                        ),
                        qid,
                    ),
                )
            except Exception:
                continue

    def _migrate_questions_tags_cleanup() -> None:
        """修复历史 tags/portable_tags 存储（例如 tags='[]' 导致 portable_tags='[\"[]\"]'）。"""
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()]
        if not cols:
            return
        colset = set(cols)

        # 新表结构不再依赖 portable_tags 清理
        if "portable_tags" not in colset and "portable_type" not in colset:
            return

        if "tags" in colset:
            conn.execute("UPDATE questions SET tags = '' WHERE tags IS NULL OR tags IN ('[]', '[ ]')")

        if "portable_tags" in colset:
            conn.execute(
                """
                UPDATE questions
                SET portable_tags = '[]'
                WHERE portable_tags IS NULL
                   OR portable_tags = ''
                   OR portable_tags IN ('["[]"]', '["[ ]"]', '[""]')
                """
            )

    def _migrate_rebuild_questions_to_pqf() -> None:
        """重建 questions 表为 PQF 同名列结构，并删除旧列。

        新列（核心）：type/content/options/answer/analysis/tags/difficulty
        兼容保留：subject_id/image_path/created_by/updated_by/created_at/updated_at/source
        """
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(questions)").fetchall()]
        if not cols:
            return
        colset = set(cols)

        # 已是新结构则跳过
        if "type" in colset and "q_type" not in colset:
            return

        import json as _json
        from app.core.utils.portable_question_format import internal_question_to_portable

        def _safe_int(v, default=0):
            try:
                return int(v)
            except Exception:
                return int(default)

        has_subject_id = "subject_id" in colset
        has_q_type = "q_type" in colset
        has_content = "content" in colset
        has_options = "options" in colset
        has_answer = "answer" in colset
        has_explanation = "explanation" in colset
        has_difficulty = "difficulty" in colset
        has_image_path = "image_path" in colset
        has_source = "source" in colset
        has_created_by = "created_by" in colset
        has_updated_by = "updated_by" in colset
        has_created_at = "created_at" in colset
        has_updated_at = "updated_at" in colset
        has_tags = "tags" in colset

        select_cols = ["id"]
        for c, ok in (
            ("subject_id", has_subject_id),
            ("q_type", has_q_type),
            ("content", has_content),
            ("options", has_options),
            ("answer", has_answer),
            ("explanation", has_explanation),
            ("difficulty", has_difficulty),
            ("image_path", has_image_path),
            ("source", has_source),
            ("created_by", has_created_by),
            ("updated_by", has_updated_by),
            ("created_at", has_created_at),
            ("updated_at", has_updated_at),
            ("tags", has_tags),
        ):
            if ok:
                select_cols.append(c)

        rows = conn.execute(f"SELECT {', '.join(select_cols)} FROM questions ORDER BY id ASC").fetchall()

        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE IF EXISTS questions__new")
        conn.execute(
            """
            CREATE TABLE questions__new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                options TEXT DEFAULT '[]',
                answer TEXT DEFAULT '[]',
                analysis TEXT,
                tags TEXT DEFAULT '[]',
                difficulty INTEGER DEFAULT 1,
                image_path TEXT,
                source TEXT,
                created_by INTEGER,
                updated_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
            )
            """
        )

        max_id = 0
        for r in rows or []:
            try:
                qid = int(r["id"])
            except Exception:
                continue
            max_id = max(max_id, qid)

            portable = internal_question_to_portable(
                q_id=qid,
                q_type=r["q_type"] if has_q_type else "",
                content=r["content"] if has_content else "",
                options=r["options"] if has_options else "[]",
                answer=r["answer"] if has_answer else "",
                explanation=r["explanation"] if has_explanation else "",
                difficulty=r["difficulty"] if has_difficulty else 1,
                tags=r["tags"] if has_tags else None,
            )

            conn.execute(
                """
                INSERT INTO questions__new (
                    id, subject_id, type, content, options, answer, analysis, tags, difficulty,
                    image_path, source, created_by, updated_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    qid,
                    r["subject_id"] if has_subject_id else None,
                    portable.get("type") or "essay",
                    portable.get("content") or "",
                    _json.dumps(portable.get("options") or [], ensure_ascii=False),
                    _json.dumps(
                        portable.get("answer") if portable.get("answer") is not None else [],
                        ensure_ascii=False,
                    ),
                    portable.get("analysis") or "",
                    _json.dumps(portable.get("tags") or [], ensure_ascii=False),
                    _safe_int(portable.get("difficulty"), 1),
                    r["image_path"] if has_image_path else None,
                    r["source"] if has_source else None,
                    _safe_int(r["created_by"], None) if has_created_by and r["created_by"] is not None else None,
                    _safe_int(r["updated_by"], None) if has_updated_by and r["updated_by"] is not None else None,
                    r["created_at"] if has_created_at else None,
                    r["updated_at"] if has_updated_at else None,
                ),
            )

        conn.execute("DROP TABLE questions")
        conn.execute("ALTER TABLE questions__new RENAME TO questions")
        try:
            if max_id > 0:
                conn.execute("DELETE FROM sqlite_sequence WHERE name = 'questions'")
                conn.execute("INSERT INTO sqlite_sequence(name, seq) VALUES('questions', ?)", (int(max_id),))
        except Exception:
            pass
        conn.execute("PRAGMA foreign_keys = ON")

    def _migrate_rebuild_user_bank_questions_to_pqf() -> None:
        """重建 user_bank_questions 表为 PQF 同名列结构，并删除旧列。"""
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(user_bank_questions)").fetchall()]
        if not cols:
            return
        colset = set(cols)

        # 已是新结构则跳过
        if "type" in colset and "q_type" not in colset:
            return

        import json as _json
        from app.core.utils.portable_question_format import internal_question_to_portable

        def _safe_int(v, default=0):
            try:
                return int(v)
            except Exception:
                return int(default)

        has_bank_id = "bank_id" in colset
        has_user_id = "user_id" in colset
        has_q_type = "q_type" in colset
        has_content = "content" in colset
        has_options = "options" in colset
        has_answer = "answer" in colset
        has_explanation = "explanation" in colset
        has_difficulty = "difficulty" in colset
        has_image_path = "image_path" in colset
        has_source_type = "source_type" in colset
        has_source_question_id = "source_question_id" in colset
        has_sort_order = "sort_order" in colset
        has_created_at = "created_at" in colset
        has_updated_at = "updated_at" in colset
        has_tags = "tags" in colset

        select_cols = ["id"]
        for c, ok in (
            ("bank_id", has_bank_id),
            ("user_id", has_user_id),
            ("q_type", has_q_type),
            ("content", has_content),
            ("options", has_options),
            ("answer", has_answer),
            ("explanation", has_explanation),
            ("difficulty", has_difficulty),
            ("image_path", has_image_path),
            ("source_type", has_source_type),
            ("source_question_id", has_source_question_id),
            ("sort_order", has_sort_order),
            ("created_at", has_created_at),
            ("updated_at", has_updated_at),
            ("tags", has_tags),
        ):
            if ok:
                select_cols.append(c)

        rows = conn.execute(
            f"SELECT {', '.join(select_cols)} FROM user_bank_questions ORDER BY id ASC"
        ).fetchall()

        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE IF EXISTS user_bank_questions__new")
        conn.execute(
            """
            CREATE TABLE user_bank_questions__new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                options TEXT DEFAULT '[]',
                answer TEXT DEFAULT '[]',
                analysis TEXT,
                tags TEXT DEFAULT '[]',
                difficulty INTEGER DEFAULT 1,
                image_path TEXT,
                source_type TEXT DEFAULT 'custom',
                source_question_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        max_id = 0
        for r in rows or []:
            try:
                qid = int(r["id"])
            except Exception:
                continue
            max_id = max(max_id, qid)

            portable = internal_question_to_portable(
                q_id=qid,
                q_type=r["q_type"] if has_q_type else "",
                content=r["content"] if has_content else "",
                options=r["options"] if has_options else "[]",
                answer=r["answer"] if has_answer else "",
                explanation=r["explanation"] if has_explanation else "",
                difficulty=r["difficulty"] if has_difficulty else 1,
                tags=r["tags"] if has_tags else None,
            )

            conn.execute(
                """
                INSERT INTO user_bank_questions__new (
                    id, bank_id, user_id, type, content, options, answer, analysis, tags, difficulty,
                    image_path, source_type, source_question_id, sort_order, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    qid,
                    _safe_int(r["bank_id"], 0) if has_bank_id else 0,
                    _safe_int(r["user_id"], 0) if has_user_id else 0,
                    portable.get("type") or "essay",
                    portable.get("content") or "",
                    _json.dumps(portable.get("options") or [], ensure_ascii=False) if portable.get("options") is not None else None,
                    _json.dumps(
                        portable.get("answer") if portable.get("answer") is not None else [],
                        ensure_ascii=False,
                    ),
                    portable.get("analysis") or "",
                    _json.dumps(portable.get("tags") or [], ensure_ascii=False),
                    _safe_int(portable.get("difficulty"), 1),
                    r["image_path"] if has_image_path else None,
                    r["source_type"] if has_source_type and r["source_type"] is not None else "custom",
                    r["source_question_id"] if has_source_question_id else None,
                    _safe_int(r["sort_order"], 0) if has_sort_order else 0,
                    r["created_at"] if has_created_at else None,
                    r["updated_at"] if has_updated_at else None,
                ),
            )

        conn.execute("DROP TABLE user_bank_questions")
        conn.execute("ALTER TABLE user_bank_questions__new RENAME TO user_bank_questions")
        try:
            if max_id > 0:
                conn.execute("DELETE FROM sqlite_sequence WHERE name = 'user_bank_questions'")
                conn.execute(
                    "INSERT INTO sqlite_sequence(name, seq) VALUES('user_bank_questions', ?)",
                    (int(max_id),),
                )
        except Exception:
            pass
        conn.execute("PRAGMA foreign_keys = ON")

    def _migrate_user_progress_tags_to_uqti() -> None:
        """把历史 user_progress 中的标签数据迁移到 user_question_tag_items（按用户维度）。

        迁移来源：
        - 公共题库：p_key='question_tags_v1'，结构 {tags:[], bindings:{qid:[tag,...]}}
        - 个人/共享题库：p_key GLOB 'bank_*_tags'，结构 {tags:[], question_tags:{qid:[tag,...]}}

        说明：
        - 仅做 INSERT OR IGNORE，不覆盖用户已在新表中的现有标签
        - 不删除旧的 user_progress 数据（避免误删）
        """
        import json as _json
        import re as _re

        try:
            from app.core.utils.user_question_tags import (
                SCOPE_QUESTION_CENTER,
                SCOPE_USER_BANK,
                TAG_DEF_QUESTION_ID,
                ensure_tag_tables,
            )

            ensure_tag_tables(conn)
        except Exception:
            return

        def _clean_tag(name) -> str:
            s = (name or "").strip()
            if not s:
                return ""
            s = _re.sub(r"\s+", " ", str(s)).strip()
            if len(s) > 20:
                s = s[:20].strip()
            if not s or s.lower() == "all":
                return ""
            return s

        # ---- question_center: question_tags_v1 ----
        try:
            rows = conn.execute(
                "SELECT user_id, data FROM user_progress WHERE p_key = ?",
                ("question_tags_v1",),
            ).fetchall()
        except Exception:
            rows = []

        for r in rows or []:
            try:
                uid = int(r["user_id"])
            except Exception:
                continue
            raw = r["data"] if r and r["data"] is not None else ""
            try:
                store = _json.loads(raw) if raw else {}
            except Exception:
                store = {}
            if not isinstance(store, dict):
                continue

            tags = store.get("tags") if isinstance(store.get("tags"), list) else []
            bindings = store.get("bindings") if isinstance(store.get("bindings"), dict) else {}

            for t in tags:
                tag = _clean_tag(t)
                if not tag:
                    continue
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (uid, str(SCOPE_QUESTION_CENTER), 0, int(TAG_DEF_QUESTION_ID), tag),
                    )
                except Exception:
                    continue

            if isinstance(bindings, dict):
                for qid_raw, tag_list in bindings.items():
                    try:
                        qid = int(qid_raw)
                    except Exception:
                        continue
                    if qid <= 0 or not isinstance(tag_list, list):
                        continue
                    for t in tag_list:
                        tag = _clean_tag(t)
                        if not tag:
                            continue
                        try:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (uid, str(SCOPE_QUESTION_CENTER), 0, int(qid), tag),
                            )
                        except Exception:
                            continue

        # ---- user_bank: bank_*_tags ----
        try:
            rows = conn.execute(
                "SELECT user_id, p_key, data FROM user_progress WHERE p_key GLOB 'bank_*_tags'"
            ).fetchall()
        except Exception:
            rows = []

        for r in rows or []:
            try:
                uid = int(r["user_id"])
            except Exception:
                continue
            key = (r["p_key"] or "").strip()
            m = _re.match(r"^bank_(\\d+)_tags$", key)
            if not m:
                continue
            try:
                bank_id = int(m.group(1))
            except Exception:
                continue
            if bank_id <= 0:
                continue

            raw = r["data"] if r and r["data"] is not None else ""
            try:
                store = _json.loads(raw) if raw else {}
            except Exception:
                store = {}
            if not isinstance(store, dict):
                continue

            tags = store.get("tags") if isinstance(store.get("tags"), list) else []
            question_tags = (
                store.get("question_tags") if isinstance(store.get("question_tags"), dict) else {}
            )

            for t in tags:
                tag = _clean_tag(t)
                if not tag:
                    continue
                try:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (uid, str(SCOPE_USER_BANK), int(bank_id), int(TAG_DEF_QUESTION_ID), tag),
                    )
                except Exception:
                    continue

            if isinstance(question_tags, dict):
                for qid_raw, tag_list in question_tags.items():
                    try:
                        qid = int(qid_raw)
                    except Exception:
                        continue
                    if qid <= 0 or not isinstance(tag_list, list):
                        continue
                    for t in tag_list:
                        tag = _clean_tag(t)
                        if not tag:
                            continue
                        try:
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (uid, str(SCOPE_USER_BANK), int(bank_id), int(qid), tag),
                            )
                        except Exception:
                            continue

    def _migrate_rebuild_user_question_tag_items_scope_id_not_null() -> None:
        """重建 user_question_tag_items，确保 scope_id 非 NULL，并用 COALESCE(scope_id,0) 去重。"""
        try:
            info = conn.execute("PRAGMA table_info(user_question_tag_items)").fetchall()
        except Exception:
            info = []
        if not info:
            return

        scope_id_info = None
        for r in info or []:
            try:
                if r["name"] == "scope_id":
                    scope_id_info = r
                    break
            except Exception:
                continue

        already_notnull = False
        try:
            already_notnull = bool(scope_id_info and int(scope_id_info.get("notnull") or 0) == 1)
        except Exception:
            already_notnull = False

        has_null_rows = False
        try:
            row = conn.execute("SELECT 1 FROM user_question_tag_items WHERE scope_id IS NULL LIMIT 1").fetchone()
            has_null_rows = row is not None
        except Exception:
            has_null_rows = False

        if already_notnull and not has_null_rows:
            return

        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE IF EXISTS user_question_tag_items__new")
        conn.execute(
            """
            CREATE TABLE user_question_tag_items__new (
                user_id INTEGER NOT NULL,
                scope TEXT NOT NULL,
                scope_id INTEGER NOT NULL DEFAULT 0,
                question_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, scope, scope_id, question_id, tag),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_question_tag_items__new
                (user_id, scope, scope_id, question_id, tag, created_at, updated_at)
                SELECT user_id, scope, COALESCE(scope_id, 0), question_id, tag, created_at, updated_at
                FROM user_question_tag_items
                """
            )
        except Exception:
            pass

        conn.execute("DROP TABLE user_question_tag_items")
        conn.execute("ALTER TABLE user_question_tag_items__new RENAME TO user_question_tag_items")
        conn.execute("PRAGMA foreign_keys = ON")

    def _migrate_timezone_beijing_utc8() -> None:
        """Unify SQLite timestamps to Beijing time (UTC+8).

        What it does:
        - Backfill: convert legacy SQLite CURRENT_TIMESTAMP values (UTC, second precision) to Beijing (+8 hours)
        - Future-proof: add INSERT/UPDATE triggers that automatically convert newly written UTC timestamps to Beijing

        Notes:
        - Triggers only convert values that look "close to UTC now" (threshold < 8 hours), avoiding touching values
          that are already Beijing (typically ~8 hours ahead when interpreted as UTC).
        - Does not depend on system timezone (works in Docker default UTC too).
        """
        import re

        def _q(ident: str) -> str:
            return '"' + str(ident).replace('"', '""') + '"'

        def _trigger_name(prefix: str, table: str) -> str:
            safe = re.sub(r"[^0-9a-zA-Z_]+", "_", str(table or "").strip())
            safe = safe.strip("_") or "t"
            return f"{prefix}_{safe}"

        # 6h threshold: less than the 8h UTC<->BJ gap, but wide enough for normal write delays
        threshold_seconds = 6 * 60 * 60

        # Some columns are written with CURRENT_TIMESTAMP but have no DEFAULT CURRENT_TIMESTAMP in schema
        extra_cols = {
            "last_active",
            "public_at",
            "submitted_at",
            "answered_at",
            "last_access_at",
            "last_reset_at",
        }

        # Backfill only typical SQLite UTC strings: "YYYY-MM-DD HH:MM:SS"
        migrate_where_suffix = " AND instr({c}, 'T') = 0 AND instr({c}, '.') = 0 AND length({c}) >= 19"

        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            tables = []
            for r in rows or []:
                try:
                    name = r["name"]
                except Exception:
                    continue
                if name:
                    tables.append(name)
        except Exception:
            tables = []

        for table in tables:
            try:
                info = conn.execute(f"PRAGMA table_info({_q(table)})").fetchall()
            except Exception:
                continue
            if not info:
                continue

            col_names = []
            default_ts_cols = []
            for r in info:
                try:
                    name = r["name"]
                    col_names.append(name)
                    dflt = (r["dflt_value"] if "dflt_value" in r.keys() else None) or ""
                    if "CURRENT_TIMESTAMP" in str(dflt).upper():
                        default_ts_cols.append(name)
                except Exception:
                    continue

            migrate_cols = sorted({*default_ts_cols, *[c for c in extra_cols if c in col_names]})
            for c in migrate_cols:
                try:
                    qc = _q(c)
                    qt = _q(table)
                    sql = (
                        f"UPDATE {qt} "
                        f"SET {qc} = datetime({qc}, '+8 hours') "
                        f"WHERE {qc} IS NOT NULL"
                        + migrate_where_suffix.format(c=qc)
                    )
                    conn.execute(sql)
                except Exception:
                    continue

            ts_cols = [
                n
                for n in col_names
                if str(n).endswith("_at") or n in {"last_active", "last_updated"}
            ]
            if not ts_cols:
                continue

            set_expr_parts = []
            for n in ts_cols:
                qn = _q(n)
                cond = (
                    f"{qn} IS NOT NULL AND "
                    f"abs(strftime('%s', {qn}) - strftime('%s', 'now')) <= {int(threshold_seconds)}"
                )
                set_expr_parts.append(
                    f"{qn} = CASE WHEN {cond} THEN datetime({qn}, '+8 hours') ELSE {qn} END"
                )

            set_expr = ",\n                            ".join(set_expr_parts)
            qt = _q(table)

            trig_ai = _trigger_name("tz_bj_ai", table)
            trig_au = _trigger_name("tz_bj_au", table)

            try:
                conn.execute(f"DROP TRIGGER IF EXISTS {_q(trig_ai)}")
            except Exception:
                pass
            try:
                conn.execute(f"DROP TRIGGER IF EXISTS {_q(trig_au)}")
            except Exception:
                pass

            try:
                conn.execute(
                    f"""
                    CREATE TRIGGER {_q(trig_ai)}
                    AFTER INSERT ON {qt}
                    BEGIN
                        UPDATE {qt}
                        SET
                            {set_expr}
                        WHERE rowid = NEW.rowid;
                    END;
                    """
                )
            except Exception:
                pass

            try:
                conn.execute(
                    f"""
                    CREATE TRIGGER {_q(trig_au)}
                    AFTER UPDATE ON {qt}
                    BEGIN
                        UPDATE {qt}
                        SET
                            {set_expr}
                        WHERE rowid = NEW.rowid;
                    END;
                    """
                )
            except Exception:
                pass

    def _migrate_question_center_tags_to_subject_scopes() -> None:
        """把公共题库标签从 scope_id=0（旧“全局”）迁移到 scope_id=subject_id（按题库隔离）。

        - 仅迁移 question_id>0 的绑定行（tag-题目关系）
        - 为迁移到各 subject 的 tag 补齐占位行（question_id=0），使“标签定义”可显示（count=0）
        - 删除旧 scope_id=0 的绑定行，避免重复统计
        """
        import re as _re

        try:
            from app.core.utils.user_question_tags import (
                SCOPE_QUESTION_CENTER,
                TAG_DEF_QUESTION_ID,
                ensure_tag_tables,
            )

            ensure_tag_tables(conn)
        except Exception:
            return

        try:
            row = conn.execute(
                "SELECT 1 FROM user_question_tag_items WHERE scope=? AND scope_id=0 AND question_id>0 LIMIT 1",
                (str(SCOPE_QUESTION_CENTER),),
            ).fetchone()
            if not row:
                return
        except Exception:
            return

        try:
            rows = conn.execute(
                """
                SELECT
                  uq.user_id AS user_id,
                  uq.question_id AS question_id,
                  uq.tag AS tag,
                  q.subject_id AS subject_id
                FROM user_question_tag_items uq
                JOIN questions q ON q.id = uq.question_id
                WHERE uq.scope = ?
                  AND uq.scope_id = 0
                  AND uq.question_id > 0
                  AND q.subject_id IS NOT NULL
                """,
                (str(SCOPE_QUESTION_CENTER),),
            ).fetchall()
        except Exception:
            rows = []

        insert_rows = []
        placeholder_rows = set()

        for r in rows or []:
            try:
                uid = int(r["user_id"])
                qid = int(r["question_id"])
                sid = int(r["subject_id"] or 0)
            except Exception:
                continue
            if uid <= 0 or qid <= 0 or sid <= 0:
                continue

            tag = _re.sub(r"\s+", " ", str(r["tag"] or "")).strip()
            if not tag or tag.lower() == "all":
                continue
            if len(tag) > 20:
                tag = tag[:20].strip()
            if not tag:
                continue

            insert_rows.append((uid, str(SCOPE_QUESTION_CENTER), sid, qid, tag))
            placeholder_rows.add((uid, str(SCOPE_QUESTION_CENTER), sid, int(TAG_DEF_QUESTION_ID), tag))

        if insert_rows:
            try:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    insert_rows,
                )
            except Exception:
                pass

        if placeholder_rows:
            try:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO user_question_tag_items (user_id, scope, scope_id, question_id, tag)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    list(placeholder_rows),
                )
            except Exception:
                pass

        try:
            conn.execute(
                "DELETE FROM user_question_tag_items WHERE scope=? AND scope_id=0 AND question_id>0",
                (str(SCOPE_QUESTION_CENTER),),
            )
        except Exception:
            pass

    _run_once('20260116_001_users_has_password_set_backfill', _migrate_users_has_password_set_backfill)
    _run_once('20260116_002_mistakes_columns_compat', _migrate_mistakes_columns_compat)
    _run_once('20260116_003_questions_portable_columns', _migrate_portable_columns_questions)
    _run_once('20260116_004_user_bank_questions_portable_columns', _migrate_portable_columns_user_bank_questions)
    _run_once('20260116_005_questions_tags_cleanup', _migrate_questions_tags_cleanup)
    _run_once('20260117_001_rebuild_questions_to_pqf', _migrate_rebuild_questions_to_pqf)
    _run_once('20260117_002_rebuild_user_bank_questions_to_pqf', _migrate_rebuild_user_bank_questions_to_pqf)
    _run_once('20260117_003_migrate_user_progress_tags_to_uqti', _migrate_user_progress_tags_to_uqti)
    _run_once('20260117_004_rebuild_user_question_tag_items_scope_id', _migrate_rebuild_user_question_tag_items_scope_id_not_null)
    _run_once('20260119_001_migrate_question_center_tags_subject_scoped', _migrate_question_center_tags_to_subject_scopes)
    _run_once('20260117_005_timezone_beijing_utc8', _migrate_timezone_beijing_utc8)


def _create_tables(conn):
    """创建数据库表"""
    # 基础表：用户表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_locked INTEGER DEFAULT 0,
            session_version INTEGER DEFAULT 0,
            avatar TEXT,
            contact TEXT,
            college TEXT,
            last_active DATETIME,
            is_subject_admin INTEGER DEFAULT 0,
            is_notification_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 邮箱验证码表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS email_verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            code_type TEXT NOT NULL CHECK(code_type IN ('bind', 'login', 'reset_password')),
            user_id INTEGER,
            is_used INTEGER DEFAULT 0,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            used_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：科目表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            is_locked INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 基础表：题目表（题库中心专用，PQF 结构化存储）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            options TEXT DEFAULT '[]',
            answer TEXT DEFAULT '[]',
            analysis TEXT,
            tags TEXT DEFAULT '[]',
            difficulty INTEGER DEFAULT 1,
            image_path TEXT,
            source TEXT,
            created_by INTEGER,
            updated_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
        )
    ''')
    
    # 编程题专用表：编程题集表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS coding_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            is_locked INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 编程题专用表：编程题目表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS coding_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coding_subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            q_type TEXT NOT NULL CHECK(q_type IN ('函数题', '编程题')),
            description TEXT NOT NULL,
            difficulty TEXT NOT NULL CHECK(difficulty IN ('easy', 'medium', 'hard')),
            code_template TEXT,
            programming_language TEXT DEFAULT "python",
            time_limit INTEGER DEFAULT 5,
            memory_limit INTEGER DEFAULT 128,
            test_cases_json TEXT NOT NULL,
            examples TEXT,
            constraints TEXT,
            hints TEXT,
            is_enabled INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(coding_subject_id) REFERENCES coding_subjects(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：收藏表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：错题表
    # 兼容历史版本：部分库可能存在 last_updated 字段；新库统一使用 created_at/updated_at
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            wrong_count INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：用户答题记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            user_answer TEXT,
            is_correct INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 用户进度表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            p_key TEXT NOT NULL,
            data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, p_key),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 按用户维度的题目标签明细表（跨题库统一：系统/个人/共享）
    # 说明：question_id 可能来自不同题表，因此不做 question_id 外键约束；用 (scope, scope_id) 区分来源域。
    # 用户签到表（按天）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, checkin_date),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_question_tag_items (
            user_id INTEGER NOT NULL,
            scope TEXT NOT NULL,
            scope_id INTEGER NOT NULL DEFAULT 0,
            question_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, scope, scope_id, question_id, tag),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    # 考试表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT,
            duration_minutes INTEGER NOT NULL,
            config_json TEXT,
            total_score REAL DEFAULT 0,
            status TEXT DEFAULT 'ongoing',
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            submitted_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # 考试题目表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            order_index INTEGER NOT NULL,
            score_val REAL DEFAULT 1,
            user_answer TEXT,
            is_correct INTEGER,
            answered_at DATETIME,
            FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS exam_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            config_json TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # 添加用户表列（如果不存在）- 兼容旧数据库
    try:
        cur = conn.cursor()
        # 检查users表是否存在
        table_check = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if table_check:
            cols = [r['name'] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
            if 'is_locked' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN is_locked INTEGER DEFAULT 0')
            if 'session_version' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN session_version INTEGER DEFAULT 0')
            if 'avatar' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN avatar TEXT')
            if 'contact' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN contact TEXT')
            if 'college' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN college TEXT')
            if 'last_active' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN last_active DATETIME')
            if 'is_subject_admin' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN is_subject_admin INTEGER DEFAULT 0')
            if 'is_notification_admin' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN is_notification_admin INTEGER DEFAULT 0')
            if 'email' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN email TEXT')
            if 'email_verified' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0')
            if 'email_verified_at' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN email_verified_at DATETIME')
            if 'has_password_set' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN has_password_set INTEGER DEFAULT 0')
                # 为所有有password_hash但没有email的老用户设置has_password_set=1
                # （老用户通过用户名注册，有真实密码）
                try:
                    cur.execute('''
                        UPDATE users 
                        SET has_password_set = 1 
                        WHERE password_hash IS NOT NULL 
                        AND password_hash != '' 
                        AND (email IS NULL OR email = '')
                    ''')
                    updated_count = cur.rowcount
                    if updated_count > 0:
                        print(f'[迁移] 已为 {updated_count} 个老用户设置 has_password_set=1')
                except Exception as e:
                    print(f'[WARN] 迁移老用户has_password_set字段失败: {e}')
            if 'openid' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN openid TEXT')
            
            # 创建邮箱唯一索引（如果不存在）
            try:
                index_rows = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='users'"
                ).fetchall()
                indexes = [row[0] for row in index_rows]
                if 'idx_users_email_unique' not in indexes:
                    # SQLite中，UNIQUE约束通过唯一索引实现
                    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL')
                # 创建openid唯一索引（如果不存在）
                if 'idx_users_openid' not in indexes:
                    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_openid ON users(openid) WHERE openid IS NOT NULL')
            except Exception as e:
                print(f'[WARN] 创建邮箱/openid唯一索引失败: {e}')

        # 添加 questions 表的字段（如果不存在）- 兼容旧数据库
        # 注意：questions 表只用于题库中心，不包含编程题字段
        table_check = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='questions'").fetchone()
        if table_check:
            question_cols = [r['name'] for r in cur.execute("PRAGMA table_info(questions)").fetchall()]
            if 'image_path' not in question_cols:
                cur.execute('ALTER TABLE questions ADD COLUMN image_path TEXT')
            
            # 不再添加编程题相关字段到 questions 表
            # 编程题应使用 coding_questions 表
        
        # 添加 subjects 表的字段（如果不存在）- 兼容旧数据库
        table_check = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subjects'").fetchone()
        if table_check:
            subject_cols = [r['name'] for r in cur.execute("PRAGMA table_info(subjects)").fetchall()]
            if 'description' not in subject_cols:
                cur.execute('ALTER TABLE subjects ADD COLUMN description TEXT')
            if 'is_locked' not in subject_cols:
                cur.execute('ALTER TABLE subjects ADD COLUMN is_locked INTEGER DEFAULT 0')
            if 'created_at' not in subject_cols:
                # SQLite不支持带非常量默认值的ALTER TABLE,所以不设置默认值
                cur.execute('ALTER TABLE subjects ADD COLUMN created_at DATETIME')
    except Exception as e:
        print(f'[WARN] 添加字段失败: {e}')
        pass
    
    # 添加user_progress表的created_at字段（如果不存在）
    try:
        cur = conn.cursor()
        progress_cols = [r['name'] for r in cur.execute("PRAGMA table_info(user_progress)").fetchall()]
        if 'created_at' not in progress_cols:
            # SQLite不支持带非常量默认值的ALTER TABLE,所以不设置默认值
            cur.execute('ALTER TABLE user_progress ADD COLUMN created_at TIMESTAMP')
    except Exception:
        pass

    # 聊天：会话表
    # 说明：为从根源杜绝 direct 私聊重复会话，增加 direct_pair_key：
    # - direct 私聊：存 "min_uid:max_uid"（例如 "1:10"）
    # - 非 direct：可为空
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            c_type TEXT NOT NULL DEFAULT 'direct',
            title TEXT,
            direct_pair_key TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 聊天：用户备注表（每个用户对“其他用户”的备注，仅自己可见）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_remarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            target_user_id INTEGER NOT NULL,
            remark TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner_user_id, target_user_id),
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 兼容老库：补字段 direct_pair_key（如果不存在）
    try:
        cur = conn.cursor()
        conv_cols = [r['name'] for r in cur.execute("PRAGMA table_info(chat_conversations)").fetchall()]
        if 'direct_pair_key' not in conv_cols:
            cur.execute('ALTER TABLE chat_conversations ADD COLUMN direct_pair_key TEXT')
    except Exception:
        pass

    # 聊天：会话成员表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            last_read_message_id INTEGER DEFAULT 0,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(conversation_id, user_id),
            FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 聊天：消息表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT 'text',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 通知表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            n_type TEXT NOT NULL DEFAULT 'info',
            priority INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            start_at DATETIME,
            end_at DATETIME,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 用户关闭通知记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notification_dismissals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notification_id INTEGER NOT NULL,
            dismissed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, notification_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(notification_id) REFERENCES notifications(id) ON DELETE CASCADE
        )
    ''')
    
    # 弹窗配置表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS popups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            popup_type TEXT NOT NULL DEFAULT 'info' CHECK(popup_type IN ('info', 'warning', 'success', 'error')),
            is_active INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            start_at DATETIME,
            end_at DATETIME,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 用户关闭弹窗记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS popup_dismissals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            popup_id INTEGER NOT NULL,
            dismissed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, popup_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(popup_id) REFERENCES popups(id) ON DELETE CASCADE
        )
    ''')
    
    # 弹窗显示统计表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS popup_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            popup_id INTEGER NOT NULL,
            user_id INTEGER,
            viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(popup_id) REFERENCES popups(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 代码提交历史表（用于记录编程题的提交记录）
    # 注意：question_id 引用 coding_questions 表，不是 questions 表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS code_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT NOT NULL,
            passed_cases INTEGER DEFAULT 0,
            total_cases INTEGER DEFAULT 0,
            execution_time REAL,
            error_message TEXT,
            score REAL DEFAULT 0.0,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES coding_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 用户编程统计表（用于快速查询用户对每道题的统计信息）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS coding_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            total_submissions INTEGER DEFAULT 0,
            accepted_submissions INTEGER DEFAULT 0,
            best_time REAL,
            best_score REAL DEFAULT 0.0,
            first_accepted_at DATETIME,
            last_submitted_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES coding_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 用户编程总统计表（用于快速查询用户整体统计）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_coding_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            total_submissions INTEGER DEFAULT 0,
            accepted_submissions INTEGER DEFAULT 0,
            solved_questions INTEGER DEFAULT 0,
            total_score REAL DEFAULT 0.0,
            average_score REAL DEFAULT 0.0,
            acceptance_rate REAL DEFAULT 0.0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 代码草稿表（用于实时保存用户代码）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS code_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            language TEXT DEFAULT 'python',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES coding_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 用户-科目限制表（黑名单模式）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            restricted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            restricted_by INTEGER,
            UNIQUE(user_id, subject_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY(restricted_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 系统配置表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY(updated_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 用户刷题统计表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_quiz_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            total_answered INTEGER DEFAULT 0,
            last_reset_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 查重记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_check_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            total_pairs INTEGER DEFAULT 0,
            duplicates_json TEXT NOT NULL,
            similarity_threshold REAL DEFAULT 0.8,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 加强训练：相似题缓存（保存到云端/DB，避免每次打开都重新计算）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reinforce_similar_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            scope_id INTEGER NOT NULL,
            version TEXT NOT NULL,
            pairs_json TEXT NOT NULL,
            pairs_count INTEGER DEFAULT 0,
            computed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, scope_id)
        )
    ''')
    
    # ============================================
    # 用户私人题库功能相关表
    # ============================================

    # 用户题库分类表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_bank_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, name),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 用户题库表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_question_banks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            cover_image TEXT,
            is_public INTEGER DEFAULT 0,
            public_description TEXT,
            allow_copy INTEGER DEFAULT 1,
            public_at DATETIME,
            question_count INTEGER DEFAULT 0,
            share_count INTEGER DEFAULT 0,
            public_use_count INTEGER DEFAULT 0,
            status INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(category_id) REFERENCES user_bank_categories(id) ON DELETE SET NULL
        )
    ''')

    # 用户题库题目表（PQF 结构化存储）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_bank_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            options TEXT DEFAULT '[]',
            answer TEXT DEFAULT '[]',
            analysis TEXT,
            tags TEXT DEFAULT '[]',
            difficulty INTEGER DEFAULT 1,
            image_path TEXT,
            source_type TEXT DEFAULT 'custom',
            source_question_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 题库分享表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bank_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            share_code TEXT UNIQUE,
            share_token TEXT UNIQUE,
            permission TEXT DEFAULT 'read',
            expires_at DATETIME,
            max_uses INTEGER,
            current_uses INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
            FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 分享记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bank_share_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            share_id INTEGER NOT NULL,
            bank_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status INTEGER DEFAULT 1,
            last_access_at DATETIME,
            access_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(share_id, user_id),
            FOREIGN KEY(share_id) REFERENCES bank_shares(id) ON DELETE CASCADE,
            FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 用户题库答题记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_bank_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bank_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            user_answer TEXT,
            is_correct INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES user_bank_questions(id) ON DELETE CASCADE
        )
    ''')

    # 用户题库错题表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_bank_mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bank_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            wrong_count INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES user_bank_questions(id) ON DELETE CASCADE
        )
    ''')

    # 公开题库使用记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS public_bank_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            last_access_at DATETIME,
            access_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bank_id, user_id),
            FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 用户题库收藏表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_bank_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bank_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(bank_id) REFERENCES user_question_banks(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES user_bank_questions(id) ON DELETE CASCADE
        )
    ''')

    # ============================================
    # ???????? / ???Study?
    # ============================================

    # ?????
    conn.execute('''
        CREATE TABLE IF NOT EXISTS study_learning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            scope_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            streak INTEGER DEFAULT 0,
            is_learned INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            last_result TEXT,
            last_answered_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, source, scope_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ?????
    conn.execute('''
        CREATE TABLE IF NOT EXISTS study_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            scope_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            review_level INTEGER DEFAULT 0,
            next_due_at DATETIME,
            last_review_at DATETIME,
            last_rating TEXT,
            lapse_count INTEGER DEFAULT 0,
            is_mastered INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, source, scope_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')


    # 初始化系统配置（如果不存在）
    default_configs = [
        ('quiz_limit_enabled', '0', '刷题数限制功能开关（0=关闭，1=开启）'),
        ('quiz_limit_count', '100', '用户刷题数限制（达到此数量后提示付费）')
    ]
    
    for config_key, config_value, description in default_configs:
        existing = conn.execute(
            'SELECT id FROM system_config WHERE config_key = ?',
            (config_key,)
        ).fetchone()
        
        if not existing:
            conn.execute(
                '''INSERT INTO system_config (config_key, config_value, description)
                   VALUES (?, ?, ?)''',
                (config_key, config_value, description)
            )


def _create_indexes(conn):
    """创建数据库索引"""
    # 检查表是否存在，只对存在的表创建索引
    cur = conn.cursor()
    existing_tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    
    indexes = []
    
    # 用户相关索引（只对存在的表创建）
    if 'favorites' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_favorites_user_question ON favorites(user_id, question_id)')
    if 'mistakes' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_mistakes_user_question ON mistakes(user_id, question_id)')
    if 'user_answers' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_user_answers_user ON user_answers(user_id, created_at)',
            'CREATE INDEX IF NOT EXISTS idx_user_answers_question ON user_answers(question_id)',
        ])
    
    # 题目相关索引（只对存在的表创建）
    if 'questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject_id)',
            'CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(type)',
            'CREATE INDEX IF NOT EXISTS idx_questions_subject_type ON questions(subject_id, type)',
        ])
    
    # 查重记录相关索引
    if 'duplicate_check_records' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_duplicate_check_subject ON duplicate_check_records(subject_id, created_at DESC)',
        ])

    # 加强训练：相似题缓存索引
    if 'reinforce_similar_cache' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_reinforce_similar_cache_updated ON reinforce_similar_cache(updated_at)')
    
    # 考试相关索引（只对存在的表创建）
    if 'exams' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exams_user_status ON exams(user_id, status)',
            'CREATE INDEX IF NOT EXISTS idx_exams_submitted ON exams(submitted_at)',
        ])
    if 'exam_questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exam_questions_exam ON exam_questions(exam_id)',
            'CREATE INDEX IF NOT EXISTS idx_exam_questions_question ON exam_questions(question_id)',
        ])
    if 'exam_templates' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exam_templates_user ON exam_templates(user_id, updated_at DESC)',
        ])
    
    # 用户进度索引（只对存在的表创建）
    if 'user_progress' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_progress_key ON user_progress(user_id, p_key)')

    if 'user_checkins' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_checkins_user_date ON user_checkins(user_id, checkin_date DESC)')

    # 用户题目标签（按用户维度）索引
    if 'user_question_tag_items' in existing_tables:
        indexes.extend([
            "CREATE INDEX IF NOT EXISTS idx_uqti_user_scope_scopeid_tag ON user_question_tag_items(user_id, scope, scope_id, tag)",
            "CREATE INDEX IF NOT EXISTS idx_uqti_user_scope_scopeid_qid ON user_question_tag_items(user_id, scope, scope_id, question_id)",
        ])

    # 聊天相关索引（只对存在的表创建）
    if 'chat_members' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_chat_members_user ON chat_members(user_id, conversation_id)')
    if 'chat_messages' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id, id DESC)')
    if 'chat_conversations' in existing_tables:
        # direct 私聊唯一键：从根源杜绝重复会话（仅当 c_type='direct' 时生效）
        indexes.append("CREATE UNIQUE INDEX IF NOT EXISTS ux_chat_direct_pair ON chat_conversations(direct_pair_key) WHERE c_type='direct' AND direct_pair_key IS NOT NULL")
    if 'user_remarks' in existing_tables:
        # 用户备注：便于查询
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_remarks_owner ON user_remarks(owner_user_id, target_user_id)')

    # 通知相关索引（只对存在的表创建）
    if 'notifications' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_notifications_time ON notifications(start_at, end_at)',
        ])
    if 'notification_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_notification_dismissals_user ON notification_dismissals(user_id, notification_id)')
    
    # 弹窗相关索引（只对存在的表创建）
    if 'popups' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popups_active ON popups(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_popups_time ON popups(start_at, end_at)',
            'CREATE INDEX IF NOT EXISTS idx_popups_type ON popups(popup_type)',
        ])
    if 'popup_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_popup_dismissals_user ON popup_dismissals(user_id, popup_id)')
    if 'popup_views' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popup_views_popup ON popup_views(popup_id, viewed_at)',
            'CREATE INDEX IF NOT EXISTS idx_popup_views_user ON popup_views(user_id, viewed_at)',
        ])
    
    # 代码提交相关索引（只对存在的表创建）
    if 'code_submissions' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_submissions_user_question ON code_submissions(user_id, question_id, submitted_at DESC)')
    
    # 代码草稿相关索引
    if 'code_drafts' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_drafts_user_question ON code_drafts(user_id, question_id)')
    
    # 用户-科目限制表索引
    if 'user_subjects' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_user_id ON user_subjects(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_subject_id ON user_subjects(subject_id)'
        ])
    
    # 系统配置表索引
    if 'system_config' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key)')
    
    # 用户刷题统计表索引
    if 'user_quiz_stats' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_quiz_stats_user_id ON user_quiz_stats(user_id)')
    
    # 邮箱验证码表索引
    if 'email_verification_codes' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_email_codes_email ON email_verification_codes(email, code_type, is_used)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_expires ON email_verification_codes(expires_at)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_user ON email_verification_codes(user_id)',
        ])

    # ============================================
    # 用户私人题库功能相关索引
    # ============================================

    # 用户题库分类表索引
    if 'user_bank_categories' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_ubc_user_id ON user_bank_categories(user_id)')

    # 用户题库表索引
    if 'user_question_banks' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_uqb_user_id ON user_question_banks(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_uqb_category_id ON user_question_banks(category_id)',
            'CREATE INDEX IF NOT EXISTS idx_uqb_status ON user_question_banks(status)',
            'CREATE INDEX IF NOT EXISTS idx_uqb_is_public ON user_question_banks(is_public, status)',
        ])

    # 用户题库题目表索引
    if 'user_bank_questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_ubq_bank_id ON user_bank_questions(bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_ubq_user_id ON user_bank_questions(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_ubq_source ON user_bank_questions(source_type, source_question_id)',
            'CREATE INDEX IF NOT EXISTS idx_ubq_type ON user_bank_questions(type)',
        ])

    # 题库分享表索引
    if 'bank_shares' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_bs_bank_id ON bank_shares(bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_bs_owner_id ON bank_shares(owner_id)',
        ])

    # 分享记录表索引
    if 'bank_share_records' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_bsr_user_id ON bank_share_records(user_id, status)',
            'CREATE INDEX IF NOT EXISTS idx_bsr_bank_id ON bank_share_records(bank_id)',
        ])

    # 用户题库答题记录表索引
    if 'user_bank_answers' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_uba_user_bank ON user_bank_answers(user_id, bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_uba_user_question ON user_bank_answers(user_id, question_id)',
        ])

    # 用户题库错题表索引
    if 'user_bank_mistakes' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_ubm_user_bank ON user_bank_mistakes(user_id, bank_id)')

    # 公开题库使用记录表索引
    if 'public_bank_users' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_pbu_bank_id ON public_bank_users(bank_id)',
            'CREATE INDEX IF NOT EXISTS idx_pbu_user_id ON public_bank_users(user_id)',
        ])



    # Study ????
    if 'study_learning' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_study_learning_user_scope ON study_learning(user_id, source, scope_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_learning_user_question ON study_learning(user_id, source, scope_id, question_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_learning_learned ON study_learning(user_id, source, scope_id, is_learned)',
        ])
    if 'study_review' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_study_review_user_scope ON study_review(user_id, source, scope_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_review_user_question ON study_review(user_id, source, scope_id, question_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_review_due ON study_review(user_id, source, scope_id, is_mastered, next_due_at)',
        ])
    for index_sql in indexes:
        conn.execute(index_sql)
