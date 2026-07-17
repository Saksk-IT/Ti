-- Phase 4C test-only golden rows for the personal-bank user-counts HTTP slice.
-- This adapts the immutable Phase 4B capture fixture to the typed PostgreSQL
-- schema supplied by 030/062/065/067. It is not a production migration.

INSERT INTO users (
    id, username, password_hash, is_admin, is_locked, session_version,
    is_subject_admin, is_notification_admin, has_password_set, email,
    phone, openid, last_active
) VALUES
    (99451, 'phase4b_counts_owner', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_owner@test.example.com', NULL, NULL, NULL),
    (99452, 'phase4b_counts_other', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_other@test.example.com', NULL, NULL, NULL),
    (99453, 'phase4b_counts_shared_future', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_future@test.example.com', NULL, NULL, NULL),
    (99454, 'phase4b_counts_shared_null', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_null@test.example.com', NULL, NULL, NULL),
    (99455, 'phase4b_counts_shared_equal', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_equal@test.example.com', NULL, NULL, NULL),
    (99456, 'phase4b_counts_shared_expired', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_expired@test.example.com', NULL, NULL, NULL),
    (99457, 'phase4b_counts_shared_inactive', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_inactive@test.example.com', NULL, NULL, NULL),
    (99458, 'phase4b_counts_shared_malformed', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_malformed@test.example.com', NULL, NULL, NULL),
    (99459, 'phase4b_counts_shared_multi', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_multi@test.example.com', NULL, NULL, NULL),
    (99460, 'phase4b_counts_shared_mismatch', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_mismatch@test.example.com', NULL, NULL, NULL),
    (99461, 'phase4b_counts_shared_empty', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_empty@test.example.com', NULL, NULL, NULL),
    (99462, 'phase4b_counts_shared_aware', 'public-test-only-password-hash',
     false, false, 11, false, false, true,
     'phase4b_counts_shared_aware@test.example.com', NULL, NULL, NULL),
    (99463, 'phase4b_counts_revoked', 'public-test-only-password-hash',
     false, false, 12, false, false, true,
     'phase4b_counts_revoked@test.example.com', NULL, NULL, NULL);

INSERT INTO user_question_banks (
    id, user_id, name, is_public, status, question_count, created_at, updated_at
) VALUES
    (99551, 99451, 'user counts owner_active 高数・α／🧪',
     false, 1, 9, TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 08:00:00'),
    (99552, 99451, 'user counts inactive 高数・α／🧪',
     true, 0, 9, TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 08:00:00'),
    (99553, 99451, 'user counts null_status 高数・α／🧪',
     false, NULL, 9, TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 08:00:00'),
    (99554, 99451, 'user counts status_two 高数・α／🧪',
     false, 2, 9, TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 08:00:00'),
    (99555, 99452, 'user counts public_other 高数・α／🧪',
     true, 1, 9, TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 08:00:00'),
    (99556, 99452, 'user counts private_other 高数・α／🧪',
     false, 1, 9, TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 08:00:00'),
    (99557, 99451, 'user counts empty 高数・α／🧪',
     false, 1, 0, TIMESTAMP '2026-07-17 08:00:00', TIMESTAMP '2026-07-17 08:00:00');

-- The malformed text expiry and offset-aware expiry capture rows are omitted:
-- neither value is representable by PostgreSQL timestamp without time zone
-- without changing its approved meaning. The legacy empty-string expiry is the
-- approved target representation exception and is written explicitly as NULL.
INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
) VALUES
    (99651, 99551, 99451, 'C00001', 'user-count-token-0001', 'read',
     TIMESTAMP '2026-07-17 13:00:00', NULL, 1, true, TIMESTAMP '2026-07-17 08:01:00'),
    (99652, 99551, 99451, 'C00002', 'user-count-token-0002', 'copy',
     NULL, NULL, 2, true, TIMESTAMP '2026-07-17 08:02:00'),
    (99653, 99551, 99451, 'C00003', 'user-count-token-0003', NULL,
     TIMESTAMP '2026-07-17 12:00:00', NULL, 3, true, TIMESTAMP '2026-07-17 08:03:00'),
    (99654, 99551, 99451, 'C00004', 'user-count-token-0004', 'read',
     TIMESTAMP '2026-07-17 11:59:59', NULL, 4, true, TIMESTAMP '2026-07-17 08:04:00'),
    (99655, 99551, 99451, 'C00005', 'user-count-token-0005', 'read',
     TIMESTAMP '2027-01-01 00:00:00', NULL, 5, false, TIMESTAMP '2026-07-17 08:05:00'),
    (99657, 99551, 99451, 'C00007', 'user-count-token-0007', 'read',
     TIMESTAMP '2026-07-17 11:00:00', NULL, 7, true, TIMESTAMP '2026-07-17 08:07:00'),
    (99658, 99551, 99451, 'C00008', 'user-count-token-0008', 'copy',
     TIMESTAMP '2026-07-17 14:00:00', NULL, 8, true, TIMESTAMP '2026-07-17 08:08:00'),
    (99659, 99556, 99451, 'C00009', 'user-count-token-0009', NULL,
     NULL, NULL, 9, true, TIMESTAMP '2026-07-17 08:09:00'),
    (99660, 99551, 99451, 'C00010', 'user-count-token-0010', 'read',
     NULL, NULL, 10, true, TIMESTAMP '2026-07-17 08:10:00');

INSERT INTO bank_share_records (
    id, share_id, bank_id, user_id, status, last_access_at, access_count, created_at
) VALUES
    (99671, 99651, 99551, 99453, 1,
     TIMESTAMP '2026-07-17 09:01:00', 1, TIMESTAMP '2026-07-17 08:01:00'),
    (99672, 99652, 99551, 99454, 1,
     TIMESTAMP '2026-07-17 09:02:00', 2, TIMESTAMP '2026-07-17 08:02:00'),
    (99673, 99653, 99551, 99455, 1,
     TIMESTAMP '2026-07-17 09:03:00', 3, TIMESTAMP '2026-07-17 08:03:00'),
    (99674, 99654, 99551, 99456, 1,
     TIMESTAMP '2026-07-17 09:04:00', 4, TIMESTAMP '2026-07-17 08:04:00'),
    (99675, 99655, 99551, 99457, 1,
     TIMESTAMP '2026-07-17 09:05:00', 5, TIMESTAMP '2026-07-17 08:05:00'),
    (99677, 99657, 99551, 99459, 1,
     TIMESTAMP '2026-07-17 09:07:00', 7, TIMESTAMP '2026-07-17 08:07:00'),
    (99678, 99658, 99551, 99459, 1,
     TIMESTAMP '2026-07-17 09:08:00', 8, TIMESTAMP '2026-07-17 08:08:00'),
    -- Deliberately cross-bank: the record points at owner_active while its share
    -- belongs to private_other, matching the captured legacy access fixture.
    (99679, 99659, 99551, 99460, 1,
     TIMESTAMP '2026-07-17 09:09:00', 9, TIMESTAMP '2026-07-17 08:09:00'),
    (99680, 99660, 99551, 99461, 1,
     TIMESTAMP '2026-07-17 09:10:00', 10, TIMESTAMP '2026-07-17 08:10:00');

INSERT INTO user_bank_questions (
    id, bank_id, user_id, type, content, options, answer, created_at
) VALUES
    (99701, 99551, 99451, 'single_choice', 'counts question 1', '[]', '[]',
     TIMESTAMP '2026-07-17 08:01:00'),
    (99702, 99551, 99451, 'multi_choice', 'counts question 2', '[]', '[]',
     TIMESTAMP '2026-07-17 08:02:00'),
    (99703, 99551, 99451, 'boolean', 'counts question 3', '[]', '[]',
     TIMESTAMP '2026-07-17 08:03:00'),
    (99704, 99551, 99451, 'fill', 'counts question 4', '[]', '[]',
     TIMESTAMP '2026-07-17 08:04:00'),
    (99705, 99551, 99451, 'essay', 'counts question 5', '[]', '[]',
     TIMESTAMP '2026-07-17 08:05:00'),
    (99706, 99551, 99451, 'unknown_type', 'counts question 6', '[]', '[]',
     TIMESTAMP '2026-07-17 08:06:00'),
    (99707, 99551, 99451, 'single', 'counts question 7', '[]', '[]',
     TIMESTAMP '2026-07-17 08:07:00'),
    (99708, 99551, 99451, '', 'counts question 8', '[]', '[]',
     TIMESTAMP '2026-07-17 08:08:00'),
    (99709, 99551, 99451, 'single_choice', 'counts question 9', '[]', '[]',
     TIMESTAMP '2026-07-17 08:09:00');

-- Approved P4C-LEARNING-001 target state after normalizing the legacy sa2
-- empty-value tag key into the typed target membership relation.
INSERT INTO user_question_tag_items (
    user_id, scope, scope_id, question_id, tag, created_at, updated_at
) VALUES
    (99451, 'user_bank', 99551, 99701, '重点',
     TIMESTAMP '2026-07-17 08:01:00', TIMESTAMP '2026-07-17 08:01:00');

INSERT INTO user_bank_favorites (
    id, user_id, bank_id, question_id, created_at
) VALUES
    (99801, 99451, 99551, 99701, TIMESTAMP '2026-07-17 10:01:00'),
    (99802, 99451, 99551, 99703, TIMESTAMP '2026-07-17 10:02:00'),
    (99803, 99451, 99551, 99706, TIMESTAMP '2026-07-17 10:03:00'),
    (99804, 99451, 99551, 99707, TIMESTAMP '2026-07-17 10:04:00'),
    -- Legacy counting joins through question_id and ignores favorites.bank_id.
    (99805, 99451, 99556, 99709, TIMESTAMP '2026-07-17 10:05:00'),
    (99806, 99452, 99551, 99702, TIMESTAMP '2026-07-17 10:06:00');

INSERT INTO user_bank_mistakes (
    id, user_id, bank_id, question_id, wrong_count, created_at, updated_at
) VALUES
    (99901, 99451, 99551, 99702, 1,
     TIMESTAMP '2026-07-17 11:01:00', TIMESTAMP '2026-07-17 11:01:00'),
    (99902, 99451, 99551, 99703, 2,
     TIMESTAMP '2026-07-17 11:02:00', TIMESTAMP '2026-07-17 11:02:00'),
    (99903, 99451, 99551, 99705, 3,
     TIMESTAMP '2026-07-17 11:03:00', TIMESTAMP '2026-07-17 11:03:00');
