-- Phase 4C Node C test-only schema for the disabled-by-default operator core.
-- It is neither a Flyway migration nor authorization to create production objects.

CREATE ROLE ti_phase4c_tag_operator
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

CREATE ROLE ti_phase4c_tag_schema_owner
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

GRANT ti_phase4c_tag_operator TO ti_phase2_fixture_owner;

DO $$
BEGIN
    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM PUBLIC', current_database());
    EXECUTE format(
        'REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE %I FROM ti_phase4c_tag_operator',
        current_database()
    );
END;
$$;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO ti_phase4c_tag_operator;

CREATE SCHEMA ti_migration;
REVOKE ALL ON SCHEMA ti_migration FROM PUBLIC;
GRANT USAGE ON SCHEMA ti_migration TO ti_phase4c_tag_operator;

CREATE TABLE ti_migration.operator_schema_metadata (
    singleton boolean PRIMARY KEY DEFAULT true,
    schema_version integer NOT NULL,
    schema_fingerprint char(64) NOT NULL,
    CONSTRAINT operator_schema_metadata_singleton CHECK (singleton),
    CONSTRAINT operator_schema_metadata_version CHECK (schema_version = 1),
    CONSTRAINT operator_schema_metadata_fingerprint CHECK (
        schema_fingerprint ~ '^[0-9a-f]{64}$'
    )
);

CREATE TABLE ti_migration.personal_bank_tag_run (
    migration_id uuid PRIMARY KEY,
    migration_run_uuid uuid NOT NULL UNIQUE,
    state text NOT NULL,
    version integer NOT NULL,
    backup_manifest_sha256 char(64) NOT NULL,
    cluster_database_identity_sha256 char(64) NOT NULL,
    run_identity_sha256 char(64) NOT NULL,
    preflight_digest_sha256 char(64) NOT NULL,
    source_set_digest_sha256 char(64) NOT NULL,
    plan_set_digest_sha256 char(64) NOT NULL,
    preapply_target_set_digest_sha256 char(64) NOT NULL,
    final_target_set_digest_sha256 char(64) NOT NULL,
    membership_set_digest_sha256 char(64) NOT NULL,
    source_count integer NOT NULL,
    migrated_count integer NOT NULL DEFAULT 0,
    target_already_present_count integer NOT NULL DEFAULT 0,
    empty_noop_count integer NOT NULL DEFAULT 0,
    prepare_evidence_receipt_sha256 char(64) NOT NULL,
    source_writer_stop_receipt_sha256 char(64),
    target_writer_stop_receipt_sha256 char(64),
    membership_writer_stop_receipt_sha256 char(64),
    connection_drain_receipt_sha256 char(64),
    connection_rejection_receipt_sha256 char(64),
    restored_backup_receipt_sha256 char(64),
    apply_authorization_receipt_sha256 char(64),
    legacy_runtime_disabled_receipt_sha256 char(64),
    blocked_failure_code text,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT personal_bank_tag_run_identity
        UNIQUE (migration_id, migration_run_uuid),
    CONSTRAINT personal_bank_tag_run_receipt_identity UNIQUE (
        migration_id,
        migration_run_uuid,
        backup_manifest_sha256,
        cluster_database_identity_sha256,
        run_identity_sha256,
        preflight_digest_sha256,
        source_set_digest_sha256,
        plan_set_digest_sha256,
        preapply_target_set_digest_sha256,
        final_target_set_digest_sha256,
        membership_set_digest_sha256,
        source_writer_stop_receipt_sha256,
        target_writer_stop_receipt_sha256,
        membership_writer_stop_receipt_sha256,
        connection_drain_receipt_sha256,
        connection_rejection_receipt_sha256,
        restored_backup_receipt_sha256,
        apply_authorization_receipt_sha256,
        legacy_runtime_disabled_receipt_sha256
    ),
    CONSTRAINT personal_bank_tag_run_state CHECK (
        (state = 'PLANNED' AND version = 0)
        OR (state = 'FROZEN' AND version = 1)
        OR (state = 'APPLYING' AND version = 2)
        OR (state = 'APPLIED' AND version = 3)
        OR (state = 'BLOCKED' AND version BETWEEN 1 AND 3)
    ),
    CONSTRAINT personal_bank_tag_run_source_count CHECK (source_count > 0),
    CONSTRAINT personal_bank_tag_run_counts CHECK (
        migrated_count >= 0
        AND target_already_present_count >= 0
        AND empty_noop_count >= 0
        AND migrated_count + target_already_present_count + empty_noop_count
            <= source_count
    ),
    CONSTRAINT personal_bank_tag_run_writer_stop_receipts_distinct CHECK (
        (
            source_writer_stop_receipt_sha256 IS NULL
            AND target_writer_stop_receipt_sha256 IS NULL
            AND membership_writer_stop_receipt_sha256 IS NULL
        )
        OR (
            source_writer_stop_receipt_sha256 IS NOT NULL
            AND target_writer_stop_receipt_sha256 IS NOT NULL
            AND membership_writer_stop_receipt_sha256 IS NOT NULL
            AND source_writer_stop_receipt_sha256
                <> target_writer_stop_receipt_sha256
            AND source_writer_stop_receipt_sha256
                <> membership_writer_stop_receipt_sha256
            AND target_writer_stop_receipt_sha256
                <> membership_writer_stop_receipt_sha256
        )
    ),
    CONSTRAINT personal_bank_tag_run_block_code CHECK (
        (state <> 'BLOCKED' AND blocked_failure_code IS NULL)
        OR (
            state = 'BLOCKED'
            AND blocked_failure_code IN (
                'PREFLIGHT_MISMATCH',
                'SOURCE_DRIFT',
                'PLAN_DRIFT',
                'TARGET_MISMATCH',
                'MEMBERSHIP_DRIFT',
                'RECEIPT_MISMATCH',
                'INCOMPLETE_RECEIPTS'
            )
        )
    ),
    CONSTRAINT personal_bank_tag_run_digest_shape CHECK (
        backup_manifest_sha256 ~ '^[0-9a-f]{64}$'
        AND cluster_database_identity_sha256 ~ '^[0-9a-f]{64}$'
        AND run_identity_sha256 ~ '^[0-9a-f]{64}$'
        AND preflight_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND source_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND plan_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND preapply_target_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND final_target_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND membership_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND prepare_evidence_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND (source_writer_stop_receipt_sha256 IS NULL
             OR source_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$')
        AND (target_writer_stop_receipt_sha256 IS NULL
             OR target_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$')
        AND (membership_writer_stop_receipt_sha256 IS NULL
             OR membership_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$')
        AND (connection_drain_receipt_sha256 IS NULL
             OR connection_drain_receipt_sha256 ~ '^[0-9a-f]{64}$')
        AND (connection_rejection_receipt_sha256 IS NULL
             OR connection_rejection_receipt_sha256 ~ '^[0-9a-f]{64}$')
        AND (restored_backup_receipt_sha256 IS NULL
             OR restored_backup_receipt_sha256 ~ '^[0-9a-f]{64}$')
        AND (apply_authorization_receipt_sha256 IS NULL
             OR apply_authorization_receipt_sha256 ~ '^[0-9a-f]{64}$')
        AND (legacy_runtime_disabled_receipt_sha256 IS NULL
             OR legacy_runtime_disabled_receipt_sha256 ~ '^[0-9a-f]{64}$')
    )
);

CREATE TABLE ti_migration.personal_bank_tag_run_source (
    migration_id uuid NOT NULL,
    migration_run_uuid uuid NOT NULL,
    source_row_id bigint NOT NULL,
    user_id bigint NOT NULL,
    bank_id integer NOT NULL,
    key_digest_sha256 char(64) NOT NULL,
    source_digest_sha256 char(64) NOT NULL,
    plan_digest_sha256 char(64) NOT NULL,
    preflight_target_digest_sha256 char(64) NOT NULL,
    preapply_target_digest_sha256 char(64) NOT NULL,
    expected_target_digest_sha256 char(64) NOT NULL,
    membership_digest_sha256 char(64) NOT NULL,
    disposition text NOT NULL,
    definition_count integer NOT NULL,
    question_binding_count integer NOT NULL,
    distinct_tag_count integer NOT NULL,
    plan_row_count integer NOT NULL,
    preapply_target_row_count integer NOT NULL,
    expected_final_target_row_count integer NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (migration_id, migration_run_uuid, source_row_id),
    CONSTRAINT personal_bank_tag_run_source_run_fk
        FOREIGN KEY (migration_id, migration_run_uuid)
        REFERENCES ti_migration.personal_bank_tag_run (
            migration_id, migration_run_uuid
        ) ON DELETE RESTRICT,
    CONSTRAINT personal_bank_tag_run_source_identity CHECK (
        source_row_id > 0 AND user_id > 0 AND bank_id > 0
    ),
    CONSTRAINT personal_bank_tag_run_source_disposition CHECK (
        disposition IN ('MIGRATED', 'TARGET_ALREADY_PRESENT', 'EMPTY_NOOP')
    ),
    CONSTRAINT personal_bank_tag_run_source_counts CHECK (
        definition_count >= 0
        AND question_binding_count >= 0
        AND distinct_tag_count >= 0
        AND plan_row_count >= 0
        AND preapply_target_row_count >= 0
        AND expected_final_target_row_count >= 0
    ),
    CONSTRAINT personal_bank_tag_run_source_digest_shape CHECK (
        key_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND source_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND plan_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND preflight_target_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND preapply_target_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND expected_target_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND membership_digest_sha256 ~ '^[0-9a-f]{64}$'
    )
);

CREATE INDEX personal_bank_tag_run_source_user_bank_idx
    ON ti_migration.personal_bank_tag_run_source (user_id, bank_id);

CREATE TABLE ti_migration.personal_bank_tag_receipt (
    migration_id uuid NOT NULL,
    migration_run_uuid uuid NOT NULL,
    source_row_id bigint NOT NULL,
    backup_manifest_sha256 char(64) NOT NULL,
    cluster_database_identity_sha256 char(64) NOT NULL,
    run_identity_sha256 char(64) NOT NULL,
    preflight_digest_sha256 char(64) NOT NULL,
    source_set_digest_sha256 char(64) NOT NULL,
    plan_set_digest_sha256 char(64) NOT NULL,
    preapply_target_set_digest_sha256 char(64) NOT NULL,
    final_target_set_digest_sha256 char(64) NOT NULL,
    membership_set_digest_sha256 char(64) NOT NULL,
    source_writer_stop_receipt_sha256 char(64) NOT NULL,
    target_writer_stop_receipt_sha256 char(64) NOT NULL,
    membership_writer_stop_receipt_sha256 char(64) NOT NULL,
    connection_drain_receipt_sha256 char(64) NOT NULL,
    connection_rejection_receipt_sha256 char(64) NOT NULL,
    restored_backup_receipt_sha256 char(64) NOT NULL,
    apply_authorization_receipt_sha256 char(64) NOT NULL,
    legacy_runtime_disabled_receipt_sha256 char(64) NOT NULL,
    disposition text NOT NULL,
    key_digest_sha256 char(64) NOT NULL,
    source_digest_sha256 char(64) NOT NULL,
    plan_digest_sha256 char(64) NOT NULL,
    expected_target_digest_sha256 char(64) NOT NULL,
    membership_digest_sha256 char(64) NOT NULL,
    actual_target_digest_sha256 char(64) NOT NULL,
    inserted_target_row_count integer NOT NULL,
    created_txid bigint NOT NULL DEFAULT txid_current(),
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (migration_id, migration_run_uuid, source_row_id),
    CONSTRAINT personal_bank_tag_receipt_source_fk
        FOREIGN KEY (migration_id, migration_run_uuid, source_row_id)
        REFERENCES ti_migration.personal_bank_tag_run_source (
            migration_id, migration_run_uuid, source_row_id
        ) ON DELETE RESTRICT,
    CONSTRAINT personal_bank_tag_receipt_run_identity_fk FOREIGN KEY (
        migration_id,
        migration_run_uuid,
        backup_manifest_sha256,
        cluster_database_identity_sha256,
        run_identity_sha256,
        preflight_digest_sha256,
        source_set_digest_sha256,
        plan_set_digest_sha256,
        preapply_target_set_digest_sha256,
        final_target_set_digest_sha256,
        membership_set_digest_sha256,
        source_writer_stop_receipt_sha256,
        target_writer_stop_receipt_sha256,
        membership_writer_stop_receipt_sha256,
        connection_drain_receipt_sha256,
        connection_rejection_receipt_sha256,
        restored_backup_receipt_sha256,
        apply_authorization_receipt_sha256,
        legacy_runtime_disabled_receipt_sha256
    ) REFERENCES ti_migration.personal_bank_tag_run (
        migration_id,
        migration_run_uuid,
        backup_manifest_sha256,
        cluster_database_identity_sha256,
        run_identity_sha256,
        preflight_digest_sha256,
        source_set_digest_sha256,
        plan_set_digest_sha256,
        preapply_target_set_digest_sha256,
        final_target_set_digest_sha256,
        membership_set_digest_sha256,
        source_writer_stop_receipt_sha256,
        target_writer_stop_receipt_sha256,
        membership_writer_stop_receipt_sha256,
        connection_drain_receipt_sha256,
        connection_rejection_receipt_sha256,
        restored_backup_receipt_sha256,
        apply_authorization_receipt_sha256,
        legacy_runtime_disabled_receipt_sha256
    ) ON DELETE RESTRICT,
    CONSTRAINT personal_bank_tag_receipt_disposition CHECK (
        disposition IN ('MIGRATED', 'TARGET_ALREADY_PRESENT', 'EMPTY_NOOP')
    ),
    CONSTRAINT personal_bank_tag_receipt_insert_count CHECK (
        inserted_target_row_count >= 0
    ),
    CONSTRAINT personal_bank_tag_receipt_digest_shape CHECK (
        backup_manifest_sha256 ~ '^[0-9a-f]{64}$'
        AND cluster_database_identity_sha256 ~ '^[0-9a-f]{64}$'
        AND run_identity_sha256 ~ '^[0-9a-f]{64}$'
        AND preflight_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND source_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND plan_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND preapply_target_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND final_target_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND membership_set_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND source_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND target_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND membership_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND connection_drain_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND connection_rejection_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND restored_backup_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND apply_authorization_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND legacy_runtime_disabled_receipt_sha256 ~ '^[0-9a-f]{64}$'
        AND key_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND source_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND plan_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND expected_target_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND membership_digest_sha256 ~ '^[0-9a-f]{64}$'
        AND actual_target_digest_sha256 ~ '^[0-9a-f]{64}$'
    )
);

CREATE TABLE ti_migration.personal_bank_tag_audit (
    audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    migration_id uuid NOT NULL,
    migration_run_uuid uuid NOT NULL,
    event_type text NOT NULL,
    from_state text,
    to_state text NOT NULL,
    state_version integer NOT NULL,
    failure_code text,
    transaction_id bigint NOT NULL DEFAULT txid_current(),
    created_at timestamp with time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT personal_bank_tag_audit_event CHECK (
        event_type IN ('PREPARED', 'FROZEN', 'APPLYING', 'APPLIED', 'BLOCKED')
    )
);

CREATE FUNCTION ti_migration.personal_bank_tag_target_digest(
    requested_user_id bigint,
    requested_bank_id integer
)
RETURNS char(64)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
    SELECT encode(
        sha256(
            int4send(octet_length(convert_to(
                'ti:phase4c:tag-migration:operator-target-facts:v1', 'UTF8'
            )))
            || convert_to(
                'ti:phase4c:tag-migration:operator-target-facts:v1', 'UTF8'
            )
            || decode(
                coalesce(
                    string_agg(
                        encode(
                            int4send(question_id)
                            || int4send(octet_length(convert_to(tag, 'UTF8')))
                            || convert_to(tag, 'UTF8'),
                            'hex'
                        ),
                        '' ORDER BY question_id, tag COLLATE "C"
                    ),
                    ''
                ),
                'hex'
            )
        ),
        'hex'
    )::char(64)
    FROM (
        SELECT DISTINCT question_id, tag
        FROM public.user_question_tag_items
        WHERE user_id = requested_user_id
          AND scope = 'user_bank'
          AND scope_id = requested_bank_id
    ) AS target_facts
$$;

CREATE FUNCTION ti_migration.personal_bank_tag_run_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, ti_migration
AS $$
DECLARE
    receipt_count integer;
    migrated_count integer;
    already_count integer;
    noop_count integer;
    facts_valid boolean;
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.created_at := CURRENT_TIMESTAMP;
        NEW.updated_at := CURRENT_TIMESTAMP;
        IF NEW.state <> 'PLANNED' OR NEW.version <> 0
           OR NEW.migrated_count <> 0
           OR NEW.target_already_present_count <> 0
           OR NEW.empty_noop_count <> 0
           OR NEW.source_writer_stop_receipt_sha256 IS NOT NULL
           OR NEW.target_writer_stop_receipt_sha256 IS NOT NULL
           OR NEW.membership_writer_stop_receipt_sha256 IS NOT NULL
           OR NEW.connection_drain_receipt_sha256 IS NOT NULL
           OR NEW.connection_rejection_receipt_sha256 IS NOT NULL
           OR NEW.restored_backup_receipt_sha256 IS NOT NULL
           OR NEW.apply_authorization_receipt_sha256 IS NOT NULL
           OR NEW.legacy_runtime_disabled_receipt_sha256 IS NOT NULL THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'invalid planned run';
        END IF;
    ELSE
        NEW.updated_at := CURRENT_TIMESTAMP;
        IF (OLD.migration_id, OLD.migration_run_uuid,
            OLD.backup_manifest_sha256,
            OLD.cluster_database_identity_sha256,
            OLD.run_identity_sha256,
            OLD.preflight_digest_sha256,
            OLD.source_set_digest_sha256,
            OLD.plan_set_digest_sha256,
            OLD.preapply_target_set_digest_sha256,
            OLD.final_target_set_digest_sha256,
            OLD.membership_set_digest_sha256,
            OLD.source_count,
            OLD.prepare_evidence_receipt_sha256,
            OLD.created_at)
           IS DISTINCT FROM
           (NEW.migration_id, NEW.migration_run_uuid,
            NEW.backup_manifest_sha256,
            NEW.cluster_database_identity_sha256,
            NEW.run_identity_sha256,
            NEW.preflight_digest_sha256,
            NEW.source_set_digest_sha256,
            NEW.plan_set_digest_sha256,
            NEW.preapply_target_set_digest_sha256,
            NEW.final_target_set_digest_sha256,
            NEW.membership_set_digest_sha256,
            NEW.source_count,
            NEW.prepare_evidence_receipt_sha256,
            NEW.created_at) THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'immutable run identity';
        END IF;

        IF NEW.version <> OLD.version + 1 THEN
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'invalid run version';
        END IF;

        IF OLD.state = 'PLANNED' AND NEW.state = 'FROZEN' THEN
            IF NEW.migrated_count <> OLD.migrated_count
               OR NEW.target_already_present_count
                    <> OLD.target_already_present_count
               OR NEW.empty_noop_count <> OLD.empty_noop_count
               OR NEW.source_writer_stop_receipt_sha256 IS NULL
               OR NEW.target_writer_stop_receipt_sha256 IS NULL
               OR NEW.membership_writer_stop_receipt_sha256 IS NULL
               OR NEW.source_writer_stop_receipt_sha256
                    = NEW.target_writer_stop_receipt_sha256
               OR NEW.source_writer_stop_receipt_sha256
                    = NEW.membership_writer_stop_receipt_sha256
               OR NEW.target_writer_stop_receipt_sha256
                    = NEW.membership_writer_stop_receipt_sha256
               OR NEW.connection_drain_receipt_sha256 IS NULL
               OR NEW.connection_rejection_receipt_sha256 IS NULL
               OR NEW.restored_backup_receipt_sha256 IS NULL
               OR NEW.apply_authorization_receipt_sha256 IS NOT NULL
               OR NEW.legacy_runtime_disabled_receipt_sha256 IS NOT NULL THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'invalid freeze';
            END IF;
        ELSIF OLD.state = 'FROZEN' AND NEW.state = 'APPLYING' THEN
            IF NEW.migrated_count <> OLD.migrated_count
               OR NEW.target_already_present_count
                    <> OLD.target_already_present_count
               OR NEW.empty_noop_count <> OLD.empty_noop_count
               OR NEW.source_writer_stop_receipt_sha256
                    IS DISTINCT FROM OLD.source_writer_stop_receipt_sha256
               OR NEW.target_writer_stop_receipt_sha256
                    IS DISTINCT FROM OLD.target_writer_stop_receipt_sha256
               OR NEW.membership_writer_stop_receipt_sha256
                    IS DISTINCT FROM OLD.membership_writer_stop_receipt_sha256
               OR NEW.connection_drain_receipt_sha256 IS DISTINCT FROM OLD.connection_drain_receipt_sha256
               OR NEW.connection_rejection_receipt_sha256 IS DISTINCT FROM OLD.connection_rejection_receipt_sha256
               OR NEW.restored_backup_receipt_sha256 IS DISTINCT FROM OLD.restored_backup_receipt_sha256
               OR NEW.apply_authorization_receipt_sha256 IS NULL
               OR NEW.legacy_runtime_disabled_receipt_sha256 IS NULL THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'invalid apply start';
            END IF;
        ELSIF OLD.state = 'APPLYING' AND NEW.state = 'APPLIED' THEN
            IF NEW.source_writer_stop_receipt_sha256
                    IS DISTINCT FROM OLD.source_writer_stop_receipt_sha256
               OR NEW.target_writer_stop_receipt_sha256
                    IS DISTINCT FROM OLD.target_writer_stop_receipt_sha256
               OR NEW.membership_writer_stop_receipt_sha256
                    IS DISTINCT FROM OLD.membership_writer_stop_receipt_sha256
               OR NEW.connection_drain_receipt_sha256
                    IS DISTINCT FROM OLD.connection_drain_receipt_sha256
               OR NEW.connection_rejection_receipt_sha256
                    IS DISTINCT FROM OLD.connection_rejection_receipt_sha256
               OR NEW.restored_backup_receipt_sha256
                    IS DISTINCT FROM OLD.restored_backup_receipt_sha256
               OR NEW.apply_authorization_receipt_sha256
                    IS DISTINCT FROM OLD.apply_authorization_receipt_sha256
               OR NEW.legacy_runtime_disabled_receipt_sha256
                    IS DISTINCT FROM OLD.legacy_runtime_disabled_receipt_sha256 THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'apply receipts changed';
            END IF;

            SELECT count(receipt.source_row_id),
                   count(*) FILTER (WHERE receipt.disposition = 'MIGRATED'),
                   count(*) FILTER (WHERE receipt.disposition = 'TARGET_ALREADY_PRESENT'),
                   count(*) FILTER (WHERE receipt.disposition = 'EMPTY_NOOP'),
                   coalesce(bool_and(
                       receipt.actual_target_digest_sha256 =
                           ti_migration.personal_bank_tag_target_digest(
                               source.user_id, source.bank_id)
                       AND receipt.actual_target_digest_sha256 =
                           source.expected_target_digest_sha256
                   ), false)
            INTO receipt_count, migrated_count, already_count, noop_count, facts_valid
            FROM ti_migration.personal_bank_tag_run_source AS source
            LEFT JOIN ti_migration.personal_bank_tag_receipt AS receipt
              ON receipt.migration_id = source.migration_id
             AND receipt.migration_run_uuid = source.migration_run_uuid
             AND receipt.source_row_id = source.source_row_id
            WHERE source.migration_id = NEW.migration_id
              AND source.migration_run_uuid = NEW.migration_run_uuid;

            IF receipt_count <> NEW.source_count
               OR migrated_count <> NEW.migrated_count
               OR already_count <> NEW.target_already_present_count
               OR noop_count <> NEW.empty_noop_count
               OR NOT facts_valid THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'incomplete apply';
            END IF;
        ELSIF NEW.state = 'BLOCKED'
              AND OLD.state IN ('PLANNED', 'FROZEN', 'APPLYING') THEN
            IF (NEW.migrated_count,
                NEW.target_already_present_count,
                NEW.empty_noop_count,
                NEW.source_writer_stop_receipt_sha256,
                NEW.target_writer_stop_receipt_sha256,
                NEW.membership_writer_stop_receipt_sha256,
                NEW.connection_drain_receipt_sha256,
                NEW.connection_rejection_receipt_sha256,
                NEW.restored_backup_receipt_sha256,
                NEW.apply_authorization_receipt_sha256,
                NEW.legacy_runtime_disabled_receipt_sha256)
               IS DISTINCT FROM
               (OLD.migrated_count,
                OLD.target_already_present_count,
                OLD.empty_noop_count,
                OLD.source_writer_stop_receipt_sha256,
                OLD.target_writer_stop_receipt_sha256,
                OLD.membership_writer_stop_receipt_sha256,
                OLD.connection_drain_receipt_sha256,
                OLD.connection_rejection_receipt_sha256,
                OLD.restored_backup_receipt_sha256,
                OLD.apply_authorization_receipt_sha256,
                OLD.legacy_runtime_disabled_receipt_sha256) THEN
                RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'blocked run mutated';
            END IF;
        ELSE
            RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'illegal run transition';
        END IF;
    END IF;

    INSERT INTO ti_migration.personal_bank_tag_audit (
        migration_id, migration_run_uuid, event_type,
        from_state, to_state, state_version, failure_code
    ) VALUES (
        NEW.migration_id,
        NEW.migration_run_uuid,
        CASE
            WHEN TG_OP = 'INSERT' THEN 'PREPARED'
            ELSE NEW.state
        END,
        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.state END,
        NEW.state,
        NEW.version,
        NEW.blocked_failure_code
    );
    RETURN NEW;
END;
$$;

CREATE FUNCTION ti_migration.personal_bank_tag_reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'append-only relation';
END;
$$;

CREATE FUNCTION ti_migration.personal_bank_tag_run_source_insert_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, ti_migration
AS $$
DECLARE
    requested_count integer;
    requested_state text;
BEGIN
    SELECT source_count, state
    INTO requested_count, requested_state
    FROM ti_migration.personal_bank_tag_run
    WHERE migration_id = NEW.migration_id
      AND migration_run_uuid = NEW.migration_run_uuid;
    IF requested_state <> 'PLANNED' OR requested_count IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'manifest run is not planned';
    END IF;
    IF (SELECT count(*) FROM ti_migration.personal_bank_tag_run_source
        WHERE migration_id = NEW.migration_id
          AND migration_run_uuid = NEW.migration_run_uuid) >= requested_count THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'manifest count exceeded';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION ti_migration.personal_bank_tag_manifest_complete_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, ti_migration
AS $$
DECLARE
    requested_migration_id uuid;
    requested_run_uuid uuid;
    expected_count integer;
    actual_count integer;
BEGIN
    requested_migration_id := NEW.migration_id;
    requested_run_uuid := NEW.migration_run_uuid;
    SELECT source_count INTO expected_count
    FROM ti_migration.personal_bank_tag_run
    WHERE migration_id = requested_migration_id
      AND migration_run_uuid = requested_run_uuid;
    SELECT count(*) INTO actual_count
    FROM ti_migration.personal_bank_tag_run_source
    WHERE migration_id = requested_migration_id
      AND migration_run_uuid = requested_run_uuid;
    IF expected_count IS NULL OR actual_count <> expected_count THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'manifest incomplete';
    END IF;
    RETURN NULL;
END;
$$;

CREATE FUNCTION ti_migration.personal_bank_tag_receipt_insert_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, ti_migration
AS $$
DECLARE
    manifest ti_migration.personal_bank_tag_run_source%ROWTYPE;
    requested_run ti_migration.personal_bank_tag_run%ROWTYPE;
BEGIN
    SELECT * INTO manifest
    FROM ti_migration.personal_bank_tag_run_source
    WHERE migration_id = NEW.migration_id
      AND migration_run_uuid = NEW.migration_run_uuid
      AND source_row_id = NEW.source_row_id;
    SELECT * INTO requested_run
    FROM ti_migration.personal_bank_tag_run
    WHERE migration_id = NEW.migration_id
      AND migration_run_uuid = NEW.migration_run_uuid;
    IF requested_run.state <> 'APPLYING'
       OR NEW.backup_manifest_sha256
            <> requested_run.backup_manifest_sha256
       OR NEW.cluster_database_identity_sha256
            <> requested_run.cluster_database_identity_sha256
       OR NEW.run_identity_sha256 <> requested_run.run_identity_sha256
       OR NEW.preflight_digest_sha256
            <> requested_run.preflight_digest_sha256
       OR NEW.source_set_digest_sha256
            <> requested_run.source_set_digest_sha256
       OR NEW.plan_set_digest_sha256
            <> requested_run.plan_set_digest_sha256
       OR NEW.preapply_target_set_digest_sha256
            <> requested_run.preapply_target_set_digest_sha256
       OR NEW.final_target_set_digest_sha256
            <> requested_run.final_target_set_digest_sha256
       OR NEW.membership_set_digest_sha256
            <> requested_run.membership_set_digest_sha256
       OR NEW.source_writer_stop_receipt_sha256
            <> requested_run.source_writer_stop_receipt_sha256
       OR NEW.target_writer_stop_receipt_sha256
            <> requested_run.target_writer_stop_receipt_sha256
       OR NEW.membership_writer_stop_receipt_sha256
            <> requested_run.membership_writer_stop_receipt_sha256
       OR NEW.connection_drain_receipt_sha256
            <> requested_run.connection_drain_receipt_sha256
       OR NEW.connection_rejection_receipt_sha256
            <> requested_run.connection_rejection_receipt_sha256
       OR NEW.restored_backup_receipt_sha256
            <> requested_run.restored_backup_receipt_sha256
       OR NEW.apply_authorization_receipt_sha256
            <> requested_run.apply_authorization_receipt_sha256
       OR NEW.legacy_runtime_disabled_receipt_sha256
            <> requested_run.legacy_runtime_disabled_receipt_sha256
       OR NEW.disposition <> manifest.disposition
       OR NEW.key_digest_sha256 <> manifest.key_digest_sha256
       OR NEW.source_digest_sha256 <> manifest.source_digest_sha256
       OR NEW.plan_digest_sha256 <> manifest.plan_digest_sha256
       OR NEW.expected_target_digest_sha256 <> manifest.expected_target_digest_sha256
       OR NEW.membership_digest_sha256 <> manifest.membership_digest_sha256
       OR NEW.actual_target_digest_sha256 <> manifest.expected_target_digest_sha256
       OR NEW.inserted_target_row_count <>
          (CASE WHEN manifest.disposition = 'MIGRATED'
                THEN manifest.plan_row_count ELSE 0 END) THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'invalid receipt';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION ti_migration.personal_bank_tag_receipt_commit_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, ti_migration
AS $$
DECLARE
    manifest ti_migration.personal_bank_tag_run_source%ROWTYPE;
    actual_digest char(64);
    actual_count integer;
BEGIN
    SELECT * INTO manifest
    FROM ti_migration.personal_bank_tag_run_source
    WHERE migration_id = NEW.migration_id
      AND migration_run_uuid = NEW.migration_run_uuid
      AND source_row_id = NEW.source_row_id;
    actual_digest := ti_migration.personal_bank_tag_target_digest(
        manifest.user_id, manifest.bank_id
    );
    SELECT count(*) INTO actual_count
    FROM public.user_question_tag_items
    WHERE user_id = manifest.user_id
      AND scope = 'user_bank'
      AND scope_id = manifest.bank_id;
    IF actual_digest <> NEW.actual_target_digest_sha256
       OR actual_digest <> manifest.expected_target_digest_sha256
       OR actual_count <> manifest.expected_final_target_row_count THEN
        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'receipt target mismatch';
    END IF;
    RETURN NULL;
END;
$$;

CREATE FUNCTION ti_migration.personal_bank_tag_target_insert_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, ti_migration
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM ti_migration.personal_bank_tag_receipt AS receipt
        JOIN ti_migration.personal_bank_tag_run_source AS source
          ON source.migration_id = receipt.migration_id
         AND source.migration_run_uuid = receipt.migration_run_uuid
         AND source.source_row_id = receipt.source_row_id
        JOIN ti_migration.personal_bank_tag_run AS run
          ON run.migration_id = receipt.migration_id
         AND run.migration_run_uuid = receipt.migration_run_uuid
        WHERE source.user_id = NEW.user_id
          AND source.bank_id = NEW.scope_id
          AND NEW.scope = 'user_bank'
          AND source.disposition = 'MIGRATED'
          AND receipt.created_txid = txid_current()
          AND run.state = 'APPLYING'
    ) THEN
        RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'target insert lacks receipt';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER personal_bank_tag_run_transition_guard
BEFORE INSERT OR UPDATE OR DELETE
ON ti_migration.personal_bank_tag_run
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_run_guard();

CREATE TRIGGER personal_bank_tag_run_source_insert_guard
BEFORE INSERT
ON ti_migration.personal_bank_tag_run_source
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_run_source_insert_guard();

CREATE TRIGGER personal_bank_tag_run_source_immutable
BEFORE UPDATE OR DELETE
ON ti_migration.personal_bank_tag_run_source
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_reject_mutation();

CREATE CONSTRAINT TRIGGER personal_bank_tag_manifest_complete_from_run
AFTER INSERT ON ti_migration.personal_bank_tag_run
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_manifest_complete_guard();

CREATE CONSTRAINT TRIGGER personal_bank_tag_manifest_complete_from_source
AFTER INSERT ON ti_migration.personal_bank_tag_run_source
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_manifest_complete_guard();

CREATE TRIGGER personal_bank_tag_receipt_insert_guard
BEFORE INSERT
ON ti_migration.personal_bank_tag_receipt
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_receipt_insert_guard();

CREATE TRIGGER personal_bank_tag_receipt_append_only
BEFORE UPDATE OR DELETE
ON ti_migration.personal_bank_tag_receipt
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_reject_mutation();

CREATE CONSTRAINT TRIGGER personal_bank_tag_receipt_commit_guard
AFTER INSERT ON ti_migration.personal_bank_tag_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_receipt_commit_guard();

CREATE TRIGGER personal_bank_tag_audit_append_only
BEFORE UPDATE OR DELETE
ON ti_migration.personal_bank_tag_audit
FOR EACH ROW
EXECUTE FUNCTION ti_migration.personal_bank_tag_reject_mutation();

CREATE TRIGGER personal_bank_tag_audit_truncate_guard
BEFORE TRUNCATE
ON ti_migration.personal_bank_tag_audit
FOR EACH STATEMENT
EXECUTE FUNCTION ti_migration.personal_bank_tag_reject_mutation();

ALTER SCHEMA ti_migration OWNER TO ti_phase4c_tag_schema_owner;
ALTER TABLE ti_migration.operator_schema_metadata
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER TABLE ti_migration.personal_bank_tag_run
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER TABLE ti_migration.personal_bank_tag_run_source
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER TABLE ti_migration.personal_bank_tag_receipt
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER TABLE ti_migration.personal_bank_tag_audit
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER SEQUENCE ti_migration.personal_bank_tag_audit_audit_id_seq
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_target_digest(bigint, integer)
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_run_guard()
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_reject_mutation()
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_run_source_insert_guard()
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_manifest_complete_guard()
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_receipt_insert_guard()
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_receipt_commit_guard()
    OWNER TO ti_phase4c_tag_schema_owner;
ALTER FUNCTION ti_migration.personal_bank_tag_target_insert_guard()
    OWNER TO ti_phase4c_tag_schema_owner;

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ti_migration FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ti_migration FROM ti_phase4c_tag_operator;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM ti_phase4c_tag_operator;
REVOKE ALL ON ALL TABLES IN SCHEMA ti_migration FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA ti_migration FROM ti_phase4c_tag_operator;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA ti_migration FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA ti_migration FROM ti_phase4c_tag_operator;

GRANT USAGE ON SCHEMA public TO ti_phase4c_tag_schema_owner;
GRANT SELECT ON public.user_question_tag_items
TO ti_phase4c_tag_schema_owner;

GRANT SELECT ON ti_migration.operator_schema_metadata
TO ti_phase4c_tag_operator;
GRANT SELECT, INSERT, UPDATE ON ti_migration.personal_bank_tag_run
TO ti_phase4c_tag_operator;
GRANT SELECT, INSERT ON ti_migration.personal_bank_tag_run_source
TO ti_phase4c_tag_operator;
GRANT SELECT, INSERT ON ti_migration.personal_bank_tag_receipt
TO ti_phase4c_tag_operator;

REVOKE ALL ON public.user_progress FROM ti_phase4c_tag_operator;
GRANT SELECT ON public.user_progress TO ti_phase4c_tag_operator;
REVOKE ALL ON public.user_question_tag_items FROM ti_phase4c_tag_operator;
GRANT SELECT, INSERT ON public.user_question_tag_items
TO ti_phase4c_tag_operator;
