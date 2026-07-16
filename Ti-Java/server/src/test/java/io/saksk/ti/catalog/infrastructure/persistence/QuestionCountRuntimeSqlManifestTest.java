package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionSubjectAssignmentScope;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.LongStream;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

/** Emits every exact runtime SQL variant needed by the question-count plan gate. */
class QuestionCountRuntimeSqlManifestTest {

    @Test
    void exportsExactRuntimeStatementsWithCompactDeterministicArrayParameters() throws Exception {
        List<Integer> excludedSubjectIds = List.of(2, 4);
        List<Long> largeCandidateIds = LongStream.rangeClosed(1, 100_000).boxed().toList();

        Map<String, Object> restrictedParameters = new LinkedHashMap<>();
        restrictedParameters.put(
                "excluded_subject_ids",
                arrayParameter("integer", excludedSubjectIds, 2, 4, 2));

        Map<String, Object> subjectTypeParameters = new LinkedHashMap<>();
        subjectTypeParameters.put("subject_name", "数学");
        subjectTypeParameters.put("question_type", "single_choice");

        Map<String, Object> candidateParameters = new LinkedHashMap<>();
        Map<String, Object> largeCandidateParameter =
                arrayParameter("bigint", largeCandidateIds, 1, 100_000, 1);
        candidateParameters.put("candidate_question_ids", largeCandidateParameter);

        List<Map<String, Object>> queries = List.of(
                queryEntry(
                        "question-count-anonymous-all",
                        query(QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED)),
                queryEntry(
                        "question-count-auth-unrestricted",
                        query(QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT)),
                queryEntry(
                        "question-count-auth-restricted",
                        new QuestionCatalogCountQuery(
                                Optional.empty(),
                                Optional.empty(),
                                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                                Set.copyOf(excludedSubjectIds),
                                Optional.empty()),
                        restrictedParameters),
                queryEntry(
                        "question-count-subject-type",
                        new QuestionCatalogCountQuery(
                                Optional.of("数学"),
                                Optional.of("single_choice"),
                                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                                Set.of(),
                                Optional.empty()),
                        subjectTypeParameters),
                queryEntry(
                        "question-count-candidate-large",
                        new QuestionCatalogCountQuery(
                                Optional.empty(),
                                Optional.empty(),
                                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                                Set.of(),
                                Optional.of(largeCandidateIds)),
                        candidateParameters));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4a.question-count-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcQuestionCountQueryAdapter.class.getName());
        manifest.put("query_count", queries.size());
        manifest.put("queries", queries);

        String json = new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
        assertThat(json)
                .contains(
                        "\"manifest_id\" : \"ti.phase4a.question-count-runtime-sql\"",
                        "\"query_count\" : 5",
                        "\"element_count\" : 100000",
                        "\"postgres_type\" : \"bigint[]\"",
                        "\"canonical_encoding\" : \"utf8-decimal-lines-with-final-newline\"")
                .doesNotContain("99999, 100000", "\"values\"");
        assertThat(largeCandidateParameter)
                .containsEntry("first", 1L)
                .containsEntry("last", 100_000L)
                .containsEntry("min", 1L)
                .containsEntry("max", 100_000L)
                .containsEntry("element_count", 100_000L);
    }

    private static QuestionCatalogCountQuery query(QuestionSubjectAssignmentScope scope) {
        return new QuestionCatalogCountQuery(
                Optional.empty(),
                Optional.empty(),
                scope,
                Set.of(),
                Optional.empty());
    }

    private static Map<String, Object> queryEntry(
            String queryId,
            QuestionCatalogCountQuery query
    ) {
        return queryEntry(queryId, query, Map.of());
    }

    private static Map<String, Object> queryEntry(
            String queryId,
            QuestionCatalogCountQuery query,
            Map<String, Object> parameters
    ) {
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("query_id", queryId);
        entry.put("operation", "question-count");
        entry.put("sql", JdbcQuestionCountQueryAdapter.sqlFor(query));
        entry.put("parameters", parameters);
        return entry;
    }

    private static Map<String, Object> arrayParameter(
            String elementType,
            List<? extends Number> values,
            long rangeStart,
            long rangeEnd,
            long rangeStep
    ) throws Exception {
        Map<String, Object> generator = new LinkedHashMap<>();
        generator.put("kind", "inclusive-integer-range");
        generator.put("start", rangeStart);
        generator.put("end", rangeEnd);
        generator.put("step", rangeStep);

        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("bind_kind", "jdbc-sql-array");
        metadata.put("postgres_type", elementType + "[]");
        metadata.put("element_type", elementType);
        metadata.put("element_count", (long) values.size());
        metadata.put("canonical_encoding", "utf8-decimal-lines-with-final-newline");
        metadata.put("sha256", digestDecimalLines(values));
        metadata.put("first", values.getFirst().longValue());
        metadata.put("last", values.getLast().longValue());
        metadata.put("min", values.stream().mapToLong(Number::longValue).min().orElseThrow());
        metadata.put("max", values.stream().mapToLong(Number::longValue).max().orElseThrow());
        metadata.put("value_generator", generator);
        return metadata;
    }

    private static String digestDecimalLines(List<? extends Number> values) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        for (Number value : values) {
            digest.update(value.toString().getBytes(StandardCharsets.UTF_8));
            digest.update((byte) '\n');
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty("ti.question-count.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4a-question-count-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException(
                    "Question-count runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
