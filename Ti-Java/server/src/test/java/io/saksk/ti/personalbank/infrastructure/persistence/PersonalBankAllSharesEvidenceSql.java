package io.saksk.ti.personalbank.infrastructure.persistence;

/** Test-only SQL frozen before the personal-bank all-shares implementation starts. */
public final class PersonalBankAllSharesEvidenceSql {

    public static final String ALL_SHARES = """
            SELECT bs.id,
                   bs.bank_id,
                   bs.owner_id,
                   bs.share_code,
                   bs.share_token,
                   bs.permission,
                   bs.expires_at,
                   bs.max_uses,
                   bs.current_uses,
                   bs.is_active,
                   bs.created_at,
                   b.name AS bank_name
            FROM bank_shares bs
            JOIN user_question_banks b ON bs.bank_id = b.id
            WHERE bs.owner_id = :viewer_id
              AND b.status = 1
            ORDER BY bs.created_at DESC NULLS FIRST
            """;

    public static final String LEGACY_ALL_SHARES = """
            SELECT bs.*,
                   b.name AS bank_name
            FROM bank_shares bs
            JOIN user_question_banks b ON bs.bank_id = b.id
            WHERE bs.owner_id = :uid
              AND b.status = 1
            ORDER BY bs.created_at DESC
            """;

    private PersonalBankAllSharesEvidenceSql() {
    }
}
