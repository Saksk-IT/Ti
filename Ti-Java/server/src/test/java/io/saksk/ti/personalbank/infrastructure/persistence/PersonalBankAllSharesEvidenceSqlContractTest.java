package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import org.junit.jupiter.api.Test;

class PersonalBankAllSharesEvidenceSqlContractTest {

    @Test
    void allSharesUsesOneViewerBindAndTwelveExplicitDatabaseFields() {
        String sql = normalized(PersonalBankAllSharesEvidenceSql.ALL_SHARES);

        assertThat(sql).isEqualTo("select bs.id, bs.bank_id, bs.owner_id, bs.share_code, "
                + "bs.share_token, bs.permission, bs.expires_at, bs.max_uses, "
                + "bs.current_uses, bs.is_active, bs.created_at, b.name as bank_name "
                + "from bank_shares bs join user_question_banks b on bs.bank_id = b.id "
                + "where bs.owner_id = :viewer_id and b.status = 1 "
                + "order by bs.created_at desc nulls first");
        assertThat(occurrences(sql, ":viewer_id")).isOne();
        assertThat(sql).doesNotContain(
                "select *", " limit ", " offset ", " for update", "id desc", ";");
    }

    @Test
    void allSharesPreservesOwnerAndActiveBankFiltersWithoutFilteringShareState() {
        String sql = normalized(PersonalBankAllSharesEvidenceSql.ALL_SHARES);

        assertThat(sql).contains(
                "where bs.owner_id = :viewer_id",
                "and b.status = 1",
                "order by bs.created_at desc nulls first");
        assertThat(sql).doesNotContain(
                "bs.is_active =", "bs.expires_at <", "bs.expires_at >",
                "bs.current_uses <", "bs.max_uses >",
                "b.user_id =", "share_link", "share_base_url", "request.host");
    }

    @Test
    void targetIsOnlyAnExplicitProjectionAndPostgresNullOrderingTightening() {
        String legacy = normalized(PersonalBankAllSharesEvidenceSql.LEGACY_ALL_SHARES);
        String target = normalized(PersonalBankAllSharesEvidenceSql.ALL_SHARES);

        assertThat(legacy).isEqualTo("select bs.*, b.name as bank_name "
                + "from bank_shares bs join user_question_banks b on bs.bank_id = b.id "
                + "where bs.owner_id = :uid and b.status = 1 "
                + "order by bs.created_at desc");
        assertThat(target.replace(":viewer_id", ":uid"))
                .contains("from bank_shares bs join user_question_banks b "
                        + "on bs.bank_id = b.id where bs.owner_id = :uid and b.status = 1")
                .endsWith("order by bs.created_at desc nulls first");
    }

    @Test
    void noPreimplementationEvidenceSqlCanWriteOrChangeSchema() {
        for (String statement : new String[] {
                PersonalBankAllSharesEvidenceSql.ALL_SHARES,
                PersonalBankAllSharesEvidenceSql.LEGACY_ALL_SHARES
        }) {
            assertThat(normalized(statement)).startsWith("select ").doesNotContain(
                    " insert ", " update ", " delete ", " merge ", " create ",
                    " alter ", " drop ", " truncate ", " grant ", " revoke ");
        }
    }

    private static String normalized(String sql) {
        return sql.strip().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT);
    }

    private static int occurrences(String value, String fragment) {
        return (value.length() - value.replace(fragment, "").length()) / fragment.length();
    }
}
