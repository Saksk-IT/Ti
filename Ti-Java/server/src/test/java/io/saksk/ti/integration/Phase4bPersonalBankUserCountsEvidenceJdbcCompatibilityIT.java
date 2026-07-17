package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;

import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUserCountsEvidenceSql;
import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUserCountsEvidenceSql.EvidenceQuery;
import io.saksk.ti.personalbank.infrastructure.persistence.PersonalBankUserCountsEvidenceSql.Source;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT {

    private static final int BANK_ID = 7_101;
    private static final long VIEWER_ID = 7_001L;
    private static final List<String> SNAPSHOT_TABLES = List.of(
            "user_question_banks",
            "bank_shares",
            "bank_share_records",
            "public_bank_users",
            "user_bank_questions",
            "user_bank_favorites",
            "user_bank_mistakes",
            "user_progress",
            "user_question_tag_items");

    @Container
    static final PostgreSQLContainer POSTGRES_18 = userCountsFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = userCountsFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void evidenceQueriesRemainCompatibleWithPostgres18() throws SQLException {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void evidenceQueriesRemainCompatibleWithPostgres16() throws SQLException {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer userCountsFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/062-personal-bank-share-list-schema.sql"),
                        "/docker-entrypoint-initdb.d/062-personal-bank-share-list-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/063-personal-bank-share-list-seed.sql"),
                        "/docker-entrypoint-initdb.d/063-personal-bank-share-list-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/064-personal-bank-all-shares-seed.sql"),
                        "/docker-entrypoint-initdb.d/064-personal-bank-all-shares-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/065-personal-bank-usage-stats-schema.sql"),
                        "/docker-entrypoint-initdb.d/065-personal-bank-usage-stats-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/066-personal-bank-usage-stats-seed.sql"),
                        "/docker-entrypoint-initdb.d/066-personal-bank-usage-stats-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/067-personal-bank-user-counts-schema.sql"),
                        "/docker-entrypoint-initdb.d/067-personal-bank-user-counts-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/068-personal-bank-user-counts-seed.sql"),
                        "/docker-entrypoint-initdb.d/068-personal-bank-user-counts-seed.sql");
    }

    private static void assertCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws SQLException {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        JdbcClient jdbc = JdbcClient.create(dataSource);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertParameterBindings(jdbc);

        DatabaseSnapshot before = databaseSnapshot(jdbc);
        assertAccessQueries(jdbc);
        assertStatisticsFamilies(jdbc);
        assertRawJdbcTypesAndNullability(jdbc);
        assertFixtureIndexShape(jdbc);
        assertThat(databaseSnapshot(jdbc)).isEqualTo(before);

        assertTransactionPoisoningAndRollbackRecovery(dataSource);
        assertThat(databaseSnapshot(jdbc)).isEqualTo(before);
    }

    private static void assertParameterBindings(JdbcClient jdbc) {
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:bank_id) AS text)")
                .param("bank_id", BANK_ID)
                .query(String.class)
                .single())
                .isEqualTo("integer");
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:uid) AS text)")
                .param("uid", VIEWER_ID)
                .query(String.class)
                .single())
                .isEqualTo("bigint");
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:user_id) AS text)")
                .param("user_id", VIEWER_ID)
                .query(String.class)
                .single())
                .isEqualTo("bigint");

        String manifestPrepareType = PersonalBankUserCountsEvidenceSql
                .queryFamilies(true, 0)
                .get(2)
                .parameters()
                .get("q_type_f");
        String jdbcClientObservedType = jdbc.sql("SELECT CAST(pg_typeof(:q_type_f) AS text)")
                .param("q_type_f", "single_choice")
                .query(String.class)
                .single();
        assertThat(manifestPrepareType).isEqualTo("text");
        assertThat(jdbcClientObservedType).isEqualTo("character varying");
        assertThat(jdbcClientObservedType).isNotEqualTo(manifestPrepareType);
        assertThat(jdbc.sql("SELECT CAST(pg_typeof(:tq_0) AS text)")
                .param("tq_0", 8_101)
                .query(String.class)
                .single())
                .isEqualTo("integer");
    }

    private static void assertAccessQueries(JdbcClient jdbc) {
        assertThat(bankRows(jdbc, 7_101))
                .singleElement()
                .isEqualTo(new BankRow(7_101, 7_001, false, 1));
        assertThat(bankRows(jdbc, 7_102))
                .singleElement()
                .isEqualTo(new BankRow(7_102, 7_001, false, 0));
        assertThat(bankRows(jdbc, 7_103))
                .singleElement()
                .isEqualTo(new BankRow(7_103, 7_001, false, null));
        assertThat(bankRows(jdbc, 79_999)).isEmpty();

        assertThat(shareRows(jdbc, 7_006L, 7_101)).containsExactlyInAnyOrder(
                new ShareAccessRow(7_505, 7_404, 7_101, 7_006, 1,
                        "read", false, null),
                new ShareAccessRow(7_509, 7_405, 7_101, 7_006, 1,
                        "read", true, null));
        assertThat(shareRows(jdbc, 7_008L, 7_101))
                .singleElement()
                .isEqualTo(new ShareAccessRow(
                        7_507, 7_300, 7_101, 7_008, 1, null, null, null));
        assertThat(shareRows(jdbc, 7_006L, 79_999)).isEmpty();
    }

    private static void assertStatisticsFamilies(JdbcClient jdbc) {
        StatisticsResult all = statistics(jdbc, Source.ALL, null, List.of());
        assertThat(all).isEqualTo(new StatisticsResult(
                9,
                4,
                4,
                Arrays.asList(
                        "",
                        "boolean",
                        "essay",
                        "fill",
                        "multi_choice",
                        "single_choice",
                        "unexpected_type",
                        null)));

        assertThat(statistics(jdbc, Source.FAVORITES, null, List.of()))
                .isEqualTo(new StatisticsResult(
                        4,
                        4,
                        4,
                        Arrays.asList("essay", "multi_choice", "single_choice", null)));
        assertThat(statistics(jdbc, Source.MISTAKES, null, List.of()))
                .isEqualTo(new StatisticsResult(
                        4,
                        4,
                        4,
                        Arrays.asList("boolean", "fill", "multi_choice", null)));

        assertThat(statistics(jdbc, Source.ALL, "single_choice", List.of()))
                .isEqualTo(new StatisticsResult(2, 1, 0, List.of("single_choice")));
        assertThat(statistics(jdbc, Source.ALL, null, List.of(8_101, 8_102, 8_201)))
                .isEqualTo(new StatisticsResult(
                        2, 2, 1, List.of("multi_choice", "single_choice")));
        assertThat(statistics(
                jdbc, Source.ALL, "single_choice", List.of(8_101, 8_102, 8_201)))
                .isEqualTo(new StatisticsResult(1, 1, 0, List.of("single_choice")));
        assertThat(statistics(jdbc, Source.ALL, null, List.of(89_999)))
                .isEqualTo(new StatisticsResult(0, 0, 0, List.of()));

        // These two rows intentionally have f.bank_id/m.bank_id attached to 7105.
        // The frozen joins only use question_id and uid, so both still count in 7101.
        assertThat(statistics(jdbc, Source.ALL, null, List.of(8_102)))
                .isEqualTo(new StatisticsResult(1, 1, 1, List.of("multi_choice")));
        assertThat(statistics(jdbc, Source.ALL, null, List.of(8_103)))
                .isEqualTo(new StatisticsResult(1, 0, 1, List.of("boolean")));
    }

    private static void assertRawJdbcTypesAndNullability(JdbcClient jdbc) {
        RawJdbcValue count = jdbc.sql("""
                        SELECT COUNT(*) AS cnt
                        FROM user_bank_questions
                        WHERE bank_id = :bank_id
                        """)
                .param("bank_id", BANK_ID)
                .query((resultSet, rowNumber) -> rawLong(resultSet, "cnt"))
                .single();
        assertThat(count).isEqualTo(new RawJdbcValue("int8", 9L, false));

        RawJdbcValue nullType = jdbc.sql("""
                        SELECT type AS p_type
                        FROM user_bank_questions
                        WHERE id = :question_id
                        """)
                .param("question_id", 8_108)
                .query((resultSet, rowNumber) -> rawString(resultSet, "p_type"))
                .single();
        assertThat(nullType).isEqualTo(new RawJdbcValue("text", null, true));

        RawJdbcValue blankType = jdbc.sql("""
                        SELECT type AS p_type
                        FROM user_bank_questions
                        WHERE id = :question_id
                        """)
                .param("question_id", 8_107)
                .query((resultSet, rowNumber) -> rawString(resultSet, "p_type"))
                .single();
        assertThat(blankType).isEqualTo(new RawJdbcValue("text", "", false));

        RawJdbcValue unknownType = jdbc.sql("""
                        SELECT type AS p_type
                        FROM user_bank_questions
                        WHERE id = :question_id
                        """)
                .param("question_id", 8_106)
                .query((resultSet, rowNumber) -> rawString(resultSet, "p_type"))
                .single();
        assertThat(unknownType)
                .isEqualTo(new RawJdbcValue("text", "unexpected_type", false));
    }

    private static void assertFixtureIndexShape(JdbcClient jdbc) {
        assertThat(indexDefinitions(jdbc, "user_bank_questions"))
                .hasSize(2)
                .anyMatch(definition -> definition.matches(
                        "(?is).*\\(\\s*bank_id\\s*\\).*"));
        assertThat(indexDefinitions(jdbc, "user_bank_favorites"))
                .hasSize(3)
                .anyMatch(definition -> definition.matches(
                        "(?is).*\\(\\s*user_id\\s*,\\s*bank_id\\s*\\).*"));
        assertThat(indexDefinitions(jdbc, "user_bank_mistakes"))
                .hasSize(3)
                .anyMatch(definition -> definition.matches(
                        "(?is).*\\(\\s*user_id\\s*,\\s*bank_id\\s*\\).*"));

        List<String> tagIndexes = indexDefinitions(jdbc, "user_question_tag_items");
        assertThat(tagIndexes).hasSize(1);
        assertThat(tagIndexes).noneMatch(definition -> definition.contains(
                "idx_uqti_user_scope_scopeid_tag"));
        assertThat(tagIndexes).noneMatch(definition -> definition.contains(
                "idx_uqti_user_scope_scopeid_qid"));
    }

    private static void assertTransactionPoisoningAndRollbackRecovery(DataSource dataSource)
            throws SQLException {
        try (Connection connection = dataSource.getConnection();
             Statement statement = connection.createStatement()) {
            connection.setAutoCommit(false);

            SQLException initialFailure = assertThrows(
                    SQLException.class,
                    () -> statement.executeQuery(
                            "SELECT missing_user_counts_column FROM user_bank_questions"));
            assertThat(initialFailure.getSQLState()).isEqualTo("42703");

            SQLException poisonedTransaction = assertThrows(
                    SQLException.class,
                    () -> statement.executeQuery(
                            "SELECT COUNT(*) FROM user_bank_questions"));
            assertThat(poisonedTransaction.getSQLState()).isEqualTo("25P02");

            connection.rollback();
            try (ResultSet resultSet = statement.executeQuery(
                    "SELECT COUNT(*) FROM user_bank_questions")) {
                assertThat(resultSet.next()).isTrue();
                assertThat(resultSet.getLong(1)).isEqualTo(10L);
            }
            connection.rollback();
        }
    }

    private static List<BankRow> bankRows(JdbcClient jdbc, int bankId) {
        return jdbc.sql(PersonalBankUserCountsEvidenceSql.accessBank().sql())
                .param("bank_id", bankId)
                .query(Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT::mapBank)
                .list();
    }

    private static List<ShareAccessRow> shareRows(JdbcClient jdbc, long userId, int bankId) {
        return jdbc.sql(PersonalBankUserCountsEvidenceSql.accessShare().sql())
                .param("user_id", userId)
                .param("bank_id", bankId)
                .query(Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT::mapShare)
                .list();
    }

    private static StatisticsResult statistics(
            JdbcClient jdbc,
            Source source,
            String qType,
            List<Integer> tagQuestionIds
    ) {
        List<EvidenceQuery> queries = PersonalBankUserCountsEvidenceSql.statisticsSequence(
                source, qType != null, tagQuestionIds.size());
        return new StatisticsResult(
                count(jdbc, queries.get(0), qType, tagQuestionIds),
                count(jdbc, queries.get(1), qType, tagQuestionIds),
                count(jdbc, queries.get(2), qType, tagQuestionIds),
                types(jdbc, queries.get(3), qType, tagQuestionIds));
    }

    private static long count(
            JdbcClient jdbc,
            EvidenceQuery query,
            String qType,
            List<Integer> tagQuestionIds
    ) {
        return bind(jdbc, query, qType, tagQuestionIds).query(Long.class).single();
    }

    private static List<String> types(
            JdbcClient jdbc,
            EvidenceQuery query,
            String qType,
            List<Integer> tagQuestionIds
    ) {
        return bind(jdbc, query, qType, tagQuestionIds)
                .query((resultSet, rowNumber) -> resultSet.getString("p_type"))
                .list();
    }

    private static JdbcClient.StatementSpec bind(
            JdbcClient jdbc,
            EvidenceQuery query,
            String qType,
            List<Integer> tagQuestionIds
    ) {
        JdbcClient.StatementSpec statement = jdbc.sql(query.sql());
        for (String parameter : query.parameterOrder()) {
            Object value = switch (parameter) {
                case "bank_id" -> BANK_ID;
                case "uid" -> VIEWER_ID;
                case "q_type_f" -> Objects.requireNonNull(qType, "qType");
                default -> tagValue(parameter, tagQuestionIds);
            };
            statement = statement.param(parameter, value);
        }
        return statement;
    }

    private static int tagValue(String parameter, List<Integer> tagQuestionIds) {
        if (!parameter.startsWith("tq_")) {
            throw new IllegalArgumentException("Unexpected evidence parameter: " + parameter);
        }
        int index = Integer.parseInt(parameter.substring("tq_".length()));
        return tagQuestionIds.get(index);
    }

    private static BankRow mapBank(ResultSet resultSet, int rowNumber) throws SQLException {
        return new BankRow(
                resultSet.getInt("id"),
                resultSet.getInt("user_id"),
                resultSet.getObject("is_public", Boolean.class),
                resultSet.getObject("status", Integer.class));
    }

    private static ShareAccessRow mapShare(ResultSet resultSet, int rowNumber)
            throws SQLException {
        return new ShareAccessRow(
                resultSet.getInt("id"),
                resultSet.getInt("share_id"),
                resultSet.getInt("bank_id"),
                resultSet.getInt("user_id"),
                resultSet.getObject("status", Integer.class),
                resultSet.getString("permission"),
                resultSet.getObject("is_active", Boolean.class),
                resultSet.getObject("expires_at", LocalDateTime.class));
    }

    private static RawJdbcValue rawLong(ResultSet resultSet, String column)
            throws SQLException {
        Long value = resultSet.getObject(column, Long.class);
        return new RawJdbcValue(
                resultSet.getMetaData().getColumnTypeName(resultSet.findColumn(column)),
                value,
                resultSet.wasNull());
    }

    private static RawJdbcValue rawString(ResultSet resultSet, String column)
            throws SQLException {
        String value = resultSet.getString(column);
        return new RawJdbcValue(
                resultSet.getMetaData().getColumnTypeName(resultSet.findColumn(column)),
                value,
                resultSet.wasNull());
    }

    private static DatabaseSnapshot databaseSnapshot(JdbcClient jdbc) {
        Map<String, Long> rows = new LinkedHashMap<>();
        Map<String, List<String>> indexes = new LinkedHashMap<>();
        for (String table : SNAPSHOT_TABLES) {
            rows.put(table, jdbc.sql("SELECT COUNT(*) FROM " + table)
                    .query(Long.class)
                    .single());
            indexes.put(table, indexDefinitions(jdbc, table));
        }
        return new DatabaseSnapshot(
                Collections.unmodifiableMap(rows),
                Collections.unmodifiableMap(indexes));
    }

    private static List<String> indexDefinitions(JdbcClient jdbc, String table) {
        return jdbc.sql("""
                        SELECT indexdef
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                          AND tablename = :table
                        ORDER BY indexname
                        """)
                .param("table", table)
                .query(String.class)
                .list();
    }

    private record BankRow(int id, int userId, Boolean publicBank, Integer status) {
    }

    private record ShareAccessRow(
            int id,
            int shareId,
            int bankId,
            int userId,
            Integer status,
            String permission,
            Boolean active,
            LocalDateTime expiresAt
    ) {
    }

    private record StatisticsResult(
            long total,
            long favorites,
            long mistakes,
            List<String> types
    ) {
    }

    private record RawJdbcValue(String jdbcType, Object value, boolean nullValue) {
    }

    private record DatabaseSnapshot(
            Map<String, Long> rows,
            Map<String, List<String>> indexes
    ) {
    }
}
