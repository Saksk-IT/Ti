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

/** Emits the two exact sequential runtime statements for the share-list plan gate. */
class PersonalBankShareRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementsInExecutionOrder() throws Exception {
        Map<String, Object> probe = new LinkedHashMap<>();
        probe.put("query_id", "personal-bank-share-owner-status-probe");
        probe.put("ordinal", 1);
        probe.put("sql", JdbcPersonalBankShareQueryAdapter.SELECT_OWNER_ACTIVE_BANK);
        probe.put("parameters", Map.of("bank_id", "integer", "viewer_id", "bigint"));

        Map<String, Object> shares = new LinkedHashMap<>();
        shares.put("query_id", "personal-bank-share-list");
        shares.put("ordinal", 2);
        shares.put("sql", JdbcPersonalBankShareQueryAdapter.SELECT_PERSONAL_BANK_SHARES);
        shares.put("parameters", Map.of("bank_id", "integer"));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4b.personal-bank-share-list-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcPersonalBankShareQueryAdapter.class.getName());
        manifest.put("sequential_execution", true);
        manifest.put("query_count", 2);
        manifest.put("queries", List.of(probe, shares));

        String json = new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty("ti.personal-bank-share.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4b-personal-bank-share-list-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Personal-bank share runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
