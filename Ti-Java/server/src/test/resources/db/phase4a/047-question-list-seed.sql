-- Phase 4A test-only rows for the HTTP-neutral catalog question-summary list primitive.
-- This is neither a Flyway baseline nor a production migration.

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
        'Question list negative subject fixture',
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
        'Question list zero subject fixture',
        'PUBLIC TEST-ONLY synthetic zero-ID subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        4701,
        'Question list primary subject fixture',
        'PUBLIC TEST-ONLY synthetic primary subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        4702,
        'Question list secondary subject fixture',
        'PUBLIC TEST-ONLY synthetic secondary subject',
        false,
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
    difficulty,
    tags,
    image_path,
    created_by,
    updated_at
) VALUES
    (
        -1,
        4702,
        'negative_question_id',
        'Legacy negative question ID remains a raw database fact',
        1,
        'negative-question-id-tags',
        NULL,
        NULL,
        TIMESTAMP '2026-07-15 23:59:59'
    ),
    (
        0,
        4701,
        'single_choice',
        'Legacy zero-ID list row',
        0,
        'legacy-zero-tags',
        '[]',
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        4704,
        -7,
        'negative_subject',
        'Negative subject filter remains an exact integer bind',
        1,
        'negative-subject-tags',
        NULL,
        NULL,
        TIMESTAMP '2026-07-16 04:00:00'
    ),
    (
        4705,
        0,
        'zero_subject',
        'Zero subject filter remains an exact integer bind',
        2,
        'zero-subject-tags',
        NULL,
        NULL,
        TIMESTAMP '2026-07-16 05:00:00'
    ),
    (
        4706,
        NULL,
        '',
        'Empty question type remains an exact text bind',
        3,
        '',
        '  ',
        NULL,
        TIMESTAMP '2026-07-16 06:00:00'
    ),
    (
        4707,
        4702,
        'single_choice',
        'Secondary subject single choice',
        2,
        '["secondary"]',
        '["secondary.png"]',
        900000007,
        TIMESTAMP '2026-07-16 07:00:00'
    ),
    (
        4708,
        4701,
        'essay',
        'Nullable summary columns remain null',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL
    ),
    (
        4709,
        4701,
        'single_choice',
        'Malformed raw summary text remains untouched',
        5,
        '{not-json-tags',
        '[not-json-image',
        900000009,
        TIMESTAMP '2026-07-16 09:10:11'
    );

ANALYZE subjects;
ANALYZE questions;
