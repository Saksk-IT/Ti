-- Phase 4C Node B disposable evidence only. The canary must remain confined to
-- this source fixture and must never appear in ledger, receipt, audit, or JSON.

INSERT INTO phase4c_tag_migration_design_source (
    source_row_id,
    user_id,
    legacy_key,
    legacy_payload
) VALUES
    (
        98001,
        99001,
        'NODEB_SENSITIVE_CANARY_KEY_DO_NOT_PERSIST',
        '{"secret":"NODEB_SENSITIVE_CANARY_PAYLOAD_DO_NOT_PERSIST"}'
    ),
    (
        98002,
        99002,
        'bank_98002_tags',
        '{"tags":["alpha"],"question_tags":{"98102":["alpha"]}}'
    );

INSERT INTO phase4c_tag_migration_design_membership (bank_id, question_id)
VALUES (98002, 98102);

INSERT INTO phase4c_tag_migration_design_retry_counter (counter_id, value)
VALUES (1, 0);

INSERT INTO phase4c_tag_migration_design_retry_locks (lock_id, value)
VALUES (1, 0), (2, 0);
