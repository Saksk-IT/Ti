# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta

from app.core.utils.time_utils import now_bj as _now_bj
REVIEW_INTERVAL_DAYS = [1, 2, 4, 7, 15, 30, 60, 120]


def now_bj() -> datetime:
    return _now_bj()


def dt_to_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def next_4am(dt: datetime | None = None) -> datetime:
    base = dt or now_bj()
    target = base.replace(hour=4, minute=0, second=0, microsecond=0)
    if base >= target:
        target += timedelta(days=1)
    return target


def clamp_level(level: int) -> int:
    return max(0, min(int(level), len(REVIEW_INTERVAL_DAYS) - 1))


def calc_next_due(level: int, now: datetime | None = None) -> datetime:
    base = next_4am(now)
    days = REVIEW_INTERVAL_DAYS[clamp_level(level)]
    return base + timedelta(days=days)
