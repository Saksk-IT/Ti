-- Phase 4C Node D local disposable rehearsal expectations. All values are
-- public test constants; no credential, key material, signature, raw tag, or
-- production-derived value is stored here.

INSERT INTO phase4c_tag_execution_fixture.writer_expectation (
    writer_id,
    runtime_name,
    component_name,
    application_name,
    local_disposable_only
) VALUES
    ('legacy_web', 'legacy', 'web',
     'phase4c-rehearsal-legacy-web', true),
    ('legacy_worker', 'legacy', 'worker',
     'phase4c-rehearsal-legacy-worker', true),
    ('legacy_scheduler', 'legacy', 'scheduler',
     'phase4c-rehearsal-legacy-scheduler', true),
    ('java_web', 'java', 'web',
     'phase4c-rehearsal-java-web', true),
    ('java_worker', 'java', 'worker',
     'phase4c-rehearsal-java-worker', true),
    ('java_scheduler', 'java', 'scheduler',
     'phase4c-rehearsal-java-scheduler', true);

INSERT INTO phase4c_tag_execution_fixture.writer_domain_expectation (
    writer_id,
    writer_domain
)
SELECT writer.writer_id, domain_value.writer_domain
FROM phase4c_tag_execution_fixture.writer_expectation AS writer
CROSS JOIN (
    VALUES ('SOURCE'), ('TARGET'), ('MEMBERSHIP')
) AS domain_value(writer_domain);

INSERT INTO phase4c_tag_execution_fixture.phase_expectation (
    phase_name,
    phase_ordinal,
    freeze_receipts_required,
    apply_authorization_required,
    legacy_runtime_disabled_required
) VALUES
    ('PREPARE', 0, false, false, false),
    ('FREEZE', 1, true, false, false),
    ('APPLY', 2, true, true, true),
    ('RECOVERY', 3, true, true, true);

INSERT INTO phase4c_tag_execution_fixture.acl_sentinel (
    singleton,
    fixture_scope,
    public_marker_sha256
) VALUES (
    true,
    'local-disposable-backup-restore-rehearsal-only',
    '70e7ad017277f34c061515a53a4e7dfc62ce0d983d1459104dbf206bfb42f264'
);

ANALYZE phase4c_tag_execution_fixture.writer_expectation;
ANALYZE phase4c_tag_execution_fixture.writer_domain_expectation;
ANALYZE phase4c_tag_execution_fixture.phase_expectation;
ANALYZE phase4c_tag_execution_fixture.acl_sentinel;
