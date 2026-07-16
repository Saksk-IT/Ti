-- PUBLIC TEST-ONLY deterministic Phase 4A public-bank snapshot.
-- Values mirror docs/refactor/phase4a/golden-public-bank-reads.json at the
-- fixed Beijing clock 2026-07-16 12:00:00. This is not production data.

TRUNCATE TABLE
    public_bank_plaza_snapshot_state,
    public_bank_plaza_viewer_state,
    public_bank_plaza_metrics
    RESTART IDENTITY;

-- The Phase 2 schema fixture contributes board id 1. Replace only the known
-- fixture boards so the Phase 4A subject rows from 041 remain intact.
DELETE FROM plaza_boards
WHERE id IN (1, 5201, 5202, 5203, 5204);

-- These identities make optional JWT/session HTTP coverage exercise the same
-- owner and viewer IDs as the snapshot. Avatar data intentionally lives only
-- in the complete catalog projection because the Phase 3 users slice has no
-- avatar column.
DELETE FROM users
WHERE id IN (5101, 5102, 5103, 5104, 5105, 5106);

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
        5101,
        'owner',
        'synthetic-fixed-password-hash',
        false,
        false,
        11,
        false,
        false,
        true,
        'owner@phase4a.test',
        NULL,
        'phase4a-openid-5101',
        NULL
    ),
    (
        5102,
        'public_viewer',
        'synthetic-fixed-password-hash',
        false,
        false,
        12,
        false,
        false,
        true,
        'public_viewer@phase4a.test',
        NULL,
        'phase4a-openid-5102',
        NULL
    ),
    (
        5103,
        'shared_viewer',
        'synthetic-fixed-password-hash',
        false,
        false,
        13,
        false,
        false,
        true,
        'shared_viewer@phase4a.test',
        NULL,
        'phase4a-openid-5103',
        NULL
    ),
    (
        5104,
        'both_viewer',
        'synthetic-fixed-password-hash',
        false,
        false,
        14,
        false,
        false,
        true,
        'both_viewer@phase4a.test',
        NULL,
        'phase4a-openid-5104',
        NULL
    ),
    (
        5105,
        'system_viewer',
        'synthetic-fixed-password-hash',
        false,
        false,
        15,
        false,
        false,
        true,
        'system_viewer@phase4a.test',
        NULL,
        'phase4a-openid-5105',
        NULL
    ),
    (
        5106,
        'needle_author',
        'synthetic-fixed-password-hash',
        false,
        false,
        16,
        false,
        false,
        true,
        'needle_author@phase4a.test',
        NULL,
        'phase4a-openid-5106',
        NULL
    );

INSERT INTO plaza_boards (
    id,
    slug,
    name,
    description,
    icon,
    sort_order,
    is_active,
    created_at,
    updated_at
) VALUES
    (
        5201,
        'alpha',
        'Alpha Board',
        NULL,
        NULL,
        20,
        true,
        TIMESTAMP '2026-07-01 08:00:00',
        TIMESTAMP '2026-07-01 08:00:00'
    ),
    (
        5202,
        'beta',
        'Beta Board',
        'Beta fixture board',
        NULL,
        10,
        true,
        TIMESTAMP '2026-07-01 08:00:00',
        TIMESTAMP '2026-07-01 08:00:00'
    ),
    (
        5203,
        'empty-active',
        'Empty Active Board',
        'No metrics belong here',
        NULL,
        5,
        true,
        TIMESTAMP '2026-07-01 08:00:00',
        TIMESTAMP '2026-07-01 08:00:00'
    ),
    (
        5204,
        'inactive',
        'Inactive Board',
        'Hidden from board directory',
        NULL,
        1,
        false,
        TIMESTAMP '2026-07-01 08:00:00',
        TIMESTAMP '2026-07-01 08:00:00'
    );

INSERT INTO public_bank_plaza_metrics (
    source_type,
    source_id,
    name,
    description,
    cover_image,
    owner_id,
    owner_label,
    owner_avatar,
    question_count_total,
    plaza_board_id,
    is_featured,
    featured_weight,
    published_at,
    last_activity_at,
    join_count_total,
    join_users_7d,
    join_users_30d,
    answer_count_7d,
    answer_count_30d,
    answer_users_7d,
    answer_users_30d,
    hot_score,
    active_score,
    recommended_score,
    join_mode,
    join_note,
    allow_copy,
    share_count,
    snapshot_generation,
    updated_at
) VALUES
    (
        'system',
        5301,
        'needle',
        'Exact-name system fixture',
        NULL,
        NULL,
        '系统题库',
        NULL,
        2,
        5201,
        true,
        10,
        TIMESTAMP '2026-07-10 10:00:00',
        TIMESTAMP '2026-07-16 10:00:00',
        2,
        2,
        2,
        2,
        2,
        2,
        2,
        13.54,
        10.3,
        1017.24,
        'free',
        '',
        false,
        0,
        1,
        TIMESTAMP '2026-07-16 12:00:00'
    ),
    (
        'system',
        5302,
        'Needle Prefix System',
        'System prefix fixture',
        NULL,
        NULL,
        '系统题库',
        NULL,
        1,
        5202,
        false,
        0,
        TIMESTAMP '2026-07-16 09:00:00',
        TIMESTAMP '2026-07-16 09:00:00',
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0.02,
        0.0,
        0.02,
        'free',
        '',
        false,
        0,
        1,
        TIMESTAMP '2026-07-16 12:00:00'
    ),
    (
        'system',
        5303,
        'Wildcard Catalog',
        'Inactive-board fixture',
        NULL,
        NULL,
        '系统题库',
        NULL,
        0,
        5204,
        false,
        0,
        TIMESTAMP '2026-07-15 07:00:00',
        TIMESTAMP '2026-07-15 07:00:00',
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0.0,
        0.0,
        0.0,
        'free',
        '',
        false,
        0,
        1,
        TIMESTAMP '2026-07-16 12:00:00'
    ),
    (
        'user_public',
        5401,
        'Atlas Needle User',
        'Public atlas card',
        '/uploads/bank_covers/atlas.png',
        5101,
        'owner',
        '/uploads/avatars/owner.png',
        9,
        5201,
        true,
        5,
        TIMESTAMP '2026-07-15 08:00:00',
        TIMESTAMP '2026-07-16 11:00:00',
        3,
        3,
        3,
        1,
        1,
        1,
        1,
        14.13,
        9.15,
        1016.68,
        'approval',
        'Synthetic approval required',
        false,
        2,
        1,
        TIMESTAMP '2026-07-16 12:00:00'
    ),
    (
        'user_public',
        5402,
        'Needle User Prefix',
        'Prefix public card',
        NULL,
        5101,
        'owner',
        '/uploads/avatars/owner.png',
        5,
        5202,
        false,
        0,
        TIMESTAMP '2026-07-16 08:00:00',
        TIMESTAMP '2026-07-16 08:00:00',
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0.1,
        0.0,
        0.1,
        'free',
        '',
        true,
        0,
        1,
        TIMESTAMP '2026-07-16 12:00:00'
    ),
    (
        'user_public',
        5403,
        'Description Match',
        'needle guide from description',
        NULL,
        5101,
        'owner',
        '/uploads/avatars/owner.png',
        12,
        5201,
        false,
        0,
        TIMESTAMP '2026-07-11 07:00:00',
        TIMESTAMP '2026-07-12 07:30:00',
        1,
        1,
        1,
        1,
        1,
        1,
        1,
        6.99,
        5.15,
        7.84,
        'member',
        'Members later',
        true,
        0,
        1,
        TIMESTAMP '2026-07-16 12:00:00'
    ),
    (
        'user_public',
        5404,
        'Owner Match',
        'Owner keyword public card',
        '/uploads/bank_covers/owner-match.png',
        5106,
        'needle_author',
        '/uploads/avatars/needle-author.png',
        3,
        NULL,
        false,
        0,
        TIMESTAMP '2026-07-14 06:00:00',
        TIMESTAMP '2026-07-14 06:00:00',
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0.06,
        0.0,
        0.06,
        'free',
        '',
        true,
        0,
        1,
        TIMESTAMP '2026-07-16 12:00:00'
    );

-- Four relation rows freeze the public, shared, both and system-public paths.
-- Two activity-only rows retain answer activity that the legacy current-day
-- summary excluded but the approved rolling seven-day projection must count.
INSERT INTO public_bank_plaza_viewer_state (
    identity_id,
    source_type,
    source_id,
    has_public,
    has_shared,
    last_activity_at,
    snapshot_generation,
    updated_at
) VALUES
    (
        5102,
        'user_public',
        5401,
        true,
        false,
        TIMESTAMPTZ '2026-07-16 11:00:00+08:00',
        1,
        TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
    ),
    (
        5103,
        'user_public',
        5401,
        false,
        true,
        TIMESTAMPTZ '2026-07-16 09:00:00+08:00',
        1,
        TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
    ),
    (
        5104,
        'user_public',
        5401,
        true,
        true,
        TIMESTAMPTZ '2026-07-16 08:30:00+08:00',
        1,
        TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
    ),
    (
        5105,
        'system',
        5301,
        true,
        false,
        TIMESTAMPTZ '2026-07-16 10:00:00+08:00',
        1,
        TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
    ),
    (
        5101,
        'system',
        5301,
        false,
        false,
        TIMESTAMPTZ '2026-07-11 10:00:00+08:00',
        1,
        TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
    ),
    (
        5101,
        'user_public',
        5403,
        false,
        false,
        TIMESTAMPTZ '2026-07-15 08:30:00+08:00',
        1,
        TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
    );

UPDATE public_bank_plaza_metrics
SET projection_digest =
    '88f25097554a6789dafe7f0902061a5804bee8526ac2cfd32f8e806fd80b8181';

UPDATE public_bank_plaza_viewer_state
SET projection_digest =
    '88f25097554a6789dafe7f0902061a5804bee8526ac2cfd32f8e806fd80b8181';

INSERT INTO public_bank_plaza_snapshot_state (
    snapshot_name,
    status,
    last_success_at,
    metrics_count,
    system_count,
    user_public_count,
    viewer_state_count,
    projection_digest,
    projector_schema_version,
    source_high_watermark,
    generation,
    updated_at
) VALUES (
    'public-bank-plaza',
    'complete',
    TIMESTAMPTZ '2026-07-16 12:00:00+08:00',
    7,
    3,
    4,
    6,
    -- Fixed test sentinel: SHA-256 of
    -- "phase4a-public-bank-golden-snapshot-generation-1". The production
    -- projector must define and calculate its own canonical digest.
    '88f25097554a6789dafe7f0902061a5804bee8526ac2cfd32f8e806fd80b8181',
    1,
    'legacy-golden@700006dfdfa063deb4387be572911e782bcea0d9',
    1,
    TIMESTAMPTZ '2026-07-16 12:00:00+08:00'
);

ANALYZE users;
ANALYZE plaza_boards;
ANALYZE public_bank_plaza_metrics;
ANALYZE public_bank_plaza_viewer_state;
ANALYZE public_bank_plaza_snapshot_state;
