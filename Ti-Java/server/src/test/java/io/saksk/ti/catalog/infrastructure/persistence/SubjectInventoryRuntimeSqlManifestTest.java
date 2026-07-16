package io.saksk.ti.catalog.infrastructure.persistence;

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

/** Emits the exact parameter-free SQL consumed by the subject-inventory plan gate. */
class SubjectInventoryRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementForTheSubjectInventoryPlanGate() throws Exception {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("query_id", "subject-inventory-summaries");
        query.put("operation", "subject-inventory");
        query.put("sql", JdbcSubjectInventoryQueryAdapter.SELECT_SUBJECT_INVENTORY_SUMMARIES);
        query.put("parameters", Map.of());

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4a.subject-inventory-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcSubjectInventoryQueryAdapter.class.getName());
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
        String configured = System.getProperty("ti.subject-inventory.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4a-subject-inventory-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Subject-inventory runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
