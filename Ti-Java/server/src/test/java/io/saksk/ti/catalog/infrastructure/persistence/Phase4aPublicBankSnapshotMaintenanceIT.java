package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotMaintenancePort;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotQueryPort;
import io.saksk.ti.catalog.domain.PublicBankMetricProjection;
import io.saksk.ti.catalog.domain.PublicBankProjectionBatch;
import io.saksk.ti.catalog.domain.PublicBankSnapshotCommit;
import io.saksk.ti.catalog.domain.PublicBankViewerProjection;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.Connection;
import java.sql.Statement;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.List;
import java.util.OptionalLong;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Supplier;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase4aPublicBankSnapshotMaintenanceIT {

    private static final long WRITER_LOCK_KEY = 0x54495055424C4943L;
    private static final Instant BASE_TIME = Instant.parse("2026-07-16T04:00:00Z");
    private static final PublicBankRef SYSTEM =
            new PublicBankRef(PublicBankSource.SYSTEM, 6301);
    private static final PublicBankRef USER =
            new PublicBankRef(PublicBankSource.USER_PUBLIC, 6401);

    @Container
    static final PostgreSQLContainer POSTGRES_18 = maintenanceFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = maintenanceFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void maintenanceIsAtomicAndSelfInvalidatingOnPostgres18() throws Exception {
        assertMaintenanceContract(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void maintenanceIsAtomicAndSelfInvalidatingOnPostgres16() throws Exception {
        assertMaintenanceContract(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer maintenanceFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/040-subject-catalog-schema.sql"),
                        "/docker-entrypoint-initdb.d/040-subject-catalog-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/041-subject-catalog-seed.sql"),
                        "/docker-entrypoint-initdb.d/041-subject-catalog-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/042-public-bank-snapshot-schema.sql"),
                        "/docker-entrypoint-initdb.d/042-public-bank-snapshot-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4a/043-public-bank-snapshot-seed.sql"),
                        "/docker-entrypoint-initdb.d/043-public-bank-snapshot-seed.sql");
    }

    private static void assertMaintenanceContract(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        JdbcClient jdbc = JdbcClient.create(dataSource);
        PlatformTransactionManager transactions = new DataSourceTransactionManager(dataSource);
        JdbcPublicBankSnapshotMaintenanceAdapter maintenance =
                new JdbcPublicBankSnapshotMaintenanceAdapter(jdbc, transactions);
        PublicBankSnapshotQueryPort query =
                JdbcPublicBankSnapshotQueryAdapterTestAccess.create(jdbc);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertTriggerDefinitions(jdbc);

        PublicBankSnapshotMaintenancePort.CommitResult replaced = maintenance.replace(() -> {
            assertRepeatableReadWriterTransaction(jdbc);
            return batch("initial", 1, "Initial system", "Initial user");
        });
        assertThat(replaced.outcome())
                .isEqualTo(PublicBankSnapshotMaintenancePort.Outcome.COMMITTED);
        assertCompleteState(jdbc, replaced, 2, 1, 1, 2);
        assertVisibleName(query, SYSTEM, "Initial system");

        PublicBankSnapshotMaintenancePort.CommitResult empty = maintenance.replace(
                new PublicBankProjectionBatch(commit("empty", 2), List.of(), List.of()));
        assertCompleteState(jdbc, empty, 0, 0, 0, 0);
        var emptyRead = query.detail(SYSTEM, OptionalLong.empty());
        assertThat(emptyRead.snapshot().structurallyComplete()).isTrue();
        assertThat(emptyRead.data()).isEmpty();
        assertThat(query.summary(PublicBankFilter.all(), BASE_TIME.minusSeconds(604_800))
                .data().totalBanks()).isZero();

        PublicBankSnapshotMaintenancePort.CommitResult restored = maintenance.replace(
                batch("restore", 3, "Restored system", "Restored user"));
        PublicBankSnapshotMaintenancePort.CommitResult tombstoned = inTransaction(
                transactions,
                () -> maintenance.tombstone(USER, commit("tombstone", 4)));
        assertThat(tombstoned.generation()).isEqualTo(restored.generation() + 1);
        assertCompleteState(jdbc, tombstoned, 1, 1, 0, 1);
        assertThat(query.detail(USER, OptionalLong.empty()).data()).isEmpty();
        assertVisibleName(query, SYSTEM, "Restored system");

        String beforeFailedReplace = fingerprint(jdbc);
        assertThatThrownBy(() -> maintenance.replace(invalidForeignKeyBatch(5)))
                .isInstanceOf(DataIntegrityViolationException.class);
        assertThat(fingerprint(jdbc)).isEqualTo(beforeFailedReplace);
        assertThat(state(jdbc).status()).isEqualTo("complete");

        jdbc.sql("""
                UPDATE public_bank_plaza_metrics
                   SET name = 'tampered outside projector'
                 WHERE source_type = 'system' AND source_id = 6301
                """).update();
        assertThat(state(jdbc).status()).isEqualTo("failed");
        assertThat(query.detail(SYSTEM, OptionalLong.empty()).snapshot().structurallyComplete())
                .isFalse();

        PublicBankSnapshotMaintenancePort.CommitResult repaired = maintenance.replace(
                batch("repair", 6, "Before lock", "Repair user"));
        assertCompleteState(jdbc, repaired, 2, 1, 1, 2);

        String wrongDigest = "c".repeat(64);
        jdbc.sql("""
                UPDATE public_bank_plaza_snapshot_state
                   SET projection_digest = :digest
                 WHERE snapshot_name = 'public-bank-plaza'
                """).param("digest", wrongDigest).update();
        assertThat(query.detail(SYSTEM, OptionalLong.empty()).snapshot().structurallyComplete())
                .isFalse();
        repaired = maintenance.replace(
                batch("digest-repair", 7, "Before lock", "Repair user"));
        assertCompleteState(jdbc, repaired, 2, 1, 1, 2);

        assertThatThrownBy(() -> jdbc.sql("""
                        UPDATE public_bank_plaza_snapshot_state
                           SET metrics_count = -1
                         WHERE snapshot_name = 'public-bank-plaza'
                        """).update())
                .isInstanceOf(DataIntegrityViolationException.class);
        assertThat(state(jdbc).status()).isEqualTo("complete");

        String originalBoardName = boardName(jdbc, 5201);
        IllegalStateException rollbackBoardUpdate =
                new IllegalStateException("roll back board update");
        assertThatThrownBy(() -> inTransaction(transactions, () -> {
            assertThat(jdbc.sql("""
                            UPDATE plaza_boards
                               SET name = 'Rolled back board name'
                             WHERE id = 5201
                            """).update()).isEqualTo(1);
            assertThat(state(jdbc).status()).isEqualTo("failed");
            throw rollbackBoardUpdate;
        })).isSameAs(rollbackBoardUpdate);
        assertThat(boardName(jdbc, 5201)).isEqualTo(originalBoardName);
        assertThat(state(jdbc).status()).isEqualTo("complete");

        assertThat(jdbc.sql("""
                        UPDATE plaza_boards
                           SET name = 'Committed board name'
                         WHERE id = 5201
                        """).update()).isEqualTo(1);
        assertThat(state(jdbc).status()).isEqualTo("failed");
        assertThat(query.detail(SYSTEM, OptionalLong.empty()).snapshot().structurallyComplete())
                .isFalse();

        repaired = maintenance.replace(
                () -> batch("board-repair", 8, "Before lock", "Repair user"));
        assertCompleteState(jdbc, repaired, 2, 1, 1, 2);

        String beforeLoaderFailure = fingerprint(jdbc);
        IllegalStateException loaderFailure = new IllegalStateException("loader failed");
        AtomicInteger failedLoaderCalls = new AtomicInteger();
        assertThatThrownBy(() -> maintenance.replace(() -> {
                    failedLoaderCalls.incrementAndGet();
                    assertCurrentBackendHoldsWriterLock(jdbc);
                    assertThat(jdbc.sql("""
                                    UPDATE plaza_boards
                                       SET description = 'transient loader mutation'
                                     WHERE id = 5202
                                    """).update()).isEqualTo(1);
                    assertThat(state(jdbc).status()).isEqualTo("failed");
                    throw loaderFailure;
                })).isSameAs(loaderFailure);
        assertThat(failedLoaderCalls).as("non-transient loader failure is not retried").hasValue(1);
        assertThat(fingerprint(jdbc)).isEqualTo(beforeLoaderFailure);
        assertThat(state(jdbc).status()).isEqualTo("complete");

        repaired = assertWriterLockVisibility(
                dataSource, maintenance, query, jdbc, repaired);
        repaired = assertSupplierLoadersSerialize(
                maintenance, query, jdbc, repaired);
        assertCompleteState(jdbc, repaired, 2, 1, 1, 2);

        jdbc.sql("""
                DELETE FROM public_bank_plaza_metrics
                 WHERE source_type = 'user_public' AND source_id = 6401
                """).update();
        assertThat(state(jdbc).status()).isEqualTo("failed");
        assertThat(query.detail(USER, OptionalLong.empty()).snapshot().structurallyComplete())
                .isFalse();

        jdbc.sql("DELETE FROM public_bank_plaza_snapshot_state").update();
        assertThat(query.detail(SYSTEM, OptionalLong.empty()).snapshot().markerPresent()).isFalse();
    }

    private static PublicBankSnapshotMaintenancePort.CommitResult assertWriterLockVisibility(
            DataSource dataSource,
            JdbcPublicBankSnapshotMaintenanceAdapter maintenance,
            PublicBankSnapshotQueryPort query,
            JdbcClient jdbc,
            PublicBankSnapshotMaintenancePort.CommitResult previous
    ) throws Exception {
        try (Connection lockConnection = dataSource.getConnection();
                Statement statement = lockConnection.createStatement();
                ExecutorService executor = Executors.newSingleThreadExecutor()) {
            lockConnection.setAutoCommit(false);
            statement.execute("SELECT pg_advisory_xact_lock(" + WRITER_LOCK_KEY + ")");

            Future<PublicBankSnapshotMaintenancePort.CommitResult> future = executor.submit(
                    () -> maintenance.replace(
                            batch("concurrent", 9, "After lock", "Concurrent user")));
            awaitAdvisoryWaiter(jdbc);

            assertThat(future).isNotDone();
            assertVisibleName(query, SYSTEM, "Before lock");
            assertThat(state(jdbc).generation()).isEqualTo(previous.generation());

            lockConnection.commit();
            PublicBankSnapshotMaintenancePort.CommitResult committed =
                    future.get(5, TimeUnit.SECONDS);
            assertThat(committed.generation()).isEqualTo(previous.generation() + 1);
            assertVisibleName(query, SYSTEM, "After lock");
            assertCompleteState(jdbc, committed, 2, 1, 1, 2);
            return committed;
        }
    }

    private static PublicBankSnapshotMaintenancePort.CommitResult assertSupplierLoadersSerialize(
            JdbcPublicBankSnapshotMaintenanceAdapter maintenance,
            PublicBankSnapshotQueryPort query,
            JdbcClient jdbc,
            PublicBankSnapshotMaintenancePort.CommitResult previous
    ) throws Exception {
        CountDownLatch firstLoaderEntered = new CountDownLatch(1);
        CountDownLatch releaseFirstLoader = new CountDownLatch(1);
        CountDownLatch secondRetryLoaderEntered = new CountDownLatch(1);
        CountDownLatch releaseSecondRetryLoader = new CountDownLatch(1);
        AtomicInteger secondLoaderInvocations = new AtomicInteger();
        AtomicInteger activeLoaders = new AtomicInteger();
        AtomicInteger maximumActiveLoaders = new AtomicInteger();
        AtomicLong staleAttemptObservedGeneration = new AtomicLong(-1);
        AtomicLong retryObservedGeneration = new AtomicLong(-1);
        AtomicLong staleAttemptTransactionId = new AtomicLong(-1);
        AtomicLong retryTransactionId = new AtomicLong(-1);

        try (ExecutorService executor = Executors.newFixedThreadPool(2)) {
            Future<PublicBankSnapshotMaintenancePort.CommitResult> first = executor.submit(
                    () -> maintenance.replace(() -> {
                        assertRepeatableReadWriterTransaction(jdbc);
                        int active = activeLoaders.incrementAndGet();
                        maximumActiveLoaders.accumulateAndGet(active, Math::max);
                        firstLoaderEntered.countDown();
                        try {
                            if (!releaseFirstLoader.await(5, TimeUnit.SECONDS)) {
                                throw new IllegalStateException("Timed out releasing first loader");
                            }
                            return batch(
                                    "supplier-first", 10, "Supplier first", "Supplier user one");
                        } catch (InterruptedException exception) {
                            Thread.currentThread().interrupt();
                            throw new IllegalStateException(
                                    "Interrupted while holding public-bank writer lock", exception);
                        } finally {
                            activeLoaders.decrementAndGet();
                        }
                    }));

            assertThat(firstLoaderEntered.await(5, TimeUnit.SECONDS)).isTrue();
            Future<PublicBankSnapshotMaintenancePort.CommitResult> second = executor.submit(
                    () -> maintenance.replace(() -> {
                        int invocation = secondLoaderInvocations.incrementAndGet();
                        assertRepeatableReadWriterTransaction(jdbc);
                        int active = activeLoaders.incrementAndGet();
                        maximumActiveLoaders.accumulateAndGet(active, Math::max);
                        try {
                            long observedGeneration = state(jdbc).generation();
                            if (invocation == 1) {
                                staleAttemptObservedGeneration.set(observedGeneration);
                                staleAttemptTransactionId.set(currentTransactionId(jdbc));
                            } else if (invocation == 2) {
                                retryObservedGeneration.set(observedGeneration);
                                retryTransactionId.set(currentTransactionId(jdbc));
                                secondRetryLoaderEntered.countDown();
                                if (!releaseSecondRetryLoader.await(5, TimeUnit.SECONDS)) {
                                    throw new IllegalStateException(
                                            "Timed out releasing retried second loader");
                                }
                            } else {
                                throw new IllegalStateException(
                                        "Unexpected public-bank replacement retry count");
                            }
                            return batch(
                                    "supplier-second", 11,
                                    "Supplier second", "Supplier user two");
                        } catch (InterruptedException exception) {
                            Thread.currentThread().interrupt();
                            throw new IllegalStateException(
                                    "Interrupted while holding public-bank writer lock", exception);
                        } finally {
                            activeLoaders.decrementAndGet();
                        }
                    }));

            awaitAdvisoryWaiter(jdbc);
            assertThat(secondLoaderInvocations).hasValue(0);
            assertThat(maximumActiveLoaders).hasValue(1);

            releaseFirstLoader.countDown();
            PublicBankSnapshotMaintenancePort.CommitResult firstCommit =
                    first.get(5, TimeUnit.SECONDS);
            assertThat(secondRetryLoaderEntered.await(5, TimeUnit.SECONDS))
                    .as("second writer entered a fresh retry transaction")
                    .isTrue();

            assertThat(firstCommit.generation()).isEqualTo(previous.generation() + 1);
            assertThat(staleAttemptObservedGeneration)
                    .as("first second-writer attempt retained the pre-wait RR snapshot")
                    .hasValue(previous.generation());
            assertThat(retryObservedGeneration)
                    .as("retry entered a new RR transaction after rollback")
                    .hasValue(firstCommit.generation());
            assertThat(retryTransactionId.get())
                    .as("retry received a distinct PostgreSQL transaction id")
                    .isPositive()
                    .isNotEqualTo(staleAttemptTransactionId.get());
            assertThat(secondLoaderInvocations)
                    .as("projection source is reloaded in the fresh retry transaction")
                    .hasValue(2);
            assertCompleteState(jdbc, firstCommit, 2, 1, 1, 2);
            assertVisibleName(query, SYSTEM, "Supplier first");

            releaseSecondRetryLoader.countDown();
            PublicBankSnapshotMaintenancePort.CommitResult secondCommit =
                    second.get(5, TimeUnit.SECONDS);

            assertThat(secondCommit.generation()).isEqualTo(firstCommit.generation() + 1);
            assertThat(maximumActiveLoaders).hasValue(1);
            assertCompleteState(jdbc, secondCommit, 2, 1, 1, 2);
            assertVisibleName(query, SYSTEM, "Supplier second");
            return secondCommit;
        } finally {
            releaseFirstLoader.countDown();
            releaseSecondRetryLoader.countDown();
        }
    }

    private static void awaitAdvisoryWaiter(JdbcClient jdbc) throws InterruptedException {
        Instant deadline = Instant.now().plus(Duration.ofSeconds(5));
        long waiters = 0;
        while (waiters == 0 && Instant.now().isBefore(deadline)) {
            waiters = jdbc.sql("""
                            SELECT COUNT(*)
                              FROM pg_locks
                             WHERE locktype = 'advisory' AND NOT granted
                            """)
                    .query(Long.class)
                    .single();
            if (waiters == 0) {
                Thread.sleep(25);
            }
        }
        assertThat(waiters).as("blocked public-bank snapshot writer").isPositive();
    }

    private static void assertTriggerDefinitions(JdbcClient jdbc) {
        List<String> definitions = jdbc.sql("""
                        SELECT pg_get_triggerdef(oid)
                          FROM pg_trigger
                         WHERE tgname IN (
                             'trg_public_bank_boards_invalidate_snapshot',
                             'trg_public_bank_metrics_invalidate_snapshot',
                             'trg_public_bank_viewer_invalidate_snapshot'
                         )
                         ORDER BY tgname
                        """)
                .query(String.class)
                .list();
        assertThat(definitions).hasSize(3).allSatisfy(definition -> assertThat(definition)
                .contains("INSERT OR DELETE OR UPDATE OR TRUNCATE")
                .contains("FOR EACH STATEMENT"));
    }

    private static void assertRepeatableReadWriterTransaction(JdbcClient jdbc) {
        assertCurrentBackendHoldsWriterLock(jdbc);
        assertThat(jdbc.sql("SHOW transaction_isolation").query(String.class).single())
                .as("snapshot projection loader transaction isolation")
                .isEqualTo("repeatable read");
    }

    private static long currentTransactionId(JdbcClient jdbc) {
        return jdbc.sql("SELECT pg_current_xact_id()::text::bigint")
                .query(Long.class)
                .single();
    }

    private static void assertCurrentBackendHoldsWriterLock(JdbcClient jdbc) {
        assertThat(jdbc.sql("""
                        SELECT EXISTS (
                            SELECT 1
                              FROM pg_locks
                             WHERE locktype = 'advisory'
                               AND pid = pg_backend_pid()
                               AND granted
                               AND mode = 'ExclusiveLock'
                        )
                        """).query(Boolean.class).single())
                .as("projection loader runs after acquiring the PostgreSQL writer lock")
                .isTrue();
    }

    private static void assertCompleteState(
            JdbcClient jdbc,
            PublicBankSnapshotMaintenancePort.CommitResult result,
            long metrics,
            long system,
            long user,
            long viewers
    ) {
        State state = state(jdbc);
        assertThat(state.status()).isEqualTo("complete");
        assertThat(state.generation()).isEqualTo(result.generation());
        assertThat(state.projectionDigest()).isEqualTo(result.projectionDigest());
        assertThat(state.metricsCount()).isEqualTo(metrics);
        assertThat(state.systemCount()).isEqualTo(system);
        assertThat(state.userPublicCount()).isEqualTo(user);
        assertThat(state.viewerCount()).isEqualTo(viewers);
        assertThat(jdbc.sql("""
                        SELECT COUNT(*)
                          FROM public_bank_plaza_metrics
                         WHERE snapshot_generation <> :generation
                            OR projection_digest <> :digest
                        """)
                .param("generation", result.generation())
                .param("digest", result.projectionDigest())
                .query(Long.class)
                .single()).isZero();
        assertThat(jdbc.sql("""
                        SELECT COUNT(*)
                          FROM public_bank_plaza_viewer_state
                         WHERE snapshot_generation <> :generation
                            OR projection_digest <> :digest
                        """)
                .param("generation", result.generation())
                .param("digest", result.projectionDigest())
                .query(Long.class)
                .single()).isZero();
    }

    private static void assertVisibleName(
            PublicBankSnapshotQueryPort query,
            PublicBankRef reference,
            String name
    ) {
        var result = query.detail(reference, OptionalLong.empty());
        assertThat(result.snapshot().structurallyComplete()).as(result.snapshot().toString())
                .isTrue();
        assertThat(result.data()).isPresent().get().satisfies(detail ->
                assertThat(detail.card().name()).isEqualTo(name));
    }

    private static PublicBankProjectionBatch batch(
            String highWatermark,
            int step,
            String systemName,
            String userName
    ) {
        return new PublicBankProjectionBatch(
                commit(highWatermark, step),
                List.of(metric(SYSTEM, systemName, 5201), metric(USER, userName, 5202)),
                List.of(
                        new PublicBankViewerProjection(
                                7101, SYSTEM, true, false, BASE_TIME.plusSeconds(step)),
                        new PublicBankViewerProjection(
                                7102, USER, false, true, BASE_TIME.plusSeconds(step))));
    }

    private static PublicBankProjectionBatch invalidForeignKeyBatch(int step) {
        return new PublicBankProjectionBatch(
                commit("invalid-fk", step),
                List.of(metric(SYSTEM, "Invalid board", 999_999)),
                List.of());
    }

    private static PublicBankSnapshotCommit commit(String highWatermark, int step) {
        return new PublicBankSnapshotCommit(
                BASE_TIME.plusSeconds(step), 1, "maintenance-it:" + highWatermark);
    }

    private static PublicBankMetricProjection metric(
            PublicBankRef reference,
            String name,
            Integer boardId
    ) {
        boolean user = reference.source() == PublicBankSource.USER_PUBLIC;
        return new PublicBankMetricProjection(
                reference,
                name,
                "maintenance integration fixture",
                null,
                user ? 7201L : null,
                user ? "maintenance-owner" : "系统题库",
                null,
                10,
                boardId,
                true,
                5,
                LocalDateTime.of(2026, 7, 16, 11, 0),
                LocalDateTime.of(2026, 7, 16, 11, 30),
                3,
                2,
                3,
                4,
                5,
                2,
                3,
                12.5,
                8.5,
                1012.5,
                "free",
                "",
                user,
                user ? 2 : 0);
    }

    private static String boardName(JdbcClient jdbc, long boardId) {
        return jdbc.sql("SELECT name FROM plaza_boards WHERE id = :boardId")
                .param("boardId", boardId)
                .query(String.class)
                .single();
    }

    private static State state(JdbcClient jdbc) {
        return jdbc.sql("""
                        SELECT status,
                               generation,
                               projection_digest,
                               metrics_count,
                               system_count,
                               user_public_count,
                               viewer_state_count
                          FROM public_bank_plaza_snapshot_state
                         WHERE snapshot_name = 'public-bank-plaza'
                        """)
                .query((row, rowNumber) -> new State(
                        row.getString("status"),
                        row.getLong("generation"),
                        row.getString("projection_digest"),
                        row.getLong("metrics_count"),
                        row.getLong("system_count"),
                        row.getLong("user_public_count"),
                        row.getLong("viewer_state_count")))
                .single();
    }

    private static String fingerprint(JdbcClient jdbc) {
        return jdbc.sql("""
                        SELECT jsonb_build_object(
                            'state', (SELECT to_jsonb(s)
                                        FROM public_bank_plaza_snapshot_state s),
                            'metrics', (SELECT COALESCE(jsonb_agg(to_jsonb(m)
                                ORDER BY source_type, source_id), '[]'::jsonb)
                                FROM public_bank_plaza_metrics m),
                            'viewers', (SELECT COALESCE(jsonb_agg(to_jsonb(v)
                                ORDER BY identity_id, source_type, source_id), '[]'::jsonb)
                                FROM public_bank_plaza_viewer_state v),
                            'boards', (SELECT COALESCE(jsonb_agg(to_jsonb(b)
                                ORDER BY id), '[]'::jsonb)
                                FROM plaza_boards b)
                        )::text
                        """).query(String.class).single();
    }

    private static <T> T inTransaction(
            PlatformTransactionManager transactions,
            Supplier<T> work
    ) {
        return new TransactionTemplate(transactions).execute(status -> work.get());
    }

    private record State(
            String status,
            long generation,
            String projectionDigest,
            long metricsCount,
            long systemCount,
            long userPublicCount,
            long viewerCount
    ) {}
}
