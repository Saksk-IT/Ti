-- PUBLIC TEST-ONLY synthetic credentials. Never copy these values into a deployed environment.
TRUNCATE TABLE system_config, users RESTART IDENTITY CASCADE;

INSERT INTO users (
    id,
    username,
    password_hash,
    is_admin,
    is_locked,
    session_version,
    is_subject_admin,
    is_notification_admin,
    has_password_set,
    email,
    phone,
    openid,
    last_active
) VALUES
    (
        1,
        'phase3-user',
        'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
        true,
        false,
        7,
        false,
        true,
        false,
        'phase3@example.test',
        '13800138000',
        'o-public-test-only-openid-0001',
        NULL
    ),
    (
        2,
        'phase3-locked',
        'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
        false,
        true,
        3,
        false,
        false,
        true,
        'locked@example.test',
        '13900139000',
        NULL,
        NULL
    ),
    (
        3,
        'phase3-duplicate-a',
        'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
        false,
        false,
        0,
        false,
        false,
        true,
        'duplicate@example.test',
        '13700137000',
        NULL,
        NULL
    ),
    (
        4,
        'phase3-duplicate-b',
        'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
        false,
        false,
        0,
        false,
        false,
        true,
        'duplicate@example.test',
        '13600136000',
        NULL,
        NULL
    ),
    (
        4242,
        'public-test-user',
        'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
        false,
        false,
        7,
        true,
        false,
        true,
        'legacy-vector@example.test',
        '13500135000',
        'o-public-test-only-openid-0001',
        NULL
    );

INSERT INTO system_config (config_key, config_value) VALUES
    ('auth_phone_login_enabled', 'false'),
    ('auth_wechat_login_enabled', 'true');
