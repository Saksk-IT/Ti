package io.saksk.ti.personalbank.infrastructure.persistence;

/** Test-only SQL frozen before the personal-bank share-list implementation starts. */
public final class PersonalBankShareListEvidenceSql {

    public static final String OWNER_STATUS_PROBE = """
            SELECT id
            FROM user_question_banks
            WHERE id = :bank_id
              AND user_id = :viewer_id
              AND status = 1
            """;

    public static final String SHARE_LIST = """
            SELECT id,
                   bank_id,
                   owner_id,
                   share_code,
                   share_token,
                   permission,
                   expires_at,
                   max_uses,
                   current_uses,
                   is_active,
                   created_at
            FROM bank_shares
            WHERE bank_id = :bank_id
            ORDER BY created_at DESC NULLS FIRST
            """;

    public static final String LEGACY_OWNER_STATUS_PROBE = """
            SELECT id
            FROM user_question_banks
            WHERE id = :bank_id
              AND user_id = :uid
              AND status = 1
            """;

    public static final String LEGACY_SHARE_LIST = """
            SELECT *
            FROM bank_shares
            WHERE bank_id = :bank_id
            ORDER BY created_at DESC
            """;

    private PersonalBankShareListEvidenceSql() {
    }
}
