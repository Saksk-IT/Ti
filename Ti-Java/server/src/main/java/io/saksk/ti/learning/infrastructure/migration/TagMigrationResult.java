package io.saksk.ti.learning.infrastructure.migration;

import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

/** Redacted result from one explicit operator phase. */
public record TagMigrationResult(
        Outcome outcome,
        State state,
        int version,
        UUID migrationId,
        UUID migrationRunUuid,
        int sourceCount,
        int migratedCount,
        int targetAlreadyPresentCount,
        int emptyNoopCount,
        int transactionAttempts,
        int transactionRetries,
        Optional<FailureCode> failureCode
) {
    public TagMigrationResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        state = Objects.requireNonNull(state, "state");
        migrationId = Objects.requireNonNull(migrationId, "migrationId");
        migrationRunUuid = Objects.requireNonNull(
                migrationRunUuid, "migrationRunUuid");
        failureCode = Objects.requireNonNull(failureCode, "failureCode");
        if (version < -1 || sourceCount < 0 || migratedCount < 0
                || targetAlreadyPresentCount < 0 || emptyNoopCount < 0
                || transactionAttempts < 0 || transactionRetries < 0
                || transactionRetries > transactionAttempts) {
            throw new IllegalArgumentException("invalid operator result count");
        }
        if (!state.acceptsVersion(version)) {
            throw new IllegalArgumentException("state/version pair is invalid");
        }
        int dispositions = Math.addExact(
                Math.addExact(migratedCount, targetAlreadyPresentCount),
                emptyNoopCount);
        if ((outcome == Outcome.APPLIED
                || outcome == Outcome.ALREADY_APPLIED_ZERO_DML)
                && dispositions != sourceCount) {
            throw new IllegalArgumentException(
                    "APPLIED requires one disposition per source");
        }
        if (outcome == Outcome.BLOCKED && failureCode.isEmpty()) {
            throw new IllegalArgumentException("blocked outcome requires a failure code");
        }
        if (outcome != Outcome.BLOCKED && failureCode.isPresent()) {
            throw new IllegalArgumentException(
                    "only blocked outcomes may expose a failure code");
        }
        requireOutcomeState(outcome, state);
    }

    public enum Outcome {
        PREPARED,
        ALREADY_PREPARED_ZERO_DML,
        FROZEN,
        ALREADY_FROZEN_ZERO_DML,
        APPLIED,
        ALREADY_APPLIED_ZERO_DML,
        BLOCKED
    }

    public enum State {
        PLANNED(0),
        FROZEN(1),
        APPLYING(2),
        APPLIED(3),
        BLOCKED(-1),
        UNAVAILABLE(-1);

        private final int fixedVersion;

        State(int fixedVersion) {
            this.fixedVersion = fixedVersion;
        }

        public boolean acceptsVersion(int candidate) {
            return this == UNAVAILABLE
                    ? candidate == -1
                    : this == BLOCKED
                    ? candidate >= 1 && candidate <= 3
                    : candidate == fixedVersion;
        }
    }

    public enum FailureCode {
        SCHEMA_MISSING,
        SCHEMA_FINGERPRINT_MISMATCH,
        SCHEMA_ACL_MISMATCH,
        EVIDENCE_REJECTED,
        LOCK_BUSY,
        IDENTITY_MISMATCH,
        PREFLIGHT_MISMATCH,
        SOURCE_DRIFT,
        PLAN_DRIFT,
        TARGET_MISMATCH,
        MEMBERSHIP_DRIFT,
        RECEIPT_MISMATCH,
        INCOMPLETE_RECEIPTS,
        ILLEGAL_STATE,
        CONCURRENT_STATE_CHANGE,
        COMMIT_OUTCOME_UNKNOWN,
        SQL_FAILURE;

        boolean durableBlockEligible() {
            return switch (this) {
                case PREFLIGHT_MISMATCH,
                        SOURCE_DRIFT,
                        PLAN_DRIFT,
                        TARGET_MISMATCH,
                        MEMBERSHIP_DRIFT,
                        RECEIPT_MISMATCH,
                        INCOMPLETE_RECEIPTS -> true;
                default -> false;
            };
        }
    }

    private static void requireOutcomeState(Outcome outcome, State state) {
        boolean valid = switch (outcome) {
            case PREPARED, ALREADY_PREPARED_ZERO_DML -> state == State.PLANNED;
            case FROZEN, ALREADY_FROZEN_ZERO_DML -> state == State.FROZEN;
            case APPLIED, ALREADY_APPLIED_ZERO_DML -> state == State.APPLIED;
            case BLOCKED -> state == State.UNAVAILABLE
                    || state == State.PLANNED
                    || state == State.FROZEN
                    || state == State.APPLYING
                    || state == State.APPLIED
                    || state == State.BLOCKED;
        };
        if (!valid) {
            throw new IllegalArgumentException("outcome/state pair is invalid");
        }
    }
}
