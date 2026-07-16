-- Phase 4B test-only rows for the personal-bank category list.
-- This is neither a Flyway baseline nor a production migration.

INSERT INTO users (
    id, username, password_hash, is_locked, session_version, has_password_set, email
) VALUES
    (6001, 'phase4b-category-owner', 'public-test-only-hash', false, 11, true,
     'phase4b-category-owner@test.invalid'),
    (6002, 'phase4b-category-other', 'public-test-only-hash', false, 11, true,
     'phase4b-category-other@test.invalid');

INSERT INTO user_bank_categories (
    id, user_id, name, description, sort_order, created_at, updated_at
) VALUES
    (-1, 6001, 'Negative category', 'signed category identifier', -5,
     TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 09:00:00'),
    (0, 6001, '', '', 0,
     TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 09:00:00'),
    (6101, 6001, '高数・α／🧪', 'Unicode 描述', 0,
     TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 09:00:00'),
    (6102, 6001, 'Nullable tail', NULL, NULL, NULL, NULL),
    (6103, 6002, 'Other identity category', 'must remain isolated', -100,
     TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 09:00:00');

INSERT INTO user_question_banks (
    id, user_id, category_id, name, status
) VALUES
    (-1, 6001, -1, 'active owner bank', 1),
    (0, 6001, -1, 'inactive owner bank', 0),
    (6201, 6002, -1, 'cross-owner active bank', 1),
    (6202, 6002, 0, 'second cross-owner active bank', 1),
    (6203, 6001, 6101, 'negative-status bank', -1),
    (6204, 6001, 6102, 'nullable category active bank', 1),
    (6205, 6002, 6103, 'other identity active bank', 1),
    (6206, 6001, 6101, 'status two is not active', 2),
    (6207, 6001, 6101, 'null status is not active', NULL);

ANALYZE user_bank_categories;
ANALYZE user_question_banks;
