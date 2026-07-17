-- Phase 4B test-only rows for preimplementation personal-bank usage-statistics evidence.
-- This extends the share-list/all-shares fixtures and is not a production migration.

INSERT INTO users (
    id, username, password_hash, is_locked, session_version, has_password_set, email
) VALUES
    (7003, 'phase4b-usage-shared-a', 'public-test-only-hash', false, 1, true,
     'phase4b-usage-shared-a@test.invalid'),
    (7004, 'phase4b-usage-expired', 'public-test-only-hash', false, 1, true,
     'phase4b-usage-expired@test.invalid'),
    (7005, 'phase4b-usage-shared-b', 'public-test-only-hash', false, 1, true,
     'phase4b-usage-shared-b@test.invalid'),
    (7006, 'phase4b-usage-public', 'public-test-only-hash', false, 1, true,
     'phase4b-usage-public@test.invalid'),
    (7007, 'phase4b-usage-overlap', 'public-test-only-hash', false, 1, true,
     'phase4b-usage-overlap@test.invalid'),
    (7008, 'phase4b-usage-null-active', 'public-test-only-hash', false, 1, true,
     'phase4b-usage-null-active@test.invalid');

INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
) VALUES
    (7401, 7101, 7001, 'USAGE1', 'usage-future-token-01', 'read',
     TIMESTAMP '2099-01-01 00:00:00', NULL, 0, true,
     TIMESTAMP '2026-07-17 18:00:00'),
    (7402, 7101, 7001, 'USAGE2', 'usage-expired-token-2', 'read',
     TIMESTAMP '2020-01-01 00:00:00', NULL, 0, true,
     TIMESTAMP '2026-07-17 17:00:00'),
    (7403, 7101, 7001, 'USAGE3', 'usage-null-token-003', 'copy',
     NULL, NULL, 0, true, TIMESTAMP '2026-07-17 16:00:00'),
    (7404, 7101, 7001, 'USAGE4', 'usage-inactive-0004', 'read',
     NULL, NULL, 0, false, TIMESTAMP '2026-07-17 15:00:00'),
    (7405, 7105, 7002, 'USAGE5', 'usage-cross-bank-05', 'read',
     NULL, NULL, 0, true, TIMESTAMP '2026-07-17 14:00:00');

INSERT INTO bank_share_records (
    id, share_id, bank_id, user_id, status, last_access_at, access_count, created_at
) VALUES
    (7501, 7401, 7101, 7003, 1, TIMESTAMP '2026-07-17 18:10:00', 1,
     TIMESTAMP '2026-07-17 18:00:00'),
    (7502, 7402, 7101, 7004, 1, TIMESTAMP '2026-07-17 17:10:00', 1,
     TIMESTAMP '2026-07-17 17:00:00'),
    (7503, 7403, 7101, 7003, 1, TIMESTAMP '2026-07-17 16:10:00', 2,
     TIMESTAMP '2026-07-17 16:00:00'),
    (7504, 7203, 7101, 7005, 1, TIMESTAMP '2026-07-17 15:10:00', 1,
     TIMESTAMP '2026-07-17 15:00:00'),
    (7505, 7404, 7101, 7006, 1, TIMESTAMP '2026-07-17 14:10:00', 1,
     TIMESTAMP '2026-07-17 14:00:00'),
    (7506, 7306, 7101, 7007, 1, TIMESTAMP '2026-07-17 13:10:00', 1,
     TIMESTAMP '2026-07-17 13:00:00'),
    (7507, 7300, 7101, 7008, 1, TIMESTAMP '2026-07-17 12:10:00', 1,
     TIMESTAMP '2026-07-17 12:00:00'),
    (7508, 7403, 7101, 7001, 1, TIMESTAMP '2026-07-17 11:10:00', 1,
     TIMESTAMP '2026-07-17 11:00:00'),
    (7509, 7405, 7101, 7006, 1, TIMESTAMP '2026-07-17 10:10:00', 1,
     TIMESTAMP '2026-07-17 10:00:00'),
    (7510, 7403, 7101, 7006, 0, TIMESTAMP '2026-07-17 09:10:00', 1,
     TIMESTAMP '2026-07-17 09:00:00');

INSERT INTO public_bank_users (
    id, bank_id, user_id, last_access_at, access_count, created_at
) VALUES
    (7601, 7101, 7001, TIMESTAMP '2026-07-17 18:00:00', 1,
     TIMESTAMP '2026-07-17 18:00:00'),
    (7602, 7101, 7003, TIMESTAMP '2026-07-17 17:00:00', 2,
     TIMESTAMP '2026-07-17 17:00:00'),
    (7603, 7101, 7006, TIMESTAMP '2026-07-17 16:00:00', 3,
     TIMESTAMP '2026-07-17 16:00:00'),
    (7604, 7101, 7007, NULL, 0, NULL),
    (7605, 7105, 7004, TIMESTAMP '2026-07-17 15:00:00', 1,
     TIMESTAMP '2026-07-17 15:00:00');

ANALYZE user_question_banks;
ANALYZE bank_shares;
ANALYZE bank_share_records;
ANALYZE public_bank_users;
