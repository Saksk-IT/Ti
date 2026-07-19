-- Phase 4C test-only mixed global-preflight fixture for bank_<bank_id>_tags.
-- The fixture deliberately contains apply-ready rows and independent blockers.
-- A conforming Node A run is read-only and therefore leaves every row and
-- schema/index fingerprint byte-for-byte unchanged.

INSERT INTO users (
    id, username, password_hash, is_locked, session_version, has_password_set, email
) VALUES
    (9401, 'phase4c-global-ready', 'public-test-only-hash', false, 1, true,
     'phase4c-global-ready@test.invalid'),
    (9402, 'phase4c-global-normalized', 'public-test-only-hash', false, 1, true,
     'phase4c-global-normalized@test.invalid'),
    (9403, 'phase4c-global-present', 'public-test-only-hash', false, 1, true,
     'phase4c-global-present@test.invalid'),
    (9404, 'phase4c-global-conflict', 'public-test-only-hash', false, 1, true,
     'phase4c-global-conflict@test.invalid'),
    (9405, 'phase4c-global-missing', 'public-test-only-hash', false, 1, true,
     'phase4c-global-missing@test.invalid'),
    (9406, 'phase4c-global-orphan', 'public-test-only-hash', false, 1, true,
     'phase4c-global-orphan@test.invalid'),
    (9407, 'phase4c-global-invalid', 'public-test-only-hash', false, 1, true,
     'phase4c-global-invalid@test.invalid'),
    (9408, 'phase4c-global-id-conflict', 'public-test-only-hash', false, 1, true,
     'phase4c-global-id-conflict@test.invalid'),
    (9409, 'phase4c-global-tag-conflict', 'public-test-only-hash', false, 1, true,
     'phase4c-global-tag-conflict@test.invalid'),
    (9410, 'phase4c-global-target-invalid', 'public-test-only-hash', false, 1, true,
     'phase4c-global-target-invalid@test.invalid'),
    (9411, 'phase4c-global-near-miss', 'public-test-only-hash', false, 1, true,
     'phase4c-global-near-miss@test.invalid'),
    (9412, 'phase4c-global-control', 'public-test-only-hash', false, 1, true,
     'phase4c-global-control@test.invalid'),
    (9413, 'phase4c-global-membership-down', 'public-test-only-hash', false, 1, true,
     'phase4c-global-membership-down@test.invalid');

INSERT INTO user_question_banks (
    id, user_id, name, status
) VALUES
    (9401, 9401, 'global preflight ready bank', 1),
    (9402, 9402, 'global preflight normalized-id bank', 1),
    (9403, 9403, 'global preflight target-present bank', 1),
    (9404, 9404, 'global preflight target-conflict bank', 1),
    (9406, 9406, 'global preflight orphan bank', 1),
    (9407, 9407, 'global preflight invalid-data bank', 1),
    (9408, 9408, 'global preflight normalized-id-conflict bank', 1),
    (9409, 9409, 'global preflight tag-collision bank', 1),
    (9410, 9410, 'global preflight invalid-target bank', 1),
    (9411, 9411, 'global preflight near-miss control bank', 1),
    (9412, 9412, 'global preflight empty-noop bank', 1),
    (9413, 9413, 'global preflight unavailable-membership bank', 1);

INSERT INTO user_bank_questions (
    id, bank_id, user_id, type, content
) VALUES
    (10401, 9401, 9401, 'single_choice', 'ready membership one'),
    (10402, 9401, 9401, 'multi_choice', 'ready membership two'),
    (10411, 9402, 9402, 'boolean', 'normalized membership'),
    (10421, 9403, 9403, 'fill', 'target-present membership'),
    (10431, 9404, 9404, 'essay', 'target-conflict membership'),
    (10441, 9406, 9406, 'single_choice', 'orphan-row own-bank membership'),
    (10442, 9401, 9401, 'single_choice', 'foreign membership for orphan row'),
    (10451, 9407, 9407, 'multi_choice', 'invalid-data membership'),
    (10461, 9408, 9408, 'boolean', 'normalized-id-conflict membership'),
    (10471, 9409, 9409, 'fill', 'tag-collision membership'),
    (10481, 9410, 9410, 'essay', 'invalid-target membership'),
    (10491, 9411, 9411, 'essay', 'near-miss control membership'),
    (10501, 9413, 9413, 'single_choice', 'unavailable membership probe');

-- An exact source-plan superset is valid target precedence; no write is needed.
INSERT INTO user_question_tag_items (
    user_id, scope, scope_id, question_id, tag,
    created_at, updated_at
) VALUES
    (9403, 'user_bank', 9403, 0, 'already-there',
     TIMESTAMP '2026-07-18 00:03:00', TIMESTAMP '2026-07-18 00:03:00'),
    (9403, 'user_bank', 9403, 10421, 'bound',
     TIMESTAMP '2026-07-18 00:03:01', TIMESTAMP '2026-07-18 00:03:01'),
    (9403, 'user_bank', 9403, 0, 'bound',
     TIMESTAMP '2026-07-18 00:03:02', TIMESTAMP '2026-07-18 00:03:02'),
    (9403, 'user_bank', 9403, 0, 'target-extra',
     TIMESTAMP '2026-07-18 00:03:03', TIMESTAMP '2026-07-18 00:03:03'),

    -- This source-derived plan is not a subset of the existing target.
    (9404, 'user_bank', 9404, 0, 'target-only',
     TIMESTAMP '2026-07-18 00:04:00', TIMESTAMP '2026-07-18 00:04:00'),

    -- Existing target data is deliberately non-canonical and independently
    -- blocks the global apply decision.
    (9410, 'user_bank', 9410, 0, 'ALL',
     TIMESTAMP '2026-07-18 00:10:00', TIMESTAMP '2026-07-18 00:10:00'),
    (9410, 'user_bank', 9410, 10999, 'foreign-question',
     TIMESTAMP '2026-07-18 00:10:01', TIMESTAMP '2026-07-18 00:10:01');

INSERT INTO user_progress (
    id, user_id, p_key, data,
    created_at, updated_at
) VALUES
    (9501, 9401, 'bank_9401_tags',
     '{"tags":[" alpha ","ALL","alpha","beta"],"question_tags":{"10401":"alpha，gamma","10402":["beta"]}}',
     TIMESTAMP '2026-07-18 01:01:00', TIMESTAMP '2026-07-18 01:01:00'),

    -- Python int-compatible Unicode digits, sign, underscores and whitespace
    -- normalize to question 10411 without a collision.
    (9502, 9402, 'bank_9402_tags',
     '{"tags":["normalized"],"question_tags":{" +１０_４１１ ":["normalized"]}}',
     TIMESTAMP '2026-07-18 01:02:00', TIMESTAMP '2026-07-18 01:02:00'),

    (9503, 9403, 'bank_9403_tags',
     '{"tags":["already-there"],"question_tags":{"10421":["bound"]}}',
     TIMESTAMP '2026-07-18 01:03:00', TIMESTAMP '2026-07-18 01:03:00'),
    (9504, 9404, 'bank_9404_tags',
     '{"tags":["source-only"],"question_tags":{"10431":["source-bound"]}}',
     TIMESTAMP '2026-07-18 01:04:00', TIMESTAMP '2026-07-18 01:04:00'),
    (9505, 9405, 'bank_9499_tags',
     '{"tags":["missing-bank"],"question_tags":{}}',
     TIMESTAMP '2026-07-18 01:05:00', TIMESTAMP '2026-07-18 01:05:00'),
    (9506, 9406, 'bank_9406_tags',
     '{"tags":["orphan"],"question_tags":{"10442":["foreign-bank"]}}',
     TIMESTAMP '2026-07-18 01:06:00', TIMESTAMP '2026-07-18 01:06:00'),
    (9507, 9407, 'bank_9407_tags',
     '{"tags":"not-a-list","question_tags":{"10451":["invalid"]}}',
     TIMESTAMP '2026-07-18 01:07:00', TIMESTAMP '2026-07-18 01:07:00'),

    -- Two raw object keys normalize to the same positive question ID.
    (9508, 9408, 'bank_9408_tags',
     '{"tags":[],"question_tags":{"10461":["plain"],"+１０_４６１":["normalized"]}}',
     TIMESTAMP '2026-07-18 01:08:00', TIMESTAMP '2026-07-18 01:08:00'),

    -- Distinct raw tags collapse after the legacy 20-code-point truncation.
    (9509, 9409, 'bank_9409_tags',
     '{"tags":["12345678901234567890-a","12345678901234567890-b"],"question_tags":{"10471":[]}}',
     TIMESTAMP '2026-07-18 01:09:00', TIMESTAMP '2026-07-18 01:09:00'),
    (9510, 9410, 'bank_9410_tags',
     '{"tags":["canonical-source"],"question_tags":{"10481":["canonical-source"]}}',
     TIMESTAMP '2026-07-18 01:10:00', TIMESTAMP '2026-07-18 01:10:00'),

    -- Broad legacy-shaped near misses must never silently normalize into a
    -- canonical source key during the global sweep.
    (9511, 9411, 'bank_09411_tags',
     '{"tags":["leading-zero-key"],"question_tags":{"10491":[]}}',
     TIMESTAMP '2026-07-18 01:11:00', TIMESTAMP '2026-07-18 01:11:00'),
    (9512, 9411, 'bank_9411_extra_tags',
     '{"tags":["extra-segment-key"],"question_tags":{"10491":[]}}',
     TIMESTAMP '2026-07-18 01:12:00', TIMESTAMP '2026-07-18 01:12:00'),
    (9513, 9411, 'bank_９４１１_tags',
     '{"tags":["unicode-key"],"question_tags":{"10491":[]}}',
     TIMESTAMP '2026-07-18 01:13:00', TIMESTAMP '2026-07-18 01:13:00'),
    (9514, 9411, 'bank_2147483648_tags',
     '{"tags":["overflow-key"],"question_tags":{}}',
     TIMESTAMP '2026-07-18 01:14:00', TIMESTAMP '2026-07-18 01:14:00'),

    (9517, 9412, 'bank_9412_tags',
     '{"tags":[],"question_tags":{}}',
     TIMESTAMP '2026-07-18 01:17:00', TIMESTAMP '2026-07-18 01:17:00'),
    (9518, 9413, 'bank_9413_tags',
     '{"tags":["membership-unavailable"],"question_tags":{"10501":["probe"]}}',
     TIMESTAMP '2026-07-18 01:18:00', TIMESTAMP '2026-07-18 01:18:00'),

    -- Unrelated namespaces are immutable controls and are not candidates.
    (9515, 9412, 'last_practice_session', '{"control":true}',
     TIMESTAMP '2026-07-18 01:15:00', TIMESTAMP '2026-07-18 01:15:00'),
    (9516, 9412, 'question_tags_v1', '{"control":true}',
     TIMESTAMP '2026-07-18 01:16:00', TIMESTAMP '2026-07-18 01:16:00');

ANALYZE users;
ANALYZE user_question_banks;
ANALYZE user_bank_questions;
ANALYZE user_question_tag_items;
ANALYZE user_progress;
