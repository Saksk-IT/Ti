-- Phase 4C Node D test-only schema for a local disposable backup/restore
-- rehearsal. It is layered over 076/077 and is not a Flyway migration,
-- production schema, production writer fence, or authorization to migrate data.

CREATE SCHEMA phase4c_tag_execution_fixture;
REVOKE ALL ON SCHEMA phase4c_tag_execution_fixture FROM PUBLIC;
REVOKE ALL ON SCHEMA phase4c_tag_execution_fixture
FROM ti_phase4c_tag_operator;

CREATE TABLE phase4c_tag_execution_fixture.writer_expectation (
    writer_id text PRIMARY KEY,
    runtime_name text NOT NULL CHECK (
        runtime_name IN ('legacy', 'java')
    ),
    component_name text NOT NULL CHECK (
        component_name IN ('web', 'worker', 'scheduler')
    ),
    application_name text NOT NULL UNIQUE CHECK (
        application_name ~ '^phase4c-rehearsal-(legacy|java)-(web|worker|scheduler)$'
    ),
    local_disposable_only boolean NOT NULL CHECK (local_disposable_only),
    CHECK (
        writer_id = runtime_name || '_' || component_name
    )
);

-- A conservative all-domains matrix prevents a local rehearsal from treating
-- one stopped process as proof that the source, target, and membership writer
-- surfaces have all stopped. It is expectation data, not a production receipt.
CREATE TABLE phase4c_tag_execution_fixture.writer_domain_expectation (
    writer_id text NOT NULL REFERENCES
        phase4c_tag_execution_fixture.writer_expectation (writer_id)
        ON DELETE RESTRICT,
    writer_domain text NOT NULL CHECK (
        writer_domain IN ('SOURCE', 'TARGET', 'MEMBERSHIP')
    ),
    PRIMARY KEY (writer_id, writer_domain)
);

CREATE TABLE phase4c_tag_execution_fixture.phase_expectation (
    phase_name text PRIMARY KEY CHECK (
        phase_name IN ('PREPARE', 'FREEZE', 'APPLY', 'RECOVERY')
    ),
    phase_ordinal smallint NOT NULL UNIQUE CHECK (
        phase_ordinal BETWEEN 0 AND 3
    ),
    freeze_receipts_required boolean NOT NULL,
    apply_authorization_required boolean NOT NULL,
    legacy_runtime_disabled_required boolean NOT NULL,
    CHECK (
        (phase_name = 'PREPARE'
            AND phase_ordinal = 0
            AND NOT freeze_receipts_required
            AND NOT apply_authorization_required
            AND NOT legacy_runtime_disabled_required)
        OR (phase_name = 'FREEZE'
            AND phase_ordinal = 1
            AND freeze_receipts_required
            AND NOT apply_authorization_required
            AND NOT legacy_runtime_disabled_required)
        OR (phase_name = 'APPLY'
            AND phase_ordinal = 2
            AND freeze_receipts_required
            AND apply_authorization_required
            AND legacy_runtime_disabled_required)
        OR (phase_name = 'RECOVERY'
            AND phase_ordinal = 3
            AND freeze_receipts_required
            AND apply_authorization_required
            AND legacy_runtime_disabled_required)
    )
);

-- This table contains only public deterministic sentinel values. Dynamic dump
-- paths, database names, credentials, signatures, private keys, raw tags, and
-- business payloads are deliberately forbidden from this SQL fixture.
CREATE TABLE phase4c_tag_execution_fixture.acl_sentinel (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    fixture_scope text NOT NULL CHECK (
        fixture_scope = 'local-disposable-backup-restore-rehearsal-only'
    ),
    public_marker_sha256 char(64) NOT NULL CHECK (
        public_marker_sha256 ~ '^[0-9a-f]{64}$'
    )
);

REVOKE ALL PRIVILEGES ON ALL TABLES
IN SCHEMA phase4c_tag_execution_fixture FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL TABLES
IN SCHEMA phase4c_tag_execution_fixture FROM ti_phase4c_tag_operator;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES
IN SCHEMA phase4c_tag_execution_fixture FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES
IN SCHEMA phase4c_tag_execution_fixture FROM ti_phase4c_tag_operator;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS
IN SCHEMA phase4c_tag_execution_fixture FROM PUBLIC;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS
IN SCHEMA phase4c_tag_execution_fixture FROM ti_phase4c_tag_operator;

ALTER DEFAULT PRIVILEGES IN SCHEMA phase4c_tag_execution_fixture
REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA phase4c_tag_execution_fixture
REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA phase4c_tag_execution_fixture
REVOKE ALL ON FUNCTIONS FROM PUBLIC;
