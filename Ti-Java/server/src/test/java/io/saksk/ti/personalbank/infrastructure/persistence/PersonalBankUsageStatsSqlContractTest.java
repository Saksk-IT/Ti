package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

class PersonalBankUsageStatsSqlContractTest {

    @Test
    void runtimeStatementsRemainByteEquivalentToThePreimplementationEvidence() {
        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.SELECT_BANK)
                .isEqualTo(PersonalBankUsageStatsEvidenceSql.BANK_PROBE);
        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.SELECT_SHARED_USERS)
                .isEqualTo(PersonalBankUsageStatsEvidenceSql.SHARED_USERS);
        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.SELECT_PUBLIC_USER_IDS)
                .isEqualTo(PersonalBankUsageStatsEvidenceSql.PUBLIC_USERS);
    }

    @Test
    void keepsThreeIndependentReadOnlyStatementsWithoutHiddenFilteringOrOrdering() {
        List<String> statements = List.of(
                JdbcPersonalBankUsageStatsQueryAdapter.SELECT_BANK,
                JdbcPersonalBankUsageStatsQueryAdapter.SELECT_SHARED_USERS,
                JdbcPersonalBankUsageStatsQueryAdapter.SELECT_PUBLIC_USER_IDS);

        statements.forEach(PersonalBankUsageStatsSqlContractTest::assertSingleReadOnlyStatement);
        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.SELECT_BANK)
                .doesNotContain("status =", "JOIN ", "ORDER BY", "LIMIT ", "OFFSET ");
        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.SELECT_SHARED_USERS)
                .contains(
                        "SELECT DISTINCT bsr.user_id AS user_id,",
                        "bs.expires_at AS expires_at",
                        "JOIN bank_shares bs ON bsr.share_id = bs.id",
                        "bsr.status = 1",
                        "bs.is_active = TRUE")
                .doesNotContain("ORDER BY", "LIMIT ", "OFFSET ");
        assertThat(JdbcPersonalBankUsageStatsQueryAdapter.SELECT_PUBLIC_USER_IDS)
                .contains("SELECT DISTINCT user_id", "FROM public_bank_users")
                .doesNotContain("JOIN ", "ORDER BY", "LIMIT ", "OFFSET ");
    }

    @Test
    void everyRuntimeMethodBindsBankIdExplicitlyAsInteger() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toRealPath();
        Path source = basedir.resolve(
                "src/main/java/io/saksk/ti/personalbank/infrastructure/persistence/"
                        + "JdbcPersonalBankUsageStatsQueryAdapter.java");
        String java = Files.readString(source, StandardCharsets.UTF_8);

        assertThat(occurrences(java, ".param(\"bank_id\", bankId, Types.INTEGER)"))
                .isEqualTo(3);
        assertThat(java)
                .contains(
                        "Optional<BankAccess> findBank(int bankId)",
                        "List<SharedUserAccess> listSharedUsers(int bankId)",
                        "List<Object> listPublicUserIds(int bankId)")
                .doesNotContain(
                        ".param(\"bank_id\", bankId)",
                        "CompletableFuture",
                        "parallelStream",
                        "catch (DataAccessException",
                        "CREATE INDEX",
                        "ALTER TABLE");
    }

    private static void assertSingleReadOnlyStatement(String sql) {
        String upper = sql.toUpperCase(Locale.ROOT);
        assertThat(occurrences(upper, "SELECT ")).isOne();
        assertThat(occurrences(sql, ":bank_id")).isOne();
        assertThat(upper).doesNotContain(
                ";", "INSERT ", "UPDATE ", "DELETE ", "CREATE ",
                "ALTER ", "DROP ", "TRUNCATE ", "TEMP ");
    }

    private static int occurrences(String text, String token) {
        return text.split(Pattern.quote(token), -1).length - 1;
    }
}
