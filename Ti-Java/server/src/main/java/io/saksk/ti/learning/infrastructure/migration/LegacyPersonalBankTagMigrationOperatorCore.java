package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.Execution;
import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.FailureKind;
import io.saksk.ti.learning.infrastructure.migration.BoundedSqlRetry.SqlOperationException;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.DatabaseIdentityFacts;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.Disposition;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.ManifestRow;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.OperatorSession;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.ReadOnlyRecoverySession;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.ReceiptSnapshot;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.RunManifest;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.RunSnapshot;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.SourceSnapshot;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.TargetSnapshot;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.KeyAnalysis;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseFailure;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseResult;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.KeyClassification;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.RowOutcome;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightReport.SourceRow;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.ApplyCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.FreezeCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.PrepareCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.RecoveryCommand;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.SignedEvidence;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.ManifestDigestRow;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.ManifestDigests;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.TargetIdentity;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.FailureCode;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.Outcome;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.State;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.TreeSet;
import java.util.UUID;
import javax.sql.DataSource;

/**
 * Explicit, disabled-by-default library core for the legacy personal-bank tag migration.
 *
 * <p>This type is intentionally not a Spring component, command-line runner, scheduled
 * task, HTTP endpoint, or environment-driven switch. It performs no DDL and can only be
 * used by a caller that supplies an authenticated evidence verifier and invokes one of
 * the four phase methods directly.</p>
 */
public final class LegacyPersonalBankTagMigrationOperatorCore {

    private final PersonalBankQuestionFactsApi memberships;
    private final EvidenceVerifier evidenceVerifier;
    private final JdbcTagMigrationStore store;
    private final BoundedSqlRetry retry;

    public LegacyPersonalBankTagMigrationOperatorCore(
            DataSource operatorDataSource,
            PersonalBankQuestionFactsApi memberships,
            EvidenceVerifier evidenceVerifier
    ) {
        Objects.requireNonNull(operatorDataSource, "operatorDataSource");
        this.memberships = Objects.requireNonNull(memberships, "memberships");
        this.evidenceVerifier = Objects.requireNonNull(
                evidenceVerifier, "evidenceVerifier");
        this.store = new JdbcTagMigrationStore(operatorDataSource);
        this.retry = new BoundedSqlRetry(operatorDataSource);
    }

    LegacyPersonalBankTagMigrationOperatorCore(
            PersonalBankQuestionFactsApi memberships,
            EvidenceVerifier evidenceVerifier,
            JdbcTagMigrationStore store,
            BoundedSqlRetry retry
    ) {
        this.memberships = Objects.requireNonNull(memberships, "memberships");
        this.evidenceVerifier = Objects.requireNonNull(
                evidenceVerifier, "evidenceVerifier");
        this.store = Objects.requireNonNull(store, "store");
        this.retry = Objects.requireNonNull(retry, "retry");
    }

    public TagMigrationResult prepare(PrepareCommand command) {
        Objects.requireNonNull(command, "command");
        VerifiedPrepareEvidence evidence;
        try {
            evidence = Objects.requireNonNull(
                    evidenceVerifier.verifyPrepare(
                            command.migrationId(), command.migrationRunUuid(),
                            command.signedEvidence()),
                    "verified prepare evidence");
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return unavailable(command, FailureCode.EVIDENCE_REJECTED);
        }

        try (OperatorSession session = store.openSession()) {
            requireSessionIdentity(
                    session.databaseIdentity(), command.migrationRunUuid(),
                    evidence.binding());
            Execution<PhaseOutcome> execution = retry.execute((connection, attempt) -> {
                requireTransactionIdentity(
                        connection, command.migrationRunUuid(), evidence.binding());
                RunManifest manifest = buildManifest(
                        connection, command, evidence.binding());
                requireBinding(evidence.binding(), manifest);

                Optional<RunSnapshot> existing = store.readRun(
                        connection, command.migrationId(),
                        command.migrationRunUuid(), true);
                if (existing.isPresent()) {
                    RunSnapshot run = existing.orElseThrow();
                    requireExactPreparedReplay(
                            connection, run, manifest,
                            evidence.prepareEvidenceReceiptSha256());
                    return PhaseOutcome.replayed(run);
                }
                store.insertPreparedRun(
                        connection, manifest,
                        evidence.prepareEvidenceReceiptSha256());
                return PhaseOutcome.created(manifest.rows().size());
            });
            PhaseOutcome phase = execution.value();
            return new TagMigrationResult(
                    phase.replayed()
                            ? Outcome.ALREADY_PREPARED_ZERO_DML
                            : Outcome.PREPARED,
                    State.PLANNED,
                    0,
                    command.migrationId(),
                    command.migrationRunUuid(),
                    phase.sourceCount(),
                    0, 0, 0,
                    execution.attempts(), execution.retries(), Optional.empty());
        } catch (TagMigrationSchemaVerifier.SchemaVerificationException failure) {
            return unavailable(command, failure.failureCode());
        } catch (JdbcTagMigrationStore.LockBusyException failure) {
            return unavailable(command, FailureCode.LOCK_BUSY);
        } catch (CoreFailure failure) {
            return unavailable(command, failure.failureCode());
        } catch (SqlOperationException failure) {
            return observeDurable(
                    command,
                    evidence.binding(),
                    sqlFailureCode(failure),
                    failure.attempts(),
                    failure.retries());
        } catch (SQLException | RuntimeException failure) {
            return observeDurable(
                    command, evidence.binding(), FailureCode.SQL_FAILURE, 0, 0);
        }
    }

    public TagMigrationResult freeze(FreezeCommand command) {
        Objects.requireNonNull(command, "command");
        VerifiedFreezeEvidence evidence;
        try {
            evidence = Objects.requireNonNull(
                    evidenceVerifier.verifyFreeze(
                            command.migrationId(), command.migrationRunUuid(),
                            command.signedEvidence()),
                    "verified freeze evidence");
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return unavailable(command, FailureCode.EVIDENCE_REJECTED);
        }

        try (OperatorSession session = store.openSession()) {
            requireSessionIdentity(
                    session.databaseIdentity(), command.migrationRunUuid(),
                    evidence.binding());
            Execution<PhaseOutcome> execution = retry.execute((connection, attempt) -> {
                requireTransactionIdentity(
                        connection, command.migrationRunUuid(), evidence.binding());
                RunSnapshot run = requireRun(connection, command, true);
                requireBinding(evidence.binding(), run);
                List<ManifestRow> manifest = requireStoredManifest(connection, run);
                revalidateAll(connection, manifest, ValidationPhase.PREAPPLY);
                if (run.state() == State.FROZEN) {
                    requireFreezeReceipts(run, evidence);
                    return PhaseOutcome.replayed(run);
                }
                if (run.state() != State.PLANNED || run.version() != 0) {
                    throw new CoreFailure(FailureCode.ILLEGAL_STATE);
                }
                int changed = store.freeze(
                        connection, run,
                        evidence.sourceWriterStopReceiptSha256(),
                        evidence.targetWriterStopReceiptSha256(),
                        evidence.membershipWriterStopReceiptSha256(),
                        evidence.connectionDrainReceiptSha256(),
                        evidence.connectionRejectionReceiptSha256(),
                        evidence.restoredBackupReceiptSha256());
                if (changed != 1) {
                    throw new CoreFailure(FailureCode.CONCURRENT_STATE_CHANGE);
                }
                return PhaseOutcome.created(run.sourceCount());
            });
            return new TagMigrationResult(
                    execution.value().replayed()
                            ? Outcome.ALREADY_FROZEN_ZERO_DML
                            : Outcome.FROZEN,
                    State.FROZEN,
                    1,
                    command.migrationId(), command.migrationRunUuid(),
                    execution.value().sourceCount(),
                    0, 0, 0,
                    execution.attempts(), execution.retries(), Optional.empty());
        } catch (TagMigrationSchemaVerifier.SchemaVerificationException failure) {
            return unavailable(command, failure.failureCode());
        } catch (JdbcTagMigrationStore.LockBusyException failure) {
            return unavailable(command, FailureCode.LOCK_BUSY);
        } catch (CoreFailure failure) {
            return unavailable(command, failure.failureCode());
        } catch (SqlOperationException failure) {
            return persistKnownDrift(
                    command,
                    evidence.binding(),
                    sqlFailureCode(failure),
                    failure.attempts(),
                    failure.retries());
        } catch (SQLException | RuntimeException failure) {
            return observeDurable(
                    command, evidence.binding(), FailureCode.SQL_FAILURE, 0, 0);
        }
    }

    public TagMigrationResult apply(ApplyCommand command) {
        Objects.requireNonNull(command, "command");
        VerifiedApplyEvidence evidence;
        try {
            evidence = Objects.requireNonNull(
                    evidenceVerifier.verifyApply(
                            command.migrationId(), command.migrationRunUuid(),
                            command.signedEvidence()),
                    "verified apply evidence");
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return unavailable(command, FailureCode.EVIDENCE_REJECTED);
        }

        int attempts = 0;
        int retries = 0;
        try (OperatorSession session = store.openSession()) {
            requireSessionIdentity(
                    session.databaseIdentity(), command.migrationRunUuid(),
                    evidence.binding());
            Execution<ApplyStart> start = retry.execute((connection, attempt) -> {
                requireTransactionIdentity(
                        connection, command.migrationRunUuid(), evidence.binding());
                RunSnapshot run = requireRun(connection, command, true);
                requireBinding(evidence.binding(), run);
                requireFreezeReceipts(run, evidence);
                List<ManifestRow> manifest = requireStoredManifest(connection, run);
                if (run.state() == State.APPLIED) {
                    requireApplyReceipts(run, evidence);
                    verifyApplied(connection, run, manifest);
                    return new ApplyStart(run, manifest, true);
                }
                if (run.state() == State.FROZEN) {
                    revalidateAll(connection, manifest, ValidationPhase.PREAPPLY);
                    int changed = store.markApplying(
                            connection, run,
                            evidence.applyAuthorizationReceiptSha256(),
                            evidence.legacyRuntimeDisabledReceiptSha256());
                    if (changed != 1) {
                        throw new CoreFailure(FailureCode.CONCURRENT_STATE_CHANGE);
                    }
                    RunSnapshot applying = requireRun(connection, command, true);
                    return new ApplyStart(applying, manifest, false);
                }
                if (run.state() == State.APPLYING) {
                    requireApplyReceipts(run, evidence);
                    verifyPartialReceipts(
                            connection,
                            run,
                            manifest,
                            store.readReceipts(
                                    connection,
                                    run.migrationId(),
                                    run.migrationRunUuid()));
                    return new ApplyStart(run, manifest, false);
                }
                throw new CoreFailure(FailureCode.ILLEGAL_STATE);
            });
            attempts = Math.addExact(attempts, start.attempts());
            retries = Math.addExact(retries, start.retries());
            if (start.value().alreadyApplied()) {
                return appliedResult(
                        command, start.value().run(),
                        Outcome.ALREADY_APPLIED_ZERO_DML, attempts, retries);
            }

            for (ManifestRow row : start.value().manifest()) {
                Execution<Disposition> source = retry.execute((connection, attempt) ->
                        applyOne(connection, command, evidence, row));
                attempts = Math.addExact(attempts, source.attempts());
                retries = Math.addExact(retries, source.retries());
            }

            Execution<RunSnapshot> finish = retry.execute((connection, attempt) -> {
                requireTransactionIdentity(
                        connection, command.migrationRunUuid(), evidence.binding());
                RunSnapshot run = requireRun(connection, command, true);
                requireBinding(evidence.binding(), run);
                requireFreezeReceipts(run, evidence);
                requireApplyReceipts(run, evidence);
                if (run.state() == State.APPLIED) {
                    verifyApplied(connection, run, start.value().manifest());
                    return run;
                }
                if (run.state() != State.APPLYING || run.version() != 2) {
                    throw new CoreFailure(FailureCode.ILLEGAL_STATE);
                }
                DispositionCounts counts = verifyAppliedFacts(
                        connection, run, start.value().manifest());
                int changed = store.finalizeApplied(
                        connection, run,
                        counts.migrated(), counts.targetAlreadyPresent(),
                        counts.emptyNoop());
                if (changed != 1) {
                    throw new CoreFailure(FailureCode.CONCURRENT_STATE_CHANGE);
                }
                return requireRun(connection, command, true);
            });
            attempts = Math.addExact(attempts, finish.attempts());
            retries = Math.addExact(retries, finish.retries());
            return appliedResult(
                    command, finish.value(), Outcome.APPLIED, attempts, retries);
        } catch (TagMigrationSchemaVerifier.SchemaVerificationException failure) {
            return unavailable(command, failure.failureCode());
        } catch (JdbcTagMigrationStore.LockBusyException failure) {
            return unavailable(command, FailureCode.LOCK_BUSY);
        } catch (CoreFailure failure) {
            return unavailable(command, failure.failureCode(), attempts, retries);
        } catch (SqlOperationException failure) {
            int observedAttempts = Math.addExact(attempts, failure.attempts());
            int observedRetries = Math.addExact(retries, failure.retries());
            if (failure.kind() == FailureKind.COMMIT_OUTCOME_UNKNOWN
                    || failure.kind() == FailureKind.CLOSE) {
                return strictRecover(
                        command,
                        evidence.binding(),
                        evidence,
                        observedAttempts,
                        observedRetries,
                        FailureCode.COMMIT_OUTCOME_UNKNOWN);
            }
            return persistKnownDrift(
                    command,
                    evidence.binding(),
                    sqlFailureCode(failure),
                    observedAttempts,
                    observedRetries);
        } catch (SQLException | RuntimeException failure) {
            return strictRecover(
                    command,
                    evidence.binding(),
                    evidence,
                    attempts,
                    retries,
                    FailureCode.SQL_FAILURE);
        }
    }

    public TagMigrationResult recover(RecoveryCommand command) {
        Objects.requireNonNull(command, "command");
        VerifiedRecoveryEvidence evidence;
        try {
            evidence = Objects.requireNonNull(
                    evidenceVerifier.verifyRecovery(
                            command.migrationId(), command.migrationRunUuid(),
                            command.signedEvidence()),
                    "verified recovery evidence");
        } catch (EvidenceRejectedException | RuntimeException rejected) {
            return unavailable(command, FailureCode.EVIDENCE_REJECTED);
        }

        return strictRecover(
                command,
                evidence.binding(),
                evidence,
                1,
                0,
                FailureCode.ILLEGAL_STATE);
    }

    private Disposition applyOne(
            Connection connection,
            ApplyCommand command,
            VerifiedApplyEvidence evidence,
            ManifestRow manifest
    ) throws Exception {
        requireTransactionIdentity(
                connection, command.migrationRunUuid(), evidence.binding());
        RunSnapshot run = requireRun(connection, command, true);
        requireBinding(evidence.binding(), run);
        requireFreezeReceipts(run, evidence);
        requireApplyReceipts(run, evidence);
        if (run.state() != State.APPLYING || run.version() != 2) {
            throw new CoreFailure(FailureCode.ILLEGAL_STATE);
        }

        Optional<ReceiptSnapshot> existing = store.readReceipt(
                connection, command.migrationId(),
                command.migrationRunUuid(), manifest.sourceRowId());
        if (existing.isPresent()) {
            requireReceipt(existing.orElseThrow(), run, manifest);
            validateStoredRow(connection, manifest, ValidationPhase.FINAL);
            return manifest.disposition();
        }

        ValidatedSource source = validateStoredRow(
                connection, manifest, ValidationPhase.PREAPPLY);
        int insertedRows = manifest.disposition().insertedRows(
                manifest.planRowCount());
        store.insertReceipt(
                connection, run, manifest,
                manifest.expectedTargetDigestSha256(), insertedRows);
        if (manifest.disposition() == Disposition.MIGRATED) {
            store.insertTargetRows(connection, manifest, source.planRows());
        }
        validateStoredRow(connection, manifest, ValidationPhase.FINAL);
        return manifest.disposition();
    }

    private RunManifest buildManifest(
            Connection connection,
            PrepareCommand command,
            RunBinding binding
    ) throws Exception {
        LegacyPersonalBankTagPreflightReport preflight = command.freshPreflight();
        requirePreflightEnvelope(preflight, binding);
        List<Long> reportIds = preflight.rows().stream()
                .map(SourceRow::sourceRowId).toList();
        if (!reportIds.equals(reportIds.stream().distinct().sorted().toList())
                || !reportIds.equals(store.readReservedSourceIds(connection))) {
            throw new CoreFailure(FailureCode.PREFLIGHT_MISMATCH);
        }

        List<ManifestRow> rows = new ArrayList<>(preflight.rows().size());
        for (SourceRow expected : preflight.rows()) {
            rows.add(validatePreflightRow(connection, expected));
        }
        List<ManifestDigestRow> digestRows = rows.stream()
                .map(LegacyPersonalBankTagMigrationOperatorCore::digestRow)
                .toList();
        ManifestDigests digests = TagMigrationDigests.manifestDigests(digestRows);
        TargetIdentity identity = store.readIdentity(connection).bind(
                binding.backupManifestSha256(), command.migrationRunUuid());
        return new RunManifest(
                command.migrationId(), command.migrationRunUuid(),
                binding.backupManifestSha256(),
                identity.clusterDatabaseIdentitySha256(),
                identity.runIdentitySha256(),
                preflight.aggregateDigest(), digests, rows);
    }

    private ManifestRow validatePreflightRow(
            Connection connection,
            SourceRow expected
    ) throws Exception {
        if (expected.keyClassification() != KeyClassification.CANONICAL
                || expected.normalizedBankId().isEmpty()
                || expected.planDigest().isEmpty()
                || expected.targetDigest().isEmpty()
                || expected.membershipDigest().isEmpty()
                || !"NONE".equals(expected.failureCode())
                || expected.blocksDataApply()) {
            throw new CoreFailure(FailureCode.PREFLIGHT_MISMATCH);
        }
        ValidatedSource actual = inspectSource(
                connection, expected.sourceRowId(), expected.userId(),
                expected.normalizedBankId().orElseThrow());
        requireSourceFields(expected, actual);
        Disposition disposition = disposition(expected.outcome());
        requireDisposition(disposition, actual);
        return new ManifestRow(
                expected.sourceRowId(), expected.userId(), actual.bankId(),
                expected.keyDigest(), expected.sourceDigest(),
                expected.planDigest().orElseThrow(),
                expected.targetDigest().orElseThrow(),
                actual.preapplyTarget().operatorDigestSha256(),
                actual.expectedFinalTargetDigestSha256(),
                expected.membershipDigest().orElseThrow(),
                disposition,
                expected.definitionCount(), expected.questionBindingCount(),
                expected.distinctTagCount(), actual.planRows().size(),
                actual.preapplyTarget().rawRowCount(),
                actual.expectedFinalRows().size());
    }

    private ValidatedSource validateStoredRow(
            Connection connection,
            ManifestRow expected,
            ValidationPhase phase
    ) throws Exception {
        ValidatedSource actual = inspectSource(
                connection, expected.sourceRowId(),
                expected.userId(), expected.bankId());
        if (!expected.keyDigestSha256().equals(actual.keyDigestSha256())
                || !expected.sourceDigestSha256().equals(actual.sourceDigestSha256())) {
            throw new CoreFailure(FailureCode.SOURCE_DRIFT);
        }
        if (!expected.planDigestSha256().equals(actual.plan().planDigest())
                || expected.definitionCount() != actual.plan().definitionCount()
                || expected.questionBindingCount()
                        != actual.plan().questionBindingCount()
                || expected.distinctTagCount() != actual.plan().distinctTagCount()
                || expected.planRowCount() != actual.planRows().size()) {
            throw new CoreFailure(FailureCode.PLAN_DRIFT);
        }
        if (!expected.membershipDigestSha256().equals(
                actual.membership().membershipDigest())) {
            throw new CoreFailure(FailureCode.MEMBERSHIP_DRIFT);
        }
        if (phase == ValidationPhase.PREAPPLY) {
            if (!actual.preapplyTarget().structurallyValid()
                    || !expected.preapplyTargetDigestSha256().equals(
                            actual.preapplyTarget().operatorDigestSha256())
                    || expected.preapplyTargetRowCount()
                            != actual.preapplyTarget().rawRowCount()) {
                throw new CoreFailure(FailureCode.TARGET_MISMATCH);
            }
            requireDisposition(expected.disposition(), actual);
        } else if (!actual.preapplyTarget().structurallyValid()
                || !expected.expectedTargetDigestSha256().equals(
                        actual.preapplyTarget().operatorDigestSha256())
                || expected.expectedFinalTargetRowCount()
                        != actual.preapplyTarget().rawRowCount()) {
            throw new CoreFailure(FailureCode.TARGET_MISMATCH);
        }
        return actual;
    }

    private ValidatedSource inspectSource(
            Connection connection,
            long sourceRowId,
            long expectedUserId,
            int expectedBankId
    ) throws Exception {
        SourceSnapshot source = store.readSource(connection, sourceRowId)
                .orElseThrow(() -> new CoreFailure(FailureCode.SOURCE_DRIFT));
        if (source.userId() != expectedUserId) {
            throw new CoreFailure(FailureCode.SOURCE_DRIFT);
        }
        if (source.payloadTooLarge()) {
            throw new CoreFailure(FailureCode.SOURCE_DRIFT);
        }
        KeyAnalysis key = LegacyPersonalBankTagPreflightParser
                .analyzeReservedKey(source.key());
        if (!key.canonical() || key.normalizedBankId().isEmpty()
                || key.normalizedBankId().getAsInt() != expectedBankId) {
            throw new CoreFailure(FailureCode.SOURCE_DRIFT);
        }
        ParseResult plan;
        try {
            plan = LegacyPersonalBankTagPreflightParser.parse(source.data());
        } catch (ParseFailure invalid) {
            throw new CoreFailure(FailureCode.PLAN_DRIFT, invalid);
        }
        TargetSnapshot target = store.readTarget(
                connection, source.userId(), expectedBankId);
        if (!target.structurallyValid()) {
            throw new CoreFailure(FailureCode.TARGET_MISMATCH);
        }
        TreeSet<Integer> requested = new TreeSet<>();
        plan.rows().stream().map(TagRow::questionId)
                .filter(questionId -> questionId > 0).forEach(requested::add);
        target.positiveQuestionIds().forEach(requested::add);

        PersonalBankQuestionMembershipView membership;
        try {
            membership = Objects.requireNonNull(
                    memberships.inspectQuestionMembership(
                            expectedBankId, List.copyOf(requested)),
                    "membership result");
        } catch (RuntimeException providerFailure) {
            throw new CoreFailure(FailureCode.MEMBERSHIP_DRIFT, providerFailure);
        }
        if (membership.bankId() != expectedBankId
                || !membership.bankExists()
                || !membership.existingQuestionIds().equals(List.copyOf(requested))) {
            throw new CoreFailure(FailureCode.MEMBERSHIP_DRIFT);
        }

        List<TagRow> finalRows = java.util.stream.Stream.concat(
                        target.rows().stream(), plan.rows().stream())
                .distinct()
                .sorted(Comparator.comparingInt(TagRow::questionId)
                        .thenComparing(TagRow::tag))
                .toList();
        String sourceValue = source.data() == null
                ? "\u0000" : "\u0001" + source.data();
        return new ValidatedSource(
                expectedBankId,
                LegacyPersonalBankTagPreflightParser.sha256(source.key()),
                source.key().getBytes(StandardCharsets.UTF_8).length,
                LegacyPersonalBankTagPreflightParser.sha256(sourceValue),
                source.sourceUtf8Bytes() == null ? 0 : source.sourceUtf8Bytes(),
                plan, plan.rows(), target, membership, finalRows,
                TagMigrationDigests.targetFacts(finalRows));
    }

    private static void requireSourceFields(
            SourceRow expected,
            ValidatedSource actual
    ) throws CoreFailure {
        if (!expected.keyDigest().equals(actual.keyDigestSha256())
                || expected.keyUtf8Bytes() != actual.keyUtf8Bytes()
                || !expected.sourceDigest().equals(actual.sourceDigestSha256())
                || expected.sourceUtf8Bytes() != actual.sourceUtf8Bytes()) {
            throw new CoreFailure(FailureCode.SOURCE_DRIFT);
        }
        if (!expected.planDigest().orElseThrow().equals(actual.plan().planDigest())
                || expected.definitionCount() != actual.plan().definitionCount()
                || expected.questionBindingCount()
                        != actual.plan().questionBindingCount()
                || expected.distinctTagCount() != actual.plan().distinctTagCount()) {
            throw new CoreFailure(FailureCode.PLAN_DRIFT);
        }
        if (!expected.targetDigest().orElseThrow().equals(
                actual.preapplyTarget().legacyPreflightDigestSha256())
                || expected.targetRowCount()
                        != actual.preapplyTarget().rawRowCount()) {
            throw new CoreFailure(FailureCode.TARGET_MISMATCH);
        }
        if (expected.membershipRequestedQuestionCount()
                    != requestedQuestionCount(actual)
                || !expected.membershipDigest().orElseThrow().equals(
                        actual.membership().membershipDigest())) {
            throw new CoreFailure(FailureCode.MEMBERSHIP_DRIFT);
        }
    }

    private static int requestedQuestionCount(ValidatedSource source) {
        TreeSet<Integer> requested = new TreeSet<>();
        source.planRows().stream().map(TagRow::questionId)
                .filter(questionId -> questionId > 0).forEach(requested::add);
        source.preapplyTarget().positiveQuestionIds().forEach(requested::add);
        return requested.size();
    }

    private static void requireDisposition(
            Disposition expected,
            ValidatedSource actual
    ) throws CoreFailure {
        boolean valid = switch (expected) {
            case MIGRATED -> !actual.planRows().isEmpty()
                    && actual.preapplyTarget().rows().isEmpty();
            case EMPTY_NOOP -> actual.planRows().isEmpty()
                    && actual.preapplyTarget().rows().isEmpty();
            case TARGET_ALREADY_PRESENT -> !actual.preapplyTarget().rows().isEmpty()
                    && actual.preapplyTarget().rows().containsAll(actual.planRows());
        };
        if (!valid) {
            throw new CoreFailure(FailureCode.TARGET_MISMATCH);
        }
    }

    private static Disposition disposition(RowOutcome outcome)
            throws CoreFailure {
        return switch (outcome) {
            case MIGRATABLE -> Disposition.MIGRATED;
            case EMPTY_NOOP -> Disposition.EMPTY_NOOP;
            case TARGET_ALREADY_PRESENT -> Disposition.TARGET_ALREADY_PRESENT;
            default -> throw new CoreFailure(FailureCode.PREFLIGHT_MISMATCH);
        };
    }

    private void revalidateAll(
            Connection connection,
            List<ManifestRow> rows,
            ValidationPhase phase
    ) throws Exception {
        requireSourceSet(connection, rows);
        for (ManifestRow row : rows) {
            validateStoredRow(connection, row, phase);
        }
    }

    private DispositionCounts verifyAppliedFacts(
            Connection connection,
            RunSnapshot run,
            List<ManifestRow> manifest
    ) throws Exception {
        return verifyAppliedFacts(
                connection,
                run,
                manifest,
                store.readReceipts(
                        connection, run.migrationId(), run.migrationRunUuid()));
    }

    private DispositionCounts verifyAppliedFacts(
            Connection connection,
            RunSnapshot run,
            List<ManifestRow> manifest,
            List<ReceiptSnapshot> receipts
    ) throws Exception {
        requireSourceSet(connection, manifest);
        if (receipts.size() != manifest.size()) {
            throw new CoreFailure(FailureCode.INCOMPLETE_RECEIPTS);
        }
        for (int index = 0; index < manifest.size(); index++) {
            requireReceipt(receipts.get(index), run, manifest.get(index));
            validateStoredRow(connection, manifest.get(index), ValidationPhase.FINAL);
        }
        return DispositionCounts.from(manifest);
    }

    private void requireSourceSet(
            Connection connection,
            List<ManifestRow> manifest
    ) throws SQLException, CoreFailure {
        List<Long> expected = manifest.stream()
                .map(ManifestRow::sourceRowId)
                .toList();
        if (!expected.equals(store.readReservedSourceIds(connection))) {
            throw new CoreFailure(FailureCode.SOURCE_DRIFT);
        }
    }

    private void verifyApplied(
            Connection connection,
            RunSnapshot run,
            List<ManifestRow> manifest
    ) throws Exception {
        verifyApplied(
                connection,
                run,
                manifest,
                store.readReceipts(
                        connection, run.migrationId(), run.migrationRunUuid()));
    }

    private void verifyApplied(
            Connection connection,
            RunSnapshot run,
            List<ManifestRow> manifest,
            List<ReceiptSnapshot> receipts
    ) throws Exception {
        if (run.state() != State.APPLIED || run.version() != 3) {
            throw new CoreFailure(FailureCode.ILLEGAL_STATE);
        }
        DispositionCounts counts = verifyAppliedFacts(
                connection, run, manifest, receipts);
        if (run.migratedCount() != counts.migrated()
                || run.targetAlreadyPresentCount() != counts.targetAlreadyPresent()
                || run.emptyNoopCount() != counts.emptyNoop()) {
            throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
        }
    }

    private static void requireReceipt(
            ReceiptSnapshot receipt,
            RunSnapshot run,
            ManifestRow manifest
    ) throws CoreFailure {
        if (!receipt.matches(run, manifest)) {
            throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
        }
    }

    private static void requireReceiptBinding(
            ReceiptSnapshot receipt,
            TagMigrationCommand command,
            RunBinding binding,
            ApplyReceipts expectedReceipts
    ) throws CoreFailure {
        if (!receipt.migrationId().equals(command.migrationId())
                || !receipt.migrationRunUuid().equals(
                        command.migrationRunUuid())
                || !receipt.backupManifestSha256().equals(
                        binding.backupManifestSha256())
                || !receipt.clusterDatabaseIdentitySha256().equals(
                        binding.clusterDatabaseIdentitySha256())
                || !receipt.runIdentitySha256().equals(
                        binding.runIdentitySha256())
                || !receipt.preflightDigestSha256().equals(
                        binding.preflightDigestSha256())
                || !binding.matches(receipt.digests())
                || !receipt.sourceWriterStopReceiptSha256().equals(
                        expectedReceipts.sourceWriterStopReceiptSha256())
                || !receipt.targetWriterStopReceiptSha256().equals(
                        expectedReceipts.targetWriterStopReceiptSha256())
                || !receipt.membershipWriterStopReceiptSha256().equals(
                        expectedReceipts.membershipWriterStopReceiptSha256())
                || !receipt.connectionDrainReceiptSha256().equals(
                        expectedReceipts.connectionDrainReceiptSha256())
                || !receipt.connectionRejectionReceiptSha256().equals(
                        expectedReceipts.connectionRejectionReceiptSha256())
                || !receipt.restoredBackupReceiptSha256().equals(
                        expectedReceipts.restoredBackupReceiptSha256())
                || !receipt.applyAuthorizationReceiptSha256().equals(
                        expectedReceipts.applyAuthorizationReceiptSha256())
                || !receipt.legacyRuntimeDisabledReceiptSha256().equals(
                        expectedReceipts.legacyRuntimeDisabledReceiptSha256())) {
            throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
        }
    }

    private void verifyIncompleteRecoveryState(
            Connection connection,
            RunSnapshot run,
            List<ManifestRow> manifest,
            List<ReceiptSnapshot> receipts,
            ApplyReceipts expectedReceipts
    ) throws Exception {
        switch (run.state()) {
            case PLANNED -> {
                requireNoFreezeOrApplyReceipts(run);
                requireNoSourceReceipts(receipts);
                revalidateAll(connection, manifest, ValidationPhase.PREAPPLY);
            }
            case FROZEN -> {
                requireFreezeReceipts(run, expectedReceipts);
                requireNoApplyReceipts(run);
                requireNoSourceReceipts(receipts);
                revalidateAll(connection, manifest, ValidationPhase.PREAPPLY);
            }
            case APPLYING -> {
                requireFreezeReceipts(run, expectedReceipts);
                requireApplyReceipts(run, expectedReceipts);
                verifyPartialReceipts(connection, run, manifest, receipts);
            }
            case BLOCKED -> {
                if (run.version() == 1) {
                    requireNoFreezeOrApplyReceipts(run);
                    requireNoSourceReceipts(receipts);
                } else if (run.version() == 2) {
                    requireFreezeReceipts(run, expectedReceipts);
                    requireNoApplyReceipts(run);
                    requireNoSourceReceipts(receipts);
                } else {
                    requireFreezeReceipts(run, expectedReceipts);
                    requireApplyReceipts(run, expectedReceipts);
                    verifyPartialReceipts(connection, run, manifest, receipts);
                }
            }
            case APPLIED, UNAVAILABLE -> throw new CoreFailure(
                    FailureCode.ILLEGAL_STATE);
        }
    }

    private void verifyPartialReceipts(
            Connection connection,
            RunSnapshot run,
            List<ManifestRow> manifest,
            List<ReceiptSnapshot> receipts
    ) throws Exception {
        requireSourceSet(connection, manifest);
        if (receipts.size() > manifest.size()) {
            throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
        }
        for (int index = 0; index < manifest.size(); index++) {
            ManifestRow row = manifest.get(index);
            if (index < receipts.size()) {
                ReceiptSnapshot receipt = receipts.get(index);
                if (receipt.sourceRowId() != row.sourceRowId()) {
                    throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
                }
                requireReceipt(receipt, run, row);
                validateStoredRow(connection, row, ValidationPhase.FINAL);
            } else {
                validateStoredRow(connection, row, ValidationPhase.PREAPPLY);
            }
        }
    }

    private static void requireNoSourceReceipts(
            List<ReceiptSnapshot> receipts
    ) throws CoreFailure {
        if (!receipts.isEmpty()) {
            throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
        }
    }

    private static void requireNoFreezeOrApplyReceipts(RunSnapshot run)
            throws CoreFailure {
        if (run.sourceWriterStopReceiptSha256().isPresent()
                || run.targetWriterStopReceiptSha256().isPresent()
                || run.membershipWriterStopReceiptSha256().isPresent()
                || run.connectionDrainReceiptSha256().isPresent()
                || run.connectionRejectionReceiptSha256().isPresent()
                || run.restoredBackupReceiptSha256().isPresent()) {
            throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
        }
        requireNoApplyReceipts(run);
    }

    private static void requireNoApplyReceipts(RunSnapshot run)
            throws CoreFailure {
        if (run.applyAuthorizationReceiptSha256().isPresent()
                || run.legacyRuntimeDisabledReceiptSha256().isPresent()) {
            throw new CoreFailure(FailureCode.RECEIPT_MISMATCH);
        }
    }

    private List<ManifestRow> requireStoredManifest(
            Connection connection,
            RunSnapshot run
    ) throws Exception {
        List<ManifestRow> rows = store.readManifest(
                connection, run.migrationId(), run.migrationRunUuid());
        if (rows.size() != run.sourceCount()
                || !TagMigrationDigests.manifestDigests(
                        rows.stream().map(
                                LegacyPersonalBankTagMigrationOperatorCore::digestRow)
                                .toList()).equals(run.digests())) {
            throw new CoreFailure(FailureCode.PREFLIGHT_MISMATCH);
        }
        return rows;
    }

    private static ManifestDigestRow digestRow(ManifestRow row) {
        return new ManifestDigestRow(
                row.sourceRowId(), row.userId(), row.bankId(),
                row.sourceDigestSha256(), row.planDigestSha256(),
                row.preapplyTargetDigestSha256(),
                row.expectedTargetDigestSha256(),
                row.membershipDigestSha256());
    }

    private void requireTransactionIdentity(
            Connection connection,
            UUID migrationRunUuid,
            RunBinding binding
    ) throws Exception {
        try {
            store.verifySchema(connection);
        } catch (TagMigrationSchemaVerifier.SchemaVerificationException failure) {
            throw new CoreFailure(failure.failureCode(), failure);
        }
        DatabaseIdentityFacts facts = store.readIdentity(connection);
        requireSessionIdentity(facts, migrationRunUuid, binding);
    }

    private static void requireSessionIdentity(
            DatabaseIdentityFacts facts,
            UUID migrationRunUuid,
            RunBinding binding
    ) throws CoreFailure {
        TargetIdentity actual = facts.bind(
                binding.backupManifestSha256(), migrationRunUuid);
        if (!actual.clusterDatabaseIdentitySha256().equals(
                    binding.clusterDatabaseIdentitySha256())
                || !actual.runIdentitySha256().equals(
                    binding.runIdentitySha256())) {
            throw new CoreFailure(FailureCode.IDENTITY_MISMATCH);
        }
    }

    private RunSnapshot requireRun(
            Connection connection,
            TagMigrationCommand command,
            boolean forUpdate
    ) throws Exception {
        RunSnapshot run = store.readRun(
                        connection, command.migrationId(),
                        command.migrationRunUuid(), forUpdate)
                .orElseThrow(() -> new CoreFailure(FailureCode.ILLEGAL_STATE));
        if (!run.identityMatches(
                command.migrationId(), command.migrationRunUuid())) {
            throw new CoreFailure(FailureCode.IDENTITY_MISMATCH);
        }
        return run;
    }

    private void requireExactPreparedReplay(
            Connection connection,
            RunSnapshot run,
            RunManifest manifest,
            String prepareEvidenceReceiptSha256
    ) throws Exception {
        if (run.state() != State.PLANNED || run.version() != 0
                || !run.identityMatches(
                        manifest.migrationId(), manifest.migrationRunUuid())
                || !run.backupManifestSha256().equals(
                        manifest.backupManifestSha256())
                || !run.clusterDatabaseIdentitySha256().equals(
                        manifest.clusterDatabaseIdentitySha256())
                || !run.runIdentitySha256().equals(manifest.runIdentitySha256())
                || !run.preflightDigestSha256().equals(
                        manifest.preflightDigestSha256())
                || !run.digests().equals(manifest.digests())
                || run.sourceCount() != manifest.rows().size()
                || !run.prepareEvidenceReceiptSha256().equals(
                        prepareEvidenceReceiptSha256)
                || run.sourceWriterStopReceiptSha256().isPresent()
                || run.targetWriterStopReceiptSha256().isPresent()
                || run.membershipWriterStopReceiptSha256().isPresent()
                || run.connectionDrainReceiptSha256().isPresent()
                || run.connectionRejectionReceiptSha256().isPresent()
                || run.restoredBackupReceiptSha256().isPresent()
                || run.applyAuthorizationReceiptSha256().isPresent()
                || run.legacyRuntimeDisabledReceiptSha256().isPresent()
                || !store.readManifest(
                        connection, manifest.migrationId(),
                        manifest.migrationRunUuid()).equals(manifest.rows())) {
            throw new CoreFailure(FailureCode.ILLEGAL_STATE);
        }
    }

    private static void requireBinding(
            RunBinding binding,
            RunManifest manifest
    ) throws CoreFailure {
        if (!binding.backupManifestSha256().equals(
                    manifest.backupManifestSha256())
                || !binding.clusterDatabaseIdentitySha256().equals(
                    manifest.clusterDatabaseIdentitySha256())
                || !binding.runIdentitySha256().equals(manifest.runIdentitySha256())
                || !binding.preflightDigestSha256().equals(
                    manifest.preflightDigestSha256())
                || !binding.matches(manifest.digests())) {
            throw new CoreFailure(FailureCode.EVIDENCE_REJECTED);
        }
    }

    private static void requireBinding(
            RunBinding binding,
            RunSnapshot run
    ) throws CoreFailure {
        if (!binding.backupManifestSha256().equals(run.backupManifestSha256())
                || !binding.clusterDatabaseIdentitySha256().equals(
                    run.clusterDatabaseIdentitySha256())
                || !binding.runIdentitySha256().equals(run.runIdentitySha256())
                || !binding.preflightDigestSha256().equals(
                    run.preflightDigestSha256())
                || !binding.matches(run.digests())) {
            throw new CoreFailure(FailureCode.EVIDENCE_REJECTED);
        }
    }

    private static void requireFreezeReceipts(
            RunSnapshot run,
            FreezeReceipts evidence
    ) throws CoreFailure {
        if (!run.sourceWriterStopReceiptSha256().equals(Optional.of(
                    evidence.sourceWriterStopReceiptSha256()))
                || !run.targetWriterStopReceiptSha256().equals(Optional.of(
                    evidence.targetWriterStopReceiptSha256()))
                || !run.membershipWriterStopReceiptSha256().equals(Optional.of(
                    evidence.membershipWriterStopReceiptSha256()))
                || !run.connectionDrainReceiptSha256().equals(Optional.of(
                    evidence.connectionDrainReceiptSha256()))
                || !run.connectionRejectionReceiptSha256().equals(Optional.of(
                    evidence.connectionRejectionReceiptSha256()))
                || !run.restoredBackupReceiptSha256().equals(Optional.of(
                    evidence.restoredBackupReceiptSha256()))) {
            throw new CoreFailure(FailureCode.EVIDENCE_REJECTED);
        }
    }

    private static void requireApplyReceipts(
            RunSnapshot run,
            ApplyReceipts evidence
    ) throws CoreFailure {
        if (!run.applyAuthorizationReceiptSha256().equals(Optional.of(
                    evidence.applyAuthorizationReceiptSha256()))
                || !run.legacyRuntimeDisabledReceiptSha256().equals(Optional.of(
                    evidence.legacyRuntimeDisabledReceiptSha256()))) {
            throw new CoreFailure(FailureCode.EVIDENCE_REJECTED);
        }
    }

    private static void requirePreflightEnvelope(
            LegacyPersonalBankTagPreflightReport report,
            RunBinding binding
    ) throws CoreFailure {
        List<Long> ids = report.rows().stream().map(SourceRow::sourceRowId).toList();
        if (!report.fullSweepComplete()
                || !report.isDataEligible()
                || report.reservedRowCount() <= 0
                || report.canonicalRowCount() != report.reservedRowCount()
                || report.nearMissRowCount() != 0
                || report.normalizedCollisionRowCount() != 0
                || report.blockingRowCount() != 0
                || report.advisoryLockKey()
                        != LegacyPersonalBankTagGlobalPreflight.advisoryLockKey()
                || !ids.equals(ids.stream().distinct().sorted().toList())
                || !report.aggregateDigest().equals(recomputeAggregate(report))
                || !report.aggregateDigest().equals(
                        binding.preflightDigestSha256())) {
            throw new CoreFailure(FailureCode.PREFLIGHT_MISMATCH);
        }
    }

    private static String recomputeAggregate(
            LegacyPersonalBankTagPreflightReport report
    ) throws CoreFailure {
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

    private static MessageDigest sha256Digest() throws CoreFailure {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new CoreFailure(FailureCode.SQL_FAILURE, impossible);
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

    private TagMigrationResult strictRecover(
            TagMigrationCommand command,
            RunBinding binding,
            ApplyReceipts expectedReceipts,
            int attempts,
            int retries,
            FailureCode incompleteStateCode
    ) {
        RunSnapshot observed = null;
        try (ReadOnlyRecoverySession session = store.openRecoverySession()) {
            requireSessionIdentity(
                    session.databaseIdentity(),
                    command.migrationRunUuid(),
                    binding);
            Connection connection = session.connection();
            List<ReceiptSnapshot> receipts = store.readReceipts(
                    connection,
                    command.migrationId(),
                    command.migrationRunUuid());
            for (ReceiptSnapshot receipt : receipts) {
                requireReceiptBinding(
                        receipt, command, binding, expectedReceipts);
            }
            observed = requireRun(connection, command, false);
            requireBinding(binding, observed);
            List<ManifestRow> manifest = requireStoredManifest(
                    connection, observed);
            if (observed.state() != State.APPLIED || observed.version() != 3) {
                verifyIncompleteRecoveryState(
                        connection,
                        observed,
                        manifest,
                        receipts,
                        expectedReceipts);
                session.commit();
                return blocked(
                        observed,
                        observedFailureCode(observed, incompleteStateCode),
                        attempts,
                        retries);
            }
            requireFreezeReceipts(observed, expectedReceipts);
            requireApplyReceipts(observed, expectedReceipts);
            verifyApplied(connection, observed, manifest, receipts);
            session.commit();
            return appliedResult(
                    command,
                    observed,
                    Outcome.ALREADY_APPLIED_ZERO_DML,
                    attempts,
                    retries);
        } catch (TagMigrationSchemaVerifier.SchemaVerificationException failure) {
            return unavailable(
                    command, failure.failureCode(), attempts, retries);
        } catch (CoreFailure failure) {
            return observed == null
                    ? unavailable(
                            command, failure.failureCode(), attempts, retries)
                    : blocked(
                            observed, failure.failureCode(), attempts, retries);
        } catch (SQLException | RuntimeException failure) {
            return observed == null
                    ? unavailable(
                            command, FailureCode.SQL_FAILURE, attempts, retries)
                    : blocked(
                            observed, FailureCode.SQL_FAILURE, attempts, retries);
        } catch (Exception failure) {
            return observed == null
                    ? unavailable(
                            command, FailureCode.SQL_FAILURE, attempts, retries)
                    : blocked(
                            observed, FailureCode.SQL_FAILURE, attempts, retries);
        }
    }

    private TagMigrationResult persistKnownDrift(
            TagMigrationCommand command,
            RunBinding binding,
            FailureCode failureCode,
            int priorAttempts,
            int priorRetries
    ) {
        if (!failureCode.durableBlockEligible()) {
            return observeDurable(
                    command, binding, failureCode, priorAttempts, priorRetries);
        }
        try (OperatorSession session = store.openSession()) {
            requireSessionIdentity(
                    session.databaseIdentity(),
                    command.migrationRunUuid(),
                    binding);
            Execution<RunSnapshot> execution = retry.execute((connection, attempt) -> {
                requireTransactionIdentity(
                        connection, command.migrationRunUuid(), binding);
                RunSnapshot run = requireRun(connection, command, true);
                requireBinding(binding, run);
                if (run.state() == State.BLOCKED || run.state() == State.APPLIED) {
                    return run;
                }
                if (run.state() != State.PLANNED
                        && run.state() != State.FROZEN
                        && run.state() != State.APPLYING) {
                    throw new CoreFailure(FailureCode.ILLEGAL_STATE);
                }
                if (store.block(connection, run, failureCode) != 1) {
                    throw new CoreFailure(FailureCode.CONCURRENT_STATE_CHANGE);
                }
                RunSnapshot blockedRun = requireRun(connection, command, true);
                if (blockedRun.state() != State.BLOCKED
                        || blockedRun.blockedFailureCode().orElse(null)
                                != failureCode) {
                    throw new CoreFailure(FailureCode.CONCURRENT_STATE_CHANGE);
                }
                return blockedRun;
            });
            int attempts = Math.addExact(priorAttempts, execution.attempts());
            int retries = Math.addExact(priorRetries, execution.retries());
            RunSnapshot observed = execution.value();
            return blocked(
                    observed,
                    observedFailureCode(observed, failureCode),
                    attempts,
                    retries);
        } catch (TagMigrationSchemaVerifier.SchemaVerificationException failure) {
            return unavailable(
                    command, failure.failureCode(), priorAttempts, priorRetries);
        } catch (JdbcTagMigrationStore.LockBusyException failure) {
            return observeDurable(
                    command, binding, failureCode, priorAttempts, priorRetries);
        } catch (CoreFailure failure) {
            return unavailable(
                    command, failure.failureCode(), priorAttempts, priorRetries);
        } catch (SqlOperationException failure) {
            int attempts = Math.addExact(priorAttempts, failure.attempts());
            int retries = Math.addExact(priorRetries, failure.retries());
            return observeDurable(
                    command, binding, failureCode, attempts, retries);
        } catch (SQLException | RuntimeException failure) {
            return observeDurable(
                    command, binding, failureCode, priorAttempts, priorRetries);
        }
    }

    private TagMigrationResult observeDurable(
            TagMigrationCommand command,
            RunBinding binding,
            FailureCode failureCode,
            int attempts,
            int retries
    ) {
        try (ReadOnlyRecoverySession session = store.openRecoverySession()) {
            requireSessionIdentity(
                    session.databaseIdentity(),
                    command.migrationRunUuid(),
                    binding);
            Optional<RunSnapshot> found = store.readRun(
                    session.connection(),
                    command.migrationId(),
                    command.migrationRunUuid(),
                    false);
            if (found.isEmpty()) {
                session.commit();
                return unavailable(command, failureCode, attempts, retries);
            }
            RunSnapshot observed = found.orElseThrow();
            if (!observed.identityMatches(
                    command.migrationId(), command.migrationRunUuid())) {
                throw new CoreFailure(FailureCode.IDENTITY_MISMATCH);
            }
            requireBinding(binding, observed);
            session.commit();
            return blocked(
                    observed,
                    observedFailureCode(observed, failureCode),
                    attempts,
                    retries);
        } catch (TagMigrationSchemaVerifier.SchemaVerificationException failure) {
            return unavailable(
                    command, failure.failureCode(), attempts, retries);
        } catch (CoreFailure failure) {
            return unavailable(
                    command, failure.failureCode(), attempts, retries);
        } catch (SQLException | RuntimeException failure) {
            return unavailable(
                    command, FailureCode.SQL_FAILURE, attempts, retries);
        }
    }

    private static FailureCode observedFailureCode(
            RunSnapshot observed,
            FailureCode fallback
    ) {
        return observed.state() == State.BLOCKED
                ? observed.blockedFailureCode().orElse(fallback)
                : fallback;
    }

    private static TagMigrationResult unavailable(
            TagMigrationCommand command,
            FailureCode failureCode
    ) {
        return unavailable(command, failureCode, 0, 0);
    }

    private static TagMigrationResult unavailable(
            TagMigrationCommand command,
            FailureCode failureCode,
            int attempts,
            int retries
    ) {
        return new TagMigrationResult(
                Outcome.BLOCKED, State.UNAVAILABLE, -1,
                command.migrationId(), command.migrationRunUuid(),
                0, 0, 0, 0, attempts, retries, Optional.of(failureCode));
    }

    private static TagMigrationResult blocked(
            RunSnapshot run,
            FailureCode failureCode,
            int attempts,
            int retries
    ) {
        return new TagMigrationResult(
                Outcome.BLOCKED, run.state(), run.version(),
                run.migrationId(), run.migrationRunUuid(),
                run.sourceCount(), run.migratedCount(),
                run.targetAlreadyPresentCount(), run.emptyNoopCount(),
                attempts, retries, Optional.of(failureCode));
    }

    private static TagMigrationResult appliedResult(
            TagMigrationCommand command,
            RunSnapshot run,
            Outcome outcome,
            int attempts,
            int retries
    ) {
        return new TagMigrationResult(
                outcome, State.APPLIED, 3,
                command.migrationId(), command.migrationRunUuid(),
                run.sourceCount(), run.migratedCount(),
                run.targetAlreadyPresentCount(), run.emptyNoopCount(),
                attempts, retries, Optional.empty());
    }

    private static FailureCode sqlFailureCode(SqlOperationException failure) {
        if (failure.getCause() instanceof CoreFailure coreFailure) {
            return coreFailure.failureCode();
        }
        return failure.kind() == FailureKind.COMMIT_OUTCOME_UNKNOWN
                ? FailureCode.COMMIT_OUTCOME_UNKNOWN
                : FailureCode.SQL_FAILURE;
    }

    /** Trusted signature verification boundary; implementations are supplied externally. */
    public interface EvidenceVerifier {
        VerifiedPrepareEvidence verifyPrepare(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException;

        VerifiedFreezeEvidence verifyFreeze(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException;

        VerifiedApplyEvidence verifyApply(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException;

        VerifiedRecoveryEvidence verifyRecovery(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException;
    }

    public interface FreezeReceipts {
        String sourceWriterStopReceiptSha256();

        String targetWriterStopReceiptSha256();

        String membershipWriterStopReceiptSha256();

        String connectionDrainReceiptSha256();

        String connectionRejectionReceiptSha256();

        String restoredBackupReceiptSha256();
    }

    public interface ApplyReceipts extends FreezeReceipts {
        String applyAuthorizationReceiptSha256();

        String legacyRuntimeDisabledReceiptSha256();
    }

    public record RunBinding(
            String backupManifestSha256,
            String clusterDatabaseIdentitySha256,
            String runIdentitySha256,
            String preflightDigestSha256,
            String sourceSetDigestSha256,
            String planSetDigestSha256,
            String preapplyTargetSetDigestSha256,
            String finalTargetSetDigestSha256,
            String membershipSetDigestSha256
    ) {
        public RunBinding {
            backupManifestSha256 = requireSha(
                    backupManifestSha256, "backupManifestSha256");
            clusterDatabaseIdentitySha256 = requireSha(
                    clusterDatabaseIdentitySha256,
                    "clusterDatabaseIdentitySha256");
            runIdentitySha256 = requireSha(
                    runIdentitySha256, "runIdentitySha256");
            preflightDigestSha256 = requireSha(
                    preflightDigestSha256, "preflightDigestSha256");
            sourceSetDigestSha256 = requireSha(
                    sourceSetDigestSha256, "sourceSetDigestSha256");
            planSetDigestSha256 = requireSha(
                    planSetDigestSha256, "planSetDigestSha256");
            preapplyTargetSetDigestSha256 = requireSha(
                    preapplyTargetSetDigestSha256,
                    "preapplyTargetSetDigestSha256");
            finalTargetSetDigestSha256 = requireSha(
                    finalTargetSetDigestSha256,
                    "finalTargetSetDigestSha256");
            membershipSetDigestSha256 = requireSha(
                    membershipSetDigestSha256,
                    "membershipSetDigestSha256");
        }

        private boolean matches(ManifestDigests digests) {
            return sourceSetDigestSha256.equals(
                            digests.sourceSetDigestSha256())
                    && planSetDigestSha256.equals(
                            digests.planSetDigestSha256())
                    && preapplyTargetSetDigestSha256.equals(
                            digests.preapplyTargetSetDigestSha256())
                    && finalTargetSetDigestSha256.equals(
                            digests.finalTargetSetDigestSha256())
                    && membershipSetDigestSha256.equals(
                            digests.membershipSetDigestSha256());
        }
    }

    public record VerifiedPrepareEvidence(
            RunBinding binding,
            String prepareEvidenceReceiptSha256
    ) {
        public VerifiedPrepareEvidence {
            binding = Objects.requireNonNull(binding, "binding");
            prepareEvidenceReceiptSha256 = requireSha(
                    prepareEvidenceReceiptSha256,
                    "prepareEvidenceReceiptSha256");
        }
    }

    public record VerifiedFreezeEvidence(
            RunBinding binding,
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256,
            String connectionDrainReceiptSha256,
            String connectionRejectionReceiptSha256,
            String restoredBackupReceiptSha256
    ) implements FreezeReceipts {
        public VerifiedFreezeEvidence {
            binding = Objects.requireNonNull(binding, "binding");
            sourceWriterStopReceiptSha256 = requireSha(
                    sourceWriterStopReceiptSha256,
                    "sourceWriterStopReceiptSha256");
            targetWriterStopReceiptSha256 = requireSha(
                    targetWriterStopReceiptSha256,
                    "targetWriterStopReceiptSha256");
            membershipWriterStopReceiptSha256 = requireSha(
                    membershipWriterStopReceiptSha256,
                    "membershipWriterStopReceiptSha256");
            connectionDrainReceiptSha256 = requireSha(
                    connectionDrainReceiptSha256,
                    "connectionDrainReceiptSha256");
            connectionRejectionReceiptSha256 = requireSha(
                    connectionRejectionReceiptSha256,
                    "connectionRejectionReceiptSha256");
            restoredBackupReceiptSha256 = requireSha(
                    restoredBackupReceiptSha256,
                    "restoredBackupReceiptSha256");
            requireDistinctWriterStopReceipts(
                    sourceWriterStopReceiptSha256,
                    targetWriterStopReceiptSha256,
                    membershipWriterStopReceiptSha256);
        }
    }

    public record VerifiedApplyEvidence(
            RunBinding binding,
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256,
            String connectionDrainReceiptSha256,
            String connectionRejectionReceiptSha256,
            String restoredBackupReceiptSha256,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256
    ) implements ApplyReceipts {
        public VerifiedApplyEvidence {
            binding = Objects.requireNonNull(binding, "binding");
            sourceWriterStopReceiptSha256 = requireSha(
                    sourceWriterStopReceiptSha256,
                    "sourceWriterStopReceiptSha256");
            targetWriterStopReceiptSha256 = requireSha(
                    targetWriterStopReceiptSha256,
                    "targetWriterStopReceiptSha256");
            membershipWriterStopReceiptSha256 = requireSha(
                    membershipWriterStopReceiptSha256,
                    "membershipWriterStopReceiptSha256");
            connectionDrainReceiptSha256 = requireSha(
                    connectionDrainReceiptSha256,
                    "connectionDrainReceiptSha256");
            connectionRejectionReceiptSha256 = requireSha(
                    connectionRejectionReceiptSha256,
                    "connectionRejectionReceiptSha256");
            restoredBackupReceiptSha256 = requireSha(
                    restoredBackupReceiptSha256,
                    "restoredBackupReceiptSha256");
            applyAuthorizationReceiptSha256 = requireSha(
                    applyAuthorizationReceiptSha256,
                    "applyAuthorizationReceiptSha256");
            legacyRuntimeDisabledReceiptSha256 = requireSha(
                    legacyRuntimeDisabledReceiptSha256,
                    "legacyRuntimeDisabledReceiptSha256");
            requireDistinctWriterStopReceipts(
                    sourceWriterStopReceiptSha256,
                    targetWriterStopReceiptSha256,
                    membershipWriterStopReceiptSha256);
        }
    }

    public record VerifiedRecoveryEvidence(
            RunBinding binding,
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256,
            String connectionDrainReceiptSha256,
            String connectionRejectionReceiptSha256,
            String restoredBackupReceiptSha256,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256
    ) implements ApplyReceipts {
        public VerifiedRecoveryEvidence {
            binding = Objects.requireNonNull(binding, "binding");
            sourceWriterStopReceiptSha256 = requireSha(
                    sourceWriterStopReceiptSha256,
                    "sourceWriterStopReceiptSha256");
            targetWriterStopReceiptSha256 = requireSha(
                    targetWriterStopReceiptSha256,
                    "targetWriterStopReceiptSha256");
            membershipWriterStopReceiptSha256 = requireSha(
                    membershipWriterStopReceiptSha256,
                    "membershipWriterStopReceiptSha256");
            connectionDrainReceiptSha256 = requireSha(
                    connectionDrainReceiptSha256,
                    "connectionDrainReceiptSha256");
            connectionRejectionReceiptSha256 = requireSha(
                    connectionRejectionReceiptSha256,
                    "connectionRejectionReceiptSha256");
            restoredBackupReceiptSha256 = requireSha(
                    restoredBackupReceiptSha256,
                    "restoredBackupReceiptSha256");
            applyAuthorizationReceiptSha256 = requireSha(
                    applyAuthorizationReceiptSha256,
                    "applyAuthorizationReceiptSha256");
            legacyRuntimeDisabledReceiptSha256 = requireSha(
                    legacyRuntimeDisabledReceiptSha256,
                    "legacyRuntimeDisabledReceiptSha256");
            requireDistinctWriterStopReceipts(
                    sourceWriterStopReceiptSha256,
                    targetWriterStopReceiptSha256,
                    membershipWriterStopReceiptSha256);
        }
    }

    public static final class EvidenceRejectedException extends Exception {
        public EvidenceRejectedException() {
            super("tag migration evidence was rejected");
        }
    }

    private static String requireSha(String value, String name) {
        return TagMigrationDigests.requireSha256(value, name);
    }

    private static void requireDistinctWriterStopReceipts(
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256
    ) {
        if (sourceWriterStopReceiptSha256.equals(targetWriterStopReceiptSha256)
                || sourceWriterStopReceiptSha256.equals(
                        membershipWriterStopReceiptSha256)
                || targetWriterStopReceiptSha256.equals(
                        membershipWriterStopReceiptSha256)) {
            throw new IllegalArgumentException(
                    "writer-stop receipt digests must be pairwise distinct");
        }
    }

    private enum ValidationPhase {
        PREAPPLY,
        FINAL
    }

    private record ValidatedSource(
            int bankId,
            String keyDigestSha256,
            int keyUtf8Bytes,
            String sourceDigestSha256,
            int sourceUtf8Bytes,
            ParseResult plan,
            List<TagRow> planRows,
            TargetSnapshot preapplyTarget,
            PersonalBankQuestionMembershipView membership,
            List<TagRow> expectedFinalRows,
            String expectedFinalTargetDigestSha256
    ) {
        private ValidatedSource {
            planRows = List.copyOf(planRows);
            expectedFinalRows = List.copyOf(expectedFinalRows);
        }
    }

    private record PhaseOutcome(boolean replayed, int sourceCount) {
        private static PhaseOutcome replayed(RunSnapshot run) {
            return new PhaseOutcome(true, run.sourceCount());
        }

        private static PhaseOutcome created(int sourceCount) {
            return new PhaseOutcome(false, sourceCount);
        }
    }

    private record ApplyStart(
            RunSnapshot run,
            List<ManifestRow> manifest,
            boolean alreadyApplied
    ) {
        private ApplyStart {
            manifest = List.copyOf(manifest);
        }
    }

    private record DispositionCounts(
            int migrated,
            int targetAlreadyPresent,
            int emptyNoop
    ) {
        private static DispositionCounts from(List<ManifestRow> rows) {
            EnumMap<Disposition, Integer> counts = new EnumMap<>(Disposition.class);
            for (Disposition disposition : Disposition.values()) {
                counts.put(disposition, 0);
            }
            rows.forEach(row -> counts.compute(
                    row.disposition(), (ignored, count) -> count + 1));
            return new DispositionCounts(
                    counts.get(Disposition.MIGRATED),
                    counts.get(Disposition.TARGET_ALREADY_PRESENT),
                    counts.get(Disposition.EMPTY_NOOP));
        }
    }

    private static final class CoreFailure extends Exception {
        private final FailureCode failureCode;

        private CoreFailure(FailureCode failureCode) {
            this(failureCode, null);
        }

        private CoreFailure(FailureCode failureCode, Throwable cause) {
            super("tag migration operator phase failed", cause);
            this.failureCode = Objects.requireNonNull(
                    failureCode, "failureCode");
        }

        private FailureCode failureCode() {
            return failureCode;
        }
    }
}
