-- Phase 4C test-only projection for explicit legacy personal-bank tag migration evidence.
-- It is neither a production schema migration nor a Learning/PersonalBank runtime API.

CREATE VIEW phase4c_personal_bank_membership_projection AS
SELECT b.id AS bank_id,
       q.id AS question_id
FROM user_question_banks b
LEFT JOIN user_bank_questions q ON q.bank_id = b.id;
