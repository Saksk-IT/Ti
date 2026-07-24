package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditIdempotencyKey;
import io.saksk.ti.catalog.api.QuestionEditResult;
import io.saksk.ti.catalog.api.QuestionEditorIdentity;
import io.saksk.ti.catalog.application.QuestionEditWriteTransactionTestAccess;
import io.saksk.ti.catalog.application.port.CatalogQuestionEditReceiptPort;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcCatalogQuestionEditReceiptAdapterTestAccess;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcQuestionEditStateAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
class Phase4cQuestionEditWriteTransactionIT {

    private static final String RECEIPT_SECRET =
            "phase4c-question-edit-receipt-secret-001";
    private static final Clock RECEIPT_CLOCK = Clock.fixed(
            Instant.parse("2026-07-24T07:00:00Z"),
            ZoneOffset.UTC);

    @Container
    static final PostgreSQLContainer POSTGRES_18 =
            Phase2PostgresContainers.reference18();

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

    @Test
    void questionEditAndReceiptAreAtomicOnPostgres18() throws Exception {
        assertQuestionEditTransactions(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void questionEditAndReceiptAreAtomicOnPostgres16() throws Exception {
        assertQuestionEditTransactions(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertQuestionEditTransactions(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(),
                postgres.getUsername(),
                postgres.getPassword());
        Flyway.configure()
                .dataSource(dataSource)
                .locations("classpath:db/migration")
                .baselineOnMigrate(true)
                .baselineVersion("0")
                .validateMigrationNaming(true)
                .load()
                .migrate();

        JdbcClient jdbc = JdbcClient.create(dataSource);
        TransactionTemplate transactions =
                new TransactionTemplate(new DataSourceTransactionManager(dataSource));
        QuestionEditStatePort state =
                JdbcQuestionEditStateAdapterTestAccess.create(jdbc);
        CatalogQuestionEditReceiptPort receipts =
                JdbcCatalogQuestionEditReceiptAdapterTestAccess.create(
                        jdbc,
                        RECEIPT_SECRET,
                        Duration.ofHours(48),
                        RECEIPT_CLOCK);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        createLegacyFixture(jdbc);
        truncate(jdbc);

        assertPersistentEditReplayAndConflict(jdbc, transactions, state, receipts);
        assertRollbackReleasesQuestionAndReceipt(jdbc, transactions, state, receipts);
        assertValidationAndMissingOutcomesAreDurable(
                jdbc, transactions, state, receipts);
        assertConcurrentSameKeyMutatesOnce(jdbc, transactions, state, receipts);
        assertNoHeaderRequestsRemainIndependent(jdbc, transactions, state, receipts);
        assertThatThrownBy(() -> state.findForUpdate(93001))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("writable transaction");
    }

    private static void assertPersistentEditReplayAndConflict(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts
    ) {
        insertQuestion(jdbc, 93001, "原始题干", "single_choice");
        QuestionEditCommand command = choiceCommand(
                91,
                93001,
                QuestionEditIdempotencyKey.of("question-edit-replay-key"),
                "更新后的题干",
                "A");

        QuestionEditResult first = execute(
                transactions, state, receipts, command, digest(1));
        QuestionEditResult replay = execute(
                transactions, state, receipts, command, digest(1));
        QuestionEditResult conflict = execute(
                transactions, state, receipts, command, digest(2));

        assertThat(first.outcome()).isEqualTo(QuestionEditResult.Outcome.SUCCESS);
        assertThat(first.replayed()).isFalse();
        assertThat(first.data().orElseThrow().content()).isEqualTo("更新后的题干");
        assertThat(first.data().orElseThrow().questionType()).isEqualTo("选择题");
        assertThat(first.data().orElseThrow().answer()).isEqualTo("A");
        assertThat(first.data().orElseThrow().subject()).isEqualTo("高等数学");
        assertThat(replay).isEqualTo(QuestionEditResult.success(
                first.data().orElseThrow(),
                true));
        assertThat(conflict.outcome())
                .isEqualTo(QuestionEditResult.Outcome.IDEMPOTENCY_CONFLICT);
        assertQuestionColumns(
                jdbc,
                93001,
                "single_choice",
                "更新后的题干",
                "[\"甲\", \"乙\"]",
                "[0]",
                "更新后的解析",
                "[\"标签一\", \"标签二\"]",
                3);
        assertThat(receiptRows(jdbc, 91, 93001)).isEqualTo(1);
    }

    private static void assertRollbackReleasesQuestionAndReceipt(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts
    ) {
        insertQuestion(jdbc, 93002, "回滚前", "single_choice");
        QuestionEditCommand command = choiceCommand(
                92,
                93002,
                QuestionEditIdempotencyKey.of("question-edit-rollback-key"),
                "不得提交",
                "B");

        assertThatThrownBy(() -> transactions.executeWithoutResult(status -> {
            QuestionEditWriteTransactionTestAccess.execute(
                    state,
                    receipts,
                    command,
                    digest(3));
            throw new IllegalStateException("force rollback");
        })).isInstanceOf(IllegalStateException.class)
                .hasMessage("force rollback");
        assertThat(questionContent(jdbc, 93002)).isEqualTo("回滚前");
        assertThat(receiptRows(jdbc, 92, 93002)).isZero();

        QuestionEditResult retry = execute(
                transactions, state, receipts, command, digest(3));
        assertThat(retry.outcome()).isEqualTo(QuestionEditResult.Outcome.SUCCESS);
        assertThat(questionContent(jdbc, 93002)).isEqualTo("不得提交");
        assertThat(receiptRows(jdbc, 92, 93002)).isEqualTo(1);
    }

    private static void assertValidationAndMissingOutcomesAreDurable(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts
    ) {
        insertQuestion(jdbc, 93003, "多选原题", "multi_choice");
        QuestionEditCommand invalid = new QuestionEditCommand(
                new QuestionEditorIdentity(93, false, true),
                93003,
                Optional.of("不应更新"),
                Optional.of("多选题"),
                Optional.of("AC"),
                Optional.of("不应更新"),
                Optional.of("[\"A. 甲\",\"B. 乙\"]"),
                QuestionEditIdempotencyKey.of("question-edit-invalid-key"));

        QuestionEditResult invalidFirst = execute(
                transactions, state, receipts, invalid, digest(4));
        QuestionEditResult invalidReplay = execute(
                transactions, state, receipts, invalid, digest(4));
        assertThat(invalidFirst.outcome())
                .isEqualTo(QuestionEditResult.Outcome.INVALID_MULTI_CHOICE_ANSWER);
        assertThat(invalidFirst.detail()).contains(
                "多选题答案中包含无效选项：C。有效选项为：A, B");
        assertThat(invalidReplay.replayed()).isTrue();
        assertThat(questionContent(jdbc, 93003)).isEqualTo("多选原题");
        assertThat(receiptStatus(jdbc, 93, 93003)).isEqualTo(400);

        QuestionEditCommand missing = choiceCommand(
                94,
                93999,
                QuestionEditIdempotencyKey.of("question-edit-missing-key"),
                "不存在",
                "A");
        QuestionEditResult missingFirst = execute(
                transactions, state, receipts, missing, digest(5));
        QuestionEditResult missingReplay = execute(
                transactions, state, receipts, missing, digest(5));
        assertThat(missingFirst.outcome())
                .isEqualTo(QuestionEditResult.Outcome.QUESTION_NOT_FOUND);
        assertThat(missingReplay.replayed()).isTrue();
        assertThat(receiptStatus(jdbc, 94, 93999)).isEqualTo(404);
    }

    private static void assertConcurrentSameKeyMutatesOnce(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts
    ) throws Exception {
        insertQuestion(jdbc, 93004, "并发前", "single_choice");
        QuestionEditCommand command = choiceCommand(
                95,
                93004,
                QuestionEditIdempotencyKey.of("question-edit-concurrent-key"),
                "并发后",
                "B");

        List<QuestionEditResult> results = concurrently(2, () -> execute(
                transactions, state, receipts, command, digest(6)));
        assertThat(results).allMatch(
                result -> result.outcome() == QuestionEditResult.Outcome.SUCCESS);
        assertThat(results.stream().filter(QuestionEditResult::replayed).count())
                .isEqualTo(1);
        assertThat(questionContent(jdbc, 93004)).isEqualTo("并发后");
        assertThat(receiptRows(jdbc, 95, 93004)).isEqualTo(1);
    }

    private static void assertNoHeaderRequestsRemainIndependent(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts
    ) throws Exception {
        insertQuestion(jdbc, 93005, "无键前", "single_choice");
        QuestionEditCommand first = choiceCommand(
                96,
                93005,
                QuestionEditIdempotencyKey.absent(),
                "无键甲",
                "A");
        QuestionEditCommand second = choiceCommand(
                96,
                93005,
                QuestionEditIdempotencyKey.absent(),
                "无键乙",
                "B");

        List<QuestionEditResult> results = concurrently(
                List.of(
                        () -> execute(transactions, state, receipts, first, digest(7)),
                        () -> execute(transactions, state, receipts, second, digest(8))));
        assertThat(results).allMatch(
                result -> result.outcome() == QuestionEditResult.Outcome.SUCCESS);
        assertThat(results).allMatch(result -> !result.replayed());
        assertThat(questionContent(jdbc, 93005)).isIn("无键甲", "无键乙");
        assertThat(receiptRows(jdbc, 96, 93005)).isZero();
    }

    private static QuestionEditResult execute(
            TransactionTemplate transactions,
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts,
            QuestionEditCommand command,
            byte[] digest
    ) {
        return transactions.execute(status ->
                QuestionEditWriteTransactionTestAccess.execute(
                        state,
                        receipts,
                        command,
                        digest));
    }

    private static QuestionEditCommand choiceCommand(
            long actorId,
            long questionId,
            QuestionEditIdempotencyKey key,
            String content,
            String answer
    ) {
        return new QuestionEditCommand(
                new QuestionEditorIdentity(actorId, true, false),
                questionId,
                Optional.of(content),
                Optional.of("选择题"),
                Optional.of(answer),
                Optional.of("更新后的解析"),
                Optional.of(
                        "[{\"key\":\"A\",\"value\":\"甲\"},"
                                + "{\"key\":\"B\",\"value\":\"乙\"}]"),
                key);
    }

    private static <T> List<T> concurrently(
            int count,
            java.util.concurrent.Callable<T> task
    ) throws Exception {
        List<java.util.concurrent.Callable<T>> tasks = new ArrayList<>();
        for (int index = 0; index < count; index++) {
            tasks.add(task);
        }
        return concurrently(tasks);
    }

    private static <T> List<T> concurrently(
            List<java.util.concurrent.Callable<T>> tasks
    ) throws Exception {
        CountDownLatch ready = new CountDownLatch(tasks.size());
        CountDownLatch start = new CountDownLatch(1);
        try (ExecutorService executor = Executors.newFixedThreadPool(tasks.size())) {
            List<Future<T>> futures = new ArrayList<>();
            for (java.util.concurrent.Callable<T> task : tasks) {
                futures.add(executor.submit(() -> {
                    ready.countDown();
                    assertThat(start.await(10, TimeUnit.SECONDS)).isTrue();
                    return task.call();
                }));
            }
            assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            List<T> results = new ArrayList<>();
            for (Future<T> future : futures) {
                results.add(future.get(20, TimeUnit.SECONDS));
            }
            return List.copyOf(results);
        }
    }

    private static void createLegacyFixture(JdbcClient jdbc) {
        jdbc.sql("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id BIGINT PRIMARY KEY,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS questions (
                    id BIGINT PRIMARY KEY,
                    subject_id BIGINT REFERENCES subjects(id) ON DELETE SET NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    options TEXT DEFAULT '[]',
                    answer TEXT DEFAULT '[]',
                    analysis TEXT,
                    tags TEXT DEFAULT '[]',
                    difficulty INTEGER DEFAULT 1,
                    image_path TEXT,
                    source TEXT,
                    created_by BIGINT,
                    updated_by BIGINT,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """).update();
    }

    private static void truncate(JdbcClient jdbc) {
        jdbc.sql("""
                TRUNCATE TABLE
                    catalog_question_edit_commands,
                    questions,
                    subjects
                RESTART IDENTITY CASCADE
                """).update();
        jdbc.sql("INSERT INTO subjects (id, name) VALUES (92001, '高等数学')")
                .update();
    }

    private static void insertQuestion(
            JdbcClient jdbc,
            long questionId,
            String content,
            String type
    ) {
        jdbc.sql("""
                        INSERT INTO questions (
                            id,
                            subject_id,
                            type,
                            content,
                            options,
                            answer,
                            analysis,
                            tags,
                            difficulty,
                            image_path,
                            source,
                            created_by,
                            updated_by
                        ) VALUES (
                            :id,
                            92001,
                            :type,
                            :content,
                            '[{"key":"A","value":"旧甲"},{"key":"B","value":"旧乙"}]',
                            CASE WHEN :type = 'multi_choice' THEN '[0,1]' ELSE '[0]' END,
                            '原始解析',
                            '["标签一","标签二"]',
                            3,
                            '/question.png',
                            'phase4c-it',
                            91,
                            91
                        )
                        """)
                .param("id", questionId)
                .param("type", type)
                .param("content", content)
                .update();
    }

    private static void assertQuestionColumns(
            JdbcClient jdbc,
            long questionId,
            String type,
            String content,
            String optionsJson,
            String answerJson,
            String analysis,
            String tagsJson,
            int difficulty
    ) {
        List<String> values = jdbc.sql("""
                        SELECT type,
                               content,
                               options::jsonb::text,
                               answer::jsonb::text,
                               analysis,
                               tags::jsonb::text,
                               difficulty::text
                          FROM questions
                         WHERE id = :id
                        """)
                .param("id", questionId)
                .query((row, rowNumber) -> List.of(
                        row.getString(1),
                        row.getString(2),
                        row.getString(3),
                        row.getString(4),
                        row.getString(5),
                        row.getString(6),
                        row.getString(7)))
                .single();
        assertThat(values).containsExactly(
                type,
                content,
                optionsJson,
                answerJson,
                analysis,
                tagsJson,
                Integer.toString(difficulty));
    }

    private static String questionContent(JdbcClient jdbc, long questionId) {
        return jdbc.sql("SELECT content FROM questions WHERE id = :id")
                .param("id", questionId)
                .query(String.class)
                .single();
    }

    private static long receiptRows(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM catalog_question_edit_commands
                         WHERE actor_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .query(Long.class)
                .single();
    }

    private static int receiptStatus(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        return jdbc.sql("""
                        SELECT response_status
                          FROM catalog_question_edit_commands
                         WHERE actor_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .query(Integer.class)
                .single();
    }

    private static byte[] digest(int firstByte) {
        byte[] value = new byte[32];
        value[0] = (byte) firstByte;
        return value;
    }
}
