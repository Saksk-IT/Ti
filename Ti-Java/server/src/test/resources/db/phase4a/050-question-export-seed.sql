-- Phase 4A test-only rows for the HTTP-neutral catalog question-export snapshot.
-- This is neither a Flyway baseline nor a production migration.

ALTER TABLE questions ALTER COLUMN type DROP NOT NULL;
ALTER TABLE questions ALTER COLUMN content DROP NOT NULL;

INSERT INTO subjects (
    id,
    name,
    description,
    is_locked,
    plaza_board_id,
    is_plaza_featured,
    plaza_featured_weight,
    plaza_featured_at,
    created_at
) VALUES
    (
        -7,
        'Question export negative subject fixture',
        'PUBLIC TEST-ONLY synthetic negative-ID subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        0,
        'Question export zero subject fixture',
        'PUBLIC TEST-ONLY synthetic zero-ID subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        5001,
        '',
        'PUBLIC TEST-ONLY synthetic empty-name subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        5002,
        'Question export primary 🧪',
        'PUBLIC TEST-ONLY synthetic primary subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        5003,
        'Question export secondary subject',
        'PUBLIC TEST-ONLY synthetic secondary subject',
        true,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    );

INSERT INTO questions (
    id,
    subject_id,
    type,
    content,
    options,
    answer,
    analysis,
    difficulty,
    tags
) VALUES
    (
        -1,
        5003,
        'negative_question_id',
        'Legacy negative question ID remains a raw export fact',
        '[]',
        '[]',
        'negative-id-analysis',
        1,
        '[]'
    ),
    (
        0,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL
    ),
    (
        5004,
        -7,
        '',
        'Malformed and scalar JSON remains raw',
        '{not-json-options',
        'true',
        '',
        0,
        '42'
    ),
    (
        5005,
        0,
        'zero_subject',
        'Zero subject filter remains an exact integer bind',
        '["A","B"]',
        '{"value":"A"}',
        '  ',
        2,
        '["zero"]'
    ),
    (
        5006,
        5001,
        'essay',
        'Empty subject name remains a raw joined value',
        '',
        '  ',
        NULL,
        3,
        '{malformed-tags'
    ),
    (
        5007,
        5002,
        'single_choice',
        'Unicode 题干 🧪',
        '["甲","乙"]',
        '"甲"',
        '解析',
        4,
        '["中文","🧪"]'
    ),
    (
        5008,
        5002,
        'essay',
        'Second primary-subject export row',
        '[]',
        '[]',
        '',
        5,
        '[]'
    );

-- Preserve the production foreign-key definition while inserting one historical-orphan edge row.
-- session_replication_role is scoped to this test-only initialization session and reset immediately.
SET session_replication_role = replica;

INSERT INTO questions (
    id,
    subject_id,
    type,
    content,
    options,
    answer,
    analysis,
    difficulty,
    tags
) VALUES (
    5009,
    5999,
    'orphan_subject',
    'Missing subject join target remains a raw export fact',
    '["orphan"]',
    '"orphan-answer"',
    'orphan-analysis',
    -3,
    '["orphan-subject"]'
);

SET session_replication_role = origin;

ANALYZE subjects;
ANALYZE questions;
