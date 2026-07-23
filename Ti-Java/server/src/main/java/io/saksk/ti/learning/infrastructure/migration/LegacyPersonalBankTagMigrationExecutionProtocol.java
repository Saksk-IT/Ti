package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceRejectedException;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceVerifier;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.ApplyCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.FreezeCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.PrepareCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.RecoveryCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.SignedEvidence;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.FailureCode;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.Outcome;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.State;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import javax.sql.DataSource;

/**
 * Explicit, disabled-by-default sequencing boundary around the tag-migration core.
 *
 * <p>Every phase is a separate caller action. This type neither produces operational
 * receipts nor stops writers, drains connections, restores backups, creates schema, or
 * discovers credentials.</p>
 */
public final class LegacyPersonalBankTagMigrationExecutionProtocol {

    private final TagMigrationPlanCandidateFactory candidateFactory;
    private final EvidenceVerifier evidenceVerifier;
    private final LegacyPersonalBankTagMigrationOperatorCore core;

    /**
     * Creates the public protocol with the concrete production wire verifier.
     *
     * <p>The same verifier instance performs protocol pre-verification and the core's
     * authoritative verification.</p>
     */
    public LegacyPersonalBankTagMigrationExecutionProtocol(
            DataSource operatorDataSource,
            PersonalBankQuestionFactsApi memberships,
            Ed25519TagMigrationEvidenceVerifier evidenceVerifier
    ) {
        this(
                operatorDataSource,
                memberships,
                (EvidenceVerifier) Objects.requireNonNull(
                        evidenceVerifier, "evidenceVerifier"));
    }

    /** Package-private compatibility seam for deterministic tests only. */
    LegacyPersonalBankTagMigrationExecutionProtocol(
            DataSource operatorDataSource,
            PersonalBankQuestionFactsApi memberships,
            EvidenceVerifier evidenceVerifier
    ) {
        DataSource requiredDataSource = Objects.requireNonNull(
                operatorDataSource, "operatorDataSource");
        PersonalBankQuestionFactsApi requiredMemberships = Objects.requireNonNull(
                memberships, "memberships");
        this.candidateFactory = new TagMigrationPlanCandidateFactory();
        this.evidenceVerifier = Objects.requireNonNull(
                evidenceVerifier, "evidenceVerifier");
        this.core = new LegacyPersonalBankTagMigrationOperatorCore(
                requiredDataSource,
                requiredMemberships,
                this.evidenceVerifier);
    }

    public TagMigrationPlanCandidate candidate(
            UUID migrationId,
            UUID migrationRunUuid,
            LegacyPersonalBankTagPreflightReport freshPreflight,
            RunBinding proposedBinding
    ) {
        return candidateFactory.create(
                migrationId,
                migrationRunUuid,
                freshPreflight,
                proposedBinding);
    }

    public TagMigrationResult prepare(
            TagMigrationPlanCandidate candidate,
            SignedEvidence signedEvidence
    ) {
        TagMigrationPlanCandidate required = requireCandidate(candidate);
        try {
            RunBinding verified = Objects.requireNonNull(
                    evidenceVerifier.verifyPrepare(
                            required.migrationId(),
                            required.migrationRunUuid(),
                            signedEvidence),
                    "verified prepare evidence")
                    .binding();
            if (!verified.equals(required.binding())) {
                return evidenceRejected(required);
            }
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return evidenceRejected(required);
        }
        return core.prepare(new PrepareCommand(
                required.migrationId(),
                required.migrationRunUuid(),
                required.freshPreflight(),
                signedEvidence));
    }

    public TagMigrationResult freeze(
            TagMigrationPlanCandidate candidate,
            SignedEvidence signedEvidence
    ) {
        TagMigrationPlanCandidate required = requireCandidate(candidate);
        try {
            RunBinding verified = Objects.requireNonNull(
                    evidenceVerifier.verifyFreeze(
                            required.migrationId(),
                            required.migrationRunUuid(),
                            signedEvidence),
                    "verified freeze evidence")
                    .binding();
            if (!verified.equals(required.binding())) {
                return evidenceRejected(required);
            }
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return evidenceRejected(required);
        }
        return core.freeze(new FreezeCommand(
                required.migrationId(),
                required.migrationRunUuid(),
                signedEvidence));
    }

    public TagMigrationResult apply(
            TagMigrationPlanCandidate candidate,
            SignedEvidence signedEvidence
    ) {
        TagMigrationPlanCandidate required = requireCandidate(candidate);
        try {
            RunBinding verified = Objects.requireNonNull(
                    evidenceVerifier.verifyApply(
                            required.migrationId(),
                            required.migrationRunUuid(),
                            signedEvidence),
                    "verified apply evidence")
                    .binding();
            if (!verified.equals(required.binding())) {
                return evidenceRejected(required);
            }
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return evidenceRejected(required);
        }
        return core.apply(new ApplyCommand(
                required.migrationId(),
                required.migrationRunUuid(),
                signedEvidence));
    }

    public TagMigrationResult recover(
            TagMigrationPlanCandidate candidate,
            SignedEvidence signedEvidence
    ) {
        TagMigrationPlanCandidate required = requireCandidate(candidate);
        try {
            RunBinding verified = Objects.requireNonNull(
                    evidenceVerifier.verifyRecovery(
                            required.migrationId(),
                            required.migrationRunUuid(),
                            signedEvidence),
                    "verified recovery evidence")
                    .binding();
            if (!verified.equals(required.binding())) {
                return evidenceRejected(required);
            }
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return evidenceRejected(required);
        }
        return core.recover(new RecoveryCommand(
                required.migrationId(),
                required.migrationRunUuid(),
                signedEvidence));
    }

    private static TagMigrationPlanCandidate requireCandidate(
            TagMigrationPlanCandidate candidate
    ) {
        TagMigrationPlanCandidate required = Objects.requireNonNull(
                candidate, "candidate");
        String recomputed = TagMigrationPlanCandidateFactory.candidateDigest(
                required.migrationId(),
                required.migrationRunUuid(),
                required.binding());
        if (!recomputed.equals(required.candidateSha256())) {
            throw new IllegalArgumentException(
                    "candidate digest does not match its bound inputs");
        }
        return required;
    }

    private static TagMigrationResult evidenceRejected(
            TagMigrationPlanCandidate candidate
    ) {
        return new TagMigrationResult(
                Outcome.BLOCKED,
                State.UNAVAILABLE,
                -1,
                candidate.migrationId(),
                candidate.migrationRunUuid(),
                0,
                0,
                0,
                0,
                0,
                0,
                Optional.of(FailureCode.EVIDENCE_REJECTED));
    }
}
