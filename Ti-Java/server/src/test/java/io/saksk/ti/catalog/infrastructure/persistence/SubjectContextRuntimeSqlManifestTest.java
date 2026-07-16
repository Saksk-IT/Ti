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

/** Emits the exact SQL consumed by the external PostgreSQL subject-context plan gate. */
class SubjectContextRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementForTheSubjectContextPlanGate() throws Exception {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("query_id", "subject-context-by-id");
        query.put("operation", "subject-context");
        query.put("sql", JdbcSubjectDetailQueryAdapter.SELECT_SUBJECT_BY_ID);
        query.put("parameters", Map.of("subject_id", "bigint"));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4a.subject-context-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcSubjectDetailQueryAdapter.class.getName());
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
        String configured = System.getProperty("ti.subject-context.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4a-subject-context-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Subject-context runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
