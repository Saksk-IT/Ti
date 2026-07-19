-- Phase 4C test-only projections for the global legacy personal-bank tag
-- preflight. They are fingerprint sentinels, not production schema objects and
-- grant no migration, operator, credential, backup, or cutover authorization.

CREATE VIEW phase4c_legacy_personal_bank_tag_global_source_projection AS
SELECT id AS source_row_id,
       user_id,
       p_key,
       data,
       created_at,
       updated_at
FROM user_progress
WHERE p_key LIKE 'bank_%_tags';

CREATE VIEW phase4c_legacy_personal_bank_tag_global_target_projection AS
SELECT user_id,
       scope,
       scope_id,
       question_id,
       tag,
       created_at,
       updated_at
FROM user_question_tag_items
WHERE scope = 'user_bank';

-- 020 creates this ephemeral Testcontainers-only role before the Phase 3/4
-- relations exist. Grant only the reads needed by this evidence fixture so the
-- preflight itself runs under a database-enforced read-only identity.
GRANT SELECT ON user_progress,
                user_question_tag_items,
                user_question_banks,
                user_bank_questions,
                phase4c_legacy_personal_bank_tag_global_source_projection,
                phase4c_legacy_personal_bank_tag_global_target_projection
TO ti_phase2_read;
