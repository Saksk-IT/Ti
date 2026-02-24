# -*- coding: utf-8 -*-
"""
数据库核心模块：连接管理、初始化入口。

== 新旧共存说明 ==
本项目正在从 raw SQLite → SQLAlchemy ORM 渐进迁移：
- 旧代码：继续使用 get_db() 获取 sqlite3.Connection，执行手写 SQL。
- 新代码：推荐使用 app.core.extensions.db.session + app.models 中的 ORM 模型。
- 当 DATABASE_URL 指向 PostgreSQL 时，ORM 代码自动适配；
  旧 get_db() 仍仅连接 SQLite（仅用于开发/过渡期）。
- 迁移完成后，本文件中的 SQLite 相关代码将被移除。

拆分说明：
- 表创建 → db_tables.py
- 迁移函数 → migrations.py
- 索引管理 → db_indexes.py

本文件末尾通过 re-export 保持向后兼容。
"""
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager

from flask import current_app, g

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 表结构缓存（短 TTL）
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 连接管理
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 事务管理
# ---------------------------------------------------------------------------
@contextmanager
def transaction(conn=None):
    """事务上下文管理器，自动 commit/rollback。

    用法::

        with transaction() as conn:
            conn.execute("INSERT INTO ...")
            conn.execute("UPDATE ...")
        # 正常退出自动 commit；异常自动 rollback 并重新抛出
    """
    c = conn or get_db()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise


# ---------------------------------------------------------------------------
# IN 子句安全构建工具
# ---------------------------------------------------------------------------
_IN_BATCH_SIZE = 900  # SQLite 参数上限 ~999，留余量


def safe_in_clause(column: str, values: list, sql: str, params: list) -> tuple:
    """安全地向 SQL 追加 ``AND column IN (...)`` 子句。

    - 当 *values* 不超过 ``_IN_BATCH_SIZE`` 时使用参数化占位符。
    - 超过时，对每个值强制 ``int()`` 转换后拼接，避免 SQLite 参数上限错误。
      ``int()`` 保证只有纯整数进入 SQL，杜绝注入风险。

    返回 ``(sql, params)``，调用方直接解包即可。
    """
    if not values:
        return sql, params
    if len(values) <= _IN_BATCH_SIZE:
        placeholders = ','.join(['?'] * len(values))
        sql += f" AND {column} IN ({placeholders})"
        params.extend(values)
    else:
        safe_ids = ','.join(str(int(v)) for v in values)
        sql += f" AND {column} IN ({safe_ids})"
    return sql, params


def init_db():
    """初始化数据库（创建表和索引）"""
    from app.core.utils.db_indexes import _create_indexes
    from app.core.utils.db_tables import _create_tables
    from app.core.utils.migrations import _run_migrations

    conn = connect_db()

    try:
        # 创建表
        _create_tables(conn)
        # 运行数据迁移
        _run_migrations(conn)
        # 创建索引（放在迁移之后，避免重建表导致索引丢失）
        _create_indexes(conn)
        conn.commit()
        logger.info('数据库初始化完成')
    except Exception as e:
        logger.error('数据库初始化失败: %s', e)
        conn.rollback()
    finally:
        conn.close()


__all__ = [
    # 核心连接
    'get_db', 'close_db', 'connect_db', 'init_db',
    'get_table_columns', 'invalidate_schema_cache',
    'safe_in_clause', 'transaction',
]
