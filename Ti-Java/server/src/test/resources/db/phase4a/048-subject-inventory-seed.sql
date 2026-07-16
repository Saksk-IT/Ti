-- Phase 4A test-only rows for the HTTP-neutral catalog subject-inventory primitive.
-- This is neither a Flyway baseline nor a production migration.

TRUNCATE TABLE questions, subjects RESTART IDENTITY CASCADE;

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
        -2147483648,
        '',
        'PUBLIC TEST-ONLY minimum signed subject ID with empty name',
        NULL,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        -7,
        '科目 🧪',
        'PUBLIC TEST-ONLY locked Unicode subject',
        true,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        0,
        '  ',
        'PUBLIC TEST-ONLY zero-ID whitespace-name subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
    ),
    (
        7,
        'Unlocked subject',
        'PUBLIC TEST-ONLY unlocked subject',
        false,
        NULL,
        false,
        0,
        NULL,
        TIMESTAMP '2026-07-16 00:00:00'
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
        TIMESTAMP '2026-07-16 00:00:00'
    );

INSERT INTO questions (
    id,
    subject_id,
    type,
    content,
    created_at,
    updated_at
) VALUES
    (-100, -2147483648, 'minimum_subject', 'Counted for minimum subject',
        TIMESTAMP '2026-07-16 01:00:00', TIMESTAMP '2026-07-16 01:00:00'),
    (-99, -7, 'locked_subject', 'First counted locked-subject question',
        TIMESTAMP '2026-07-16 02:00:00', TIMESTAMP '2026-07-16 02:00:00'),
    (0, -7, 'locked_subject', 'Second counted locked-subject question',
        TIMESTAMP '2026-07-16 03:00:00', TIMESTAMP '2026-07-16 03:00:00'),
    (1, 7, 'unlocked_subject', 'Counted unlocked-subject question',
        TIMESTAMP '2026-07-16 04:00:00', TIMESTAMP '2026-07-16 04:00:00'),
    (2147483647, NULL, 'unassigned', 'Unassigned question is not counted for any subject',
        TIMESTAMP '2026-07-16 05:00:00', TIMESTAMP '2026-07-16 05:00:00');

ANALYZE subjects;
ANALYZE questions;
