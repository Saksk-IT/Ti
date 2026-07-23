package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.ApplyClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.CommonClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.FreezeClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.FreezeReceiptClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.PrepareClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.Purpose;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.RecoveryClaims;
import io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifier.TrustedKey;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.DatabaseIdentityFacts;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.SourceSnapshot;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.TargetSnapshot;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseResult;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationCommand.SignedEvidence;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.ManifestDigestRow;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.ManifestDigests;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.TargetIdentity;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.FailureCode;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.Outcome;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.State;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.DigestInputStream;
import java.security.GeneralSecurityException;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.Signature;
import java.security.interfaces.EdECPublicKey;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.SQLFeatureNotSupportedException;
import java.sql.Statement;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.logging.Logger;
import java.util.stream.Stream;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.containers.Container.ExecResult;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

/**
 * Local disposable evidence only. Nothing in this test performs or authorizes
 * a production freeze, backup, restore, data migration, rollback, or cutover.
 */
@Testcontainers
@Execution(ExecutionMode.SAME_THREAD)
class Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT {

    private static final String OPERATOR = "ti_phase4c_tag_operator";
    private static final String LOCAL_ISSUER =
            "phase4c-local-disposable-rehearsal";
    private static final String MANIFEST_DOMAIN =
            "ti:phase4c:tag-migration:local-backup-manifest:v1";
    private static final String IDENTITY_DOMAIN =
            "ti:phase4c:tag-migration:local-database-identity:v1";
    private static final String FINGERPRINT_DOMAIN =
            "ti:phase4c:tag-migration:local-business-fingerprint:v1";
    private static final String WRITER_RECEIPT_DOMAIN =
            "ti:phase4c:tag-migration:local-writer-receipt:v1";
    private static final String RESTORE_RECEIPT_DOMAIN =
            "ti:phase4c:tag-migration:local-restore-receipt:v1";
    private static final String LEGACY_DISABLED_DOMAIN =
            "ti:phase4c:tag-migration:local-legacy-disabled:v1";
    private static final long MAX_LOCAL_DUMP_BYTES = 64L * 1024L * 1024L;

    private static final List<WriterIdentity> WRITERS = List.of(
            new WriterIdentity(
                    "legacy_web",
                    "phase4c-rehearsal-legacy-web",
                    "ti_p4c_rehearsal_legacy_web"),
            new WriterIdentity(
                    "legacy_worker",
                    "phase4c-rehearsal-legacy-worker",
                    "ti_p4c_rehearsal_legacy_worker"),
            new WriterIdentity(
                    "legacy_scheduler",
                    "phase4c-rehearsal-legacy-scheduler",
                    "ti_p4c_rehearsal_legacy_scheduler"),
            new WriterIdentity(
                    "java_web",
                    "phase4c-rehearsal-java-web",
                    "ti_p4c_rehearsal_java_web"),
            new WriterIdentity(
                    "java_worker",
                    "phase4c-rehearsal-java-worker",
                    "ti_p4c_rehearsal_java_worker"),
            new WriterIdentity(
                    "java_scheduler",
                    "phase4c-rehearsal-java-scheduler",
                    "ti_p4c_rehearsal_java_scheduler"));

    @Container
    static final PostgreSQLContainer POSTGRES_18 = rehearsalFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = rehearsalFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void localDisposableExecutionRehearsalHoldsOnPostgres18(
            @TempDir Path temporaryDirectory
    ) throws Exception {
        assertLocalDisposableRehearsal(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4",
                temporaryDirectory);
    }

    @Test
    void localDisposableExecutionRehearsalHoldsOnPostgres16(
            @TempDir Path temporaryDirectory
    ) throws Exception {
        assertLocalDisposableRehearsal(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14",
                temporaryDirectory);
    }

    private static PostgreSQLContainer rehearsalFixture(
            PostgreSQLContainer postgres
    ) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/062-personal-bank-share-list-schema.sql"),
                        "/docker-entrypoint-initdb.d/062-personal-bank-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/067-personal-bank-user-counts-schema.sql"),
                        "/docker-entrypoint-initdb.d/067-learning-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/076-legacy-personal-bank-tag-"
                                        + "operator-core-schema.sql"),
                        "/docker-entrypoint-initdb.d/076-operator-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/077-legacy-personal-bank-tag-"
                                        + "operator-core-seed.sql"),
                        "/docker-entrypoint-initdb.d/077-operator-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/078-legacy-personal-bank-tag-"
                                        + "migration-execution-protocol-schema.sql"),
                        "/docker-entrypoint-initdb.d/078-execution-protocol-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/079-legacy-personal-bank-tag-"
                                        + "migration-execution-protocol-seed.sql"),
                        "/docker-entrypoint-initdb.d/079-execution-protocol-seed.sql");
    }

    private static void assertLocalDisposableRehearsal(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion,
            Path temporaryDirectory
    ) throws Exception {
        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        DriverManagerDataSource sourceOwner = ownerDataSource(
                postgres, postgres.getDatabaseName());
        DataSource sourceOperator = new SetRoleDataSource(sourceOwner, OPERATOR);
        assertThat(queryString(sourceOwner, "SHOW server_version"))
                .isEqualTo(expectedVersion);
        assertFixtureAndOperatorAcl(sourceOwner, sourceOperator);

        DatabaseMembershipApi sourceMembership =
                new DatabaseMembershipApi(sourceOwner);
        LegacyPersonalBankTagPreflightReport sourcePreflight =
                new LegacyPersonalBankTagGlobalPreflight(
                        sourceOperator, sourceMembership).run();
        assertEligiblePreflight(sourcePreflight);
        DatabaseFingerprint sourceBefore = fingerprint(
                sourceOwner, sourceOperator);

        String suffix = UUID.randomUUID().toString()
                .replace("-", "").substring(0, 12);
        String abortDatabase = validatedIdentifier(
                "p4c_abort_" + expectedVersion.replace('.', '_') + "_" + suffix);
        String applyDatabase = validatedIdentifier(
                "p4c_apply_" + expectedVersion.replace('.', '_') + "_" + suffix);
        String recoveryDatabase = validatedIdentifier(
                "p4c_recover_" + expectedVersion.replace('.', '_') + "_" + suffix);
        String containerDump = "/tmp/p4c-tag-rehearsal-" + suffix + ".dump";
        Path hostDump = temporaryDirectory.resolve("rehearsal.dump");
        Path corruptDump = temporaryDirectory.resolve("rehearsal-corrupt.dump");
        List<String> disposableDatabases = List.of(
                abortDatabase, applyDatabase, recoveryDatabase);

        WriterFence writerFence = new WriterFence(postgres, sourceOwner);
        try {
            writerFence.installAndOpen();
            assertThat(writerFence.activeWriterCount()).isEqualTo(WRITERS.size());
            WriterFenceReceipts firstFence = writerFence.stopAndReject(
                    sourceBefore.immutableFactsSha256());
            assertThat(firstFence.allDistinct()).isTrue();
            assertThat(fingerprint(sourceOwner, sourceOperator))
                    .isEqualTo(sourceBefore);

            BackupArtifact artifact = createBackup(
                    postgres,
                    expectedImage,
                    expectedVersion,
                    sourceOwner,
                    sourceOperator,
                    sourceBefore,
                    containerDump,
                    hostDump);
            verifyArtifact(hostDump, artifact);
            proveCorruptArtifactFailsBeforeRestore(
                    hostDump, corruptDump, artifact);

            restoreIntoNewDatabase(
                    postgres, abortDatabase, containerDump);
            assertRestoredPreapplyState(
                    postgres, abortDatabase, sourceBefore, artifact);
            dropDatabase(postgres, abortDatabase);

            // This is a pre-apply local abort only. No data has moved and the
            // frozen source fingerprint must remain byte-for-byte unchanged.
            writerFence.resumeAndProbe();
            WriterFenceReceipts finalFence = writerFence.stopAndReject(
                    sourceBefore.immutableFactsSha256());
            assertThat(finalFence.allDistinct()).isTrue();
            assertThat(fingerprint(sourceOwner, sourceOperator))
                    .isEqualTo(sourceBefore);

            restoreIntoNewDatabase(
                    postgres, applyDatabase, containerDump);
            DriverManagerDataSource targetOwner = ownerDataSource(
                    postgres, applyDatabase);
            DataSource targetOperator = new SetRoleDataSource(
                    targetOwner, OPERATOR);
            assertFixtureAndOperatorAcl(targetOwner, targetOperator);
            DatabaseFingerprint targetBefore = fingerprint(
                    targetOwner, targetOperator);
            assertThat(targetBefore).isEqualTo(sourceBefore);

            DatabaseIdentityFacts sourceIdentity = identity(sourceOwner);
            DatabaseIdentityFacts targetIdentity = identity(targetOwner);
            assertThat(targetIdentity.databaseOid())
                    .isNotEqualTo(sourceIdentity.databaseOid());
            assertThat(identitySha256(targetIdentity))
                    .isNotEqualTo(identitySha256(sourceIdentity));

            LegacyPersonalBankTagPreflightReport restoredPreflight =
                    new LegacyPersonalBankTagGlobalPreflight(
                            targetOperator,
                            new DatabaseMembershipApi(targetOwner)).run();
            assertEligiblePreflight(restoredPreflight);
            assertEquivalentPreflightBusinessEvidence(
                    sourcePreflight, restoredPreflight);

            UUID migrationId = UUID.randomUUID();
            UUID migrationRunUuid = UUID.randomUUID();
            RunBinding binding = binding(
                    targetOperator,
                    restoredPreflight,
                    migrationRunUuid,
                    artifact.manifestSha256());
            FreezeReceiptClaims freezeReceipts = new FreezeReceiptClaims(
                    finalFence.sourceWriterStopReceiptSha256(),
                    finalFence.targetWriterStopReceiptSha256(),
                    finalFence.membershipWriterStopReceiptSha256(),
                    finalFence.connectionDrainReceiptSha256(),
                    finalFence.connectionRejectionReceiptSha256(),
                    sha256Fields(
                            RESTORE_RECEIPT_DOMAIN,
                            artifact.manifestSha256(),
                            identitySha256(targetIdentity),
                            targetBefore.immutableFactsSha256(),
                            targetBefore.targetFactsSha256()));
            EvidenceFixture evidence = evidenceFixture(
                    migrationId,
                    migrationRunUuid,
                    binding,
                    freezeReceipts,
                    targetBefore);

            LegacyPersonalBankTagMigrationExecutionProtocol protocol =
                    new LegacyPersonalBankTagMigrationExecutionProtocol(
                            targetOperator,
                            new DatabaseMembershipApi(targetOwner),
                            evidence.verifier());
            TagMigrationPlanCandidateFactory candidateFactory =
                    new TagMigrationPlanCandidateFactory();
            TagMigrationPlanCandidate candidate = candidateFactory.create(
                    migrationId,
                    migrationRunUuid,
                    restoredPreflight,
                    binding);
            TagMigrationPlanCandidate protocolCandidate = protocol.candidate(
                    migrationId,
                    migrationRunUuid,
                    restoredPreflight,
                    binding);
            assertThat(protocolCandidate.candidateSha256())
                    .isEqualTo(candidate.candidateSha256());

            proveWrongIdentityEvidenceFailsBeforeDml(
                    protocol,
                    candidate,
                    evidence,
                    targetOwner);

            TagMigrationResult prepared = protocol.prepare(
                    candidate, evidence.prepareEvidence());
            assertPhase(prepared, Outcome.PREPARED, State.PLANNED, 0);
            assertPhase(
                    protocol.prepare(candidate, evidence.prepareEvidence()),
                    Outcome.ALREADY_PREPARED_ZERO_DML,
                    State.PLANNED,
                    0);

            TagMigrationResult frozen = protocol.freeze(
                    candidate, evidence.freezeEvidence());
            assertPhase(frozen, Outcome.FROZEN, State.FROZEN, 1);
            assertPhase(
                    protocol.freeze(candidate, evidence.freezeEvidence()),
                    Outcome.ALREADY_FROZEN_ZERO_DML,
                    State.FROZEN,
                    1);

            TagMigrationResult applied = protocol.apply(
                    candidate, evidence.applyEvidence());
            assertPhase(applied, Outcome.APPLIED, State.APPLIED, 3);
            assertPhase(
                    protocol.apply(candidate, evidence.applyEvidence()),
                    Outcome.ALREADY_APPLIED_ZERO_DML,
                    State.APPLIED,
                    3);
            assertPhase(
                    protocol.recover(candidate, evidence.recoveryEvidence()),
                    Outcome.ALREADY_APPLIED_ZERO_DML,
                    State.APPLIED,
                    3);
            assertPhase(
                    protocol.recover(candidate, evidence.recoveryEvidence()),
                    Outcome.ALREADY_APPLIED_ZERO_DML,
                    State.APPLIED,
                    3);

            DatabaseFingerprint targetAfter = fingerprint(
                    targetOwner, targetOperator);
            assertThat(targetAfter.schemaFingerprintSha256())
                    .isEqualTo(targetBefore.schemaFingerprintSha256());
            assertThat(targetAfter.immutableFactsSha256())
                    .isEqualTo(targetBefore.immutableFactsSha256());
            assertThat(targetAfter.targetRowCount()
                    - targetBefore.targetRowCount()).isEqualTo(3);
            assertThat(targetAfter.runCount()).isOne();
            assertThat(targetAfter.receiptCount()).isEqualTo(3);
            assertThat(fingerprint(sourceOwner, sourceOperator))
                    .isEqualTo(sourceBefore);

            // Destroying the applied disposable target and restoring the same
            // snapshot only proves local archive recoverability. It is not a
            // production rollback and must not restart any legacy writer.
            dropDatabase(postgres, applyDatabase);
            restoreIntoNewDatabase(
                    postgres, recoveryDatabase, containerDump);
            assertRestoredPreapplyState(
                    postgres, recoveryDatabase, sourceBefore, artifact);
            assertThat(writerFence.activeWriterCount()).isZero();
            writerFence.assertConnectionsRejected();
            dropDatabase(postgres, recoveryDatabase);
        } finally {
            for (String database : disposableDatabases) {
                dropDatabaseIfExists(postgres, database);
            }
            writerFence.close();
            ExecResult remove = postgres.execInContainer(
                    "rm", "-f", containerDump);
            assertThat(remove.getExitCode()).isZero();
            assertThat(databaseExists(sourceOwner, abortDatabase)).isFalse();
            assertThat(databaseExists(sourceOwner, applyDatabase)).isFalse();
            assertThat(databaseExists(sourceOwner, recoveryDatabase)).isFalse();
            assertThat(writerFence.installedRoleCount()).isZero();
        }
    }

    private static void proveWrongIdentityEvidenceFailsBeforeDml(
            LegacyPersonalBankTagMigrationExecutionProtocol protocol,
            TagMigrationPlanCandidate candidate,
            EvidenceFixture evidence,
            DataSource owner
    ) throws Exception {
        int runCount = queryInt(
                owner,
                "SELECT count(*) FROM ti_migration.personal_bank_tag_run");
        SignedEvidence wrong = evidence.prepareEvidenceWithWrongBinding();
        TagMigrationResult rejected = protocol.prepare(candidate, wrong);
        assertThat(rejected.outcome()).isEqualTo(Outcome.BLOCKED);
        assertThat(rejected.state()).isEqualTo(State.UNAVAILABLE);
        assertThat(rejected.failureCode()).contains(FailureCode.EVIDENCE_REJECTED);
        assertThat(queryInt(
                owner,
                "SELECT count(*) FROM ti_migration.personal_bank_tag_run"))
                .isEqualTo(runCount);
        assertThat(queryInt(
                owner,
                "SELECT count(*) FROM ti_migration.personal_bank_tag_receipt"))
                .isZero();
    }

    private static void assertPhase(
            TagMigrationResult result,
            Outcome expectedOutcome,
            State expectedState,
            int expectedVersion
    ) {
        assertThat(result.outcome()).isEqualTo(expectedOutcome);
        assertThat(result.state()).isEqualTo(expectedState);
        assertThat(result.version()).isEqualTo(expectedVersion);
        assertThat(result.failureCode()).isEmpty();
    }

    private static EvidenceFixture evidenceFixture(
            UUID migrationId,
            UUID migrationRunUuid,
            RunBinding binding,
            FreezeReceiptClaims freezeReceipts,
            DatabaseFingerprint targetBefore
    ) throws Exception {
        Instant now = Instant.parse("2026-07-20T10:00:00Z");
        Instant keyValidFrom = now.minus(Duration.ofHours(1));
        Instant keyValidUntil = now.plus(Duration.ofHours(1));
        Instant issuedAt = now.minusSeconds(1);
        Instant expiresAt = now.plus(Duration.ofMinutes(2));

        Map<Purpose, KeyPair> pairs = new EnumMap<>(Purpose.class);
        List<TrustedKey> trustedKeys = new ArrayList<>();
        for (Purpose purpose : Purpose.values()) {
            KeyPair pair = KeyPairGenerator.getInstance("Ed25519")
                    .generateKeyPair();
            pairs.put(purpose, pair);
            trustedKeys.add(new TrustedKey(
                    keyId(purpose),
                    LOCAL_ISSUER,
                    purpose,
                    (EdECPublicKey) pair.getPublic(),
                    keyValidFrom,
                    keyValidUntil,
                    false));
        }
        Ed25519TagMigrationEvidenceVerifier verifier =
                new Ed25519TagMigrationEvidenceVerifier(
                        trustedKeys,
                        Clock.fixed(now, ZoneOffset.UTC),
                        Duration.ofSeconds(5),
                        Duration.ofMinutes(5));

        CommonClaims prepareCommon = commonClaims(
                Purpose.PREPARE,
                migrationId,
                migrationRunUuid,
                binding,
                issuedAt,
                expiresAt);
        PrepareClaims prepareClaims = new PrepareClaims(prepareCommon);
        byte[] preparePayload =
                Ed25519TagMigrationEvidenceVerifier.encodePreparePayload(
                        prepareClaims);
        SignedEvidence prepare = signedEvidence(
                Purpose.PREPARE,
                preparePayload,
                pairs.get(Purpose.PREPARE));

        CommonClaims freezeCommon = commonClaims(
                Purpose.FREEZE,
                migrationId,
                migrationRunUuid,
                binding,
                issuedAt,
                expiresAt);
        FreezeClaims freezeClaims = new FreezeClaims(
                freezeCommon, freezeReceipts);
        byte[] freezePayload =
                Ed25519TagMigrationEvidenceVerifier.encodeFreezePayload(
                        freezeClaims);
        SignedEvidence freeze = signedEvidence(
                Purpose.FREEZE,
                freezePayload,
                pairs.get(Purpose.FREEZE));

        String legacyDisabledReceipt = sha256Fields(
                LEGACY_DISABLED_DOMAIN,
                targetBefore.immutableFactsSha256(),
                freezeReceipts.sourceWriterStopReceiptSha256(),
                freezeReceipts.targetWriterStopReceiptSha256(),
                freezeReceipts.membershipWriterStopReceiptSha256());
        CommonClaims applyCommon = commonClaims(
                Purpose.APPLY,
                migrationId,
                migrationRunUuid,
                binding,
                issuedAt,
                expiresAt);
        ApplyClaims applyClaims = new ApplyClaims(
                applyCommon,
                freezeReceipts,
                legacyDisabledReceipt);
        byte[] applyPayload =
                Ed25519TagMigrationEvidenceVerifier.encodeApplyPayload(
                        applyClaims);
        SignedEvidence apply = signedEvidence(
                Purpose.APPLY,
                applyPayload,
                pairs.get(Purpose.APPLY));
        String applyAuthorizationReceipt = verifier.verifyApply(
                migrationId,
                migrationRunUuid,
                apply).applyAuthorizationReceiptSha256();

        CommonClaims recoveryCommon = commonClaims(
                Purpose.RECOVERY,
                migrationId,
                migrationRunUuid,
                binding,
                issuedAt,
                expiresAt);
        RecoveryClaims recoveryClaims = new RecoveryClaims(
                recoveryCommon,
                freezeReceipts,
                applyAuthorizationReceipt,
                legacyDisabledReceipt);
        byte[] recoveryPayload =
                Ed25519TagMigrationEvidenceVerifier.encodeRecoveryPayload(
                        recoveryClaims);
        SignedEvidence recovery = signedEvidence(
                Purpose.RECOVERY,
                recoveryPayload,
                pairs.get(Purpose.RECOVERY));

        RunBinding wrongBinding = new RunBinding(
                sha256Fields("wrong-local-manifest", binding.backupManifestSha256()),
                binding.clusterDatabaseIdentitySha256(),
                binding.runIdentitySha256(),
                binding.preflightDigestSha256(),
                binding.sourceSetDigestSha256(),
                binding.planSetDigestSha256(),
                binding.preapplyTargetSetDigestSha256(),
                binding.finalTargetSetDigestSha256(),
                binding.membershipSetDigestSha256());
        PrepareClaims wrongClaims = new PrepareClaims(commonClaims(
                Purpose.PREPARE,
                migrationId,
                migrationRunUuid,
                wrongBinding,
                issuedAt,
                expiresAt));
        SignedEvidence wrongPrepare = signedEvidence(
                Purpose.PREPARE,
                Ed25519TagMigrationEvidenceVerifier.encodePreparePayload(
                        wrongClaims),
                pairs.get(Purpose.PREPARE));
        return new EvidenceFixture(
                verifier,
                prepare,
                freeze,
                apply,
                recovery,
                wrongPrepare);
    }

    private static CommonClaims commonClaims(
            Purpose purpose,
            UUID migrationId,
            UUID migrationRunUuid,
            RunBinding binding,
            Instant issuedAt,
            Instant expiresAt
    ) {
        return new CommonClaims(
                LOCAL_ISSUER,
                keyId(purpose),
                migrationId,
                migrationRunUuid,
                UUID.randomUUID(),
                issuedAt,
                expiresAt,
                binding);
    }

    private static String keyId(Purpose purpose) {
        return "phase4c-local-" + purpose.name().toLowerCase();
    }

    private static SignedEvidence signedEvidence(
            Purpose purpose,
            byte[] canonicalPayload,
            KeyPair keyPair
    ) throws GeneralSecurityException {
        Signature signer = Signature.getInstance("Ed25519");
        signer.initSign(keyPair.getPrivate());
        signer.update(Ed25519TagMigrationEvidenceVerifier.signatureInput(
                purpose, canonicalPayload));
        byte[] signature = signer.sign();
        assertThat(signature).hasSize(64);
        return new SignedEvidence(
                keyId(purpose), canonicalPayload, signature);
    }

    private static RunBinding binding(
            DataSource operator,
            LegacyPersonalBankTagPreflightReport report,
            UUID runUuid,
            String backupManifestSha256
    ) throws Exception {
        JdbcTagMigrationStore store = new JdbcTagMigrationStore(operator);
        List<ManifestDigestRow> rows = new ArrayList<>();
        DatabaseIdentityFacts identity;
        try (Connection connection = operator.getConnection()) {
            identity = store.readIdentity(connection);
            for (LegacyPersonalBankTagPreflightReport.SourceRow row
                    : report.rows()) {
                SourceSnapshot source = store.readSource(
                                connection, row.sourceRowId())
                        .orElseThrow();
                ParseResult plan = LegacyPersonalBankTagPreflightParser
                        .parse(source.data());
                TargetSnapshot target = store.readTarget(
                        connection,
                        row.userId(),
                        row.normalizedBankId().orElseThrow());
                List<TagRow> finalRows = Stream.concat(
                                target.rows().stream(),
                                plan.rows().stream())
                        .distinct()
                        .sorted(Comparator.comparingInt(TagRow::questionId)
                                .thenComparing(TagRow::tag))
                        .toList();
                rows.add(new ManifestDigestRow(
                        row.sourceRowId(),
                        row.userId(),
                        row.normalizedBankId().orElseThrow(),
                        row.sourceDigest(),
                        row.planDigest().orElseThrow(),
                        target.operatorDigestSha256(),
                        TagMigrationDigests.targetFacts(finalRows),
                        row.membershipDigest().orElseThrow()));
            }
        }
        TargetIdentity targetIdentity = identity.bind(
                backupManifestSha256, runUuid);
        ManifestDigests digests = TagMigrationDigests.manifestDigests(rows);
        return new RunBinding(
                backupManifestSha256,
                targetIdentity.clusterDatabaseIdentitySha256(),
                targetIdentity.runIdentitySha256(),
                report.aggregateDigest(),
                digests.sourceSetDigestSha256(),
                digests.planSetDigestSha256(),
                digests.preapplyTargetSetDigestSha256(),
                digests.finalTargetSetDigestSha256(),
                digests.membershipSetDigestSha256());
    }

    private static BackupArtifact createBackup(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion,
            DataSource sourceOwner,
            DataSource sourceOperator,
            DatabaseFingerprint sourceFingerprint,
            String containerDump,
            Path hostDump
    ) throws Exception {
        ExecResult dump = postgres.execInContainer(
                "pg_dump",
                "--username", postgres.getUsername(),
                "--dbname", postgres.getDatabaseName(),
                "--format", "custom",
                "--file", containerDump);
        assertThat(dump.getExitCode()).isZero();
        postgres.copyFileFromContainer(containerDump, hostDump.toString());
        long byteCount = Files.size(hostDump);
        assertThat(byteCount).isBetween(1L, MAX_LOCAL_DUMP_BYTES);
        String artifactSha256 = sha256File(hostDump);
        String identitySha256 = identitySha256(identity(sourceOwner));
        String dumpToolSha256 = sha256Utf8(queryExecOutput(
                postgres, "pg_dump", "--version"));
        String manifestSha256 = sha256Fields(
                MANIFEST_DOMAIN,
                artifactSha256,
                Long.toString(byteCount),
                sha256Utf8(expectedImage),
                expectedVersion,
                dumpToolSha256,
                identitySha256,
                sourceFingerprint.schemaFingerprintSha256(),
                sourceFingerprint.immutableFactsSha256(),
                sourceFingerprint.targetFactsSha256(),
                Integer.toString(sourceFingerprint.targetRowCount()),
                "pg_dump-format=custom",
                "database-acl-restored-separately=true",
                "local-disposable-only=true");
        // Re-run the fixed operator verifier after the dump to prove that the
        // archive process itself did not alter the source schema or business data.
        assertThat(fingerprint(sourceOwner, sourceOperator))
                .isEqualTo(sourceFingerprint);
        return new BackupArtifact(
                artifactSha256,
                byteCount,
                manifestSha256,
                identitySha256,
                sourceFingerprint);
    }

    private static void verifyArtifact(
            Path artifact,
            BackupArtifact expected
    ) throws IOException {
        if (Files.size(artifact) != expected.artifactByteCount()
                || !sha256File(artifact).equals(expected.artifactSha256())) {
            throw new IllegalStateException(
                    "local rehearsal backup artifact was rejected");
        }
    }

    private static void proveCorruptArtifactFailsBeforeRestore(
            Path source,
            Path corrupted,
            BackupArtifact expected
    ) throws IOException {
        Files.copy(source, corrupted, StandardCopyOption.REPLACE_EXISTING);
        long size = Files.size(corrupted);
        assertThat(size).isPositive();
        try (SeekableByteChannel channel = Files.newByteChannel(
                corrupted,
                StandardOpenOption.READ,
                StandardOpenOption.WRITE)) {
            long position = Math.min(32L, size - 1L);
            channel.position(position);
            ByteBuffer original = ByteBuffer.allocate(1);
            assertThat(channel.read(original)).isOne();
            original.flip();
            byte changed = (byte) (original.get() ^ 0x01);
            channel.position(position);
            assertThat(channel.write(ByteBuffer.wrap(new byte[]{changed})))
                    .isOne();
        }
        assertThatThrownBy(() -> verifyArtifact(corrupted, expected))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("local rehearsal backup artifact was rejected");
    }

    private static void restoreIntoNewDatabase(
            PostgreSQLContainer postgres,
            String database,
            String containerDump
    ) throws Exception {
        createDatabase(postgres, database);
        ExecResult restore = postgres.execInContainer(
                "pg_restore",
                "--exit-on-error",
                "--username", postgres.getUsername(),
                "--dbname", database,
                containerDump);
        assertThat(restore.getExitCode()).isZero();
        // Database ACL is cluster state and is not safely inferred from an
        // object archive restored under a new database name.
        executeDatabaseAclBoundary(postgres, database);
    }

    private static void assertRestoredPreapplyState(
            PostgreSQLContainer postgres,
            String database,
            DatabaseFingerprint expected,
            BackupArtifact artifact
    ) throws Exception {
        DriverManagerDataSource owner = ownerDataSource(postgres, database);
        DataSource operator = new SetRoleDataSource(owner, OPERATOR);
        assertFixtureAndOperatorAcl(owner, operator);
        assertThat(fingerprint(owner, operator)).isEqualTo(expected);
        assertThat(identitySha256(identity(owner)))
                .isNotEqualTo(artifact.sourceIdentitySha256());
    }

    private static void createDatabase(
            PostgreSQLContainer postgres,
            String database
    ) throws SQLException {
        DriverManagerDataSource admin = ownerDataSource(
                postgres, postgres.getDatabaseName());
        try (Connection connection = admin.getConnection();
             Statement statement = connection.createStatement()) {
            connection.setAutoCommit(true);
            statement.execute("CREATE DATABASE " + quotedIdentifier(database)
                    + " WITH TEMPLATE template0 OWNER "
                    + quotedIdentifier(postgres.getUsername()));
        }
        executeDatabaseAclBoundary(postgres, database);
    }

    private static void executeDatabaseAclBoundary(
            PostgreSQLContainer postgres,
            String database
    ) throws SQLException {
        DriverManagerDataSource admin = ownerDataSource(
                postgres, postgres.getDatabaseName());
        try (Connection connection = admin.getConnection();
             Statement statement = connection.createStatement()) {
            connection.setAutoCommit(true);
            statement.execute("REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE "
                    + quotedIdentifier(database) + " FROM PUBLIC");
            statement.execute("REVOKE CONNECT, CREATE, TEMPORARY ON DATABASE "
                    + quotedIdentifier(database) + " FROM " + OPERATOR);
        }
    }

    private static void dropDatabaseIfExists(
            PostgreSQLContainer postgres,
            String database
    ) throws SQLException {
        DriverManagerDataSource admin = ownerDataSource(
                postgres, postgres.getDatabaseName());
        try (Connection connection = admin.getConnection()) {
            try (PreparedStatement terminate = connection.prepareStatement("""
                    SELECT pg_catalog.pg_terminate_backend(pid)
                    FROM pg_catalog.pg_stat_activity
                    WHERE datname = ?
                      AND pid <> pg_catalog.pg_backend_pid()
                    """)) {
                terminate.setString(1, database);
                terminate.execute();
            }
            try (Statement statement = connection.createStatement()) {
                connection.setAutoCommit(true);
                statement.execute("DROP DATABASE IF EXISTS "
                        + quotedIdentifier(database));
            }
        }
    }

    private static void dropDatabase(
            PostgreSQLContainer postgres,
            String database
    ) throws SQLException {
        dropDatabaseIfExists(postgres, database);
        DriverManagerDataSource admin = ownerDataSource(
                postgres, postgres.getDatabaseName());
        assertThat(databaseExists(admin, database)).isFalse();
    }

    private static boolean databaseExists(
            DataSource dataSource,
            String database
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement("""
                     SELECT EXISTS (
                         SELECT 1
                         FROM pg_catalog.pg_database
                         WHERE datname = ?
                     )
                     """)) {
            statement.setString(1, database);
            try (ResultSet row = statement.executeQuery()) {
                row.next();
                return row.getBoolean(1);
            }
        }
    }

    private static void assertFixtureAndOperatorAcl(
            DataSource owner,
            DataSource operator
    ) throws Exception {
        assertThat(queryInt(owner, """
                SELECT count(*)
                FROM phase4c_tag_execution_fixture.writer_expectation
                """)).isEqualTo(6);
        assertThat(queryInt(owner, """
                SELECT count(*)
                FROM phase4c_tag_execution_fixture.writer_domain_expectation
                """)).isEqualTo(18);
        assertThat(queryInt(owner, """
                SELECT count(*)
                FROM phase4c_tag_execution_fixture.phase_expectation
                """)).isEqualTo(4);
        assertThat(queryInt(owner, """
                SELECT count(*)
                FROM phase4c_tag_execution_fixture.acl_sentinel
                WHERE singleton
                  AND fixture_scope =
                      'local-disposable-backup-restore-rehearsal-only'
                  AND public_marker_sha256 =
                      '70e7ad017277f34c061515a53a4e7dfc62ce0d983d1459104dbf206bfb42f264'
                """)).isOne();
        assertThat(queryBoolean(operator, """
                SELECT pg_catalog.has_schema_privilege(
                    current_user,
                    'phase4c_tag_execution_fixture',
                    'USAGE')
                """)).isFalse();
        assertThat(queryInt(owner, """
                SELECT count(*)
                FROM information_schema.table_privileges
                WHERE table_schema = 'phase4c_tag_execution_fixture'
                  AND grantee IN ('PUBLIC', 'ti_phase4c_tag_operator')
                """)).isZero();
        assertThatThrownBy(() -> queryInt(operator, """
                SELECT count(*)
                FROM phase4c_tag_execution_fixture.writer_expectation
                """))
                .isInstanceOf(SQLException.class)
                .extracting(error -> ((SQLException) error).getSQLState())
                .isEqualTo("42501");
        try (Connection connection = operator.getConnection()) {
            new TagMigrationSchemaVerifier().verify(connection);
        }
    }

    private static void assertEligiblePreflight(
            LegacyPersonalBankTagPreflightReport report
    ) {
        assertThat(report.fullSweepComplete()).isTrue();
        assertThat(report.blockingRowCount()).as(report.toString()).isZero();
        assertThat(report.isDataEligible()).isTrue();
        assertThat(report.isApplyEligible()).isFalse();
        assertThat(report.reservedRowCount()).isEqualTo(3);
    }

    private static void assertEquivalentPreflightBusinessEvidence(
            LegacyPersonalBankTagPreflightReport source,
            LegacyPersonalBankTagPreflightReport restored
    ) {
        // A restored database must have a different database-identity digest,
        // so the identity-bound aggregate digest is deliberately not equal.
        // The complete classified business evidence must nevertheless match.
        assertThat(restored.databaseIdentityDigest())
                .isNotEqualTo(source.databaseIdentityDigest());
        assertThat(restored.aggregateDigest())
                .isNotEqualTo(source.aggregateDigest());
        assertThat(restored.mode()).isEqualTo(source.mode());
        assertThat(restored.status()).isEqualTo(source.status());
        assertThat(restored.advisoryLockKey())
                .isEqualTo(source.advisoryLockKey());
        assertThat(restored.reservedRowCount())
                .isEqualTo(source.reservedRowCount());
        assertThat(restored.canonicalRowCount())
                .isEqualTo(source.canonicalRowCount());
        assertThat(restored.nearMissRowCount())
                .isEqualTo(source.nearMissRowCount());
        assertThat(restored.normalizedCollisionRowCount())
                .isEqualTo(source.normalizedCollisionRowCount());
        assertThat(restored.rows()).isEqualTo(source.rows());
        assertThat(restored.outcomeCounts())
                .isEqualTo(source.outcomeCounts());
        assertThat(restored.reportingGroupCounts())
                .isEqualTo(source.reportingGroupCounts());
        assertThat(restored.globalFailures())
                .isEqualTo(source.globalFailures());
        assertThat(restored.blockingRowCount())
                .isEqualTo(source.blockingRowCount());
        assertThat(restored.applyPrerequisiteBlockers())
                .isEqualTo(source.applyPrerequisiteBlockers());
        assertThat(restored.mutationStatementCount())
                .isEqualTo(source.mutationStatementCount());
        assertThat(restored.ddlStatementCount())
                .isEqualTo(source.ddlStatementCount());
    }

    private static DatabaseFingerprint fingerprint(
            DataSource owner,
            DataSource operator
    ) throws Exception {
        String schemaFingerprint;
        try (Connection connection = operator.getConnection()) {
            schemaFingerprint = TagMigrationSchemaVerifier
                    .catalogFingerprint(connection);
        }
        MessageDigest immutable = digest(FINGERPRINT_DOMAIN + ":immutable");
        updateQuery(immutable, owner, """
                SELECT id, username, password_hash, is_locked,
                       session_version, has_password_set, email, last_active
                FROM public.users
                ORDER BY id
                """);
        updateQuery(immutable, owner, """
                SELECT id, user_id, name, status
                FROM public.user_question_banks
                ORDER BY id
                """);
        updateQuery(immutable, owner, """
                SELECT id, bank_id, user_id, type, content
                FROM public.user_bank_questions
                ORDER BY id
                """);
        updateQuery(immutable, owner, """
                SELECT id, user_id, p_key, data, created_at, updated_at
                FROM public.user_progress
                ORDER BY id
                """);
        updateQuery(immutable, owner, """
                SELECT writer_id, runtime_name, component_name,
                       application_name, local_disposable_only
                FROM phase4c_tag_execution_fixture.writer_expectation
                ORDER BY writer_id
                """);
        updateQuery(immutable, owner, """
                SELECT writer_id, writer_domain
                FROM phase4c_tag_execution_fixture.writer_domain_expectation
                ORDER BY writer_id, writer_domain
                """);
        updateQuery(immutable, owner, """
                SELECT phase_name, phase_ordinal, freeze_receipts_required,
                       apply_authorization_required,
                       legacy_runtime_disabled_required
                FROM phase4c_tag_execution_fixture.phase_expectation
                ORDER BY phase_ordinal
                """);
        updateQuery(immutable, owner, """
                SELECT singleton, fixture_scope, public_marker_sha256
                FROM phase4c_tag_execution_fixture.acl_sentinel
                ORDER BY singleton
                """);

        MessageDigest target = digest(FINGERPRINT_DOMAIN + ":target");
        updateQuery(target, owner, """
                SELECT user_id, scope, scope_id, question_id, tag,
                       created_at, updated_at
                FROM public.user_question_tag_items
                ORDER BY user_id, scope, scope_id, question_id,
                         tag COLLATE "C", created_at, updated_at
                """);
        int targetCount = queryInt(owner, """
                SELECT count(*) FROM public.user_question_tag_items
                """);
        int runCount = queryInt(owner, """
                SELECT count(*) FROM ti_migration.personal_bank_tag_run
                """);
        int receiptCount = queryInt(owner, """
                SELECT count(*) FROM ti_migration.personal_bank_tag_receipt
                """);
        return new DatabaseFingerprint(
                schemaFingerprint,
                finish(immutable),
                finish(target),
                targetCount,
                runCount,
                receiptCount);
    }

    private static void updateQuery(
            MessageDigest digest,
            DataSource dataSource,
            String sql
    ) throws SQLException {
        updateField(digest, sql);
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql);
             ResultSet rows = statement.executeQuery()) {
            ResultSetMetaData metadata = rows.getMetaData();
            int columnCount = metadata.getColumnCount();
            int rowCount = 0;
            while (rows.next()) {
                digest.update((byte) 1);
                for (int column = 1; column <= columnCount; column++) {
                    updateNullableField(digest, rows.getString(column));
                }
                rowCount++;
            }
            digest.update((byte) 0);
            digest.update(ByteBuffer.allocate(Integer.BYTES)
                    .putInt(rowCount).array());
        }
    }

    private static DatabaseIdentityFacts identity(DataSource dataSource)
            throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return new JdbcTagMigrationStore(dataSource)
                    .readIdentity(connection);
        }
    }

    private static String identitySha256(DatabaseIdentityFacts identity) {
        return sha256Fields(
                IDENTITY_DOMAIN,
                identity.systemIdentifier(),
                Long.toString(identity.databaseOid()),
                identity.serverVersion(),
                identity.serverAddress(),
                identity.serverPort());
    }

    private static DriverManagerDataSource ownerDataSource(
            PostgreSQLContainer postgres,
            String database
    ) {
        return new DriverManagerDataSource(
                jdbcUrlForDatabase(postgres.getJdbcUrl(), database),
                postgres.getUsername(),
                postgres.getPassword());
    }

    private static String jdbcUrlForDatabase(
            String jdbcUrl,
            String database
    ) {
        validatedIdentifier(database);
        String prefix = "jdbc:";
        if (!jdbcUrl.startsWith(prefix)) {
            throw new IllegalArgumentException("unexpected JDBC URL");
        }
        try {
            URI source = new URI(jdbcUrl.substring(prefix.length()));
            return prefix + new URI(
                    source.getScheme(),
                    source.getUserInfo(),
                    source.getHost(),
                    source.getPort(),
                    "/" + database,
                    source.getQuery(),
                    source.getFragment());
        } catch (URISyntaxException invalid) {
            throw new IllegalArgumentException("unexpected JDBC URL", invalid);
        }
    }

    private static String validatedIdentifier(String identifier) {
        if (!identifier.matches("[a-z][a-z0-9_]{0,62}")) {
            throw new IllegalArgumentException("invalid rehearsal identifier");
        }
        return identifier;
    }

    private static String quotedIdentifier(String identifier) {
        return '"' + validatedIdentifier(identifier) + '"';
    }

    private static int queryInt(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()) {
                throw new SQLException("integer query returned no row");
            }
            return row.getInt(1);
        }
    }

    private static String queryString(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()) {
                throw new SQLException("string query returned no row");
            }
            return row.getString(1);
        }
    }

    private static boolean queryBoolean(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(sql);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()) {
                throw new SQLException("boolean query returned no row");
            }
            return row.getBoolean(1);
        }
    }

    private static String queryExecOutput(
            PostgreSQLContainer postgres,
            String... command
    ) throws Exception {
        ExecResult result = postgres.execInContainer(command);
        assertThat(result.getExitCode()).isZero();
        return result.getStdout().strip();
    }

    private static MessageDigest digest(String domain) {
        try {
            MessageDigest result = MessageDigest.getInstance("SHA-256");
            updateField(result, domain);
            return result;
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }

    private static String sha256File(Path file) throws IOException {
        MessageDigest digest = rawSha256();
        try (InputStream input = Files.newInputStream(file);
             DigestInputStream hashing = new DigestInputStream(input, digest)) {
            hashing.transferTo(java.io.OutputStream.nullOutputStream());
        }
        return finish(digest);
    }

    private static String sha256Utf8(String value) {
        MessageDigest digest = rawSha256();
        digest.update(Objects.requireNonNull(value, "value")
                .getBytes(StandardCharsets.UTF_8));
        return finish(digest);
    }

    private static MessageDigest rawSha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }

    private static String sha256Fields(String domain, String... fields) {
        MessageDigest digest = digest(domain);
        for (String field : fields) {
            updateField(digest, field);
        }
        return finish(digest);
    }

    private static void updateField(MessageDigest digest, String value) {
        byte[] bytes = Objects.requireNonNull(value, "digest field")
                .getBytes(StandardCharsets.UTF_8);
        digest.update(ByteBuffer.allocate(Integer.BYTES)
                .putInt(bytes.length).array());
        digest.update(bytes);
    }

    private static void updateNullableField(
            MessageDigest digest,
            String value
    ) {
        digest.update((byte) (value == null ? 0 : 1));
        if (value != null) {
            updateField(digest, value);
        }
    }

    private static String finish(MessageDigest digest) {
        return HexFormat.of().formatHex(digest.digest());
    }

    private record WriterIdentity(
            String writerId,
            String applicationName,
            String roleName
    ) {
        private WriterIdentity {
            writerId = Objects.requireNonNull(writerId, "writerId");
            applicationName = Objects.requireNonNull(
                    applicationName, "applicationName");
            roleName = validatedIdentifier(roleName);
        }
    }

    private record BackupArtifact(
            String artifactSha256,
            long artifactByteCount,
            String manifestSha256,
            String sourceIdentitySha256,
            DatabaseFingerprint sourceFingerprint
    ) {
        private BackupArtifact {
            if (artifactByteCount <= 0
                    || !artifactSha256.matches("[0-9a-f]{64}")
                    || !manifestSha256.matches("[0-9a-f]{64}")
                    || !sourceIdentitySha256.matches("[0-9a-f]{64}")) {
                throw new IllegalArgumentException(
                        "invalid local backup artifact descriptor");
            }
            sourceFingerprint = Objects.requireNonNull(
                    sourceFingerprint, "sourceFingerprint");
        }
    }

    private record DatabaseFingerprint(
            String schemaFingerprintSha256,
            String immutableFactsSha256,
            String targetFactsSha256,
            int targetRowCount,
            int runCount,
            int receiptCount
    ) {
        private DatabaseFingerprint {
            if (targetRowCount < 0 || runCount < 0 || receiptCount < 0
                    || !schemaFingerprintSha256.matches("[0-9a-f]{64}")
                    || !immutableFactsSha256.matches("[0-9a-f]{64}")
                    || !targetFactsSha256.matches("[0-9a-f]{64}")) {
                throw new IllegalArgumentException(
                        "invalid local database fingerprint");
            }
        }
    }

    private record WriterFenceReceipts(
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256,
            String connectionDrainReceiptSha256,
            String connectionRejectionReceiptSha256
    ) {
        private WriterFenceReceipts {
            List.of(
                    sourceWriterStopReceiptSha256,
                    targetWriterStopReceiptSha256,
                    membershipWriterStopReceiptSha256,
                    connectionDrainReceiptSha256,
                    connectionRejectionReceiptSha256).forEach(value -> {
                        if (value == null || !value.matches("[0-9a-f]{64}")) {
                            throw new IllegalArgumentException(
                                    "invalid local writer receipt");
                        }
                    });
        }

        private boolean allDistinct() {
            return Stream.of(
                    sourceWriterStopReceiptSha256,
                    targetWriterStopReceiptSha256,
                    membershipWriterStopReceiptSha256,
                    connectionDrainReceiptSha256,
                    connectionRejectionReceiptSha256)
                    .distinct().count() == 5;
        }
    }

    private record EvidenceFixture(
            Ed25519TagMigrationEvidenceVerifier verifier,
            SignedEvidence prepareEvidence,
            SignedEvidence freezeEvidence,
            SignedEvidence applyEvidence,
            SignedEvidence recoveryEvidence,
            SignedEvidence prepareEvidenceWithWrongBinding
    ) {
        private EvidenceFixture {
            verifier = Objects.requireNonNull(verifier, "verifier");
            prepareEvidence = Objects.requireNonNull(
                    prepareEvidence, "prepareEvidence");
            freezeEvidence = Objects.requireNonNull(
                    freezeEvidence, "freezeEvidence");
            applyEvidence = Objects.requireNonNull(
                    applyEvidence, "applyEvidence");
            recoveryEvidence = Objects.requireNonNull(
                    recoveryEvidence, "recoveryEvidence");
            prepareEvidenceWithWrongBinding = Objects.requireNonNull(
                    prepareEvidenceWithWrongBinding,
                    "prepareEvidenceWithWrongBinding");
        }
    }

    private static final class WriterFence implements AutoCloseable {
        private final PostgreSQLContainer postgres;
        private final DataSource owner;
        private final Map<WriterIdentity, String> passwords =
                new LinkedHashMap<>();
        private final List<Connection> connections = new ArrayList<>();
        private final AtomicBoolean installed = new AtomicBoolean();

        private WriterFence(
                PostgreSQLContainer postgres,
                DataSource owner
        ) {
            this.postgres = postgres;
            this.owner = owner;
        }

        private void installAndOpen() throws SQLException {
            if (!installed.compareAndSet(false, true)) {
                throw new IllegalStateException("writer fence already installed");
            }
            try (Connection connection = owner.getConnection();
                 Statement statement = connection.createStatement()) {
                connection.setAutoCommit(true);
                for (WriterIdentity writer : WRITERS) {
                    String password = UUID.randomUUID().toString()
                            + UUID.randomUUID();
                    passwords.put(writer, password);
                    statement.execute("CREATE ROLE "
                            + quotedIdentifier(writer.roleName())
                            + " LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                            + "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD '"
                            + password + "'");
                    statement.execute("GRANT CONNECT ON DATABASE "
                            + quotedIdentifier(postgres.getDatabaseName())
                            + " TO " + quotedIdentifier(writer.roleName()));
                }
            }
            openAllConnections();
        }

        private void openAllConnections() throws SQLException {
            for (WriterIdentity writer : WRITERS) {
                Properties properties = new Properties();
                properties.setProperty("user", writer.roleName());
                properties.setProperty("password", passwords.get(writer));
                properties.setProperty(
                        "ApplicationName", writer.applicationName());
                Connection connection = DriverManager.getConnection(
                        postgres.getJdbcUrl(), properties);
                try (Statement statement = connection.createStatement();
                     ResultSet row = statement.executeQuery("SELECT 1")) {
                    assertThat(row.next()).isTrue();
                    assertThat(row.getInt(1)).isOne();
                }
                connections.add(connection);
            }
        }

        private int activeWriterCount() throws SQLException {
            try (Connection connection = owner.getConnection();
                 PreparedStatement statement = connection.prepareStatement("""
                         SELECT count(*)
                         FROM pg_catalog.pg_stat_activity
                         WHERE application_name = ANY (?::text[])
                         """)) {
                statement.setArray(1, connection.createArrayOf(
                        "text",
                        WRITERS.stream()
                                .map(WriterIdentity::applicationName)
                                .toArray(String[]::new)));
                try (ResultSet row = statement.executeQuery()) {
                    row.next();
                    return row.getInt(1);
                }
            }
        }

        private WriterFenceReceipts stopAndReject(
                String sourceFingerprint
        ) throws SQLException {
            closeConnections();
            try (Connection connection = owner.getConnection();
                 Statement statement = connection.createStatement()) {
                connection.setAutoCommit(true);
                for (WriterIdentity writer : WRITERS) {
                    statement.execute("REVOKE CONNECT ON DATABASE "
                            + quotedIdentifier(postgres.getDatabaseName())
                            + " FROM " + quotedIdentifier(writer.roleName()));
                    statement.execute("ALTER ROLE "
                            + quotedIdentifier(writer.roleName())
                            + " NOLOGIN");
                }
            }
            assertThat(activeWriterCount()).isZero();
            assertConnectionsRejected();
            String writerSet = WRITERS.stream()
                    .map(WriterIdentity::writerId)
                    .sorted()
                    .reduce((left, right) -> left + "," + right)
                    .orElseThrow();
            return new WriterFenceReceipts(
                    sha256Fields(
                            WRITER_RECEIPT_DOMAIN + ":source",
                            sourceFingerprint, writerSet),
                    sha256Fields(
                            WRITER_RECEIPT_DOMAIN + ":target",
                            sourceFingerprint, writerSet),
                    sha256Fields(
                            WRITER_RECEIPT_DOMAIN + ":membership",
                            sourceFingerprint, writerSet),
                    sha256Fields(
                            WRITER_RECEIPT_DOMAIN + ":drain",
                            sourceFingerprint, "active=0", writerSet),
                    sha256Fields(
                            WRITER_RECEIPT_DOMAIN + ":reject",
                            sourceFingerprint, "rejected=6", writerSet));
        }

        private void resumeAndProbe() throws SQLException {
            try (Connection connection = owner.getConnection();
                 Statement statement = connection.createStatement()) {
                connection.setAutoCommit(true);
                for (WriterIdentity writer : WRITERS) {
                    statement.execute("ALTER ROLE "
                            + quotedIdentifier(writer.roleName()) + " LOGIN");
                    statement.execute("GRANT CONNECT ON DATABASE "
                            + quotedIdentifier(postgres.getDatabaseName())
                            + " TO " + quotedIdentifier(writer.roleName()));
                }
            }
            openAllConnections();
            assertThat(activeWriterCount()).isEqualTo(WRITERS.size());
        }

        private void assertConnectionsRejected() {
            for (WriterIdentity writer : WRITERS) {
                Properties properties = new Properties();
                properties.setProperty("user", writer.roleName());
                properties.setProperty("password", passwords.get(writer));
                properties.setProperty(
                        "ApplicationName", writer.applicationName());
                assertThatThrownBy(() -> {
                    try (Connection ignored = DriverManager.getConnection(
                            postgres.getJdbcUrl(), properties)) {
                        // A successful connection is a test failure.
                    }
                }).isInstanceOf(SQLException.class);
            }
        }

        private int installedRoleCount() throws SQLException {
            if (WRITERS.isEmpty()) {
                return 0;
            }
            try (Connection connection = owner.getConnection();
                 PreparedStatement statement = connection.prepareStatement("""
                         SELECT count(*)
                         FROM pg_catalog.pg_roles
                         WHERE rolname = ANY (?::text[])
                         """)) {
                statement.setArray(1, connection.createArrayOf(
                        "text",
                        WRITERS.stream()
                                .map(WriterIdentity::roleName)
                                .toArray(String[]::new)));
                try (ResultSet row = statement.executeQuery()) {
                    row.next();
                    return row.getInt(1);
                }
            }
        }

        private void closeConnections() throws SQLException {
            SQLException failure = null;
            for (Connection connection : connections) {
                try {
                    connection.close();
                } catch (SQLException closeFailure) {
                    if (failure == null) {
                        failure = closeFailure;
                    } else {
                        failure.addSuppressed(closeFailure);
                    }
                }
            }
            connections.clear();
            if (failure != null) {
                throw failure;
            }
        }

        @Override
        public void close() throws SQLException {
            closeConnections();
            if (!installed.get()) {
                return;
            }
            try (Connection connection = owner.getConnection();
                 Statement statement = connection.createStatement()) {
                connection.setAutoCommit(true);
                for (WriterIdentity writer : WRITERS) {
                    statement.execute("REVOKE CONNECT ON DATABASE "
                            + quotedIdentifier(postgres.getDatabaseName())
                            + " FROM " + quotedIdentifier(writer.roleName()));
                    statement.execute("DROP ROLE IF EXISTS "
                            + quotedIdentifier(writer.roleName()));
                }
            } finally {
                passwords.clear();
                installed.set(false);
            }
        }
    }

    private static final class DatabaseMembershipApi
            implements PersonalBankQuestionFactsApi {
        private final DataSource dataSource;

        private DatabaseMembershipApi(DataSource dataSource) {
            this.dataSource = dataSource;
        }

        @Override
        public PersonalBankQuestionMembershipView inspectQuestionMembership(
                int bankId,
                List<Integer> questionIds
        ) {
            try (Connection connection = dataSource.getConnection()) {
                boolean bankExists;
                try (PreparedStatement statement = connection.prepareStatement("""
                        SELECT EXISTS (
                            SELECT 1
                            FROM public.user_question_banks
                            WHERE id = ?
                        )
                        """)) {
                    statement.setInt(1, bankId);
                    try (ResultSet row = statement.executeQuery()) {
                        row.next();
                        bankExists = row.getBoolean(1);
                    }
                }
                List<Integer> existing = new ArrayList<>();
                if (!questionIds.isEmpty()) {
                    try (PreparedStatement statement = connection.prepareStatement("""
                            SELECT id
                            FROM public.user_bank_questions
                            WHERE bank_id = ?
                              AND id = ANY (?::integer[])
                            ORDER BY id
                            """)) {
                        statement.setInt(1, bankId);
                        statement.setArray(2, connection.createArrayOf(
                                "integer",
                                questionIds.toArray(Integer[]::new)));
                        try (ResultSet row = statement.executeQuery()) {
                            while (row.next()) {
                                existing.add(row.getInt(1));
                            }
                        }
                    }
                }
                return PersonalBankQuestionMembershipView.create(
                        bankId, bankExists, existing);
            } catch (SQLException failure) {
                throw new IllegalStateException(
                        "test membership query failed", failure);
            }
        }

        @Override
        public PersonalBankQuestionAccessResult checkQuestionAccess(
                AuthenticatedPersonalBankViewer viewer,
                int bankId
        ) {
            throw new UnsupportedOperationException();
        }

        @Override
        public PersonalBankQuestionFactsResult summarizeQuestions(
                AuthenticatedPersonalBankViewer viewer,
                PersonalBankQuestionSelection selection
        ) {
            throw new UnsupportedOperationException();
        }
    }

    private static final class SetRoleDataSource implements DataSource {
        private final DataSource delegate;
        private final String role;

        private SetRoleDataSource(DataSource delegate, String role) {
            this.delegate = delegate;
            this.role = validatedIdentifier(role);
        }

        @Override
        public Connection getConnection() throws SQLException {
            Connection connection = delegate.getConnection();
            try (Statement statement = connection.createStatement()) {
                statement.execute("SET ROLE " + quotedIdentifier(role));
                return connection;
            } catch (SQLException failure) {
                connection.close();
                throw failure;
            }
        }

        @Override
        public Connection getConnection(String username, String password)
                throws SQLException {
            throw new SQLFeatureNotSupportedException();
        }

        @Override
        public PrintWriter getLogWriter() throws SQLException {
            return delegate.getLogWriter();
        }

        @Override
        public void setLogWriter(PrintWriter out) throws SQLException {
            delegate.setLogWriter(out);
        }

        @Override
        public void setLoginTimeout(int seconds) throws SQLException {
            delegate.setLoginTimeout(seconds);
        }

        @Override
        public int getLoginTimeout() throws SQLException {
            return delegate.getLoginTimeout();
        }

        @Override
        public Logger getParentLogger() throws SQLFeatureNotSupportedException {
            return delegate.getParentLogger();
        }

        @Override
        public <T> T unwrap(Class<T> iface) throws SQLException {
            if (iface.isInstance(this)) {
                return iface.cast(this);
            }
            return delegate.unwrap(iface);
        }

        @Override
        public boolean isWrapperFor(Class<?> iface) throws SQLException {
            return iface.isInstance(this) || delegate.isWrapperFor(iface);
        }
    }

}
