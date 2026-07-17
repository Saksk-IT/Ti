package io.saksk.ti.personalbank.infrastructure.persistence;

/** Test-only SQL frozen before the personal-bank usage-statistics implementation starts. */
public final class PersonalBankUsageStatsEvidenceSql {

    public static final String BANK_PROBE = """
            SELECT id,
                   user_id,
                   is_public,
                   status
            FROM user_question_banks
            WHERE id = :bank_id
            """;

    public static final String SHARED_USERS = """
            SELECT DISTINCT bsr.user_id AS user_id,
                            bs.expires_at AS expires_at
            FROM bank_share_records bsr
            JOIN bank_shares bs ON bsr.share_id = bs.id
            WHERE bsr.bank_id = :bank_id
              AND bsr.status = 1
              AND bs.is_active = TRUE
            """;

    public static final String PUBLIC_USERS = """
            SELECT DISTINCT user_id
            FROM public_bank_users
            WHERE bank_id = :bank_id
            """;

    private PersonalBankUsageStatsEvidenceSql() {
    }
}
