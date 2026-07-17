-- Phase 4B test-only rows for preimplementation personal-bank user-counts evidence.
-- This extends 062-067 fixtures and is not a production migration.

INSERT INTO user_bank_questions (
    id, bank_id, user_id, type, content
) VALUES
    (8101, 7101, 7001, 'single_choice', 'single choice α'),
    (8102, 7101, 7001, 'multi_choice', 'multiple choice β'),
    (8103, 7101, 7001, 'boolean', 'boolean γ'),
    (8104, 7101, 7001, 'essay', 'essay δ'),
    (8105, 7101, 7001, 'fill', 'fill ε'),
    (8106, 7101, 7001, 'unexpected_type', 'unknown raw type'),
    (8107, 7101, 7001, '', 'blank raw type'),
    (8108, 7101, 7001, NULL, 'null raw type'),
    (8109, 7101, 7001, 'single_choice', 'second single choice'),
    (8201, 7105, 7002, 'single_choice', 'other-bank control');

INSERT INTO user_bank_favorites (
    id, user_id, bank_id, question_id
) VALUES
    (8301, 7001, 7101, 8101),
    -- Deliberately attached to the wrong favorites.bank_id. The legacy SQL joins
    -- by question_id and viewer only, so this still counts for question bank 7101.
    (8302, 7001, 7105, 8102),
    (8303, 7001, 7101, 8104),
    (8304, 7001, 7101, 8108),
    (8305, 7001, 7105, 8201),
    (8306, 7002, 7101, 8103);

INSERT INTO user_bank_mistakes (
    id, user_id, bank_id, question_id, wrong_count
) VALUES
    (8401, 7001, 7101, 8102, 1),
    -- Deliberately attached to the wrong mistakes.bank_id for the same reason.
    (8402, 7001, 7105, 8103, 2),
    (8403, 7001, 7101, 8105, 3),
    (8404, 7001, 7101, 8108, 1),
    (8405, 7001, 7105, 8201, 1),
    (8406, 7002, 7101, 8104, 1);

INSERT INTO user_question_tag_items (
    user_id, scope, scope_id, question_id, tag
) VALUES
    (7001, 'user_bank', 7101, 0, 'alpha'),
    (7001, 'user_bank', 7101, 0, 'beta'),
    (7001, 'user_bank', 7101, 0, 'raw'),
    (7001, 'user_bank', 7101, 8101, 'alpha'),
    (7001, 'user_bank', 7101, 8102, 'alpha'),
    (7001, 'user_bank', 7101, 8201, 'alpha'),
    (7001, 'user_bank', 7101, 8102, 'beta'),
    (7001, 'user_bank', 7101, 8105, 'beta'),
    (7001, 'user_bank', 7101, 8108, 'raw'),
    (7002, 'user_bank', 7101, 8103, 'alpha'),
    (7001, 'user_bank', 7105, 8201, 'other-scope');

INSERT INTO user_progress (
    id, user_id, p_key, data
) VALUES
    (8501, 7001, 'bank_7101_tags',
     '{"tags":["legacy-only"],"question_tags":{"8109":["legacy-only"]}}');

ANALYZE user_bank_questions;
ANALYZE user_bank_favorites;
ANALYZE user_bank_mistakes;
ANALYZE user_progress;
ANALYZE user_question_tag_items;
