#!/usr/bin/env python3
"""Generate deterministic phase-0 inventories from the legacy Flask repository.

This tool is migration-only.  It requires an explicit legacy root and writes only
to the requested output directory under Ti-Java.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib
import inspect
import json
import logging
import os
import pkgutil
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


# Inventory imports the protected Flask tree; never leave bytecode artifacts there.
sys.dont_write_bytecode = True


ROUTE_FIELDS = [
    "route_id",
    "path",
    "methods",
    "endpoint",
    "legacy_module",
    "source",
    "registration_source",
    "registration_kind",
    "decorators",
    "inline_auth_signals",
    "auth_semantics",
    "client_surfaces",
    "client_references",
    "contract_source",
    "target_module",
    "migration_status",
    "compatibility_notes",
]

DATA_FIELDS = [
    "resource_kind",
    "resource_name",
    "legacy_owner",
    "legacy_source",
    "target_owner",
    "persistence_role",
    "constraints_or_pattern",
    "migration_status",
    "notes",
]


TABLE_OWNERS: dict[str, str] = {
    # identity
    "users": "identity",
    "email_verification_codes": "identity",
    "user_subjects": "identity",
    # catalog
    "subjects": "catalog",
    "questions": "catalog",
    "plaza_boards": "catalog",
    "public_bank_plaza_metrics": "catalog",
    "public_subject_users": "catalog",
    # personal bank
    "user_bank_categories": "personalbank",
    "user_question_banks": "personalbank",
    "user_bank_questions": "personalbank",
    "bank_shares": "personalbank",
    "bank_share_records": "personalbank",
    "public_bank_users": "personalbank",
    # learning
    "favorites": "learning",
    "mistakes": "learning",
    "user_answers": "learning",
    "user_progress": "learning",
    "user_checkins": "learning",
    "user_quiz_stats": "learning",
    "user_bank_answers": "learning",
    "user_bank_mistakes": "learning",
    "user_bank_favorites": "learning",
    "user_question_tag_items": "learning",
    "study_learning": "learning",
    "study_review": "learning",
    "reinforce_similar_cache": "learning",
    # assessment
    "exams": "assessment",
    "exam_questions": "assessment",
    "exam_templates": "assessment",
    # community
    "forum_boards": "community",
    "forum_posts": "community",
    "forum_comments": "community",
    "forum_likes": "community",
    "forum_favorites": "community",
    "forum_reactions": "community",
    "forum_poll_votes": "community",
    "forum_reports": "community",
    "forum_mentions": "community",
    "forum_uploads": "community",
    "forum_user_bans": "community",
    "user_follows": "community",
    # messaging
    "chat_conversations": "messaging",
    "chat_members": "messaging",
    "chat_messages": "messaging",
    "user_remarks": "messaging",
    "notifications": "messaging",
    "notification_dismissals": "messaging",
    "interaction_notifications": "messaging",
    # campus
    "edu_schedule_credentials": "campus",
    "edu_schedule_snapshots": "campus",
    "edu_grade_snapshots": "campus",
    "edu_grade_overview_snapshots": "campus",
    # coding
    "coding_subjects": "coding",
    "coding_questions": "coding",
    "code_submissions": "coding",
    "coding_statistics": "coding",
    "user_coding_stats": "coding",
    "code_drafts": "coding",
    # intelligence
    "ai_chat_sessions": "intelligence",
    "ai_chat_messages": "intelligence",
    "ai_change_records": "intelligence",
    # operations
    "system_config": "operations",
    "popups": "operations",
    "popup_dismissals": "operations",
    "popup_views": "operations",
    "backup_jobs": "operations",
    "duplicate_check_records": "operations",
    "schema_migrations": "operations",
    "alembic_version": "operations",
}


# This is deliberately independent from TABLE_OWNERS.  A legacy owner records
# the Flask area that currently reads/writes a table; it must not be inferred
# from the future bounded-context decision.
TABLE_LEGACY_OWNERS: dict[str, str] = {
    "users": "user/auth",
    "email_verification_codes": "auth",
    "user_subjects": "user/admin",
    "subjects": "quiz/admin",
    "questions": "quiz/admin",
    "plaza_boards": "user_bank",
    "public_bank_plaza_metrics": "user_bank",
    "public_subject_users": "user_bank",
    "user_bank_categories": "user_bank",
    "user_question_banks": "user_bank",
    "user_bank_questions": "user_bank",
    "bank_shares": "user_bank",
    "bank_share_records": "user_bank",
    "public_bank_users": "user_bank",
    "favorites": "quiz",
    "mistakes": "quiz",
    "user_answers": "quiz",
    "user_progress": "quiz/auth/user",
    "user_checkins": "user",
    "user_quiz_stats": "quiz",
    "user_bank_answers": "user_bank",
    "user_bank_mistakes": "user_bank",
    "user_bank_favorites": "user_bank",
    "user_question_tag_items": "quiz/user_bank",
    "study_learning": "quiz",
    "study_review": "quiz",
    "reinforce_similar_cache": "quiz",
    "exams": "exam",
    "exam_questions": "exam",
    "exam_templates": "exam",
    "forum_boards": "forum",
    "forum_posts": "forum",
    "forum_comments": "forum",
    "forum_likes": "forum",
    "forum_favorites": "forum",
    "forum_reactions": "forum",
    "forum_poll_votes": "forum",
    "forum_reports": "forum",
    "forum_mentions": "forum",
    "forum_uploads": "forum",
    "forum_user_bans": "forum",
    "user_follows": "forum",
    "chat_conversations": "chat",
    "chat_members": "chat",
    "chat_messages": "chat",
    "user_remarks": "chat",
    "notifications": "notifications/admin",
    "notification_dismissals": "notifications",
    "interaction_notifications": "forum",
    "edu_schedule_credentials": "edu_schedule",
    "edu_schedule_snapshots": "edu_schedule",
    "edu_grade_snapshots": "edu_schedule",
    "edu_grade_overview_snapshots": "edu_schedule",
    "coding_subjects": "coding",
    "coding_questions": "coding",
    "code_submissions": "coding",
    "coding_statistics": "coding",
    "user_coding_stats": "coding",
    "code_drafts": "coding",
    "ai_chat_sessions": "ai_chat",
    "ai_chat_messages": "ai_chat",
    "ai_change_records": "admin/ai",
    "system_config": "admin",
    "popups": "popups/admin",
    "popup_dismissals": "popups",
    "popup_views": "popups",
    "backup_jobs": "admin/backup",
    "duplicate_check_records": "admin",
    "schema_migrations": "system",
    "alembic_version": "alembic",
}


ADDITIONAL_TABLE_MIGRATION_SOURCES: dict[str, tuple[str, ...]] = {
    "forum_posts": (
        "migrations/versions/d1e2f3a4b5c6_add_forum_fulltext_search.py",
    ),
}


TABLE_PHYSICAL_FACTS: dict[str, str] = {
    "forum_posts": (
        "physical_columns=28; physical_extra_column="
        "search_vector tsvector GENERATED ALWAYS AS (...) STORED"
    ),
}


def external_resource(
    kind: str,
    name: str,
    legacy_owner: str,
    source: str,
    target_owner: str,
    role: str,
    pattern: str,
    notes: str,
) -> dict[str, str]:
    return {
        "resource_kind": kind,
        "resource_name": name,
        "legacy_owner": legacy_owner,
        "legacy_source": source,
        "target_owner": target_owner,
        "persistence_role": role,
        "constraints_or_pattern": pattern,
        "migration_status": "inventoried",
        "notes": notes,
    }


EXTERNAL_RESOURCES: list[dict[str, str]] = []

# ProgressKV namespaces are rows in PostgreSQL user_progress, not Redis keys.
_FIXED_PROGRESS_KV_OWNER_NOTE = (
    "System-scoped row is stored under KV_OWNER_USER_ID (default 1, otherwise "
    "the first user), not the business user; preserve or deliberately replace "
    "that ownership rule during migration."
)

for name, legacy_owner, owner, source, role, pattern, notes in (
    ("web_login_session:<sid>", "auth", "identity", "app/modules/auth/services/web_login_service.py", "short_lived_coordination", "JSON expires_at=20m", f"Read-time expiry only; no row/file cleanup found. {_FIXED_PROGRESS_KV_OWNER_NOTE}"),
    ("web_login_token:<token>", "auth", "identity", "app/modules/auth/services/web_login_service.py", "single_use_coordination", "JSON expires_at=30s", f"Single-use token; expired/consumed tokens are deleted only when consumed. {_FIXED_PROGRESS_KV_OWNER_NOTE}"),
    ("web_wechat_bind_session:<sid>", "auth", "identity", "app/modules/auth/services/web_login_service.py", "short_lived_coordination", "JSON expires_at=20m", f"Read-time expiry only; no row/file cleanup found. {_FIXED_PROGRESS_KV_OWNER_NOTE}"),
    ("wechat_temp_token:<token>", "auth", "identity", "app/modules/auth/services/web_login_service.py", "single_use_coordination", "JSON expires_at=5m", f"Sensitive single-use token; no periodic cleanup. {_FIXED_PROGRESS_KV_OWNER_NOTE}"),
    ("user_profile_extra_v1", "user", "identity", "app/modules/user/routes/api.py", "business_state", "no TTL", "Legacy profile extension document."),
    ("question_tags_v1", "quiz", "learning", "app/modules/quiz/services/question_tags_service.py", "legacy_compatibility_state", "no TTL", "Read-only compatibility source migrated on demand to user_question_tag_items; current writes no longer update this namespace."),
    ("bank_<bank_id>_tags", "user_bank", "personalbank", "app/modules/user_bank/routes/api_tags.py", "legacy_compatibility_state", "no TTL", "Read-only compatibility source migrated on demand to user_question_tag_items; current writes no longer update this namespace."),
    ("user_bank_duplicate_check:<bank_id>", "user_bank", "personalbank", "app/modules/user_bank/services/duplicate_check_service.py", "rebuildable_snapshot", "no TTL", "Rebuildable duplicate-check snapshot."),
    ("study_progress_<uid>_...", "quiz", "learning", "app/modules/quiz/routes/pages_helpers.py; app/modules/quiz/templates/quiz/partials/quiz/assets/js/_00_bootstrap.html", "business_state", "no TTL", "Study ordering/progress state."),
    ("quiz_progress_<uid>_...", "quiz", "learning", "app/modules/quiz/routes/pages_helpers.py; miniprogram-1/miniprogram/pages/quiz/quiz.ts", "business_state", "no TTL", "Public-bank and reinforce/quiz ordering and answer progress."),
    ("bank_quiz_progress_<uid>_...", "miniprogram/user_bank", "learning", "miniprogram-1/miniprogram/pages/quiz/quiz.ts", "business_state", "no TTL", "Miniprogram personal-bank quiz progress; intentionally owned with learning progress."),
    ("last_practice_session", "quiz/miniprogram", "learning", "app/modules/quiz/templates/quiz/partials/quiz/assets/js/_00_bootstrap.html; miniprogram-1/miniprogram/pages/quiz/quiz.ts", "business_state", "no TTL", "Cross-surface resume pointer for the most recent practice session."),
    ("user_settings_v1", "settings/miniprogram", "identity", "app/modules/main/templates/main/settings/theme.html; miniprogram-1/miniprogram/utils/user-settings.ts", "business_state", "no TTL", "Cross-surface user preferences; do not absorb into the generic learning namespace."),
    ("subject:overview", "development seed", "catalog", "scripts/严格初始化开发数据.py", "seed_state", "no TTL", "Initialization data."),
    ("<client_supplied_p_key>", "quiz API", "learning", "app/modules/quiz/routes/api_components/progress_tags_notifications.py", "unbounded_legacy_namespace", "no TTL; mixed/unknown namespace", "POST /api/progress accepts arbitrary client keys; inventory known keys explicitly and constrain this escape hatch during migration."),
):
    EXTERNAL_RESOURCES.append(
        external_resource(
            "db_kv_namespace",
            name,
            legacy_owner,
            f"{source}; app/models/quiz.py",
            owner,
            role,
            f"user_progress(user_id,p_key,data); unique(user_id,p_key); {pattern}",
            notes,
        )
    )

# Response-cache features all use cache:<feature>:<sha256(params)> in Redis DB 0.
for feature, owner, ttl in (
    ("chat:convs", "messaging", "5s"),
    ("forum:boards", "community", "300s"),
    ("data_center", "learning", "120s"),
    ("quiz:question_detail", "catalog", "300s"),
    ("quiz:questions_count", "catalog", "60s; production default 120s"),
    ("quiz:user_counts", "learning", "30s"),
    ("quiz:history", "learning", "30s"),
    ("quiz:subject_stats_detail", "learning", "30s"),
    ("quiz:subjects", "catalog", "60s; production default 300s"),
    ("quiz:subjects_meta", "catalog", "60s; production default 300s"),
    ("quiz:subject_info", "catalog", "subjects-meta TTL"),
    ("quiz:ai_explain", "intelligence", "30d default"),
):
    EXTERNAL_RESOURCES.append(
        external_resource(
            "redis_key",
            f"cache:{feature}:<sha256(params)>",
            "shared cache_utils",
            "app/core/utils/cache_utils.py",
            owner,
            "rebuildable_cache",
            f"Redis DB 0; TTL={ttl}",
            "Redis uses allkeys-lru; never treat cache content as final business truth.",
        )
    )

for name, owner in (
    ("cache:ver:quiz:questions", "catalog"),
    ("cache:ver:quiz:subjects", "catalog"),
    ("cache:ver:quiz:u:<user_id>", "learning"),
    ("cache:ver:chat:conv:<user_id>", "messaging"),
    ("cache:ver:forum:boards", "community"),
):
    EXTERNAL_RESOURCES.append(
        external_resource(
            "redis_key",
            name,
            "shared cache_utils",
            "app/core/utils/cache_utils.py",
            owner,
            "rebuildable_cache_version",
            "Redis DB 0; integer; no TTL",
            "Invalidation version only.",
        )
    )

for name, legacy_owner, source, owner, role, pattern, notes in (
    ("auth:user_state:<user_id>", "auth", "app/core/utils/user_state_cache.py", "identity", "rebuildable_auth_cache", "JSON; TTL 20s default; if configured as 0 the Redis key has no expiry and the process-local fallback is disabled", "Authoritative state remains PostgreSQL; zero is a configuration edge case, not the current default."),
    ("chat:unread:<user_id>", "chat", "app/core/utils/unread_counter.py", "messaging", "rebuildable_counter_cache", "Hash conversation_id->count; no TTL", "Rebuild from durable messages/read state."),
    ("ai_explain:result:<hash>", "quiz", "app/modules/quiz/routes/api_components/ai_jobs.py; app/tasks/ai_explain_tasks.py", "intelligence", "rebuildable_result_cache", "JSON; TTL 30d default", "The route defines/reads the key and the RQ task writes the result."),
    ("ai_explain:job:<hash>", "quiz", "app/modules/quiz/routes/api_components/ai_jobs.py", "intelligence", "idempotency_coordination", "job id; TTL 600s", "Enqueue de-duplication only."),
    ("sms:rate:<phone>", "auth", "app/modules/auth/services/sms_auth_service.py", "identity", "rate_limit", "nominal TTL 60s; INCR then EXPIRE are not atomic", "Never a delivery fact; a crash or EXPIRE failure can leave a non-expiring key."),
    ("sms:rate_hour:<phone>", "auth", "app/modules/auth/services/sms_auth_service.py", "identity", "rate_limit", "nominal TTL 3600s; INCR then EXPIRE are not atomic", "Never a delivery fact; a crash or EXPIRE failure can leave a non-expiring key."),
    ("sms:failed:<timestamp>", "auth", "app/tasks/sms_tasks.py", "operations", "failure_telemetry", "TTL 7d", "Masked failure telemetry."),
    ("email:failed:<timestamp>", "auth", "app/tasks/email_tasks.py", "operations", "failure_telemetry", "TTL 7d", "Masked failure telemetry."),
    ("edu_schedule:query_task:<task_id>", "edu_schedule", "app/modules/edu_schedule/services/query_tasks.py", "campus", "temporary_task_state", "JSON; TTL 1800s", "Credentials/job payload also live only in process memory, so Redis state cannot recover execution."),
    ("edu_schedule:user_query_tasks:<user_id>", "edu_schedule", "app/modules/edu_schedule/services/query_tasks.py", "campus", "temporary_task_index", "max 10 tasks; TTL 1800s", "Recent-task lookup index."),
    ("edu_schedule:query_dedupe:<sha256>", "edu_schedule", "app/modules/edu_schedule/services/query_tasks.py", "campus", "idempotency_coordination", "TTL 1800s", "Prevents duplicate fragile-upstream queries."),
    ("edu_schedule:grade_refresh_order:<user_id>:<account_key>", "edu_schedule", "app/modules/edu_schedule/services/query_tasks.py", "campus", "sequence_coordination", "integer; TTL 1800s", "Monotonic refresh order."),
    ("edu_schedule:webvpn_challenge:<challenge_id>", "edu_schedule", "app/modules/edu_schedule/services/webvpn_refresh.py", "campus", "short_lived_coordination", "encrypted cookies/token; TTL 300s", "Never report plaintext challenge material."),
    ("edu_schedule:upstream_slots", "edu_schedule", "app/modules/edu_schedule/services/upstream_executor.py", "campus", "concurrency_coordination", "Sorted Set; global limit 20; stale after 120s", "Protect fragile upstream."),
    ("plaza:metrics:refresh:lock", "public_bank", "app/modules/user_bank/services/plaza_metrics_service.py", "catalog", "distributed_lock", "SET NX EX 30s", "Rebuildable metrics refresh coordination."),
    ("LIMITS:*", "Flask-Limiter", "app/core/extensions.py", "operations", "library_managed_rate_limit", "version-dependent Redis keys", "Do not freeze library-internal key layout as a business contract."),
    ("rq:*", "RQ", "app/core/utils/rq_utils.py", "operations", "library_managed_queue_state", "queue/job/worker/registries; version-dependent", "Drain or explicitly abandon jobs before cutover."),
):
    EXTERNAL_RESOURCES.append(external_resource("redis_key", name, legacy_owner, source, owner, role, pattern, notes))

for name, source, pattern, notes in (
    ("RQ queue saksk", "compose.dev.yml; compose.prod.yml; app/core/utils/rq_utils.py", "AI explain, email, SMS; Compose worker listens this queue", "Stop producers and drain/reconcile before cutover."),
    ("RQ queue default", "app/modules/chat/routes/api.py; compose.dev.yml; compose.prod.yml", "chat audio transcode; direct Queue(connection=...) selects RQ default; Compose worker does not listen", "Known legacy risk: an accepted job can remain unconsumed while the message retains its raw-audio URL."),
):
    EXTERNAL_RESOURCES.append(external_resource("queue", name, "RQ", source, "operations", "transient_work_queue", pattern, notes))

for name, legacy_owner, source, owner, pattern, notes in (
    ("app.tasks.ai_explain_tasks.ai_explain_task", "quiz", "app/tasks/ai_explain_tasks.py", "intelligence", "saksk; timeout 120s; result/failure TTL 24h", "Stable idempotency key required in target."),
    ("app.tasks.email_tasks.send_email_task", "auth", "app/tasks/email_tasks.py", "identity", "saksk; retry 30/60/120s; timeout 120s; queue TTL 600s", "Final failure telemetry in Redis."),
    ("app.tasks.sms_tasks.send_sms_task", "auth", "app/tasks/sms_tasks.py", "identity", "saksk; retry 10/30s; timeout 30s", "Final failure telemetry in Redis."),
    ("app.modules.chat.tasks.transcode_audio_task", "chat", "app/modules/chat/routes/api.py; app/modules/chat/tasks.py", "messaging", "default queue; bypasses RQ_DISABLED", "No current Compose consumer for default queue; synchronous fallback happens only when enqueue fails."),
):
    EXTERNAL_RESOURCES.append(external_resource("queue_task", name, legacy_owner, source, owner, "background_command", pattern, notes))

for name, legacy_owner, source, owner, pattern, notes in (
    ("expired email verification cleanup", "auth", "app/core/tasks.py", "identity", "startup then hourly; once per Gunicorn worker", "Production default 2 workers can run duplicate cleaners."),
    ("orphan forum upload cleanup", "forum", "app/core/tasks.py; app/modules/forum/services/upload_service.py", "community", "startup then hourly; 24h orphan threshold", "Must remain idempotent under concurrent workers."),
    ("R2 backup scheduler", "admin/backup", "app/tasks/backup_scheduler.py; app/modules/admin/services/backup_job_service.py", "operations", "sidecar polls every 60s; always recovers stale jobs/retries deletion/executes queued jobs; only scheduled-job creation is disabled by default; cron default 02:00", "Current local container still runs the older backup-cron.sh image/config."),
    ("campus schedule/grade query", "edu_schedule", "app/modules/edu_schedule/services/query_tasks.py", "campus", "per-request daemon thread; unbounded attempts; backoff 5/20/60/120/300s", "_QUERY_TASK_MAX_ATTEMPTS=None; process restart cannot recover in-memory credentials/job payload."),
    ("SSE Redis subscriber", "core SSE", "app/core/sse/event_bus.py", "messaging", "lazy daemon thread per process", "In-memory fallback queue size 64 may drop events."),
    ("backup lease heartbeat", "admin/backup", "app/modules/admin/services/backup_job_service.py", "operations", "thread per active backup job", "Lease state must be observable and recoverable."),
):
    EXTERNAL_RESOURCES.append(external_resource("scheduled_or_background_task", name, legacy_owner, source, owner, "background_process", pattern, notes))

EXTERNAL_RESOURCES.extend(
    [
        external_resource("realtime_channel", "sse:events", "core SSE", "app/core/sse/event_bus.py; app/core/sse/routes.py; app/core/config.py", "messaging", "ephemeral_delivery", "Redis Pub/Sub; connected,reconnect,chat_message,chat_unread,chat_message_revoked,interact_unread,notif_unread", "Heartbeat is an SSE comment, not an event; PostgreSQL retains facts; ProductionConfig disables SSE by default."),
        external_resource("realtime_channel", "AI chat response stream", "ai_chat", "app/modules/ai_chat/routes/api.py; app/modules/ai_chat/services/ai_chat_service.py", "intelligence", "ephemeral_delivery", "direct HTTP SSE events meta,delta,done,error", "Does not use sse:events."),
    ]
)

for name, legacy_owner, source, owner, role, pattern, notes in (
    ("uploads/avatars/", "user", "app/modules/user/routes/api.py", "identity", "durable_file", "generated filename; extension allowlist only; no size/MIME/magic-byte validation", "Replacing an avatar deletes the previous local file; preserve public URL behavior and record the legacy validation gap."),
    ("uploads/bank_covers/", "user_bank", "app/modules/user_bank/routes/api_uploads.py", "personalbank", "durable_file", "5MB maximum; extension+MIME+magic-byte checks; realpath boundary", "No general orphan cleanup found for superseded cover files."),
    ("uploads/question_images/", "admin/quiz", "app/modules/admin/routes/api_components/questions_io.py; app/modules/admin/routes/api_legacy.py", "catalog", "durable_file", "extension allowlist only (including SVG); secure filename; no size/MIME/magic-byte validation", "No general orphan cleanup found; retain the validation difference as a compatibility/security decision."),
    ("uploads/user_bank_question_images/", "user_bank", "app/modules/user_bank/routes/api_uploads.py", "personalbank", "durable_file", "5MB maximum; extension+MIME+magic-byte checks; realpath boundary", "Separate from catalog images; no general orphan cleanup found."),
    ("uploads/questions/", "main", "app/__init__.py", "catalog", "legacy_compatibility_file", "read allowlist; writer not confirmed", "Retain only while compatibility evidence requires it."),
    ("uploads/forum/", "forum", "app/modules/forum/services/upload_service.py", "community", "durable_file", "forum_uploads association; 24h orphan cleanup", "Preserve attachment authorization."),
    ("uploads/chat/", "chat", "app/modules/chat/routes/api.py; app/modules/chat/tasks.py", "messaging", "durable_file", "images, thumbnails, raw audio, m4a/mp3", "Conversion may use an isolated worker command; no general orphan cleanup was found."),
    ("uploads/web_login/", "auth", "app/modules/auth/services/web_login_service.py", "identity", "short_lived_file", "unguessable QR filename; no cleanup found", "Do not claim a TTL that legacy does not enforce."),
    ("uploads/wechat_bind/", "auth", "app/modules/auth/services/web_login_service.py", "identity", "short_lived_file", "unguessable QR filename; no cleanup found", "Do not claim a TTL that legacy does not enforce."),
    ("R2 <configured-prefix>/backup_*.tar.gz", "admin/backup", "app/modules/admin/services/backup_archive_service.py; app/modules/admin/services/backup_storage_service.py; app/tasks/backup_scheduler.py", "operations", "durable_backup_archive", "default backups/; retention 14d and max 3; checksums", "Restore rehearsal required."),
    ("R2 <configured-prefix>/.healthcheck/<uuid>.txt", "admin/backup", "app/modules/admin/services/backup_storage_service.py", "operations", "temporary_healthcheck_object", "create/read/delete health probe", "Never persist credentials in the probe."),
):
    EXTERNAL_RESOURCES.append(external_resource("object_prefix", name, legacy_owner, source, owner, role, pattern, notes))

for name, legacy_owner, source, owner, pattern, notes in (
    ("OpenAI-compatible /models,/chat/completions,/responses", "quiz/ai_chat", "app/modules/quiz/services; app/modules/ai_chat/services", "intelligence", "configurable HTTPS base URL; streaming supported", "Ordinary model HTTP remains Java; apply egress/SSRF policy and redact prompts/keys."),
    ("WeChat jscode2session/token/getwxacodeunlimit", "auth", "app/modules/auth/services", "identity", "AppID/secret; HTTPS", "Never inventory real secrets."),
    ("SMTP email", "auth", "app/core/utils/email_service.py; app/tasks/email_tasks.py", "identity", "timeouts; masked config; idempotent delivery", "Configuration administration remains operations-owned."),
    ("Aliyun DYPNS SMS", "auth", "app/core/utils/sms_service.py; app/tasks/sms_tasks.py", "identity", "SendSmsVerifyCode/CheckSmsVerifyCode", "Configuration administration remains operations-owned."),
    ("SYN U WebVPN/JWXT", "edu_schedule", "app/modules/edu_schedule/services", "campus", "low concurrency; timeout; backoff; circuit breaker; snapshot fallback", "Existing encrypted credentials must remain decryptable."),
    ("Cloudflare R2 S3 API", "admin/backup", "app/modules/admin/services/backup_storage_service.py", "operations", "configurable bucket/prefix; 300s presigned download", "Encrypted credentials and restore validation required."),
    ("Epay submit/query/order", "payment/admin", "app/modules/payment/services/epay_service.py", "operations", "configurable HTTP(S) endpoint; signed requests", "No payment ORM table found; approve egress/SSRF allowlist decision."),
    ("Sentry SDK/DSN", "platform", "app/__init__.py; app/core/config.py", "operations", "optional telemetry endpoint", "Redact credentials and user-sensitive context."),
    ("browser export extension: Chaoxing/PTA/Yuketang", "export_extension", "app/modules/main/resources/export_extension/manifest.json; app/modules/main/resources/export_extension/content/xuexitong-export.js; app/modules/main/resources/export_extension/content/pta-export.js", "web", "content-script host permissions for Chaoxing/Pintia/Yuketang; authenticated Chaoxing activity/result GETs; Yuketang show_paper GET; PTA DOM extraction", "Runs in the user's browser with the learning site's cookies and page access; treat host permissions and extracted question data as an explicit integration contract."),
    ("browser CDN/fonts", "Jinja web", "app/modules/**/templates", "web", "Google Fonts/jsDelivr/Toast UI and similar", "Ancillary runtime dependency; vendor or define availability policy."),
):
    EXTERNAL_RESOURCES.append(external_resource("external_api", name, legacy_owner, source, owner, "external_integration", pattern, notes))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def relative_source(path: str | None, legacy_root: Path) -> str:
    if not path:
        return "unknown"
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(legacy_root).as_posix()
    except ValueError:
        return f"framework:{resolved.name}"


def decorator_metadata(view: Any, legacy_root: Path) -> tuple[str, int, list[str], list[str]]:
    original = inspect.unwrap(view)
    source_file = inspect.getsourcefile(original)
    if not source_file:
        return "unknown", 0, [], []
    try:
        _, line = inspect.getsourcelines(original)
    except (OSError, TypeError):
        line = 0
    source = relative_source(source_file, legacy_root)
    if not str(Path(source_file).resolve()).startswith(str(legacy_root)):
        return source, line, [], []
    try:
        tree = ast.parse(Path(source_file).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return source, line, [], []
    candidates: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == getattr(original, "__name__", ""):
                candidates.append(node)
    if not candidates:
        return source, line, [], []
    def decorator_start(item: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        return min((decorator.lineno for decorator in item.decorator_list), default=item.lineno)

    node = min(candidates, key=lambda item: (decorator_start(item) != line, abs(decorator_start(item) - line)))

    def decorator_name(item: ast.expr) -> str:
        target = item.func if isinstance(item, ast.Call) else item
        if isinstance(target, ast.Attribute):
            return target.attr
        if isinstance(target, ast.Name):
            return target.id
        return ""

    route_decorators = {"route", "get", "post", "put", "delete", "patch"}
    decorators = [
        ast.unparse(item)
        for item in node.decorator_list
        if decorator_name(item).lower() not in route_decorators
    ]
    names = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
    constants = {
        str(item.value).lower()
        for item in ast.walk(node)
        if isinstance(item, ast.Constant) and isinstance(item.value, (str, int))
    }
    signals: list[str] = []
    if "session" in names:
        signals.append("session_reference")
    if names & {"current_user_id", "_get_uid_from_request", "get_current_user"}:
        signals.append("current_user_resolution")
    if "jwt" in " ".join(names).lower() or any("authorization" in value for value in constants):
        signals.append("jwt_or_authorization_reference")
    if "401" in constants or any("unauthorized" in value for value in constants):
        signals.append("unauthorized_response_signal")
    if "403" in constants or any("forbidden" in value or "权限" in value for value in constants):
        signals.append("forbidden_response_signal")
    return source, line, decorators, signals


ANONYMOUS_ALLOW_EXACT = {
    "/",
    "/hub",
    "/login",
    "/favicon.ico",
    "/public/banks",
    "/terms",
    "/privacy",
    "/api/ping",
    "/api/login",
    "/api/auth/login-methods",
    "/api/public/banks",
    "/api/wechat/login",
    "/api/wechat/create",
    "/api/wechat/bind",
    "/api/wechat/bind/send_code",
    "/api/wechat/bind_confirm",
    "/api/mini/login",
    "/api/mini/email/send-login-code",
    "/api/mini/email/login",
    "/api/email/send-login-code",
    "/api/email/login",
    "/api/forgot-password/send-code",
    "/api/forgot-password/reset",
    "/api/sms/send-login-code",
    "/api/sms/login",
    "/api/sms/forgot-password/send-code",
    "/api/sms/forgot-password/reset",
}

CSRF_EXEMPT_EXACT = ANONYMOUS_ALLOW_EXACT & {
    path for path in ANONYMOUS_ALLOW_EXACT if path.startswith("/api/")
}
CSRF_EXEMPT_EXACT.update({"/api/sms/send-bind-code", "/api/sms/bind"})


def global_anonymous_gate(path: str, endpoint: str) -> str:
    if endpoint == "static" or path.startswith("/static") or path.endswith(".ico") or path == "/api/ping":
        return "global_anonymous_allow_fast_path"
    if path in ANONYMOUS_ALLOW_EXACT:
        return "global_anonymous_allow_exact"
    if path.startswith("/admin/api/ai-change-records"):
        return "global_record_token_or_bearer_bypass_else_login_redirect"
    if path.startswith("/api/public/banks/"):
        return "global_anonymous_allow_public_bank_prefix"
    if path.startswith("/api/web_login/"):
        return "global_anonymous_allow_web_login_prefix"
    if path.startswith(("/uploads/web_login/", "/uploads/wechat_bind/")):
        return "global_anonymous_allow_qr_file_prefix"
    if path.startswith(("/uploads/avatars/", "/uploads/bank_covers/", "/uploads/question_images/", "/uploads/questions/")):
        return "global_anonymous_allow_only_common_image_extension"
    if path == "/api/questions/count":
        return "global_anonymous_allow_except_mode_favorites_or_mistakes_returns_401"
    if path == "/api/questions/user_counts":
        return "global_anonymous_allow_returns_zero_counts"
    if path == "/notifications":
        return "global_anonymous_returns_401"
    if path.startswith("/api/notifications"):
        return "global_anonymous_allow_notification_route_inline_policy"
    for prefix in ("/quiz", "/exams", "/profile", "/search", "/coding"):
        if path.startswith(prefix):
            return "global_anonymous_login_redirect"
    for prefix in ("/api/favorite", "/api/record_result", "/api/progress", "/api/exams", "/coding/api"):
        if path.startswith(prefix):
            return "global_session_or_valid_jwt_else_401"
    if path.startswith("/api"):
        return "global_session_or_valid_jwt_else_401"
    if path in {
        "/admin/api/settings/backup",
        "/admin/api/settings/backup/test",
        "/admin/api/backups",
    } or path.startswith("/admin/api/backups/"):
        return "global_session_or_valid_jwt_else_backup_error_401"
    return "global_anonymous_login_redirect"


def auth_semantics(path: str, methods: Iterable[str], decorators: Iterable[str], endpoint: str) -> str:
    decorator_names = {
        item.split("(", 1)[0].rsplit(".", 1)[-1].strip().lower()
        for item in decorators
    }
    semantics: list[str] = []
    write_methods = sorted(set(methods) & {"POST", "PUT", "DELETE", "PATCH"})
    if path.startswith("/api") and write_methods and path not in CSRF_EXEMPT_EXACT:
        semantics.append(f"global_write_csrf_for_{'+'.join(write_methods)}:valid_jwt_or_xhr_required")
    semantics.append(global_anonymous_gate(path, endpoint))
    if endpoint.startswith("admin."):
        semantics.append("admin_blueprint_hook:session_or_jwt_plus_role_if_global_gate_passes")
    mapping = (
        ("subject_admin_required", "session+subject_admin_role"),
        ("notification_admin_required", "session+notification_admin_role"),
        ("session_admin_required", "session+admin_role"),
        ("admin_required", "session+admin_role"),
        ("_record_auth_required", "record_token_or_bearer"),
        ("jwt_required", "jwt"),
        ("auth_required", "session_or_jwt"),
        ("login_required", "session"),
    )
    route_semantics = [label for name, label in mapping if name in decorator_names]
    semantics.extend(f"route_decorator:{label}" for label in route_semantics)
    if not route_semantics:
        semantics.append("route_auth:none")
    return json.dumps(list(dict.fromkeys(semantics)), ensure_ascii=False, separators=(",", ":"))


def legacy_module(endpoint: str, source: str) -> str:
    if endpoint == "static":
        return "framework"
    if source.startswith("app/__init__.py"):
        return "application"
    prefix = endpoint.split(".", 1)[0]
    if prefix.startswith("api_"):
        return "quiz_alias"
    match = re.search(r"app/modules/([^/]+)/", source)
    return match.group(1) if match else prefix


def target_module(path: str, endpoint: str, legacy: str) -> str:
    lowered = f"{path} {endpoint} {legacy}".lower()
    handler = endpoint.rsplit(".", 1)[-1]
    handler_overrides = {
        "api_grade_subjective": "learning",
        "api_job_status": "intelligence",
        "progress_api": "learning",
        "api_progress": "learning",
        "api_questions_count": "catalog",
        "api_user_counts": "learning",
        "api_questions_user_counts": "learning",
        "record_result": "learning",
        "api_record_result": "learning",
        "user_checkin": "learning",
        "user_checkin_status": "learning",
        "user_last_practice": "learning",
        "user_stats": "learning",
        "stats_daily": "learning",
        "stats_by_subject": "learning",
        "stats_by_type": "learning",
        "get_user_quiz_stats": "learning",
        "api_user_favorites": "community",
        "api_user_likes": "community",
        "api_user_works": "community",
    }
    if handler in handler_overrides:
        return handler_overrides[handler]
    if endpoint == "static" or path.startswith("/static/"):
        return "web"
    if any(token in lowered for token in ("edu-schedule", "edu_schedule", "edu-grades", "campus")):
        return "campus"
    if any(token in lowered for token in ("ai-chat", "ai_chat", "/ai/", "ai_explain", "ai-change", "ai_change")):
        return "intelligence"
    if "/coding" in lowered or "coding" in legacy:
        return "coding"
    if any(token in lowered for token in ("/chat", "notification", "/sse")):
        return "messaging"
    if any(token in lowered for token in ("/forum", "/community", "follow", "reaction", "mention")):
        return "community"
    if "/exams" in lowered or legacy == "exam":
        return "assessment"
    if "/public/banks" in path and not any(token in path for token in ("/join", "/joined")):
        return "catalog"
    if "user_bank" in legacy or "/user/banks" in path:
        return "personalbank"
    if path.startswith("/admin") or any(token in lowered for token in ("popup", "payment", "backup", "system_config")):
        return "operations"
    if legacy == "auth" or any(token in lowered for token in ("/login", "/logout", "/profile", "/account", "/wechat", "/email", "/sms")):
        return "identity"
    if any(token in lowered for token in ("/study", "/quiz", "/data", "/favorite", "/mistake", "/history", "/review", "/tags")):
        return "learning"
    if any(token in lowered for token in ("subject", "question", "search", "plaza")):
        return "catalog"
    if legacy in {"main", "user"}:
        return "identity"
    return "operations"


def registration_metadata(path: str, endpoint: str, source: str) -> tuple[str, str]:
    if endpoint == "static":
        return "Flask automatic static rule", "framework_static"
    if endpoint == "api_ping":
        return "app/__init__.py::_register_health_endpoints", "application_decorator"
    if endpoint.startswith("user_bank_api_root."):
        return "app/modules/user_bank/__init__.py::user_bank_api_root", "blueprint_compatibility_alias"
    if "." not in endpoint and endpoint.startswith("api_"):
        return "app/modules/quiz/__init__.py::add_url_rule", "application_compatibility_alias"
    if source.startswith("app/__init__.py"):
        return source, "application_rule"
    return source, "blueprint_decorator"


def candidate_client_files(legacy_root: Path) -> list[tuple[str, Path, str]]:
    roots = [legacy_root / "templates", legacy_root / "static", legacy_root / "app" / "modules"]
    files: list[tuple[str, Path, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".html", ".js", ".ts"}:
                continue
            if any(part in {"node_modules", "_archived", ".git"} for part in path.parts):
                continue
            if path.stat().st_size > 350_000:
                continue
            if "app/modules" in path.as_posix() and "templates" not in path.parts and "static" not in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            files.append(("web", path, text))
    for surface, root, suffixes in (
        ("tests", legacy_root / "tests", {".py", ".js", ".ts"}),
    ):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            if any(part in {"node_modules", "_archived", ".git"} for part in path.parts):
                continue
            if path.stat().st_size > 350_000:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            files.append((surface, path, text))
    return files


def miniprogram_calls(legacy_root: Path) -> list[tuple[str, str, str]]:
    endpoint_file = legacy_root / "miniprogram-1" / "miniprogram" / "utils" / "api-endpoints.ts"
    source = endpoint_file.read_text(encoding="utf-8")
    request_pattern = re.compile(
        r"\brequest\(\s*([`'\"])(.*?)\1\s*,\s*['\"](GET|POST|PUT|DELETE)['\"]",
        re.S,
    )
    calls: list[tuple[str, str, str]] = []
    for match in request_pattern.finditer(source):
        relative = match.group(2).split("?", 1)[0]
        line = source.count("\n", 0, match.start()) + 1
        calls.append((f"/api{relative}", match.group(3), f"miniprogram-1/miniprogram/utils/api-endpoints.ts:{line}:request"))

    def add_direct(relative_file: str, marker: str, path: str, method: str, evidence: str) -> None:
        direct_file = legacy_root / relative_file
        direct_source = direct_file.read_text(encoding="utf-8")
        position = direct_source.find(marker)
        if position < 0:
            raise RuntimeError(f"Missing expected miniprogram direct call marker: {relative_file}: {marker}")
        line = direct_source.count("\n", 0, position) + 1
        calls.append((path, method, f"{relative_file}:{line}:{evidence}"))

    add_direct(
        "miniprogram-1/miniprogram/utils/api-endpoints.ts",
        "`${apiBaseUrl}/profile/avatar`",
        "/api/profile/avatar",
        "POST",
        "wx.uploadFile",
    )
    add_direct(
        "miniprogram-1/miniprogram/pages/dev-settings/dev-settings.ts",
        "`${apiUrl}/ping`",
        "/api/ping",
        "GET",
        "wx.request",
    )
    add_direct(
        "miniprogram-1/miniprogram/pages/subject-detail-v2/subject-detail-v2.ts",
        "`${baseUrl}/subjects/${subjectId}/export?${params.join('&')}`",
        "/api/subjects/${subjectId}/export",
        "GET",
        "wx.downloadFile",
    )
    return calls


def literal_matches_rule(call_path: str, rule_path: str) -> bool:
    """Match a concrete client path while respecting common Flask converters."""
    call_path = call_path.rstrip("/") or "/"
    rule_path = rule_path.rstrip("/") or "/"
    converter_patterns = {
        "int": r"\d+",
        "float": r"\d+(?:\.\d+)?",
        "uuid": r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
        "path": r".+",
        "string": r"[^/]+",
        "default": r"[^/]+",
    }
    parts: list[str] = []
    cursor = 0
    variable = re.compile(r"<(?:(?P<converter>[^:>]+):)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)>")
    for match in variable.finditer(rule_path):
        parts.append(re.escape(rule_path[cursor : match.start()]))
        converter = (match.group("converter") or "default").strip()
        base_converter = converter.split("(", 1)[0]
        if base_converter == "any" and "(" in converter and converter.endswith(")"):
            choices = [choice.strip() for choice in converter[converter.index("(") + 1 : -1].split(",")]
            parts.append("(?:" + "|".join(re.escape(choice) for choice in choices if choice) + ")")
        else:
            parts.append(f"(?:{converter_patterns.get(base_converter, converter_patterns['default'])})")
        cursor = match.end()
    parts.append(re.escape(rule_path[cursor:]))
    return re.fullmatch("".join(parts), call_path) is not None


def structurally_matches(call_path: str, rule_path: str) -> bool:
    has_template_placeholder = "{" in call_path and "}" in call_path
    if not has_template_placeholder:
        return literal_matches_rule(call_path, rule_path)
    call_parts = [part for part in call_path.strip("/").split("/") if part]
    rule_parts = [part for part in rule_path.strip("/").split("/") if part]
    if len(call_parts) != len(rule_parts):
        return False
    for call_part, rule_part in zip(call_parts, rule_parts):
        call_dynamic = "{" in call_part and "}" in call_part
        rule_dynamic = rule_part.startswith("<") and rule_part.endswith(">")
        if call_dynamic and not rule_dynamic:
            return False
        if not call_dynamic and not rule_dynamic and call_part != rule_part:
            return False
    return True


def balanced_call_expression(source: str, open_paren: int) -> str:
    """Return one JavaScript call expression without scanning into the next call."""
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = open_paren
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if character in "\r\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if character == "*" and following == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character == "/" and following == "/":
            line_comment = True
            index += 2
            continue
        if character == "/" and following == "*":
            block_comment = True
            index += 2
            continue
        if character in {"'", '"', "`"}:
            quote = character
            index += 1
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return source[open_paren : index + 1]
        index += 1
    return source[open_paren:]


def select_rule(rules: list[Any], call_path: str, method: str) -> Any | None:
    exact = [rule for rule in rules if rule.rule == call_path and method in rule.methods]
    if exact:
        return exact[0]
    order = {id(rule): index for index, rule in enumerate(rules)}
    candidates = [
        rule
        for rule in rules
        if method in rule.methods and structurally_matches(call_path, rule.rule)
    ]
    candidates.sort(
        key=lambda rule: (
            -sum(
                not (part.startswith("<") and part.endswith(">"))
                for part in rule.rule.strip("/").split("/")
            ),
            order[id(rule)],
        )
    )
    return candidates[0] if candidates else None


def miniprogram_call_index(app: Any, legacy_root: Path) -> tuple[dict[tuple[str, str, str], list[str]], int]:
    rules = list(app.url_map.iter_rules())
    index: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    missing: list[str] = []
    for call_path, method, source in miniprogram_calls(legacy_root):
        selected = select_rule(rules, call_path, method)
        if selected is None:
            missing.append(f"{method} {call_path} ({source})")
            continue
        index[(selected.rule, selected.endpoint, method)].append(source)
    if missing:
        raise RuntimeError("Unmapped miniprogram calls:\n" + "\n".join(missing))
    unique_calls = len({(path, method) for path, method, _source in miniprogram_calls(legacy_root)})
    return index, unique_calls


def normalize_client_path(value: str) -> str | None:
    path = value.strip().replace("\\/", "/")
    if path.startswith(("http://", "https://", "//")):
        return None
    path = path.split("?", 1)[0].split("#", 1)[0]
    return path if path.startswith("/") else None


def source_reference(path: Path, text: str, position: int, legacy_root: Path, evidence: str) -> str:
    line = text.count("\n", 0, position) + 1
    return f"{path.relative_to(legacy_root).as_posix()}:{line}:{evidence}"


def extract_path_calls(
    surface: str,
    path: Path,
    source: str,
    legacy_root: Path,
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str]]]:
    calls: list[tuple[str, str, str]] = []
    endpoint_refs: list[tuple[str, str]] = []

    if surface == "tests":
        test_call = re.compile(
            r"\.(get|post|put|delete|patch)\(\s*(?:f|r|fr|rf)?([`'\"])(/[^`'\"]*)\2",
            re.I,
        )
        for match in test_call.finditer(source):
            call_path = normalize_client_path(match.group(3))
            if call_path:
                calls.append(
                    (
                        call_path,
                        match.group(1).upper(),
                        source_reference(path, source, match.start(), legacy_root, "test_client_literal"),
                    )
                )
        open_call = re.compile(
            r"\.open\(\s*(?:f|r|fr|rf)?([`'\"])(/[^`'\"]*)\1(?P<body>.{0,500}?)method\s*=\s*['\"](GET|POST|PUT|DELETE|PATCH)['\"]",
            re.I | re.S,
        )
        for match in open_call.finditer(source):
            call_path = normalize_client_path(match.group(2))
            if call_path:
                calls.append(
                    (
                        call_path,
                        match.group(4).upper(),
                        source_reference(path, source, match.start(), legacy_root, "test_client_open_literal"),
                    )
                )
        return calls, endpoint_refs

    url_for_pattern = re.compile(r"\burl_for\(\s*['\"]([^'\"]+)['\"]")
    for match in url_for_pattern.finditer(source):
        endpoint_refs.append(
            (
                match.group(1),
                source_reference(path, source, match.start(), legacy_root, "url_for_endpoint"),
            )
        )

    fetch_pattern = re.compile(r"\bfetch\(\s*([`'\"])(/[^`'\"]*)\1", re.S)
    for match in fetch_pattern.finditer(source):
        call_path = normalize_client_path(match.group(2))
        if not call_path:
            continue
        open_paren = source.find("(", match.start(), match.end())
        expression = balanced_call_expression(source, open_paren)
        method_match = re.search(
            r"\bmethod\s*:\s*['\"](GET|POST|PUT|DELETE|PATCH)['\"]",
            expression,
            re.I,
        )
        method = method_match.group(1).upper() if method_match else "GET"
        calls.append(
            (call_path, method, source_reference(path, source, match.start(), legacy_root, "fetch_literal"))
        )

    method_call = re.compile(
        r"(?:axios|\$)\.(get|post|put|delete|patch)\(\s*([`'\"])(/[^`'\"]*)\2",
        re.I,
    )
    for match in method_call.finditer(source):
        call_path = normalize_client_path(match.group(3))
        if call_path:
            calls.append(
                (
                    call_path,
                    match.group(1).upper(),
                    source_reference(path, source, match.start(), legacy_root, "http_client_literal"),
                )
            )

    event_source = re.compile(r"\bEventSource\(\s*([`'\"])(/[^`'\"]*)\1")
    for match in event_source.finditer(source):
        call_path = normalize_client_path(match.group(2))
        if call_path:
            calls.append(
                (call_path, "GET", source_reference(path, source, match.start(), legacy_root, "event_source_literal"))
            )

    for match in re.finditer(r"<form\b[^>]*>", source, re.I | re.S):
        tag = match.group(0)
        action = re.search(r"\baction\s*=\s*['\"](/[^'\"]*)['\"]", tag, re.I)
        if not action:
            continue
        call_path = normalize_client_path(action.group(1))
        method_match = re.search(r"\bmethod\s*=\s*['\"](GET|POST)['\"]", tag, re.I)
        if call_path:
            calls.append(
                (
                    call_path,
                    method_match.group(1).upper() if method_match else "GET",
                    source_reference(path, source, match.start(), legacy_root, "form_action_literal"),
                )
            )

    navigation = re.compile(
        r"(?:\bhref\s*=|\b(?:window\.)?location(?:\.href)?\s*=)\s*['\"](/[^'\"]*)['\"]",
        re.I,
    )
    for match in navigation.finditer(source):
        call_path = normalize_client_path(match.group(1))
        if call_path:
            calls.append(
                (call_path, "GET", source_reference(path, source, match.start(), legacy_root, "navigation_literal"))
            )
    return calls, endpoint_refs


def static_client_indexes(
    app: Any,
    files: list[tuple[str, Path, str]],
    legacy_root: Path,
) -> tuple[dict[tuple[str, str, str], list[tuple[str, str]]], dict[str, list[tuple[str, str]]]]:
    rules = list(app.url_map.iter_rules())
    path_index: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    endpoint_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for surface, path, source in files:
        calls, endpoint_refs = extract_path_calls(surface, path, source, legacy_root)
        for call_path, method, reference in calls:
            selected = select_rule(rules, call_path, method)
            if selected is not None:
                path_index[(selected.rule, selected.endpoint, method)].append((surface, reference))
        for endpoint, reference in endpoint_refs:
            if endpoint in app.view_functions:
                endpoint_index[endpoint].append((surface, reference))
    return path_index, endpoint_index


def discover_clients(
    rule: str,
    endpoint: str,
    methods: list[str],
    mini_index: dict[tuple[str, str, str], list[str]],
    static_index: dict[tuple[str, str, str], list[tuple[str, str]]],
    endpoint_index: dict[str, list[tuple[str, str]]],
) -> tuple[str, str]:
    refs: dict[str, list[str]] = defaultdict(list)
    for method in methods:
        sources = mini_index.get((rule, endpoint, method), [])
        if sources:
            refs["miniprogram"].extend(sources)
        for surface, reference in static_index.get((rule, endpoint, method), []):
            refs[surface].append(reference)
    for surface, reference in endpoint_index.get(endpoint, []):
        refs[surface].append(reference)
    surfaces = ";".join(sorted(refs)) if refs else "not_found_static_scan"
    rendered = {surface: sorted(set(values)) for surface, values in sorted(refs.items())}
    return (
        surfaces,
        json.dumps(rendered, ensure_ascii=False, separators=(",", ":"))
        if rendered
        else "not_found_static_scan",
    )


def route_compatibility_notes(path: str, endpoint: str, methods: list[str]) -> str:
    notes = ["preserve path/method/status/envelope/auth/null/pagination"]
    if path == "/profile" and "GET" in methods:
        if endpoint == "main.main_pages.profile_page":
            notes.append("legacy collision effective winner: registered first")
        else:
            notes.append("legacy collision unreachable/shadowed endpoint: registered second")
    if path in {"/api/mini/forgot-password/send-code", "/api/mini/forgot-password/reset"}:
        notes.append("legacy defect: miniprogram sends neither JWT nor XHR; CSRF hook returns 403 first; login gate would then return 401; route comment claims anonymous use; correction requires ADR")
    if endpoint.startswith("coding_admin."):
        notes.append("independent blueprint; does not inherit admin blueprint before_request hook")
    if endpoint.endswith(".api_user_works"):
        notes.append("cross-module read facade over personalbank and community data; target owner is community pending ADR")
    return "; ".join(notes)


def write_routes(app: Any, legacy_root: Path, output: Path) -> list[dict[str, str]]:
    client_files = candidate_client_files(legacy_root)
    mini_index, _unique_calls = miniprogram_call_index(app, legacy_root)
    static_index, endpoint_index = static_client_indexes(app, client_files, legacy_root)
    rows: list[dict[str, str]] = []
    rules = sorted(app.url_map.iter_rules(), key=lambda item: (item.rule, item.endpoint, sorted(item.methods)))
    for rule in rules:
        methods = sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
        view = app.view_functions[rule.endpoint]
        source_file, line, decorators, inline_auth_signals = decorator_metadata(view, legacy_root)
        source = f"{source_file}:{line}" if line else source_file
        legacy = legacy_module(rule.endpoint, source_file)
        registration_source, registration_kind = registration_metadata(rule.rule, rule.endpoint, source)
        clients, client_refs = discover_clients(
            rule.rule,
            rule.endpoint,
            methods,
            mini_index,
            static_index,
            endpoint_index,
        )
        route_key = f"{','.join(methods)} {rule.rule} {rule.endpoint}"
        rows.append(
            {
                "route_id": hashlib.sha1(route_key.encode("utf-8")).hexdigest()[:12],
                "path": rule.rule,
                "methods": ",".join(methods),
                "endpoint": rule.endpoint,
                "legacy_module": legacy,
                "source": source,
                "registration_source": registration_source,
                "registration_kind": registration_kind,
                "decorators": json.dumps(decorators, ensure_ascii=False, separators=(",", ":")),
                "inline_auth_signals": json.dumps(inline_auth_signals, ensure_ascii=False, separators=(",", ":")),
                "auth_semantics": auth_semantics(rule.rule, methods, decorators, rule.endpoint),
                "client_surfaces": clients,
                "client_references": client_refs,
                "contract_source": f"runtime:url_map;source:{source}",
                "target_module": target_module(rule.rule, rule.endpoint, legacy),
                "migration_status": "pending",
                "compatibility_notes": route_compatibility_notes(rule.rule, rule.endpoint, methods),
            }
        )
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROUTE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def source_route_decorator_facts(legacy_root: Path) -> list[dict[str, Any]]:
    """Enumerate every Flask-style route decorator without importing modules."""
    route_decorators = {"route", "get", "post", "put", "delete", "patch"}
    facts: list[dict[str, Any]] = []
    for path in sorted((legacy_root / "app").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                target = decorator.func
                if isinstance(target, ast.Attribute):
                    name = target.attr.lower()
                elif isinstance(target, ast.Name):
                    name = target.id.lower()
                else:
                    name = ""
                if name not in route_decorators:
                    continue
                declared_path = "<dynamic>"
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    value = decorator.args[0].value
                    if isinstance(value, str):
                        declared_path = value
                methods: list[str] = []
                if name != "route":
                    methods = [name.upper()]
                for keyword in decorator.keywords:
                    if keyword.arg != "methods" or not isinstance(keyword.value, (ast.List, ast.Tuple)):
                        continue
                    methods = [
                        str(element.value).upper()
                        for element in keyword.value.elts
                        if isinstance(element, ast.Constant) and isinstance(element.value, str)
                    ]
                if not methods:
                    methods = ["GET"]
                facts.append(
                    {
                        "source": (
                            f"{path.relative_to(legacy_root).as_posix()}:{decorator.lineno}"
                        ),
                        "declared_path": declared_path,
                        "methods": sorted(methods),
                    }
                )
    return sorted(
        facts,
        key=lambda item: (item["source"], item["declared_path"], item["methods"]),
    )


def identity_sha256(rows: Iterable[dict[str, str]], fields: tuple[str, ...]) -> str:
    material = "\n".join(
        "\t".join(row[field] for field in fields)
        for row in sorted(rows, key=lambda item: tuple(item[field] for field in fields))
    )
    return hashlib.sha256((material + "\n").encode("utf-8")).hexdigest()


def migration_tables(legacy_root: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    patterns = [
        re.compile(r"op\.create_table\(\s*['\"]([^'\"]+)['\"]"),
        re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"']?([a-zA-Z_][a-zA-Z0-9_]*)", re.I),
    ]
    for path in sorted((legacy_root / "migrations" / "versions").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            for match in pattern.finditer(text):
                found.setdefault(match.group(1), path.relative_to(legacy_root).as_posix())
    return found


def import_all_model_modules(db: Any) -> tuple[int, int, list[str]]:
    """Import every app.models module so metadata cannot silently omit models."""
    import app.models as models_package

    package_count = len(db.metadata.tables)
    imported: list[str] = []
    for module_info in sorted(pkgutil.iter_modules(models_package.__path__), key=lambda item: item.name):
        module_name = f"app.models.{module_info.name}"
        importlib.import_module(module_name)
        imported.append(module_name)
    return package_count, len(db.metadata.tables), imported


def model_table_sources(db: Any, legacy_root: Path) -> dict[str, tuple[str, ...]]:
    """Resolve each mapped table to concrete model files for traceable evidence."""
    sources: dict[str, set[str]] = defaultdict(set)
    for mapper in db.Model.registry.mappers:
        table = getattr(mapper, "local_table", None)
        model_class = getattr(mapper, "class_", None)
        if table is None or model_class is None:
            continue
        source_file = inspect.getsourcefile(model_class)
        source = relative_source(source_file, legacy_root)
        if source != "unknown":
            sources[str(table.name)].add(source)
    return {name: tuple(sorted(values)) for name, values in sources.items()}


def alembic_facts(legacy_root: Path) -> tuple[str, int]:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(legacy_root / "alembic.ini"))
    config.set_main_option("script_location", str(legacy_root / "migrations"))
    scripts = ScriptDirectory.from_config(config)
    heads = scripts.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Expected one Alembic head, got {heads}")
    return heads[0], sum(1 for _revision in scripts.walk_revisions())


def migration_indexes(legacy_root: Path) -> dict[str, set[str]]:
    indexes: dict[str, set[str]] = defaultdict(set)
    raw_index = re.compile(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"[\"']?([a-zA-Z_][a-zA-Z0-9_]*)[\"']?\s+ON\s+"
        r"(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?[\"']?([a-zA-Z_][a-zA-Z0-9_]*)",
        re.I,
    )

    def literal_string(node: ast.expr) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Call) and node.args:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "f":
                return literal_string(node.args[0])
        return None

    class IndexVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.batch_tables: dict[str, str] = {}

        def visit_With(self, node: ast.With) -> None:
            previous = dict(self.batch_tables)
            for item in node.items:
                expression = item.context_expr
                if not isinstance(expression, ast.Call) or not expression.args:
                    continue
                if not isinstance(expression.func, ast.Attribute) or expression.func.attr != "batch_alter_table":
                    continue
                table_name = literal_string(expression.args[0])
                if table_name and isinstance(item.optional_vars, ast.Name):
                    self.batch_tables[item.optional_vars.id] = table_name
            self.generic_visit(node)
            self.batch_tables = previous

        def visit_Call(self, node: ast.Call) -> None:
            index_name: str | None = None
            table_name: str | None = None
            if isinstance(node.func, ast.Attribute) and node.func.attr == "create_index" and node.args:
                index_name = literal_string(node.args[0])
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id in self.batch_tables:
                        table_name = self.batch_tables[node.func.value.id]
                    elif node.func.value.id == "op" and len(node.args) > 1:
                        table_name = literal_string(node.args[1])
            elif isinstance(node.func, ast.Name) and node.func.id == "_index_safe" and len(node.args) > 1:
                index_name = literal_string(node.args[0])
                table_name = literal_string(node.args[1])
            if index_name and table_name:
                indexes[table_name].add(index_name)
            self.generic_visit(node)

    for path in sorted((legacy_root / "migrations" / "versions").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for match in raw_index.finditer(text):
            indexes[match.group(2)].add(match.group(1))
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
                if not any(name.endswith("INDEXES") for name in target_names):
                    continue
                if not isinstance(node.value, (ast.List, ast.Tuple)):
                    continue
                for item in node.value.elts:
                    if isinstance(item, (ast.List, ast.Tuple)) and len(item.elts) >= 2:
                        index_name = literal_string(item.elts[0])
                        table_name = literal_string(item.elts[1])
                        if index_name and table_name:
                            indexes[table_name].add(index_name)
        IndexVisitor().visit(tree)
    return dict(indexes)


def migration_index_count(legacy_root: Path) -> int:
    return sum(len(names) for names in migration_indexes(legacy_root).values())


def table_constraints(
    table: Any,
    migration_index_names: Iterable[str] = (),
    physical_fact: str | None = None,
) -> str:
    foreign_keys = sorted(f"{fk.parent.name}->{fk.target_fullname}" for fk in table.foreign_keys)
    unique_constraints: list[str] = []
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_constraints.append("+".join(column.name for column in constraint.columns))
    indexes = sorted(
        f"{index.name}({'+'.join(column.name for column in index.columns)}){' unique' if index.unique else ''}"
        for index in table.indexes
    )
    parts = [f"columns={len(table.columns)}"]
    if foreign_keys:
        parts.append(f"fk={'|'.join(foreign_keys)}")
    if unique_constraints:
        parts.append(f"unique={'|'.join(sorted(unique_constraints))}")
    if indexes:
        parts.append(f"indexes={'|'.join(indexes)}")
    migration_indexes_for_table = sorted(set(migration_index_names))
    if migration_indexes_for_table:
        parts.append(f"migration_indexes={'|'.join(migration_indexes_for_table)}")
    if physical_fact:
        parts.append(physical_fact)
    return "; ".join(parts)


def legacy_owner_for_table(name: str) -> str:
    owner = TABLE_LEGACY_OWNERS.get(name)
    if owner is None:
        raise RuntimeError(f"Table has no explicit legacy owner: {name}")
    return owner


def write_data_ownership(db: Any, legacy_root: Path, output: Path) -> list[dict[str, str]]:
    migrations = migration_tables(legacy_root)
    indexes_by_table = migration_indexes(legacy_root)
    model_sources = model_table_sources(db, legacy_root)
    metadata_tables = dict(db.metadata.tables)
    names = sorted(set(metadata_tables) | set(migrations) | {"alembic_version"})
    if set(TABLE_LEGACY_OWNERS) != set(TABLE_OWNERS):
        missing = sorted(set(TABLE_OWNERS) - set(TABLE_LEGACY_OWNERS))
        extra = sorted(set(TABLE_LEGACY_OWNERS) - set(TABLE_OWNERS))
        raise RuntimeError(
            f"Legacy owner map mismatch: missing={missing}, extra={extra}"
        )
    special_notes = {
        "forum_posts": "The inspected PostgreSQL schema has 28 physical columns: 27 ORM columns plus generated search_vector; its GIN index and ALTER migration are explicit contract evidence.",
        "interaction_notifications": "ORM exists in app/models/follow.py but app.models package does not import it; the legacy forum service is the only runtime reader/writer, while the target owner remains messaging and the database has uq_interaction_notifications_dedup absent from ORM.",
        "user_follows": "ORM exists in app/models/follow.py but app.models package does not import it; ORM and database constraint names differ.",
        "user_question_tag_items": "Runtime attempts two extra composite indexes that are absent from Alembic and the inspected local database.",
        "alembic_version": "Physical migration-tooling table; included to close the 70-table local PostgreSQL inventory.",
    }
    rows: list[dict[str, str]] = []
    for name in names:
        table = metadata_tables.get(name)
        owner = TABLE_OWNERS.get(name)
        if owner is None:
            raise RuntimeError(f"Table has no unique target owner: {name}")
        source_parts: list[str] = []
        if table is not None:
            source_parts.extend(model_sources.get(name, ("SQLAlchemy metadata (model source unresolved)",)))
        if name in migrations:
            source_parts.append(migrations[name])
        source_parts.extend(ADDITIONAL_TABLE_MIGRATION_SOURCES.get(name, ()))
        if name == "alembic_version":
            source_parts.append("Alembic migration tooling")
        persistence_role = (
            "migration_tooling"
            if name == "alembic_version"
            else "supporting_state"
            if name in {"schema_migrations", "reinforce_similar_cache"}
            else "business_fact"
        )
        rows.append(
            {
                "resource_kind": "table",
                "resource_name": name,
                "legacy_owner": legacy_owner_for_table(name),
                "legacy_source": "; ".join(source_parts),
                "target_owner": owner,
                "persistence_role": persistence_role,
                "constraints_or_pattern": table_constraints(
                    table,
                    indexes_by_table.get(name, ()),
                    TABLE_PHYSICAL_FACTS.get(name),
                )
                if table is not None
                else "version column; physical database tooling table",
                "migration_status": "inventoried",
                "notes": special_notes.get(name, "One runtime writer during cutover."),
            }
        )
    rows.extend(EXTERNAL_RESOURCES)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DATA_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> int:
    args = parse_args()
    legacy_root = args.legacy_root.resolve()
    output_dir = args.output_dir.resolve()
    if not (legacy_root / "app" / "__init__.py").is_file():
        raise SystemExit(f"Not a Ti legacy root: {legacy_root}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ti-java-inventory-") as data_dir:
        os.environ["DATA_DIR"] = data_dir
        os.environ["FLASK_ENV"] = "testing"
        os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
        os.environ["RATELIMIT_STORAGE_URL"] = "memory://"
        os.environ.pop("REDIS_URL", None)
        sys.path.insert(0, str(legacy_root))
        os.chdir(legacy_root)

        import app as legacy_app
        from app.core.extensions import db

        logging.disable(logging.CRITICAL)
        legacy_app._start_background_tasks = lambda _app: None
        app = legacy_app.create_app("testing")
        route_rows = write_routes(app, legacy_root, output_dir / "02-route-parity-matrix.csv")
        with app.app_context():
            package_table_count, all_model_table_count, imported_model_modules = import_all_model_modules(db)
            data_rows = write_data_ownership(db, legacy_root, output_dir / "03-data-ownership.csv")

    alembic_head, alembic_revision_count = alembic_facts(legacy_root)
    mini_calls = miniprogram_calls(legacy_root)
    source_decorators = source_route_decorator_facts(legacy_root)
    unregistered_popup_decorators = [
        fact
        for fact in source_decorators
        if fact["source"].startswith(
            (
                "app/modules/admin/routes/api_components/popups.py:",
                "app/modules/popups/routes/api.py:",
            )
        )
    ]
    registration_kinds = Counter(row["registration_kind"] for row in route_rows)

    summary = {
        "legacy_commit": "700006dfdfa063deb4387be572911e782bcea0d9",
        "registered_url_rules": len(route_rows),
        "route_identity_sha256": identity_sha256(
            route_rows,
            ("route_id", "path", "methods", "endpoint"),
        ),
        "route_contract_sha256": identity_sha256(route_rows, tuple(ROUTE_FIELDS)),
        "source_route_decorators": len(source_decorators),
        "registered_decorator_rules": (
            registration_kinds["blueprint_decorator"]
            + registration_kinds["application_decorator"]
        ),
        "unregistered_route_decorators": len(unregistered_popup_decorators),
        "unregistered_route_definitions": unregistered_popup_decorators,
        "route_registration_kinds": dict(sorted(registration_kinds.items())),
        "miniprogram_call_expressions": len(mini_calls),
        "miniprogram_unique_calls": len({(path, method) for path, method, _source in mini_calls}),
        "miniprogram_registered_rules": sum(
            "miniprogram" in row["client_surfaces"].split(";") for row in route_rows
        ),
        "route_methods": dict(sorted(Counter(row["methods"] for row in route_rows).items())),
        "auth_semantics": dict(sorted(Counter(row["auth_semantics"] for row in route_rows).items())),
        "target_modules": dict(sorted(Counter(row["target_module"] for row in route_rows).items())),
        "client_surfaces": dict(sorted(Counter(row["client_surfaces"] for row in route_rows).items())),
        "data_resources": len(data_rows),
        "data_resource_identity_sha256": identity_sha256(
            data_rows,
            ("resource_kind", "resource_name"),
        ),
        "data_contract_sha256": identity_sha256(data_rows, tuple(DATA_FIELDS)),
        "resource_kinds": dict(
            sorted(Counter(row["resource_kind"] for row in data_rows).items())
        ),
        "tables": sum(row["resource_kind"] == "table" for row in data_rows),
        "application_tables": sum(row["resource_kind"] == "table" and row["resource_name"] != "alembic_version" for row in data_rows),
        "orm_application_columns": sum(len(table.columns) for table in db.metadata.tables.values()),
        "migration_only_application_columns": 1,
        "migration_tooling_columns": 1,
        "known_physical_columns": (
            sum(len(table.columns) for table in db.metadata.tables.values()) + 2
        ),
        "package_discovered_tables": package_table_count,
        "all_model_modules_tables": all_model_table_count,
        "imported_model_modules": len(imported_model_modules),
        "alembic_head": alembic_head,
        "alembic_revisions": alembic_revision_count,
        "migration_explicit_indexes": migration_index_count(legacy_root),
        "external_resources": sum(row["resource_kind"] != "table" for row in data_rows),
        "target_owners": dict(sorted(Counter(row["target_owner"] for row in data_rows).items())),
    }
    (output_dir / "phase0-inventory-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
