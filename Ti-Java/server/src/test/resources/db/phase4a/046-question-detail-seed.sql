-- Phase 4A test-only rows for the HTTP-neutral catalog question-detail primitive.
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
) VALUES (
    4501,
    'Question detail fixture subject',
    'PUBLIC TEST-ONLY synthetic subject',
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
    options,
    answer,
    analysis,
    tags,
    difficulty,
    image_path,
    source,
    created_by,
    updated_by,
    created_at,
    updated_at
) VALUES
    (
        0,
        4501,
        'single_choice',
        'Legacy zero-id question',
        '["zero","one"]',
        'zero',
        NULL,
        'legacy-zero',
        0,
        '[]',
        'phase4a-public-fixture',
        NULL,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00',
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        4601,
        4501,
        'multiple_choice',
        'Complete fifteen-column question',
        '["A","B"]',
        '["A"]',
        'Complete analysis',
        '["catalog","detail"]',
        4,
        '{"content":["question.png"],"answer":[],"explanation":[]}',
        'phase4a-public-fixture',
        900000001,
        900000002,
        TIMESTAMP '2026-07-16 01:02:03',
        TIMESTAMP '2026-07-16 04:05:06'
    ),
    (
        4602,
        NULL,
        'essay',
        'Nullable column question',
        NULL,
        NULL,
        NULL,
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
        4603,
        NULL,
        'single_choice',
        'Malformed JSON remains raw',
        '{not-json-options',
        '[not-json-answer',
        NULL,
        'not-json-tags]',
        1,
        '{not-json-image-path',
        NULL,
        NULL,
        NULL,
        TIMESTAMP '2026-07-16 07:08:09',
        TIMESTAMP '2026-07-16 10:11:12'
    );

ANALYZE questions;
