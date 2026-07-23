package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.KeyClassification;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.RowOutcome;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.SourceRow;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/** Pure, I/O-free constructor for explicit tag-migration plan candidates. */
public final class TagMigrationPlanCandidateFactory {

    static final String CANDIDATE_DOMAIN =
            "ti:phase4c:tag-migration:plan-candidate:v1";

    public TagMigrationPlanCandidate create(
            UUID migrationId,
            UUID migrationRunUuid,
            LegacyPersonalBankTagPreflightReport freshPreflight,
            RunBinding proposedBinding
    ) {
        UUID requiredMigrationId = requireUuid(migrationId, "migrationId");
        UUID requiredRunUuid = requireUuid(
                migrationRunUuid, "migrationRunUuid");
        LegacyPersonalBankTagPreflightReport report = Objects.requireNonNull(
                freshPreflight, "freshPreflight");
        RunBinding binding = Objects.requireNonNull(
                proposedBinding, "proposedBinding");
        requireEligibleEnvelope(report, binding);

        int migrated = exactOutcomeCount(report, RowOutcome.MIGRATABLE);
        int alreadyPresent = exactOutcomeCount(
                report, RowOutcome.TARGET_ALREADY_PRESENT);
        int emptyNoop = exactOutcomeCount(report, RowOutcome.EMPTY_NOOP);
        return new TagMigrationPlanCandidate(
                requiredMigrationId,
                requiredRunUuid,
                report,
                binding,
                candidateDigest(requiredMigrationId, requiredRunUuid, binding),
                report.reservedRowCount(),
                migrated,
                alreadyPresent,
                emptyNoop);
    }

    static String candidateDigest(
            UUID migrationId,
            UUID migrationRunUuid,
            RunBinding binding
    ) {
        UUID requiredMigrationId = requireUuid(migrationId, "migrationId");
        UUID requiredRunUuid = requireUuid(
                migrationRunUuid, "migrationRunUuid");
        RunBinding requiredBinding = Objects.requireNonNull(binding, "binding");
        MessageDigest digest = sha256Digest();
        updateString(digest, CANDIDATE_DOMAIN);
        updateUuid(digest, requiredMigrationId);
        updateUuid(digest, requiredRunUuid);
        updateSha(digest, requiredBinding.backupManifestSha256());
        updateSha(digest, requiredBinding.clusterDatabaseIdentitySha256());
        updateSha(digest, requiredBinding.runIdentitySha256());
        updateSha(digest, requiredBinding.preflightDigestSha256());
        updateSha(digest, requiredBinding.sourceSetDigestSha256());
        updateSha(digest, requiredBinding.planSetDigestSha256());
        updateSha(digest, requiredBinding.preapplyTargetSetDigestSha256());
        updateSha(digest, requiredBinding.finalTargetSetDigestSha256());
        updateSha(digest, requiredBinding.membershipSetDigestSha256());
        return HexFormat.of().formatHex(digest.digest());
    }

    private static void requireEligibleEnvelope(
            LegacyPersonalBankTagPreflightReport report,
            RunBinding binding
    ) {
        List<Long> sourceIds = report.rows().stream()
                .map(SourceRow::sourceRowId)
                .toList();
        if (!report.fullSweepComplete()
                || !report.isDataEligible()
                || report.reservedRowCount() <= 0
                || report.canonicalRowCount() != report.reservedRowCount()
                || report.nearMissRowCount() != 0
                || report.normalizedCollisionRowCount() != 0
                || report.blockingRowCount() != 0
                || report.advisoryLockKey()
                        != LegacyPersonalBankTagGlobalPreflight.advisoryLockKey()
                || !sourceIds.equals(sourceIds.stream().distinct().sorted().toList())
                || !report.aggregateDigest().equals(recomputeAggregate(report))
                || !report.aggregateDigest().equals(
                        binding.preflightDigestSha256())
                || report.rows().stream().anyMatch(
                        row -> !eligibleSource(row))) {
            throw new IllegalArgumentException(
                    "candidate requires a complete bound eligible preflight");
        }
    }

    private static boolean eligibleSource(SourceRow row) {
        return row.keyClassification() == KeyClassification.CANONICAL
                && row.normalizedBankId().isPresent()
                && row.planDigest().isPresent()
                && row.targetDigest().isPresent()
                && row.membershipDigest().isPresent()
                && "NONE".equals(row.failureCode())
                && !row.blocksDataApply();
    }

    private static int exactOutcomeCount(
            LegacyPersonalBankTagPreflightReport report,
            RowOutcome outcome
    ) {
        return Math.toIntExact(report.outcomeCounts().getOrDefault(outcome, 0L));
    }

    private static String recomputeAggregate(
            LegacyPersonalBankTagPreflightReport report
    ) {
        MessageDigest digest = sha256Digest();
        updateNullableString(digest, report.mode());
        updateNullableString(digest, report.status().name());
        updateNullableString(
                digest, report.databaseIdentityDigest().orElse(null));
        for (SourceRow row : report.rows()) {
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
        report.globalFailures().forEach(failure -> {
            updateNullableString(digest, failure.code().name());
            updateNullableString(digest, failure.sqlState().orElse(null));
            updateNullableString(digest, failure.exceptionType().orElse(null));
        });
        return HexFormat.of().formatHex(digest.digest());
    }

    private static UUID requireUuid(UUID value, String name) {
        UUID required = Objects.requireNonNull(value, name);
        if (required.equals(new UUID(0L, 0L))) {
            throw new IllegalArgumentException(name + " must not be the nil UUID");
        }
        return required;
    }

    private static void updateUuid(MessageDigest digest, UUID value) {
        digest.update(ByteBuffer.allocate(Long.BYTES * 2)
                .putLong(value.getMostSignificantBits())
                .putLong(value.getLeastSignificantBits())
                .array());
    }

    private static void updateSha(MessageDigest digest, String value) {
        digest.update(HexFormat.of().parseHex(
                TagMigrationDigests.requireSha256(value, "binding digest")));
    }

    private static void updateString(MessageDigest digest, String value) {
        byte[] bytes = Objects.requireNonNull(value, "value")
                .getBytes(StandardCharsets.UTF_8);
        digest.update(ByteBuffer.allocate(Integer.BYTES)
                .putInt(bytes.length).array());
        digest.update(bytes);
    }

    private static void updateNullableString(MessageDigest digest, String value) {
        digest.update((byte) (value == null ? 0 : 1));
        if (value != null) {
            updateString(digest, value);
        }
    }

    private static MessageDigest sha256Digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }
}
