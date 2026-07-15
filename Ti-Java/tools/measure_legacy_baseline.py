#!/usr/bin/env python3
"""Measure a safe legacy startup/SQL baseline with an isolated temporary DB."""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import math
import os
import pkgutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=5)
    return parser.parse_args()


def current_rss_mib() -> float:
    result = subprocess.run(
        ["/bin/ps", "-o", "rss=", "-p", str(os.getpid())],
        check=True,
        capture_output=True,
        text=True,
    )
    return round(int(result.stdout.strip()) / 1024, 3)


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def main() -> int:
    args = parse_args()
    if args.samples < 5 or args.samples > 20:
        raise SystemExit("--samples must be between 5 and 20")
    legacy_root = args.legacy_root.resolve()
    output = args.output.resolve()
    if not (legacy_root / "app" / "__init__.py").is_file():
        raise SystemExit(f"Not a Ti legacy root: {legacy_root}")

    with tempfile.TemporaryDirectory(prefix="ti-java-performance-") as data_dir:
        os.environ["DATA_DIR"] = data_dir
        os.environ["FLASK_ENV"] = "testing"
        os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
        os.environ["RATELIMIT_STORAGE_URL"] = "memory://"
        os.environ.pop("REDIS_URL", None)
        sys.path.insert(0, str(legacy_root))
        os.chdir(legacy_root)
        logging.disable(logging.CRITICAL)

        rss_before_mib = current_rss_mib()
        started = time.perf_counter()
        import app as legacy_app
        from app.core.extensions import db

        legacy_app._start_background_tasks = lambda _app: None
        app = legacy_app.create_app("testing")
        startup_ms = (time.perf_counter() - started) * 1000
        rss_after_app_mib = current_rss_mib()

        with app.app_context():
            import app.models as models_package

            for module_info in pkgutil.iter_modules(models_package.__path__):
                importlib.import_module(f"app.models.{module_info.name}")
            db.create_all()

            from sqlalchemy import event

            request_sql: list[float] = []
            query_started: list[float] = []

            def before_cursor_execute(*_args: Any) -> None:
                query_started.append(time.perf_counter())

            def after_cursor_execute(*_args: Any) -> None:
                request_sql.append((time.perf_counter() - query_started.pop()) * 1000)

            event.listen(db.engine, "before_cursor_execute", before_cursor_execute)
            event.listen(db.engine, "after_cursor_execute", after_cursor_execute)

            client = app.test_client()
            endpoints = (
                "/api/ping",
                "/api/public/banks/summary",
                "/api/questions/count",
                "/hub",
            )
            measurements: dict[str, dict[str, Any]] = {}
            try:
                for path in endpoints:
                    # A warm-up is intentionally excluded from the recorded samples.
                    client.get(path)
                    latencies: list[float] = []
                    sql_counts: list[int] = []
                    sql_durations: list[float] = []
                    statuses: list[int] = []
                    for _sample in range(args.samples):
                        request_sql.clear()
                        request_started = time.perf_counter()
                        response = client.get(path)
                        latencies.append((time.perf_counter() - request_started) * 1000)
                        statuses.append(response.status_code)
                        sql_counts.append(len(request_sql))
                        sql_durations.append(sum(request_sql))
                    measurements[path] = {
                        "samples": args.samples,
                        "statuses": statuses,
                        "latency_ms_median": round(statistics.median(latencies), 3),
                        "latency_ms_p95": round(percentile95(latencies), 3),
                        "sql_count_min": min(sql_counts),
                        "sql_count_max": max(sql_counts),
                        "sql_duration_ms_median": round(statistics.median(sql_durations), 3),
                    }
            finally:
                event.remove(db.engine, "before_cursor_execute", before_cursor_execute)
                event.remove(db.engine, "after_cursor_execute", after_cursor_execute)
                db.session.remove()
                db.drop_all()

        result = {
            "captured_at": "2026-07-16",
            "legacy_commit": "700006dfdfa063deb4387be572911e782bcea0d9",
            "environment": {
                "mode": "Flask testing profile with temporary SQLite",
                "python": sys.version.split()[0],
                "platform": sys.platform,
                "samples_per_endpoint": args.samples,
                "cache_state": "one in-process warm-up before each endpoint",
            },
            "safety": "No production or persistent local database; background tasks disabled; localhost network not used.",
            "startup": {
                "legacy_import_and_create_app_ms": round(startup_ms, 3),
                "rss_before_import_mib": rss_before_mib,
                "rss_after_create_app_mib": rss_after_app_mib,
                "rss_delta_mib": round(rss_after_app_mib - rss_before_mib, 3),
            },
            "requests": measurements,
            "limitations": [
                "Empty SQLite fixtures do not represent PostgreSQL query plans or production data scale.",
                "Numbers are regression orientation only, not the phase-9 performance acceptance baseline.",
            ],
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
