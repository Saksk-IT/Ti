# -*- coding: utf-8 -*-
"""
时间工具（统一北京时间，UTC+8）。

说明：
- 业务时间基准统一为北京时间（Asia/Shanghai），但不依赖系统 tzdata（Docker/Windows 均可用）。
- 为兼容 SQLite/旧数据的常见存储格式，本模块默认提供"无 tzinfo 的北京时间"用于写库与比较。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

BEIJING_OFFSET = timedelta(hours=8)
BEIJING_TZ = timezone(BEIJING_OFFSET, name="Asia/Shanghai")

# SQLite 侧：以 UTC 为基准 +8 小时，得到北京时间
SQLITE_BJ_NOW_EXPR = "datetime('now', '+8 hours')"
SQLITE_BJ_DATE_EXPR = "date('now', '+8 hours')"


def now_bj() -> datetime:
    """返回无 tzinfo 的北京时间（YYYY-MM-DD HH:MM:SS 使用此基准更稳）。"""
    return (datetime.now(timezone.utc) + BEIJING_OFFSET).replace(tzinfo=None)


def today_bj() -> date:
    return now_bj().date()

