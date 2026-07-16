package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;

class PersonalBankCategorySqlContractTest {

    private static final List<String> EXPECTED_PROJECTION = List.of(
            "c.id AS category_id",
            "c.user_id AS category_user_id",
            "c.name AS category_name",
            "c.description AS category_description",
            "c.sort_order AS category_sort_order",
            "c.created_at AS category_created_at",
            "c.updated_at AS category_updated_at",
            "COUNT(b.id) AS bank_count");

    @Test
    void usesOneEightColumnCurrentIdentityAggregate() {
        String sql = JdbcPersonalBankCategoryQueryAdapter.SELECT_PERSONAL_BANK_CATEGORIES;

        assertThat(projection(sql)).containsExactlyElementsOf(EXPECTED_PROJECTION);
        assertThat(sql)
                .contains(
                        "FROM user_bank_categories c",
                        "LEFT JOIN user_question_banks b",
                        "ON b.category_id = c.id",
                        "AND b.status = 1",
                        "WHERE c.user_id = :user_id")
                .doesNotContain(
                        "SELECT *",
                        "b.user_id",
                        "LIMIT ",
                        "OFFSET ",
                        "FETCH FIRST");
        assertThat(occurrences(sql, ":user_id")).isOne();
        assertThat(occurrences(sql.toUpperCase(Locale.ROOT), "SELECT ")).isOne();
    }

    @Test
    void preservesNullableRawFieldsAndPostgresNullsLastOrder() {
        String sql = JdbcPersonalBankCategoryQueryAdapter.SELECT_PERSONAL_BANK_CATEGORIES;

        assertThat(sql)
                .contains(
                        "GROUP BY c.id,",
                        "c.user_id,",
                        "c.name,",
                        "c.description,",
                        "c.sort_order,",
                        "c.created_at,",
                        "c.updated_at")
                .endsWith("ORDER BY c.sort_order ASC NULLS LAST, c.id ASC")
                .doesNotContain(
                        "COALESCE",
                        "CASE ",
                        "LOWER(",
                        "TRIM(");
    }

    @Test
    void remainsAReadOnlySingleStatementWithoutHiddenRelations() {
        String sql = JdbcPersonalBankCategoryQueryAdapter.SELECT_PERSONAL_BANK_CATEGORIES;
        String upper = sql.toUpperCase(Locale.ROOT);

        assertThat(sql).doesNotContain(";");
        assertThat(upper).doesNotContain(
                "INSERT ",
                "UPDATE ",
                "DELETE ",
                "CREATE ",
                "ALTER ",
                "DROP ",
                "TEMP ",
                "USERS ",
                "BANK_SHARES",
                "USER_BANK_QUESTIONS");
        assertThat(occurrences(upper, "JOIN ")).isOne();
        assertThat(occurrences(upper, "COUNT(")).isOne();
    }

    private static List<String> projection(String sql) {
        String columns = sql.substring("SELECT ".length(), sql.indexOf("\nFROM "));
        return Arrays.stream(columns.split(",\\R"))
                .map(String::trim)
                .toList();
    }

    private static int occurrences(String text, String token) {
        return text.split(java.util.regex.Pattern.quote(token), -1).length - 1;
    }
}
