-- Phase 4C Node B test-only durable-ledger/freeze protocol fixture.
-- This is not a Flyway migration, production relation, operator, or cutover.

CREATE ROLE ti_phase4c_tag_design_operator
    NOLOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

-- Phase 2 already removes PUBLIC TEMPORARY. This fixture also removes the
-- inherited PUBLIC CONNECT capability so the NOLOGIN role has neither a
-- credential nor effective database CONNECT privilege.
DO $$
BEGIN
    EXECUTE format(
        'REVOKE CONNECT ON DATABASE %I FROM PUBLIC',
        current_database()
    );
    EXECUTE format(
        'REVOKE CONNECT ON DATABASE %I FROM ti_phase4c_tag_design_operator',
        current_database()
    );
END;
$$;

GRANT USAGE ON SCHEMA public
TO ti_phase4c_tag_design_operator;

CREATE TABLE phase4c_tag_migration_design_source (
    source_row_id bigint PRIMARY KEY,
    user_id bigint NOT NULL,
    legacy_key text NOT NULL,
    legacy_payload text NOT NULL
);

CREATE TABLE phase4c_tag_migration_design_membership (
    bank_id integer NOT NULL,
    question_id integer NOT NULL,
    PRIMARY KEY (bank_id, question_id)
);

CREATE TABLE phase4c_tag_migration_design_ledger (
    migration_id uuid PRIMARY KEY,
    state text NOT NULL CHECK (
        state IN ('PLANNED', 'FROZEN', 'APPLYING', 'APPLIED', 'BLOCKED')
    ),
    version integer NOT NULL CHECK (version >= 0),
    migration_run_uuid uuid NOT NULL UNIQUE,
    backup_manifest_sha256 char(64) NOT NULL CHECK (
        backup_manifest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    cluster_database_identity_sha256 char(64) NOT NULL CHECK (
        cluster_database_identity_sha256 ~ '^[0-9a-f]{64}$'
    ),
    database_identity_sha256 char(64) NOT NULL CHECK (
        database_identity_sha256 ~ '^[0-9a-f]{64}$'
    ),
    preflight_digest_sha256 char(64) NOT NULL CHECK (
        preflight_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    plan_digest_sha256 char(64) NOT NULL CHECK (
        plan_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    source_digest_sha256 char(64) NOT NULL CHECK (
        source_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    target_digest_sha256 char(64) NOT NULL CHECK (
        target_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    membership_digest_sha256 char(64) NOT NULL CHECK (
        membership_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    source_writer_stop_receipt_sha256 char(64) CHECK (
        source_writer_stop_receipt_sha256 IS NULL
        OR source_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    target_writer_stop_receipt_sha256 char(64) CHECK (
        target_writer_stop_receipt_sha256 IS NULL
        OR target_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    membership_writer_stop_receipt_sha256 char(64) CHECK (
        membership_writer_stop_receipt_sha256 IS NULL
        OR membership_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    restored_backup_sha256 char(64) CHECK (
        restored_backup_sha256 IS NULL
        OR restored_backup_sha256 ~ '^[0-9a-f]{64}$'
    ),
    blocked_code text CHECK (
        blocked_code IS NULL
        OR blocked_code IN (
            'DIGEST_DRIFT',
            'RECEIPT_MISMATCH',
            'TARGET_MISMATCH',
            'IDENTITY_MISMATCH',
            'ILLEGAL_STATE'
        )
    ),
    created_at timestamp with time zone NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamp with time zone NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (
        migration_id,
        migration_run_uuid,
        backup_manifest_sha256,
        cluster_database_identity_sha256,
        database_identity_sha256,
        preflight_digest_sha256,
        plan_digest_sha256,
        source_digest_sha256,
        target_digest_sha256,
        membership_digest_sha256,
        source_writer_stop_receipt_sha256,
        target_writer_stop_receipt_sha256,
        membership_writer_stop_receipt_sha256,
        restored_backup_sha256
    ),
    CHECK (
        (state = 'PLANNED' AND version = 0)
        OR (state = 'FROZEN' AND version = 1)
        OR (state = 'APPLYING' AND version = 2)
        OR (state = 'APPLIED' AND version = 3)
        OR (state = 'BLOCKED' AND version BETWEEN 1 AND 3)
    ),
    CHECK (
        state IN ('PLANNED', 'BLOCKED')
        OR (
            source_writer_stop_receipt_sha256 IS NOT NULL
            AND target_writer_stop_receipt_sha256 IS NOT NULL
            AND membership_writer_stop_receipt_sha256 IS NOT NULL
            AND restored_backup_sha256 IS NOT NULL
        )
    ),
    CHECK (
        (state = 'BLOCKED' AND blocked_code IS NOT NULL)
        OR (state <> 'BLOCKED' AND blocked_code IS NULL)
    )
);

CREATE TABLE phase4c_tag_migration_design_receipt (
    migration_id uuid NOT NULL,
    source_row_id bigint NOT NULL
        REFERENCES phase4c_tag_migration_design_source (source_row_id),
    migration_run_uuid uuid NOT NULL,
    backup_manifest_sha256 char(64) NOT NULL CHECK (
        backup_manifest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    cluster_database_identity_sha256 char(64) NOT NULL CHECK (
        cluster_database_identity_sha256 ~ '^[0-9a-f]{64}$'
    ),
    database_identity_sha256 char(64) NOT NULL CHECK (
        database_identity_sha256 ~ '^[0-9a-f]{64}$'
    ),
    preflight_digest_sha256 char(64) NOT NULL CHECK (
        preflight_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    source_digest_sha256 char(64) NOT NULL CHECK (
        source_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    plan_digest_sha256 char(64) NOT NULL CHECK (
        plan_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    target_digest_sha256 char(64) NOT NULL CHECK (
        target_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    membership_digest_sha256 char(64) NOT NULL CHECK (
        membership_digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    source_writer_stop_receipt_sha256 char(64) NOT NULL CHECK (
        source_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    target_writer_stop_receipt_sha256 char(64) NOT NULL CHECK (
        target_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    membership_writer_stop_receipt_sha256 char(64) NOT NULL CHECK (
        membership_writer_stop_receipt_sha256 ~ '^[0-9a-f]{64}$'
    ),
    restored_backup_sha256 char(64) NOT NULL CHECK (
        restored_backup_sha256 ~ '^[0-9a-f]{64}$'
    ),
    disposition text NOT NULL CHECK (
        disposition IN ('MIGRATED', 'TARGET_ALREADY_PRESENT', 'EMPTY_NOOP')
    ),
    applied_target_row_count integer NOT NULL CHECK (
        applied_target_row_count >= 0
    ),
    committed_at timestamp with time zone NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (migration_id, source_row_id),
    FOREIGN KEY (
        migration_id,
        migration_run_uuid,
        backup_manifest_sha256,
        cluster_database_identity_sha256,
        database_identity_sha256,
        preflight_digest_sha256,
        plan_digest_sha256,
        source_digest_sha256,
        target_digest_sha256,
        membership_digest_sha256,
        source_writer_stop_receipt_sha256,
        target_writer_stop_receipt_sha256,
        membership_writer_stop_receipt_sha256,
        restored_backup_sha256
    ) REFERENCES phase4c_tag_migration_design_ledger (
        migration_id,
        migration_run_uuid,
        backup_manifest_sha256,
        cluster_database_identity_sha256,
        database_identity_sha256,
        preflight_digest_sha256,
        plan_digest_sha256,
        source_digest_sha256,
        target_digest_sha256,
        membership_digest_sha256,
        source_writer_stop_receipt_sha256,
        target_writer_stop_receipt_sha256,
        membership_writer_stop_receipt_sha256,
        restored_backup_sha256
    ),
    CHECK (
        (disposition = 'EMPTY_NOOP' AND applied_target_row_count = 0)
        OR (
            disposition IN ('MIGRATED', 'TARGET_ALREADY_PRESENT')
            AND applied_target_row_count > 0
        )
    )
);

CREATE TABLE phase4c_tag_migration_design_target (
    migration_id uuid NOT NULL,
    source_row_id bigint NOT NULL,
    question_id integer NOT NULL CHECK (question_id >= 0),
    tag text NOT NULL CHECK (length(tag) BETWEEN 1 AND 20),
    PRIMARY KEY (migration_id, source_row_id, question_id, tag),
    FOREIGN KEY (migration_id, source_row_id)
        REFERENCES phase4c_tag_migration_design_receipt
        (migration_id, source_row_id)
);

CREATE TABLE phase4c_tag_migration_design_mutation_audit (
    audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    relation_name text NOT NULL,
    operation text NOT NULL,
    migration_id uuid NOT NULL,
    source_row_id bigint,
    occurred_at timestamp with time zone NOT NULL DEFAULT clock_timestamp()
);

-- Row audit proves committed row effects. The separate statement audit also
-- observes zero-row UPDATE and INSERT ... ON CONFLICT DO NOTHING attempts.
CREATE TABLE phase4c_tag_migration_design_statement_audit (
    audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    relation_name text NOT NULL,
    operation text NOT NULL,
    occurred_at timestamp with time zone NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE phase4c_tag_migration_design_retry_counter (
    counter_id integer PRIMARY KEY,
    value integer NOT NULL
);

CREATE TABLE phase4c_tag_migration_design_retry_locks (
    lock_id integer PRIMARY KEY,
    value integer NOT NULL
);

-- The caller cannot supply a target-fact digest. PostgreSQL derives one from
-- the distinct canonical (question_id, tag) fact set, sorted bytewise. Each
-- field is UTF-8 byte-length-prefixed, so delimiters inside a tag are harmless.
CREATE FUNCTION phase4c_tag_migration_design_canonical_target_digest(
    requested_migration_id uuid
)
RETURNS char(64)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
    SELECT encode(
        sha256(
            convert_to(
                'ti:phase4c:tag-migration:canonical-target-facts:v1'
                || chr(10)
                || coalesce(
                    string_agg(
                        octet_length(question_id::text)::text
                        || ':' || question_id::text
                        || octet_length(convert_to(tag, 'UTF8'))::text
                        || ':' || tag,
                        '' ORDER BY question_id, tag COLLATE "C"
                    ),
                    ''
                ),
                'UTF8'
            )
        ),
        'hex'
    )::char(64)
    FROM (
        SELECT DISTINCT question_id, tag
        FROM public.phase4c_tag_migration_design_target
        WHERE migration_id = requested_migration_id
    ) AS canonical_facts
$$;

-- APPLIED is valid only when every frozen source row has one explicit
-- disposition receipt. EMPTY_NOOP is a receipt with zero target rows; the two
-- material dispositions require at least one row. Counts and the database-
-- derived canonical target digest must agree with every receipt and the ledger.
CREATE FUNCTION phase4c_tag_migration_design_validate_complete_dispositions(
    requested_migration_id uuid,
    expected_target_digest char(64)
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    source_count bigint;
    receipt_count bigint;
    canonical_target_digest char(64);
BEGIN
    SELECT count(*)
    INTO source_count
    FROM public.phase4c_tag_migration_design_source;

    SELECT count(*)
    INTO receipt_count
    FROM public.phase4c_tag_migration_design_receipt
    WHERE migration_id = requested_migration_id;

    canonical_target_digest :=
        public.phase4c_tag_migration_design_canonical_target_digest(
            requested_migration_id
        );

    IF source_count = 0
       OR receipt_count <> source_count
       OR canonical_target_digest IS DISTINCT FROM expected_target_digest
       OR EXISTS (
           SELECT 1
           FROM public.phase4c_tag_migration_design_source AS source
           LEFT JOIN public.phase4c_tag_migration_design_receipt AS receipt
             ON receipt.migration_id = requested_migration_id
            AND receipt.source_row_id = source.source_row_id
           LEFT JOIN LATERAL (
               SELECT count(*)::integer AS actual_target_count
               FROM public.phase4c_tag_migration_design_target AS target
               WHERE target.migration_id = requested_migration_id
                 AND target.source_row_id = source.source_row_id
           ) AS target_count ON true
           WHERE receipt.source_row_id IS NULL
              OR receipt.target_digest_sha256
                    IS DISTINCT FROM expected_target_digest
              OR receipt.applied_target_row_count
                    IS DISTINCT FROM target_count.actual_target_count
              OR (
                  receipt.disposition = 'EMPTY_NOOP'
                  AND target_count.actual_target_count <> 0
              )
              OR (
                  receipt.disposition IN (
                      'MIGRATED',
                      'TARGET_ALREADY_PRESENT'
                  )
                  AND target_count.actual_target_count = 0
              )
       ) THEN
        RAISE EXCEPTION
            'APPLIED requires complete dispositions and canonical target digest'
            USING ERRCODE = '23514';
    END IF;
END;
$$;

CREATE FUNCTION phase4c_tag_migration_design_guard_ledger_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.state <> 'PLANNED'
       OR NEW.version <> 0
       OR NEW.blocked_code IS NOT NULL
       OR NEW.source_writer_stop_receipt_sha256 IS NOT NULL
       OR NEW.target_writer_stop_receipt_sha256 IS NOT NULL
       OR NEW.membership_writer_stop_receipt_sha256 IS NOT NULL
       OR NEW.restored_backup_sha256 IS NOT NULL THEN
        RAISE EXCEPTION 'ledger must be inserted as clean PLANNED(v0)'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER phase4c_tag_migration_design_ledger_insert_guard
BEFORE INSERT ON phase4c_tag_migration_design_ledger
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_guard_ledger_insert();

CREATE FUNCTION phase4c_tag_migration_design_guard_ledger_transition()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    IF NEW.migration_id <> OLD.migration_id
       OR NEW.created_at <> OLD.created_at
       OR NEW.migration_run_uuid <> OLD.migration_run_uuid
       OR NEW.backup_manifest_sha256 <> OLD.backup_manifest_sha256
       OR NEW.cluster_database_identity_sha256
          <> OLD.cluster_database_identity_sha256
       OR NEW.database_identity_sha256 <> OLD.database_identity_sha256
       OR NEW.preflight_digest_sha256 <> OLD.preflight_digest_sha256
       OR NEW.plan_digest_sha256 <> OLD.plan_digest_sha256
       OR NEW.source_digest_sha256 <> OLD.source_digest_sha256
       OR NEW.target_digest_sha256 <> OLD.target_digest_sha256
       OR NEW.membership_digest_sha256 <> OLD.membership_digest_sha256 THEN
        RAISE EXCEPTION 'immutable ledger identity/digest changed'
            USING ERRCODE = '23514';
    END IF;

    IF OLD.state <> 'PLANNED'
       AND (
           NEW.source_writer_stop_receipt_sha256
               IS DISTINCT FROM OLD.source_writer_stop_receipt_sha256
           OR NEW.target_writer_stop_receipt_sha256
               IS DISTINCT FROM OLD.target_writer_stop_receipt_sha256
           OR NEW.membership_writer_stop_receipt_sha256
               IS DISTINCT FROM OLD.membership_writer_stop_receipt_sha256
           OR NEW.restored_backup_sha256
               IS DISTINCT FROM OLD.restored_backup_sha256
       ) THEN
        RAISE EXCEPTION 'frozen stop/backup receipts are immutable'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'ledger version must advance by one'
            USING ERRCODE = '23514';
    END IF;

    IF NOT (
        (OLD.state = 'PLANNED' AND NEW.state IN ('FROZEN', 'BLOCKED'))
        OR (OLD.state = 'FROZEN' AND NEW.state IN ('APPLYING', 'BLOCKED'))
        OR (OLD.state = 'APPLYING' AND NEW.state IN ('APPLIED', 'BLOCKED'))
    ) THEN
        RAISE EXCEPTION 'illegal durable-ledger transition'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.state = 'APPLIED' THEN
        PERFORM public.phase4c_tag_migration_design_validate_complete_dispositions(
            NEW.migration_id,
            NEW.target_digest_sha256
        );
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER phase4c_tag_migration_design_ledger_transition_guard
BEFORE UPDATE ON phase4c_tag_migration_design_ledger
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_guard_ledger_transition();

CREATE FUNCTION phase4c_tag_migration_design_reject_receipt_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'migration receipts are append-only'
        USING ERRCODE = '55000';
END;
$$;

CREATE TRIGGER phase4c_tag_migration_design_receipt_append_only
BEFORE UPDATE OR DELETE ON phase4c_tag_migration_design_receipt
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_reject_receipt_mutation();

CREATE FUNCTION phase4c_tag_migration_design_guard_apply_insert()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    ledger_state text;
    ledger_run_uuid uuid;
    ledger_backup char(64);
    ledger_cluster char(64);
    ledger_identity char(64);
    ledger_preflight char(64);
    ledger_plan char(64);
    ledger_source char(64);
    ledger_target char(64);
    ledger_membership char(64);
    ledger_source_stop char(64);
    ledger_target_stop char(64);
    ledger_membership_stop char(64);
    ledger_restored_backup char(64);
BEGIN
    SELECT state,
           migration_run_uuid,
           backup_manifest_sha256,
           cluster_database_identity_sha256,
           database_identity_sha256,
           preflight_digest_sha256,
           plan_digest_sha256,
           source_digest_sha256,
           target_digest_sha256,
           membership_digest_sha256,
           source_writer_stop_receipt_sha256,
           target_writer_stop_receipt_sha256,
           membership_writer_stop_receipt_sha256,
           restored_backup_sha256
    INTO ledger_state,
         ledger_run_uuid,
         ledger_backup,
         ledger_cluster,
         ledger_identity,
         ledger_preflight,
         ledger_plan,
         ledger_source,
         ledger_target,
         ledger_membership,
         ledger_source_stop,
         ledger_target_stop,
         ledger_membership_stop,
         ledger_restored_backup
    FROM public.phase4c_tag_migration_design_ledger
    WHERE migration_id = NEW.migration_id
    FOR KEY SHARE;

    IF ledger_state IS DISTINCT FROM 'APPLYING' THEN
        RAISE EXCEPTION 'receipt/target insert requires APPLYING ledger'
            USING ERRCODE = '23514';
    END IF;

    IF TG_TABLE_NAME = 'phase4c_tag_migration_design_receipt' THEN
        IF NEW.migration_run_uuid IS DISTINCT FROM ledger_run_uuid
           OR NEW.backup_manifest_sha256 IS DISTINCT FROM ledger_backup
           OR NEW.cluster_database_identity_sha256 IS DISTINCT FROM ledger_cluster
           OR NEW.database_identity_sha256 IS DISTINCT FROM ledger_identity
           OR NEW.preflight_digest_sha256 IS DISTINCT FROM ledger_preflight
           OR NEW.plan_digest_sha256 IS DISTINCT FROM ledger_plan
           OR NEW.source_digest_sha256 IS DISTINCT FROM ledger_source
           OR NEW.target_digest_sha256 IS DISTINCT FROM ledger_target
           OR NEW.membership_digest_sha256 IS DISTINCT FROM ledger_membership
           OR NEW.source_writer_stop_receipt_sha256
               IS DISTINCT FROM ledger_source_stop
           OR NEW.target_writer_stop_receipt_sha256
               IS DISTINCT FROM ledger_target_stop
           OR NEW.membership_writer_stop_receipt_sha256
               IS DISTINCT FROM ledger_membership_stop
           OR NEW.restored_backup_sha256
               IS DISTINCT FROM ledger_restored_backup THEN
            RAISE EXCEPTION 'receipt identity/digest does not match ledger'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER phase4c_tag_migration_design_receipt_insert_guard
BEFORE INSERT ON phase4c_tag_migration_design_receipt
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_guard_apply_insert();

CREATE TRIGGER phase4c_tag_migration_design_target_insert_guard
BEFORE INSERT ON phase4c_tag_migration_design_target
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_guard_apply_insert();

CREATE FUNCTION phase4c_tag_migration_design_require_applied_at_commit()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    ledger_state text;
    ledger_target_digest char(64);
    expected_target_count integer;
    actual_target_count integer;
BEGIN
    SELECT state, target_digest_sha256
    INTO ledger_state, ledger_target_digest
    FROM public.phase4c_tag_migration_design_ledger
    WHERE migration_id = NEW.migration_id;

    IF ledger_state IS DISTINCT FROM 'APPLIED' THEN
        RAISE EXCEPTION 'receipt/target commit requires APPLIED ledger'
            USING ERRCODE = '23514';
    END IF;

    PERFORM public.phase4c_tag_migration_design_validate_complete_dispositions(
        NEW.migration_id,
        ledger_target_digest
    );

    SELECT applied_target_row_count
    INTO expected_target_count
    FROM public.phase4c_tag_migration_design_receipt
    WHERE migration_id = NEW.migration_id
      AND source_row_id = NEW.source_row_id;

    SELECT count(*)
    INTO actual_target_count
    FROM public.phase4c_tag_migration_design_target
    WHERE migration_id = NEW.migration_id
      AND source_row_id = NEW.source_row_id;

    IF expected_target_count IS NULL
       OR expected_target_count <> actual_target_count THEN
        RAISE EXCEPTION 'receipt target count mismatch at commit'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION
phase4c_tag_migration_design_require_complete_applied_transition_at_commit()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    current_state text;
    current_target_digest char(64);
BEGIN
    IF NEW.state <> 'APPLIED' THEN
        RETURN NEW;
    END IF;

    SELECT state, target_digest_sha256
    INTO current_state, current_target_digest
    FROM public.phase4c_tag_migration_design_ledger
    WHERE migration_id = NEW.migration_id;

    IF current_state IS DISTINCT FROM 'APPLIED' THEN
        RAISE EXCEPTION 'APPLIED transition did not remain terminal at commit'
            USING ERRCODE = '23514';
    END IF;

    PERFORM public.phase4c_tag_migration_design_validate_complete_dispositions(
        NEW.migration_id,
        current_target_digest
    );
    RETURN NEW;
END;
$$;

CREATE CONSTRAINT TRIGGER
phase4c_tag_migration_design_ledger_applied_commit_guard
AFTER UPDATE ON phase4c_tag_migration_design_ledger
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION
phase4c_tag_migration_design_require_complete_applied_transition_at_commit();

CREATE CONSTRAINT TRIGGER phase4c_tag_migration_design_receipt_commit_guard
AFTER INSERT ON phase4c_tag_migration_design_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_require_applied_at_commit();

CREATE CONSTRAINT TRIGGER phase4c_tag_migration_design_target_commit_guard
AFTER INSERT ON phase4c_tag_migration_design_target
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_require_applied_at_commit();

CREATE FUNCTION phase4c_tag_migration_design_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    row_value jsonb;
BEGIN
    IF TG_OP = 'DELETE' THEN
        row_value := to_jsonb(OLD);
    ELSE
        row_value := to_jsonb(NEW);
    END IF;
    INSERT INTO public.phase4c_tag_migration_design_mutation_audit (
        relation_name,
        operation,
        migration_id,
        source_row_id
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP,
        (row_value ->> 'migration_id')::uuid,
        NULLIF(row_value ->> 'source_row_id', '')::bigint
    );
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER phase4c_tag_migration_design_audit_ledger
AFTER INSERT OR UPDATE OR DELETE ON phase4c_tag_migration_design_ledger
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_audit_mutation();

CREATE TRIGGER phase4c_tag_migration_design_audit_receipt
AFTER INSERT OR UPDATE OR DELETE ON phase4c_tag_migration_design_receipt
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_audit_mutation();

CREATE TRIGGER phase4c_tag_migration_design_audit_target
AFTER INSERT OR UPDATE OR DELETE ON phase4c_tag_migration_design_target
FOR EACH ROW
EXECUTE FUNCTION phase4c_tag_migration_design_audit_mutation();

CREATE FUNCTION phase4c_tag_migration_design_audit_statement()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    INSERT INTO public.phase4c_tag_migration_design_statement_audit (
        relation_name,
        operation
    ) VALUES (
        TG_TABLE_NAME,
        TG_OP
    );
    RETURN NULL;
END;
$$;

CREATE TRIGGER phase4c_tag_migration_design_statement_audit_ledger
AFTER INSERT OR UPDATE OR DELETE ON phase4c_tag_migration_design_ledger
FOR EACH STATEMENT
EXECUTE FUNCTION phase4c_tag_migration_design_audit_statement();

CREATE TRIGGER phase4c_tag_migration_design_statement_audit_receipt
AFTER INSERT OR UPDATE OR DELETE ON phase4c_tag_migration_design_receipt
FOR EACH STATEMENT
EXECUTE FUNCTION phase4c_tag_migration_design_audit_statement();

CREATE TRIGGER phase4c_tag_migration_design_statement_audit_target
AFTER INSERT OR UPDATE OR DELETE ON phase4c_tag_migration_design_target
FOR EACH STATEMENT
EXECUTE FUNCTION phase4c_tag_migration_design_audit_statement();

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public
FROM ti_phase4c_tag_design_operator;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public
FROM ti_phase4c_tag_design_operator;
REVOKE EXECUTE ON FUNCTION
    phase4c_tag_migration_design_canonical_target_digest(uuid),
    phase4c_tag_migration_design_validate_complete_dispositions(
        uuid,
        character
    ),
    phase4c_tag_migration_design_guard_ledger_insert(),
    phase4c_tag_migration_design_guard_ledger_transition(),
    phase4c_tag_migration_design_reject_receipt_mutation(),
    phase4c_tag_migration_design_guard_apply_insert(),
    phase4c_tag_migration_design_require_applied_at_commit(),
    phase4c_tag_migration_design_require_complete_applied_transition_at_commit(),
    phase4c_tag_migration_design_audit_mutation(),
    phase4c_tag_migration_design_audit_statement()
FROM PUBLIC, ti_phase4c_tag_design_operator;

GRANT SELECT ON
    phase4c_tag_migration_design_source,
    phase4c_tag_migration_design_membership
TO ti_phase4c_tag_design_operator;

GRANT SELECT, INSERT, UPDATE ON
    phase4c_tag_migration_design_ledger
TO ti_phase4c_tag_design_operator;

GRANT SELECT, INSERT ON
    phase4c_tag_migration_design_receipt,
    phase4c_tag_migration_design_target
TO ti_phase4c_tag_design_operator;
