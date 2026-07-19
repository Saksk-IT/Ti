package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.io.IOException;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.SQLFeatureNotSupportedException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.logging.Logger;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

@Testcontainers
class Phase4cLegacyPersonalBankTagDurableLedgerFreezeDesignIT {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-tag-migration-durable-ledger-freeze-"
                    + "design-contract";
    private static final String CONTRACT_SHA256 =
            "995e964a32d4be1438945024acf9af7f0fb9a9ecfdab7134685e36c4d6a90041";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "fba73f917a285b85cb8fcd7afd22a94f60bac960beb508f173caf0ea96079ffa";
    private static final long CONTRACT_BYTE_COUNT = 23_110L;
    private static final String NODE_A_ANCHOR_SHA256 =
            "66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3";
    private static final String NODE_A_ANCHOR_PAYLOAD_SHA256 =
            "85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e";
    private static final String NODE_A_ANCHOR_COMMIT =
            "345deff63d2d3e867926f1e0d05d5e6d90885c4a";
    private static final String OPERATOR = "ti_phase4c_tag_design_operator";
    private static final String CLUSTER_DATABASE_DOMAIN =
            "ti:phase4c:tag-migration:cluster-database:v1";
    private static final String RUN_IDENTITY_DOMAIN =
            "ti:phase4c:tag-migration:run-identity:v1";
    private static final String MIGRATION_ID_DOMAIN =
            "ti:phase4c:tag-migration:test-migration-id:v1";
    private static final String CANONICAL_TARGET_FACTS_DOMAIN =
            "ti:phase4c:tag-migration:canonical-target-facts:v1";
    private static final String PREFLIGHT_DIGEST = "1".repeat(64);
    private static final String SOURCE_DIGEST = "2".repeat(64);
    private static final String TARGET_DIGEST = sha256((
            CANONICAL_TARGET_FACTS_DOMAIN + "\n5:981025:alpha")
            .getBytes(StandardCharsets.UTF_8));
    private static final String MEMBERSHIP_DIGEST = "4".repeat(64);
    private static final String PLAN_DIGEST = "5".repeat(64);
    private static final String SOURCE_STOP_RECEIPT = "6".repeat(64);
    private static final String TARGET_STOP_RECEIPT = "7".repeat(64);
    private static final String MEMBERSHIP_STOP_RECEIPT = "8".repeat(64);
    private static final String RESTORED_BACKUP_DIGEST = "9".repeat(64);
    private static final long EMPTY_NOOP_SOURCE_ROW_ID = 98_001L;
    private static final long MIGRATED_SOURCE_ROW_ID = 98_002L;
    private static final String SENSITIVE_CANARY_PREFIX =
            "NODEB_SENSITIVE_CANARY";
    private static final Set<String> RETRYABLE_SQLSTATES =
            Set.of("40001", "40P01");

    @Container
    static final PostgreSQLContainer POSTGRES_18 = ledgerFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = ledgerFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void durableLedgerFreezeDesignEvidenceHoldsOnPostgres18() throws Exception {
        assertCompatibility(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void durableLedgerFreezeDesignEvidenceHoldsOnPostgres16() throws Exception {
        assertCompatibility(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static PostgreSQLContainer ledgerFixture(
            PostgreSQLContainer postgres
    ) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/074-legacy-personal-bank-tag-"
                                        + "durable-ledger-freeze-design-schema.sql"),
                        "/docker-entrypoint-initdb.d/074-tag-ledger-design-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/075-legacy-personal-bank-tag-"
                                        + "durable-ledger-freeze-design-seed.sql"),
                        "/docker-entrypoint-initdb.d/075-tag-ledger-design-seed.sql");
    }

    private static void assertCompatibility(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DriverManagerDataSource owner = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        DataSource operator = new SetRoleDataSource(owner, OPERATOR);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(queryString(owner, "SHOW server_version"))
                .isEqualTo(expectedVersion);
        assertThat(queryString(operator, "SELECT current_user"))
                .isEqualTo(OPERATOR);
        assertContractParity();

        String clusterDatabaseIdentity = clusterDatabaseIdentity(owner);
        assertThat(clusterDatabaseIdentity).matches("[0-9a-f]{64}");
        String backupManifest = sha256((
                "ti:phase4c:tag-migration:test-backup-manifest:v1\u0000"
                        + expectedVersion).getBytes(StandardCharsets.UTF_8));

        proveStateMachineAndConcurrentCas(
                owner, operator, clusterDatabaseIdentity, backupManifest);
        proveAtomicApplyReplayAndAmbiguity(
                owner, operator, clusterDatabaseIdentity, backupManifest);
        proveRealSqlstatesAndBoundedRetry(owner);
        proveRestrictedAclAndSensitiveCanary(owner, operator);
    }

    private static void proveStateMachineAndConcurrentCas(
            DataSource owner,
            DataSource operator,
            String clusterIdentity,
            String backupManifest
    ) throws Exception {
        RunIdentity stateIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        insertPlanned(operator, "state-machine", stateIdentity);
        assertLedger(operator, "state-machine", "PLANNED", 0);
        assertThat(freeze(operator, "state-machine", 0, stateIdentity)).isOne();
        assertLedger(operator, "state-machine", "FROZEN", 1);
        assertThat(freeze(operator, "state-machine", 0, stateIdentity)).isZero();
        assertThat(transition(
                operator,
                "state-machine",
                "FROZEN",
                1,
                "APPLYING",
                stateIdentity)).isOne();
        assertLedger(operator, "state-machine", "APPLYING", 2);
        SQLException emptyApplied = captureSqlException(() -> transition(
                operator,
                "state-machine",
                "APPLYING",
                2,
                "APPLIED",
                stateIdentity));
        assertThat(emptyApplied.getSQLState()).isEqualTo("23514");
        assertLedger(operator, "state-machine", "APPLYING", 2);
        SQLException frozenReceiptRewrite = captureSqlException(() -> executeUpdate(
                operator,
                """
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'APPLIED',
                    version = 3,
                    source_writer_stop_receipt_sha256 = repeat('f', 64),
                    updated_at = clock_timestamp()
                WHERE migration_id = '%s'
                """.formatted(migrationUuid("state-machine"))));
        assertThat(frozenReceiptRewrite.getSQLState()).isEqualTo("23514");
        assertLedger(operator, "state-machine", "APPLYING", 2);

        RunIdentity illegalIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        insertPlanned(operator, "illegal-transition", illegalIdentity);
        SQLException forgedInitialState = captureSqlException(() -> executeUpdate(
                operator,
                """
                INSERT INTO phase4c_tag_migration_design_ledger
                SELECT '%s'::uuid,
                       'APPLIED',
                       3,
                       '00000000-0000-0000-0000-000000000001'::uuid,
                       backup_manifest_sha256,
                       cluster_database_identity_sha256,
                       database_identity_sha256,
                       preflight_digest_sha256,
                       plan_digest_sha256,
                       source_digest_sha256,
                       target_digest_sha256,
                       membership_digest_sha256,
                       repeat('6', 64),
                       repeat('7', 64),
                       repeat('8', 64),
                       repeat('9', 64),
                       NULL,
                       clock_timestamp(),
                       clock_timestamp()
                FROM phase4c_tag_migration_design_ledger
                WHERE migration_id = '%s'
                """.formatted(
                        migrationUuid("forged-applied"),
                        migrationUuid("illegal-transition"))));
        assertThat(forgedInitialState.getSQLState()).isEqualTo("23514");
        SQLException sensitiveMigrationId = captureSqlException(() -> executeUpdate(
                operator,
                """
                INSERT INTO phase4c_tag_migration_design_ledger
                SELECT 'NODEB_SENSITIVE_CANARY_MIGRATION_ID'::uuid,
                       'PLANNED',
                       0,
                       gen_random_uuid(),
                       backup_manifest_sha256,
                       cluster_database_identity_sha256,
                       database_identity_sha256,
                       preflight_digest_sha256,
                       plan_digest_sha256,
                       source_digest_sha256,
                       target_digest_sha256,
                       membership_digest_sha256,
                       NULL,
                       NULL,
                       NULL,
                       NULL,
                       NULL,
                       clock_timestamp(),
                       clock_timestamp()
                FROM phase4c_tag_migration_design_ledger
                WHERE migration_id = '%s'
                """.formatted(migrationUuid("illegal-transition"))));
        assertThat(sensitiveMigrationId.getSQLState()).isEqualTo("22P02");
        SQLException illegal = captureSqlException(() -> executeUpdate(
                operator,
                """
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'APPLIED', version = 1, updated_at = clock_timestamp()
                WHERE migration_id = '%s'
                """.formatted(migrationUuid("illegal-transition"))));
        assertThat(illegal.getSQLState()).isEqualTo("23514");
        assertLedger(operator, "illegal-transition", "PLANNED", 0);

        SQLException sensitiveBlockedCode = captureSqlException(() -> executeUpdate(
                operator,
                """
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'BLOCKED',
                    version = 1,
                    blocked_code = 'NODEB_SENSITIVE_CANARY_ARBITRARY_MESSAGE',
                    updated_at = clock_timestamp()
                WHERE migration_id = '%s'
                """.formatted(migrationUuid("illegal-transition"))));
        assertThat(sensitiveBlockedCode.getSQLState()).isEqualTo("23514");
        assertLedger(operator, "illegal-transition", "PLANNED", 0);

        SQLException immutable = captureSqlException(() -> executeUpdate(
                operator,
                """
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'BLOCKED',
                    version = 1,
                    blocked_code = 'IDENTITY_MISMATCH',
                    database_identity_sha256 = repeat('f', 64),
                    updated_at = clock_timestamp()
                WHERE migration_id = '%s'
                """.formatted(migrationUuid("illegal-transition"))));
        assertThat(immutable.getSQLState()).isEqualTo("23514");
        assertLedger(operator, "illegal-transition", "PLANNED", 0);

        RunIdentity raceIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        insertPlanned(operator, "concurrent-race", raceIdentity);
        int raceRowsBefore = mutationAuditCount(owner, "concurrent-race");
        int raceStatementsBefore = businessStatementAuditCount(owner);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch release = new CountDownLatch(1);
        try {
            List<Future<Integer>> futures = new ArrayList<>();
            for (int index = 0; index < 2; index++) {
                futures.add(pool.submit(() -> {
                    ready.countDown();
                    assertThat(release.await(5, TimeUnit.SECONDS)).isTrue();
                    return freeze(operator, "concurrent-race", 0, raceIdentity);
                }));
            }
            assertThat(ready.await(5, TimeUnit.SECONDS)).isTrue();
            release.countDown();
            List<Integer> results = List.of(
                    futures.get(0).get(10, TimeUnit.SECONDS),
                    futures.get(1).get(10, TimeUnit.SECONDS));
            assertThat(results).containsExactlyInAnyOrder(1, 0);
        } finally {
            pool.shutdownNow();
            assertThat(pool.awaitTermination(5, TimeUnit.SECONDS)).isTrue();
        }
        assertLedger(operator, "concurrent-race", "FROZEN", 1);

        assertThat(mutationAuditCount(owner, "concurrent-race") - raceRowsBefore)
                .isOne();
        assertThat(businessStatementAuditCount(owner) - raceStatementsBefore)
                .isEqualTo(2);
        assertThat(queryInt(owner, """
                SELECT count(*)
                FROM phase4c_tag_migration_design_mutation_audit
                WHERE migration_id = '%s'
                  AND relation_name = 'phase4c_tag_migration_design_ledger'
                  AND operation = 'UPDATE'
                """.formatted(migrationUuid("concurrent-race")))).isOne();

        int beforeConflictRows = mutationAuditCount(owner, "concurrent-race");
        int beforeConflictStatements = businessStatementAuditCount(owner);
        assertThat(executeUpdate(operator, """
                INSERT INTO phase4c_tag_migration_design_ledger (
                    migration_id,
                    state,
                    version,
                    migration_run_uuid,
                    backup_manifest_sha256,
                    cluster_database_identity_sha256,
                    database_identity_sha256,
                    preflight_digest_sha256,
                    plan_digest_sha256,
                    source_digest_sha256,
                    target_digest_sha256,
                    membership_digest_sha256
                )
                SELECT migration_id,
                       'PLANNED',
                       0,
                       '00000000-0000-0000-0000-000000000002'::uuid,
                       backup_manifest_sha256,
                       cluster_database_identity_sha256,
                       database_identity_sha256,
                       preflight_digest_sha256,
                       plan_digest_sha256,
                       source_digest_sha256,
                       target_digest_sha256,
                       membership_digest_sha256
                FROM phase4c_tag_migration_design_ledger
                WHERE migration_id = '%s'
                ON CONFLICT (migration_id) DO NOTHING
                """.formatted(migrationUuid("concurrent-race")))).isZero();
        assertThat(mutationAuditCount(owner, "concurrent-race"))
                .isEqualTo(beforeConflictRows);
        assertThat(businessStatementAuditCount(owner))
                .isEqualTo(beforeConflictStatements + 1);

        RunIdentity plannedBlocked = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        insertPlanned(operator, "blocked-from-planned", plannedBlocked);
        assertThat(block(
                operator,
                "blocked-from-planned",
                "PLANNED",
                0,
                plannedBlocked)).isOne();
        assertLedger(operator, "blocked-from-planned", "BLOCKED", 1);

        RunIdentity frozenBlocked = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        insertPlanned(operator, "blocked-from-frozen", frozenBlocked);
        assertThat(freeze(operator, "blocked-from-frozen", 0, frozenBlocked))
                .isOne();
        assertThat(block(
                operator,
                "blocked-from-frozen",
                "FROZEN",
                1,
                frozenBlocked)).isOne();
        assertLedger(operator, "blocked-from-frozen", "BLOCKED", 2);

        RunIdentity applyingBlocked = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        prepareApplying(operator, "blocked-from-applying", applyingBlocked);
        assertThat(block(
                operator,
                "blocked-from-applying",
                "APPLYING",
                2,
                applyingBlocked)).isOne();
        assertLedger(operator, "blocked-from-applying", "BLOCKED", 3);
        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                """
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'BLOCKED',
                    version = 4,
                    blocked_code = 'ILLEGAL_STATE',
                    updated_at = clock_timestamp()
                WHERE migration_id = '%s'
                """.formatted(migrationUuid("blocked-from-applying"))))
                .getSQLState()).isEqualTo("23514");
        assertLedger(operator, "blocked-from-applying", "BLOCKED", 3);
    }

    private static void proveAtomicApplyReplayAndAmbiguity(
            DataSource owner,
            DataSource operator,
            String clusterIdentity,
            String backupManifest
    ) throws Exception {
        RunIdentity plannedIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        insertPlanned(operator, "planned-receipt-rejected", plannedIdentity);
        assertThat(captureSqlException(() -> {
            try (Connection connection = operator.getConnection()) {
                insertReceipt(
                        connection,
                        "planned-receipt-rejected",
                        98_002L,
                        plannedIdentity);
            }
        }).getSQLState()).isEqualTo("23514");
        assertThat(recoverReceiptFirst(
                operator,
                "planned-receipt-rejected",
                98_002L,
                plannedIdentity)).isEqualTo(RecoveryDisposition.BLOCKED_NO_RECEIPT);

        RunIdentity partialIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        prepareApplying(operator, "partial-receipt-rejected", partialIdentity);
        assertThat(captureSqlException(() -> {
            try (Connection connection = operator.getConnection()) {
                insertTarget(
                        connection,
                        "partial-receipt-rejected",
                        98_002L);
            }
        }).getSQLState()).isEqualTo("23503");
        assertThat(captureSqlException(() -> {
            try (Connection connection = operator.getConnection()) {
                insertReceipt(
                        connection,
                        "partial-receipt-rejected",
                        98_002L,
                        partialIdentity,
                        "f".repeat(64));
            }
        }).getSQLState()).isEqualTo("23514");
        assertThat(attemptPartialReceiptCommit(
                operator,
                "partial-receipt-rejected",
                98_002L,
                partialIdentity).getSQLState()).isEqualTo("23514");
        assertThat(countReceipt(owner, "partial-receipt-rejected", 98_002L))
                .isZero();
        assertThat(countTarget(owner, "partial-receipt-rejected", 98_002L))
                .isZero();
        assertThat(recoverReceiptFirst(
                operator,
                "partial-receipt-rejected",
                98_002L,
                partialIdentity)).isEqualTo(RecoveryDisposition.BLOCKED_NO_RECEIPT);

        RunIdentity countMismatchIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        prepareApplying(operator, "target-count-rejected", countMismatchIdentity);
        assertThat(attemptAppliedWithoutTargetCommit(
                operator,
                "target-count-rejected",
                98_002L,
                countMismatchIdentity).getSQLState()).isEqualTo("23514");
        assertLedger(operator, "target-count-rejected", "APPLYING", 2);
        assertThat(countReceipt(owner, "target-count-rejected", 98_002L))
                .isZero();
        assertThat(countTarget(owner, "target-count-rejected", 98_002L))
                .isZero();

        RunIdentity forgedFactIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        prepareApplying(operator, "forged-target-fact", forgedFactIdentity);
        assertThat(attemptWrongCanonicalTargetFact(
                operator,
                "forged-target-fact",
                MIGRATED_SOURCE_ROW_ID,
                forgedFactIdentity).getSQLState()).isEqualTo("23514");
        assertLedger(operator, "forged-target-fact", "APPLYING", 2);
        assertThat(countReceipt(
                owner, "forged-target-fact", EMPTY_NOOP_SOURCE_ROW_ID)).isZero();
        assertThat(countReceipt(
                owner, "forged-target-fact", MIGRATED_SOURCE_ROW_ID)).isZero();
        assertThat(countTarget(
                owner, "forged-target-fact", MIGRATED_SOURCE_ROW_ID)).isZero();
        assertThat(block(
                operator,
                "forged-target-fact",
                "APPLYING",
                2,
                "TARGET_MISMATCH",
                forgedFactIdentity)).isOne();
        assertLedger(operator, "forged-target-fact", "BLOCKED", 3);

        RunIdentity atomicIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        prepareApplying(operator, "atomic-apply", atomicIdentity);

        applyTransaction(operator, "atomic-apply", 98_002L, atomicIdentity, false);
        assertLedger(operator, "atomic-apply", "APPLYING", 2);
        assertThat(countReceipt(owner, "atomic-apply", 98_002L)).isZero();
        assertThat(countTarget(owner, "atomic-apply", 98_002L)).isZero();

        applyTransaction(operator, "atomic-apply", 98_002L, atomicIdentity, true);
        assertLedger(operator, "atomic-apply", "APPLIED", 3);
        assertThat(countReceipt(
                owner, "atomic-apply", EMPTY_NOOP_SOURCE_ROW_ID)).isOne();
        assertThat(countTarget(
                owner, "atomic-apply", EMPTY_NOOP_SOURCE_ROW_ID)).isZero();
        assertThat(countReceipt(owner, "atomic-apply", 98_002L)).isOne();
        assertThat(countTarget(owner, "atomic-apply", 98_002L)).isOne();
        assertThat(queryString(owner, """
                SELECT disposition
                FROM phase4c_tag_migration_design_receipt
                WHERE migration_id = '%s'
                  AND source_row_id = %d
                """.formatted(
                        migrationUuid("atomic-apply"),
                        EMPTY_NOOP_SOURCE_ROW_ID))).isEqualTo("EMPTY_NOOP");
        assertThat(queryString(owner, """
                SELECT phase4c_tag_migration_design_canonical_target_digest(
                    '%s'::uuid
                )
                """.formatted(migrationUuid("atomic-apply"))))
                .isEqualTo(TARGET_DIGEST);
        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                """
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'BLOCKED',
                    version = 4,
                    blocked_code = 'ILLEGAL_STATE',
                    updated_at = clock_timestamp()
                WHERE migration_id = '%s'
                """.formatted(migrationUuid("atomic-apply"))))
                .getSQLState()).isEqualTo("23514");
        assertLedger(operator, "atomic-apply", "APPLIED", 3);
        assertThat(captureSqlException(() -> {
            try (Connection connection = operator.getConnection()) {
                insertReceipt(
                        connection,
                        "atomic-apply",
                        98_001L,
                        atomicIdentity);
            }
        }).getSQLState()).isEqualTo("23514");

        int beforeReplayAudit = mutationAuditCount(owner, "atomic-apply");
        int beforeReplayStatements = businessStatementAuditCount(owner);
        RunIdentity freshAtomicIdentity = runIdentity(
                atomicIdentity.runUuid(),
                atomicIdentity.backupManifestSha256(),
                clusterDatabaseIdentity(owner));
        assertThat(freshAtomicIdentity).isEqualTo(atomicIdentity);
        assertThat(recoverReceiptFirst(
                operator, "atomic-apply", 98_002L, freshAtomicIdentity))
                .isEqualTo(RecoveryDisposition.COMMITTED_ZERO_DML);
        assertThat(mutationAuditCount(owner, "atomic-apply"))
                .isEqualTo(beforeReplayAudit);
        assertThat(businessStatementAuditCount(owner))
                .isEqualTo(beforeReplayStatements);

        RunIdentity wrongRecovery = runIdentity(
                atomicIdentity.runUuid(),
                "f".repeat(64),
                clusterIdentity);
        assertThat(recoverReceiptFirst(
                operator, "atomic-apply", 98_002L, wrongRecovery))
                .isEqualTo(RecoveryDisposition.BLOCKED_IDENTITY_MISMATCH);
        RunIdentity wrongRunUuid = runIdentity(
                UUID.randomUUID(),
                atomicIdentity.backupManifestSha256(),
                clusterIdentity);
        assertThat(recoverReceiptFirst(
                operator, "atomic-apply", 98_002L, wrongRunUuid))
                .isEqualTo(RecoveryDisposition.BLOCKED_IDENTITY_MISMATCH);
        RunIdentity wrongCluster = runIdentity(
                atomicIdentity.runUuid(),
                atomicIdentity.backupManifestSha256(),
                "e".repeat(64));
        assertThat(recoverReceiptFirst(
                operator, "atomic-apply", 98_002L, wrongCluster))
                .isEqualTo(RecoveryDisposition.BLOCKED_IDENTITY_MISMATCH);
        assertThat(mutationAuditCount(owner, "atomic-apply"))
                .isEqualTo(beforeReplayAudit);
        assertThat(businessStatementAuditCount(owner))
                .isEqualTo(beforeReplayStatements);

        executeUpdate(owner, """
                UPDATE phase4c_tag_migration_design_target
                SET tag = 'beta'
                WHERE migration_id = '%s'
                  AND source_row_id = 98002
                """.formatted(migrationUuid("atomic-apply")));
        int beforeMismatchRecoveryRows = mutationAuditCount(owner, "atomic-apply");
        int beforeMismatchRecoveryStatements = businessStatementAuditCount(owner);
        assertThat(recoverReceiptFirst(
                operator, "atomic-apply", 98_002L, freshAtomicIdentity))
                .isEqualTo(
                        RecoveryDisposition.BLOCKED_RECEIPT_OR_TARGET_MISMATCH);
        assertThat(mutationAuditCount(owner, "atomic-apply"))
                .isEqualTo(beforeMismatchRecoveryRows);
        assertThat(businessStatementAuditCount(owner))
                .isEqualTo(beforeMismatchRecoveryStatements);

        RunIdentity ambiguousIdentity = runIdentity(
                UUID.randomUUID(), backupManifest, clusterIdentity);
        prepareApplying(operator, "ack-discard", ambiguousIdentity);
        assertThatThrownBy(() -> commitThenDiscardAckFixture(
                operator, "ack-discard", 98_002L, ambiguousIdentity))
                .isInstanceOf(AckDiscardedAfterCommitFixtureException.class)
                .hasMessage("test fixture discarded commit acknowledgement");
        assertLedger(operator, "ack-discard", "APPLIED", 3);
        assertThat(countReceipt(owner, "ack-discard", 98_002L)).isOne();
        assertThat(countTarget(owner, "ack-discard", 98_002L)).isOne();

        int beforeRecoveryAudit = mutationAuditCount(owner, "ack-discard");
        int beforeRecoveryStatements = businessStatementAuditCount(owner);
        RunIdentity freshAmbiguousIdentity = runIdentity(
                ambiguousIdentity.runUuid(),
                ambiguousIdentity.backupManifestSha256(),
                clusterDatabaseIdentity(owner));
        assertThat(freshAmbiguousIdentity).isEqualTo(ambiguousIdentity);
        assertThat(recoverReceiptFirst(
                operator, "ack-discard", 98_002L, freshAmbiguousIdentity))
                .isEqualTo(RecoveryDisposition.COMMITTED_ZERO_DML);
        assertThat(mutationAuditCount(owner, "ack-discard"))
                .isEqualTo(beforeRecoveryAudit);
        assertThat(businessStatementAuditCount(owner))
                .isEqualTo(beforeRecoveryStatements);
    }

    private static void proveRealSqlstatesAndBoundedRetry(DataSource owner)
            throws Exception {
        RetryTrace deadlockTrace = new RetryTrace();
        int deadlockResult = withBoundedTransactionRetry(
                owner, (connection, attempt) -> {
            if (attempt == 1) {
                try {
                    throw provokeDeadlock(owner);
                } catch (SQLException error) {
                    assertThat(error.getSQLState()).isEqualTo("40P01");
                    throw error;
                } catch (Exception error) {
                    throw new AssertionError(
                            "real PostgreSQL deadlock fixture failed", error);
                }
            }
            return queryInt(connection, "SELECT 1");
        }, deadlockTrace);
        assertThat(deadlockResult).isOne();
        assertThat(deadlockTrace.attempts).isEqualTo(2);
        assertThat(deadlockTrace.retries).isOne();
        assertFreshTransactions(deadlockTrace);

        RetryTrace serializationTrace = new RetryTrace();
        int serializationResult = withBoundedTransactionRetry(
                owner, (connection, attempt) -> {
            if (attempt == 1) {
                provokeSerializationFailureOn(connection, owner);
            }
            return queryInt(connection, "SELECT 1");
        }, serializationTrace);
        assertThat(serializationResult).isOne();
        assertThat(serializationTrace.attempts).isEqualTo(2);
        assertThat(serializationTrace.retries).isOne();
        assertFreshTransactions(serializationTrace);

        assertThat(isRetryableSqlstate("40P01")).isTrue();
        assertThat(isRetryableSqlstate("40001")).isTrue();

        RetryTrace exhaustedTrace = new RetryTrace();
        assertThatThrownBy(() -> withBoundedTransactionRetry(
                owner,
                (connection, attempt) -> {
                    provokeSerializationFailureOn(connection, owner);
                    return 0;
                },
                exhaustedTrace))
                .isInstanceOfSatisfying(SQLException.class, error ->
                        assertThat(error.getSQLState()).isEqualTo("40001"));
        assertThat(exhaustedTrace.attempts).isEqualTo(3);
        assertThat(exhaustedTrace.retries).isEqualTo(2);
        assertFreshTransactions(exhaustedTrace);

        RetryTrace nonRetryableTrace = new RetryTrace();
        assertThatThrownBy(() -> withBoundedTransactionRetry(
                owner,
                (connection, attempt) -> {
                    executeUpdate(connection, """
                            INSERT INTO phase4c_tag_migration_design_retry_counter
                                (counter_id, value)
                            VALUES (1, 0)
                            """);
                    return 0;
                },
                nonRetryableTrace))
                .isInstanceOfSatisfying(SQLException.class, error ->
                        assertThat(error.getSQLState()).isEqualTo("23505"));
        assertThat(nonRetryableTrace.attempts).isOne();
        assertThat(nonRetryableTrace.retries).isZero();
        assertFreshTransactions(nonRetryableTrace);

        RetryTrace unknownTrace = new RetryTrace();
        assertThatThrownBy(() -> withBoundedTransactionRetry(
                owner,
                (connection, attempt) -> {
                    throw new SQLException("unknown SQLSTATE fixture", "ZZZZZ");
                },
                unknownTrace))
                .isInstanceOfSatisfying(SQLException.class, error ->
                        assertThat(error.getSQLState()).isEqualTo("ZZZZZ"));
        assertThat(unknownTrace.attempts).isOne();
        assertThat(unknownTrace.retries).isZero();
        assertFreshTransactions(unknownTrace);

        RetryTrace nullStateTrace = new RetryTrace();
        assertThatThrownBy(() -> withBoundedTransactionRetry(
                owner,
                (connection, attempt) -> {
                    throw new SQLException("null SQLSTATE fixture", (String) null);
                },
                nullStateTrace))
                .isInstanceOfSatisfying(SQLException.class, error ->
                        assertThat(error.getSQLState()).isNull());
        assertThat(nullStateTrace.attempts).isOne();
        assertThat(nullStateTrace.retries).isZero();
        assertFreshTransactions(nullStateTrace);
        assertThat(RETRYABLE_SQLSTATES)
                .containsExactlyInAnyOrder("40001", "40P01");
    }

    private static void proveRestrictedAclAndSensitiveCanary(
            DataSource owner,
            DataSource operator
    ) throws Exception {
        assertThat(queryBoolean(owner, """
                SELECT NOT rolsuper
                       AND NOT rolcanlogin
                       AND NOT rolcreatedb
                       AND NOT rolcreaterole
                       AND NOT rolinherit
                       AND NOT rolreplication
                       AND NOT rolbypassrls
                FROM pg_roles
                WHERE rolname = 'ti_phase4c_tag_design_operator'
                """)).isTrue();
        assertThat(queryBoolean(owner, """
                SELECT NOT has_database_privilege(
                    'ti_phase4c_tag_design_operator',
                    current_database(),
                    'CONNECT'
                )
                """)).isTrue();
        assertThat(queryBoolean(owner, """
                SELECT NOT EXISTS (
                    SELECT 1
                    FROM pg_database AS database
                    CROSS JOIN LATERAL aclexplode(
                        coalesce(
                            database.datacl,
                            acldefault('d', database.datdba)
                        )
                    ) AS privilege
                    WHERE database.datname = current_database()
                      AND privilege.grantee = 0
                      AND privilege.privilege_type = 'CONNECT'
                )
                """)).isTrue();
        assertThat(hasTablePrivilege(owner,
                "phase4c_tag_migration_design_source", "SELECT")).isTrue();
        for (String privilege : List.of("INSERT", "UPDATE", "DELETE")) {
            assertThat(hasTablePrivilege(owner,
                    "phase4c_tag_migration_design_source", privilege))
                    .as("source " + privilege).isFalse();
        }
        assertThat(hasTablePrivilege(owner,
                "phase4c_tag_migration_design_membership", "SELECT")).isTrue();
        for (String privilege : List.of("INSERT", "UPDATE", "DELETE")) {
            assertThat(hasTablePrivilege(owner,
                    "phase4c_tag_migration_design_membership", privilege))
                    .as("membership " + privilege).isFalse();
        }
        for (String privilege : List.of("SELECT", "INSERT", "UPDATE")) {
            assertThat(hasTablePrivilege(owner,
                    "phase4c_tag_migration_design_ledger", privilege))
                    .as("ledger " + privilege).isTrue();
        }
        assertThat(hasTablePrivilege(owner,
                "phase4c_tag_migration_design_ledger", "DELETE")).isFalse();
        for (String table : List.of(
                "phase4c_tag_migration_design_receipt",
                "phase4c_tag_migration_design_target")) {
            for (String privilege : List.of("SELECT", "INSERT")) {
                assertThat(hasTablePrivilege(owner, table, privilege))
                        .as(table + " " + privilege).isTrue();
            }
            for (String privilege : List.of("UPDATE", "DELETE")) {
                assertThat(hasTablePrivilege(owner, table, privilege))
                        .as(table + " " + privilege).isFalse();
            }
        }
        assertThat(hasTablePrivilege(owner,
                "phase4c_tag_migration_design_mutation_audit", "SELECT"))
                .isFalse();
        assertThat(hasTablePrivilege(owner,
                "phase4c_tag_migration_design_statement_audit", "SELECT"))
                .isFalse();
        assertThat(queryBoolean(owner, """
                SELECT has_schema_privilege(
                    'ti_phase4c_tag_design_operator', 'public', 'CREATE')
                """)).isFalse();

        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                "UPDATE phase4c_tag_migration_design_source "
                        + "SET legacy_key = legacy_key WHERE false"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                "CREATE TABLE phase4c_forbidden_design_table (id integer)"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                "CREATE TEMP TABLE phase4c_forbidden_temp_table (id integer)"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                "CREATE SCHEMA phase4c_forbidden_design_schema"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                "UPDATE phase4c_tag_migration_design_membership "
                        + "SET question_id = question_id WHERE false"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> queryInt(
                operator,
                "SELECT count(*) "
                        + "FROM phase4c_tag_migration_design_mutation_audit"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> queryInt(
                operator,
                "SELECT count(*) "
                        + "FROM phase4c_tag_migration_design_statement_audit"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> executeUpdate(
                operator,
                "UPDATE phase4c_tag_migration_design_receipt "
                        + "SET disposition = disposition WHERE false"))
                .getSQLState()).isEqualTo("42501");
        assertThat(captureSqlException(() -> executeUpdate(
                owner,
                "UPDATE phase4c_tag_migration_design_receipt "
                        + "SET disposition = 'EMPTY_NOOP' "
                        + "WHERE migration_id = '"
                        + migrationUuid("ack-discard") + "'"))
                .getSQLState()).isEqualTo("55000");

        String sourceFixture = queryString(owner, """
                SELECT string_agg(legacy_key || legacy_payload, '')
                FROM phase4c_tag_migration_design_source
                """);
        assertThat(sourceFixture).contains(SENSITIVE_CANARY_PREFIX);
        for (String table : List.of(
                "phase4c_tag_migration_design_ledger",
                "phase4c_tag_migration_design_receipt",
                "phase4c_tag_migration_design_target",
                "phase4c_tag_migration_design_mutation_audit",
                "phase4c_tag_migration_design_statement_audit")) {
            assertThat(queryString(owner,
                    "SELECT coalesce(string_agg(row_to_json(t)::text, ''), '') "
                            + "FROM " + table + " t"))
                    .as(table)
                    .doesNotContain(SENSITIVE_CANARY_PREFIX);
        }
        assertThat(new String(
                Files.readAllBytes(contractPath()), StandardCharsets.UTF_8))
                .doesNotContain(SENSITIVE_CANARY_PREFIX);
        String schema = new String(
                Phase4cLegacyPersonalBankTagDurableLedgerFreezeDesignIT.class
                        .getResourceAsStream(
                                "/db/phase4c/074-legacy-personal-bank-tag-"
                                        + "durable-ledger-freeze-design-schema.sql")
                        .readAllBytes(),
                StandardCharsets.UTF_8);
        assertThat(schema)
                .contains(
                        "NOLOGIN",
                        "NOBYPASSRLS",
                        "REVOKE CONNECT ON DATABASE",
                        "migration_id uuid",
                        "canonical-target-facts:v1",
                        "SET search_path = pg_catalog, pg_temp")
                .doesNotContain(
                        "PASSWORD",
                        "GRANT CONNECT",
                        "target_fact_digest_sha256");
    }

    private static void prepareApplying(
            DataSource operator,
            String migrationId,
            RunIdentity identity
    ) throws SQLException {
        insertPlanned(operator, migrationId, identity);
        assertThat(freeze(operator, migrationId, 0, identity)).isOne();
        assertThat(transition(
                operator,
                migrationId,
                "FROZEN",
                1,
                "APPLYING",
                identity)).isOne();
    }

    private static void insertPlanned(
            DataSource dataSource,
            String migrationId,
            RunIdentity identity
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement("""
                        INSERT INTO phase4c_tag_migration_design_ledger (
                            migration_id,
                            state,
                            version,
                            migration_run_uuid,
                            backup_manifest_sha256,
                            cluster_database_identity_sha256,
                            database_identity_sha256,
                            preflight_digest_sha256,
                            plan_digest_sha256,
                            source_digest_sha256,
                            target_digest_sha256,
                            membership_digest_sha256
                        ) VALUES (?, 'PLANNED', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """)) {
            statement.setObject(1, migrationUuid(migrationId));
            bindIdentityAndDigests(statement, 2, identity);
            assertThat(statement.executeUpdate()).isOne();
        }
    }

    private static int freeze(
            DataSource dataSource,
            String migrationId,
            int expectedVersion,
            RunIdentity identity
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return freeze(connection, migrationId, expectedVersion, identity);
        }
    }

    private static int freeze(
            Connection connection,
            String migrationId,
            int expectedVersion,
            RunIdentity identity
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("""
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'FROZEN',
                    version = version + 1,
                    source_writer_stop_receipt_sha256 = ?,
                    target_writer_stop_receipt_sha256 = ?,
                    membership_writer_stop_receipt_sha256 = ?,
                    restored_backup_sha256 = ?,
                    updated_at = clock_timestamp()
                WHERE migration_id = ?
                  AND state = 'PLANNED'
                  AND version = ?
                  AND source_writer_stop_receipt_sha256 IS NULL
                  AND target_writer_stop_receipt_sha256 IS NULL
                  AND membership_writer_stop_receipt_sha256 IS NULL
                  AND restored_backup_sha256 IS NULL
                  AND migration_run_uuid = ?
                  AND backup_manifest_sha256 = ?
                  AND cluster_database_identity_sha256 = ?
                  AND database_identity_sha256 = ?
                  AND preflight_digest_sha256 = ?
                  AND plan_digest_sha256 = ?
                  AND source_digest_sha256 = ?
                  AND target_digest_sha256 = ?
                  AND membership_digest_sha256 = ?
                """)) {
            statement.setString(1, SOURCE_STOP_RECEIPT);
            statement.setString(2, TARGET_STOP_RECEIPT);
            statement.setString(3, MEMBERSHIP_STOP_RECEIPT);
            statement.setString(4, RESTORED_BACKUP_DIGEST);
            statement.setObject(5, migrationUuid(migrationId));
            statement.setInt(6, expectedVersion);
            bindIdentityAndDigests(statement, 7, identity);
            return statement.executeUpdate();
        }
    }

    private static int transition(
            DataSource dataSource,
            String migrationId,
            String expectedState,
            int expectedVersion,
            String nextState,
            RunIdentity identity
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return transition(
                    connection,
                    migrationId,
                    expectedState,
                    expectedVersion,
                    nextState,
                    identity);
        }
    }

    private static int block(
            DataSource dataSource,
            String migrationId,
            String expectedState,
            int expectedVersion,
            RunIdentity identity
    ) throws SQLException {
        return block(
                dataSource,
                migrationId,
                expectedState,
                expectedVersion,
                "ILLEGAL_STATE",
                identity);
    }

    private static int block(
            DataSource dataSource,
            String migrationId,
            String expectedState,
            int expectedVersion,
            String blockedCode,
            RunIdentity identity
    ) throws SQLException {
        String freezePredicate = expectedState.equals("PLANNED")
                ? """
                  AND source_writer_stop_receipt_sha256 IS NULL
                  AND target_writer_stop_receipt_sha256 IS NULL
                  AND membership_writer_stop_receipt_sha256 IS NULL
                  AND restored_backup_sha256 IS NULL
                  """
                : """
                  AND source_writer_stop_receipt_sha256 = ?
                  AND target_writer_stop_receipt_sha256 = ?
                  AND membership_writer_stop_receipt_sha256 = ?
                  AND restored_backup_sha256 = ?
                  """;
        String sql = """
                UPDATE phase4c_tag_migration_design_ledger
                SET state = 'BLOCKED',
                    version = version + 1,
                    blocked_code = ?,
                    updated_at = clock_timestamp()
                WHERE migration_id = ?
                  AND state = ?
                  AND version = ?
                """ + freezePredicate + """
                  AND migration_run_uuid = ?
                  AND backup_manifest_sha256 = ?
                  AND cluster_database_identity_sha256 = ?
                  AND database_identity_sha256 = ?
                  AND preflight_digest_sha256 = ?
                  AND plan_digest_sha256 = ?
                  AND source_digest_sha256 = ?
                  AND target_digest_sha256 = ?
                  AND membership_digest_sha256 = ?
                """;
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, blockedCode);
            statement.setObject(2, migrationUuid(migrationId));
            statement.setString(3, expectedState);
            statement.setInt(4, expectedVersion);
            int identityOffset;
            if (expectedState.equals("PLANNED")) {
                identityOffset = 5;
            } else {
                statement.setString(5, SOURCE_STOP_RECEIPT);
                statement.setString(6, TARGET_STOP_RECEIPT);
                statement.setString(7, MEMBERSHIP_STOP_RECEIPT);
                statement.setString(8, RESTORED_BACKUP_DIGEST);
                identityOffset = 9;
            }
            bindIdentityAndDigests(statement, identityOffset, identity);
            return statement.executeUpdate();
        }
    }

    private static int transition(
            Connection connection,
            String migrationId,
            String expectedState,
            int expectedVersion,
            String nextState,
            RunIdentity identity
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("""
                UPDATE phase4c_tag_migration_design_ledger
                SET state = ?, version = version + 1, updated_at = clock_timestamp()
                WHERE migration_id = ?
                  AND state = ?
                  AND version = ?
                  AND source_writer_stop_receipt_sha256 = ?
                  AND target_writer_stop_receipt_sha256 = ?
                  AND membership_writer_stop_receipt_sha256 = ?
                  AND restored_backup_sha256 = ?
                  AND migration_run_uuid = ?
                  AND backup_manifest_sha256 = ?
                  AND cluster_database_identity_sha256 = ?
                  AND database_identity_sha256 = ?
                  AND preflight_digest_sha256 = ?
                  AND plan_digest_sha256 = ?
                  AND source_digest_sha256 = ?
                  AND target_digest_sha256 = ?
                  AND membership_digest_sha256 = ?
                """)) {
            statement.setString(1, nextState);
            statement.setObject(2, migrationUuid(migrationId));
            statement.setString(3, expectedState);
            statement.setInt(4, expectedVersion);
            statement.setString(5, SOURCE_STOP_RECEIPT);
            statement.setString(6, TARGET_STOP_RECEIPT);
            statement.setString(7, MEMBERSHIP_STOP_RECEIPT);
            statement.setString(8, RESTORED_BACKUP_DIGEST);
            bindIdentityAndDigests(statement, 9, identity);
            return statement.executeUpdate();
        }
    }

    private static void bindIdentityAndDigests(
            PreparedStatement statement,
            int offset,
            RunIdentity identity
    ) throws SQLException {
        statement.setObject(offset, identity.runUuid());
        statement.setString(offset + 1, identity.backupManifestSha256());
        statement.setString(offset + 2, identity.clusterDatabaseIdentitySha256());
        statement.setString(offset + 3, identity.runIdentitySha256());
        statement.setString(offset + 4, PREFLIGHT_DIGEST);
        statement.setString(offset + 5, PLAN_DIGEST);
        statement.setString(offset + 6, SOURCE_DIGEST);
        statement.setString(offset + 7, TARGET_DIGEST);
        statement.setString(offset + 8, MEMBERSHIP_DIGEST);
    }

    private static void applyTransaction(
            DataSource dataSource,
            String migrationId,
            long sourceRowId,
            RunIdentity identity,
            boolean commit
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            try {
                insertEmptyNoopReceipt(
                        connection,
                        migrationId,
                        EMPTY_NOOP_SOURCE_ROW_ID,
                        identity);
                insertReceipt(connection, migrationId, sourceRowId, identity);
                insertTarget(connection, migrationId, sourceRowId);
                assertThat(transition(
                        connection,
                        migrationId,
                        "APPLYING",
                        2,
                        "APPLIED",
                        identity)).isOne();
                if (commit) {
                    connection.commit();
                } else {
                    connection.rollback();
                }
            } catch (SQLException | RuntimeException error) {
                connection.rollback();
                throw error;
            }
        }
    }

    private static void insertReceipt(
            Connection connection,
            String migrationId,
            long sourceRowId,
            RunIdentity identity
    ) throws SQLException {
        insertReceipt(
                connection,
                migrationId,
                sourceRowId,
                identity,
                TARGET_DIGEST,
                "MIGRATED",
                1);
    }

    private static void insertEmptyNoopReceipt(
            Connection connection,
            String migrationId,
            long sourceRowId,
            RunIdentity identity
    ) throws SQLException {
        insertReceipt(
                connection,
                migrationId,
                sourceRowId,
                identity,
                TARGET_DIGEST,
                "EMPTY_NOOP",
                0);
    }

    private static void insertReceipt(
            Connection connection,
            String migrationId,
            long sourceRowId,
            RunIdentity identity,
            String receiptTargetDigest
    ) throws SQLException {
        insertReceipt(
                connection,
                migrationId,
                sourceRowId,
                identity,
                receiptTargetDigest,
                "MIGRATED",
                1);
    }

    private static void insertReceipt(
            Connection connection,
            String migrationId,
            long sourceRowId,
            RunIdentity identity,
            String receiptTargetDigest,
            String disposition,
            int appliedTargetRowCount
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("""
                INSERT INTO phase4c_tag_migration_design_receipt (
                    migration_id,
                    source_row_id,
                    migration_run_uuid,
                    backup_manifest_sha256,
                    cluster_database_identity_sha256,
                    database_identity_sha256,
                    preflight_digest_sha256,
                    source_digest_sha256,
                    plan_digest_sha256,
                    target_digest_sha256,
                    membership_digest_sha256,
                    source_writer_stop_receipt_sha256,
                    target_writer_stop_receipt_sha256,
                    membership_writer_stop_receipt_sha256,
                    restored_backup_sha256,
                    disposition,
                    applied_target_row_count
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """)) {
            statement.setObject(1, migrationUuid(migrationId));
            statement.setLong(2, sourceRowId);
            statement.setObject(3, identity.runUuid());
            statement.setString(4, identity.backupManifestSha256());
            statement.setString(5, identity.clusterDatabaseIdentitySha256());
            statement.setString(6, identity.runIdentitySha256());
            statement.setString(7, PREFLIGHT_DIGEST);
            statement.setString(8, SOURCE_DIGEST);
            statement.setString(9, PLAN_DIGEST);
            statement.setString(10, receiptTargetDigest);
            statement.setString(11, MEMBERSHIP_DIGEST);
            statement.setString(12, SOURCE_STOP_RECEIPT);
            statement.setString(13, TARGET_STOP_RECEIPT);
            statement.setString(14, MEMBERSHIP_STOP_RECEIPT);
            statement.setString(15, RESTORED_BACKUP_DIGEST);
            statement.setString(16, disposition);
            statement.setInt(17, appliedTargetRowCount);
            assertThat(statement.executeUpdate()).isOne();
        }
    }

    private static SQLException attemptPartialReceiptCommit(
            DataSource dataSource,
            String migrationId,
            long sourceRowId,
            RunIdentity identity
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            insertReceipt(connection, migrationId, sourceRowId, identity);
            try {
                connection.commit();
            } catch (SQLException error) {
                connection.rollback();
                return error;
            }
            throw new AssertionError(
                    "deferred APPLIED/target-count guard accepted partial receipt");
        }
    }

    private static SQLException attemptAppliedWithoutTargetCommit(
            DataSource dataSource,
            String migrationId,
            long sourceRowId,
            RunIdentity identity
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            insertEmptyNoopReceipt(
                    connection,
                    migrationId,
                    EMPTY_NOOP_SOURCE_ROW_ID,
                    identity);
            insertReceipt(connection, migrationId, sourceRowId, identity);
            try {
                assertThat(transition(
                        connection,
                        migrationId,
                        "APPLYING",
                        2,
                        "APPLIED",
                        identity)).isOne();
                connection.commit();
            } catch (SQLException error) {
                connection.rollback();
                return error;
            }
            throw new AssertionError(
                    "deferred target-count guard accepted missing target");
        }
    }

    private static SQLException attemptWrongCanonicalTargetFact(
            DataSource dataSource,
            String migrationId,
            long sourceRowId,
            RunIdentity identity
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            connection.setAutoCommit(false);
            insertEmptyNoopReceipt(
                    connection,
                    migrationId,
                    EMPTY_NOOP_SOURCE_ROW_ID,
                    identity);
            insertReceipt(connection, migrationId, sourceRowId, identity);
            insertTarget(connection, migrationId, sourceRowId, 98_102, "beta");
            try {
                transition(
                        connection,
                        migrationId,
                        "APPLYING",
                        2,
                        "APPLIED",
                        identity);
            } catch (SQLException error) {
                connection.rollback();
                return error;
            }
            connection.rollback();
            throw new AssertionError(
                    "caller facts bypassed canonical target-digest validation");
        }
    }

    private static void insertTarget(
            Connection connection,
            String migrationId,
            long sourceRowId
    ) throws SQLException {
        insertTarget(connection, migrationId, sourceRowId, 98_102, "alpha");
    }

    private static void insertTarget(
            Connection connection,
            String migrationId,
            long sourceRowId,
            int questionId,
            String tag
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("""
                INSERT INTO phase4c_tag_migration_design_target (
                    migration_id,
                    source_row_id,
                    question_id,
                    tag
                ) VALUES (?, ?, ?, ?)
                """)) {
            statement.setObject(1, migrationUuid(migrationId));
            statement.setLong(2, sourceRowId);
            statement.setInt(3, questionId);
            statement.setString(4, tag);
            assertThat(statement.executeUpdate()).isOne();
        }
    }

    private static void commitThenDiscardAckFixture(
            DataSource dataSource,
            String migrationId,
            long sourceRowId,
            RunIdentity identity
    ) throws SQLException {
        applyTransaction(dataSource, migrationId, sourceRowId, identity, true);
        throw new AckDiscardedAfterCommitFixtureException(
                "test fixture discarded commit acknowledgement");
    }

    private static RecoveryDisposition recoverReceiptFirst(
            DataSource dataSource,
            String migrationId,
            long sourceRowId,
            RunIdentity freshIdentity
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            String canonicalTargetDigest = canonicalTargetDigest(
                    connection, migrationId);
            try (PreparedStatement statement = connection.prepareStatement("""
                        SELECT l.state,
                               l.version,
                               l.migration_run_uuid AS ledger_run_uuid,
                               l.backup_manifest_sha256 AS ledger_backup,
                               l.cluster_database_identity_sha256 AS ledger_cluster,
                               l.database_identity_sha256 AS ledger_identity,
                               l.preflight_digest_sha256 AS ledger_preflight,
                               l.plan_digest_sha256 AS ledger_plan,
                               l.source_digest_sha256 AS ledger_source,
                               l.target_digest_sha256 AS ledger_target,
                               l.membership_digest_sha256 AS ledger_membership,
                               l.source_writer_stop_receipt_sha256
                                   AS ledger_source_stop,
                               l.target_writer_stop_receipt_sha256
                                   AS ledger_target_stop,
                               l.membership_writer_stop_receipt_sha256
                                   AS ledger_membership_stop,
                               l.restored_backup_sha256 AS ledger_restored_backup,
                               r.migration_run_uuid AS receipt_run_uuid,
                               r.backup_manifest_sha256 AS receipt_backup,
                               r.cluster_database_identity_sha256 AS receipt_cluster,
                               r.database_identity_sha256 AS receipt_identity,
                               r.preflight_digest_sha256 AS receipt_preflight,
                               r.plan_digest_sha256 AS receipt_plan,
                               r.source_digest_sha256 AS receipt_source,
                               r.target_digest_sha256 AS receipt_target,
                               r.membership_digest_sha256 AS receipt_membership,
                               r.source_writer_stop_receipt_sha256
                                   AS receipt_source_stop,
                               r.target_writer_stop_receipt_sha256
                                   AS receipt_target_stop,
                               r.membership_writer_stop_receipt_sha256
                                   AS receipt_membership_stop,
                               r.restored_backup_sha256 AS receipt_restored_backup,
                               r.disposition,
                               r.applied_target_row_count,
                               (
                                   SELECT count(*)
                                   FROM phase4c_tag_migration_design_target t
                                   WHERE t.migration_id = r.migration_id
                                     AND t.source_row_id = r.source_row_id
                               ) AS target_count,
                               (
                                   SELECT count(*)
                                   FROM phase4c_tag_migration_design_source
                               ) AS source_count,
                               (
                                   SELECT count(*)
                                   FROM phase4c_tag_migration_design_receipt rr
                                   WHERE rr.migration_id = r.migration_id
                               ) AS receipt_count,
                               (
                                   SELECT count(*)
                                   FROM phase4c_tag_migration_design_receipt rr
                                   LEFT JOIN LATERAL (
                                       SELECT count(*)::integer
                                           AS actual_target_count
                                       FROM phase4c_tag_migration_design_target tt
                                       WHERE tt.migration_id = rr.migration_id
                                         AND tt.source_row_id = rr.source_row_id
                                   ) tc ON true
                                   WHERE rr.migration_id = r.migration_id
                                     AND (
                                         rr.target_digest_sha256
                                             IS DISTINCT FROM l.target_digest_sha256
                                         OR rr.applied_target_row_count
                                             IS DISTINCT FROM tc.actual_target_count
                                         OR (
                                             rr.disposition = 'EMPTY_NOOP'
                                             AND tc.actual_target_count <> 0
                                         )
                                         OR (
                                             rr.disposition IN (
                                                 'MIGRATED',
                                                 'TARGET_ALREADY_PRESENT'
                                             )
                                             AND tc.actual_target_count = 0
                                         )
                                     )
                               ) AS invalid_disposition_count
                        FROM phase4c_tag_migration_design_receipt r
                        JOIN phase4c_tag_migration_design_ledger l
                          ON l.migration_id = r.migration_id
                        WHERE r.migration_id = ?
                          AND r.source_row_id = ?
                        """)) {
            statement.setObject(1, migrationUuid(migrationId));
            statement.setLong(2, sourceRowId);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    return RecoveryDisposition.BLOCKED_NO_RECEIPT;
                }
                boolean identityMatches =
                        result.getObject("ledger_run_uuid", UUID.class)
                                .equals(freshIdentity.runUuid())
                        && result.getString("ledger_backup").equals(
                                freshIdentity.backupManifestSha256())
                        && result.getString("ledger_cluster").equals(
                                freshIdentity.clusterDatabaseIdentitySha256())
                        && result.getString("ledger_identity").equals(
                                freshIdentity.runIdentitySha256())
                        && result.getObject("receipt_run_uuid", UUID.class)
                                .equals(freshIdentity.runUuid())
                        && result.getString("receipt_backup").equals(
                                freshIdentity.backupManifestSha256())
                        && result.getString("receipt_cluster").equals(
                                freshIdentity.clusterDatabaseIdentitySha256())
                        && result.getString("receipt_identity").equals(
                                freshIdentity.runIdentitySha256());
                if (!identityMatches) {
                    return RecoveryDisposition.BLOCKED_IDENTITY_MISMATCH;
                }
                boolean exactReceiptAndTarget =
                        result.getString(1).equals("APPLIED")
                        && result.getInt(2) == 3
                        && result.getString("ledger_preflight").equals(PREFLIGHT_DIGEST)
                        && result.getString("ledger_plan").equals(PLAN_DIGEST)
                        && result.getString("ledger_source").equals(SOURCE_DIGEST)
                        && result.getString("ledger_target").equals(TARGET_DIGEST)
                        && result.getString("ledger_membership")
                                .equals(MEMBERSHIP_DIGEST)
                        && result.getString("ledger_source_stop")
                                .equals(SOURCE_STOP_RECEIPT)
                        && result.getString("ledger_target_stop")
                                .equals(TARGET_STOP_RECEIPT)
                        && result.getString("ledger_membership_stop")
                                .equals(MEMBERSHIP_STOP_RECEIPT)
                        && result.getString("ledger_restored_backup")
                                .equals(RESTORED_BACKUP_DIGEST)
                        && result.getString("receipt_preflight")
                                .equals(PREFLIGHT_DIGEST)
                        && result.getString("receipt_plan").equals(PLAN_DIGEST)
                        && result.getString("receipt_source").equals(SOURCE_DIGEST)
                        && result.getString("receipt_target").equals(TARGET_DIGEST)
                        && result.getString("receipt_membership")
                                .equals(MEMBERSHIP_DIGEST)
                        && result.getString("receipt_source_stop")
                                .equals(SOURCE_STOP_RECEIPT)
                        && result.getString("receipt_target_stop")
                                .equals(TARGET_STOP_RECEIPT)
                        && result.getString("receipt_membership_stop")
                                .equals(MEMBERSHIP_STOP_RECEIPT)
                        && result.getString("receipt_restored_backup")
                                .equals(RESTORED_BACKUP_DIGEST)
                        && result.getString("disposition").equals("MIGRATED")
                        && result.getInt("applied_target_row_count") == 1
                        && result.getInt("target_count") == 1
                        && result.getInt("source_count") > 0
                        && result.getInt("receipt_count")
                                == result.getInt("source_count")
                        && result.getInt("invalid_disposition_count") == 0
                        && canonicalTargetDigest.equals(TARGET_DIGEST)
                        && canonicalTargetDigest.equals(
                                result.getString("ledger_target"))
                        && canonicalTargetDigest.equals(
                                result.getString("receipt_target"))
                        && !result.next();
                return exactReceiptAndTarget
                        ? RecoveryDisposition.COMMITTED_ZERO_DML
                        : RecoveryDisposition.BLOCKED_RECEIPT_OR_TARGET_MISMATCH;
            }
            }
        }
    }

    private static void provokeSerializationFailureOn(
            Connection attemptConnection,
            DataSource competitorDataSource
    ) throws SQLException {
        int observed = queryInt(attemptConnection,
                "SELECT value FROM phase4c_tag_migration_design_retry_counter "
                        + "WHERE counter_id = 1");
        try (Connection competitor = competitorDataSource.getConnection()) {
            configureSerializable(competitor);
            executeUpdate(competitor,
                    "UPDATE phase4c_tag_migration_design_retry_counter "
                            + "SET value = value + 1 WHERE counter_id = 1");
            competitor.commit();
        }
        try {
            executeUpdate(attemptConnection,
                    "UPDATE phase4c_tag_migration_design_retry_counter SET value = "
                            + (observed + 1) + " WHERE counter_id = 1");
        } catch (SQLException error) {
            throw findSqlState(error, "40001");
        }
        throw new AssertionError("PostgreSQL did not emit serialization failure");
    }

    private static SQLException provokeDeadlock(DataSource dataSource)
            throws Exception {
        executeUpdate(dataSource,
                "UPDATE phase4c_tag_migration_design_retry_locks SET value = 0");
        try (Connection first = dataSource.getConnection();
                Connection second = dataSource.getConnection()) {
            first.setAutoCommit(false);
            second.setAutoCommit(false);
            executeUpdate(first, "SET LOCAL deadlock_timeout = '100ms'");
            executeUpdate(second, "SET LOCAL deadlock_timeout = '100ms'");
            CountDownLatch firstLocksHeld = new CountDownLatch(2);
            ExecutorService pool = Executors.newFixedThreadPool(2);
            try {
                Future<SQLException> left = pool.submit(() -> deadlockParticipant(
                        first, 1, 2, firstLocksHeld));
                Future<SQLException> right = pool.submit(() -> deadlockParticipant(
                        second, 2, 1, firstLocksHeld));
                SQLException leftError = left.get(10, TimeUnit.SECONDS);
                SQLException rightError = right.get(10, TimeUnit.SECONDS);
                for (SQLException error : new SQLException[] {
                        leftError, rightError
                }) {
                    if (error == null) {
                        continue;
                    }
                    SQLException matching = findSqlStateOrNull(error, "40P01");
                    if (matching != null) {
                        return matching;
                    }
                }
                throw new AssertionError("PostgreSQL did not emit deadlock failure");
            } finally {
                pool.shutdownNow();
                assertThat(pool.awaitTermination(5, TimeUnit.SECONDS)).isTrue();
            }
        }
    }

    private static SQLException deadlockParticipant(
            Connection connection,
            int firstId,
            int secondId,
            CountDownLatch firstLocksHeld
    ) {
        try {
            executeUpdate(connection,
                    "UPDATE phase4c_tag_migration_design_retry_locks "
                            + "SET value = value + 1 WHERE lock_id = " + firstId);
            firstLocksHeld.countDown();
            if (!firstLocksHeld.await(5, TimeUnit.SECONDS)) {
                throw new AssertionError("deadlock fixture barrier timed out");
            }
            executeUpdate(connection,
                    "UPDATE phase4c_tag_migration_design_retry_locks "
                            + "SET value = value + 1 WHERE lock_id = " + secondId);
            connection.commit();
            return null;
        } catch (SQLException error) {
            try {
                connection.rollback();
            } catch (SQLException rollbackError) {
                error.addSuppressed(rollbackError);
            }
            return error;
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            throw new AssertionError("deadlock fixture interrupted", error);
        }
    }

    private static <T> T withBoundedTransactionRetry(
            DataSource dataSource,
            TransactionalSqlAttempt<T> attempt,
            RetryTrace trace
    ) throws SQLException {
        for (int attemptNumber = 1; attemptNumber <= 3; attemptNumber++) {
            trace.attempts++;
            try (Connection connection = dataSource.getConnection()) {
                configureSerializable(connection);
                trace.backendProcessIds.add(queryInt(
                        connection, "SELECT pg_backend_pid()"));
                trace.transactionIds.add(queryString(
                        connection, "SELECT pg_current_xact_id()::text"));
                try {
                    T result = attempt.run(connection, attemptNumber);
                    connection.commit();
                    return result;
                } catch (SQLException error) {
                    connection.rollback();
                    if (isRetryableSqlstate(error.getSQLState())
                            && attemptNumber < 3) {
                        trace.retries++;
                        continue;
                    }
                    throw error;
                }
            }
        }
        throw new AssertionError("bounded retry loop fell through");
    }

    private static boolean isRetryableSqlstate(String sqlstate) {
        return sqlstate != null && RETRYABLE_SQLSTATES.contains(sqlstate);
    }

    private static void assertFreshTransactions(RetryTrace trace) {
        assertThat(trace.backendProcessIds).hasSize(trace.attempts);
        assertThat(trace.transactionIds).hasSize(trace.attempts);
        assertThat(Set.copyOf(trace.backendProcessIds)).hasSize(trace.attempts);
        assertThat(Set.copyOf(trace.transactionIds)).hasSize(trace.attempts);
    }

    private static void configureSerializable(Connection connection)
            throws SQLException {
        connection.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
        connection.setAutoCommit(false);
    }

    private static String canonicalTargetDigest(
            Connection connection,
            String migrationId
    ) throws SQLException {
        StringBuilder canonical = new StringBuilder(
                CANONICAL_TARGET_FACTS_DOMAIN).append('\n');
        try (PreparedStatement statement = connection.prepareStatement("""
                SELECT question_id, tag
                FROM (
                    SELECT DISTINCT question_id, tag
                    FROM phase4c_tag_migration_design_target
                    WHERE migration_id = ?
                ) AS canonical_facts
                ORDER BY question_id, tag COLLATE "C"
                """)) {
            statement.setObject(1, migrationUuid(migrationId));
            try (ResultSet result = statement.executeQuery()) {
                while (result.next()) {
                    appendCanonicalField(
                            canonical,
                            Integer.toString(result.getInt("question_id")));
                    appendCanonicalField(canonical, result.getString("tag"));
                }
            }
        }
        return sha256(canonical.toString().getBytes(StandardCharsets.UTF_8));
    }

    private static void appendCanonicalField(
            StringBuilder canonical,
            String value
    ) {
        canonical.append(value.getBytes(StandardCharsets.UTF_8).length)
                .append(':')
                .append(value);
    }

    private static UUID migrationUuid(String nonSensitiveTestLabel) {
        try {
            return UUID.fromString(nonSensitiveTestLabel);
        } catch (IllegalArgumentException notAlreadyUuid) {
            return UUID.nameUUIDFromBytes(joinDomain(
                    MIGRATION_ID_DOMAIN,
                    nonSensitiveTestLabel));
        }
    }

    private static RunIdentity runIdentity(
            UUID runUuid,
            String backupManifestSha256,
            String clusterDatabaseIdentitySha256
    ) {
        String identity = sha256(joinDomain(
                RUN_IDENTITY_DOMAIN,
                backupManifestSha256,
                runUuid.toString(),
                clusterDatabaseIdentitySha256));
        return new RunIdentity(
                runUuid,
                backupManifestSha256,
                clusterDatabaseIdentitySha256,
                identity);
    }

    private static String clusterDatabaseIdentity(DataSource dataSource)
            throws SQLException {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement("""
                        SELECT system_identifier::text,
                               (
                                   SELECT oid::text
                                   FROM pg_database
                                   WHERE datname = current_database()
                               ),
                               current_setting('server_version'),
                               coalesce(inet_server_addr()::text, 'local'),
                               inet_server_port()::text
                        FROM pg_control_system()
                        """)) {
            try (ResultSet result = statement.executeQuery()) {
                assertThat(result.next()).isTrue();
                String digest = sha256(joinDomain(
                        CLUSTER_DATABASE_DOMAIN,
                        result.getString(1),
                        result.getString(2),
                        result.getString(3),
                        result.getString(4),
                        result.getString(5)));
                assertThat(result.next()).isFalse();
                return digest;
            }
        }
    }

    private static byte[] joinDomain(String domain, String... values) {
        StringBuilder builder = new StringBuilder(domain);
        for (String value : values) {
            builder.append('\u0000').append(value);
        }
        return builder.toString().getBytes(StandardCharsets.UTF_8);
    }

    private static void assertLedger(
            DataSource dataSource,
            String migrationId,
            String state,
            int version
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement("""
                        SELECT state, version
                        FROM phase4c_tag_migration_design_ledger
                        WHERE migration_id = ?
                        """)) {
            statement.setObject(1, migrationUuid(migrationId));
            try (ResultSet result = statement.executeQuery()) {
                assertThat(result.next()).isTrue();
                assertThat(result.getString(1)).isEqualTo(state);
                assertThat(result.getInt(2)).isEqualTo(version);
                assertThat(result.next()).isFalse();
            }
        }
    }

    private static int countReceipt(
            DataSource dataSource,
            String migrationId,
            long sourceRowId
    ) throws SQLException {
        return countByMigrationAndSource(
                dataSource,
                "phase4c_tag_migration_design_receipt",
                migrationId,
                sourceRowId);
    }

    private static int countTarget(
            DataSource dataSource,
            String migrationId,
            long sourceRowId
    ) throws SQLException {
        return countByMigrationAndSource(
                dataSource,
                "phase4c_tag_migration_design_target",
                migrationId,
                sourceRowId);
    }

    private static int countByMigrationAndSource(
            DataSource dataSource,
            String table,
            String migrationId,
            long sourceRowId
    ) throws SQLException {
        try (Connection connection = dataSource.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "SELECT count(*) FROM " + table
                                + " WHERE migration_id = ? AND source_row_id = ?")) {
            statement.setObject(1, migrationUuid(migrationId));
            statement.setLong(2, sourceRowId);
            try (ResultSet result = statement.executeQuery()) {
                assertThat(result.next()).isTrue();
                return result.getInt(1);
            }
        }
    }

    private static int mutationAuditCount(
            DataSource owner,
            String migrationId
    ) throws SQLException {
        try (Connection connection = owner.getConnection();
                PreparedStatement statement = connection.prepareStatement("""
                        SELECT count(*)
                        FROM phase4c_tag_migration_design_mutation_audit
                        WHERE migration_id = ?
                        """)) {
            statement.setObject(1, migrationUuid(migrationId));
            try (ResultSet result = statement.executeQuery()) {
                assertThat(result.next()).isTrue();
                return result.getInt(1);
            }
        }
    }

    private static int businessStatementAuditCount(DataSource owner)
            throws SQLException {
        return queryInt(owner, """
                SELECT count(*)
                FROM phase4c_tag_migration_design_statement_audit
                """);
    }

    private static boolean hasTablePrivilege(
            DataSource owner,
            String table,
            String privilege
    ) throws SQLException {
        try (Connection connection = owner.getConnection();
                PreparedStatement statement = connection.prepareStatement(
                        "SELECT has_table_privilege(?, ?, ?)")) {
            statement.setString(1, OPERATOR);
            statement.setString(2, table);
            statement.setString(3, privilege);
            try (ResultSet result = statement.executeQuery()) {
                assertThat(result.next()).isTrue();
                return result.getBoolean(1);
            }
        }
    }

    private static int executeUpdate(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return executeUpdate(connection, sql);
        }
    }

    private static int executeUpdate(Connection connection, String sql)
            throws SQLException {
        try (Statement statement = connection.createStatement()) {
            return statement.executeUpdate(sql);
        }
    }

    private static int queryInt(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return queryInt(connection, sql);
        }
    }

    private static int queryInt(Connection connection, String sql)
            throws SQLException {
        try (Statement statement = connection.createStatement();
                ResultSet result = statement.executeQuery(sql)) {
            assertThat(result.next()).isTrue();
            int value = result.getInt(1);
            assertThat(result.next()).isFalse();
            return value;
        }
    }

    private static String queryString(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            return queryString(connection, sql);
        }
    }

    private static String queryString(Connection connection, String sql)
            throws SQLException {
        try (Statement statement = connection.createStatement();
                ResultSet result = statement.executeQuery(sql)) {
            assertThat(result.next()).isTrue();
            String value = result.getString(1);
            assertThat(result.next()).isFalse();
            return value;
        }
    }

    private static boolean queryBoolean(DataSource dataSource, String sql)
            throws SQLException {
        try (Connection connection = dataSource.getConnection();
                Statement statement = connection.createStatement();
                ResultSet result = statement.executeQuery(sql)) {
            assertThat(result.next()).isTrue();
            boolean value = result.getBoolean(1);
            assertThat(result.next()).isFalse();
            return value;
        }
    }

    private static SQLException captureSqlException(SqlOperation operation) {
        try {
            operation.run();
        } catch (SQLException error) {
            return error;
        }
        throw new AssertionError("expected PostgreSQL to reject operation");
    }

    private static SQLException findSqlState(SQLException error, String state) {
        SQLException result = findSqlStateOrNull(error, state);
        if (result == null) {
            throw new AssertionError(
                    "expected SQLSTATE " + state + " but received "
                            + error.getSQLState(),
                    error);
        }
        return result;
    }

    private static SQLException findSqlStateOrNull(
            SQLException error,
            String state
    ) {
        SQLException current = error;
        while (current != null) {
            if (state.equals(current.getSQLState())) {
                return current;
            }
            current = current.getNextException();
        }
        return null;
    }

    private static void assertContractParity() throws Exception {
        Path path = contractPath();
        byte[] payload = Files.readAllBytes(path);
        assertThat(payload).hasSize((int) CONTRACT_BYTE_COUNT);
        assertThat(sha256(payload)).isEqualTo(CONTRACT_SHA256);
        JsonNode contract = JSON.readTree(payload);
        assertThat(contract.path("contract_id").asString()).isEqualTo(CONTRACT_ID);
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(CONTRACT_PAYLOAD_SHA256);
        assertThat(payloadSha256(contract)).isEqualTo(CONTRACT_PAYLOAD_SHA256);
        assertThat(contract.path("predecessor").path("sha256").asString())
                .isEqualTo(NODE_A_ANCHOR_SHA256);
        assertThat(contract.path("predecessor")
                .path("document_payload_sha256").asString())
                .isEqualTo(NODE_A_ANCHOR_PAYLOAD_SHA256);
        assertThat(contract.path("node_a_git_authority")
                .path("external_anchor_checkpoint").path("commit_oid").asString())
                .isEqualTo(NODE_A_ANCHOR_COMMIT);
        assertThat(contract.path("node_a_git_authority")
                .path("external_anchor_checkpoint").path("artifacts"))
                .hasSize(6);
        assertThat(contract.path("durable_ledger_design")
                .path("state_machine").path("transitions"))
                .hasSize(6);
        assertThat(contract.path("durable_ledger_design")
                .path("migration_id_storage_type").asString())
                .isEqualTo("uuid");
        assertThat(contract.path("durable_ledger_design")
                .path("state_machine")
                .path("applied_transition_deferred_commit_guard")
                .asBoolean()).isTrue();
        assertThat(contract.path("durable_ledger_design")
                .path("receipt_protocol")
                .path("every_frozen_source_has_exactly_one_receipt")
                .asBoolean()).isTrue();
        assertThat(contract.path("durable_ledger_design")
                .path("receipt_protocol")
                .path("empty_noop_requires_explicit_receipt")
                .asBoolean()).isTrue();
        assertThat(contract.path("durable_ledger_design")
                .path("target_fact_digest_protocol")
                .path("java_recovery_independently_recomputes_canonical_digest")
                .asBoolean()).isTrue();
        assertThat(contract.path("durable_ledger_design")
                .path("database_identity")
                .path("ledger_receipt_and_fresh_recovery_identity_exact_match")
                .asBoolean()).isTrue();
        assertThat(contract.path("retry_and_ambiguity_design")
                .path("retryable_sqlstates").toString())
                .isEqualTo("[\"40001\",\"40P01\"]");
        assertThat(contract.path("retry_and_ambiguity_design")
                .path("maximum_attempts").asInt()).isEqualTo(3);
        assertThat(contract.path("retry_and_ambiguity_design")
                .path("maximum_retries").asInt()).isEqualTo(2);
        assertThat(contract.path("retry_and_ambiguity_design")
                .path("real_postgresql_40001_traversed_retry_loop")
                .asBoolean()).isTrue();
        assertThat(contract.path("retry_and_ambiguity_design")
                .path("real_postgresql_40P01_traversed_retry_loop")
                .asBoolean()).isTrue();
        assertThat(contract.path("retry_and_ambiguity_design")
                .path("ack_discard_fixture_is_real_network_failure").asBoolean())
                .isFalse();
        assertThat(contract.path("retry_and_ambiguity_design")
                .path("real_network_commit_ack_loss_evidenced").asBoolean())
                .isFalse();
        assertThat(contract.path("evidence")
                .path("independent_java_acceptance_claimed").asBoolean())
                .isFalse();
        assertThat(contract.path("acl_and_sensitive_material_design")
                .path("fixture_role_effective_connect_privilege")
                .asBoolean()).isFalse();
        assertThat(contract.path("source_authority")
                .path("control_sources")).hasSize(8);
        assertThat(contract.path("source_authority")
                .path("ordinary_build_and_load_are_gitless").asBoolean()).isTrue();

        JsonNode authorization = contract.path("authorization");
        assertThat(authorization.path("newly_closed_gates").toString())
                .isEqualTo(
                        "[\"migration_durable_ledger_freeze_design_evidence_closed\"]");
        assertThat(authorization
                .path("migration_global_preflight_evidence_closed").asBoolean())
                .isTrue();
        assertThat(authorization.path(
                "migration_durable_ledger_freeze_design_evidence_closed")
                .asBoolean()).isTrue();
        for (String field : List.of(
                "migration_design_closed",
                "production_durable_ledger_or_tombstone",
                "production_source_write_freeze_evidence_closed",
                "production_target_write_freeze_evidence_closed",
                "production_membership_write_freeze_or_digest_recheck_evidence_closed",
                "bounded_40001_40P01_retry_implemented",
                "operator_migration_implementation",
                "production_schema_or_index",
                "flyway_baseline_or_migration",
                "backup_and_rollback_evidence_closed",
                "real_data_migration_execution",
                "legacy_runtime_permanently_disabled",
                "route_or_openapi_delta",
                "client_gateway_or_proxy_change",
                "production_cutover")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        JsonNode route = contract.path("route_state");
        assertThat(route.path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt())
                .isZero();
    }

    private static Path contractPath() throws IOException {
        String relative = "docs/refactor/phase4c/"
                + "personal-bank-tag-migration-durable-ledger-freeze-"
                + "design-contract.json";
        for (Path candidate : List.of(
                Path.of("..").resolve(relative),
                Path.of(relative),
                Path.of("Ti-Java").resolve(relative))) {
            if (Files.isRegularFile(candidate) && !Files.isSymbolicLink(candidate)) {
                return candidate.toRealPath();
            }
        }
        throw new IOException("fixed Node B contract path not found");
    }

    private static String payloadSha256(JsonNode document) {
        ObjectNode copy = (ObjectNode) document.deepCopy();
        copy.remove("document_payload_sha256");
        return sha256(JSON.writeValueAsBytes(canonicalNode(copy)));
    }

    private static JsonNode canonicalNode(JsonNode value) {
        if (value.isObject()) {
            ObjectNode object = JSON.createObjectNode();
            TreeMap<String, JsonNode> sorted = new TreeMap<>();
            value.properties().forEach(entry ->
                    sorted.put(entry.getKey(), canonicalNode(entry.getValue())));
            sorted.forEach(object::set);
            return object;
        }
        if (value.isArray()) {
            ArrayNode array = JSON.createArrayNode();
            value.forEach(item -> array.add(canonicalNode(item)));
            return array;
        }
        return value.deepCopy();
    }

    private static String sha256(byte[] value) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    private record RunIdentity(
            UUID runUuid,
            String backupManifestSha256,
            String clusterDatabaseIdentitySha256,
            String runIdentitySha256
    ) {
    }

    private enum RecoveryDisposition {
        COMMITTED_ZERO_DML,
        BLOCKED_NO_RECEIPT,
        BLOCKED_IDENTITY_MISMATCH,
        BLOCKED_RECEIPT_OR_TARGET_MISMATCH
    }

    private static final class RetryTrace {
        private int attempts;
        private int retries;
        private final List<Integer> backendProcessIds = new ArrayList<>();
        private final List<String> transactionIds = new ArrayList<>();
    }

    @FunctionalInterface
    private interface SqlOperation {
        void run() throws SQLException;
    }

    @FunctionalInterface
    private interface TransactionalSqlAttempt<T> {
        T run(Connection connection, int attempt) throws SQLException;
    }

    private static final class AckDiscardedAfterCommitFixtureException
            extends RuntimeException {

        private AckDiscardedAfterCommitFixtureException(String message) {
            super(message);
        }
    }

    private static final class SetRoleDataSource implements DataSource {

        private final DataSource delegate;
        private final String role;

        private SetRoleDataSource(DataSource delegate, String role) {
            this.delegate = delegate;
            this.role = role;
        }

        @Override
        public Connection getConnection() throws SQLException {
            Connection connection = delegate.getConnection();
            try (Statement statement = connection.createStatement()) {
                statement.execute("SET ROLE " + role);
                return connection;
            } catch (SQLException error) {
                connection.close();
                throw error;
            }
        }

        @Override
        public Connection getConnection(String username, String password)
                throws SQLException {
            throw new SQLFeatureNotSupportedException(
                    "Node B fixture has no role credentials");
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
            return delegate.unwrap(iface);
        }

        @Override
        public boolean isWrapperFor(Class<?> iface) throws SQLException {
            return delegate.isWrapperFor(iface);
        }
    }
}
