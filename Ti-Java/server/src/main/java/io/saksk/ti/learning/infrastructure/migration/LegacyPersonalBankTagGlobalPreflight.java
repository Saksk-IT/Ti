package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.KeyAnalysis;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.KeyKind;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseFailure;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseResult;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ApplyPrerequisiteBlocker;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.GlobalFailure;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.GlobalFailureCode;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.KeyClassification;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.ReportingGroup;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.RowOutcome;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.SourceRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.Status;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import javax.sql.DataSource;

/**
 * Explicit, production-side dry-run preflight for legacy personal-bank tags.
 *
 * <p>The class is deliberately not a Spring component, runner, scheduled task,
 * or HTTP endpoint. Every SQL statement is read-only (apart from transaction
 * control and a session advisory lock), and the returned report never exposes
 * a legacy key, payload, tag value, database name, or database user.</p>
 *
 * <p>This node is not an apply operator. Even a clean data report remains
 * apply-ineligible until a write freeze, a durable marker, and an explicit
 * operator are implemented and independently accepted.</p>
 */
public final class LegacyPersonalBankTagGlobalPreflight {

    private static final long ADVISORY_LOCK_KEY = 0x5449503443544147L;
    private static final int FETCH_SIZE = 256;
    private static final int SOURCE_FETCH_SIZE = 16;
    static final int MAX_RESERVED_SOURCE_ROWS = 100_000;
    static final long MAX_RESERVED_SOURCE_UTF8_BYTES = 256L * 1024L * 1024L;

    static final String TRY_LOCK_SQL =
            "SELECT pg_catalog.pg_backend_pid(), "
                    + "pg_catalog.pg_try_advisory_lock(?)";
    static final String UNLOCK_SQL =
            "SELECT pg_catalog.pg_advisory_unlock(?)";
    static final String CONNECTION_METADATA_SQL = """
            SELECT pg_catalog.current_database()::text,
                   current_user::text,
                   pg_catalog.current_setting('server_version')::text
            """;
    static final String SET_TRANSACTION_SQL =
            "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE READ ONLY DEFERRABLE";
    static final String TRANSACTION_FACTS_SQL = """
            SELECT pg_catalog.current_setting('transaction_isolation')::text,
                   pg_catalog.current_setting('transaction_read_only')::text,
                   pg_catalog.current_setting('transaction_deferrable')::text
            """;
    static final String DISCOVER_RESERVED_SOURCE_SQL = """
            SELECT id,
                   user_id,
                   p_key,
                   CASE
                       WHEN data IS NULL
                            OR pg_catalog.octet_length(
                                pg_catalog.convert_to(data, 'UTF8')) <= ?
                       THEN data
                       ELSE NULL
                   END AS bounded_data,
                   pg_catalog.octet_length(
                       pg_catalog.convert_to(data, 'UTF8')) AS data_utf8_bytes
            FROM public.user_progress
            WHERE p_key LIKE 'bank_%_tags'
            ORDER BY id
            """;
    static final String TARGET_ROWS_SQL = """
            SELECT question_id, tag
            FROM public.user_question_tag_items
            WHERE user_id = ?
              AND scope = 'user_bank'
              AND scope_id = ?
            ORDER BY question_id, tag
            """;

    private final DataSource dataSource;
    private final PersonalBankQuestionFactsApi memberships;
    private final Clock clock;
    private final long advisoryLockKey;

    public LegacyPersonalBankTagGlobalPreflight(
            DataSource dataSource,
            PersonalBankQuestionFactsApi memberships
    ) {
        this(dataSource, memberships, Clock.systemUTC(), ADVISORY_LOCK_KEY);
    }

    LegacyPersonalBankTagGlobalPreflight(
            DataSource dataSource,
            PersonalBankQuestionFactsApi memberships,
            Clock clock,
            long advisoryLockKey
    ) {
        this.dataSource = Objects.requireNonNull(dataSource, "dataSource");
        this.memberships = Objects.requireNonNull(memberships, "memberships");
        this.clock = Objects.requireNonNull(clock, "clock");
        this.advisoryLockKey = advisoryLockKey;
    }

    public static long advisoryLockKey() {
        return ADVISORY_LOCK_KEY;
    }

    /**
     * Runs one complete dry-run and always reduces ordinary connection/JDBC
     * failures to a sanitized global report. VM errors still propagate.
     */
    public LegacyPersonalBankTagPreflightReport run() {
        MutableRun run = new MutableRun(clock.instant(), advisoryLockKey);
        Connection connection = null;
        boolean lockHeld = false;
        boolean transactionOpen = false;
        GlobalFailureCode stage = GlobalFailureCode.CONNECTION_ACQUISITION_FAILED;

        try {
            connection = dataSource.getConnection();
            stage = GlobalFailureCode.CONNECTION_SETUP_FAILED;
            connection.setAutoCommit(true);

            stage = GlobalFailureCode.ADVISORY_LOCK_ACQUISITION_FAILED;
            LockAttempt lock = tryLock(connection, advisoryLockKey);
            run.backendProcessId = Optional.of(lock.backendProcessId());
            if (!lock.acquired()) {
                run.requestedStatus = Status.LOCK_BUSY;
            } else {
                lockHeld = true;
                stage = GlobalFailureCode.CONNECTION_METADATA_READ_FAILED;
                readConnectionMetadata(connection, run);

                stage = GlobalFailureCode.TRANSACTION_SETUP_FAILED;
                connection.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
                connection.setReadOnly(true);
                connection.setAutoCommit(false);
                transactionOpen = true;
                try (Statement statement = connection.createStatement()) {
                    statement.execute(SET_TRANSACTION_SQL);
                }
                readAndVerifyTransactionFacts(connection, run);

                stage = GlobalFailureCode.SOURCE_SCAN_FAILED;
                List<SourceSnapshot> sources = discoverSources(connection);
                run.recordDiscovery(sources);

                stage = GlobalFailureCode.CLASSIFICATION_READ_FAILED;
                run.rows.addAll(classifyAll(connection, sources));

                stage = GlobalFailureCode.READ_ONLY_COMMIT_FAILED;
                connection.commit();
                transactionOpen = false;
                run.requestedStatus = Status.COMPLETED;
            }
        } catch (SQLException | RuntimeException failure) {
            run.addGlobalFailure(stage, failure);
        } finally {
            if (connection != null && transactionOpen) {
                try {
                    connection.rollback();
                    transactionOpen = false;
                } catch (SQLException | RuntimeException rollbackFailure) {
                    run.addGlobalFailure(
                            GlobalFailureCode.READ_ONLY_ROLLBACK_FAILED,
                            rollbackFailure);
                }
            }
            if (connection != null && lockHeld) {
                try {
                    connection.setAutoCommit(true);
                    if (!unlock(connection, advisoryLockKey)) {
                        run.addGlobalFailure(
                                GlobalFailureCode.ADVISORY_UNLOCK_REJECTED,
                                null);
                    }
                } catch (SQLException | RuntimeException unlockFailure) {
                    run.addGlobalFailure(
                            GlobalFailureCode.ADVISORY_UNLOCK_FAILED,
                            unlockFailure);
                }
            }
            if (connection != null) {
                try {
                    connection.close();
                } catch (SQLException | RuntimeException closeFailure) {
                    run.addGlobalFailure(
                            GlobalFailureCode.CONNECTION_CLOSE_FAILED,
                            closeFailure);
                }
            }
        }

        return run.toReport(clock.instant());
    }

    /** Exact read/control statement surface; contains no DDL or business DML. */
    static List<String> statementSurface() {
        return List.of(
                TRY_LOCK_SQL,
                CONNECTION_METADATA_SQL,
                SET_TRANSACTION_SQL,
                TRANSACTION_FACTS_SQL,
                DISCOVER_RESERVED_SOURCE_SQL,
                TARGET_ROWS_SQL,
                UNLOCK_SQL);
    }

    private List<SourceRow> classifyAll(
            Connection connection,
            List<SourceSnapshot> sources
    ) throws SQLException {
        Set<Long> collisionRows = normalizedCollisionRows(sources);
        List<SourceRow> reports = new ArrayList<>(sources.size());
        for (SourceSnapshot source : sources) {
            reports.add(classifyOne(connection, source, collisionRows.contains(source.id())));
        }
        return List.copyOf(reports);
    }

    private SourceRow classifyOne(
            Connection connection,
            SourceSnapshot source,
            boolean normalizedCollision
    ) throws SQLException {
        RowReportBuilder report = RowReportBuilder.forSource(source);
        if (normalizedCollision) {
            return report.finish(
                    RowOutcome.NORMALIZED_BANK_COLLISION,
                    "NORMALIZED_BANK_COLLISION");
        }
        if (!source.keyAnalysis().canonical()) {
            return report.finish(RowOutcome.INVALID_KEY, source.keyAnalysis().failure().name());
        }
        if (source.payloadTooLarge()) {
            return report.finish(RowOutcome.INVALID_DATA, "PAYLOAD_LIMIT_EXCEEDED");
        }

        int bankId = source.keyAnalysis().normalizedBankId().orElseThrow();
        report.bankId = Optional.of(bankId);
        ParseResult plan;
        try {
            plan = LegacyPersonalBankTagPreflightParser.parse(source.data());
        } catch (ParseFailure invalidPayload) {
            return report.finish(RowOutcome.INVALID_DATA, invalidPayload.code().name());
        }
        report.recordPlan(plan);

        TargetSnapshot target = readTarget(connection, source.userId(), bankId);
        report.recordTarget(target);

        TreeSet<Integer> requestedQuestionIds = new TreeSet<>();
        plan.rows().stream()
                .map(TagRow::questionId)
                .filter(questionId -> questionId > 0)
                .forEach(requestedQuestionIds::add);
        target.positiveQuestionIds().forEach(requestedQuestionIds::add);
        report.membershipRequestedQuestionCount = requestedQuestionIds.size();

        PersonalBankQuestionMembershipView membership;
        try {
            membership = Objects.requireNonNull(
                    memberships.inspectQuestionMembership(
                            bankId, List.copyOf(requestedQuestionIds)),
                    "membership result");
            if (membership.bankId() != bankId
                    || !requestedQuestionIds.containsAll(membership.existingQuestionIds())) {
                return report.finish(
                        RowOutcome.MEMBERSHIP_UNAVAILABLE,
                        "MEMBERSHIP_PROVIDER_CONTRACT_VIOLATION");
            }
        } catch (RuntimeException providerFailure) {
            return report.finish(
                    RowOutcome.MEMBERSHIP_UNAVAILABLE,
                    "MEMBERSHIP_PROVIDER_FAILURE");
        }
        report.membershipDigest = Optional.of(membership.membershipDigest());

        if (!membership.bankExists()) {
            return report.finish(RowOutcome.BANK_MISSING, "BANK_NOT_FOUND");
        }

        Set<Integer> existingQuestionIds = Set.copyOf(membership.existingQuestionIds());
        boolean sourceOrphan = plan.rows().stream()
                .map(TagRow::questionId)
                .filter(questionId -> questionId > 0)
                .anyMatch(questionId -> !existingQuestionIds.contains(questionId));
        if (sourceOrphan) {
            return report.finish(
                    RowOutcome.ORPHAN_QUESTION,
                    "SOURCE_QUESTION_OUTSIDE_BANK");
        }
        if (!target.structurallyValid()) {
            return report.finish(RowOutcome.TARGET_INVALID, target.failureCode());
        }
        if (target.positiveQuestionIds().stream()
                .anyMatch(questionId -> !existingQuestionIds.contains(questionId))) {
            return report.finish(
                    RowOutcome.TARGET_INVALID,
                    "TARGET_QUESTION_OUTSIDE_BANK");
        }

        if (!target.rows().isEmpty()) {
            if (!target.rows().containsAll(plan.rows())) {
                return report.finish(
                        RowOutcome.TARGET_CONFLICT,
                        "SOURCE_PLAN_NOT_SUBSET_OF_TARGET");
            }
            return report.finish(RowOutcome.TARGET_ALREADY_PRESENT, "NONE");
        }
        if (plan.rows().isEmpty()) {
            return report.finish(RowOutcome.EMPTY_NOOP, "NONE");
        }
        return report.finish(RowOutcome.MIGRATABLE, "NONE");
    }

    private static LockAttempt tryLock(Connection connection, long lockKey)
            throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(TRY_LOCK_SQL)) {
            statement.setLong(1, lockKey);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) {
                    throw new SQLException("advisory lock query returned no row");
                }
                return new LockAttempt(row.getInt(1), row.getBoolean(2));
            }
        }
    }

    private static boolean unlock(Connection connection, long lockKey) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(UNLOCK_SQL)) {
            statement.setLong(1, lockKey);
            try (ResultSet row = statement.executeQuery()) {
                return row.next() && row.getBoolean(1);
            }
        }
    }

    private static void readConnectionMetadata(Connection connection, MutableRun run)
            throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(CONNECTION_METADATA_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()) {
                throw new SQLException("connection metadata query returned no row");
            }
            String database = row.getString(1);
            String user = row.getString(2);
            run.databaseIdentityDigest = Optional.of(
                    LegacyPersonalBankTagPreflightParser.sha256(database + "\u0000" + user));
            run.serverVersion = Optional.ofNullable(row.getString(3));
        }
    }

    private static void readAndVerifyTransactionFacts(
            Connection connection,
            MutableRun run
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(TRANSACTION_FACTS_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()) {
                throw new SQLException("transaction facts query returned no row");
            }
            String isolation = row.getString(1);
            boolean readOnly = "on".equalsIgnoreCase(row.getString(2));
            boolean deferrable = "on".equalsIgnoreCase(row.getString(3));
            run.transactionIsolation = Optional.ofNullable(isolation);
            run.transactionReadOnly = readOnly;
            run.transactionDeferrable = deferrable;
            if (!"serializable".equalsIgnoreCase(isolation) || !readOnly || !deferrable) {
                throw new SQLException("required read-only transaction facts were not active");
            }
        }
    }

    private static List<SourceSnapshot> discoverSources(Connection connection)
            throws SQLException {
        List<SourceSnapshot> sources = new ArrayList<>();
        long observedPayloadBytes = 0L;
        try (PreparedStatement statement =
                     connection.prepareStatement(DISCOVER_RESERVED_SOURCE_SQL)) {
            statement.setFetchSize(SOURCE_FETCH_SIZE);
            statement.setInt(
                    1, LegacyPersonalBankTagPreflightParser.MAX_PAYLOAD_UTF8_BYTES);
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    if (sources.size() >= MAX_RESERVED_SOURCE_ROWS) {
                        throw new SQLException("reserved source row limit exceeded");
                    }
                    String key = row.getString("p_key");
                    Integer dataUtf8Bytes = row.getObject(
                            "data_utf8_bytes", Integer.class);
                    String data = row.getString("bounded_data");
                    if (key == null) {
                        throw new SQLException("reserved source key is null");
                    }
                    int sourceBytes = dataUtf8Bytes == null ? 0 : dataUtf8Bytes;
                    observedPayloadBytes = Math.addExact(
                            observedPayloadBytes, (long) sourceBytes);
                    if (observedPayloadBytes > MAX_RESERVED_SOURCE_UTF8_BYTES) {
                        throw new SQLException("reserved source byte limit exceeded");
                    }
                    boolean payloadTooLarge = sourceBytes
                            > LegacyPersonalBankTagPreflightParser.MAX_PAYLOAD_UTF8_BYTES;
                    sources.add(new SourceSnapshot(
                            row.getLong("id"),
                            row.getLong("user_id"),
                            key,
                            data,
                            sourceBytes,
                            payloadTooLarge,
                            LegacyPersonalBankTagPreflightParser.analyzeReservedKey(key)));
                }
            }
        }
        return List.copyOf(sources);
    }

    private static TargetSnapshot readTarget(
            Connection connection,
            long userId,
            int bankId
    ) throws SQLException {
        List<RawTargetRow> rawRows = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(TARGET_ROWS_SQL)) {
            statement.setLong(1, userId);
            statement.setInt(2, bankId);
            statement.setFetchSize(FETCH_SIZE);
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    rawRows.add(new RawTargetRow(
                            row.getObject("question_id", Integer.class),
                            row.getString("tag")));
                }
            }
        }

        List<TagRow> canonicalRows = new ArrayList<>();
        TreeSet<Integer> positiveQuestionIds = new TreeSet<>();
        String failureCode = "NONE";
        for (RawTargetRow raw : rawRows) {
            if (raw.questionId() == null || raw.questionId() < 0) {
                failureCode = "TARGET_QUESTION_ID_INVALID";
                continue;
            }
            if (!LegacyPersonalBankTagPreflightParser.isCanonicalTargetTag(raw.tag())) {
                failureCode = "TARGET_TAG_NOT_CANONICAL";
                continue;
            }
            TagRow canonical = new TagRow(raw.questionId(), raw.tag());
            canonicalRows.add(canonical);
            if (canonical.questionId() > 0) {
                positiveQuestionIds.add(canonical.questionId());
            }
        }
        canonicalRows.sort(Comparator.comparingInt(TagRow::questionId).thenComparing(TagRow::tag));
        return new TargetSnapshot(
                List.copyOf(canonicalRows),
                List.copyOf(positiveQuestionIds),
                digestRawTargetRows(rawRows),
                "NONE".equals(failureCode),
                failureCode,
                rawRows.size());
    }

    private static Set<Long> normalizedCollisionRows(List<SourceSnapshot> sources) {
        Map<CollisionIdentity, List<Long>> byIdentity = new HashMap<>();
        for (SourceSnapshot source : sources) {
            source.keyAnalysis().normalizedBankId().ifPresent(bankId ->
                    byIdentity.computeIfAbsent(
                                    new CollisionIdentity(source.userId(), bankId),
                                    ignored -> new ArrayList<>())
                            .add(source.id()));
        }
        Set<Long> collisions = new HashSet<>();
        byIdentity.values().stream()
                .filter(ids -> ids.size() > 1)
                .forEach(collisions::addAll);
        return Set.copyOf(collisions);
    }

    private static String digestRawTargetRows(List<RawTargetRow> rows) {
        MessageDigest digest = sha256Digest();
        rows.stream()
                .sorted(Comparator
                        .comparing(RawTargetRow::questionId,
                                Comparator.nullsFirst(Integer::compareTo))
                        .thenComparing(RawTargetRow::tag,
                                Comparator.nullsFirst(String::compareTo)))
                .forEach(row -> {
                    updateNullableInt(digest, row.questionId());
                    updateNullableString(digest, row.tag());
                });
        return HexFormat.of().formatHex(digest.digest());
    }

    private static void updateNullableInt(MessageDigest digest, Integer value) {
        digest.update((byte) (value == null ? 0 : 1));
        if (value != null) {
            digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(value).array());
        }
    }

    private static void updateNullableString(MessageDigest digest, String value) {
        digest.update((byte) (value == null ? 0 : 1));
        if (value != null) {
            byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
            digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(bytes.length).array());
            digest.update(bytes);
        }
    }

    private static MessageDigest sha256Digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }

    private record LockAttempt(int backendProcessId, boolean acquired) {
    }

    private record CollisionIdentity(long userId, int bankId) {
    }

    private record RawTargetRow(Integer questionId, String tag) {
    }

    private record TargetSnapshot(
            List<TagRow> rows,
            List<Integer> positiveQuestionIds,
            String digest,
            boolean structurallyValid,
            String failureCode,
            int rawRowCount
    ) {
    }

    private static final class SourceSnapshot {
        private final long id;
        private final long userId;
        private final String key;
        private final String data;
        private final int dataUtf8Bytes;
        private final boolean payloadTooLarge;
        private final KeyAnalysis keyAnalysis;

        private SourceSnapshot(
                long id,
                long userId,
                String key,
                String data,
                int dataUtf8Bytes,
                boolean payloadTooLarge,
                KeyAnalysis keyAnalysis
        ) {
            this.id = id;
            this.userId = userId;
            this.key = key;
            this.data = data;
            this.dataUtf8Bytes = dataUtf8Bytes;
            this.payloadTooLarge = payloadTooLarge;
            this.keyAnalysis = keyAnalysis;
            boolean exceedsPayloadLimit = dataUtf8Bytes
                    > LegacyPersonalBankTagPreflightParser.MAX_PAYLOAD_UTF8_BYTES;
            boolean boundedDataLengthMismatch = !payloadTooLarge
                    && data != null
                    && data.getBytes(StandardCharsets.UTF_8).length != dataUtf8Bytes;
            boolean nullPayloadLengthMismatch = !payloadTooLarge
                    && data == null
                    && dataUtf8Bytes != 0;
            if (dataUtf8Bytes < 0
                    || payloadTooLarge != exceedsPayloadLimit
                    || payloadTooLarge && data != null
                    || boundedDataLengthMismatch
                    || nullPayloadLengthMismatch) {
                throw new IllegalArgumentException("source payload bound is inconsistent");
            }
        }

        private long id() {
            return id;
        }

        private long userId() {
            return userId;
        }

        private String key() {
            return key;
        }

        private String data() {
            return data;
        }

        private int dataUtf8Bytes() {
            return dataUtf8Bytes;
        }

        private boolean payloadTooLarge() {
            return payloadTooLarge;
        }

        private KeyAnalysis keyAnalysis() {
            return keyAnalysis;
        }

        @Override
        public String toString() {
            return "SourceSnapshot[id=" + id + ",userId=" + userId + ",redacted=true]";
        }
    }

    private static final class RowReportBuilder {
        private final long sourceRowId;
        private final long userId;
        private final KeyClassification keyClassification;
        private Optional<Integer> bankId;
        private final String keyDigest;
        private final int keyBytes;
        private final String sourceDigest;
        private final int sourceBytes;
        private Optional<String> planDigest = Optional.empty();
        private int definitionCount;
        private int questionBindingCount;
        private int distinctTagCount;
        private Optional<String> targetDigest = Optional.empty();
        private int targetRowCount;
        private int membershipRequestedQuestionCount;
        private Optional<String> membershipDigest = Optional.empty();

        private RowReportBuilder(SourceSnapshot source) {
            this.sourceRowId = source.id();
            this.userId = source.userId();
            this.keyClassification = switch (source.keyAnalysis().kind()) {
                case CANONICAL -> KeyClassification.CANONICAL;
                case CANONICAL_INVALID -> KeyClassification.CANONICAL_INVALID;
                case NEAR_MISS -> KeyClassification.NEAR_MISS;
            };
            this.bankId = source.keyAnalysis().normalizedBankId().isPresent()
                    ? Optional.of(source.keyAnalysis().normalizedBankId().getAsInt())
                    : Optional.empty();
            this.keyBytes = source.key().getBytes(StandardCharsets.UTF_8).length;
            this.keyDigest = LegacyPersonalBankTagPreflightParser.sha256(source.key());
            String sourceValue = source.payloadTooLarge()
                    ? "\u0002" + source.dataUtf8Bytes()
                    : source.data() == null ? "\u0000" : "\u0001" + source.data();
            this.sourceBytes = source.dataUtf8Bytes();
            this.sourceDigest = LegacyPersonalBankTagPreflightParser.sha256(sourceValue);
        }

        private static RowReportBuilder forSource(SourceSnapshot source) {
            return new RowReportBuilder(source);
        }

        private void recordPlan(ParseResult plan) {
            planDigest = Optional.of(plan.planDigest());
            definitionCount = plan.definitionCount();
            questionBindingCount = plan.questionBindingCount();
            distinctTagCount = plan.distinctTagCount();
        }

        private void recordTarget(TargetSnapshot target) {
            targetDigest = Optional.of(target.digest());
            targetRowCount = target.rawRowCount();
        }

        private SourceRow finish(RowOutcome outcome, String failureCode) {
            return new SourceRow(
                    sourceRowId,
                    userId,
                    keyClassification,
                    bankId,
                    keyDigest,
                    keyBytes,
                    sourceDigest,
                    sourceBytes,
                    planDigest,
                    definitionCount,
                    questionBindingCount,
                    distinctTagCount,
                    targetDigest,
                    targetRowCount,
                    membershipRequestedQuestionCount,
                    membershipDigest,
                    outcome,
                    failureCode);
        }
    }

    private static final class MutableRun {
        private final Instant startedAt;
        private final long advisoryLockKey;
        private Status requestedStatus = Status.FAILED;
        private Optional<Integer> backendProcessId = Optional.empty();
        private Optional<String> databaseIdentityDigest = Optional.empty();
        private Optional<String> serverVersion = Optional.empty();
        private Optional<String> transactionIsolation = Optional.empty();
        private boolean transactionReadOnly;
        private boolean transactionDeferrable;
        private int reservedRowCount;
        private int canonicalRowCount;
        private int nearMissRowCount;
        private int normalizedCollisionRowCount;
        private final List<SourceRow> rows = new ArrayList<>();
        private final List<GlobalFailure> globalFailures = new ArrayList<>();

        private MutableRun(Instant startedAt, long advisoryLockKey) {
            this.startedAt = startedAt;
            this.advisoryLockKey = advisoryLockKey;
        }

        private void recordDiscovery(List<SourceSnapshot> sources) {
            reservedRowCount = sources.size();
            canonicalRowCount = Math.toIntExact(sources.stream()
                    .filter(source -> source.keyAnalysis().kind() == KeyKind.CANONICAL)
                    .count());
            nearMissRowCount = Math.toIntExact(sources.stream()
                    .filter(source -> source.keyAnalysis().kind() != KeyKind.CANONICAL)
                    .count());
            normalizedCollisionRowCount = normalizedCollisionRows(sources).size();
        }

        private void addGlobalFailure(GlobalFailureCode code, Throwable failure) {
            Optional<String> sqlState = failure instanceof SQLException sqlFailure
                    ? Optional.ofNullable(sqlFailure.getSQLState())
                    : Optional.empty();
            Optional<String> exceptionType = failure == null
                    ? Optional.empty()
                    : Optional.of(failure.getClass().getName());
            globalFailures.add(new GlobalFailure(code, sqlState, exceptionType));
        }

        private LegacyPersonalBankTagPreflightReport toReport(Instant completedAt) {
            Status status = globalFailures.isEmpty()
                    ? requestedStatus
                    : Status.FAILED;
            EnumMap<RowOutcome, Long> outcomes = new EnumMap<>(RowOutcome.class);
            for (RowOutcome outcome : RowOutcome.values()) {
                outcomes.put(outcome, 0L);
            }
            EnumMap<ReportingGroup, Long> groups = new EnumMap<>(ReportingGroup.class);
            for (ReportingGroup group : ReportingGroup.values()) {
                groups.put(group, 0L);
            }
            for (SourceRow row : rows) {
                outcomes.compute(row.outcome(), (ignored, count) -> count + 1L);
                groups.compute(row.reportingGroup(), (ignored, count) -> count + 1L);
            }
            groups.put(ReportingGroup.GLOBAL_FAILURE, (long) globalFailures.size());
            long blockers = rows.stream().filter(SourceRow::blocksDataApply).count();
            return new LegacyPersonalBankTagPreflightReport(
                    "DRY_RUN",
                    status,
                    startedAt,
                    completedAt,
                    advisoryLockKey,
                    backendProcessId,
                    databaseIdentityDigest,
                    serverVersion,
                    transactionIsolation,
                    transactionReadOnly,
                    transactionDeferrable,
                    reservedRowCount,
                    canonicalRowCount,
                    nearMissRowCount,
                    normalizedCollisionRowCount,
                    rows,
                    outcomes,
                    groups,
                    globalFailures,
                    blockers,
                    aggregateDigest(status, rows, globalFailures),
                    Set.of(
                            ApplyPrerequisiteBlocker.PREFLIGHT_ONLY_NO_APPLY_OPERATOR,
                            ApplyPrerequisiteBlocker.WRITE_FREEZE_OR_VERSION_RECHECK_NOT_PROVEN,
                            ApplyPrerequisiteBlocker.DURABLE_MIGRATION_MARKER_NOT_IMPLEMENTED),
                    0,
                    0);
        }

        private String aggregateDigest(
                Status status,
                List<SourceRow> rows,
                List<GlobalFailure> failures
        ) {
            MessageDigest digest = sha256Digest();
            updateNullableString(digest, "DRY_RUN");
            updateNullableString(digest, status.name());
            updateNullableString(digest, databaseIdentityDigest.orElse(null));
            for (SourceRow row : rows) {
                digest.update(ByteBuffer.allocate(Long.BYTES)
                        .putLong(row.sourceRowId()).array());
                updateNullableString(digest, row.keyDigest());
                updateNullableString(digest, row.sourceDigest());
                updateNullableString(digest, row.planDigest().orElse(null));
                updateNullableString(digest, row.targetDigest().orElse(null));
                updateNullableString(digest, row.membershipDigest().orElse(null));
                updateNullableString(digest, row.outcome().name());
                updateNullableString(digest, row.failureCode());
            }
            for (GlobalFailure failure : failures) {
                updateNullableString(digest, failure.code().name());
                updateNullableString(digest, failure.sqlState().orElse(null));
                updateNullableString(digest, failure.exceptionType().orElse(null));
            }
            return HexFormat.of().formatHex(digest.digest());
        }
    }
}
