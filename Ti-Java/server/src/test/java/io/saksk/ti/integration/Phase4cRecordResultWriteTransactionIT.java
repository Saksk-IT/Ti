package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.QuizLimitPolicy;
import io.saksk.ti.learning.api.RecordResultAction;
import io.saksk.ti.learning.api.RecordResultResult;
import io.saksk.ti.learning.application.RecordResultWriteTransactionTestAccess;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.RecordResultStatePort;
import io.saksk.ti.learning.infrastructure.persistence.JdbcLearningWriteReceiptAdapterTestAccess;
import io.saksk.ti.learning.infrastructure.persistence.JdbcRecordResultStateAdapterTestAccess;
import io.saksk.ti.operations.api.QuizLimitPolicyView;
import io.saksk.ti.operations.application.QuizLimitPolicyQueryServiceTestAccess;
import io.saksk.ti.operations.application.port.QuizLimitPolicyReadPort;
import io.saksk.ti.operations.infrastructure.persistence.JdbcQuizLimitPolicyReadAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
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
class Phase4cRecordResultWriteTransactionIT {

    private static final String RECEIPT_SECRET =
            "phase4c-record-result-receipt-secret-0001";
    private static final Clock CLOCK = Clock.fixed(
            Instant.parse("2026-07-23T13:00:00Z"),
            ZoneOffset.UTC);

    @Container
    static final PostgreSQLContainer POSTGRES_18 =
            Phase2PostgresContainers.reference18();

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

    @Test
    void recordResultStateAndReceiptAreAtomicOnPostgres18() throws Exception {
        assertRecordResultTransaction(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void recordResultStateAndReceiptAreAtomicOnPostgres16() throws Exception {
        assertRecordResultTransaction(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertRecordResultTransaction(
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
        RecordResultStatePort state =
                JdbcRecordResultStateAdapterTestAccess.create(jdbc);
        LearningWriteReceiptPort receipts =
                JdbcLearningWriteReceiptAdapterTestAccess.create(
                        jdbc,
                        RECEIPT_SECRET,
                        Duration.ofHours(24),
                        CLOCK);
        QuizLimitPolicyReadPort policyRows =
                JdbcQuizLimitPolicyReadAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        createLegacyFixture(jdbc);
        truncate(jdbc);

        assertOperationsOwnedPolicyRead(jdbc, policyRows);
        assertLegacyMistakeAndLatestAnswerTransitions(
                jdbc, transactions, state, receipts);
        assertQuotaAndAdministratorSemantics(
                jdbc, transactions, state, receipts);
        assertReplayAndConflict(jdbc, transactions, state, receipts);
        assertRollbackReleasesEveryBusinessRowAndReceipt(
                jdbc, transactions, state, receipts);
        assertConcurrentSameKeyCommitsExactlyOnce(
                jdbc, transactions, state, receipts);
        assertConcurrentNoHeaderQuotaCannotOvershoot(
                jdbc, transactions, state, receipts);
        assertThatThrownBy(() -> state.lockActor(9001L))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("writable transaction");
    }

    private static void assertOperationsOwnedPolicyRead(
            JdbcClient jdbc,
            QuizLimitPolicyReadPort policyRows
    ) {
        assertThat(QuizLimitPolicyQueryServiceTestAccess.read(policyRows))
                .isEqualTo(new QuizLimitPolicyView(false, 100));

        jdbc.sql("""
                        INSERT INTO system_config (config_key, config_value)
                        VALUES
                            ('quiz_limit_enabled', '1'),
                            ('quiz_limit_count', '60')
                        """)
                .update();
        assertThat(QuizLimitPolicyQueryServiceTestAccess.read(policyRows))
                .isEqualTo(new QuizLimitPolicyView(true, 60));

        jdbc.sql("""
                        UPDATE system_config
                           SET config_value = 'not-an-integer'
                         WHERE config_key = 'quiz_limit_count'
                        """)
                .update();
        assertThat(QuizLimitPolicyQueryServiceTestAccess.read(policyRows))
                .isEqualTo(new QuizLimitPolicyView(true, 100));
        jdbc.sql("TRUNCATE TABLE system_config").update();
    }

    private static void assertLegacyMistakeAndLatestAnswerTransitions(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 1001L);
        insertQuestion(jdbc, 1101L);

        RecordResultResult firstWrong = execute(
                transactions,
                state,
                receipts,
                1001L,
                false,
                1101L,
                false,
                true,
                QuizLimitPolicy.disabled(),
                LearningWriteIdempotencyKey.absent(),
                digest(1));
        RecordResultResult secondWrong = execute(
                transactions,
                state,
                receipts,
                1001L,
                false,
                1101L,
                false,
                true,
                QuizLimitPolicy.disabled(),
                LearningWriteIdempotencyKey.absent(),
                digest(1));

        assertThat(firstWrong.action()).contains(RecordResultAction.ADDED_MISTAKE);
        assertThat(secondWrong.action()).contains(RecordResultAction.ADDED_MISTAKE);
        assertThat(mistakeCount(jdbc, 1001L, 1101L)).isEqualTo(2L);
        assertThat(answerCount(jdbc, 1001L, 1101L)).isEqualTo(1L);
        assertThat(latestCorrect(jdbc, 1001L, 1101L)).isFalse();
        assertThat(quizCount(jdbc, 1001L)).isZero();

        RecordResultResult kept = execute(
                transactions,
                state,
                receipts,
                1001L,
                false,
                1101L,
                true,
                false,
                QuizLimitPolicy.disabled(),
                LearningWriteIdempotencyKey.absent(),
                digest(2));
        assertThat(kept.action()).contains(RecordResultAction.KEPT_MISTAKE);
        assertThat(mistakeCount(jdbc, 1001L, 1101L)).isEqualTo(2L);
        assertThat(latestCorrect(jdbc, 1001L, 1101L)).isTrue();

        RecordResultResult removed = execute(
                transactions,
                state,
                receipts,
                1001L,
                false,
                1101L,
                true,
                true,
                QuizLimitPolicy.disabled(),
                LearningWriteIdempotencyKey.absent(),
                digest(3));
        assertThat(removed.action()).contains(RecordResultAction.REMOVED_MISTAKE);
        assertThat(mistakeRows(jdbc, 1001L, 1101L)).isZero();
        assertThat(answerCount(jdbc, 1001L, 1101L)).isEqualTo(1L);
        assertThat(latestCorrect(jdbc, 1001L, 1101L)).isTrue();
    }

    private static void assertQuotaAndAdministratorSemantics(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 2001L);
        insertQuestion(jdbc, 2101L);
        insertQuestion(jdbc, 2102L);
        QuizLimitPolicy oneAttempt = new QuizLimitPolicy(true, 1);

        RecordResultResult accepted = execute(
                transactions,
                state,
                receipts,
                2001L,
                false,
                2101L,
                false,
                true,
                oneAttempt,
                LearningWriteIdempotencyKey.absent(),
                digest(4));
        RecordResultResult limited = execute(
                transactions,
                state,
                receipts,
                2001L,
                false,
                2102L,
                false,
                true,
                oneAttempt,
                LearningWriteIdempotencyKey.absent(),
                digest(5));

        assertThat(accepted.outcome()).isEqualTo(RecordResultResult.Outcome.SUCCESS);
        assertThat(limited)
                .isEqualTo(RecordResultResult.quizLimitReached(1L, 1, false));
        assertThat(quizCount(jdbc, 2001L)).isEqualTo(1L);
        assertThat(answerCount(jdbc, 2001L, 2102L)).isZero();
        assertThat(mistakeRows(jdbc, 2001L, 2102L)).isZero();

        insertActor(jdbc, 2002L);
        insertQuestion(jdbc, 2103L);
        RecordResultResult administrator = execute(
                transactions,
                state,
                receipts,
                2002L,
                true,
                2103L,
                false,
                true,
                new QuizLimitPolicy(true, 0),
                LearningWriteIdempotencyKey.absent(),
                digest(6));
        assertThat(administrator.outcome())
                .isEqualTo(RecordResultResult.Outcome.SUCCESS);
        assertThat(quizCount(jdbc, 2002L)).isZero();
    }

    private static void assertReplayAndConflict(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 3001L);
        insertQuestion(jdbc, 3101L);
        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("record-result-replay-key");
        QuizLimitPolicy policy = new QuizLimitPolicy(true, 10);

        RecordResultResult first = execute(
                transactions,
                state,
                receipts,
                3001L,
                false,
                3101L,
                false,
                true,
                policy,
                key,
                digest(7));
        RecordResultResult replay = execute(
                transactions,
                state,
                receipts,
                3001L,
                false,
                3101L,
                false,
                true,
                policy,
                key,
                digest(7));
        RecordResultResult conflict = execute(
                transactions,
                state,
                receipts,
                3001L,
                false,
                3101L,
                false,
                true,
                policy,
                key,
                digest(8));

        assertThat(first).isEqualTo(RecordResultResult.success(
                RecordResultAction.ADDED_MISTAKE,
                false));
        assertThat(replay).isEqualTo(RecordResultResult.success(
                RecordResultAction.ADDED_MISTAKE,
                true));
        assertThat(conflict.outcome())
                .isEqualTo(RecordResultResult.Outcome.IDEMPOTENCY_CONFLICT);
        assertThat(mistakeCount(jdbc, 3001L, 3101L)).isEqualTo(1L);
        assertThat(answerCount(jdbc, 3001L, 3101L)).isEqualTo(1L);
        assertThat(quizCount(jdbc, 3001L)).isEqualTo(1L);
        assertThat(receiptCount(jdbc, 3001L)).isEqualTo(1L);
    }

    private static void assertRollbackReleasesEveryBusinessRowAndReceipt(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 4001L);
        insertQuestion(jdbc, 4101L);
        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("record-result-rollback-key");
        QuizLimitPolicy policy = new QuizLimitPolicy(true, 10);

        RecordResultResult rolledBack = transactions.execute(status -> {
            RecordResultResult result = RecordResultWriteTransactionTestAccess.execute(
                    state,
                    receipts,
                    4001L,
                    false,
                    4101L,
                    false,
                    true,
                    policy,
                    key,
                    digest(9));
            status.setRollbackOnly();
            return result;
        });
        assertThat(rolledBack.outcome())
                .isEqualTo(RecordResultResult.Outcome.SUCCESS);
        assertThat(mistakeRows(jdbc, 4001L, 4101L)).isZero();
        assertThat(answerCount(jdbc, 4001L, 4101L)).isZero();
        assertThat(quizCount(jdbc, 4001L)).isZero();
        assertThat(receiptCount(jdbc, 4001L)).isZero();

        RecordResultResult retried = execute(
                transactions,
                state,
                receipts,
                4001L,
                false,
                4101L,
                false,
                true,
                policy,
                key,
                digest(9));
        assertThat(retried.outcome())
                .isEqualTo(RecordResultResult.Outcome.SUCCESS);
        assertThat(mistakeCount(jdbc, 4001L, 4101L)).isEqualTo(1L);
        assertThat(answerCount(jdbc, 4001L, 4101L)).isEqualTo(1L);
        assertThat(quizCount(jdbc, 4001L)).isEqualTo(1L);
        assertThat(receiptCount(jdbc, 4001L)).isEqualTo(1L);
    }

    private static void assertConcurrentSameKeyCommitsExactlyOnce(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts
    ) throws Exception {
        insertActor(jdbc, 5001L);
        insertQuestion(jdbc, 5101L);
        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("record-result-concurrent-key");
        QuizLimitPolicy policy = new QuizLimitPolicy(true, 10);
        CountDownLatch winnerCompletedButUncommitted = new CountDownLatch(1);
        CountDownLatch allowWinnerCommit = new CountDownLatch(1);
        CountDownLatch contenderStarted = new CountDownLatch(1);

        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            Future<RecordResultResult> winner = executor.submit(() ->
                    transactions.execute(status -> {
                        RecordResultResult result =
                                RecordResultWriteTransactionTestAccess.execute(
                                        state,
                                        receipts,
                                        5001L,
                                        false,
                                        5101L,
                                        false,
                                        true,
                                        policy,
                                        key,
                                        digest(10));
                        winnerCompletedButUncommitted.countDown();
                        await(allowWinnerCommit);
                        return result;
                    }));
            assertThat(winnerCompletedButUncommitted.await(10, TimeUnit.SECONDS))
                    .isTrue();

            Future<RecordResultResult> contender = executor.submit(() -> {
                contenderStarted.countDown();
                return execute(
                        transactions,
                        state,
                        receipts,
                        5001L,
                        false,
                        5101L,
                        false,
                        true,
                        policy,
                        key,
                        digest(10));
            });
            assertThat(contenderStarted.await(10, TimeUnit.SECONDS)).isTrue();
            assertThatThrownBy(() -> contender.get(300, TimeUnit.MILLISECONDS))
                    .isInstanceOf(TimeoutException.class);

            allowWinnerCommit.countDown();
            assertThat(get(winner)).isEqualTo(RecordResultResult.success(
                    RecordResultAction.ADDED_MISTAKE,
                    false));
            assertThat(get(contender)).isEqualTo(RecordResultResult.success(
                    RecordResultAction.ADDED_MISTAKE,
                    true));
            assertThat(mistakeCount(jdbc, 5001L, 5101L)).isEqualTo(1L);
            assertThat(answerCount(jdbc, 5001L, 5101L)).isEqualTo(1L);
            assertThat(quizCount(jdbc, 5001L)).isEqualTo(1L);
            assertThat(receiptCount(jdbc, 5001L)).isEqualTo(1L);
        } finally {
            allowWinnerCommit.countDown();
        }
    }

    private static void assertConcurrentNoHeaderQuotaCannotOvershoot(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts
    ) throws Exception {
        insertActor(jdbc, 6001L);
        insertQuestion(jdbc, 6101L);
        insertQuestion(jdbc, 6102L);
        QuizLimitPolicy policy = new QuizLimitPolicy(true, 1);
        CountDownLatch start = new CountDownLatch(1);

        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            Future<RecordResultResult> first = executor.submit(() -> {
                await(start);
                return execute(
                        transactions,
                        state,
                        receipts,
                        6001L,
                        false,
                        6101L,
                        false,
                        true,
                        policy,
                        LearningWriteIdempotencyKey.absent(),
                        digest(11));
            });
            Future<RecordResultResult> second = executor.submit(() -> {
                await(start);
                return execute(
                        transactions,
                        state,
                        receipts,
                        6001L,
                        false,
                        6102L,
                        false,
                        true,
                        policy,
                        LearningWriteIdempotencyKey.absent(),
                        digest(12));
            });
            start.countDown();

            List<RecordResultResult.Outcome> outcomes =
                    List.of(get(first).outcome(), get(second).outcome());
            assertThat(outcomes)
                    .containsExactlyInAnyOrder(
                            RecordResultResult.Outcome.SUCCESS,
                            RecordResultResult.Outcome.QUIZ_LIMIT_REACHED);
            assertThat(quizCount(jdbc, 6001L)).isEqualTo(1L);
            assertThat(mistakeRowsForActor(jdbc, 6001L)).isEqualTo(1L);
            assertThat(answerRowsForActor(jdbc, 6001L)).isEqualTo(1L);
        }
    }

    private static RecordResultResult execute(
            TransactionTemplate transactions,
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts,
            long actorId,
            boolean administrator,
            long questionId,
            boolean correct,
            boolean clearMistake,
            QuizLimitPolicy policy,
            LearningWriteIdempotencyKey key,
            byte[] requestSha256
    ) {
        return transactions.execute(status ->
                RecordResultWriteTransactionTestAccess.execute(
                        state,
                        receipts,
                        actorId,
                        administrator,
                        questionId,
                        correct,
                        clearMistake,
                        policy,
                        key,
                        requestSha256));
    }

    private static void createLegacyFixture(JdbcClient jdbc) {
        jdbc.sql("""
                        CREATE TABLE users (
                            id INTEGER PRIMARY KEY
                        )
                        """)
                .update();
        jdbc.sql("""
                        CREATE TABLE questions (
                            id INTEGER PRIMARY KEY
                        )
                        """)
                .update();
        jdbc.sql("""
                        CREATE TABLE mistakes (
                            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            question_id INTEGER NOT NULL
                                REFERENCES questions(id) ON DELETE CASCADE,
                            wrong_count INTEGER DEFAULT 1,
                            created_at TIMESTAMP WITHOUT TIME ZONE
                                DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITHOUT TIME ZONE
                                DEFAULT CURRENT_TIMESTAMP,
                            last_updated TIMESTAMP WITHOUT TIME ZONE
                                DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT uq_mistakes_user_question
                                UNIQUE (user_id, question_id)
                        )
                        """)
                .update();
        jdbc.sql("""
                        CREATE TABLE user_answers (
                            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            question_id INTEGER NOT NULL
                                REFERENCES questions(id) ON DELETE CASCADE,
                            user_answer TEXT,
                            is_correct BOOLEAN,
                            created_at TIMESTAMP WITHOUT TIME ZONE
                                DEFAULT CURRENT_TIMESTAMP
                        )
                        """)
                .update();
        jdbc.sql("""
                        CREATE TABLE user_quiz_stats (
                            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                            user_id INTEGER NOT NULL UNIQUE
                                REFERENCES users(id) ON DELETE CASCADE,
                            total_answered INTEGER DEFAULT 0,
                            last_reset_at TIMESTAMP WITHOUT TIME ZONE,
                            updated_at TIMESTAMP WITHOUT TIME ZONE
                                DEFAULT CURRENT_TIMESTAMP
                        )
                        """)
                .update();
        jdbc.sql("""
                        CREATE TABLE system_config (
                            id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                            config_key VARCHAR(128) NOT NULL UNIQUE,
                            config_value TEXT
                        )
                        """)
                .update();
    }

    private static void truncate(JdbcClient jdbc) {
        jdbc.sql("""
                        TRUNCATE TABLE
                            mistakes,
                            user_answers,
                            user_quiz_stats,
                            system_config,
                            users,
                            questions,
                            learning_idempotency_receipts
                        RESTART IDENTITY CASCADE
                        """)
                .update();
    }

    private static void insertActor(JdbcClient jdbc, long actorId) {
        jdbc.sql("INSERT INTO users (id) VALUES (:id)")
                .param("id", actorId)
                .update();
    }

    private static void insertQuestion(JdbcClient jdbc, long questionId) {
        jdbc.sql("INSERT INTO questions (id) VALUES (:id)")
                .param("id", questionId)
                .update();
    }

    private static long mistakeCount(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        return jdbc.sql("""
                        SELECT COALESCE(MAX(wrong_count), 0)::bigint
                          FROM mistakes
                         WHERE user_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .query(Long.class)
                .single();
    }

    private static long mistakeRows(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        return rowCount(jdbc, "mistakes", actorId, questionId);
    }

    private static long answerCount(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        return rowCount(jdbc, "user_answers", actorId, questionId);
    }

    private static long rowCount(
            JdbcClient jdbc,
            String table,
            long actorId,
            long questionId
    ) {
        String sql = switch (table) {
            case "mistakes" -> """
                    SELECT COUNT(*)
                      FROM mistakes
                     WHERE user_id = :actorId
                       AND question_id = :questionId
                    """;
            case "user_answers" -> """
                    SELECT COUNT(*)
                      FROM user_answers
                     WHERE user_id = :actorId
                       AND question_id = :questionId
                    """;
            default -> throw new IllegalArgumentException("Unsupported table");
        };
        return jdbc.sql(sql)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .query(Long.class)
                .single();
    }

    private static boolean latestCorrect(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        return jdbc.sql("""
                        SELECT is_correct
                          FROM user_answers
                         WHERE user_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .query(Boolean.class)
                .single();
    }

    private static long quizCount(JdbcClient jdbc, long actorId) {
        return jdbc.sql("""
                        SELECT COALESCE(MAX(total_answered), 0)::bigint
                          FROM user_quiz_stats
                         WHERE user_id = :actorId
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    private static long receiptCount(JdbcClient jdbc, long actorId) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM learning_idempotency_receipts
                         WHERE actor_id = :actorId
                           AND operation = 'record-result'
                           AND state = 'COMPLETED'
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    private static long mistakeRowsForActor(JdbcClient jdbc, long actorId) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM mistakes
                         WHERE user_id = :actorId
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    private static long answerRowsForActor(JdbcClient jdbc, long actorId) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM user_answers
                         WHERE user_id = :actorId
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    private static byte[] digest(int firstByte) {
        byte[] value = new byte[32];
        value[0] = (byte) firstByte;
        return value;
    }

    private static <T> T get(Future<T> future) throws Exception {
        try {
            return future.get(10, TimeUnit.SECONDS);
        } catch (ExecutionException exception) {
            if (exception.getCause() instanceof Exception cause) {
                throw cause;
            }
            throw exception;
        }
    }

    private static void await(CountDownLatch latch) {
        try {
            if (!latch.await(10, TimeUnit.SECONDS)) {
                throw new IllegalStateException(
                        "Timed out waiting for record-result test gate");
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(
                    "Record-result test gate was interrupted",
                    exception);
        }
    }
}
