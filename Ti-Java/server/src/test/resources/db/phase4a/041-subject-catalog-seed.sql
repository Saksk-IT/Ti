-- PUBLIC TEST-ONLY synthetic Phase 4A state.

TRUNCATE TABLE user_subjects, questions, system_config, users, subjects
    RESTART IDENTITY CASCADE;

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
        4101,
        'phase4a_reader',
        'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
        false,
        false,
        3,
        false,
        false,
        true,
        'phase4a_reader@test.example.com',
        NULL,
        NULL,
        NULL
    ),
    (
        4102,
        'phase4a_admin',
        'scrypt:32768:8:1$PublicSalt123456$1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651da42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c',
        true,
        false,
        5,
        false,
        false,
        true,
        'phase4a_admin@test.example.com',
        NULL,
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
    (4201, '算法基础', 'visible', false, NULL, false, 0, NULL, TIMESTAMP '2026-07-15 00:00:00'),
    (4202, '数据库系统', NULL, NULL, NULL, false, 0, NULL, TIMESTAMP '2026-07-15 00:00:00'),
    (4203, '锁定科目', 'locked', true, NULL, false, 0, NULL, TIMESTAMP '2026-07-15 00:00:00'),
    (4204, '受限科目', 'restricted', false, NULL, false, 0, NULL, TIMESTAMP '2026-07-15 00:00:00');

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
    (4301, 4201, 'single_choice', 'A', '[]', '[]', '[]', 1, 4102, 4102,
        TIMESTAMP '2026-07-15 01:00:00', TIMESTAMP '2026-07-15 01:00:00'),
    (4302, 4201, 'boolean', 'B', '[]', '[]', '[]', 1, 4102, 4102,
        TIMESTAMP '2026-07-15 01:00:00', TIMESTAMP '2026-07-15 01:00:00'),
    (4303, 4203, 'fill', 'C', '[]', '[]', '[]', 1, 4102, 4102,
        TIMESTAMP '2026-07-15 01:00:00', TIMESTAMP '2026-07-15 01:00:00'),
    (4304, 4204, 'essay', 'D', '[]', '[]', '[]', 1, 4102, 4102,
        TIMESTAMP '2026-07-15 01:00:00', TIMESTAMP '2026-07-15 01:00:00');

INSERT INTO user_subjects (
    id,
    user_id,
    subject_id,
    restricted_at,
    restricted_by
) VALUES (
    4401,
    4101,
    4204,
    TIMESTAMP '2026-07-15 08:00:00',
    4102
);

ANALYZE users;
ANALYZE user_subjects;
ANALYZE subjects;
ANALYZE questions;
