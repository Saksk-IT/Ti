package io.saksk.ti.architecture;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;

import static org.assertj.core.api.Assertions.assertThat;

/** Static fail-closed checks for the dormant Phase 4C receipt migration. */
class Phase4cTransactionWriteMigrationStaticTest {

    @Test
    void migrationOwnsOnlyTheTwoAuthorizedReceiptTables() throws Exception {
        String migration = Files.readString(serverRoot().resolve(
                "src/main/resources/db/migration/"
                        + "V001__phase4c_transaction_write_idempotency.sql"));

        assertThat(migration).contains(
                "CREATE TABLE learning_idempotency_receipts",
                "CREATE TABLE catalog_question_edit_commands",
                "PRIMARY KEY (actor_id, operation, key_hmac)",
                "PRIMARY KEY (actor_id, key_hmac)",
                "CHECK (octet_length(key_hmac) = 32)",
                "CHECK (octet_length(request_sha256) = 32)");
        assertThat(migration).doesNotContain(
                "CREATE TABLE questions",
                "CREATE TABLE favorites",
                "ALTER TABLE questions",
                "ALTER TABLE favorites",
                "DROP TABLE",
                "IF NOT EXISTS");
        assertThat(count(migration, "CREATE TABLE ")).isEqualTo(2);
        assertThat(count(migration, "CREATE INDEX ")).isEqualTo(2);
    }

    @Test
    void flywayIsFailClosedByDefaultAndRequiresExplicitOperatorEnablement()
            throws Exception {
        String application = Files.readString(
                serverRoot().resolve("src/main/resources/application.yml"));

        assertThat(application).contains(
                "enabled: ${TI_FLYWAY_ENABLED:false}",
                "baseline-on-migrate: true",
                "baseline-version: \"0\"",
                "locations: classpath:db/migration",
                "validate-migration-naming: true");
    }

    private static int count(String value, String needle) {
        int result = 0;
        int offset = 0;
        while ((offset = value.indexOf(needle, offset)) >= 0) {
            result++;
            offset += needle.length();
        }
        return result;
    }

    private static Path serverRoot() {
        return Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
    }
}
