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

/** Emits the four exact SQL variants consumed by the external question-list plan gate. */
class QuestionListRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementsForTheQuestionListPlanGate() throws Exception {
        List<Map<String, Object>> queries = List.of(
                query(
                        "question-summaries-all",
                        JdbcQuestionSummaryQueryAdapter.SELECT_ALL_QUESTION_SUMMARIES,
                        Map.of()),
                query(
                        "question-summaries-by-subject",
                        JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_SUBJECT,
                        Map.of("subject_id", "integer")),
                query(
                        "question-summaries-by-type",
                        JdbcQuestionSummaryQueryAdapter.SELECT_QUESTION_SUMMARIES_BY_TYPE,
                        Map.of("question_type", "text")),
                query(
                        "question-summaries-by-subject-and-type",
                        JdbcQuestionSummaryQueryAdapter
                                .SELECT_QUESTION_SUMMARIES_BY_SUBJECT_AND_TYPE,
                        orderedParameters()));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4a.question-list-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcQuestionSummaryQueryAdapter.class.getName());
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
        query.put("operation", "question-list");
        query.put("sql", sql);
        query.put("parameters", parameters);
        return query;
    }

    private static Map<String, String> orderedParameters() {
        Map<String, String> parameters = new LinkedHashMap<>();
        parameters.put("subject_id", "integer");
        parameters.put("question_type", "text");
        return parameters;
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty("ti.question-list.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4a-question-list-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Question-list runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
