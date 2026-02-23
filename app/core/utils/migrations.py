# -*- coding: utf-8 -*-
"""
数据库迁移函数。

从 database.py 拆分而来，包含所有 _run_migrations 及其内部迁移逻辑。
"""
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "_run_migrations",
]


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
        logger.warning(f'创建 schema_migrations 失败: {e}')

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
            logger.warning(f'记录迁移 {migration_id} 失败: {e}')

    def _run_once(migration_id: str, fn) -> None:
        if _is_applied(migration_id):
            return
        try:
            fn()
        except Exception as e:
            logger.warning(f'迁移 {migration_id} 失败: {e}')
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
            logger.info(f'已为 {updated_count} 个老用户更新 has_password_set=1')

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
        """把公共题库标签从 scope_id=0（旧"全局"）迁移到 scope_id=subject_id（按题库隔离）。

        - 仅迁移 question_id>0 的绑定行（tag-题目关系）
        - 为迁移到各 subject 的 tag 补齐占位行（question_id=0），使"标签定义"可显示（count=0）
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
