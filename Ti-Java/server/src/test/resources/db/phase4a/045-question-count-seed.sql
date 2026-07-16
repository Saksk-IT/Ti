-- Phase 4A test-only overlay for the HTTP-neutral catalog question-count primitive.
-- This is neither a Flyway baseline nor a production migration.

INSERT INTO questions (
    id,
    subject_id,
    type,
    content,
    options,
    answer,
    tags,
    difficulty,
    created_by,
    updated_by,
    created_at,
    updated_at
) VALUES
    (4305, NULL, 'essay', 'Unassigned', '[]', '[]', '[]', 1, 4102, 4102,
        TIMESTAMP '2026-07-15 01:00:00', TIMESTAMP '2026-07-15 01:00:00'),
    (4306, 4202, 'boolean', 'Nullable lock', '[]', '[]', '[]', 1, 4102, 4102,
        TIMESTAMP '2026-07-15 01:00:00', TIMESTAMP '2026-07-15 01:00:00');

-- Preserve the legacy LEFT JOIN behavior under an explicitly inconsistent test row.
-- Production foreign keys prevent this state; the adapter still fails closed for authenticated
-- viewers if a restored historical database temporarily contains one.
SET session_replication_role = replica;
INSERT INTO questions (
    id,
    subject_id,
    type,
    content,
    options,
    answer,
    tags,
    difficulty,
    created_by,
    updated_by,
    created_at,
    updated_at
) VALUES (
    4307,
    4299,
    'essay',
    'Orphaned subject reference',
    '[]',
    '[]',
    '[]',
    1,
    4102,
    4102,
    TIMESTAMP '2026-07-15 01:00:00',
    TIMESTAMP '2026-07-15 01:00:00'
);
SET session_replication_role = DEFAULT;

ANALYZE subjects;
ANALYZE questions;
