package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import org.junit.jupiter.api.Test;

class PersonalBankUsageStatsEvidenceSqlContractTest {

    @Test
    void bankProbePreservesTheUnfilteredLegacyLookup() {
        String sql = normalized(PersonalBankUsageStatsEvidenceSql.BANK_PROBE);

        assertThat(sql).isEqualTo("select id, user_id, is_public, status "
                + "from user_question_banks where id = :bank_id");
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertThat(sql).doesNotContain("status = 1", "user_id =", "for update");
    }

    @Test
    void sharedUsersPreservePairDistinctAndOnlyTheTwoLegacyStateFilters() {
        String sql = normalized(PersonalBankUsageStatsEvidenceSql.SHARED_USERS);

        assertThat(sql).isEqualTo("select distinct bsr.user_id as user_id, "
                + "bs.expires_at as expires_at from bank_share_records bsr "
                + "join bank_shares bs on bsr.share_id = bs.id "
                + "where bsr.bank_id = :bank_id and bsr.status = 1 "
                + "and bs.is_active = true");
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertThat(sql).doesNotContain(
                "bs.bank_id =", "owner_id =", "expires_at <", "expires_at >",
                "max_uses", "current_uses", "order by", "group by");
    }

    @Test
    void publicUsersPreserveTheSingleBankScopedDistinctProjection() {
        String sql = normalized(PersonalBankUsageStatsEvidenceSql.PUBLIC_USERS);

        assertThat(sql).isEqualTo("select distinct user_id from public_bank_users "
                + "where bank_id = :bank_id");
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertThat(sql).doesNotContain("status", "last_access_at", "order by");
    }

    @Test
    void noPreimplementationEvidenceSqlCanWriteOrChangeSchema() {
        for (String statement : new String[] {
                PersonalBankUsageStatsEvidenceSql.BANK_PROBE,
                PersonalBankUsageStatsEvidenceSql.SHARED_USERS,
                PersonalBankUsageStatsEvidenceSql.PUBLIC_USERS
        }) {
            assertThat(normalized(statement)).startsWith("select ").doesNotContain(
                    " insert ", " update ", " delete ", " merge ", " create ",
                    " alter ", " drop ", " truncate ", " grant ", " revoke ", ";");
        }
    }

    private static String normalized(String sql) {
        return sql.strip().replaceAll("\\s+", " ").toLowerCase(Locale.ROOT);
    }

    private static int occurrences(String value, String fragment) {
        return (value.length() - value.replace(fragment, "").length()) / fragment.length();
    }
}
