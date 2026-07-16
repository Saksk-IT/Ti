-- PUBLIC TEST-ONLY synthetic Phase 4A question-type state.

INSERT INTO questions (subject_id, type, content) VALUES
    (NULL, 'single_choice', 'duplicate-a'),
    (NULL, 'single_choice', 'duplicate-b'),
    (NULL, 'boolean', 'boolean'),
    (NULL, '', 'exact-empty'),
    (NULL, '  ', 'exact-whitespace'),
    (NULL, '判断题', 'unicode-a'),
    (NULL, '简答题', 'unicode-b');

ANALYZE questions;
