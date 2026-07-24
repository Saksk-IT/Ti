package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.SubjectContextView;
import io.saksk.ti.catalog.application.port.SubjectContextQueryPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcSubjectContextQueryAdapterTestAccess;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRating;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyWriteOutcome;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.learning.application.StudyWriteTransactionTestAccess;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.StudyStatePort;
import io.saksk.ti.learning.infrastructure.persistence.JdbcLearningWriteReceiptAdapterTestAccess;
import io.saksk.ti.learning.infrastructure.persistence.JdbcStudyStateAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
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
class Phase4cStudyWriteTransactionIT {

    private static final String RECEIPT_SECRET =
            "phase4c-study-write-receipt-secret-0001";
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
    void studyStateAndReceiptsAreAtomicOnPostgres18() throws Exception {
        assertStudyTransactions(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void studyStateAndReceiptsAreAtomicOnPostgres16() throws Exception {
        assertStudyTransactions(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertStudyTransactions(
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
        StudyStatePort state = JdbcStudyStateAdapterTestAccess.create(jdbc);
        LearningWriteReceiptPort receipts =
                JdbcLearningWriteReceiptAdapterTestAccess.create(
                        jdbc,
                        RECEIPT_SECRET,
                        Duration.ofHours(24),
                        CLOCK);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        createLegacyFixture(jdbc);
        truncate(jdbc);

        assertExactSubjectResolution(jdbc);
        assertPublicAndPersonalBankLearning(jdbc, transactions, state, receipts);
        assertReviewSchedulingAndMastering(jdbc, transactions, state, receipts);
        assertReplayConflictAndRollback(jdbc, transactions, state, receipts);
        assertConcurrentSameKeyCommitsOnce(jdbc, transactions, state, receipts);
        assertConcurrentNoHeaderPreservesTwoAttempts(
                jdbc, transactions, state, receipts);
        assertThatThrownBy(() -> state.lockScope(
                        new StudyStatePort.StudyKey(1, "public", 1, 1)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("writable transaction");
    }

    private static void assertExactSubjectResolution(JdbcClient jdbc) {
        SubjectContextQueryPort subjects =
                JdbcSubjectContextQueryAdapterTestAccess.create(jdbc);
        jdbc.sql("""
                        INSERT INTO subjects (id, name)
                        VALUES (11, '高等数学'), (12, '高等数学 '), (13, 'Math')
                        """)
                .update();
        assertThat(subjects.findSubjectByExactName("高等数学"))
                .contains(new SubjectContextView(11, "高等数学"));
        assertThat(subjects.findSubjectByExactName("高等数学 ")).contains(
                new SubjectContextView(12, "高等数学 "));
        assertThat(subjects.findSubjectByExactName("math")).isEmpty();
        assertThat(subjects.findSubjectByExactName("不存在")).isEmpty();
    }

    private static void assertPublicAndPersonalBankLearning(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 1001);
        insertQuestion(jdbc, 1101);
        insertBankQuestion(jdbc, 1201, 1301);

        StudyWriteResult<StudyLearnView> first = learn(
                transactions,
                state,
                receipts,
                1001,
                1101,
                true,
                "public",
                201,
                LearningWriteIdempotencyKey.absent(),
                digest(1));
        learn(transactions, state, receipts, 1001, 1101, true, "public", 201,
                LearningWriteIdempotencyKey.absent(), digest(1));
        StudyWriteResult<StudyLearnView> third = learn(
                transactions,
                state,
                receipts,
                1001,
                1101,
                true,
                "public",
                201,
                LearningWriteIdempotencyKey.absent(),
                digest(1));

        assertThat(first.data()).contains(new StudyLearnView(1, false, Optional.empty()));
        assertThat(third.data()).contains(new StudyLearnView(
                3,
                true,
                Optional.of(LocalDateTime.parse("2026-07-24T04:00:00"))));
        assertThat(learningInt(jdbc, 1001, "public", 201, 1101, "streak"))
                .isEqualTo(3);
        assertThat(learningBoolean(
                        jdbc, 1001, "public", 201, 1101, "is_learned"))
                .isTrue();
        assertThat(reviewRows(jdbc, 1001, "public", 201, 1101)).isEqualTo(1);

        StudyWriteResult<StudyLearnView> wrong = learn(
                transactions,
                state,
                receipts,
                1001,
                1101,
                false,
                "public",
                201,
                LearningWriteIdempotencyKey.absent(),
                digest(2));
        assertThat(wrong.data()).contains(new StudyLearnView(0, false, Optional.empty()));
        assertThat(mistakeCount(jdbc, "mistakes", 1001, 1101)).isEqualTo(1);

        learn(transactions, state, receipts, 1001, 1301, false, "user_bank", 1201,
                LearningWriteIdempotencyKey.absent(), digest(3));
        learn(transactions, state, receipts, 1001, 1301, false, "user_bank", 1201,
                LearningWriteIdempotencyKey.absent(), digest(3));
        assertThat(mistakeCount(jdbc, "user_bank_mistakes", 1001, 1301))
                .isEqualTo(2);
        assertThat(jdbc.sql("""
                        SELECT bank_id
                          FROM user_bank_mistakes
                         WHERE user_id = 1001 AND question_id = 1301
                        """).query(Integer.class).single())
                .isEqualTo(1201);
    }

    private static void assertReviewSchedulingAndMastering(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 2001);
        insertQuestion(jdbc, 2101);

        StudyWriteResult<StudyReviewRecordView> known = review(
                transactions,
                state,
                receipts,
                2001,
                2101,
                StudyReviewRating.KNOWN,
                "public",
                202,
                LearningWriteIdempotencyKey.absent(),
                digest(4));
        assertThat(known.data()).contains(new StudyReviewRecordView(
                1,
                LocalDateTime.parse("2026-07-26T04:00:00")));

        StudyWriteResult<StudyReviewRecordView> fuzzy = review(
                transactions,
                state,
                receipts,
                2001,
                2101,
                StudyReviewRating.FUZZY,
                "public",
                202,
                LearningWriteIdempotencyKey.absent(),
                digest(5));
        assertThat(fuzzy.data()).contains(new StudyReviewRecordView(
                0,
                LocalDateTime.parse("2026-07-25T04:00:00")));

        review(transactions, state, receipts, 2001, 2101, StudyReviewRating.UNKNOWN,
                "public", 202, LearningWriteIdempotencyKey.absent(), digest(6));
        assertThat(reviewInt(
                        jdbc, 2001, "public", 202, 2101, "lapse_count"))
                .isEqualTo(1);
        assertThat(reviewString(
                        jdbc, 2001, "public", 202, 2101, "last_rating"))
                .isEqualTo("unknown");

        StudyWriteResult<StudyReviewMasterView> mastered = master(
                transactions,
                state,
                receipts,
                2001,
                2101,
                true,
                "public",
                202,
                LearningWriteIdempotencyKey.absent(),
                digest(7));
        assertThat(mastered.data()).contains(new StudyReviewMasterView(true));
        assertThat(reviewBoolean(
                        jdbc, 2001, "public", 202, 2101, "is_mastered"))
                .isTrue();
        assertThat(reviewTimestamp(
                        jdbc, 2001, "public", 202, 2101, "next_due_at"))
                .isNull();

        master(transactions, state, receipts, 2001, 2101, false, "public", 202,
                LearningWriteIdempotencyKey.absent(), digest(8));
        assertThat(reviewTimestamp(
                        jdbc, 2001, "public", 202, 2101, "next_due_at"))
                .isEqualTo(LocalDateTime.parse("2026-07-24T04:00:00"));
        assertThat(reviewInt(
                        jdbc, 2001, "public", 202, 2101, "lapse_count"))
                .isEqualTo(1);
    }

    private static void assertReplayConflictAndRollback(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 3001);
        insertQuestion(jdbc, 3101);
        LearningWriteIdempotencyKey key = LearningWriteIdempotencyKey.of("study-replay-key");

        StudyWriteResult<StudyLearnView> committed = learn(
                transactions,
                state,
                receipts,
                3001,
                3101,
                true,
                "public",
                203,
                key,
                digest(9));
        StudyWriteResult<StudyLearnView> replayed = learn(
                transactions,
                state,
                receipts,
                3001,
                3101,
                true,
                "public",
                203,
                key,
                digest(9));
        assertThat(committed.replayed()).isFalse();
        assertThat(replayed.replayed()).isTrue();
        assertThat(learningInt(jdbc, 3001, "public", 203, 3101, "correct_count"))
                .isEqualTo(1);
        assertThat(receiptRows(jdbc, 3001, "study-learn")).isEqualTo(1);

        StudyWriteResult<StudyLearnView> conflict = learn(
                transactions,
                state,
                receipts,
                3001,
                3101,
                false,
                "public",
                203,
                key,
                digest(10));
        assertThat(conflict.outcome()).isEqualTo(StudyWriteOutcome.IDEMPOTENCY_CONFLICT);
        assertThat(learningInt(jdbc, 3001, "public", 203, 3101, "wrong_count"))
                .isZero();

        insertActor(jdbc, 3002);
        insertQuestion(jdbc, 3102);
        LearningWriteIdempotencyKey rollbackKey =
                LearningWriteIdempotencyKey.of("study-rollback-key");
        assertThatThrownBy(() -> transactions.executeWithoutResult(status -> {
            StudyWriteTransactionTestAccess.recordLearning(
                    state,
                    receipts,
                    CLOCK,
                    3002,
                    3102,
                    true,
                    "public",
                    203,
                    rollbackKey,
                    digest(11));
            throw new IllegalStateException("force rollback");
        })).isInstanceOf(IllegalStateException.class)
                .hasMessage("force rollback");
        assertThat(learningRows(jdbc, 3002, "public", 203, 3102)).isZero();
        assertThat(receiptRows(jdbc, 3002, "study-learn")).isZero();

        assertThat(learn(
                        transactions,
                        state,
                        receipts,
                        3002,
                        3102,
                        true,
                        "public",
                        203,
                        rollbackKey,
                        digest(11)).outcome())
                .isEqualTo(StudyWriteOutcome.SUCCESS);
    }

    private static void assertConcurrentSameKeyCommitsOnce(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts
    ) throws Exception {
        insertActor(jdbc, 4001);
        insertQuestion(jdbc, 4101);
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch start = new CountDownLatch(1);
        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            List<Future<StudyWriteResult<StudyLearnView>>> futures = new ArrayList<>();
            for (int index = 0; index < 2; index++) {
                futures.add(executor.submit(() -> {
                    ready.countDown();
                    assertThat(start.await(10, TimeUnit.SECONDS)).isTrue();
                    return learn(
                            transactions,
                            state,
                            receipts,
                            4001,
                            4101,
                            true,
                            "public",
                            204,
                            LearningWriteIdempotencyKey.of("concurrent-study-key"),
                            digest(12));
                }));
            }
            assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            List<StudyWriteResult<StudyLearnView>> results =
                    futures.stream().map(Phase4cStudyWriteTransactionIT::get).toList();
            assertThat(results).allMatch(
                    result -> result.outcome() == StudyWriteOutcome.SUCCESS);
            assertThat(results.stream().filter(StudyWriteResult::replayed).count())
                    .isEqualTo(1);
        }
        assertThat(learningInt(jdbc, 4001, "public", 204, 4101, "correct_count"))
                .isEqualTo(1);
        assertThat(receiptRows(jdbc, 4001, "study-learn")).isEqualTo(1);
    }

    private static void assertConcurrentNoHeaderPreservesTwoAttempts(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts
    ) throws Exception {
        insertActor(jdbc, 5001);
        insertQuestion(jdbc, 5101);
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch start = new CountDownLatch(1);
        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            List<Future<StudyWriteResult<StudyLearnView>>> futures = new ArrayList<>();
            for (int index = 0; index < 2; index++) {
                futures.add(executor.submit(() -> {
                    ready.countDown();
                    assertThat(start.await(10, TimeUnit.SECONDS)).isTrue();
                    return learn(
                            transactions,
                            state,
                            receipts,
                            5001,
                            5101,
                            true,
                            "public",
                            205,
                            LearningWriteIdempotencyKey.absent(),
                            digest(13));
                }));
            }
            assertThat(ready.await(10, TimeUnit.SECONDS)).isTrue();
            start.countDown();
            assertThat(futures.stream()
                            .map(Phase4cStudyWriteTransactionIT::get)
                            .map(result -> result.data().orElseThrow().streak())
                            .sorted()
                            .toList())
                    .containsExactly(1, 2);
        }
        assertThat(learningInt(jdbc, 5001, "public", 205, 5101, "correct_count"))
                .isEqualTo(2);
        assertThat(receiptRows(jdbc, 5001, "study-learn")).isZero();
    }

    private static StudyWriteResult<StudyLearnView> learn(
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            long actorId,
            long questionId,
            boolean correct,
            String source,
            int scopeId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] digest
    ) {
        return transactions.execute(status ->
                StudyWriteTransactionTestAccess.recordLearning(
                        state,
                        receipts,
                        CLOCK,
                        actorId,
                        questionId,
                        correct,
                        source,
                        scopeId,
                        idempotencyKey,
                        digest));
    }

    private static StudyWriteResult<StudyReviewRecordView> review(
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            long actorId,
            long questionId,
            StudyReviewRating rating,
            String source,
            int scopeId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] digest
    ) {
        return transactions.execute(status ->
                StudyWriteTransactionTestAccess.recordReview(
                        state,
                        receipts,
                        CLOCK,
                        actorId,
                        questionId,
                        rating,
                        source,
                        scopeId,
                        idempotencyKey,
                        digest));
    }

    private static StudyWriteResult<StudyReviewMasterView> master(
            TransactionTemplate transactions,
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            long actorId,
            long questionId,
            boolean mastered,
            String source,
            int scopeId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] digest
    ) {
        return transactions.execute(status ->
                StudyWriteTransactionTestAccess.setReviewMastered(
                        state,
                        receipts,
                        CLOCK,
                        actorId,
                        questionId,
                        mastered,
                        source,
                        scopeId,
                        idempotencyKey,
                        digest));
    }

    private static <T> T get(Future<T> future) {
        try {
            return future.get(20, TimeUnit.SECONDS);
        } catch (Exception exception) {
            throw new AssertionError("Concurrent study request failed", exception);
        }
    }

    private static void createLegacyFixture(JdbcClient jdbc) {
        jdbc.sql("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS user_question_banks (
                    id INTEGER PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS user_bank_questions (
                    id INTEGER PRIMARY KEY,
                    bank_id INTEGER NOT NULL REFERENCES user_question_banks(id)
                );
                CREATE TABLE IF NOT EXISTS study_learning (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    scope_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    streak INTEGER DEFAULT 0,
                    is_learned BOOLEAN DEFAULT false,
                    correct_count INTEGER DEFAULT 0,
                    wrong_count INTEGER DEFAULT 0,
                    last_result TEXT,
                    last_answered_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, source, scope_id, question_id)
                );
                CREATE TABLE IF NOT EXISTS study_review (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    scope_id INTEGER NOT NULL,
                    question_id INTEGER NOT NULL,
                    review_level INTEGER DEFAULT 0,
                    next_due_at TIMESTAMP,
                    last_review_at TIMESTAMP,
                    last_rating TEXT,
                    lapse_count INTEGER DEFAULT 0,
                    is_mastered BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, source, scope_id, question_id)
                );
                CREATE TABLE IF NOT EXISTS mistakes (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                    wrong_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, question_id)
                );
                CREATE TABLE IF NOT EXISTS user_bank_mistakes (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    bank_id INTEGER NOT NULL REFERENCES user_question_banks(id) ON DELETE CASCADE,
                    question_id INTEGER NOT NULL REFERENCES user_bank_questions(id)
                        ON DELETE CASCADE,
                    wrong_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, question_id)
                )
                """).update();
    }

    private static void truncate(JdbcClient jdbc) {
        jdbc.sql("""
                TRUNCATE TABLE
                    learning_idempotency_receipts,
                    study_learning,
                    study_review,
                    mistakes,
                    user_bank_mistakes,
                    user_bank_questions,
                    user_question_banks,
                    questions,
                    subjects,
                    users
                RESTART IDENTITY CASCADE
                """).update();
    }

    private static void insertActor(JdbcClient jdbc, int actorId) {
        jdbc.sql("INSERT INTO users (id) VALUES (:id)")
                .param("id", actorId)
                .update();
    }

    private static void insertQuestion(JdbcClient jdbc, int questionId) {
        jdbc.sql("INSERT INTO questions (id) VALUES (:id)")
                .param("id", questionId)
                .update();
    }

    private static void insertBankQuestion(
            JdbcClient jdbc,
            int bankId,
            int questionId
    ) {
        jdbc.sql("INSERT INTO user_question_banks (id) VALUES (:id)")
                .param("id", bankId)
                .update();
        jdbc.sql("""
                        INSERT INTO user_bank_questions (id, bank_id)
                        VALUES (:questionId, :bankId)
                        """)
                .param("questionId", questionId)
                .param("bankId", bankId)
                .update();
    }

    private static int learningInt(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId,
            String column
    ) {
        return jdbc.sql("SELECT " + column + " FROM study_learning"
                        + " WHERE user_id=:actor AND source=:source"
                        + " AND scope_id=:scope AND question_id=:question")
                .param("actor", actorId)
                .param("source", source)
                .param("scope", scopeId)
                .param("question", questionId)
                .query(Integer.class)
                .single();
    }

    private static boolean learningBoolean(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId,
            String column
    ) {
        return jdbc.sql("SELECT " + column + " FROM study_learning"
                        + " WHERE user_id=:actor AND source=:source"
                        + " AND scope_id=:scope AND question_id=:question")
                .param("actor", actorId)
                .param("source", source)
                .param("scope", scopeId)
                .param("question", questionId)
                .query(Boolean.class)
                .single();
    }

    private static int reviewInt(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId,
            String column
    ) {
        return jdbc.sql("SELECT " + column + " FROM study_review"
                        + " WHERE user_id=:actor AND source=:source"
                        + " AND scope_id=:scope AND question_id=:question")
                .param("actor", actorId)
                .param("source", source)
                .param("scope", scopeId)
                .param("question", questionId)
                .query(Integer.class)
                .single();
    }

    private static String reviewString(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId,
            String column
    ) {
        return jdbc.sql("SELECT " + column + " FROM study_review"
                        + " WHERE user_id=:actor AND source=:source"
                        + " AND scope_id=:scope AND question_id=:question")
                .param("actor", actorId)
                .param("source", source)
                .param("scope", scopeId)
                .param("question", questionId)
                .query(String.class)
                .single();
    }

    private static boolean reviewBoolean(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId,
            String column
    ) {
        return jdbc.sql("SELECT " + column + " FROM study_review"
                        + " WHERE user_id=:actor AND source=:source"
                        + " AND scope_id=:scope AND question_id=:question")
                .param("actor", actorId)
                .param("source", source)
                .param("scope", scopeId)
                .param("question", questionId)
                .query(Boolean.class)
                .single();
    }

    private static LocalDateTime reviewTimestamp(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId,
            String column
    ) {
        return jdbc.sql("SELECT " + column + " FROM study_review"
                        + " WHERE user_id=:actor AND source=:source"
                        + " AND scope_id=:scope AND question_id=:question")
                .param("actor", actorId)
                .param("source", source)
                .param("scope", scopeId)
                .param("question", questionId)
                .query(LocalDateTime.class)
                .optional()
                .orElse(null);
    }

    private static long mistakeCount(
            JdbcClient jdbc,
            String table,
            long actorId,
            long questionId
    ) {
        assertThat(table).isIn("mistakes", "user_bank_mistakes");
        return jdbc.sql("SELECT wrong_count::bigint FROM " + table
                        + " WHERE user_id=:actor AND question_id=:question")
                .param("actor", actorId)
                .param("question", questionId)
                .query(Long.class)
                .single();
    }

    private static long reviewRows(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId
    ) {
        return count(jdbc, "study_review", actorId, source, scopeId, questionId);
    }

    private static long learningRows(
            JdbcClient jdbc,
            long actorId,
            String source,
            int scopeId,
            long questionId
    ) {
        return count(jdbc, "study_learning", actorId, source, scopeId, questionId);
    }

    private static long count(
            JdbcClient jdbc,
            String table,
            long actorId,
            String source,
            int scopeId,
            long questionId
    ) {
        assertThat(table).isIn("study_learning", "study_review");
        return jdbc.sql("SELECT COUNT(*) FROM " + table
                        + " WHERE user_id=:actor AND source=:source"
                        + " AND scope_id=:scope AND question_id=:question")
                .param("actor", actorId)
                .param("source", source)
                .param("scope", scopeId)
                .param("question", questionId)
                .query(Long.class)
                .single();
    }

    private static long receiptRows(
            JdbcClient jdbc,
            long actorId,
            String operation
    ) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM learning_idempotency_receipts
                         WHERE actor_id = :actor
                           AND operation = :operation
                        """)
                .param("actor", actorId)
                .param("operation", operation)
                .query(Long.class)
                .single();
    }

    private static byte[] digest(int firstByte) {
        byte[] value = new byte[32];
        value[0] = (byte) firstByte;
        return value;
    }
}
