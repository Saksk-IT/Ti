-- Phase 4C Node C isolated operator fixture. No value is production data.

INSERT INTO users (
    id, username, password_hash, is_locked, session_version,
    has_password_set, email, last_active
) VALUES
    (9801, 'phase4c-operator-migrate', 'public-test-only-hash', false, 1,
     true, 'phase4c-operator-migrate@test.invalid',
     TIMESTAMP '2026-07-18 08:01:00'),
    (9802, 'phase4c-operator-present', 'public-test-only-hash', false, 1,
     true, 'phase4c-operator-present@test.invalid',
     TIMESTAMP '2026-07-18 08:02:00'),
    (9803, 'phase4c-operator-empty', 'public-test-only-hash', false, 1,
     true, 'phase4c-operator-empty@test.invalid',
     TIMESTAMP '2026-07-18 08:03:00');

INSERT INTO user_question_banks (id, user_id, name, status) VALUES
    (9801, 9801, 'operator migratable bank', 1),
    (9802, 9802, 'operator already-present bank', 1),
    (9803, 9803, 'operator empty-noop bank', 1);

INSERT INTO user_bank_questions (id, bank_id, user_id, type, content) VALUES
    (10801, 9801, 9801, 'single_choice', 'operator migration membership'),
    (10802, 9802, 9802, 'multi_choice', 'operator present membership');

-- Seed existing target facts before the operator-only insert guard is installed.
INSERT INTO user_question_tag_items (
    user_id, scope, scope_id, question_id, tag, created_at, updated_at
) VALUES
    (9802, 'user_bank', 9802, 0, 'present',
     TIMESTAMP '2026-07-18 08:10:00', TIMESTAMP '2026-07-18 08:10:00'),
    (9802, 'user_bank', 9802, 10802, 'bound',
     TIMESTAMP '2026-07-18 08:10:01', TIMESTAMP '2026-07-18 08:10:01'),
    (9802, 'user_bank', 9802, 0, 'bound',
     TIMESTAMP '2026-07-18 08:10:02', TIMESTAMP '2026-07-18 08:10:02'),
    (9802, 'user_bank', 9802, 0, 'target-extra',
     TIMESTAMP '2026-07-18 08:10:03', TIMESTAMP '2026-07-18 08:10:03');

INSERT INTO user_progress (
    id, user_id, p_key, data, created_at, updated_at
) VALUES
    (9901, 9801, 'bank_9801_tags',
     '{"tags":["alpha","NODEC_CANARY_RAW_TAG_7F21"],"question_tags":{"10801":["alpha"]}}',
     TIMESTAMP '2026-07-18 08:20:00', TIMESTAMP '2026-07-18 08:20:00'),
    (9902, 9802, 'bank_9802_tags',
     '{"tags":["present"],"question_tags":{"10802":["bound"]}}',
     TIMESTAMP '2026-07-18 08:20:01', TIMESTAMP '2026-07-18 08:20:01'),
    (9903, 9803, 'bank_9803_tags',
     '{"tags":[],"question_tags":{}}',
     TIMESTAMP '2026-07-18 08:20:02', TIMESTAMP '2026-07-18 08:20:02');

CREATE TRIGGER personal_bank_tag_target_insert_guard
BEFORE INSERT
ON user_question_tag_items
FOR EACH ROW
WHEN (current_user = 'ti_phase4c_tag_operator')
EXECUTE FUNCTION ti_migration.personal_bank_tag_target_insert_guard();

INSERT INTO ti_migration.operator_schema_metadata (
    singleton, schema_version, schema_fingerprint
) VALUES (
    true,
    1,
    'f4361024a36e4e509f1ca4203c2dca5ecfd5bf1eded036e462bbbb20f395f99c'
);

ANALYZE users;
ANALYZE user_question_banks;
ANALYZE user_bank_questions;
ANALYZE user_progress;
ANALYZE user_question_tag_items;
