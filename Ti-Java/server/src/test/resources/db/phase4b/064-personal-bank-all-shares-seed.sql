-- Phase 4B test-only rows for preimplementation personal-bank all-shares evidence.
-- This extends 063-personal-bank-share-list-seed.sql and is not a production migration.

INSERT INTO bank_shares (
    id, bank_id, owner_id, share_code, share_token, permission, expires_at,
    max_uses, current_uses, is_active, created_at
) VALUES
    (7300, 7101, 7001, NULL, NULL, NULL, NULL,
     NULL, NULL, NULL, NULL),
    (7301, 7102, 7001, 'BANKOFF', 'token-bank-inactive-001', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 17:00:00'),
    (7302, 7103, 7001, 'BANKNULL', 'token-bank-null-status-02', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 17:00:00'),
    (7303, 7104, 7001, 'BANKTWO', 'token-bank-status-two-03', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-17 17:00:00'),
    (7304, 7105, 7001, 'CROSSBANK', 'token-cross-bank-owner-04', 'copy',
     TIMESTAMP '2020-01-01 00:00:00', 1, 99, false,
     TIMESTAMP '2026-07-17 16:00:00'),
    (7305, 7106, 7001, '', '', '', NULL,
     -1, -2, true, TIMESTAMP '2026-07-17 15:00:00'),
    (7306, 7101, 7002, 'OTHERVIEW', 'token-other-viewer-0005', 'read', NULL,
     NULL, 0, true, TIMESTAMP '2026-07-18 00:00:00');

ANALYZE user_question_banks;
ANALYZE bank_shares;
