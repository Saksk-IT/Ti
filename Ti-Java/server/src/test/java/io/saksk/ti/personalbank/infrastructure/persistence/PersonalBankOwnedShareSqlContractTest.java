package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

class PersonalBankOwnedShareSqlContractTest {

    private static final List<String> EXPECTED_PROJECTION = List.of(
            "bs.id",
            "bs.bank_id",
            "bs.owner_id",
            "bs.share_code",
            "bs.share_token",
            "bs.permission",
            "bs.expires_at",
            "bs.max_uses",
            "bs.current_uses",
            "bs.is_active",
            "bs.created_at",
            "b.name AS bank_name");

    @Test
    void runtimeStatementRemainsByteEquivalentToThePreimplementationTargetSql() {
        assertThat(JdbcPersonalBankOwnedShareQueryAdapter.SELECT_OWNED_SHARES)
                .isEqualTo(PersonalBankAllSharesEvidenceSql.ALL_SHARES);
    }

    @Test
    void selectsExactlyTwelveRawFieldsWithTheSingleFrozenJoinAndOrder() {
        String sql = JdbcPersonalBankOwnedShareQueryAdapter.SELECT_OWNED_SHARES;
        String upper = sql.toUpperCase(Locale.ROOT);
        String where = sql.substring(sql.indexOf("WHERE "));

        assertThat(projection(sql)).containsExactlyElementsOf(EXPECTED_PROJECTION);
        assertThat(sql)
                .contains(
                        "FROM bank_shares bs",
                        "JOIN user_question_banks b ON bs.bank_id = b.id",
                        "WHERE bs.owner_id = :viewer_id",
                        "AND b.status = 1")
                .endsWith("ORDER BY bs.created_at DESC NULLS FIRST\n")
                .doesNotContain(
                        "SELECT *",
                        "LEFT JOIN",
                        "RIGHT JOIN",
                        "FULL JOIN",
                        "b.user_id",
                        "ORDER BY bs.created_at DESC,",
                        "ORDER BY bs.created_at DESC NULLS FIRST,",
                        "LIMIT ",
                        "OFFSET ",
                        "COALESCE",
                        "CASE ",
                        "TRIM(",
                        "share_link");
        assertThat(where).doesNotContain(
                "bs.is_active =",
                "bs.expires_at ",
                "bs.permission =",
                "bs.max_uses ",
                "bs.current_uses ");
        assertThat(occurrences(sql, ":viewer_id")).isOne();
        assertThat(occurrences(upper, "SELECT ")).isOne();
        assertThat(occurrences(upper, "JOIN ")).isOne();
        assertThat(upper).doesNotContain(
                ";", "INSERT ", "UPDATE ", "DELETE ", "CREATE ",
                "ALTER ", "DROP ", "TEMP ");
    }

    @Test
    void adapterBindsViewerAsBigintWithoutNarrowingOrHttpProjection() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toRealPath();
        Path source = basedir.resolve(
                "src/main/java/io/saksk/ti/personalbank/infrastructure/persistence/"
                        + "JdbcPersonalBankOwnedShareQueryAdapter.java");
        String java = Files.readString(source, StandardCharsets.UTF_8);

        assertThat(java)
                .contains(".param(\"viewer_id\", viewerId, Types.BIGINT)")
                .doesNotContain(
                        "Math.toIntExact",
                        "(int) viewerId",
                        "shareLink",
                        "SHARE_BASE_URL",
                        "HttpServletRequest");
    }

    private static List<String> projection(String sql) {
        String columns = sql.substring("SELECT ".length(), sql.indexOf("\nFROM "));
        return Arrays.stream(columns.split(",\\R"))
                .map(String::trim)
                .toList();
    }

    private static int occurrences(String text, String token) {
        return text.split(Pattern.quote(token), -1).length - 1;
    }
}
