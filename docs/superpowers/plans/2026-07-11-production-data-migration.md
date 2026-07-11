# Production Data Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add one target-side command that safely pulls a consistent production snapshot from server 1 into a freshly deployed server 2, preserves target-local deployment credentials, restores source application secrets and data, verifies the result, and resumes server 1 on failure.

**Architecture:** A target orchestrator sends a temporary exporter plus a shared shell library to server 1 over strict SSH. The exporter freezes source writes and builds a checksummed bundle. Python helpers validate archives and merge env files without executing remote content; the target restores PostgreSQL, Redis, uploads, instance data, and configuration under rollback protection.

**Tech Stack:** Bash 4+, Python 3 standard library, Docker Compose v2, PostgreSQL 16 tools, Redis 7 tools, pytest 8.

---

## File map

- Create `scripts/lib/merge_production_env.py`: parse and merge env files as inert data.
- Create `scripts/lib/validate_migration_archive.py`: reject unsafe tar members and unexpected layouts.
- Create `scripts/lib/production_migration_common.sh`: shared validation, hashing, SSH-safe, Docker/Compose, and state helpers.
- Create `scripts/export_production_data.sh`: source-side `preflight`, `prepare`, `resume`, and `finalize` actions.
- Create `scripts/migrate_production_data.sh`: target-side CLI, orchestration, restore, verification, and rollback.
- Create `tests/production_migration_test_support.py`: shared Python-helper test utilities.
- Create `tests/test_merge_production_env.py`: env parser/merge/atomic-write tests.
- Create `tests/test_validate_migration_archive.py`: archive structure/resource-bound tests.
- Create `tests/test_production_data_migration.py`: focused Shell orchestration tests.
- Modify `docs/PRODUCTION.md`: document prerequisites, dry-run, migration, cutover, and rollback.

### Task 1: Safe configuration merge and archive validation

**Files:**
- Create: `scripts/lib/merge_production_env.py`
- Create: `scripts/lib/validate_migration_archive.py`
- Create: `tests/production_migration_test_support.py`
- Create: `tests/test_merge_production_env.py`
- Create: `tests/test_validate_migration_archive.py`

- [x] **Step 1: Write failing env-merge tests**

Add tests that invoke the helper through `subprocess.run` and prove:

```python
def test_env_merge_uses_source_secrets_and_target_local_values(tmp_path):
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    source.write_text(
        "SECRET_KEY=source-secret\nPOSTGRES_PASSWORD=source-db\n"
        "DASHSCOPE_API_KEY=source-ai\nDOMAIN=old.example.com\n",
        encoding="utf-8",
    )
    target.write_text(
        "SECRET_KEY=target-secret\nPOSTGRES_PASSWORD=target-db\n"
        "DOMAIN=new.example.com\nHTTP_PORT=8080\n",
        encoding="utf-8",
    )

    result = run_python_helper(
        "scripts/lib/merge_production_env.py",
        "--source", str(source), "--target", str(target), "--output", str(output),
    )

    assert result.returncode == 0
    merged = output.read_text(encoding="utf-8")
    assert "SECRET_KEY=source-secret" in merged
    assert "DASHSCOPE_API_KEY=source-ai" in merged
    assert "POSTGRES_PASSWORD=target-db" in merged
    assert "DOMAIN=new.example.com" in merged
    assert "HTTP_PORT=8080" in merged
```

Also test duplicate keys, malformed non-comment lines, a missing source `SECRET_KEY`, missing target `POSTGRES_PASSWORD`, output mode `0600`, atomic failure behavior, and a literal value such as `SECRET_KEY=$(touch marker)` that must never execute shell syntax.

Also assert that `GHCR_TOKEN`, `GHCR_USERNAME`, and `DOCKER_AUTH_CONFIG` are removed even when present in the source or target env.

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_merge_production_env.py
```

Expected: FAIL because `merge_production_env.py` does not exist.

- [x] **Step 3: Implement the env merge helper**

Implement a CLI with `--source`, `--target`, and `--output`. Parse only blank lines, comments, and `KEY=VALUE` records; never call `eval`, `exec`, or shell `source`. Reject duplicate/malformed keys. Build a new mapping from source values, overwrite the following keys from target when present, require `SECRET_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`, then atomically replace the output with mode `0600`:

```python
TARGET_LOCAL_KEYS = frozenset({
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "TI_IMAGE",
    "TI_IMAGE_PULL_POLICY",
    "HTTP_BIND",
    "HTTP_PORT",
    "ENABLE_HTTPS",
    "DOMAIN",
    "EXTRA_DOMAINS",
    "CERTBOT_EMAIL",
    "SESSION_COOKIE_SECURE",
})

REMOVED_AUTH_KEYS = frozenset({
    "GHCR_TOKEN",
    "GHCR_USERNAME",
    "DOCKER_AUTH_CONFIG",
})
```

- [x] **Step 4: Write failing archive-validator tests**

Create archives with Python `tarfile` and assert that the validator:

- accepts an outer bundle with exactly `database.dump`, `redis.tar.gz`, `uploads.tar.gz`, `instance.tar.gz`, `source.env.production`, `manifest.txt`, and `checksums.sha256`;
- rejects absolute paths, `../` traversal, symlinks, hard links, FIFO/device members, duplicate members, and unexpected files;
- accepts inner archives only when every regular file is below the selected `redis/`, `uploads/`, or `instance/` prefix.

- [x] **Step 5: Run the validator tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_validate_migration_archive.py
```

Expected: FAIL because `validate_migration_archive.py` does not exist.

- [x] **Step 6: Implement the archive validator**

Use `tarfile.open(..., mode="r:*")` only to inspect member metadata. Do not extract. Normalize member names with `PurePosixPath`, reject absolute paths and `..`, allow only regular files/directories, reject duplicates, and enforce a CLI profile of `bundle`, `redis`, `uploads`, or `instance`.

- [x] **Step 7: Verify GREEN and refactor**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_merge_production_env.py \
  tests/test_validate_migration_archive.py
python3 -m py_compile \
  scripts/lib/merge_production_env.py \
  scripts/lib/validate_migration_archive.py
git diff --check
```

Expected: all focused tests pass, both helpers compile, and diff check is clean.

- [x] **Step 8: Commit and push Task 1**

```bash
git add scripts/lib/merge_production_env.py \
  scripts/lib/validate_migration_archive.py \
  tests/production_migration_test_support.py \
  tests/test_merge_production_env.py \
  tests/test_validate_migration_archive.py
git commit -m "feat: add migration safety helpers"
git push origin main
```

### Task 2: Shared shell primitives and source export state machine

**Files:**
- Create: `scripts/lib/production_migration_common.sh`
- Create: `scripts/export_production_data.sh`
- Modify: `tests/test_production_data_migration.py`

- [x] **Step 1: Write failing common-library tests**

Add subprocess tests that source the common library in a clean Bash process and assert:

```python
def test_common_library_rejects_unsafe_remote_inputs():
    assert run_common("migration_validate_ssh_target", "ubuntu@10.0.0.2").returncode == 0
    assert run_common("migration_validate_ssh_target", "root@host;id").returncode != 0
    assert run_common("migration_validate_port", "22").returncode == 0
    assert run_common("migration_validate_port", "0").returncode != 0
    assert run_common("migration_validate_absolute_dir", "/opt/ti").returncode == 0
    assert run_common("migration_validate_absolute_dir", "/opt/../root").returncode != 0
```

Also test migration ID validation, SHA-256 output format, secret-safe logging, and `umask 077`. Executable scripts must use the production-safe `[[ "${BASH_SOURCE[0]}" == "$0" ]]` main guard so functions can be sourced without adding a test-only runtime branch.

- [x] **Step 2: Run the common tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_production_data_migration.py -k 'common_library'
```

Expected: FAIL because the common shell library does not exist.

- [x] **Step 3: Implement shared primitives**

Implement small functions for logging, failure, command checks, source/port/path/migration-ID validation, safe env value reads using `awk`, SHA-256 selection (`sha256sum` then `shasum -a 256` fallback), non-interactive root command selection (`root` or `sudo -n`), Compose array construction, service-state capture, service health waits, and lock directory acquire/release. Do not use `eval` and do not print env values.

- [x] **Step 4: Write failing source-export tests**

Use a fake executable directory prepended to `PATH`. Fake `docker` records arguments and produces deterministic outputs without recording secret environment values. Prove:

- `preflight` checks Compose, env, versions, image digest, data size, and disk requirements without stopping services;
- `prepare` records running services, stops `backup nginx web worker`, dumps PostgreSQL, validates the dump, records Redis `DBSIZE`, performs `SAVE`, stops Redis, creates fixed archives and checksums, and leaves source write services stopped;
- a failure after stopping services invokes `resume` behavior and restarts only services that were originally running;
- `resume` is idempotent;
- `finalize` removes temporary bundle/helper state without restarting source services;
- logs never contain values from `SECRET_KEY`, `POSTGRES_PASSWORD`, or third-party token fields.

- [x] **Step 5: Run source-export tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_production_data_migration.py -k 'source_export'
```

Expected: FAIL because `export_production_data.sh` does not exist.

- [x] **Step 6: Implement source export actions**

Implement this CLI contract:

```text
export_production_data.sh preflight --source-dir /opt/ti --migration-id ID
export_production_data.sh prepare   --source-dir /opt/ti --migration-id ID
export_production_data.sh resume    --source-dir /opt/ti --migration-id ID
export_production_data.sh finalize  --source-dir /opt/ti --migration-id ID
```

Use `pg_dump -Fc --no-owner --no-acl`, validate with `pg_restore --list`, stop Redis before host-level tar of `var/redis`, archive only relative `redis/`, `uploads/`, and `instance/` paths, write a non-secret manifest, and create a separate outer SHA-256 file. Persist atomic `PREPARING`, `FROZEN`, `RESUMED`, and `FINALIZED` states plus the originally running service set so `resume` restarts exactly those services once.

- [x] **Step 7: Verify GREEN and refactor**

Run:

```bash
bash -n scripts/lib/production_migration_common.sh \
  scripts/export_production_data.sh
.venv/bin/python -m pytest -q tests/test_production_data_migration.py
git diff --check
```

Expected: all tests pass and both shell files pass syntax checking.

- [x] **Step 8: Commit and push Task 2**

```bash
git add scripts/lib/production_migration_common.sh \
  scripts/export_production_data.sh \
  tests/test_production_data_migration.py
git commit -m "feat: export consistent production migration bundles"
git push origin main
```

### Task 3: Target-side one-click orchestration, restore, and rollback

**Files:**
- Create: `scripts/migrate_production_data.sh`
- Modify: `tests/test_production_data_migration.py`

- [x] **Step 1: Write failing CLI and preflight tests**

Assert that `--help` documents every approved option and that invalid source, port, key path, known-hosts path, target path, or same-host identity fails before `ssh`. Use fake SSH to prove the command includes:

```text
BatchMode=yes
StrictHostKeyChecking=yes
IdentitiesOnly=yes
UpdateHostKeys=no
```

Assert `--dry-run` performs local/remote checks but never stops a service or creates a bundle. Also prove that the only accepted final confirmation text is `MIGRATE <source-host> TO <target-host>`; `yes` and confirmations with either wrong hostname must not upload helpers, stop services, or mutate target data.

- [x] **Step 2: Run CLI tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_production_data_migration.py -k 'target_cli or target_preflight'
```

Expected: FAIL because `migrate_production_data.sh` does not exist.

- [x] **Step 3: Implement CLI, SSH arrays, and helper upload**

Parse `--source`, `--source-dir`, `--source-port`, `--identity-file`, `--known-hosts`, `--target-dir`, `--keep-bundle`, and `--dry-run` without `eval`. Build SSH/SCP arguments as arrays. Copy the exporter and common library into a remote `mktemp -d` directory, invoke preflight there, and clean the helper directory on every exit path.

- [x] **Step 4: Write failing restore and rollback tests**

With fake commands and a valid generated bundle, prove the target order:

1. create target rollback snapshot;
2. invoke remote `prepare`;
3. transfer and verify outer SHA-256;
4. inspect the outer archive before extraction;
5. verify internal checksums and inner archives;
6. stop target `backup nginx web worker redis`;
7. recreate and restore PostgreSQL with `pg_restore --exit-on-error --no-owner --no-privileges`;
8. restore Redis, uploads, and instance atomically;
9. merge env and preserve target-local keys;
10. run migrations with `ENSURE_DEFAULT_ADMIN=0`;
11. start the complete target stack and verify data/health;
12. invoke remote `finalize` only after every check passes.

Inject failure at checksum, PostgreSQL restore, Redis restore, file restore, env merge, migration, startup, and health verification. Every failure after remote `prepare` must invoke remote `resume` and restore the target rollback snapshot. Success must not invoke `resume`.

- [x] **Step 5: Run restore tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_production_data_migration.py -k 'target_restore or target_rollback'
```

Expected: FAIL because restore orchestration is not implemented.

- [x] **Step 6: Implement target rollback, restore, and verification**

Create a local migration workspace under `backups/migrations/<ID>` with mode `0700`. Before source freeze, briefly stop target `backup nginx web worker`, dump PostgreSQL, persist and stop Redis, capture env/uploads/instance, then restore only the target services that were originally running; this produces a consistent rollback point. Use traps to track whether source is frozen and whether target mutation began. On failure, restore target state and remotely resume source independently so one rollback failure cannot suppress the other. On success, compare PostgreSQL, Redis `DBSIZE`, manifest statistics, and file hashes before starting `web`/`worker`, then start the full stack, run local/deep health probes, remotely finalize, remove sensitive bundles unless `--keep-bundle`, and print DNS/HTTPS follow-up steps.

- [x] **Step 7: Verify GREEN and refactor**

Run:

```bash
bash -n scripts/migrate_production_data.sh
.venv/bin/python -m pytest -q tests/test_production_data_migration.py
git diff --check
```

Expected: all focused migration tests pass with no secret values in captured logs.

- [x] **Step 8: Commit and push Task 3**

```bash
git add scripts/migrate_production_data.sh \
  tests/test_production_data_migration.py
git commit -m "feat: add one-click production data migration"
git push origin main
```

### Task 4: Production runbook and complete verification

**Files:**
- Modify: `docs/PRODUCTION.md`
- Modify: `tests/test_production_data_migration.py`

- [x] **Step 1: Write failing documentation contract test**

Add a structural test requiring the production guide to contain:

```text
服务器 2 全新部署
ssh-keyscan followed by fingerprint verification instructions
--dry-run
migrate_production_data.sh
服务器 1 remains stopped after success
DNS and HTTPS cutover
failure rollback behavior
```

- [x] **Step 2: Run the documentation test and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_production_data_migration.py -k 'production_migration_documentation'
```

Expected: FAIL because the runbook has not been added.

- [x] **Step 3: Add the complete command-first runbook**

Document:

- target fresh-deploy command;
- dedicated SSH key setup and manual host-fingerprint verification;
- private GHCR target login prerequisite;
- dry-run command;
- final migration command;
- expected downtime and success behavior;
- failure behavior and manual `resume` fallback command;
- DNS switch, HTTPS reissue, external allowlist checks;
- migration bundle secret-handling and cleanup;
- source retention for 24–72 hours.

- [x] **Step 4: Run focused and regression verification**

Run fresh commands:

```bash
bash -n \
  scripts/migrate_production_data.sh \
  scripts/export_production_data.sh \
  scripts/lib/production_migration_common.sh

python3 -m py_compile \
  scripts/lib/merge_production_env.py \
  scripts/lib/validate_migration_archive.py

.venv/bin/python -m pytest -q tests/test_production_data_migration.py
.venv/bin/python -m pytest -q tests/test_deploy_healthcheck.py

docker compose --env-file .env.production -f compose.prod.yml config \
  >/tmp/ti-compose-migration-check.yml

git diff --check
```

Expected: all commands exit `0`; migration and deployment tests report zero failures.

- [x] **Step 5: Perform final requirements and security review**

Confirm line by line that:

- no secret is logged or committed;
- SSH never disables host-key checking;
- remote values are never passed through `eval` or sourced as shell code;
- target-local env keys survive;
- source `SECRET_KEY` is restored;
- unsafe archives fail before extraction;
- source resumes on every failure after freeze;
- success leaves source stopped;
- unrelated `CLAUDE.md` and `miniprogram-1/.gitignore` changes remain untouched.

- [x] **Step 6: Commit and push Task 4**

```bash
git add docs/PRODUCTION.md tests/test_production_data_migration.py
git commit -m "docs: add production data migration runbook"
git push origin main
```
