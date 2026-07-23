package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.application.port.CatalogQuestionEditReceiptPort;
import io.saksk.ti.catalog.infrastructure.persistence.JdbcCatalogQuestionEditReceiptAdapterTestAccess;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.infrastructure.persistence.JdbcLearningWriteReceiptAdapterTestAccess;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HexFormat;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
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
class Phase4cTransactionWriteReceiptStoreIT {

    private static final Instant NOW = Instant.parse("2026-07-23T08:00:00Z");
    private static final Duration RECEIPT_TTL = Duration.ofHours(24);
    private static final String LEARNING_SECRET =
            "phase4c-learning-write-idempotency-secret-0001";
    private static final String CATALOG_SECRET =
            "phase4c-catalog-question-edit-secret-0001";
    private static final String LEARNING_DOMAIN =
            "ti-java:learning-write-idempotency:v1\u0000";
    private static final String CATALOG_DOMAIN =
            "ti-java:catalog-question-edit-idempotency:v1\u0000";

    @Container
    static final PostgreSQLContainer POSTGRES_18 =
            Phase2PostgresContainers.reference18();

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

    @Test
    void receiptStoresAreAtomicAndConcurrentOnPostgres18() throws Exception {
        assertReceiptStores(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void receiptStoresAreAtomicAndConcurrentOnPostgres16() throws Exception {
        assertReceiptStores(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertReceiptStores(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(),
                postgres.getUsername(),
                postgres.getPassword());
        Flyway flyway = Flyway.configure()
                .dataSource(dataSource)
                .locations("classpath:db/migration")
                .baselineOnMigrate(true)
                .baselineVersion("0")
                .validateMigrationNaming(true)
                .load();
        flyway.migrate();

        JdbcClient jdbc = JdbcClient.create(dataSource);
        TransactionTemplate transactions =
                new TransactionTemplate(new DataSourceTransactionManager(dataSource));
        Clock clock = Clock.fixed(NOW, ZoneOffset.UTC);
        LearningWriteReceiptPort learning =
                JdbcLearningWriteReceiptAdapterTestAccess.create(
                        jdbc, LEARNING_SECRET, RECEIPT_TTL, clock);
        CatalogQuestionEditReceiptPort catalog =
                JdbcCatalogQuestionEditReceiptAdapterTestAccess.create(
                        jdbc, CATALOG_SECRET, RECEIPT_TTL, clock);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        truncate(jdbc);

        assertLearningReplayConflictRollbackAndHmac(jdbc, transactions, learning);
        assertLearningConcurrentReplay(transactions, learning);
        assertExpiredLearningReceiptCanBeReacquired(jdbc, transactions, clock);
        assertCatalogReplayConflictRollbackAndHmac(jdbc, transactions, catalog);
        assertCatalogConcurrentReplay(transactions, catalog);
        assertWritableTransactionIsMandatory(learning, catalog);
    }

    private static void assertLearningReplayConflictRollbackAndHmac(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            LearningWriteReceiptPort learning
    ) {
        byte[] request = digest(11);
        String rawKey = "learning-raw-key-α";
        LearningWriteReceiptPort.BeginResult first = transactions.execute(status ->
                learning.begin(new LearningWriteReceiptPort.BeginCommand(
                        101L,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        rawKey,
                        request)));
        assertThat(first.outcome()).isEqualTo(LearningWriteReceiptPort.BeginOutcome.ACQUIRED);

        LearningWriteReceiptPort.StoredResponse completed = transactions.execute(status ->
                learning.complete(new LearningWriteReceiptPort.CompleteCommand(
                        101L,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        rawKey,
                        request,
                        201,
                        "{\"ok\":true,\"value\":1}")));
        assertThat(completed.status()).isEqualTo(201);
        assertThat(completed.bodyJson()).isEqualTo("{\"ok\": true, \"value\": 1}");

        LearningWriteReceiptPort.BeginResult replay = transactions.execute(status ->
                learning.begin(new LearningWriteReceiptPort.BeginCommand(
                        101L,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        rawKey,
                        request)));
        assertThat(replay.outcome()).isEqualTo(LearningWriteReceiptPort.BeginOutcome.REPLAY);
        assertThat(replay.replay()).contains(completed);

        LearningWriteReceiptPort.BeginResult conflict = transactions.execute(status ->
                learning.begin(new LearningWriteReceiptPort.BeginCommand(
                        101L,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        rawKey,
                        digest(12))));
        assertThat(conflict.outcome()).isEqualTo(LearningWriteReceiptPort.BeginOutcome.CONFLICT);

        String storedHmac = jdbc.sql("""
                        SELECT encode(key_hmac, 'hex')
                          FROM learning_idempotency_receipts
                         WHERE actor_id = 101 AND operation = 'favorite'
                        """)
                .query(String.class)
                .single();
        assertThat(storedHmac)
                .isEqualTo(hmacHex(LEARNING_SECRET, LEARNING_DOMAIN, rawKey))
                .doesNotContain(HexFormat.of().formatHex(
                        rawKey.getBytes(StandardCharsets.UTF_8)));

        LearningWriteReceiptPort.BeginResult rolledBack = transactions.execute(status -> {
            LearningWriteReceiptPort.BeginResult acquired =
                    learning.begin(new LearningWriteReceiptPort.BeginCommand(
                            102L,
                            LearningWriteReceiptPort.Operation.CHECKIN,
                            "learning-rollback-key",
                            digest(13)));
            status.setRollbackOnly();
            return acquired;
        });
        assertThat(rolledBack.outcome())
                .isEqualTo(LearningWriteReceiptPort.BeginOutcome.ACQUIRED);
        assertThat(receiptCount(jdbc, "learning_idempotency_receipts", 102L)).isZero();
        LearningWriteReceiptPort.BeginResult reacquired = transactions.execute(status -> {
            LearningWriteReceiptPort.BeginResult acquired =
                    learning.begin(new LearningWriteReceiptPort.BeginCommand(
                            102L,
                            LearningWriteReceiptPort.Operation.CHECKIN,
                            "learning-rollback-key",
                            digest(13)));
            status.setRollbackOnly();
            return acquired;
        });
        assertThat(reacquired.outcome())
                .isEqualTo(LearningWriteReceiptPort.BeginOutcome.ACQUIRED);
    }

    private static void assertLearningConcurrentReplay(
            TransactionTemplate transactions,
            LearningWriteReceiptPort learning
    ) throws Exception {
        AtomicInteger businessCommits = new AtomicInteger();
        CountDownLatch receiptCompletedButUncommitted = new CountDownLatch(1);
        CountDownLatch allowCommit = new CountDownLatch(1);
        CountDownLatch contenderStarted = new CountDownLatch(1);

        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            Future<LearningWriteReceiptPort.StoredResponse> winner = executor.submit(() ->
                    transactions.execute(status -> {
                        LearningWriteReceiptPort.BeginResult acquired =
                                learning.begin(new LearningWriteReceiptPort.BeginCommand(
                                        201L,
                                        LearningWriteReceiptPort.Operation.RECORD_RESULT,
                                        "learning-concurrent-key",
                                        digest(21)));
                        assertThat(acquired.outcome())
                                .isEqualTo(LearningWriteReceiptPort.BeginOutcome.ACQUIRED);
                        businessCommits.incrementAndGet();
                        LearningWriteReceiptPort.StoredResponse response =
                                learning.complete(new LearningWriteReceiptPort.CompleteCommand(
                                        201L,
                                        LearningWriteReceiptPort.Operation.RECORD_RESULT,
                                        "learning-concurrent-key",
                                        digest(21),
                                        200,
                                        "{\"status\":\"success\"}"));
                        receiptCompletedButUncommitted.countDown();
                        await(allowCommit);
                        return response;
                    }));

            assertThat(receiptCompletedButUncommitted.await(10, TimeUnit.SECONDS)).isTrue();
            Future<LearningWriteReceiptPort.BeginResult> contender = executor.submit(() ->
                    transactions.execute(status -> {
                        contenderStarted.countDown();
                        return learning.begin(new LearningWriteReceiptPort.BeginCommand(
                                201L,
                                LearningWriteReceiptPort.Operation.RECORD_RESULT,
                                "learning-concurrent-key",
                                digest(21)));
                    }));
            assertThat(contenderStarted.await(10, TimeUnit.SECONDS)).isTrue();
            assertThatThrownBy(() -> contender.get(300, TimeUnit.MILLISECONDS))
                    .isInstanceOf(TimeoutException.class);

            allowCommit.countDown();
            LearningWriteReceiptPort.StoredResponse committed = get(winner);
            LearningWriteReceiptPort.BeginResult replay = get(contender);
            assertThat(replay.outcome())
                    .isEqualTo(LearningWriteReceiptPort.BeginOutcome.REPLAY);
            assertThat(replay.replay()).contains(committed);
            assertThat(businessCommits).hasValue(1);
        } finally {
            allowCommit.countDown();
        }
    }

    private static void assertExpiredLearningReceiptCanBeReacquired(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            Clock initialClock
    ) {
        LearningWriteReceiptPort initial =
                JdbcLearningWriteReceiptAdapterTestAccess.create(
                        jdbc, LEARNING_SECRET, RECEIPT_TTL, initialClock);
        transactions.executeWithoutResult(status -> {
            initial.begin(new LearningWriteReceiptPort.BeginCommand(
                    301L,
                    LearningWriteReceiptPort.Operation.STUDY_LEARN,
                    "expired-learning-key",
                    digest(31)));
            initial.complete(new LearningWriteReceiptPort.CompleteCommand(
                    301L,
                    LearningWriteReceiptPort.Operation.STUDY_LEARN,
                    "expired-learning-key",
                    digest(31),
                    200,
                    "{\"status\":\"success\"}"));
        });

        LearningWriteReceiptPort advanced =
                JdbcLearningWriteReceiptAdapterTestAccess.create(
                        jdbc,
                        LEARNING_SECRET,
                        RECEIPT_TTL,
                        Clock.offset(initialClock, RECEIPT_TTL.plusSeconds(1)));
        LearningWriteReceiptPort.BeginResult reacquired = transactions.execute(status -> {
            LearningWriteReceiptPort.BeginResult result =
                    advanced.begin(new LearningWriteReceiptPort.BeginCommand(
                            301L,
                            LearningWriteReceiptPort.Operation.STUDY_LEARN,
                            "expired-learning-key",
                            digest(32)));
            status.setRollbackOnly();
            return result;
        });
        assertThat(reacquired.outcome())
                .isEqualTo(LearningWriteReceiptPort.BeginOutcome.ACQUIRED);
    }

    private static void assertCatalogReplayConflictRollbackAndHmac(
            JdbcClient jdbc,
            TransactionTemplate transactions,
            CatalogQuestionEditReceiptPort catalog
    ) {
        byte[] request = digest(41);
        String rawKey = "catalog-raw-key-β";
        CatalogQuestionEditReceiptPort.BeginResult first = transactions.execute(status ->
                catalog.begin(new CatalogQuestionEditReceiptPort.BeginCommand(
                        401L, 701L, rawKey, request)));
        assertThat(first.outcome())
                .isEqualTo(CatalogQuestionEditReceiptPort.BeginOutcome.ACQUIRED);

        CatalogQuestionEditReceiptPort.StoredResponse completed =
                transactions.execute(status -> catalog.complete(
                        new CatalogQuestionEditReceiptPort.CompleteCommand(
                                401L,
                                701L,
                                rawKey,
                                request,
                                200,
                                "{\"status\":\"success\",\"id\":701}")));
        CatalogQuestionEditReceiptPort.BeginResult replay = transactions.execute(status ->
                catalog.begin(new CatalogQuestionEditReceiptPort.BeginCommand(
                        401L, 701L, rawKey, request)));
        assertThat(replay.outcome())
                .isEqualTo(CatalogQuestionEditReceiptPort.BeginOutcome.REPLAY);
        assertThat(replay.replay()).contains(completed);

        CatalogQuestionEditReceiptPort.BeginResult questionConflict =
                transactions.execute(status -> catalog.begin(
                        new CatalogQuestionEditReceiptPort.BeginCommand(
                                401L, 702L, rawKey, request)));
        assertThat(questionConflict.outcome())
                .isEqualTo(CatalogQuestionEditReceiptPort.BeginOutcome.CONFLICT);
        CatalogQuestionEditReceiptPort.BeginResult payloadConflict =
                transactions.execute(status -> catalog.begin(
                        new CatalogQuestionEditReceiptPort.BeginCommand(
                                401L, 701L, rawKey, digest(42))));
        assertThat(payloadConflict.outcome())
                .isEqualTo(CatalogQuestionEditReceiptPort.BeginOutcome.CONFLICT);

        String storedHmac = jdbc.sql("""
                        SELECT encode(key_hmac, 'hex')
                          FROM catalog_question_edit_commands
                         WHERE actor_id = 401
                        """)
                .query(String.class)
                .single();
        assertThat(storedHmac)
                .isEqualTo(hmacHex(CATALOG_SECRET, CATALOG_DOMAIN, rawKey))
                .doesNotContain(HexFormat.of().formatHex(
                        rawKey.getBytes(StandardCharsets.UTF_8)));

        CatalogQuestionEditReceiptPort.BeginResult rolledBack =
                transactions.execute(status -> {
                    CatalogQuestionEditReceiptPort.BeginResult acquired =
                            catalog.begin(new CatalogQuestionEditReceiptPort.BeginCommand(
                                    402L,
                                    703L,
                                    "catalog-rollback-key",
                                    digest(43)));
                    status.setRollbackOnly();
                    return acquired;
                });
        assertThat(rolledBack.outcome())
                .isEqualTo(CatalogQuestionEditReceiptPort.BeginOutcome.ACQUIRED);
        assertThat(receiptCount(jdbc, "catalog_question_edit_commands", 402L)).isZero();
    }

    private static void assertCatalogConcurrentReplay(
            TransactionTemplate transactions,
            CatalogQuestionEditReceiptPort catalog
    ) throws Exception {
        AtomicInteger businessCommits = new AtomicInteger();
        CountDownLatch receiptCompletedButUncommitted = new CountDownLatch(1);
        CountDownLatch allowCommit = new CountDownLatch(1);
        CountDownLatch contenderStarted = new CountDownLatch(1);

        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            Future<CatalogQuestionEditReceiptPort.StoredResponse> winner = executor.submit(() ->
                    transactions.execute(status -> {
                        CatalogQuestionEditReceiptPort.BeginResult acquired =
                                catalog.begin(new CatalogQuestionEditReceiptPort.BeginCommand(
                                        501L,
                                        801L,
                                        "catalog-concurrent-key",
                                        digest(51)));
                        assertThat(acquired.outcome())
                                .isEqualTo(CatalogQuestionEditReceiptPort.BeginOutcome.ACQUIRED);
                        businessCommits.incrementAndGet();
                        CatalogQuestionEditReceiptPort.StoredResponse response =
                                catalog.complete(
                                        new CatalogQuestionEditReceiptPort.CompleteCommand(
                                                501L,
                                                801L,
                                                "catalog-concurrent-key",
                                                digest(51),
                                                200,
                                                "{\"status\":\"success\"}"));
                        receiptCompletedButUncommitted.countDown();
                        await(allowCommit);
                        return response;
                    }));

            assertThat(receiptCompletedButUncommitted.await(10, TimeUnit.SECONDS)).isTrue();
            Future<CatalogQuestionEditReceiptPort.BeginResult> contender = executor.submit(() ->
                    transactions.execute(status -> {
                        contenderStarted.countDown();
                        return catalog.begin(new CatalogQuestionEditReceiptPort.BeginCommand(
                                501L,
                                801L,
                                "catalog-concurrent-key",
                                digest(51)));
                    }));
            assertThat(contenderStarted.await(10, TimeUnit.SECONDS)).isTrue();
            assertThatThrownBy(() -> contender.get(300, TimeUnit.MILLISECONDS))
                    .isInstanceOf(TimeoutException.class);

            allowCommit.countDown();
            CatalogQuestionEditReceiptPort.StoredResponse committed = get(winner);
            CatalogQuestionEditReceiptPort.BeginResult replay = get(contender);
            assertThat(replay.outcome())
                    .isEqualTo(CatalogQuestionEditReceiptPort.BeginOutcome.REPLAY);
            assertThat(replay.replay()).contains(committed);
            assertThat(businessCommits).hasValue(1);
        } finally {
            allowCommit.countDown();
        }
    }

    private static void assertWritableTransactionIsMandatory(
            LearningWriteReceiptPort learning,
            CatalogQuestionEditReceiptPort catalog
    ) {
        assertThatThrownBy(() -> learning.begin(
                        new LearningWriteReceiptPort.BeginCommand(
                                601L,
                                LearningWriteReceiptPort.Operation.CHECKIN,
                                "no-transaction-learning-key",
                                digest(61))))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("writable transaction");
        assertThatThrownBy(() -> catalog.begin(
                        new CatalogQuestionEditReceiptPort.BeginCommand(
                                601L,
                                901L,
                                "no-transaction-catalog-key",
                                digest(62))))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("writable transaction");
    }

    private static long receiptCount(JdbcClient jdbc, String table, long actorId) {
        return jdbc.sql("SELECT COUNT(*) FROM " + table + " WHERE actor_id = :actorId")
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    private static void truncate(JdbcClient jdbc) {
        jdbc.sql("""
                TRUNCATE TABLE
                    learning_idempotency_receipts,
                    catalog_question_edit_commands
                """).update();
    }

    private static byte[] digest(int firstByte) {
        byte[] digest = new byte[32];
        digest[0] = (byte) firstByte;
        return digest;
    }

    private static String hmacHex(String secret, String domain, String rawKey) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(
                    secret.getBytes(StandardCharsets.UTF_8),
                    "HmacSHA256"));
            mac.update(domain.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(
                    mac.doFinal(rawKey.getBytes(StandardCharsets.UTF_8)));
        } catch (java.security.GeneralSecurityException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private static void await(CountDownLatch latch) {
        try {
            if (!latch.await(10, TimeUnit.SECONDS)) {
                throw new IllegalStateException("Timed out waiting for concurrent receipt test");
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while waiting for receipt test", exception);
        }
    }

    private static <T> T get(Future<T> future)
            throws InterruptedException, ExecutionException, TimeoutException {
        return future.get(10, TimeUnit.SECONDS);
    }
}
