-- Phase 4C test-only identities dedicated to the PG16/PG18 termination gate.
-- These rows keep authentication-state and business-denial evidence independent
-- from the immutable Phase 4B golden identities. This is not a production migration.

INSERT INTO users (
    id, username, password_hash, is_admin, is_locked, session_version,
    is_subject_admin, is_notification_admin, has_password_set, email,
    phone, openid, last_active
) VALUES
    (100451, 'phase4c_pg_termination_revoked', 'public-test-only-password-hash',
     false, false, 22, false, false, true,
     'phase4c_pg_termination_revoked@test.example.com', NULL, NULL, NULL),
    (100452, 'phase4c_pg_termination_denied', 'public-test-only-password-hash',
     false, false, 21, false, false, true,
     'phase4c_pg_termination_denied@test.example.com', NULL, NULL, NULL);
