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
class PersonalBankAllSharesEvidenceSqlManifestTest {

    @Test
    void exportsTheSingleHttpNeutralPreimplementationStatement() throws Exception {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("ordinal", 1);
        query.put("query_id", "personal-bank-all-shares");
        query.put("operation", "all-shares");
        query.put("sql", PersonalBankAllSharesEvidenceSql.ALL_SHARES);
        query.put("parameter_order", List.of("viewer_id"));
        Map<String, String> parameters = new LinkedHashMap<>();
        parameters.put("viewer_id", "bigint");
        query.put("parameters", parameters);
        assertThat(parameters).containsExactly(Map.entry("viewer_id", "bigint"));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4b.personal-bank-all-shares-preimplementation-sql");
        manifest.put("schema_version", 1);
        manifest.put("source_class", PersonalBankAllSharesEvidenceSql.class.getName());
        manifest.put("scope", "test-only-preimplementation-evidence");
        manifest.put("sequential_execution_required", false);
        manifest.put("join_authorized", true);
        manifest.put("http_derived_fields_excluded", List.of("share_link"));
        manifest.put("query_count", 1);
        manifest.put("queries", List.of(query));

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
                "ti.personal-bank-all-shares-evidence.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4b-personal-bank-all-shares-evidence-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Personal-bank all-shares evidence SQL manifest must stay under server/target");
        }
        return output;
    }
}
