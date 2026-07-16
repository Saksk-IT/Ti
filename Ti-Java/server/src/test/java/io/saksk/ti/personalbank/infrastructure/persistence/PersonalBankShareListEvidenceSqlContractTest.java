package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import org.junit.jupiter.api.Test;

class PersonalBankShareListEvidenceSqlContractTest {

    @Test
    void ownerStatusProbeRemainsTheFirstTwoBindReadWithoutJoin() {
        String sql = normalized(PersonalBankShareListEvidenceSql.OWNER_STATUS_PROBE);

        assertThat(sql).isEqualTo("select id from user_question_banks "
                + "where id = :bank_id and user_id = :viewer_id and status = 1");
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertThat(occurrences(sql, ":viewer_id")).isOne();
        assertThat(sql).doesNotContain(
                " join ", " limit ", " for update", "cast(", "::integer", "::bigint", ";");
    }

    @Test
    void shareListUsesElevenExplicitColumnsAndPostgresDescNullsFirst() {
        String sql = normalized(PersonalBankShareListEvidenceSql.SHARE_LIST);

        assertThat(sql).isEqualTo("select id, bank_id, owner_id, share_code, share_token, "
                + "permission, expires_at, max_uses, current_uses, is_active, created_at "
                + "from bank_shares where bank_id = :bank_id "
                + "order by created_at desc nulls first");
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertThat(sql).doesNotContain(
                "select *", " join ", "owner_id =", "is_active =", "expires_at ",
                " limit ", " offset ", "id desc", ";");
    }

    @Test
    void targetQueriesAreSemanticTighteningsOfTheTwoLegacyStatementsOnly() {
        String legacyProbe = normalized(PersonalBankShareListEvidenceSql.LEGACY_OWNER_STATUS_PROBE);
        String targetProbe = normalized(PersonalBankShareListEvidenceSql.OWNER_STATUS_PROBE);
        String legacyList = normalized(PersonalBankShareListEvidenceSql.LEGACY_SHARE_LIST);
        String targetList = normalized(PersonalBankShareListEvidenceSql.SHARE_LIST);

        assertThat(legacyProbe.replace(":uid", ":viewer_id")).isEqualTo(targetProbe);
        assertThat(legacyList).isEqualTo("select * from bank_shares where bank_id = :bank_id "
                + "order by created_at desc");
        assertThat(targetList).endsWith("order by created_at desc nulls first");
        assertThat(targetList).contains("from bank_shares where bank_id = :bank_id");
    }

    @Test
    void noPreimplementationEvidenceSqlCanWriteOrChangeSchema() {
        for (String statement : new String[] {
                PersonalBankShareListEvidenceSql.OWNER_STATUS_PROBE,
                PersonalBankShareListEvidenceSql.SHARE_LIST,
                PersonalBankShareListEvidenceSql.LEGACY_OWNER_STATUS_PROBE,
                PersonalBankShareListEvidenceSql.LEGACY_SHARE_LIST
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
