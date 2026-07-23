package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import io.saksk.ti.learning.application.FavoriteWriteTransactionTestAccess;
import io.saksk.ti.learning.application.port.FavoriteTogglePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.infrastructure.persistence.JdbcFavoriteToggleAdapterTestAccess;
import io.saksk.ti.learning.infrastructure.persistence.JdbcLearningWriteReceiptAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
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
class Phase4cFavoriteWriteTransactionIT {

    private static final String RECEIPT_SECRET =
            "phase4c-favorite-write-receipt-secret-0001";
    private static final Clock CLOCK = Clock.fixed(
            Instant.parse("2026-07-23T12:00:00Z"),
            ZoneOffset.UTC);

    @Container
    static final PostgreSQLContainer POSTGRES_18 =
            Phase2PostgresContainers.reference18();

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

    @Test
    void favoriteMutationAndReceiptAreAtomicOnPostgres18() throws Exception {
        assertFavoriteTransaction(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void favoriteMutationAndReceiptAreAtomicOnPostgres16() throws Exception {
        assertFavoriteTransaction(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertFavoriteTransaction(
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
        FavoriteTogglePort favorites =
                JdbcFavoriteToggleAdapterTestAccess.create(jdbc);
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

        assertNoHeaderToggle(jdbc, transactions, favorites, receipts);
        assertReplayAndConflict(jdbc, transactions, favorites, receipts);
        assertRollbackReleasesBusinessRowAndReceipt(
                jdbc, transactions, favorites, receipts);
        assertConcurrentSameKeyCommitsExactlyOnce(
                jdbc, transactions, favorites, receipts);
        assertThatThrownBy(() -> favorites.toggle(9001L, 9101L))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("writable transaction");
    }

    private static void assertNoHeaderToggle(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            FavoriteTogglePort favorites,
            LearningWriteReceiptPort receipts
    ) {
        insertActorAndQuestion(jdbc, 1001L, 1101L);

        ToggleFavoriteResult added = execute(
                transactions,
                favorites,
                receipts,
                1001L,
                1101L,
                LearningWriteIdempotencyKey.absent(),
                digest(1));
        ToggleFavoriteResult removed = execute(
                transactions,
                favorites,
                receipts,
                1001L,
                1101L,
                LearningWriteIdempotencyKey.absent(),
                digest(1));

        assertThat(added).isEqualTo(ToggleFavoriteResult.success(true, false));
        assertThat(removed).isEqualTo(ToggleFavoriteResult.success(false, false));
        assertThat(favoriteCount(jdbc, 1001L, 1101L)).isZero();
        assertThat(receiptCount(jdbc, 1001L)).isZero();
    }

    private static void assertReplayAndConflict(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            FavoriteTogglePort favorites,
            LearningWriteReceiptPort receipts
    ) {
        insertActorAndQuestion(jdbc, 2001L, 2101L);
        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("favorite-replay-key");

        ToggleFavoriteResult first = execute(
                transactions, favorites, receipts, 2001L, 2101L, key, digest(2));
        ToggleFavoriteResult replay = execute(
                transactions, favorites, receipts, 2001L, 2101L, key, digest(2));
        ToggleFavoriteResult conflict = execute(
                transactions, favorites, receipts, 2001L, 2101L, key, digest(3));

        assertThat(first).isEqualTo(ToggleFavoriteResult.success(true, false));
        assertThat(replay).isEqualTo(ToggleFavoriteResult.success(true, true));
        assertThat(conflict.outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.IDEMPOTENCY_CONFLICT);
        assertThat(favoriteCount(jdbc, 2001L, 2101L)).isEqualTo(1);
        assertThat(receiptCount(jdbc, 2001L)).isEqualTo(1);
        assertThat(completedReceiptCount(jdbc, 2001L)).isEqualTo(1);
    }

    private static void assertRollbackReleasesBusinessRowAndReceipt(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            FavoriteTogglePort favorites,
            LearningWriteReceiptPort receipts
    ) {
        insertActorAndQuestion(jdbc, 3001L, 3101L);
        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("favorite-rollback-key");

        ToggleFavoriteResult rolledBack = transactions.execute(status -> {
            ToggleFavoriteResult result = FavoriteWriteTransactionTestAccess.execute(
                    favorites,
                    receipts,
                    3001L,
                    3101L,
                    key,
                    digest(4));
            status.setRollbackOnly();
            return result;
        });
        assertThat(rolledBack)
                .isEqualTo(ToggleFavoriteResult.success(true, false));
        assertThat(favoriteCount(jdbc, 3001L, 3101L)).isZero();
        assertThat(receiptCount(jdbc, 3001L)).isZero();

        ToggleFavoriteResult retried = execute(
                transactions, favorites, receipts, 3001L, 3101L, key, digest(4));
        assertThat(retried).isEqualTo(ToggleFavoriteResult.success(true, false));
        assertThat(favoriteCount(jdbc, 3001L, 3101L)).isEqualTo(1);
        assertThat(completedReceiptCount(jdbc, 3001L)).isEqualTo(1);
    }

    private static void assertConcurrentSameKeyCommitsExactlyOnce(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            FavoriteTogglePort favorites,
            LearningWriteReceiptPort receipts
    ) throws Exception {
        insertActorAndQuestion(jdbc, 4001L, 4101L);
        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("favorite-concurrent-key");
        CountDownLatch winnerCompletedButUncommitted = new CountDownLatch(1);
        CountDownLatch allowWinnerCommit = new CountDownLatch(1);
        CountDownLatch contenderStarted = new CountDownLatch(1);

        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            Future<ToggleFavoriteResult> winner = executor.submit(() ->
                    transactions.execute(status -> {
                        ToggleFavoriteResult result =
                                FavoriteWriteTransactionTestAccess.execute(
                                        favorites,
                                        receipts,
                                        4001L,
                                        4101L,
                                        key,
                                        digest(5));
                        winnerCompletedButUncommitted.countDown();
                        await(allowWinnerCommit);
                        return result;
                    }));
            assertThat(winnerCompletedButUncommitted.await(10, TimeUnit.SECONDS))
                    .isTrue();

            Future<ToggleFavoriteResult> contender = executor.submit(() -> {
                contenderStarted.countDown();
                return execute(
                        transactions,
                        favorites,
                        receipts,
                        4001L,
                        4101L,
                        key,
                        digest(5));
            });
            assertThat(contenderStarted.await(10, TimeUnit.SECONDS)).isTrue();
            assertThatThrownBy(() -> contender.get(300, TimeUnit.MILLISECONDS))
                    .isInstanceOf(TimeoutException.class);

            allowWinnerCommit.countDown();
            assertThat(get(winner))
                    .isEqualTo(ToggleFavoriteResult.success(true, false));
            assertThat(get(contender))
                    .isEqualTo(ToggleFavoriteResult.success(true, true));
            assertThat(favoriteCount(jdbc, 4001L, 4101L)).isEqualTo(1);
            assertThat(receiptCount(jdbc, 4001L)).isEqualTo(1);
            assertThat(completedReceiptCount(jdbc, 4001L)).isEqualTo(1);
        } finally {
            allowWinnerCommit.countDown();
        }
    }

    private static ToggleFavoriteResult execute(
            TransactionTemplate transactions,
            FavoriteTogglePort favorites,
            LearningWriteReceiptPort receipts,
            long actorId,
            long questionId,
            LearningWriteIdempotencyKey key,
            byte[] requestSha256
    ) {
        return transactions.execute(status ->
                FavoriteWriteTransactionTestAccess.execute(
                        favorites,
                        receipts,
                        actorId,
                        questionId,
                        key,
                        requestSha256));
    }

    private static void createLegacyFixture(JdbcClient jdbc) {
        jdbc.sql("""
                        CREATE TABLE users (
                            id BIGINT PRIMARY KEY
                        )
                        """)
                .update();
        jdbc.sql("""
                        CREATE TABLE questions (
                            id BIGINT PRIMARY KEY
                        )
                        """)
                .update();
        jdbc.sql("""
                        CREATE TABLE favorites (
                            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            CONSTRAINT uq_favorites_user_question
                                UNIQUE (user_id, question_id)
                        )
                        """)
                .update();
    }

    private static void truncate(JdbcClient jdbc) {
        jdbc.sql("""
                        TRUNCATE TABLE
                            favorites,
                            users,
                            questions,
                            learning_idempotency_receipts
                        RESTART IDENTITY CASCADE
                        """)
                .update();
    }

    private static void insertActorAndQuestion(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        jdbc.sql("INSERT INTO users (id) VALUES (:id)")
                .param("id", actorId)
                .update();
        jdbc.sql("INSERT INTO questions (id) VALUES (:id)")
                .param("id", questionId)
                .update();
    }

    private static long favoriteCount(
            JdbcClient jdbc,
            long actorId,
            long questionId
    ) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM favorites
                         WHERE user_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .query(Long.class)
                .single();
    }

    private static long receiptCount(JdbcClient jdbc, long actorId) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM learning_idempotency_receipts
                         WHERE actor_id = :actorId
                           AND operation = 'favorite'
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    private static long completedReceiptCount(JdbcClient jdbc, long actorId) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM learning_idempotency_receipts
                         WHERE actor_id = :actorId
                           AND operation = 'favorite'
                           AND state = 'COMPLETED'
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    private static byte[] digest(int firstByte) {
        byte[] digest = new byte[32];
        digest[0] = (byte) firstByte;
        return digest;
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
                throw new IllegalStateException("Timed out waiting for favorite test gate");
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Favorite test gate was interrupted", exception);
        }
    }
}
