\set ON_ERROR_STOP on

BEGIN;

INSERT INTO users (
    id,
    username,
    password_hash,
    email,
    email_verified,
    has_password_set,
    session_version,
    is_admin,
    is_locked,
    is_subject_admin,
    is_notification_admin
) VALUES (
    1,
    'phase3-fixture',
    'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
    'phase3@example.test',
    true,
    false,
    7,
    false,
    false,
    false,
    false
) ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    password_hash = EXCLUDED.password_hash,
    email = EXCLUDED.email,
    email_verified = EXCLUDED.email_verified,
    has_password_set = EXCLUDED.has_password_set,
    session_version = EXCLUDED.session_version,
    is_admin = EXCLUDED.is_admin,
    is_locked = EXCLUDED.is_locked,
    is_subject_admin = EXCLUDED.is_subject_admin,
    is_notification_admin = EXCLUDED.is_notification_admin;

-- Public transition fixture. The password is the committed compatibility-vector value
-- `PUBLIC-TEST-ONLY-密码🔒`; Java must upgrade this PBKDF2 row to the shared
-- Werkzeug scrypt format, after which the fixed Flask runtime must still accept it.
INSERT INTO users (
    id,
    username,
    password_hash,
    email,
    email_verified,
    has_password_set,
    session_version,
    is_admin,
    is_locked,
    is_subject_admin,
    is_notification_admin
) VALUES (
    2,
    'phase3-upgrade-fixture',
    'pbkdf2:sha256:600000$PublicSalt654321$6761a5705972a3a2a381cfecc1452be7c8ea01275768cf24a2b8309731cc6c31',
    'phase3-upgrade@example.test',
    true,
    false,
    9,
    false,
    false,
    false,
    false
) ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    password_hash = EXCLUDED.password_hash,
    email = EXCLUDED.email,
    email_verified = EXCLUDED.email_verified,
    has_password_set = EXCLUDED.has_password_set,
    session_version = EXCLUDED.session_version,
    is_admin = EXCLUDED.is_admin,
    is_locked = EXCLUDED.is_locked,
    is_subject_admin = EXCLUDED.is_subject_admin,
    is_notification_admin = EXCLUDED.is_notification_admin;

INSERT INTO system_config (config_key, config_value, description) VALUES
    ('auth_phone_login_enabled', 'false', 'Phase 3 sanitized parity fixture'),
    ('auth_wechat_login_enabled', 'true', 'Phase 3 sanitized parity fixture')
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    description = EXCLUDED.description;

SELECT setval('users_id_seq', GREATEST(1, (SELECT max(id) FROM users)), true);

COMMIT;
