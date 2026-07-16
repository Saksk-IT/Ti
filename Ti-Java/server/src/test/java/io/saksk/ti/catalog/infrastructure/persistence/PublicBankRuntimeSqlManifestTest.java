package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSource;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalLong;
import java.util.TreeMap;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.ObjectMapper;

/** Emits the exact SQL strings and bound values used by the runtime JDBC adapter. */
class PublicBankRuntimeSqlManifestTest {

    private static final long VIEWER_IDENTITY_ID = 700_001;
    private static final long DETAIL_SOURCE_ID = 15_839;
    private static final Instant CUTOFF = Instant.parse("2026-07-09T04:00:00Z");

    @Test
    void exportsExactRuntimeStatementsForTheLargeFixturePlanGate() throws Exception {
        List<Map<String, Object>> queries = new ArrayList<>();

        PublicBankFilter all = PublicBankFilter.all();
        PublicBankFilter keyword = new PublicBankFilter(
                Optional.empty(), "needle", Optional.empty());
        PublicBankSearchQuery allLatest = new PublicBankSearchQuery(
                all, PublicBankSort.LATEST, 5, 25);
        PublicBankSearchQuery keywordLatest = new PublicBankSearchQuery(
                keyword, PublicBankSort.LATEST, 5, 25);
        JdbcPublicBankSnapshotQueryAdapter.SearchStatements allSearch =
                JdbcPublicBankSnapshotQueryAdapter.searchStatements(
                        allLatest, OptionalLong.of(VIEWER_IDENTITY_ID));
        JdbcPublicBankSnapshotQueryAdapter.SearchStatements keywordSearch =
                JdbcPublicBankSnapshotQueryAdapter.searchStatements(
                        keywordLatest, OptionalLong.of(VIEWER_IDENTITY_ID));

        queries.add(query("search-count-keyword", "search-count", keywordSearch.total()));
        queries.add(query("search-page-latest", "search-page", allSearch.page()));
        queries.add(query(
                "search-page-latest-keyword", "search-page", keywordSearch.page()));
        queries.add(query(
                "boards-directory",
                "boards",
                JdbcPublicBankSnapshotQueryAdapter.boardsStatement(all)));
        queries.add(query(
                "hot-top-five",
                "hot",
                JdbcPublicBankSnapshotQueryAdapter.hotStatement(
                        new PublicBankHotQuery(all, 5))));
        queries.add(query(
                "summary-rolling-seven-days",
                "summary",
                JdbcPublicBankSnapshotQueryAdapter.summaryStatement(all, CUTOFF)));
        queries.add(query(
                "detail-with-both-relation",
                "detail",
                JdbcPublicBankSnapshotQueryAdapter.detailStatement(
                        new PublicBankRef(PublicBankSource.USER_PUBLIC, DETAIL_SOURCE_ID),
                        OptionalLong.of(VIEWER_IDENTITY_ID))));

        Map<String, Object> manifest = new LinkedHashMap<>();
        manifest.put("manifest_id", "ti.phase4a.public-bank-runtime-sql");
        manifest.put("schema_version", 1);
        manifest.put("adapter_class", JdbcPublicBankSnapshotQueryAdapter.class.getName());
        manifest.put("query_count", queries.size());
        manifest.put("queries", queries);

        String json = new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValueAsString(manifest) + "\n";
        Path output = outputPath();
        Files.createDirectories(output.getParent());
        Files.writeString(output, json, StandardCharsets.UTF_8);

        assertThat(queries).hasSize(7);
        assertThat(queries.stream().map(item -> item.get("query_id")))
                .doesNotHaveDuplicates();
        assertThat(Files.readString(output, StandardCharsets.UTF_8)).isEqualTo(json);
    }

    private static Map<String, Object> query(
            String queryId,
            String operation,
            JdbcPublicBankSnapshotQueryAdapter.SqlStatement statement
    ) {
        Map<String, Object> query = new LinkedHashMap<>();
        query.put("query_id", queryId);
        query.put("operation", operation);
        query.put("sql", statement.sql());
        Map<String, Object> parameters = new TreeMap<>();
        statement.parameters().forEach((name, value) ->
                parameters.put(name, parameter(value)));
        query.put("parameters", parameters);
        return query;
    }

    private static Map<String, Object> parameter(Object value) {
        Objects.requireNonNull(value, "runtime SQL parameter");
        Map<String, Object> parameter = new LinkedHashMap<>();
        switch (value) {
            case Boolean bool -> {
                parameter.put("jdbc_type", "boolean");
                parameter.put("value", bool);
            }
            case Integer integer -> {
                parameter.put("jdbc_type", "integer");
                parameter.put("value", integer);
            }
            case Long bigint -> {
                parameter.put("jdbc_type", "bigint");
                parameter.put("value", bigint.toString());
            }
            case String text -> {
                parameter.put("jdbc_type", "text");
                parameter.put("value", text);
            }
            case LocalDateTime timestamp -> {
                parameter.put("jdbc_type", "timestamp");
                parameter.put("value", timestamp.toString());
            }
            case OffsetDateTime timestamp -> {
                parameter.put("jdbc_type", "timestamptz");
                parameter.put("value", timestamp.toString());
            }
            default -> throw new IllegalArgumentException(
                    "Unsupported runtime SQL parameter type: " + value.getClass().getName());
        }
        return parameter;
    }

    private static Path outputPath() {
        Path basedir = Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .toAbsolutePath()
                .normalize();
        Path target = basedir.resolve("target").normalize();
        String configured = System.getProperty("ti.public-bank.sql-manifest-output");
        Path output = configured == null || configured.isBlank()
                ? target.resolve("phase4a-public-bank-runtime-sql.json")
                : Path.of(configured).toAbsolutePath().normalize();
        if (!output.startsWith(target) || output.equals(target)) {
            throw new IllegalArgumentException("Runtime SQL manifest must stay under server/target");
        }
        return output;
    }
}
