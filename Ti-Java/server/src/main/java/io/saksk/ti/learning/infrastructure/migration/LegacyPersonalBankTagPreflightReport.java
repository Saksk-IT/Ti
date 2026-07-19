package io.saksk.ti.learning.infrastructure.migration;

import java.time.Instant;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/** Immutable, redacted result of one explicit legacy-tag dry-run. */
public record LegacyPersonalBankTagPreflightReport(
        String mode,
        Status status,
        Instant startedAt,
        Instant completedAt,
        long advisoryLockKey,
        Optional<Integer> backendProcessId,
        Optional<String> databaseIdentityDigest,
        Optional<String> serverVersion,
        Optional<String> transactionIsolation,
        boolean transactionReadOnly,
        boolean transactionDeferrable,
        int reservedRowCount,
        int canonicalRowCount,
        int nearMissRowCount,
        int normalizedCollisionRowCount,
        List<SourceRow> rows,
        Map<RowOutcome, Long> outcomeCounts,
        Map<ReportingGroup, Long> reportingGroupCounts,
        List<GlobalFailure> globalFailures,
        long blockingRowCount,
        String aggregateDigest,
        Set<ApplyPrerequisiteBlocker> applyPrerequisiteBlockers,
        int mutationStatementCount,
        int ddlStatementCount
) {
    public LegacyPersonalBankTagPreflightReport {
        if (!"DRY_RUN".equals(mode)) {
            throw new IllegalArgumentException("preflight mode must be DRY_RUN");
        }
        status = Objects.requireNonNull(status, "status");
        startedAt = Objects.requireNonNull(startedAt, "startedAt");
        completedAt = Objects.requireNonNull(completedAt, "completedAt");
        backendProcessId = Objects.requireNonNull(backendProcessId, "backendProcessId");
        databaseIdentityDigest = requireOptionalSha256(
                databaseIdentityDigest, "databaseIdentityDigest");
        serverVersion = Objects.requireNonNull(serverVersion, "serverVersion");
        transactionIsolation = Objects.requireNonNull(
                transactionIsolation, "transactionIsolation");
        rows = List.copyOf(Objects.requireNonNull(rows, "rows"));
        outcomeCounts = Map.copyOf(Objects.requireNonNull(
                outcomeCounts, "outcomeCounts"));
        reportingGroupCounts = Map.copyOf(Objects.requireNonNull(
                reportingGroupCounts, "reportingGroupCounts"));
        globalFailures = List.copyOf(Objects.requireNonNull(
                globalFailures, "globalFailures"));
        aggregateDigest = requireSha256(aggregateDigest, "aggregateDigest");
        applyPrerequisiteBlockers = Set.copyOf(Objects.requireNonNull(
                applyPrerequisiteBlockers, "applyPrerequisiteBlockers"));
        if (reservedRowCount < 0 || canonicalRowCount < 0 || nearMissRowCount < 0
                || normalizedCollisionRowCount < 0 || blockingRowCount < 0
                || mutationStatementCount != 0 || ddlStatementCount != 0) {
            throw new IllegalArgumentException("invalid preflight count or mutation surface");
        }
        if (completedAt.isBefore(startedAt)) {
            throw new IllegalArgumentException("completedAt precedes startedAt");
        }
        if ((long) canonicalRowCount + nearMissRowCount != reservedRowCount) {
            throw new IllegalArgumentException("key classification totals are inconsistent");
        }
        if (normalizedCollisionRowCount > reservedRowCount) {
            throw new IllegalArgumentException("collision count exceeds discovered rows");
        }
        if (rows.size() > reservedRowCount) {
            throw new IllegalArgumentException("classified rows exceed discovered rows");
        }
        if (status == Status.COMPLETED && rows.size() != reservedRowCount) {
            throw new IllegalArgumentException("completed preflight did not classify every row");
        }
        if (status != Status.FAILED && !globalFailures.isEmpty()) {
            throw new IllegalArgumentException("global failures require FAILED status");
        }
        if (status == Status.COMPLETED
                && (backendProcessId.filter(processId -> processId > 0).isEmpty()
                || databaseIdentityDigest.isEmpty()
                || serverVersion.filter(version -> !version.isBlank()).isEmpty()
                || transactionIsolation
                        .filter("serializable"::equalsIgnoreCase)
                        .isEmpty()
                || !transactionReadOnly
                || !transactionDeferrable)) {
            throw new IllegalArgumentException(
                    "completed preflight lacks required read-only transaction evidence");
        }
        long actualBlockingRows = rows.stream().filter(SourceRow::blocksDataApply).count();
        if (blockingRowCount != actualBlockingRows) {
            throw new IllegalArgumentException("blocking row count is inconsistent");
        }
        requireOutcomeCounts(rows, outcomeCounts);
        requireReportingGroupCounts(rows, globalFailures, reportingGroupCounts);
        if (!applyPrerequisiteBlockers.equals(
                EnumSet.allOf(ApplyPrerequisiteBlocker.class))) {
            throw new IllegalArgumentException("all apply prerequisites must remain blocked");
        }
    }

    public boolean fullSweepComplete() {
        return status == Status.COMPLETED
                && globalFailures.isEmpty()
                && rows.size() == reservedRowCount;
    }

    public boolean isDataEligible() {
        return fullSweepComplete() && blockingRowCount == 0;
    }

    /** Node A is intentionally incapable of authorizing an apply. */
    public boolean isApplyEligible() {
        return false;
    }

    public enum Status {
        COMPLETED,
        LOCK_BUSY,
        FAILED
    }

    public enum KeyClassification {
        CANONICAL,
        CANONICAL_INVALID,
        NEAR_MISS
    }

    public enum ReportingGroup {
        ELIGIBLE,
        CONFLICT,
        INVALID,
        UNRESOLVED,
        GLOBAL_FAILURE
    }

    public enum RowOutcome {
        MIGRATABLE(ReportingGroup.ELIGIBLE),
        EMPTY_NOOP(ReportingGroup.ELIGIBLE),
        TARGET_ALREADY_PRESENT(ReportingGroup.ELIGIBLE),
        TARGET_CONFLICT(ReportingGroup.CONFLICT),
        NORMALIZED_BANK_COLLISION(ReportingGroup.CONFLICT),
        TARGET_INVALID(ReportingGroup.CONFLICT),
        INVALID_KEY(ReportingGroup.INVALID),
        INVALID_DATA(ReportingGroup.INVALID),
        BANK_MISSING(ReportingGroup.UNRESOLVED),
        ORPHAN_QUESTION(ReportingGroup.UNRESOLVED),
        MEMBERSHIP_UNAVAILABLE(ReportingGroup.UNRESOLVED);

        private final ReportingGroup group;

        RowOutcome(ReportingGroup group) {
            this.group = group;
        }

        public ReportingGroup group() {
            return group;
        }

        public boolean blocksDataApply() {
            return group != ReportingGroup.ELIGIBLE;
        }
    }

    public enum ApplyPrerequisiteBlocker {
        PREFLIGHT_ONLY_NO_APPLY_OPERATOR,
        WRITE_FREEZE_OR_VERSION_RECHECK_NOT_PROVEN,
        DURABLE_MIGRATION_MARKER_NOT_IMPLEMENTED
    }

    public enum GlobalFailureCode {
        CONNECTION_ACQUISITION_FAILED,
        CONNECTION_SETUP_FAILED,
        ADVISORY_LOCK_ACQUISITION_FAILED,
        CONNECTION_METADATA_READ_FAILED,
        TRANSACTION_SETUP_FAILED,
        SOURCE_SCAN_FAILED,
        CLASSIFICATION_READ_FAILED,
        READ_ONLY_COMMIT_FAILED,
        READ_ONLY_ROLLBACK_FAILED,
        ADVISORY_UNLOCK_REJECTED,
        ADVISORY_UNLOCK_FAILED,
        CONNECTION_CLOSE_FAILED
    }

    public record GlobalFailure(
            GlobalFailureCode code,
            Optional<String> sqlState,
            Optional<String> exceptionType
    ) {
        public GlobalFailure {
            code = Objects.requireNonNull(code, "code");
            sqlState = Objects.requireNonNull(sqlState, "sqlState");
            exceptionType = Objects.requireNonNull(exceptionType, "exceptionType");
        }
    }

    public record SourceRow(
            long sourceRowId,
            long userId,
            KeyClassification keyClassification,
            Optional<Integer> normalizedBankId,
            String keyDigest,
            int keyUtf8Bytes,
            String sourceDigest,
            int sourceUtf8Bytes,
            Optional<String> planDigest,
            int definitionCount,
            int questionBindingCount,
            int distinctTagCount,
            Optional<String> targetDigest,
            int targetRowCount,
            int membershipRequestedQuestionCount,
            Optional<String> membershipDigest,
            RowOutcome outcome,
            String failureCode
    ) {
        public SourceRow {
            if (sourceRowId <= 0 || userId <= 0) {
                throw new IllegalArgumentException("source and user IDs must be positive");
            }
            keyClassification = Objects.requireNonNull(
                    keyClassification, "keyClassification");
            normalizedBankId = Objects.requireNonNull(
                    normalizedBankId, "normalizedBankId");
            keyDigest = requireSha256(keyDigest, "keyDigest");
            sourceDigest = requireSha256(sourceDigest, "sourceDigest");
            planDigest = requireOptionalSha256(planDigest, "planDigest");
            targetDigest = requireOptionalSha256(targetDigest, "targetDigest");
            membershipDigest = requireOptionalSha256(
                    membershipDigest, "membershipDigest");
            outcome = Objects.requireNonNull(outcome, "outcome");
            failureCode = Objects.requireNonNull(failureCode, "failureCode");
            if (!failureCode.matches("[A-Z0-9_]+")) {
                throw new IllegalArgumentException("failureCode must be a stable code");
            }
            if (keyUtf8Bytes < 0 || sourceUtf8Bytes < 0 || definitionCount < 0
                    || questionBindingCount < 0 || distinctTagCount < 0
                    || targetRowCount < 0 || membershipRequestedQuestionCount < 0) {
                throw new IllegalArgumentException("report counts must be non-negative");
            }
        }

        public boolean blocksDataApply() {
            return outcome.blocksDataApply();
        }

        public ReportingGroup reportingGroup() {
            return outcome.group();
        }
    }

    private static String requireSha256(String value, String name) {
        value = Objects.requireNonNull(value, name);
        if (!value.matches("[0-9a-f]{64}")) {
            throw new IllegalArgumentException(name + " must be lowercase SHA-256");
        }
        return value;
    }

    private static Optional<String> requireOptionalSha256(
            Optional<String> value,
            String name
    ) {
        value = Objects.requireNonNull(value, name);
        value.ifPresent(digest -> requireSha256(digest, name));
        return value;
    }

    private static void requireOutcomeCounts(
            List<SourceRow> rows,
            Map<RowOutcome, Long> actual
    ) {
        if (!actual.keySet().equals(EnumSet.allOf(RowOutcome.class))) {
            throw new IllegalArgumentException("outcome counts must cover every outcome");
        }
        EnumMap<RowOutcome, Long> expected = new EnumMap<>(RowOutcome.class);
        for (RowOutcome outcome : RowOutcome.values()) {
            expected.put(outcome, 0L);
        }
        for (SourceRow row : rows) {
            expected.compute(row.outcome(), (ignored, count) -> count + 1L);
        }
        if (!actual.equals(expected)) {
            throw new IllegalArgumentException("outcome counts are inconsistent");
        }
    }

    private static void requireReportingGroupCounts(
            List<SourceRow> rows,
            List<GlobalFailure> failures,
            Map<ReportingGroup, Long> actual
    ) {
        if (!actual.keySet().equals(EnumSet.allOf(ReportingGroup.class))) {
            throw new IllegalArgumentException("group counts must cover every group");
        }
        EnumMap<ReportingGroup, Long> expected = new EnumMap<>(ReportingGroup.class);
        for (ReportingGroup group : ReportingGroup.values()) {
            expected.put(group, 0L);
        }
        for (SourceRow row : rows) {
            expected.compute(row.reportingGroup(), (ignored, count) -> count + 1L);
        }
        expected.put(ReportingGroup.GLOBAL_FAILURE, (long) failures.size());
        if (!actual.equals(expected)) {
            throw new IllegalArgumentException("group counts are inconsistent");
        }
    }
}
