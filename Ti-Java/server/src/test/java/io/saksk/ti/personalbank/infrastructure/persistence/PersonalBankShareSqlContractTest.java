package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import org.junit.jupiter.api.Test;

class PersonalBankShareSqlContractTest {

    private static final List<String> EXPECTED_SHARE_PROJECTION = List.of(
            "id",
            "bank_id",
            "owner_id",
            "share_code",
            "share_token",
            "permission",
            "expires_at",
            "max_uses",
            "current_uses",
            "is_active",
            "created_at");

    @Test
    void runtimeStatementsRemainByteEquivalentToThePreimplementationTargetSql() {
        assertThat(JdbcPersonalBankShareQueryAdapter.SELECT_OWNER_ACTIVE_BANK)
                .isEqualTo(PersonalBankShareListEvidenceSql.OWNER_STATUS_PROBE);
        assertThat(JdbcPersonalBankShareQueryAdapter.SELECT_PERSONAL_BANK_SHARES)
                .isEqualTo(PersonalBankShareListEvidenceSql.SHARE_LIST);
    }

    @Test
    void ownerProbeUsesOnlyBankViewerAndActiveStatusWithoutJoinOrMutation() {
        String sql = JdbcPersonalBankShareQueryAdapter.SELECT_OWNER_ACTIVE_BANK;
        String upper = sql.toUpperCase(Locale.ROOT);

        assertThat(normalized(sql)).isEqualTo(
                "SELECT id FROM user_question_banks WHERE id = :bank_id "
                        + "AND user_id = :viewer_id AND status = 1");
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertThat(occurrences(sql, ":viewer_id")).isOne();
        assertReadOnlySingleRelation(upper);
        assertThat(upper).doesNotContain("JOIN ", "BANK_SHARES");
    }

    @Test
    void shareListSelectsExactlyElevenRawFieldsWithObservablePostgresOrder() {
        String sql = JdbcPersonalBankShareQueryAdapter.SELECT_PERSONAL_BANK_SHARES;
        String upper = sql.toUpperCase(Locale.ROOT);

        assertThat(projection(sql)).containsExactlyElementsOf(EXPECTED_SHARE_PROJECTION);
        assertThat(sql)
                .contains("FROM bank_shares", "WHERE bank_id = :bank_id")
                .endsWith("ORDER BY created_at DESC NULLS FIRST\n")
                .doesNotContain(
                        "SELECT *",
                        "owner_id =",
                        "is_active =",
                        "expires_at ",
                        "permission =",
                        "id DESC",
                        "id ASC",
                        "LIMIT ",
                        "OFFSET ",
                        "COALESCE",
                        "CASE ",
                        "TRIM(");
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertReadOnlySingleRelation(upper);
        assertThat(upper).doesNotContain("JOIN ", "USER_QUESTION_BANKS");
    }

    @Test
    void adapterBindsBankAsIntegerAndViewerAsBigint() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toRealPath();
        Path source = basedir.resolve(
                "src/main/java/io/saksk/ti/personalbank/infrastructure/persistence/"
                        + "JdbcPersonalBankShareQueryAdapter.java");
        String java = Files.readString(source, StandardCharsets.UTF_8);

        assertThat(java)
                .contains(
                        ".param(\"bank_id\", bankId, Types.INTEGER)",
                        ".param(\"viewer_id\", viewerId, Types.BIGINT)")
                .doesNotContain(
                        "Math.toIntExact",
                        "(int) viewerId",
                        "ORDER BY created_at DESC, id");
    }

    private static List<String> projection(String sql) {
        String columns = sql.substring("SELECT ".length(), sql.indexOf("\nFROM "));
        return Arrays.stream(columns.split(",\\R"))
                .map(String::trim)
                .toList();
    }

    private static void assertReadOnlySingleRelation(String upper) {
        assertThat(upper).doesNotContain(
                ";",
                "INSERT ",
                "UPDATE ",
                "DELETE ",
                "CREATE ",
                "ALTER ",
                "DROP ",
                "TEMP ");
        assertThat(occurrences(upper, "SELECT ")).isOne();
    }

    private static String normalized(String sql) {
        return sql.replaceAll("\\s+", " ").trim();
    }

    private static int occurrences(String text, String token) {
        return text.split(java.util.regex.Pattern.quote(token), -1).length - 1;
    }
}
