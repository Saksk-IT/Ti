package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.api.CheckinResult;
import io.saksk.ti.learning.api.CheckinView;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.application.CheckinWriteTransactionTestAccess;
import io.saksk.ti.learning.application.port.CheckinStatePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.infrastructure.persistence.JdbcCheckinStateAdapterTestAccess;
import io.saksk.ti.learning.infrastructure.persistence.JdbcLearningWriteReceiptAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
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
class Phase4cCheckinWriteTransactionIT {

    private static final String RECEIPT_SECRET =
            "phase4c-checkin-receipt-secret-0000001";
    private static final LocalDate TODAY = LocalDate.parse("2026-07-24");
    private static final LocalDateTime NOW =
            LocalDateTime.parse("2026-07-24T09:15:00");
    private static final Clock RECEIPT_CLOCK = Clock.fixed(
            Instant.parse("2026-07-24T01:15:00Z"),
            ZoneOffset.UTC);

    @Container
    static final PostgreSQLContainer POSTGRES_18 =
            Phase2PostgresContainers.reference18();

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

    @Test
    void checkinStateAndReceiptAreAtomicOnPostgres18() throws Exception {
        assertCheckinTransactions(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void checkinStateAndReceiptAreAtomicOnPostgres16() throws Exception {
        assertCheckinTransactions(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertCheckinTransactions(
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
        CheckinStatePort state = JdbcCheckinStateAdapterTestAccess.create(jdbc);
        LearningWriteReceiptPort receipts =
                JdbcLearningWriteReceiptAdapterTestAccess.create(
                        jdbc,
                        RECEIPT_SECRET,
                        Duration.ofHours(48),
                        RECEIPT_CLOCK);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        createLegacyFixture(jdbc);
        truncate(jdbc);

        assertNaturalInsertAndAggregateSemantics(jdbc, transactions, state, receipts);
        assertExplicitReplayConflictAndRollback(jdbc, transactions, state, receipts);
        assertMalformedHistoricalDateFailsStreakClosed(
                jdbc, transactions, state, receipts);
        assertConcurrentNaturalKeyCreatesOneRow(
                jdbc, transactions, state, receipts);
        assertConcurrentExplicitKeyCommitsOneReceipt(
                jdbc, transactions, state, receipts);
        assertThatThrownBy(() -> state.countAll(1))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("writable transaction");
    }

    private static void assertNaturalInsertAndAggregateSemantics(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            CheckinStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 1001);
        insertCheckin(jdbc, 1001, "2026-06-30", "2026-06-30T08:00:00");
        insertCheckin(jdbc, 1001, "2026-07-21", "2026-07-21T08:00:00");
        insertCheckin(jdbc, 1001, "2026-07-22", "2026-07-22T08:00:00");
        insertCheckin(jdbc, 1001, "2026-07-23", "2026-07-23T08:00:00");

        CheckinResult first = execute(
                transactions,
                state,
                receipts,
                1001,
                LearningWriteIdempotencyKey.absent(),
                digest(1));
        assertThat(first).isEqualTo(CheckinResult.success(
                new CheckinView(
                        TODAY,
                        true,
                        Optional.of(NOW),
                        4,
                        5,
                        true,
                        List.of(
                                "2026-07-21",
                                "2026-07-22",
                                "2026-07-23",
                                "2026-07-24")),
                false));

        CheckinResult duplicate = execute(
                transactions,
                state,
                receipts,
                1001,
                LearningWriteIdempotencyKey.absent(),
                digest(1));
        assertThat(duplicate.data().orElseThrow().justCheckedIn()).isFalse();
        assertThat(duplicate.data().orElseThrow().checkedInAt()).contains(NOW);
        assertThat(checkinRows(jdbc, 1001, "2026-07-24")).isEqualTo(1);
        assertThat(receiptRows(jdbc, 1001)).isZero();
    }

    private static void assertExplicitReplayConflictAndRollback(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            CheckinStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 2001);
        LearningWriteIdempotencyKey key =
                LearningWriteIdempotencyKey.of("checkin-explicit-key");
        CheckinResult first = execute(
                transactions,
                state,
                receipts,
                2001,
                key,
                digest(2));
        CheckinResult replay = execute(
                transactions,
                state,
                receipts,
                2001,
                key,
                digest(2));
        assertThat(first.data().orElseThrow().justCheckedIn()).isTrue();
        assertThat(first.replayed()).isFalse();
        assertThat(replay.data().orElseThrow().justCheckedIn()).isTrue();
        assertThat(replay.replayed()).isTrue();
        assertThat(checkinRows(jdbc, 2001, "2026-07-24")).isEqualTo(1);
        assertThat(receiptRows(jdbc, 2001)).isEqualTo(1);

        CheckinResult conflict = execute(
                transactions,
                state,
                receipts,
                2001,
                key,
                digest(3));
        assertThat(conflict.outcome())
                .isEqualTo(CheckinResult.Outcome.IDEMPOTENCY_CONFLICT);
        assertThat(checkinRows(jdbc, 2001, "2026-07-24")).isEqualTo(1);

        insertActor(jdbc, 2002);
        LearningWriteIdempotencyKey rollbackKey =
                LearningWriteIdempotencyKey.of("checkin-rollback-key");
        assertThatThrownBy(() -> transactions.executeWithoutResult(status -> {
            CheckinWriteTransactionTestAccess.execute(
                    state,
                    receipts,
                    2002,
                    TODAY,
                    NOW,
                    rollbackKey,
                    digest(4));
            throw new IllegalStateException("force rollback");
        })).isInstanceOf(IllegalStateException.class)
                .hasMessage("force rollback");
        assertThat(checkinRows(jdbc, 2002, "2026-07-24")).isZero();
        assertThat(receiptRows(jdbc, 2002)).isZero();
        assertThat(execute(
                        transactions,
                        state,
                        receipts,
                        2002,
                        rollbackKey,
                        digest(4)).outcome())
                .isEqualTo(CheckinResult.Outcome.SUCCESS);
    }

    private static void assertMalformedHistoricalDateFailsStreakClosed(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            CheckinStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        insertActor(jdbc, 3001);
        insertCheckin(jdbc, 3001, "not-a-date", "2026-07-20T08:00:00");
        CheckinResult result = execute(
                transactions,
                state,
                receipts,
                3001,
                LearningWriteIdempotencyKey.absent(),
                digest(5));
        assertThat(result.data().orElseThrow().streakDays()).isZero();
        assertThat(result.data().orElseThrow().totalDays()).isEqualTo(2);
        assertThat(result.data().orElseThrow().checkedDates())
                .containsExactly("2026-07-24");

        insertActor(jdbc, 3002);
        jdbc.sql("""
                        INSERT INTO user_checkins (user_id, checkin_date, created_at)
                        VALUES (3002, '2026-07-24', NULL)
                        """).update();
        CheckinResult nullableTimestamp = execute(
                transactions,
                state,
                receipts,
                3002,
                LearningWriteIdempotencyKey.absent(),
                digest(6));
        assertThat(nullableTimestamp.data().orElseThrow().checkedInAt()).isEmpty();
        assertThat(nullableTimestamp.data().orElseThrow().justCheckedIn()).isFalse();
    }

    private static void assertConcurrentNaturalKeyCreatesOneRow(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            CheckinStatePort state,
            LearningWriteReceiptPort receipts
    ) throws Exception {
        insertActor(jdbc, 4001);
        List<CheckinResult> results = concurrently(2, () -> execute(
                transactions,
                state,
                receipts,
                4001,
                LearningWriteIdempotencyKey.absent(),
                digest(7)));
        assertThat(results).allMatch(
                result -> result.outcome() == CheckinResult.Outcome.SUCCESS);
        assertThat(results.stream()
                        .map(result -> result.data().orElseThrow().justCheckedIn())
                        .sorted()
                        .toList())
                .containsExactly(false, true);
        assertThat(checkinRows(jdbc, 4001, "2026-07-24")).isEqualTo(1);
        assertThat(receiptRows(jdbc, 4001)).isZero();
    }

    private static void assertConcurrentExplicitKeyCommitsOneReceipt(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            CheckinStatePort state,
            LearningWriteReceiptPort receipts
    ) throws Exception {
        insertActor(jdbc, 5001);
        List<CheckinResult> results = concurrently(2, () -> execute(
                transactions,
                state,
                receipts,
                5001,
                LearningWriteIdempotencyKey.of("concurrent-checkin-key"),
                digest(8)));
        assertThat(results).allMatch(
                result -> result.outcome() == CheckinResult.Outcome.SUCCESS);
        assertThat(results).allMatch(
                result -> result.data().orElseThrow().justCheckedIn());
        assertThat(results.stream().filter(CheckinResult::replayed).count())
                .isEqualTo(1);
        assertThat(checkinRows(jdbc, 5001, "2026-07-24")).isEqualTo(1);
        assertThat(receiptRows(jdbc, 5001)).isEqualTo(1);
    }

    private static CheckinResult execute(
            TransactionTemplate transactions,
            CheckinStatePort state,
            LearningWriteReceiptPort receipts,
            long actorId,
            LearningWriteIdempotencyKey key,
            byte[] digest
    ) {
        return transactions.execute(status ->
                CheckinWriteTransactionTestAccess.execute(
                        state,
                        receipts,
                        actorId,
                        TODAY,
                        NOW,
                        key,
                        digest));
    }

    private static <T> List<T> concurrently(
            int count,
            java.util.concurrent.Callable<T> task
    ) throws Exception {
        CountDownLatch ready = new CountDownLatch(count);
        CountDownLatch start = new CountDownLatch(1);
        try (ExecutorService executor = Executors.newFixedThreadPool(count)) {
            List<Future<T>> futures = new ArrayList<>();
            for (int index = 0; index < count; index++) {
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
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS user_checkins (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    checkin_date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, checkin_date)
                )
                """).update();
    }

    private static void truncate(JdbcClient jdbc) {
        jdbc.sql("""
                TRUNCATE TABLE
                    learning_idempotency_receipts,
                    user_checkins,
                    users
                RESTART IDENTITY CASCADE
                """).update();
    }

    private static void insertActor(JdbcClient jdbc, int actorId) {
        jdbc.sql("INSERT INTO users (id) VALUES (:id)")
                .param("id", actorId)
                .update();
    }

    private static void insertCheckin(
            JdbcClient jdbc,
            int actorId,
            String date,
            String createdAt
    ) {
        jdbc.sql("""
                        INSERT INTO user_checkins (
                            user_id,
                            checkin_date,
                            created_at
                        ) VALUES (
                            :actorId,
                            :date,
                            CAST(:createdAt AS timestamp)
                        )
                        """)
                .param("actorId", actorId)
                .param("date", date)
                .param("createdAt", createdAt)
                .update();
    }

    private static long checkinRows(
            JdbcClient jdbc,
            long actorId,
            String date
    ) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM user_checkins
                         WHERE user_id = :actorId
                           AND checkin_date = :date
                        """)
                .param("actorId", actorId)
                .param("date", date)
                .query(Long.class)
                .single();
    }

    private static long receiptRows(JdbcClient jdbc, long actorId) {
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM learning_idempotency_receipts
                         WHERE actor_id = :actorId
                           AND operation = 'checkin'
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
}
