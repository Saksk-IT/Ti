-- Phase 4A test-only rows for the HTTP-neutral catalog subject-context primitive.
-- This is neither a Flyway baseline nor a production migration.

TRUNCATE TABLE questions, subjects CASCADE;

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
        0,
        '',
        'PUBLIC TEST-ONLY zero-ID empty-name subject',
        NULL,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-17 00:00:00'
    ),
    (
        4901,
        '科目 🧪 <strong>raw</strong>',
        'PUBLIC TEST-ONLY locked Unicode and HTML-like subject name',
        true,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-17 00:00:00'
    ),
    (
        4902,
        '  ',
        'PUBLIC TEST-ONLY whitespace-name subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-17 00:00:00'
    ),
    (
        2147483647,
        'Maximum signed subject ID',
        'PUBLIC TEST-ONLY maximum signed subject ID',
        true,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-17 00:00:00'
    );

ANALYZE subjects;
