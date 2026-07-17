package io.saksk.ti.personalbank.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

/** Emits the three exact sequential runtime statements for the usage-stats plan gate. */
class PersonalBankUsageStatsRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementsInExecutionOrder() throws Exception {
        Map<String, Object> bank = query(
                "personal-bank-usage-stats-bank-probe",
                1,
                "bank-probe",
                JdbcPersonalBankUsageStatsQueryAdapter.SELECT_BANK);
        Map<String, Object> shared = query(
                "personal-bank-usage-stats-shared-users",
                2,
                "shared-users",
                JdbcPersonalBankUsageStatsQueryAdapter.SELECT_SHARED_USERS);
        Map<String, Object> publicUsers = query(
                "personal-bank-usage-stats-public-users",
                3,
                "public-users",
                JdbcPersonalBankUsageStatsQueryAdapter.SELECT_PUBLIC_USER_IDS);

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4b.personal-bank-usage-stats-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcPersonalBankUsageStatsQueryAdapter.class.getName());
        manifest.put("sequential_execution", true);
        manifest.put("query_count", 3);
        manifest.put("queries", List.of(bank, shared, publicUsers));

        String json = new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
    }

    private static Map<String, Object> query(
            String queryId,
            int ordinal,
            String operation,
            String sql
    ) {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("query_id", queryId);
        query.put("ordinal", ordinal);
        query.put("operation", operation);
        query.put("sql", sql);
        query.put("parameters", Map.of("bank_id", "integer"));
        return query;
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty(
                "ti.personal-bank-usage-stats.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4b-personal-bank-usage-stats-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Personal-bank usage-stats runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
