-- Phase 4B test-only rows for preimplementation personal-bank share-list evidence.
-- This is neither a Flyway baseline nor a production migration.

INSERT INTO users (
    id, username, password_hash, is_locked, session_version, has_password_set, email
) VALUES
    (7001, 'phase4b-share-owner', 'public-test-only-hash', false, 11, true,
     'phase4b-share-owner@test.invalid'),
    (7002, 'phase4b-share-other', 'public-test-only-hash', false, 11, true,
     'phase4b-share-other@test.invalid');

INSERT INTO user_question_banks (
    id, user_id, name, status
) VALUES
    (0, 7001, 'zero bank', 1),
    (7101, 7001, 'owner bank 高数・α／🧪', 1),
    (7102, 7001, 'inactive bank', 0),
    (7103, 7001, 'null status bank', NULL),
    (7104, 7001, 'status two bank', 2),
    (7105, 7002, 'other owner bank', 1),
    (7106, 7001, 'empty share bank', 1);

INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
) VALUES
    (-2, 7101, 7002, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL),
    (0, 7101, 7001, 'ZERO0A', 'token-newest-00000001', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 12:00:00'),
    (7201, 7101, 7001, 'OFF002', 'token-inactive-000002', 'copy',
     TIMESTAMP '2027-01-01 00:00:00', 5, 2, false,
     TIMESTAMP '2026-07-17 11:00:00'),
    (7202, 7101, 7002, 'OLD003', 'token-expired-000003', 'read',
     TIMESTAMP '2020-01-01 00:00:00', 1, 99, true,
     TIMESTAMP '2026-07-17 10:00:00'),
    (7203, 7101, 7001, 'TIE004', 'token-tie-first-000004', 'unexpected-value',
     NULL, -1, -2, true, TIMESTAMP '2026-07-17 09:00:00'),
    (7204, 7101, 7001, 'TIE005', 'token-tie-second-00005', '',
     NULL, 0, 0, true, TIMESTAMP '2026-07-17 09:00:00'),
    (7205, 7105, 7002, 'OTHER6', 'token-other-bank-00006', 'read',
     NULL, NULL, 0, true, TIMESTAMP '2026-07-17 13:00:00'),
    (7206, 0, 7001, 'ZERO07', 'token-zero-bank-00007', 'read',
     NULL, 0, 0, true, TIMESTAMP '2026-07-17 08:00:00');

ANALYZE user_question_banks;
ANALYZE bank_shares;
