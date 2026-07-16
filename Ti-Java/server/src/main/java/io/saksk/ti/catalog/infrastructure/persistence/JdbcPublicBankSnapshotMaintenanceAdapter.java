package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotMaintenancePort;
import io.saksk.ti.catalog.domain.PublicBankMetricProjection;
import io.saksk.ti.catalog.domain.PublicBankProjectionBatch;
import io.saksk.ti.catalog.domain.PublicBankSnapshotCommit;
import io.saksk.ti.catalog.domain.PublicBankViewerProjection;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayDeque;
import java.util.Collections;
import java.util.HexFormat;
import java.util.IdentityHashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.RowCallbackHandler;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

/** PostgreSQL-finalized single-writer implementation of the snapshot maintenance boundary. */
@Repository
class JdbcPublicBankSnapshotMaintenanceAdapter
        implements PublicBankSnapshotMaintenancePort {

    private static final Logger LOGGER =
            LoggerFactory.getLogger(JdbcPublicBankSnapshotMaintenanceAdapter.class);
    private static final String SNAPSHOT_NAME = "public-bank-plaza";
    private static final long WRITER_LOCK_KEY = 0x54495055424C4943L;
    private static final String PROVISIONAL_DIGEST = "0".repeat(64);
    private static final ZoneId LEGACY_LOCAL_ZONE = ZoneId.of("Asia/Shanghai");
    private static final int MAX_REPLACE_ATTEMPTS = 3;
    private static final Set<String> RETRYABLE_POSTGRES_SQL_STATES =
            Set.of("40001", "40P01");

    private static final String METRIC_INSERT = """
            INSERT INTO public_bank_plaza_metrics (
                source_type, source_id, name, description, cover_image,
                owner_id, owner_label, owner_avatar, question_count_total,
                plaza_board_id, is_featured, featured_weight, published_at,
                last_activity_at, join_count_total, join_users_7d, join_users_30d,
                answer_count_7d, answer_count_30d, answer_users_7d,
                answer_users_30d, hot_score, active_score, recommended_score,
                join_mode, join_note, allow_copy, share_count,
                snapshot_generation, projection_digest, updated_at
            ) VALUES (
                :sourceType, :sourceId, :name, :description, :coverImage,
                :ownerId, :ownerLabel, :ownerAvatar, :questionCountTotal,
                :boardId, :featured, :featuredWeight, :publishedAt,
                :lastActivityAt, :joinCountTotal, :joinUsers7d, :joinUsers30d,
                :answerCount7d, :answerCount30d, :answerUsers7d,
                :answerUsers30d, :hotScore, :activeScore, :recommendedScore,
                :joinMode, :joinNote, :allowCopy, :shareCount,
                :generation, :projectionDigest, :updatedAt
            )
            """;

    private static final String VIEWER_INSERT = """
            INSERT INTO public_bank_plaza_viewer_state (
                identity_id, source_type, source_id, has_public, has_shared,
                last_activity_at, snapshot_generation, projection_digest, updated_at
            ) VALUES (
                :identityId, :sourceType, :sourceId, :hasPublic, :hasShared,
                :lastActivityAt, :generation, :projectionDigest, :updatedAt
            )
            """;

    private static final String METRIC_DIGEST_ROWS = """
            SELECT jsonb_build_array(
                       source_type, source_id, name, description, cover_image,
                       owner_id, owner_label, owner_avatar, question_count_total,
                       plaza_board_id, is_featured, featured_weight,
                       to_char(published_at, 'YYYY-MM-DD"T"HH24:MI:SS.US'),
                       to_char(last_activity_at, 'YYYY-MM-DD"T"HH24:MI:SS.US'),
                       join_count_total, join_users_7d, join_users_30d,
                       answer_count_7d, answer_count_30d, answer_users_7d,
                       answer_users_30d, hot_score, active_score, recommended_score,
                       join_mode, join_note, allow_copy, share_count
                   )::text AS canonical_row
              FROM public_bank_plaza_metrics
             ORDER BY source_type, source_id
            """;

    private static final String VIEWER_DIGEST_ROWS = """
            SELECT jsonb_build_array(
                       identity_id, source_type, source_id, has_public, has_shared,
                       to_char(last_activity_at AT TIME ZONE 'UTC',
                               'YYYY-MM-DD"T"HH24:MI:SS.US')
                   )::text AS canonical_row
              FROM public_bank_plaza_viewer_state
             ORDER BY identity_id, source_type, source_id
            """;

    private final JdbcClient jdbc;
    private final TransactionTemplate replaceTransaction;

    JdbcPublicBankSnapshotMaintenanceAdapter(
            JdbcClient jdbc,
            PlatformTransactionManager transactions
    ) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
        this.replaceTransaction = new TransactionTemplate(
                Objects.requireNonNull(transactions, "transactions"));
        this.replaceTransaction.setName("public-bank-snapshot-replace");
        this.replaceTransaction.setPropagationBehavior(
                TransactionDefinition.PROPAGATION_REQUIRES_NEW);
        this.replaceTransaction.setIsolationLevel(
                TransactionDefinition.ISOLATION_REPEATABLE_READ);
    }

    @Override
    public CommitResult replace(Supplier<PublicBankProjectionBatch> projectionLoader) {
        Objects.requireNonNull(projectionLoader, "projectionLoader");
        return executeReplaceWithRetry(() -> {
            acquireWriterLock();
            PublicBankProjectionBatch projection = Objects.requireNonNull(
                    projectionLoader.get(), "projectionLoader result");
            return replaceLocked(projection);
        });
    }

    @Override
    public CommitResult replace(PublicBankProjectionBatch projection) {
        Objects.requireNonNull(projection, "projection");
        return executeReplaceWithRetry(() -> {
            acquireWriterLock();
            return replaceLocked(projection);
        });
    }

    private CommitResult executeReplaceWithRetry(Supplier<CommitResult> attemptWork) {
        for (int attempt = 1; attempt <= MAX_REPLACE_ATTEMPTS; attempt++) {
            try {
                return Objects.requireNonNull(
                        replaceTransaction.execute(status -> attemptWork.get()),
                        "public-bank replacement transaction result");
            } catch (RuntimeException exception) {
                if (attempt == MAX_REPLACE_ATTEMPTS
                        || !isRetryablePostgresConcurrencyFailure(exception)) {
                    throw exception;
                }
                LOGGER.warn(
                        "Retrying public-bank snapshot replacement after PostgreSQL "
                                + "concurrency failure attempt={} maxAttempts={} type={}",
                        attempt,
                        MAX_REPLACE_ATTEMPTS,
                        exception.getClass().getName());
            }
        }
        throw new IllegalStateException("Public-bank replacement retry loop exhausted");
    }

    static boolean isRetryablePostgresConcurrencyFailure(Throwable failure) {
        Objects.requireNonNull(failure, "failure");
        ArrayDeque<Throwable> pending = new ArrayDeque<>();
        Set<Throwable> visited = Collections.newSetFromMap(new IdentityHashMap<>());
        pending.add(failure);
        while (!pending.isEmpty()) {
            Throwable candidate = pending.removeFirst();
            if (!visited.add(candidate)) {
                continue;
            }
            if (candidate instanceof SQLException sqlException) {
                if (RETRYABLE_POSTGRES_SQL_STATES.contains(sqlException.getSQLState())) {
                    return true;
                }
                if (sqlException.getNextException() != null) {
                    pending.addLast(sqlException.getNextException());
                }
            }
            if (candidate.getCause() != null) {
                pending.addLast(candidate.getCause());
            }
        }
        return false;
    }

    private CommitResult replaceLocked(PublicBankProjectionBatch projection) {
        long generation = beginGeneration(projection.commit());

        jdbc.sql("DELETE FROM public_bank_plaza_viewer_state").update();
        jdbc.sql("DELETE FROM public_bank_plaza_metrics").update();
        for (PublicBankMetricProjection metric : projection.metrics()) {
            insertMetric(metric, projection.commit(), generation);
        }
        for (PublicBankViewerProjection viewer : projection.viewers()) {
            insertViewer(viewer, projection.commit(), generation);
        }

        String digest = calculateProjectionDigest();
        applyGenerationDigest(generation, digest, projection.commit());
        ProjectionCounts counts = verifyProjection(generation, digest);
        completeGeneration(generation, digest, projection.commit(), counts);
        return new CommitResult(Outcome.COMMITTED, generation, digest);
    }

    @Override
    @Transactional
    public CommitResult tombstone(PublicBankRef reference, PublicBankSnapshotCommit commit) {
        Objects.requireNonNull(reference, "reference");
        Objects.requireNonNull(commit, "commit");
        acquireWriterLock();

        CurrentSnapshot current = requireCurrentSnapshot();
        boolean visible = jdbc.sql("""
                        SELECT EXISTS (
                            SELECT 1 FROM public_bank_plaza_metrics
                             WHERE source_type = :sourceType AND source_id = :sourceId
                        )
                        """)
                .param("sourceType", databaseSourceType(reference.source()))
                .param("sourceId", reference.id())
                .query(Boolean.class)
                .single();
        if (!visible) {
            return new CommitResult(
                    Outcome.UNCHANGED, current.generation(), current.projectionDigest());
        }

        long generation = beginGeneration(commit);
        jdbc.sql("""
                        DELETE FROM public_bank_plaza_viewer_state
                         WHERE source_type = :sourceType AND source_id = :sourceId
                        """)
                .param("sourceType", databaseSourceType(reference.source()))
                .param("sourceId", reference.id())
                .update();
        int removed = jdbc.sql("""
                        DELETE FROM public_bank_plaza_metrics
                         WHERE source_type = :sourceType AND source_id = :sourceId
                        """)
                .param("sourceType", databaseSourceType(reference.source()))
                .param("sourceId", reference.id())
                .update();
        if (removed != 1) {
            throw new IllegalStateException("Visible public-bank tombstone removed no metric row");
        }

        String digest = calculateProjectionDigest();
        applyGenerationDigest(generation, digest, commit);
        ProjectionCounts counts = verifyProjection(generation, digest);
        completeGeneration(generation, digest, commit, counts);
        return new CommitResult(Outcome.COMMITTED, generation, digest);
    }

    private void acquireWriterLock() {
        Integer acquired = jdbc.sql("SELECT pg_advisory_xact_lock(:lockKey)")
                .param("lockKey", WRITER_LOCK_KEY)
                .query((row, rowNumber) -> 1)
                .single();
        if (acquired != 1) {
            throw new IllegalStateException("PostgreSQL public-bank writer lock was not acquired");
        }
    }

    private long beginGeneration(PublicBankSnapshotCommit commit) {
        long generation = jdbc.sql("""
                        SELECT COALESCE(MAX(generation), 0) + 1
                          FROM public_bank_plaza_snapshot_state
                         WHERE snapshot_name = :snapshotName
                        """)
                .param("snapshotName", SNAPSHOT_NAME)
                .query(Long.class)
                .single();
        if (generation <= 0) {
            throw new IllegalStateException("Public-bank snapshot generation overflow");
        }

        int changed = jdbc.sql("""
                        INSERT INTO public_bank_plaza_snapshot_state (
                            snapshot_name, status, last_success_at, metrics_count,
                            system_count, user_public_count, viewer_state_count,
                            projection_digest, projector_schema_version,
                            source_high_watermark, generation, updated_at
                        ) VALUES (
                            :snapshotName, 'building', NULL, 0, 0, 0, 0,
                            :projectionDigest, :schemaVersion, :sourceHighWatermark,
                            :generation, :updatedAt
                        )
                        ON CONFLICT (snapshot_name) DO UPDATE SET
                            status = 'building',
                            projection_digest = EXCLUDED.projection_digest,
                            projector_schema_version = EXCLUDED.projector_schema_version,
                            source_high_watermark = EXCLUDED.source_high_watermark,
                            generation = EXCLUDED.generation,
                            updated_at = EXCLUDED.updated_at
                        """)
                .param("snapshotName", SNAPSHOT_NAME)
                .param("projectionDigest", PROVISIONAL_DIGEST)
                .param("schemaVersion", commit.projectorSchemaVersion())
                .param("sourceHighWatermark", commit.sourceHighWatermark())
                .param("generation", generation)
                .param("updatedAt", utc(commit))
                .update();
        if (changed != 1) {
            throw new IllegalStateException("Public-bank building marker was not written");
        }
        return generation;
    }

    private void insertMetric(
            PublicBankMetricProjection metric,
            PublicBankSnapshotCommit commit,
            long generation
    ) {
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("sourceType", databaseSourceType(metric.reference().source()));
        parameters.put("sourceId", metric.reference().id());
        parameters.put("name", metric.name());
        parameters.put("description", metric.description());
        parameters.put("coverImage", metric.coverImage());
        parameters.put("ownerId", metric.ownerId());
        parameters.put("ownerLabel", metric.ownerLabel());
        parameters.put("ownerAvatar", metric.ownerAvatar());
        parameters.put("questionCountTotal", metric.questionCountTotal());
        parameters.put("boardId", metric.boardId());
        parameters.put("featured", metric.featured());
        parameters.put("featuredWeight", metric.featuredWeight());
        parameters.put("publishedAt", metric.publishedAt());
        parameters.put("lastActivityAt", metric.lastActivityAt());
        parameters.put("joinCountTotal", metric.joinCountTotal());
        parameters.put("joinUsers7d", metric.joinUsers7d());
        parameters.put("joinUsers30d", metric.joinUsers30d());
        parameters.put("answerCount7d", metric.answerCount7d());
        parameters.put("answerCount30d", metric.answerCount30d());
        parameters.put("answerUsers7d", metric.answerUsers7d());
        parameters.put("answerUsers30d", metric.answerUsers30d());
        parameters.put("hotScore", metric.hotScore());
        parameters.put("activeScore", metric.activeScore());
        parameters.put("recommendedScore", metric.recommendedScore());
        parameters.put("joinMode", metric.joinMode());
        parameters.put("joinNote", metric.joinNote());
        parameters.put("allowCopy", metric.allowCopy());
        parameters.put("shareCount", metric.shareCount());
        parameters.put("generation", generation);
        parameters.put("projectionDigest", PROVISIONAL_DIGEST);
        parameters.put("updatedAt", legacyLocal(commit));
        if (jdbc.sql(METRIC_INSERT).params(parameters).update() != 1) {
            throw new IllegalStateException("Public-bank metric projection insert failed");
        }
    }

    private void insertViewer(
            PublicBankViewerProjection viewer,
            PublicBankSnapshotCommit commit,
            long generation
    ) {
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("identityId", viewer.identityId());
        parameters.put("sourceType", databaseSourceType(viewer.reference().source()));
        parameters.put("sourceId", viewer.reference().id());
        parameters.put("hasPublic", viewer.hasPublic());
        parameters.put("hasShared", viewer.hasShared());
        parameters.put("lastActivityAt", viewer.lastActivityAt() == null
                ? null
                : OffsetDateTime.ofInstant(viewer.lastActivityAt(), ZoneOffset.UTC));
        parameters.put("generation", generation);
        parameters.put("projectionDigest", PROVISIONAL_DIGEST);
        parameters.put("updatedAt", utc(commit));
        if (jdbc.sql(VIEWER_INSERT).params(parameters).update() != 1) {
            throw new IllegalStateException("Public-bank viewer projection insert failed");
        }
    }

    private String calculateProjectionDigest() {
        MessageDigest digest = sha256();
        updateFrame(digest, "ti-public-bank-projection-v1");
        updateFrame(digest, "metrics");
        jdbc.sql(METRIC_DIGEST_ROWS).query((RowCallbackHandler) row ->
                updateFrame(digest, row.getString("canonical_row")));
        updateFrame(digest, "viewers");
        jdbc.sql(VIEWER_DIGEST_ROWS).query((RowCallbackHandler) row ->
                updateFrame(digest, row.getString("canonical_row")));
        return HexFormat.of().formatHex(digest.digest());
    }

    private void applyGenerationDigest(
            long generation,
            String digest,
            PublicBankSnapshotCommit commit
    ) {
        jdbc.sql("""
                        UPDATE public_bank_plaza_metrics
                           SET snapshot_generation = :generation,
                               projection_digest = :projectionDigest,
                               updated_at = :updatedAt
                        """)
                .param("generation", generation)
                .param("projectionDigest", digest)
                .param("updatedAt", legacyLocal(commit))
                .update();
        jdbc.sql("""
                        UPDATE public_bank_plaza_viewer_state
                           SET snapshot_generation = :generation,
                               projection_digest = :projectionDigest,
                               updated_at = :updatedAt
                        """)
                .param("generation", generation)
                .param("projectionDigest", digest)
                .param("updatedAt", utc(commit))
                .update();
    }

    private ProjectionCounts verifyProjection(long generation, String digest) {
        return jdbc.sql("""
                        SELECT COUNT(*) AS metrics_count,
                               COUNT(*) FILTER (WHERE source_type = 'system') AS system_count,
                               COUNT(*) FILTER (WHERE source_type = 'user_public')
                                   AS user_public_count,
                               COUNT(*) FILTER (
                                   WHERE snapshot_generation <> :generation
                                      OR projection_digest <> :projectionDigest
                               ) AS invalid_metric_count,
                               (SELECT COUNT(*)
                                  FROM public_bank_plaza_viewer_state) AS viewer_count,
                               (SELECT COUNT(*)
                                  FROM public_bank_plaza_viewer_state
                                 WHERE snapshot_generation <> :generation
                                    OR projection_digest <> :projectionDigest)
                                   AS invalid_viewer_count
                          FROM public_bank_plaza_metrics
                        """)
                .param("generation", generation)
                .param("projectionDigest", digest)
                .query((row, rowNumber) -> new ProjectionCounts(
                        row.getLong("metrics_count"),
                        row.getLong("system_count"),
                        row.getLong("user_public_count"),
                        row.getLong("viewer_count"),
                        row.getLong("invalid_metric_count"),
                        row.getLong("invalid_viewer_count")))
                .single()
                .verified();
    }

    private void completeGeneration(
            long generation,
            String digest,
            PublicBankSnapshotCommit commit,
            ProjectionCounts counts
    ) {
        int changed = jdbc.sql("""
                        UPDATE public_bank_plaza_snapshot_state
                           SET status = 'complete',
                               last_success_at = :completedAt,
                               metrics_count = :metricsCount,
                               system_count = :systemCount,
                               user_public_count = :userPublicCount,
                               viewer_state_count = :viewerCount,
                               projection_digest = :projectionDigest,
                               projector_schema_version = :schemaVersion,
                               source_high_watermark = :sourceHighWatermark,
                               updated_at = :completedAt
                         WHERE snapshot_name = :snapshotName
                           AND status = 'building'
                           AND generation = :generation
                        """)
                .param("completedAt", utc(commit))
                .param("metricsCount", counts.metricsCount())
                .param("systemCount", counts.systemCount())
                .param("userPublicCount", counts.userPublicCount())
                .param("viewerCount", counts.viewerCount())
                .param("projectionDigest", digest)
                .param("schemaVersion", commit.projectorSchemaVersion())
                .param("sourceHighWatermark", commit.sourceHighWatermark())
                .param("snapshotName", SNAPSHOT_NAME)
                .param("generation", generation)
                .update();
        if (changed != 1) {
            throw new IllegalStateException("Public-bank complete marker was not written");
        }
    }

    private CurrentSnapshot requireCurrentSnapshot() {
        Optional<CurrentSnapshot> current = jdbc.sql("""
                        SELECT generation, projection_digest
                          FROM public_bank_plaza_snapshot_state
                         WHERE snapshot_name = :snapshotName AND status = 'complete'
                         FOR UPDATE
                        """)
                .param("snapshotName", SNAPSHOT_NAME)
                .query((row, rowNumber) -> new CurrentSnapshot(
                        row.getLong("generation"), row.getString("projection_digest")))
                .optional();
        return current.orElseThrow(() ->
                new IllegalStateException("No complete public-bank snapshot to tombstone"));
    }

    private static OffsetDateTime utc(PublicBankSnapshotCommit commit) {
        return OffsetDateTime.ofInstant(commit.completedAt(), ZoneOffset.UTC);
    }

    private static java.time.LocalDateTime legacyLocal(PublicBankSnapshotCommit commit) {
        return commit.completedAt().atZone(LEGACY_LOCAL_ZONE).toLocalDateTime();
    }

    private static String databaseSourceType(PublicBankSource source) {
        return switch (Objects.requireNonNull(source, "source")) {
            case SYSTEM -> "system";
            case USER_PUBLIC -> "user_public";
        };
    }

    private static MessageDigest sha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static void updateFrame(MessageDigest digest, String value) {
        byte[] bytes = Objects.requireNonNull(value, "digest frame")
                .getBytes(StandardCharsets.UTF_8);
        digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(bytes.length).array());
        digest.update(bytes);
    }

    private record CurrentSnapshot(long generation, String projectionDigest) {}

    private record ProjectionCounts(
            long metricsCount,
            long systemCount,
            long userPublicCount,
            long viewerCount,
            long invalidMetricCount,
            long invalidViewerCount
    ) {

        ProjectionCounts verified() {
            if (metricsCount < 0
                    || systemCount < 0
                    || userPublicCount < 0
                    || viewerCount < 0
                    || metricsCount != systemCount + userPublicCount
                    || invalidMetricCount != 0
                    || invalidViewerCount != 0) {
                throw new IllegalStateException("Public-bank projection verification failed");
            }
            return this;
        }
    }
}
