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

/** Emits test-only preimplementation SQL for the external dual-PostgreSQL plan gate. */
class PersonalBankUsageStatsEvidenceSqlManifestTest {

    @Test
    void exportsTheThreeSequentialHttpNeutralPreimplementationStatements() throws Exception {
        List<Map<String, Object>> queries = List.of(
                query(1, "personal-bank-usage-stats-bank-probe", "bank-probe",
                        PersonalBankUsageStatsEvidenceSql.BANK_PROBE),
                query(2, "personal-bank-usage-stats-shared-users", "shared-users",
                        PersonalBankUsageStatsEvidenceSql.SHARED_USERS),
                query(3, "personal-bank-usage-stats-public-users", "public-users",
                        PersonalBankUsageStatsEvidenceSql.PUBLIC_USERS));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4b.personal-bank-usage-stats-preimplementation-sql");
        manifest.put("schema_version", 1);
        manifest.put("source_class", PersonalBankUsageStatsEvidenceSql.class.getName());
        manifest.put("scope", "test-only-preimplementation-evidence");
        manifest.put("sequential_execution_required", true);
        manifest.put("short_circuit_after_bank_probe", true);
        manifest.put("shared_and_public_failure_boundaries", "independently_degrade_to_empty");
        manifest.put("query_count", 3);
        manifest.put("queries", queries);

        String json = new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
    }

    private static Map<String, Object> query(
            int ordinal,
            String queryId,
            String operation,
            String sql
    ) {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("ordinal", ordinal);
        query.put("query_id", queryId);
        query.put("operation", operation);
        query.put("sql", sql);
        query.put("parameter_order", List.of("bank_id"));
        Map<String, String> parameters = new LinkedHashMap<>();
        parameters.put("bank_id", "integer");
        query.put("parameters", parameters);
        return query;
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty(
                "ti.personal-bank-usage-stats-evidence.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4b-personal-bank-usage-stats-evidence-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Personal-bank usage-stats evidence SQL manifest must stay under server/target");
        }
        return output;
    }
}
