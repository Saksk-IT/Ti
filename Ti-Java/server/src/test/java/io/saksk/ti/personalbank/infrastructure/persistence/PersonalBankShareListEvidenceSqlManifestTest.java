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
class PersonalBankShareListEvidenceSqlManifestTest {

    @Test
    void exportsTheTwoOrderedPreimplementationStatements() throws Exception {
        Map<String, Object> probe = new LinkedHashMap<>();
        probe.put("ordinal", 1);
        probe.put("query_id", "personal-bank-share-owner-status-probe");
        probe.put("operation", "owner-status-probe");
        probe.put("sql", PersonalBankShareListEvidenceSql.OWNER_STATUS_PROBE);
        probe.put("parameter_order", List.of("bank_id", "viewer_id"));
        Map<String, String> probeParameters = new LinkedHashMap<>();
        probeParameters.put("bank_id", "integer");
        probeParameters.put("viewer_id", "bigint");
        probe.put("parameters", probeParameters);
        assertThat(probeParameters).containsExactly(
                Map.entry("bank_id", "integer"),
                Map.entry("viewer_id", "bigint"));

        Map<String, Object> shares = new LinkedHashMap<>();
        shares.put("ordinal", 2);
        shares.put("query_id", "personal-bank-share-list");
        shares.put("operation", "share-list");
        shares.put("sql", PersonalBankShareListEvidenceSql.SHARE_LIST);
        shares.put("parameter_order", List.of("bank_id"));
        Map<String, String> shareParameters = new LinkedHashMap<>();
        shareParameters.put("bank_id", "integer");
        shares.put("parameters", shareParameters);
        assertThat(shareParameters).containsExactly(Map.entry("bank_id", "integer"));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4b.personal-bank-share-list-preimplementation-sql");
        manifest.put("schema_version", 1);
        manifest.put("source_class", PersonalBankShareListEvidenceSql.class.getName());
        manifest.put("scope", "test-only-preimplementation-evidence");
        manifest.put("sequential_execution_required", true);
        manifest.put("join_authorized", false);
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
        String configured = System.getProperty(
                "ti.personal-bank-share-list-evidence.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4b-personal-bank-share-list-evidence-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Personal-bank share-list evidence SQL manifest must stay under server/target");
        }
        return output;
    }
}
