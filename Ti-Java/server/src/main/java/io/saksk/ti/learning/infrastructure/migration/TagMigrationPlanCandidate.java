package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import java.util.Objects;
import java.util.UUID;

/**
 * Immutable, redacted intent passed between the explicit tag-migration phases.
 *
 * <p>A candidate is not a database snapshot or an apply authorization. The operator core
 * independently re-reads and validates every bound fact before it persists or advances a
 * run.</p>
 */
public final class TagMigrationPlanCandidate {

    private final UUID migrationId;
    private final UUID migrationRunUuid;
    private final LegacyPersonalBankTagPreflightReport freshPreflight;
    private final RunBinding binding;
    private final String candidateSha256;
    private final int sourceCount;
    private final int migratedCount;
    private final int targetAlreadyPresentCount;
    private final int emptyNoopCount;

    TagMigrationPlanCandidate(
            UUID migrationId,
            UUID migrationRunUuid,
            LegacyPersonalBankTagPreflightReport freshPreflight,
            RunBinding binding,
            String candidateSha256,
            int sourceCount,
            int migratedCount,
            int targetAlreadyPresentCount,
            int emptyNoopCount
    ) {
        this.migrationId = requireUuid(migrationId, "migrationId");
        this.migrationRunUuid = requireUuid(
                migrationRunUuid, "migrationRunUuid");
        this.freshPreflight = Objects.requireNonNull(
                freshPreflight, "freshPreflight");
        this.binding = Objects.requireNonNull(binding, "binding");
        this.candidateSha256 = TagMigrationDigests.requireSha256(
                candidateSha256, "candidateSha256");
        this.sourceCount = requireNonNegative(sourceCount, "sourceCount");
        this.migratedCount = requireNonNegative(
                migratedCount, "migratedCount");
        this.targetAlreadyPresentCount = requireNonNegative(
                targetAlreadyPresentCount, "targetAlreadyPresentCount");
        this.emptyNoopCount = requireNonNegative(
                emptyNoopCount, "emptyNoopCount");
        int dispositionCount = Math.addExact(
                Math.addExact(migratedCount, targetAlreadyPresentCount),
                emptyNoopCount);
        if (sourceCount != dispositionCount) {
            throw new IllegalArgumentException(
                    "candidate requires one disposition per source");
        }
    }

    public UUID migrationId() {
        return migrationId;
    }

    public UUID migrationRunUuid() {
        return migrationRunUuid;
    }

    public LegacyPersonalBankTagPreflightReport freshPreflight() {
        return freshPreflight;
    }

    public RunBinding binding() {
        return binding;
    }

    public String candidateSha256() {
        return candidateSha256;
    }

    public int sourceCount() {
        return sourceCount;
    }

    public int migratedCount() {
        return migratedCount;
    }

    public int targetAlreadyPresentCount() {
        return targetAlreadyPresentCount;
    }

    public int emptyNoopCount() {
        return emptyNoopCount;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof TagMigrationPlanCandidate candidate)) {
            return false;
        }
        return migrationId.equals(candidate.migrationId)
                && migrationRunUuid.equals(candidate.migrationRunUuid)
                && freshPreflight.equals(candidate.freshPreflight)
                && binding.equals(candidate.binding)
                && candidateSha256.equals(candidate.candidateSha256)
                && sourceCount == candidate.sourceCount
                && migratedCount == candidate.migratedCount
                && targetAlreadyPresentCount == candidate.targetAlreadyPresentCount
                && emptyNoopCount == candidate.emptyNoopCount;
    }

    @Override
    public int hashCode() {
        return Objects.hash(
                migrationId,
                migrationRunUuid,
                freshPreflight,
                binding,
                candidateSha256,
                sourceCount,
                migratedCount,
                targetAlreadyPresentCount,
                emptyNoopCount);
    }

    @Override
    public String toString() {
        return "TagMigrationPlanCandidate[migrationId=" + migrationId
                + ",migrationRunUuid=" + migrationRunUuid
                + ",candidateSha256=" + candidateSha256
                + ",sourceCount=" + sourceCount
                + ",migratedCount=" + migratedCount
                + ",targetAlreadyPresentCount=" + targetAlreadyPresentCount
                + ",emptyNoopCount=" + emptyNoopCount
                + ",redacted=true]";
    }

    private static UUID requireUuid(UUID value, String name) {
        UUID required = Objects.requireNonNull(value, name);
        if (required.equals(new UUID(0L, 0L))) {
            throw new IllegalArgumentException(name + " must not be the nil UUID");
        }
        return required;
    }

    private static int requireNonNegative(int value, String name) {
        if (value < 0) {
            throw new IllegalArgumentException(name + " must not be negative");
        }
        return value;
    }
}
