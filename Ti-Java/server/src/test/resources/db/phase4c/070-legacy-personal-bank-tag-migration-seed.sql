-- Phase 4C test-only operator fixture for bank_<bank_id>_tags migration evidence.
-- This is not production seed data and authorizes no runtime migration.

INSERT INTO users (
    id, username, password_hash, is_locked, session_version, has_password_set, email
) VALUES
    (7601, 'phase4c-tag-normal', 'public-test-only-hash', false, 1, true,
     'phase4c-tag-normal@test.invalid'),
    (7602, 'phase4c-tag-precedence', 'public-test-only-hash', false, 1, true,
     'phase4c-tag-precedence@test.invalid'),
    (7603, 'phase4c-tag-fault', 'public-test-only-hash', false, 1, true,
     'phase4c-tag-fault@test.invalid'),
    (7604, 'phase4c-tag-after-fault', 'public-test-only-hash', false, 1, true,
     'phase4c-tag-after-fault@test.invalid'),
    (7605, 'phase4c-tag-controls', 'public-test-only-hash', false, 1, true,
     'phase4c-tag-controls@test.invalid');

INSERT INTO user_question_banks (
    id, user_id, name, status
) VALUES
    (7601, 7601, 'phase4c normal migration bank', 1),
    (7602, 7602, 'phase4c target precedence bank', 1),
    (7603, 7603, 'phase4c rollback bank', 1),
    (7604, 7604, 'phase4c after failure bank', 1);

INSERT INTO user_bank_questions (
    id, bank_id, user_id, type, content
) VALUES
    (8601, 7601, 7601, 'single_choice', 'normal membership one'),
    (8602, 7601, 7601, 'multi_choice', 'normal membership two'),
    (8611, 7602, 7602, 'boolean', 'precedence membership'),
    (8621, 7603, 7603, 'fill', 'rollback membership'),
    (8631, 7604, 7604, 'essay', 'after failure membership'),
    (8699, 7602, 7602, 'essay', 'foreign-bank membership control');

-- Existing target state prevents automatic writes only after the source-derived
-- plan is proven to be a subset. The extra target row proves proper-subset behavior.
INSERT INTO user_question_tag_items (
    user_id, scope, scope_id, question_id, tag
) VALUES
    (7602, 'user_bank', 7602, 0, 'target-extra'),
    (7602, 'user_bank', 7602, 0, 'target-wins');

INSERT INTO user_progress (
    id, user_id, p_key, data,
    created_at, updated_at
) VALUES
    (8701, 7601, 'bank_7601_tags',
     '{"tags":[" alpha ","ALL","123456789012345678901234","alpha"],"question_tags":{"8601":["alpha","beta","all"],"8602":"gamma，beta"}}',
     TIMESTAMP '2026-07-17 01:00:00', TIMESTAMP '2026-07-17 01:00:00'),
    (8702, 7602, 'bank_7602_tags',
     '{"tags":["target-wins"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 02:00:00', TIMESTAMP '2026-07-17 02:00:00'),
    (8703, 7603, 'bank_7603_tags',
     '{"tags":["rollback-a","rollback-b"],"question_tags":{"8621":["rollback-a"]}}',
     TIMESTAMP '2026-07-17 03:00:00', TIMESTAMP '2026-07-17 03:00:00'),
    (8704, 7604, 'bank_7604_tags',
     '{"tags":[],"question_tags":{"8631":["after-failure"]}}',
     TIMESTAMP '2026-07-17 04:00:00', TIMESTAMP '2026-07-17 04:00:00'),
    (8705, 7605, 'bank_7999_tags',
     '{"tags":["missing-bank"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 05:00:00', TIMESTAMP '2026-07-17 05:00:00'),
    (8706, 7605, 'bank_7602_tags',
     '{"tags":["must-not-partially-apply"],"question_tags":{"8601":["orphan"]}}',
     TIMESTAMP '2026-07-17 05:01:00', TIMESTAMP '2026-07-17 05:01:00'),
    (8710, 7605, 'bank_07601_tags', '{"tags":["leading-zero"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:00:00', TIMESTAMP '2026-07-17 06:00:00'),
    (8711, 7605, 'bank_-1_tags', '{"tags":["negative"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:01:00', TIMESTAMP '2026-07-17 06:01:00'),
    (8712, 7605, 'bank_7601_tags_extra', '{"tags":["suffix"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:02:00', TIMESTAMP '2026-07-17 06:02:00'),
    (8713, 7605, 'prefix_bank_7601_tags', '{"tags":["prefix"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:03:00', TIMESTAMP '2026-07-17 06:03:00'),
    (8714, 7605, 'BANK_7601_tags', '{"tags":["case"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:04:00', TIMESTAMP '2026-07-17 06:04:00'),
    (8715, 7605, 'bank_7601_tags ', '{"tags":["space"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:05:00', TIMESTAMP '2026-07-17 06:05:00'),
    (8716, 7605, 'bank_2147483648_tags', '{"tags":["integer-overflow"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:06:00', TIMESTAMP '2026-07-17 06:06:00'),
    (8717, 7605, 'last_practice_session', '{"control":true}',
     TIMESTAMP '2026-07-17 06:07:00', TIMESTAMP '2026-07-17 06:07:00'),
    (8718, 7605, 'bank_0_tags', '{"tags":["zero-bank"],"question_tags":{}}',
     TIMESTAMP '2026-07-17 06:08:00', TIMESTAMP '2026-07-17 06:08:00');

ANALYZE users;
ANALYZE user_question_banks;
ANALYZE user_bank_questions;
ANALYZE user_question_tag_items;
ANALYZE user_progress;
