package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.Disposition;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.ManifestRow;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.RunSnapshot;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.SourceSnapshot;
import io.saksk.ti.learning.infrastructure.migration.JdbcTagMigrationStore.TargetSnapshot;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceRejectedException;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.EvidenceVerifier;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.RunBinding;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedApplyEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedFreezeEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedPrepareEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationOperatorCore.VerifiedRecoveryEvidence;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseResult;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
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
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.io.PrintWriter;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.SQLFeatureNotSupportedException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Logger;
import java.util.stream.Stream;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
@Execution(ExecutionMode.SAME_THREAD)
class Phase4cLegacyPersonalBankTagOperatorCoreIT {

    private static final String OPERATOR = "ti_phase4c_tag_operator";
    private static final String RAW_CANARY = "NODEC_CANARY_RAW_TAG_7F21";
    private static final String NORMALIZED_CANARY = "NODEC_CANARY_RAW_TAG";
    private static final SignedEvidence OPAQUE_EVIDENCE = new SignedEvidence(
            "phase4c-test-key",
            "opaque-test-only-signed-payload".getBytes(java.nio.charset.StandardCharsets.UTF_8),
            new byte[64]);

    @Container
    static final PostgreSQLContainer POSTGRES_18 = operatorFixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final PostgreSQLContainer POSTGRES_16 = operatorFixture(
            Phase2PostgresContainers.compatibility16());

    @Test
    void explicitOperatorCoreHoldsOnPostgres18() throws Exception {
        assertOperatorCore(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void explicitOperatorCoreHoldsOnPostgres16() throws Exception {
        assertOperatorCore(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    @Test
    void liveCatalogFactsAreCanonicalAcrossSupportedPostgresVersions()
            throws Exception {
        DataSource postgres16 = new SetRoleDataSource(
                new DriverManagerDataSource(
                        POSTGRES_16.getJdbcUrl(),
                        POSTGRES_16.getUsername(),
                        POSTGRES_16.getPassword()),
                OPERATOR);
        DataSource postgres18 = new SetRoleDataSource(
                new DriverManagerDataSource(
                        POSTGRES_18.getJdbcUrl(),
                        POSTGRES_18.getUsername(),
                        POSTGRES_18.getPassword()),
                OPERATOR);
        try (Connection connection16 = postgres16.getConnection();
             Connection connection18 = postgres18.getConnection()) {
            assertThat(TagMigrationSchemaVerifier.catalogFacts(connection18))
                    .containsExactlyElementsOf(
                            TagMigrationSchemaVerifier.catalogFacts(connection16));
        }
    }

    private static PostgreSQLContainer operatorFixture(PostgreSQLContainer postgres) {
        return postgres
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
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
                        "/docker-entrypoint-initdb.d/077-operator-seed.sql");
    }

    private static void assertOperatorCore(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) throws Exception {
        DriverManagerDataSource owner = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        DataSource operator = new SetRoleDataSource(owner, OPERATOR);
        JdbcClient ownerJdbc = JdbcClient.create(owner);
        JdbcClient operatorJdbc = JdbcClient.create(operator);

        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(ownerJdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(operatorJdbc.sql("SELECT current_user").query(String.class).single())
                .isEqualTo(OPERATOR);
        try (Connection connection = operator.getConnection()) {
            assertThat(TagMigrationSchemaVerifier.catalogFingerprint(connection))
                    .isEqualTo(TagMigrationSchemaVerifier.SCHEMA_FINGERPRINT);
            new TagMigrationSchemaVerifier().verify(connection);
        }

        DatabaseFingerprint before = fingerprint(ownerJdbc);
        DatabaseMembershipApi membership = new DatabaseMembershipApi(owner);
        LegacyPersonalBankTagGlobalPreflight preflight =
                new LegacyPersonalBankTagGlobalPreflight(operator, membership);
        LegacyPersonalBankTagPreflightReport report = preflight.run();
        assertThat(report.fullSweepComplete()).isTrue();
        assertThat(report.blockingRowCount()).as(report.toString()).isZero();
        assertThat(report.isDataEligible()).isTrue();
        assertThat(report.rows()).hasSize(3);
        assertThat(report.outcomeCounts())
                .containsEntry(
                        LegacyPersonalBankTagPreflightReport.RowOutcome.MIGRATABLE,
                        1L)
                .containsEntry(
                        LegacyPersonalBankTagPreflightReport.RowOutcome
                                .TARGET_ALREADY_PRESENT,
                        1L)
                .containsEntry(
                        LegacyPersonalBankTagPreflightReport.RowOutcome.EMPTY_NOOP,
                        1L);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(before);

        UUID migrationId = UUID.randomUUID();
        UUID runUuid = UUID.randomUUID();
        RunBinding binding = binding(operator, report, runUuid, expectedVersion);
        FixedEvidenceVerifier verifier = new FixedEvidenceVerifier(binding);
        LegacyPersonalBankTagMigrationOperatorCore core =
                new LegacyPersonalBankTagMigrationOperatorCore(
                        operator, membership, verifier);

        PrepareCommand prepare = new PrepareCommand(
                migrationId, runUuid, report, OPAQUE_EVIDENCE);
        TagMigrationResult prepared = core.prepare(prepare);
        assertThat(prepared.outcome()).isEqualTo(Outcome.PREPARED);
        assertThat(prepared.state()).isEqualTo(State.PLANNED);
        assertThat(prepared.sourceCount()).isEqualTo(3);
        assertThat(prepared.transactionAttempts()).isEqualTo(1);
        assertThat(prepared.transactionRetries()).isZero();
        assertThat(core.prepare(prepare).outcome())
                .isEqualTo(Outcome.ALREADY_PREPARED_ZERO_DML);

        FreezeCommand freeze = new FreezeCommand(
                migrationId, runUuid, OPAQUE_EVIDENCE);
        TagMigrationResult frozen = core.freeze(freeze);
        assertThat(frozen.outcome()).isEqualTo(Outcome.FROZEN);
        assertThat(frozen.state()).isEqualTo(State.FROZEN);
        assertThat(core.freeze(freeze).outcome())
                .isEqualTo(Outcome.ALREADY_FROZEN_ZERO_DML);

        ApplyCommand apply = new ApplyCommand(
                migrationId, runUuid, OPAQUE_EVIDENCE);
        CommitDiscardingDataSource discardFirstSourceCommit =
                new CommitDiscardingDataSource(operator, 3);
        LegacyPersonalBankTagMigrationOperatorCore ambiguousSourceCore =
                new LegacyPersonalBankTagMigrationOperatorCore(
                        discardFirstSourceCommit, membership, verifier);
        DatabaseFingerprint beforeFirstSourceCommit = fingerprint(ownerJdbc);
        TagMigrationResult ambiguousSource = ambiguousSourceCore.apply(apply);
        assertThat(discardFirstSourceCommit.discarded()).isTrue();
        assertBlocked(
                ambiguousSource,
                State.APPLYING,
                FailureCode.COMMIT_OUTCOME_UNKNOWN);
        assertThat(ownerJdbc.sql("""
                SELECT source_row_id::text || ':' || disposition || ':'
                           || inserted_target_row_count::text || ':'
                           || (actual_target_digest_sha256
                               = expected_target_digest_sha256)::text
                FROM ti_migration.personal_bank_tag_receipt
                WHERE migration_id = :migration_id
                  AND migration_run_uuid = :run_uuid
                ORDER BY source_row_id
                """)
                .param("migration_id", migrationId)
                .param("run_uuid", runUuid)
                .query(String.class)
                .list())
                .containsExactly("9901:MIGRATED:3:true");
        assertThat(ownerJdbc.sql("""
                SELECT question_id::text || ':' || tag
                FROM public.user_question_tag_items
                WHERE user_id = 9801
                  AND scope = 'user_bank'
                  AND scope_id = 9801
                ORDER BY question_id, tag COLLATE "C"
                """).query(String.class).list())
                .containsExactly(
                        "0:NODEC_CANARY_RAW_TAG",
                        "0:alpha",
                        "10801:alpha");
        DatabaseFingerprint afterFirstSourceCommit = fingerprint(ownerJdbc);
        assertThat(afterFirstSourceCommit.sourceFacts())
                .isEqualTo(beforeFirstSourceCommit.sourceFacts());
        assertThat(afterFirstSourceCommit.lastActiveFacts())
                .isEqualTo(beforeFirstSourceCommit.lastActiveFacts());
        assertThat(afterFirstSourceCommit.targetCount()
                - beforeFirstSourceCommit.targetCount()).isEqualTo(3);

        DatabaseFingerprint beforeIncompleteRecovery = fingerprint(ownerJdbc);
        TagMigrationResult incompleteRecovery = core.recover(
                new RecoveryCommand(
                        migrationId, runUuid, OPAQUE_EVIDENCE));
        assertBlocked(
                incompleteRecovery,
                State.APPLYING,
                FailureCode.ILLEGAL_STATE);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeIncompleteRecovery);

        TagMigrationResult applied = core.apply(apply);
        assertThat(applied.outcome()).isEqualTo(Outcome.APPLIED);
        assertThat(applied.state()).isEqualTo(State.APPLIED);
        assertThat(applied.sourceCount()).isEqualTo(3);
        assertThat(applied.migratedCount()).isEqualTo(1);
        assertThat(applied.targetAlreadyPresentCount()).isEqualTo(1);
        assertThat(applied.emptyNoopCount()).isEqualTo(1);
        assertThat(applied.failureCode()).isEmpty();

        DatabaseFingerprint afterApply = fingerprint(ownerJdbc);
        assertThat(afterApply.sourceFacts()).isEqualTo(before.sourceFacts());
        assertThat(afterApply.lastActiveFacts()).isEqualTo(before.lastActiveFacts());
        assertThat(afterApply.targetCount() - before.targetCount()).isEqualTo(3);
        assertThat(afterApply.targetFacts())
                .as("resuming after a source commit acknowledgement loss "
                        + "must not duplicate or rewrite that source")
                .isEqualTo(afterFirstSourceCommit.targetFacts());
        assertThat(operatorJdbc.sql("""
                SELECT count(*)
                FROM ti_migration.personal_bank_tag_receipt
                """).query(Integer.class).single()).isEqualTo(3);
        assertThat(ownerJdbc.sql("""
                SELECT event_type
                FROM ti_migration.personal_bank_tag_audit
                ORDER BY audit_id
                """).query(String.class).list())
                .containsExactly("PREPARED", "FROZEN", "APPLYING", "APPLIED");

        String durableEvidence = ownerJdbc.sql("""
                SELECT coalesce(string_agg(payload, ''), '')
                FROM (
                    SELECT row_to_json(run)::text AS payload
                    FROM ti_migration.personal_bank_tag_run AS run
                    UNION ALL
                    SELECT row_to_json(source)::text
                    FROM ti_migration.personal_bank_tag_run_source AS source
                    UNION ALL
                    SELECT row_to_json(receipt)::text
                    FROM ti_migration.personal_bank_tag_receipt AS receipt
                    UNION ALL
                    SELECT row_to_json(audit)::text
                    FROM ti_migration.personal_bank_tag_audit AS audit
                ) AS durable_rows
                """).query(String.class).single();
        assertThat(durableEvidence).doesNotContain(RAW_CANARY);
        assertThat(ownerJdbc.sql("""
                SELECT count(*)
                FROM user_question_tag_items
                WHERE tag = :canary
                """).param("canary", NORMALIZED_CANARY)
                .query(Integer.class).single())
                .isEqualTo(1);

        RecoveryCommand recovery = new RecoveryCommand(
                migrationId, runUuid, OPAQUE_EVIDENCE);
        DatabaseFingerprint beforeRecovery = fingerprint(ownerJdbc);
        TagMigrationResult recovered = core.recover(recovery);
        assertThat(recovered.outcome())
                .isEqualTo(Outcome.ALREADY_APPLIED_ZERO_DML);
        assertThat(recovered.state()).isEqualTo(State.APPLIED);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeRecovery);

        assertThat(core.apply(apply).outcome())
                .isEqualTo(Outcome.ALREADY_APPLIED_ZERO_DML);

        assertNegativeOperatorMatrix(
                owner, operator, ownerJdbc, membership, expectedVersion);
    }

    private static void assertNegativeOperatorMatrix(
            DataSource owner,
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        assertSchemaFailuresArePreDml(
                operator, ownerJdbc, membership, expectedVersion);
        assertHostileSearchPathIsContained(
                owner, ownerJdbc, membership, expectedVersion);
        assertLockAndEvidenceBoundaries(
                owner, operator, ownerJdbc, membership, expectedVersion);
        assertSessionSqlIsBounded(
                owner, operator, ownerJdbc, membership, expectedVersion);

        DatabaseFingerprint beforeFixture = fingerprint(ownerJdbc);
        installNegativeFixture(ownerJdbc);
        try {
            assertDurableDriftClassification(
                    operator, ownerJdbc, membership, expectedVersion);
            assertBoundedSourceRevalidation(
                    operator, ownerJdbc, membership, expectedVersion);
            assertBoundedTargetRevalidation(
                    operator, ownerJdbc, membership, expectedVersion);
            assertStaleCasHasOneWinner(
                    operator, membership, expectedVersion);
            assertIncompleteApplyAndReceiptGuards(
                    operator, ownerJdbc, membership, expectedVersion);
            assertFinalCommitAcknowledgementRecovery(
                    operator, ownerJdbc, membership, expectedVersion);
        } finally {
            removeNegativeFixture(ownerJdbc);
        }
        DatabaseFingerprint afterFixture = fingerprint(ownerJdbc);
        assertThat(afterFixture.sourceFacts())
                .isEqualTo(beforeFixture.sourceFacts());
        assertThat(afterFixture.lastActiveFacts())
                .isEqualTo(beforeFixture.lastActiveFacts());
        assertThat(afterFixture.targetCount())
                .isEqualTo(beforeFixture.targetCount());
        assertCanonicalCatalog(operator);
    }

    private static void assertSchemaFailuresArePreDml(
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        UPDATE ti_migration.operator_schema_metadata
                        SET schema_fingerprint = repeat('0', 64)
                        """).update(),
                () -> ownerJdbc.sql("""
                        UPDATE ti_migration.operator_schema_metadata
                        SET schema_fingerprint = :fingerprint
                        """).param(
                                "fingerprint",
                                TagMigrationSchemaVerifier.SCHEMA_FINGERPRINT)
                        .update(),
                FailureCode.SCHEMA_FINGERPRINT_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        ALTER TABLE ti_migration.personal_bank_tag_run
                        SET (fillfactor = 80)
                        """).update(),
                () -> ownerJdbc.sql("""
                        ALTER TABLE ti_migration.personal_bank_tag_run
                        RESET (fillfactor)
                        """).update(),
                FailureCode.SCHEMA_FINGERPRINT_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        GRANT UPDATE ON public.user_progress
                        TO ti_phase4c_tag_operator
                        """).update(),
                () -> ownerJdbc.sql("""
                        REVOKE UPDATE ON public.user_progress
                        FROM ti_phase4c_tag_operator
                        """).update(),
                FailureCode.SCHEMA_ACL_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        GRANT ti_phase4c_tag_schema_owner
                        TO ti_phase4c_tag_operator
                        """).update(),
                () -> ownerJdbc.sql("""
                        REVOKE ti_phase4c_tag_schema_owner
                        FROM ti_phase4c_tag_operator
                        """).update(),
                FailureCode.SCHEMA_ACL_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        ALTER ROLE ti_phase4c_tag_operator INHERIT
                        """).update(),
                () -> ownerJdbc.sql("""
                        ALTER ROLE ti_phase4c_tag_operator NOINHERIT
                        """).update(),
                FailureCode.SCHEMA_ACL_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        GRANT SELECT ON public.users
                        TO ti_phase4c_tag_operator
                        """).update(),
                () -> ownerJdbc.sql("""
                        REVOKE SELECT ON public.users
                        FROM ti_phase4c_tag_operator
                        """).update(),
                FailureCode.SCHEMA_ACL_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        GRANT SELECT (password_hash) ON public.users
                        TO ti_phase4c_tag_operator
                        """).update(),
                () -> ownerJdbc.sql("""
                        REVOKE SELECT (password_hash) ON public.users
                        FROM ti_phase4c_tag_operator
                        """).update(),
                FailureCode.SCHEMA_ACL_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        CREATE FUNCTION public.phase4c_nodec_unexpected_acl()
                        RETURNS integer LANGUAGE sql AS 'SELECT 1'
                        """).update(),
                () -> ownerJdbc.sql("""
                        DROP FUNCTION public.phase4c_nodec_unexpected_acl()
                        """).update(),
                FailureCode.SCHEMA_ACL_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        ALTER FUNCTION
                        ti_migration.personal_bank_tag_target_digest(bigint, integer)
                        SECURITY INVOKER
                        """).update(),
                () -> ownerJdbc.sql("""
                        ALTER FUNCTION
                        ti_migration.personal_bank_tag_target_digest(bigint, integer)
                        SECURITY DEFINER
                        """).update(),
                FailureCode.SCHEMA_FINGERPRINT_MISMATCH);
        assertSchemaFailureBeforeDml(
                operator, ownerJdbc, membership, expectedVersion,
                () -> ownerJdbc.sql("""
                        ALTER TABLE public.user_question_tag_items
                        DISABLE TRIGGER personal_bank_tag_target_insert_guard
                        """).update(),
                () -> ownerJdbc.sql("""
                        ALTER TABLE public.user_question_tag_items
                        ENABLE TRIGGER personal_bank_tag_target_insert_guard
                        """).update(),
                FailureCode.SCHEMA_FINGERPRINT_MISMATCH);
    }

    private static void assertSchemaFailureBeforeDml(
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion,
            Runnable mutation,
            Runnable restoration,
            FailureCode expectedFailure
    ) throws Exception {
        FreshPrepare fresh = freshPrepare(
                operator, membership, expectedVersion);
        DatabaseFingerprint before = fingerprint(ownerJdbc);
        mutation.run();
        try {
            TagMigrationResult rejected = fresh.core().prepare(fresh.command());
            assertBlocked(
                    rejected, State.UNAVAILABLE, expectedFailure);
            assertThat(fingerprint(ownerJdbc)).isEqualTo(before);
        } finally {
            restoration.run();
        }
        assertCanonicalCatalog(operator);
    }

    private static void assertCanonicalCatalog(DataSource operator)
            throws Exception {
        try (Connection connection = operator.getConnection()) {
            assertThat(TagMigrationSchemaVerifier.catalogFingerprint(connection))
                    .isEqualTo(TagMigrationSchemaVerifier.SCHEMA_FINGERPRINT);
            new TagMigrationSchemaVerifier().verify(connection);
        }
    }

    private static void assertHostileSearchPathIsContained(
            DataSource owner,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        DataSource hostile = new SetRoleDataSource(
                owner,
                OPERATOR,
                "SET search_path TO pg_temp, pg_catalog");
        try (Connection connection = hostile.getConnection();
             Statement statement = connection.createStatement();
             ResultSet row = statement.executeQuery("SHOW search_path")) {
            assertThat(row.next()).isTrue();
            assertThat(row.getString(1)).isEqualTo("pg_temp, pg_catalog");
        }

        FreshPrepare fresh = freshPrepare(
                hostile, membership, expectedVersion);
        DatabaseFingerprint before = fingerprint(ownerJdbc);
        TagMigrationResult prepared = fresh.core().prepare(fresh.command());
        assertThat(prepared.outcome())
                .as(prepared.toString())
                .isEqualTo(Outcome.PREPARED);
        TagMigrationResult frozen = fresh.core().freeze(new FreezeCommand(
                fresh.command().migrationId(),
                fresh.command().migrationRunUuid(),
                OPAQUE_EVIDENCE));
        assertThat(frozen.outcome())
                .as(frozen.toString())
                .isEqualTo(Outcome.FROZEN);
        TagMigrationResult applied = fresh.core().apply(new ApplyCommand(
                fresh.command().migrationId(),
                fresh.command().migrationRunUuid(),
                OPAQUE_EVIDENCE));
        assertThat(applied.outcome())
                .as(applied.toString())
                .isEqualTo(Outcome.APPLIED);
        DatabaseFingerprint after = fingerprint(ownerJdbc);
        assertThat(after.sourceFacts()).isEqualTo(before.sourceFacts());
        assertThat(after.lastActiveFacts()).isEqualTo(before.lastActiveFacts());
    }

    private static void assertLockAndEvidenceBoundaries(
            DataSource owner,
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        FreshPrepare lockCase = freshPrepare(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeLock = fingerprint(ownerJdbc);
        try (Connection holder = owner.getConnection();
             PreparedStatement lock = holder.prepareStatement(
                     "SELECT pg_catalog.pg_advisory_lock(?)");
             PreparedStatement unlock = holder.prepareStatement(
                     "SELECT pg_catalog.pg_advisory_unlock(?)")) {
            lock.setLong(
                    1, LegacyPersonalBankTagGlobalPreflight.advisoryLockKey());
            lock.execute();
            try {
                assertBlocked(
                        lockCase.core().prepare(lockCase.command()),
                        State.UNAVAILABLE,
                        FailureCode.LOCK_BUSY);
                assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeLock);
            } finally {
                unlock.setLong(
                        1,
                        LegacyPersonalBankTagGlobalPreflight.advisoryLockKey());
                try (ResultSet row = unlock.executeQuery()) {
                    assertThat(row.next()).isTrue();
                    assertThat(row.getBoolean(1)).isTrue();
                }
            }
        }

        FreshPrepare evidenceCase = freshPrepare(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeEvidence = fingerprint(ownerJdbc);
        LegacyPersonalBankTagMigrationOperatorCore rejectingCore =
                new LegacyPersonalBankTagMigrationOperatorCore(
                        operator, membership, new RejectingEvidenceVerifier());
        assertBlocked(
                rejectingCore.prepare(evidenceCase.command()),
                State.UNAVAILABLE,
                FailureCode.EVIDENCE_REJECTED);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeEvidence);

        FreshPrepare identityCase = freshPrepare(
                operator, membership, expectedVersion);
        RunBinding binding = identityCase.verifier().prepare.binding();
        RunBinding wrongIdentity = new RunBinding(
                binding.backupManifestSha256(),
                FixedEvidenceVerifier.digest("wrong-database-identity"),
                binding.runIdentitySha256(),
                binding.preflightDigestSha256(),
                binding.sourceSetDigestSha256(),
                binding.planSetDigestSha256(),
                binding.preapplyTargetSetDigestSha256(),
                binding.finalTargetSetDigestSha256(),
                binding.membershipSetDigestSha256());
        LegacyPersonalBankTagMigrationOperatorCore wrongIdentityCore =
                new LegacyPersonalBankTagMigrationOperatorCore(
                        operator,
                        membership,
                        new FixedEvidenceVerifier(wrongIdentity));
        DatabaseFingerprint beforeIdentity = fingerprint(ownerJdbc);
        assertBlocked(
                wrongIdentityCore.prepare(identityCase.command()),
                State.UNAVAILABLE,
                FailureCode.IDENTITY_MISMATCH);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeIdentity);

        PreparedScenario writerReceiptCase = frozenScenario(
                operator, membership, expectedVersion);
        RunBinding writerReceiptBinding =
                writerReceiptCase.verifier().prepare.binding();
        DatabaseFingerprint beforeWriterReceiptMismatch =
                fingerprint(ownerJdbc);
        List<FixedEvidenceVerifier> mismatchedWriterReceipts = List.of(
                new FixedEvidenceVerifier(
                        writerReceiptBinding,
                        "-mismatch", "", "", "", ""),
                new FixedEvidenceVerifier(
                        writerReceiptBinding,
                        "", "-mismatch", "", "", ""),
                new FixedEvidenceVerifier(
                        writerReceiptBinding,
                        "", "", "-mismatch", "", ""));
        for (FixedEvidenceVerifier mismatched : mismatchedWriterReceipts) {
            LegacyPersonalBankTagMigrationOperatorCore mismatchedCore =
                    new LegacyPersonalBankTagMigrationOperatorCore(
                            operator, membership, mismatched);
            assertBlocked(
                    mismatchedCore.apply(writerReceiptCase.applyCommand()),
                    State.FROZEN,
                    FailureCode.EVIDENCE_REJECTED);
            assertThat(fingerprint(ownerJdbc))
                    .isEqualTo(beforeWriterReceiptMismatch);
        }

        PreparedScenario collapsedWriterReceiptCase = preparedScenario(
                operator, membership, expectedVersion);
        VerifiedFreezeEvidence validReceipts =
                collapsedWriterReceiptCase.verifier().freeze;
        String collapsedReceipt = validReceipts
                .sourceWriterStopReceiptSha256();
        DatabaseFingerprint beforeCollapsedWriterReceipt =
                fingerprint(ownerJdbc);
        JdbcTagMigrationStore store = new JdbcTagMigrationStore(operator);
        try (Connection connection = operator.getConnection()) {
            connection.setAutoCommit(false);
            RunSnapshot planned = store.readRun(
                            connection,
                            collapsedWriterReceiptCase.migrationId(),
                            collapsedWriterReceiptCase.runUuid(),
                            true)
                    .orElseThrow();
            try {
                store.freeze(
                        connection,
                        planned,
                        collapsedReceipt,
                        collapsedReceipt,
                        collapsedReceipt,
                        validReceipts.connectionDrainReceiptSha256(),
                        validReceipts.connectionRejectionReceiptSha256(),
                        validReceipts.restoredBackupReceiptSha256());
                throw new AssertionError(
                        "database accepted collapsed writer-stop receipts");
            } catch (SQLException rejected) {
                assertThat(rejected.getSQLState()).isEqualTo("23514");
            } finally {
                connection.rollback();
            }
        }
        assertThat(fingerprint(ownerJdbc))
                .as("collapsed receipts fail before ledger, receipt, or target DML")
                .isEqualTo(beforeCollapsedWriterReceipt);
    }

    private static void assertSessionSqlIsBounded(
            DataSource owner,
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        FreshPrepare setupTimeout = freshPrepare(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeSetupTimeout = fingerprint(ownerJdbc);
        TimedResult setupResult;
        try (Connection blocker = owner.getConnection();
             Statement lock = blocker.createStatement()) {
            blocker.setAutoCommit(false);
            lock.execute("""
                    LOCK TABLE ti_migration.operator_schema_metadata
                    IN ACCESS EXCLUSIVE MODE
                    """);
            try {
                setupResult = awaitBounded(
                        () -> setupTimeout.core().prepare(
                                setupTimeout.command()),
                        blocker,
                        "operator setup SQL");
            } finally {
                blocker.rollback();
            }
        }
        assertThat(setupResult.elapsedMillis()).isBetween(4_000L, 9_000L);
        assertBlocked(
                setupResult.result(), State.UNAVAILABLE,
                FailureCode.SQL_FAILURE);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeSetupTimeout);
        assertThat(setupTimeout.core().prepare(setupTimeout.command()).outcome())
                .isEqualTo(Outcome.PREPARED);

        PreparedScenario recoveryTimeout = preparedScenario(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeRecoveryTimeout = fingerprint(ownerJdbc);
        TimedResult recoveryResult;
        try (Connection blocker = owner.getConnection();
             Statement lock = blocker.createStatement()) {
            blocker.setAutoCommit(false);
            lock.execute("""
                    LOCK TABLE ti_migration.personal_bank_tag_receipt
                    IN ACCESS EXCLUSIVE MODE
                    """);
            try {
                recoveryResult = awaitBounded(
                        () -> recoveryTimeout.core().recover(
                                recoveryTimeout.recoveryCommand()),
                        blocker,
                        "read-only recovery SQL");
            } finally {
                blocker.rollback();
            }
        }
        assertThat(recoveryResult.elapsedMillis()).isBetween(4_000L, 9_000L);
        assertBlocked(
                recoveryResult.result(), State.UNAVAILABLE,
                FailureCode.SQL_FAILURE);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeRecoveryTimeout);
        assertBlocked(
                recoveryTimeout.core().recover(
                        recoveryTimeout.recoveryCommand()),
                State.PLANNED,
                FailureCode.ILLEGAL_STATE);
    }

    private static TimedResult awaitBounded(
            Callable<TagMigrationResult> operation,
            Connection blocker,
            String label
    ) throws Exception {
        ExecutorService executor = Executors.newSingleThreadExecutor();
        long started = System.nanoTime();
        Future<TagMigrationResult> future = executor.submit(operation);
        try {
            TagMigrationResult result = future.get(9, TimeUnit.SECONDS);
            long elapsedMillis = TimeUnit.NANOSECONDS.toMillis(
                    System.nanoTime() - started);
            return new TimedResult(result, elapsedMillis);
        } catch (TimeoutException timeout) {
            blocker.rollback();
            try {
                future.get(10, TimeUnit.SECONDS);
            } catch (Exception completionFailure) {
                timeout.addSuppressed(completionFailure);
            }
            throw new AssertionError(label + " exceeded the fixed timeout", timeout);
        } finally {
            executor.shutdownNow();
            assertThat(executor.awaitTermination(10, TimeUnit.SECONDS))
                    .as(label + " worker terminated")
                    .isTrue();
        }
    }

    private static void assertDurableDriftClassification(
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        PreparedScenario sourceDrift = preparedScenario(
                operator, membership, expectedVersion);
        String originalData = ownerJdbc.sql("""
                SELECT data FROM public.user_progress WHERE id = 9910
                """).query(String.class).single();
        DatabaseFingerprint beforeSourceDrift = fingerprint(ownerJdbc);
        ownerJdbc.sql("""
                UPDATE public.user_progress
                SET data = '{"tags":["source-drift"],"question_tags":{}}'
                WHERE id = 9910
                """).update();
        TagMigrationResult sourceBlocked;
        try {
            sourceBlocked = sourceDrift.core().freeze(
                    sourceDrift.freezeCommand());
        } finally {
            ownerJdbc.sql("""
                    UPDATE public.user_progress SET data = :data WHERE id = 9910
                    """).param("data", originalData).update();
        }
        assertBlocked(sourceBlocked, State.BLOCKED, FailureCode.SOURCE_DRIFT);
        assertDurablyBlocked(ownerJdbc, sourceDrift, FailureCode.SOURCE_DRIFT);
        assertBusinessFactsUnchanged(beforeSourceDrift, fingerprint(ownerJdbc));

        PreparedScenario targetDrift = preparedScenario(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeTargetDrift = fingerprint(ownerJdbc);
        ownerJdbc.sql("""
                INSERT INTO public.user_question_tag_items (
                    user_id, scope, scope_id, question_id, tag
                ) VALUES (9810, 'user_bank', 9810, 0, 'target-drift')
                """).update();
        TagMigrationResult targetBlocked;
        try {
            targetBlocked = targetDrift.core().freeze(
                    targetDrift.freezeCommand());
        } finally {
            ownerJdbc.sql("""
                    DELETE FROM public.user_question_tag_items
                    WHERE user_id = 9810
                      AND scope = 'user_bank'
                      AND scope_id = 9810
                      AND question_id = 0
                      AND tag = 'target-drift'
                    """).update();
        }
        assertBlocked(targetBlocked, State.BLOCKED, FailureCode.TARGET_MISMATCH);
        assertDurablyBlocked(ownerJdbc, targetDrift, FailureCode.TARGET_MISMATCH);
        assertBusinessFactsUnchanged(beforeTargetDrift, fingerprint(ownerJdbc));

        PreparedScenario membershipDrift = preparedScenario(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeMembershipDrift = fingerprint(ownerJdbc);
        ownerJdbc.sql("""
                DELETE FROM public.user_bank_questions WHERE id = 10810
                """).update();
        TagMigrationResult membershipBlocked;
        try {
            membershipBlocked = membershipDrift.core().freeze(
                    membershipDrift.freezeCommand());
        } finally {
            ownerJdbc.sql("""
                    INSERT INTO public.user_bank_questions (
                        id, bank_id, user_id, type, content
                    ) VALUES (
                        10810, 9810, 9810, 'single_choice',
                        'operator negative membership'
                    )
                    """).update();
        }
        assertBlocked(
                membershipBlocked,
                State.BLOCKED,
                FailureCode.MEMBERSHIP_DRIFT);
        assertDurablyBlocked(
                ownerJdbc, membershipDrift, FailureCode.MEMBERSHIP_DRIFT);
        assertBusinessFactsUnchanged(
                beforeMembershipDrift, fingerprint(ownerJdbc));
    }

    private static void assertBoundedSourceRevalidation(
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        JdbcTagMigrationStore store = new JdbcTagMigrationStore(operator);
        String originalData = ownerJdbc.sql("""
                SELECT data FROM public.user_progress WHERE id = 9910
                """).query(String.class).single();
        int payloadBytes = LegacyPersonalBankTagPreflightParser
                .MAX_PAYLOAD_UTF8_BYTES + 1;

        PreparedScenario oversizedPayload = preparedScenario(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforePayload = fingerprint(ownerJdbc);
        ownerJdbc.sql("""
                UPDATE public.user_progress
                SET data = repeat('x', :payload_bytes)
                WHERE id = 9910
                """).param("payload_bytes", payloadBytes).update();
        TagMigrationResult payloadBlocked;
        try {
            try (Connection connection = operator.getConnection()) {
                SourceSnapshot source = store.readSource(connection, 9910L)
                        .orElseThrow();
                assertThat(source.data()).isNull();
                assertThat(source.sourceUtf8Bytes()).isEqualTo(payloadBytes);
                assertThat(source.payloadTooLarge()).isTrue();
            }
            payloadBlocked = oversizedPayload.core().freeze(
                    oversizedPayload.freezeCommand());
        } finally {
            ownerJdbc.sql("""
                    UPDATE public.user_progress SET data = :data WHERE id = 9910
                    """).param("data", originalData).update();
        }
        assertBlocked(
                payloadBlocked, State.BLOCKED, FailureCode.SOURCE_DRIFT);
        assertDurablyBlocked(
                ownerJdbc, oversizedPayload, FailureCode.SOURCE_DRIFT);
        assertThat(receiptCount(ownerJdbc, oversizedPayload)).isZero();
        assertThat(negativeTargetCount(ownerJdbc)).isZero();
        assertBusinessFactsUnchanged(beforePayload, fingerprint(ownerJdbc));

        PreparedScenario oversizedSourceSet = preparedScenario(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeSourceSet = fingerprint(ownerJdbc);
        int sourceLimit = LegacyPersonalBankTagGlobalPreflight
                .MAX_RESERVED_SOURCE_ROWS;
        int bulkSourceBase = 20_000_000;
        ownerJdbc.sql("""
                INSERT INTO public.user_progress (id, user_id, p_key, data)
                SELECT :base_id + series_value, 9810,
                       'bank_' || (:base_id + series_value)::text || '_tags',
                       '{}'
                FROM generate_series(1, :bulk_count)
                    AS generated(series_value)
                """)
                .param("base_id", bulkSourceBase)
                .param("bulk_count", sourceLimit + 1)
                .update();
        TagMigrationResult sourceSetBlocked;
        try {
            try (Connection connection = operator.getConnection()) {
                assertThat(store.readReservedSourceIds(connection))
                        .hasSize(sourceLimit + 1);
            }
            sourceSetBlocked = oversizedSourceSet.core().freeze(
                    oversizedSourceSet.freezeCommand());
        } finally {
            ownerJdbc.sql("""
                    DELETE FROM public.user_progress
                    WHERE id BETWEEN :first_id AND :last_id
                    """)
                    .param("first_id", bulkSourceBase + 1)
                    .param("last_id", bulkSourceBase + sourceLimit + 1)
                    .update();
        }
        assertBlocked(
                sourceSetBlocked, State.BLOCKED, FailureCode.SOURCE_DRIFT);
        assertDurablyBlocked(
                ownerJdbc, oversizedSourceSet, FailureCode.SOURCE_DRIFT);
        assertThat(receiptCount(ownerJdbc, oversizedSourceSet)).isZero();
        assertThat(negativeTargetCount(ownerJdbc)).isZero();
        assertBusinessFactsUnchanged(beforeSourceSet, fingerprint(ownerJdbc));
    }

    private static void assertBoundedTargetRevalidation(
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        JdbcTagMigrationStore store = new JdbcTagMigrationStore(operator);
        String oversizedTag = "😀".repeat(
                LegacyPersonalBankTagPreflightParser.MAX_TAG_CODE_POINTS + 1);
        PreparedScenario oversizedTagScenario = preparedScenario(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeTag = fingerprint(ownerJdbc);
        ownerJdbc.sql("""
                INSERT INTO public.user_question_tag_items (
                    user_id, scope, scope_id, question_id, tag
                ) VALUES (9810, 'user_bank', 9810, 0, :tag)
                """).param("tag", oversizedTag).update();
        TagMigrationResult tagBlocked;
        try {
            try (Connection connection = operator.getConnection()) {
                TargetSnapshot target = store.readTarget(
                        connection, 9810L, 9810);
                assertThat(target.rawRowCount()).isOne();
                assertThat(target.structurallyValid()).isFalse();
                assertThat(target.rows()).isEmpty();
                assertThat(target.operatorDigestSha256()).isNull();
            }
            tagBlocked = oversizedTagScenario.core().freeze(
                    oversizedTagScenario.freezeCommand());
        } finally {
            ownerJdbc.sql("""
                    DELETE FROM public.user_question_tag_items
                    WHERE user_id = 9810
                      AND scope = 'user_bank'
                      AND scope_id = 9810
                      AND question_id = 0
                      AND tag = :tag
                    """).param("tag", oversizedTag).update();
        }
        assertBlocked(
                tagBlocked, State.BLOCKED, FailureCode.TARGET_MISMATCH);
        assertDurablyBlocked(
                ownerJdbc, oversizedTagScenario, FailureCode.TARGET_MISMATCH);
        assertThat(receiptCount(ownerJdbc, oversizedTagScenario)).isZero();
        assertThat(negativeTargetCount(ownerJdbc)).isZero();
        assertBusinessFactsUnchanged(beforeTag, fingerprint(ownerJdbc));

        PreparedScenario oversizedTargetSet = preparedScenario(
                operator, membership, expectedVersion);
        DatabaseFingerprint beforeTargetSet = fingerprint(ownerJdbc);
        int targetLimit = LegacyPersonalBankTagPreflightParser.MAX_PLANNED_ROWS;
        int questionBase = 30_000_000;
        ownerJdbc.sql("""
                INSERT INTO public.user_question_tag_items (
                    user_id, scope, scope_id, question_id, tag
                )
                SELECT 9810, 'user_bank', 9810,
                       :question_base + series_value, 'bulk'
                FROM generate_series(1, :bulk_count)
                    AS generated(series_value)
                """)
                .param("question_base", questionBase)
                .param("bulk_count", targetLimit + 1)
                .update();
        TagMigrationResult targetSetBlocked;
        try {
            try (Connection connection = operator.getConnection()) {
                TargetSnapshot target = store.readTarget(
                        connection, 9810L, 9810);
                assertThat(target.rawRowCount()).isEqualTo(targetLimit + 1);
                assertThat(target.structurallyValid()).isFalse();
                assertThat(target.operatorDigestSha256()).isNull();
            }
            targetSetBlocked = oversizedTargetSet.core().freeze(
                    oversizedTargetSet.freezeCommand());
        } finally {
            ownerJdbc.sql("""
                    DELETE FROM public.user_question_tag_items
                    WHERE user_id = 9810
                      AND scope = 'user_bank'
                      AND scope_id = 9810
                      AND question_id BETWEEN :first_id AND :last_id
                    """)
                    .param("first_id", questionBase + 1)
                    .param("last_id", questionBase + targetLimit + 1)
                    .update();
        }
        assertBlocked(
                targetSetBlocked, State.BLOCKED, FailureCode.TARGET_MISMATCH);
        assertDurablyBlocked(
                ownerJdbc, oversizedTargetSet, FailureCode.TARGET_MISMATCH);
        assertThat(receiptCount(ownerJdbc, oversizedTargetSet)).isZero();
        assertThat(negativeTargetCount(ownerJdbc)).isZero();
        assertBusinessFactsUnchanged(
                beforeTargetSet, fingerprint(ownerJdbc));
    }

    private static void assertStaleCasHasOneWinner(
            DataSource operator,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        PreparedScenario scenario = preparedScenario(
                operator, membership, expectedVersion);
        JdbcTagMigrationStore store = new JdbcTagMigrationStore(operator);
        VerifiedFreezeEvidence receipts = scenario.verifier().freeze;
        try (Connection first = operator.getConnection();
             Connection stale = operator.getConnection()) {
            first.setAutoCommit(false);
            stale.setAutoCommit(false);
            RunSnapshot firstSnapshot = store.readRun(
                            first,
                            scenario.migrationId(),
                            scenario.runUuid(),
                            false)
                    .orElseThrow();
            RunSnapshot staleSnapshot = store.readRun(
                            stale,
                            scenario.migrationId(),
                            scenario.runUuid(),
                            false)
                    .orElseThrow();
            int firstChanged = store.freeze(
                    first,
                    firstSnapshot,
                    receipts.sourceWriterStopReceiptSha256(),
                    receipts.targetWriterStopReceiptSha256(),
                    receipts.membershipWriterStopReceiptSha256(),
                    receipts.connectionDrainReceiptSha256(),
                    receipts.connectionRejectionReceiptSha256(),
                    receipts.restoredBackupReceiptSha256());
            first.commit();
            int staleChanged = store.freeze(
                    stale,
                    staleSnapshot,
                    receipts.sourceWriterStopReceiptSha256(),
                    receipts.targetWriterStopReceiptSha256(),
                    receipts.membershipWriterStopReceiptSha256(),
                    receipts.connectionDrainReceiptSha256(),
                    receipts.connectionRejectionReceiptSha256(),
                    receipts.restoredBackupReceiptSha256());
            stale.rollback();
            assertThat(List.of(firstChanged, staleChanged))
                    .containsExactly(1, 0);
        }
    }

    private static void assertDurablyBlocked(
            JdbcClient ownerJdbc,
            PreparedScenario scenario,
            FailureCode expectedFailure
    ) {
        List<String> state = ownerJdbc.sql("""
                SELECT state || ':' || blocked_failure_code
                FROM ti_migration.personal_bank_tag_run
                WHERE migration_id = :migration_id
                  AND migration_run_uuid = :run_uuid
                """)
                .param("migration_id", scenario.migrationId())
                .param("run_uuid", scenario.runUuid())
                .query(String.class)
                .list();
        assertThat(state).containsExactly("BLOCKED:" + expectedFailure.name());
    }

    private static void assertBusinessFactsUnchanged(
            DatabaseFingerprint before,
            DatabaseFingerprint after
    ) {
        assertThat(after.sourceFacts()).isEqualTo(before.sourceFacts());
        assertThat(after.lastActiveFacts()).isEqualTo(before.lastActiveFacts());
        assertThat(after.targetFacts()).isEqualTo(before.targetFacts());
        assertThat(after.targetCount()).isEqualTo(before.targetCount());
    }

    private static void assertIncompleteApplyAndReceiptGuards(
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        PreparedScenario scenario = frozenScenario(
                operator, membership, expectedVersion);
        CommitDiscardingDataSource discardApplyStart =
                new CommitDiscardingDataSource(operator, 2);
        LegacyPersonalBankTagMigrationOperatorCore ambiguousCore =
                new LegacyPersonalBankTagMigrationOperatorCore(
                        discardApplyStart,
                        membership,
                        scenario.verifier());
        DatabaseFingerprint beforeAmbiguousApply = fingerprint(ownerJdbc);
        TagMigrationResult ambiguous = ambiguousCore.apply(
                scenario.applyCommand());
        assertThat(discardApplyStart.discarded()).isTrue();
        assertBlocked(
                ambiguous,
                State.APPLYING,
                FailureCode.COMMIT_OUTCOME_UNKNOWN);
        assertThat(receiptCount(ownerJdbc, scenario)).isZero();
        assertThat(negativeTargetCount(ownerJdbc)).isZero();
        DatabaseFingerprint afterAmbiguousApply = fingerprint(ownerJdbc);
        assertThat(afterAmbiguousApply.sourceFacts())
                .isEqualTo(beforeAmbiguousApply.sourceFacts());
        assertThat(afterAmbiguousApply.lastActiveFacts())
                .isEqualTo(beforeAmbiguousApply.lastActiveFacts());

        try (Connection connection = operator.getConnection();
             PreparedStatement statement = connection.prepareStatement("""
                     INSERT INTO public.user_question_tag_items (
                         user_id, scope, scope_id, question_id, tag
                     ) VALUES (9810, 'user_bank', 9810, 0, 'forged-target')
                     """)) {
            try {
                statement.executeUpdate();
                throw new AssertionError("target guard accepted an unreceipted insert");
            } catch (SQLException rejected) {
                assertThat(rejected.getSQLState()).isEqualTo("42501");
            }
        }

        JdbcTagMigrationStore store = new JdbcTagMigrationStore(operator);
        RunSnapshot applying;
        ManifestRow migrated;
        ManifestRow sparseReceipt;
        List<TagRow> targetRows;
        try (Connection connection = operator.getConnection()) {
            applying = store.readRun(
                            connection,
                            scenario.migrationId(),
                            scenario.runUuid(),
                            false)
                    .orElseThrow();
            List<ManifestRow> manifest = store.readManifest(
                    connection,
                    scenario.migrationId(),
                    scenario.runUuid());
            migrated = manifest
                    .stream()
                    .filter(row -> row.disposition() == Disposition.MIGRATED)
                    .findFirst()
                    .orElseThrow();
            sparseReceipt = manifest.get(1);
            assertThat(sparseReceipt.disposition())
                    .isEqualTo(Disposition.TARGET_ALREADY_PRESENT);
            SourceSnapshot source = store.readSource(
                            connection, migrated.sourceRowId())
                    .orElseThrow();
            targetRows = LegacyPersonalBankTagPreflightParser
                    .parse(source.data()).rows();
        }

        try (Connection connection = operator.getConnection()) {
            connection.setAutoCommit(false);
            try {
                store.insertReceipt(
                        connection,
                        applying,
                        migrated,
                        FixedEvidenceVerifier.digest("forged-target-digest"),
                        migrated.planRowCount());
                throw new AssertionError("receipt guard accepted forged evidence");
            } catch (SQLException rejected) {
                assertThat(rejected.getSQLState()).isEqualTo("23514");
            } finally {
                connection.rollback();
            }
        }

        try (Connection connection = operator.getConnection()) {
            connection.setAutoCommit(false);
            store.insertReceipt(
                    connection,
                    applying,
                    migrated,
                    migrated.expectedTargetDigestSha256(),
                    migrated.planRowCount());
            store.insertTargetRows(connection, migrated, targetRows);
            assertThat(store.readReceipt(
                            connection,
                            scenario.migrationId(),
                            scenario.runUuid(),
                            migrated.sourceRowId()))
                    .isPresent();
            assertThat(store.readTarget(
                            connection,
                            migrated.userId(),
                            migrated.bankId()).rawRowCount())
                    .isEqualTo(migrated.planRowCount());
            connection.rollback();
        }
        assertThat(receiptCount(ownerJdbc, scenario)).isZero();
        assertThat(negativeTargetCount(ownerJdbc)).isZero();

        DatabaseFingerprint beforeRecovery = fingerprint(ownerJdbc);
        TagMigrationResult recovered = scenario.core().recover(
                scenario.recoveryCommand());
        assertBlocked(recovered, State.APPLYING, FailureCode.ILLEGAL_STATE);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeRecovery);

        try (Connection connection = operator.getConnection()) {
            connection.setAutoCommit(false);
            store.insertReceipt(
                    connection,
                    applying,
                    sparseReceipt,
                    sparseReceipt.expectedTargetDigestSha256(),
                    0);
            connection.commit();
        }
        assertThat(receiptCount(ownerJdbc, scenario)).isEqualTo(1);
        DatabaseFingerprint beforeSparseRecovery = fingerprint(ownerJdbc);
        TagMigrationResult sparseRecovered = scenario.core().recover(
                scenario.recoveryCommand());
        assertBlocked(
                sparseRecovered,
                State.APPLYING,
                FailureCode.RECEIPT_MISMATCH);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeSparseRecovery);

        DatabaseFingerprint beforeSparseApply = fingerprint(ownerJdbc);
        TagMigrationResult sparseApply = scenario.core().apply(
                scenario.applyCommand());
        assertBlocked(
                sparseApply,
                State.BLOCKED,
                FailureCode.RECEIPT_MISMATCH);
        DatabaseFingerprint afterSparseApply = fingerprint(ownerJdbc);
        assertBusinessFactsUnchanged(beforeSparseApply, afterSparseApply);
        assertThat(afterSparseApply.receiptCount())
                .as("apply must not fill a sparse receipt gap")
                .isEqualTo(beforeSparseApply.receiptCount());
        assertThat(afterSparseApply.runCount())
                .isEqualTo(beforeSparseApply.runCount());
        assertThat(afterSparseApply.auditCount())
                .as("the only durable change is the fail-closed BLOCKED transition")
                .isEqualTo(beforeSparseApply.auditCount() + 1);
        assertDurablyBlocked(
                ownerJdbc, scenario, FailureCode.RECEIPT_MISMATCH);

        DatabaseFingerprint beforeSparseReplay = fingerprint(ownerJdbc);
        assertBlocked(
                scenario.core().apply(scenario.applyCommand()),
                State.BLOCKED,
                FailureCode.RECEIPT_MISMATCH);
        assertBlocked(
                scenario.core().recover(scenario.recoveryCommand()),
                State.BLOCKED,
                FailureCode.RECEIPT_MISMATCH);
        assertThat(fingerprint(ownerJdbc))
                .as("blocked sparse receipt replay is exact zero DML")
                .isEqualTo(beforeSparseReplay);
    }

    private static void assertFinalCommitAcknowledgementRecovery(
            DataSource operator,
            JdbcClient ownerJdbc,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        PreparedScenario scenario = frozenScenario(
                operator, membership, expectedVersion);
        CommitDiscardingDataSource discardFinalCommit =
                new CommitDiscardingDataSource(
                        operator, scenario.sourceCount() + 3);
        LegacyPersonalBankTagMigrationOperatorCore ambiguousCore =
                new LegacyPersonalBankTagMigrationOperatorCore(
                        discardFinalCommit,
                        membership,
                        scenario.verifier());
        DatabaseFingerprint beforeApply = fingerprint(ownerJdbc);
        TagMigrationResult recovered = ambiguousCore.apply(
                scenario.applyCommand());
        assertThat(discardFinalCommit.discarded()).isTrue();
        assertThat(recovered.outcome())
                .isEqualTo(Outcome.ALREADY_APPLIED_ZERO_DML);
        assertThat(recovered.state()).isEqualTo(State.APPLIED);
        assertThat(recovered.failureCode()).isEmpty();
        assertThat(recovered.migratedCount()).isEqualTo(1);
        assertThat(recovered.targetAlreadyPresentCount()).isEqualTo(2);
        assertThat(recovered.emptyNoopCount()).isEqualTo(1);
        assertThat(receiptCount(ownerJdbc, scenario))
                .isEqualTo(scenario.sourceCount());
        assertThat(negativeTargetCount(ownerJdbc)).isEqualTo(3);
        DatabaseFingerprint afterApply = fingerprint(ownerJdbc);
        assertThat(afterApply.sourceFacts()).isEqualTo(beforeApply.sourceFacts());
        assertThat(afterApply.lastActiveFacts())
                .isEqualTo(beforeApply.lastActiveFacts());
        assertThat(afterApply.targetCount() - beforeApply.targetCount())
                .isEqualTo(3);
        assertThat(ownerJdbc.sql("""
                SELECT event_type
                FROM ti_migration.personal_bank_tag_audit
                WHERE migration_id = :migration_id
                  AND migration_run_uuid = :run_uuid
                ORDER BY audit_id
                """)
                .param("migration_id", scenario.migrationId())
                .param("run_uuid", scenario.runUuid())
                .query(String.class)
                .list())
                .containsExactly("PREPARED", "FROZEN", "APPLYING", "APPLIED");

        DatabaseFingerprint beforeReplay = fingerprint(ownerJdbc);
        for (FixedEvidenceVerifier mismatchedVerifier : List.of(
                new FixedEvidenceVerifier(
                        scenario.verifier().prepare.binding(), "-mismatch", ""),
                new FixedEvidenceVerifier(
                        scenario.verifier().prepare.binding(), "", "-mismatch"))) {
            LegacyPersonalBankTagMigrationOperatorCore mismatchedCore =
                    new LegacyPersonalBankTagMigrationOperatorCore(
                            operator, membership, mismatchedVerifier);
            assertBlocked(
                    mismatchedCore.apply(scenario.applyCommand()),
                    State.APPLIED,
                    FailureCode.EVIDENCE_REJECTED);
            assertBlocked(
                    mismatchedCore.recover(scenario.recoveryCommand()),
                    State.UNAVAILABLE,
                    FailureCode.RECEIPT_MISMATCH);
        }
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeReplay);
        assertThat(ownerJdbc.sql("""
                SELECT state || ':' || version::text
                FROM ti_migration.personal_bank_tag_run
                WHERE migration_id = :migration_id
                  AND migration_run_uuid = :run_uuid
                """)
                .param("migration_id", scenario.migrationId())
                .param("run_uuid", scenario.runUuid())
                .query(String.class)
                .single())
                .isEqualTo("APPLIED:3");
        assertThat(scenario.core().apply(scenario.applyCommand()).outcome())
                .isEqualTo(Outcome.ALREADY_APPLIED_ZERO_DML);
        assertThat(fingerprint(ownerJdbc)).isEqualTo(beforeReplay);
    }

    private static int receiptCount(
            JdbcClient ownerJdbc,
            PreparedScenario scenario
    ) {
        return ownerJdbc.sql("""
                SELECT count(*)
                FROM ti_migration.personal_bank_tag_receipt
                WHERE migration_id = :migration_id
                  AND migration_run_uuid = :run_uuid
                """)
                .param("migration_id", scenario.migrationId())
                .param("run_uuid", scenario.runUuid())
                .query(Integer.class)
                .single();
    }

    private static int negativeTargetCount(JdbcClient ownerJdbc) {
        return ownerJdbc.sql("""
                SELECT count(*)
                FROM public.user_question_tag_items
                WHERE user_id = 9810
                  AND scope = 'user_bank'
                  AND scope_id = 9810
                """).query(Integer.class).single();
    }

    private static void installNegativeFixture(JdbcClient ownerJdbc) {
        ownerJdbc.sql("""
                INSERT INTO public.users (
                    id, username, password_hash, is_locked, session_version,
                    has_password_set, email, last_active
                ) VALUES (
                    9810, 'phase4c-operator-negative', 'public-test-only-hash',
                    false, 1, true, 'phase4c-operator-negative@test.invalid',
                    TIMESTAMP '2026-07-18 09:10:00'
                )
                """).update();
        ownerJdbc.sql("""
                INSERT INTO public.user_question_banks (
                    id, user_id, name, status
                ) VALUES (9810, 9810, 'operator negative bank', 1)
                """).update();
        ownerJdbc.sql("""
                INSERT INTO public.user_bank_questions (
                    id, bank_id, user_id, type, content
                ) VALUES (
                    10810, 9810, 9810, 'single_choice',
                    'operator negative membership'
                )
                """).update();
        ownerJdbc.sql("""
                INSERT INTO public.user_progress (
                    id, user_id, p_key, data, created_at, updated_at
                ) VALUES (
                    9910, 9810, 'bank_9810_tags',
                    '{"tags":["commit-ack"],"question_tags":{"10810":["bound"]}}',
                    TIMESTAMP '2026-07-18 09:20:00',
                    TIMESTAMP '2026-07-18 09:20:00'
                )
                """).update();
    }

    private static void removeNegativeFixture(JdbcClient ownerJdbc) {
        ownerJdbc.sql("""
                DELETE FROM public.user_question_tag_items
                WHERE user_id = 9810
                  AND scope = 'user_bank'
                  AND scope_id = 9810
                """).update();
        ownerJdbc.sql("""
                DELETE FROM public.user_progress WHERE id = 9910
                """).update();
        ownerJdbc.sql("""
                DELETE FROM public.user_bank_questions WHERE id = 10810
                """).update();
        ownerJdbc.sql("""
                DELETE FROM public.user_question_banks WHERE id = 9810
                """).update();
        ownerJdbc.sql("""
                DELETE FROM public.users WHERE id = 9810
                """).update();
    }

    private static FreshPrepare freshPrepare(
            DataSource operator,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        LegacyPersonalBankTagPreflightReport report =
                new LegacyPersonalBankTagGlobalPreflight(
                        operator, membership).run();
        assertThat(report.fullSweepComplete()).isTrue();
        assertThat(report.blockingRowCount()).as(report.toString()).isZero();
        assertThat(report.isDataEligible()).isTrue();
        UUID migrationId = UUID.randomUUID();
        UUID runUuid = UUID.randomUUID();
        RunBinding binding = binding(
                operator, report, runUuid, expectedVersion);
        FixedEvidenceVerifier verifier = new FixedEvidenceVerifier(binding);
        LegacyPersonalBankTagMigrationOperatorCore core =
                new LegacyPersonalBankTagMigrationOperatorCore(
                        operator, membership, verifier);
        return new FreshPrepare(
                core,
                verifier,
                new PrepareCommand(
                        migrationId,
                        runUuid,
                        report,
                        OPAQUE_EVIDENCE));
    }

    private static PreparedScenario preparedScenario(
            DataSource operator,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        FreshPrepare fresh = freshPrepare(
                operator, membership, expectedVersion);
        TagMigrationResult prepared = fresh.core().prepare(fresh.command());
        assertThat(prepared.outcome()).isEqualTo(Outcome.PREPARED);
        return new PreparedScenario(
                fresh.core(),
                fresh.verifier(),
                fresh.command().migrationId(),
                fresh.command().migrationRunUuid(),
                prepared.sourceCount());
    }

    private static PreparedScenario frozenScenario(
            DataSource operator,
            DatabaseMembershipApi membership,
            String expectedVersion
    ) throws Exception {
        PreparedScenario scenario = preparedScenario(
                operator, membership, expectedVersion);
        TagMigrationResult frozen = scenario.core().freeze(
                scenario.freezeCommand());
        assertThat(frozen.outcome()).isEqualTo(Outcome.FROZEN);
        return scenario;
    }

    private static void assertBlocked(
            TagMigrationResult result,
            State expectedState,
            FailureCode expectedFailure
    ) {
        assertThat(result.outcome()).isEqualTo(Outcome.BLOCKED);
        assertThat(result.state()).isEqualTo(expectedState);
        assertThat(result.failureCode()).contains(expectedFailure);
    }

    private static RunBinding binding(
            DataSource operator,
            LegacyPersonalBankTagPreflightReport report,
            UUID runUuid,
            String expectedVersion
    ) throws Exception {
        JdbcTagMigrationStore store = new JdbcTagMigrationStore(operator);
        List<ManifestDigestRow> rows = new ArrayList<>();
        JdbcTagMigrationStore.DatabaseIdentityFacts identity;
        try (Connection connection = operator.getConnection()) {
            identity = store.readIdentity(connection);
            for (LegacyPersonalBankTagPreflightReport.SourceRow row : report.rows()) {
                SourceSnapshot source = store.readSource(
                                connection, row.sourceRowId())
                        .orElseThrow();
                ParseResult plan = LegacyPersonalBankTagPreflightParser
                        .parse(source.data());
                TargetSnapshot target = store.readTarget(
                        connection, row.userId(),
                        row.normalizedBankId().orElseThrow());
                List<TagRow> finalRows = Stream.concat(
                                target.rows().stream(), plan.rows().stream())
                        .distinct()
                        .sorted(Comparator.comparingInt(TagRow::questionId)
                                .thenComparing(TagRow::tag))
                        .toList();
                rows.add(new ManifestDigestRow(
                        row.sourceRowId(), row.userId(),
                        row.normalizedBankId().orElseThrow(),
                        row.sourceDigest(), row.planDigest().orElseThrow(),
                        target.operatorDigestSha256(),
                        TagMigrationDigests.targetFacts(finalRows),
                        row.membershipDigest().orElseThrow()));
            }
        }
        String backup = LegacyPersonalBankTagPreflightParser.sha256(
                "phase4c-nodec-backup\u0000" + expectedVersion);
        TargetIdentity targetIdentity = identity.bind(backup, runUuid);
        ManifestDigests digests = TagMigrationDigests.manifestDigests(rows);
        return new RunBinding(
                backup,
                targetIdentity.clusterDatabaseIdentitySha256(),
                targetIdentity.runIdentitySha256(),
                report.aggregateDigest(),
                digests.sourceSetDigestSha256(),
                digests.planSetDigestSha256(),
                digests.preapplyTargetSetDigestSha256(),
                digests.finalTargetSetDigestSha256(),
                digests.membershipSetDigestSha256());
    }

    private static DatabaseFingerprint fingerprint(JdbcClient jdbc) {
        return new DatabaseFingerprint(
                jdbc.sql("""
                        SELECT string_agg(
                            id::text || ':' || user_id::text || ':' || p_key || ':' || data,
                            '|' ORDER BY id)
                        FROM user_progress
                        """).query(String.class).single(),
                jdbc.sql("""
                        SELECT string_agg(
                            id::text || ':' || coalesce(last_active::text, 'NULL'),
                            '|' ORDER BY id)
                        FROM users
                        """).query(String.class).single(),
                jdbc.sql("""
                        SELECT coalesce(string_agg(
                            user_id::text || ':' || scope
                                || ':' || scope_id::text || ':'
                                || question_id::text || ':' || tag || ':'
                                || coalesce(created_at::text, 'NULL') || ':'
                                || coalesce(updated_at::text, 'NULL'),
                            '|' ORDER BY user_id, scope, scope_id,
                                question_id, tag), '')
                        FROM public.user_question_tag_items
                        """).query(String.class).single(),
                jdbc.sql("""
                        SELECT coalesce(string_agg(
                            object_kind || ':' || payload,
                            E'\\n' ORDER BY object_kind, payload), '')
                        FROM (
                            SELECT 'run'::text AS object_kind,
                                   row_to_json(run_value)::text AS payload
                            FROM ti_migration.personal_bank_tag_run AS run_value
                            UNION ALL
                            SELECT 'source', row_to_json(source_value)::text
                            FROM ti_migration.personal_bank_tag_run_source
                                AS source_value
                            UNION ALL
                            SELECT 'receipt', row_to_json(receipt_value)::text
                            FROM ti_migration.personal_bank_tag_receipt
                                AS receipt_value
                            UNION ALL
                            SELECT 'audit', row_to_json(audit_value)::text
                            FROM ti_migration.personal_bank_tag_audit AS audit_value
                        ) AS ledger_value
                        """).query(String.class).single(),
                jdbc.sql("SELECT count(*) FROM user_question_tag_items")
                        .query(Integer.class).single(),
                jdbc.sql("SELECT count(*) FROM ti_migration.personal_bank_tag_run")
                        .query(Integer.class).single(),
                jdbc.sql("SELECT count(*) FROM ti_migration.personal_bank_tag_receipt")
                        .query(Integer.class).single(),
                jdbc.sql("SELECT count(*) FROM ti_migration.personal_bank_tag_audit")
                        .query(Integer.class).single());
    }

    private record DatabaseFingerprint(
            String sourceFacts,
            String lastActiveFacts,
            String targetFacts,
            String ledgerFacts,
            int targetCount,
            int runCount,
            int receiptCount,
            int auditCount
    ) {
    }

    private record TimedResult(
            TagMigrationResult result,
            long elapsedMillis
    ) {
    }

    private record FreshPrepare(
            LegacyPersonalBankTagMigrationOperatorCore core,
            FixedEvidenceVerifier verifier,
            PrepareCommand command
    ) {
    }

    private record PreparedScenario(
            LegacyPersonalBankTagMigrationOperatorCore core,
            FixedEvidenceVerifier verifier,
            UUID migrationId,
            UUID runUuid,
            int sourceCount
    ) {
        private FreezeCommand freezeCommand() {
            return new FreezeCommand(
                    migrationId, runUuid, OPAQUE_EVIDENCE);
        }

        private ApplyCommand applyCommand() {
            return new ApplyCommand(
                    migrationId, runUuid, OPAQUE_EVIDENCE);
        }

        private RecoveryCommand recoveryCommand() {
            return new RecoveryCommand(
                    migrationId, runUuid, OPAQUE_EVIDENCE);
        }
    }

    private static final class FixedEvidenceVerifier implements EvidenceVerifier {
        private final VerifiedPrepareEvidence prepare;
        private final VerifiedFreezeEvidence freeze;
        private final VerifiedApplyEvidence apply;
        private final VerifiedRecoveryEvidence recovery;

        private FixedEvidenceVerifier(RunBinding binding) {
            this(binding, "", "", "", "", "");
        }

        private FixedEvidenceVerifier(
                RunBinding binding,
                String applyAuthorizationVariant,
                String legacyRuntimeVariant
        ) {
            this(
                    binding,
                    "", "", "",
                    applyAuthorizationVariant,
                    legacyRuntimeVariant);
        }

        private FixedEvidenceVerifier(
                RunBinding binding,
                String sourceWriterStopVariant,
                String targetWriterStopVariant,
                String membershipWriterStopVariant,
                String applyAuthorizationVariant,
                String legacyRuntimeVariant
        ) {
            this.prepare = new VerifiedPrepareEvidence(
                    binding, digest("prepare-evidence"));
            this.freeze = new VerifiedFreezeEvidence(
                    binding,
                    digest("source-writer-stop" + sourceWriterStopVariant),
                    digest("target-writer-stop" + targetWriterStopVariant),
                    digest("membership-writer-stop"
                            + membershipWriterStopVariant),
                    digest("connection-drain"),
                    digest("connection-rejection"), digest("restored-backup"));
            this.apply = new VerifiedApplyEvidence(
                    binding,
                    freeze.sourceWriterStopReceiptSha256(),
                    freeze.targetWriterStopReceiptSha256(),
                    freeze.membershipWriterStopReceiptSha256(),
                    freeze.connectionDrainReceiptSha256(),
                    freeze.connectionRejectionReceiptSha256(),
                    freeze.restoredBackupReceiptSha256(),
                    digest("apply-authorization" + applyAuthorizationVariant),
                    digest("legacy-runtime-disabled" + legacyRuntimeVariant));
            this.recovery = new VerifiedRecoveryEvidence(
                    binding,
                    freeze.sourceWriterStopReceiptSha256(),
                    freeze.targetWriterStopReceiptSha256(),
                    freeze.membershipWriterStopReceiptSha256(),
                    freeze.connectionDrainReceiptSha256(),
                    freeze.connectionRejectionReceiptSha256(),
                    freeze.restoredBackupReceiptSha256(),
                    apply.applyAuthorizationReceiptSha256(),
                    apply.legacyRuntimeDisabledReceiptSha256());
        }

        @Override
        public VerifiedPrepareEvidence verifyPrepare(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return prepare;
        }

        @Override
        public VerifiedFreezeEvidence verifyFreeze(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return freeze;
        }

        @Override
        public VerifiedApplyEvidence verifyApply(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return apply;
        }

        @Override
        public VerifiedRecoveryEvidence verifyRecovery(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            return recovery;
        }

        private static String digest(String label) {
            return LegacyPersonalBankTagPreflightParser.sha256(
                    "phase4c-nodec-evidence\u0000" + label);
        }
    }

    private static final class RejectingEvidenceVerifier
            implements EvidenceVerifier {
        @Override
        public VerifiedPrepareEvidence verifyPrepare(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            throw new EvidenceRejectedException();
        }

        @Override
        public VerifiedFreezeEvidence verifyFreeze(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            throw new EvidenceRejectedException();
        }

        @Override
        public VerifiedApplyEvidence verifyApply(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            throw new EvidenceRejectedException();
        }

        @Override
        public VerifiedRecoveryEvidence verifyRecovery(
                UUID migrationId,
                UUID migrationRunUuid,
                SignedEvidence signedEvidence
        ) throws EvidenceRejectedException {
            throw new EvidenceRejectedException();
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
                            SELECT 1 FROM user_question_banks WHERE id = ?
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
                            FROM user_bank_questions
                            WHERE bank_id = ? AND id = ANY (?::integer[])
                            ORDER BY id
                            """)) {
                        statement.setInt(1, bankId);
                        statement.setArray(2, connection.createArrayOf(
                                "integer", questionIds.toArray(Integer[]::new)));
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
                throw new IllegalStateException("test membership query failed", failure);
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

    private static final class CommitDiscardingDataSource implements DataSource {
        private final DataSource delegate;
        private final int discardCommitOrdinal;
        private final AtomicInteger commits = new AtomicInteger();
        private final AtomicBoolean discarded = new AtomicBoolean();

        private CommitDiscardingDataSource(
                DataSource delegate,
                int discardCommitOrdinal
        ) {
            this.delegate = delegate;
            this.discardCommitOrdinal = discardCommitOrdinal;
        }

        private boolean discarded() {
            return discarded.get();
        }

        @Override
        public Connection getConnection() throws SQLException {
            return proxy(delegate.getConnection());
        }

        @Override
        public Connection getConnection(String username, String password)
                throws SQLException {
            return proxy(delegate.getConnection(username, password));
        }

        private Connection proxy(Connection connection) {
            return (Connection) Proxy.newProxyInstance(
                    Connection.class.getClassLoader(),
                    new Class<?>[]{Connection.class},
                    (proxy, method, arguments) -> {
                        Object result;
                        try {
                            result = method.invoke(connection, arguments);
                        } catch (InvocationTargetException failure) {
                            throw failure.getCause();
                        }
                        if ("commit".equals(method.getName())
                                && method.getParameterCount() == 0
                                && commits.incrementAndGet()
                                        == discardCommitOrdinal
                                && discarded.compareAndSet(false, true)) {
                            throw new SQLException(
                                    "simulated discarded commit acknowledgement",
                                    "08006");
                        }
                        return result;
                    });
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
        public Logger getParentLogger()
                throws SQLFeatureNotSupportedException {
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

    private static final class SetRoleDataSource implements DataSource {
        private final DataSource delegate;
        private final String role;
        private final List<String> sessionStatements;

        private SetRoleDataSource(
                DataSource delegate,
                String role,
                String... sessionStatements
        ) {
            this.delegate = delegate;
            this.role = role;
            this.sessionStatements = List.of(sessionStatements);
        }

        @Override
        public Connection getConnection() throws SQLException {
            Connection connection = delegate.getConnection();
            try (Statement statement = connection.createStatement()) {
                statement.execute("SET ROLE " + role);
                for (String sessionStatement : sessionStatements) {
                    statement.execute(sessionStatement);
                }
                return connection;
            } catch (SQLException failure) {
                connection.close();
                throw failure;
            }
        }

        @Override
        public Connection getConnection(String username, String password)
                throws SQLException {
            throw new SQLFeatureNotSupportedException(
                    "Node C fixture has no operator credentials");
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
