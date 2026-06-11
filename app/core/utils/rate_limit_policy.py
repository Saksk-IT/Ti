# -*- coding: utf-8 -*-
"""Rate limit policy helpers."""

from __future__ import annotations

import math
import os
import re
from typing import Callable


_LIMIT_PREFIX_RE = re.compile(
    r"(?P<prefix>^\s*)(?P<count>\d+)(?P<suffix>\s*(?:/|\s+per\s+).+)$",
    re.IGNORECASE,
)
_DEFAULT_PRODUCTION_MULTIPLIER = 100
_CONFIGURED_EXPAND_LIMITS: bool | None = None
_CONFIGURED_MULTIPLIER: int | None = None


def _positive_int(raw: object, default: int) -> int:
    try:
        value = int(str(raw or "").strip())
    except (TypeError, ValueError):
        return int(default)
    return max(1, value)


def production_rate_limit_multiplier() -> int:
    """Return the production multiplier for all rate limits."""
    raw = os.environ.get("RATELIMIT_LIMIT_MULTIPLIER", str(_DEFAULT_PRODUCTION_MULTIPLIER))
    return _positive_int(raw, _DEFAULT_PRODUCTION_MULTIPLIER)


def configure_rate_limit_policy(app) -> None:
    """Synchronize app config with decorators registered after extension init."""
    global _CONFIGURED_EXPAND_LIMITS, _CONFIGURED_MULTIPLIER

    should_expand = not bool(app.config.get("DEBUG")) and not bool(app.config.get("TESTING"))
    default = _DEFAULT_PRODUCTION_MULTIPLIER if should_expand else 1
    _CONFIGURED_EXPAND_LIMITS = should_expand
    _CONFIGURED_MULTIPLIER = (
        _positive_int(app.config.get("RATELIMIT_LIMIT_MULTIPLIER"), default)
        if should_expand
        else 1
    )


def should_expand_rate_limits() -> bool:
    if _CONFIGURED_EXPAND_LIMITS is not None:
        return bool(_CONFIGURED_EXPAND_LIMITS)

    env_name = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("APP_ENV")
        or os.environ.get("DEPLOY_ENV")
        or ""
    ).strip().lower()
    return env_name in {"production", "prod"}


def active_rate_limit_multiplier() -> int:
    """Return the multiplier for code that runs inside or outside Flask."""
    try:
        from flask import current_app

        configured = current_app.config.get("RATELIMIT_LIMIT_MULTIPLIER")
        if current_app.config.get("DEBUG") or current_app.config.get("TESTING"):
            return 1
        return _positive_int(configured, _DEFAULT_PRODUCTION_MULTIPLIER)
    except RuntimeError:
        if _CONFIGURED_MULTIPLIER is not None:
            return _CONFIGURED_MULTIPLIER
        return production_rate_limit_multiplier() if should_expand_rate_limits() else 1


def expand_manual_rate_limit_count(base_count: int) -> int:
    """Expand hand-written count based limits with the active deployment multiplier."""
    return max(1, int(base_count)) * active_rate_limit_multiplier()


def relax_manual_rate_limit_interval(base_seconds: int) -> int:
    """Relax hand-written interval based limits with the active deployment multiplier."""
    base = max(1, int(base_seconds))
    return max(1, int(math.ceil(base / active_rate_limit_multiplier())))


def expand_limit_value(limit_value: str, multiplier: int) -> str:
    """Expand a Flask-Limiter limit string by multiplying each leading count."""
    parts = []
    for raw_part in str(limit_value).split(";"):
        part = raw_part.strip()
        match = _LIMIT_PREFIX_RE.match(part)
        if not match:
            parts.append(part)
            continue
        next_count = int(match.group("count")) * int(multiplier)
        parts.append(f"{match.group('prefix')}{next_count}{match.group('suffix')}")
    return ";".join(parts)


def expand_rate_limit(limit_value: str | Callable[[], str]) -> str | Callable[[], str]:
    """Expand string or callable limits in production."""
    if not should_expand_rate_limits():
        return limit_value

    multiplier = active_rate_limit_multiplier()
    if multiplier <= 1:
        return limit_value

    if callable(limit_value):
        return lambda: expand_limit_value(str(limit_value()), multiplier)

    return expand_limit_value(str(limit_value), multiplier)
