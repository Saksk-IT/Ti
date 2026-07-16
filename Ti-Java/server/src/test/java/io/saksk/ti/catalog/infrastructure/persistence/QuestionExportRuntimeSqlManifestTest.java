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

/** Emits the two exact SQL variants consumed by the external question-export plan gate. */
class QuestionExportRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementsForTheQuestionExportPlanGate() throws Exception {
        List<Map<String, Object>> queries = List.of(
                query(
                        "question-export-all",
                        JdbcQuestionExportQueryAdapter.SELECT_ALL_QUESTION_EXPORT_RECORDS,
                        Map.of()),
                query(
                        "question-export-by-subject",
                        JdbcQuestionExportQueryAdapter.SELECT_QUESTION_EXPORT_RECORDS_BY_SUBJECT,
                        Map.of("subject_id", "integer")));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4a.question-export-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcQuestionExportQueryAdapter.class.getName());
        manifest.put("query_count", queries.size());
        manifest.put("queries", queries);

        String json = new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
    }

    private static Map<String, Object> query(
            String queryId,
            String sql,
            Map<String, String> parameters
    ) {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("query_id", queryId);
        query.put("operation", "question-export-snapshot");
        query.put("sql", sql);
        query.put("parameters", parameters);
        return query;
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty("ti.question-export.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4a-question-export-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Question-export runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
