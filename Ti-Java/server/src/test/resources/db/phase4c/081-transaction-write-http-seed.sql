-- Deterministic actors and questions for the Phase 4C transaction-write HTTP target.

INSERT INTO users (
    id,
    username,
    password_hash,
    is_admin,
    is_locked,
    session_version,
    is_subject_admin,
    is_notification_admin,
    has_password_set,
    last_active
) VALUES
    (
        99451,
        'phase4c_write_user',
        'unused-test-password-hash',
        false,
        false,
        11,
        false,
        false,
        true,
        TIMESTAMP '2026-01-01 00:00:00'
    ),
    (
        99452,
        'phase4c_write_admin',
        'unused-test-password-hash',
        true,
        false,
        13,
        false,
        false,
        true,
        TIMESTAMP '2026-01-02 00:00:00'
    );

INSERT INTO questions (
    id,
    subject_id,
    type,
    content,
    options,
    answer,
    analysis,
    tags,
    difficulty,
    source,
    created_by,
    updated_by
)
SELECT
    question_id,
    1,
    'single_choice',
    'Phase 4C transaction-write question ' || question_id,
    '[{"key":"A","value":"Alpha"},{"key":"B","value":"Beta"}]',
    '["A"]',
    'Phase 4C transaction-write explanation',
    '[]',
    1,
    'phase4c-http-fixture',
    99452,
    99452
FROM generate_series(93001, 93008) AS question_id;
