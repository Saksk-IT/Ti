package io.saksk.ti.learning.infrastructure.migration;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.ManifestDigests;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.RawTargetFact;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationDigests.TargetIdentity;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.FailureCode;
import io.saksk.ti.learning.infrastructure.migration.TagMigrationResult.State;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.TreeSet;
import java.util.UUID;
import javax.sql.DataSource;

/** JDBC persistence boundary for the explicit tag migration operator. */
final class JdbcTagMigrationStore {

    private static final int FETCH_SIZE = 256;
    private static final int MAX_SOURCE_KEY_UTF8_BYTES = 256;
    private static final int MAX_TARGET_ROWS =
            LegacyPersonalBankTagPreflightParser.MAX_PLANNED_ROWS;
    private static final int MAX_TARGET_TAG_UTF8_BYTES =
            LegacyPersonalBankTagPreflightParser.MAX_TAG_CODE_POINTS * 4;
    private static final long ADVISORY_LOCK_KEY =
            LegacyPersonalBankTagGlobalPreflight.advisoryLockKey();

    static final String TRY_LOCK_SQL =
            "SELECT pg_catalog.pg_backend_pid(), pg_catalog.pg_try_advisory_lock(?)";
    static final String UNLOCK_SQL =
            "SELECT pg_catalog.pg_advisory_unlock(?)";
    static final String IDENTITY_SQL = """
            SELECT control.system_identifier::text,
                   database.oid::bigint,
                   pg_catalog.current_setting('server_version')::text,
                   COALESCE(pg_catalog.inet_server_addr()::text, 'local'),
                   COALESCE(pg_catalog.inet_server_port()::text, 'null')
            FROM pg_catalog.pg_control_system() AS control
            CROSS JOIN pg_catalog.pg_database AS database
            WHERE database.datname = pg_catalog.current_database()
            """;
    static final String RESERVED_SOURCE_IDS_SQL = """
            SELECT id
            FROM public.user_progress
            WHERE p_key LIKE 'bank_%_tags'
            ORDER BY id
            LIMIT ?
            """;
    static final String SOURCE_SQL = """
            SELECT id, user_id, p_key,
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
            WHERE id = ?
              AND pg_catalog.octet_length(
                  pg_catalog.convert_to(p_key, 'UTF8')) <= ?
            """;
    static final String TARGET_SQL = """
            SELECT question_id,
                   CASE
                       WHEN tag IS NULL
                            OR pg_catalog.octet_length(
                                pg_catalog.convert_to(tag, 'UTF8')) <= ?
                       THEN tag
                       ELSE NULL
                   END AS bounded_tag
            FROM public.user_question_tag_items
            WHERE user_id = ?
              AND scope = 'user_bank'
              AND scope_id = ?
            ORDER BY question_id, tag COLLATE "C"
            LIMIT ?
            """;
    static final String RUN_SQL = """
            SELECT migration_id, migration_run_uuid, state, version,
                   backup_manifest_sha256,
                   cluster_database_identity_sha256,
                   run_identity_sha256,
                   preflight_digest_sha256,
                   source_set_digest_sha256,
                   plan_set_digest_sha256,
                   preapply_target_set_digest_sha256,
                   final_target_set_digest_sha256,
                   membership_set_digest_sha256,
                   source_count,
                   migrated_count,
                   target_already_present_count,
                   empty_noop_count,
                   prepare_evidence_receipt_sha256,
                   source_writer_stop_receipt_sha256,
                   target_writer_stop_receipt_sha256,
                   membership_writer_stop_receipt_sha256,
                   connection_drain_receipt_sha256,
                   connection_rejection_receipt_sha256,
                   restored_backup_receipt_sha256,
                   apply_authorization_receipt_sha256,
                   legacy_runtime_disabled_receipt_sha256,
                   blocked_failure_code
            FROM ti_migration.personal_bank_tag_run
            WHERE migration_id = ? OR migration_run_uuid = ?
            """;
    static final String RUN_FOR_UPDATE_SQL = RUN_SQL + " FOR UPDATE";
    static final String MANIFEST_SQL = """
            SELECT source_row_id, user_id, bank_id,
                   key_digest_sha256, source_digest_sha256,
                   plan_digest_sha256, preflight_target_digest_sha256,
                   preapply_target_digest_sha256,
                   expected_target_digest_sha256, membership_digest_sha256,
                   disposition, definition_count, question_binding_count,
                   distinct_tag_count, plan_row_count,
                   preapply_target_row_count, expected_final_target_row_count
            FROM ti_migration.personal_bank_tag_run_source
            WHERE migration_id = ? AND migration_run_uuid = ?
            ORDER BY source_row_id
            """;
    static final String RECEIPT_SQL = """
            SELECT migration_id, migration_run_uuid, source_row_id,
                   backup_manifest_sha256,
                   cluster_database_identity_sha256,
                   run_identity_sha256,
                   preflight_digest_sha256,
                   source_set_digest_sha256,
                   plan_set_digest_sha256,
                   preapply_target_set_digest_sha256,
                   final_target_set_digest_sha256,
                   membership_set_digest_sha256,
                   source_writer_stop_receipt_sha256,
                   target_writer_stop_receipt_sha256,
                   membership_writer_stop_receipt_sha256,
                   connection_drain_receipt_sha256,
                   connection_rejection_receipt_sha256,
                   restored_backup_receipt_sha256,
                   apply_authorization_receipt_sha256,
                   legacy_runtime_disabled_receipt_sha256,
                   disposition, key_digest_sha256,
                   source_digest_sha256, plan_digest_sha256,
                   expected_target_digest_sha256, membership_digest_sha256,
                   actual_target_digest_sha256, inserted_target_row_count
            FROM ti_migration.personal_bank_tag_receipt
            WHERE migration_id = ?
              AND migration_run_uuid = ?
              AND source_row_id = ?
            """;
    static final String RECEIPTS_SQL = """
            SELECT migration_id, migration_run_uuid, source_row_id,
                   backup_manifest_sha256,
                   cluster_database_identity_sha256,
                   run_identity_sha256,
                   preflight_digest_sha256,
                   source_set_digest_sha256,
                   plan_set_digest_sha256,
                   preapply_target_set_digest_sha256,
                   final_target_set_digest_sha256,
                   membership_set_digest_sha256,
                   source_writer_stop_receipt_sha256,
                   target_writer_stop_receipt_sha256,
                   membership_writer_stop_receipt_sha256,
                   connection_drain_receipt_sha256,
                   connection_rejection_receipt_sha256,
                   restored_backup_receipt_sha256,
                   apply_authorization_receipt_sha256,
                   legacy_runtime_disabled_receipt_sha256,
                   disposition, key_digest_sha256,
                   source_digest_sha256, plan_digest_sha256,
                   expected_target_digest_sha256, membership_digest_sha256,
                   actual_target_digest_sha256, inserted_target_row_count
            FROM ti_migration.personal_bank_tag_receipt
            WHERE migration_id = ? AND migration_run_uuid = ?
            ORDER BY source_row_id
            """;
    static final String INSERT_RUN_SQL = """
            INSERT INTO ti_migration.personal_bank_tag_run (
                migration_id, migration_run_uuid, state, version,
                backup_manifest_sha256,
                cluster_database_identity_sha256,
                run_identity_sha256,
                preflight_digest_sha256,
                source_set_digest_sha256,
                plan_set_digest_sha256,
                preapply_target_set_digest_sha256,
                final_target_set_digest_sha256,
                membership_set_digest_sha256,
                source_count,
                prepare_evidence_receipt_sha256
            ) VALUES (?, ?, 'PLANNED', 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """;
    static final String INSERT_MANIFEST_SQL = """
            INSERT INTO ti_migration.personal_bank_tag_run_source (
                migration_id, migration_run_uuid, source_row_id, user_id, bank_id,
                key_digest_sha256, source_digest_sha256,
                plan_digest_sha256, preflight_target_digest_sha256,
                preapply_target_digest_sha256,
                expected_target_digest_sha256, membership_digest_sha256,
                disposition, definition_count, question_binding_count,
                distinct_tag_count, plan_row_count,
                preapply_target_row_count, expected_final_target_row_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """;
    static final String INSERT_RECEIPT_SQL = """
            INSERT INTO ti_migration.personal_bank_tag_receipt (
                migration_id, migration_run_uuid, source_row_id, disposition,
                backup_manifest_sha256,
                cluster_database_identity_sha256,
                run_identity_sha256,
                preflight_digest_sha256,
                source_set_digest_sha256,
                plan_set_digest_sha256,
                preapply_target_set_digest_sha256,
                final_target_set_digest_sha256,
                membership_set_digest_sha256,
                source_writer_stop_receipt_sha256,
                target_writer_stop_receipt_sha256,
                membership_writer_stop_receipt_sha256,
                connection_drain_receipt_sha256,
                connection_rejection_receipt_sha256,
                restored_backup_receipt_sha256,
                apply_authorization_receipt_sha256,
                legacy_runtime_disabled_receipt_sha256,
                key_digest_sha256, source_digest_sha256, plan_digest_sha256,
                expected_target_digest_sha256, membership_digest_sha256,
                actual_target_digest_sha256, inserted_target_row_count
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """;
    static final String INSERT_TARGET_SQL = """
            INSERT INTO public.user_question_tag_items (
                user_id, scope, scope_id, question_id, tag
            ) VALUES (?, 'user_bank', ?, ?, ?)
            """;
    private static final String TRANSITION_MATCH_PREDICATE = """
            WHERE migration_id = ?
              AND migration_run_uuid = ?
              AND backup_manifest_sha256 = ?
              AND cluster_database_identity_sha256 = ?
              AND run_identity_sha256 = ?
              AND preflight_digest_sha256 = ?
              AND source_set_digest_sha256 = ?
              AND plan_set_digest_sha256 = ?
              AND preapply_target_set_digest_sha256 = ?
              AND final_target_set_digest_sha256 = ?
              AND membership_set_digest_sha256 = ?
              AND source_count = ?
              AND source_writer_stop_receipt_sha256 IS NOT DISTINCT FROM ?
              AND target_writer_stop_receipt_sha256 IS NOT DISTINCT FROM ?
              AND membership_writer_stop_receipt_sha256 IS NOT DISTINCT FROM ?
              AND connection_drain_receipt_sha256 IS NOT DISTINCT FROM ?
              AND connection_rejection_receipt_sha256 IS NOT DISTINCT FROM ?
              AND restored_backup_receipt_sha256 IS NOT DISTINCT FROM ?
              AND apply_authorization_receipt_sha256 IS NOT DISTINCT FROM ?
              AND legacy_runtime_disabled_receipt_sha256 IS NOT DISTINCT FROM ?
              AND state = ?
              AND version = ?
            """;
    static final String FREEZE_SQL = """
            UPDATE ti_migration.personal_bank_tag_run
            SET state = 'FROZEN', version = 1,
                source_writer_stop_receipt_sha256 = ?,
                target_writer_stop_receipt_sha256 = ?,
                membership_writer_stop_receipt_sha256 = ?,
                connection_drain_receipt_sha256 = ?,
                connection_rejection_receipt_sha256 = ?,
                restored_backup_receipt_sha256 = ?,
                updated_at = CURRENT_TIMESTAMP
            """ + TRANSITION_MATCH_PREDICATE;
    static final String MARK_APPLYING_SQL = """
            UPDATE ti_migration.personal_bank_tag_run
            SET state = 'APPLYING', version = 2,
                apply_authorization_receipt_sha256 = ?,
                legacy_runtime_disabled_receipt_sha256 = ?,
                updated_at = CURRENT_TIMESTAMP
            """ + TRANSITION_MATCH_PREDICATE;
    static final String FINALIZE_APPLIED_SQL = """
            UPDATE ti_migration.personal_bank_tag_run
            SET state = 'APPLIED', version = 3,
                migrated_count = ?, target_already_present_count = ?,
                empty_noop_count = ?, updated_at = CURRENT_TIMESTAMP
            """ + TRANSITION_MATCH_PREDICATE;
    static final String BLOCK_SQL = """
            UPDATE ti_migration.personal_bank_tag_run
            SET state = 'BLOCKED', version = version + 1,
                blocked_failure_code = ?, updated_at = CURRENT_TIMESTAMP
            """ + TRANSITION_MATCH_PREDICATE;
    private final DataSource dataSource;
    private final TagMigrationSchemaVerifier schemaVerifier;

    JdbcTagMigrationStore(DataSource dataSource) {
        this(dataSource, new TagMigrationSchemaVerifier());
    }

    JdbcTagMigrationStore(
            DataSource dataSource,
            TagMigrationSchemaVerifier schemaVerifier
    ) {
        this.dataSource = Objects.requireNonNull(dataSource, "dataSource");
        this.schemaVerifier = Objects.requireNonNull(
                schemaVerifier, "schemaVerifier");
    }

    OperatorSession openSession() throws SQLException,
            TagMigrationSchemaVerifier.SchemaVerificationException,
            LockBusyException {
        Connection connection = dataSource.getConnection();
        boolean lockAttempted = false;
        try {
            connection.setReadOnly(false);
            connection.setTransactionIsolation(
                    Connection.TRANSACTION_SERIALIZABLE);
            connection.setAutoCommit(false);
            BoundedSqlRetry.configureTransactionTimeouts(connection);
            schemaVerifier.verify(connection);
            DatabaseIdentityFacts identity = readIdentity(connection);
            connection.commit();
            connection.setAutoCommit(true);

            int backendProcessId;
            boolean acquired;
            lockAttempted = true;
            try (PreparedStatement statement = connection.prepareStatement(TRY_LOCK_SQL)) {
                statement.setLong(1, ADVISORY_LOCK_KEY);
                try (ResultSet row = statement.executeQuery()) {
                    if (!row.next()) {
                        throw new SQLException("operator lock query returned no row");
                    }
                    backendProcessId = row.getInt(1);
                    acquired = row.getBoolean(2);
                }
            }
            if (!acquired) {
                throw new LockBusyException();
            }
            OperatorSession session = new OperatorSession(
                    connection, backendProcessId, identity);
            return session;
        } catch (SQLException
                 | TagMigrationSchemaVerifier.SchemaVerificationException
                 | LockBusyException
                 | RuntimeException failure) {
            cleanupFailedOpen(connection, lockAttempted, failure);
            throw failure;
        } catch (Error fatal) {
            cleanupFailedOpen(connection, lockAttempted, fatal);
            throw fatal;
        }
    }

    ReadOnlyRecoverySession openRecoverySession() throws SQLException,
            TagMigrationSchemaVerifier.SchemaVerificationException {
        Connection connection = dataSource.getConnection();
        try {
            connection.setReadOnly(true);
            connection.setTransactionIsolation(
                    Connection.TRANSACTION_SERIALIZABLE);
            connection.setAutoCommit(false);
            BoundedSqlRetry.configureTransactionTimeouts(connection);
            schemaVerifier.verify(connection);
            DatabaseIdentityFacts identity = readIdentity(connection);
            return new ReadOnlyRecoverySession(connection, identity);
        } catch (SQLException
                 | TagMigrationSchemaVerifier.SchemaVerificationException
                 | RuntimeException failure) {
            try {
                if (!connection.getAutoCommit()) {
                    connection.rollback();
                }
            } catch (SQLException | RuntimeException rollbackFailure) {
                failure.addSuppressed(rollbackFailure);
            }
            try {
                connection.close();
            } catch (SQLException | RuntimeException closeFailure) {
                failure.addSuppressed(closeFailure);
            }
            throw failure;
        }
    }

    private static void cleanupFailedOpen(
            Connection connection,
            boolean lockAttempted,
            Throwable primary
    ) {
        if (lockAttempted) {
            try (PreparedStatement statement = connection.prepareStatement(UNLOCK_SQL)) {
                statement.setLong(1, ADVISORY_LOCK_KEY);
                try (ResultSet ignored = statement.executeQuery()) {
                    // Best effort: false means this session never acquired the lock.
                }
            } catch (SQLException | RuntimeException unlockFailure) {
                primary.addSuppressed(unlockFailure);
            }
        }
        try {
            if (!connection.getAutoCommit()) {
                connection.rollback();
            }
        } catch (SQLException | RuntimeException rollbackFailure) {
            primary.addSuppressed(rollbackFailure);
        }
        try {
            connection.close();
        } catch (SQLException | RuntimeException closeFailure) {
            primary.addSuppressed(closeFailure);
        }
    }

    void verifySchema(Connection connection)
            throws TagMigrationSchemaVerifier.SchemaVerificationException {
        schemaVerifier.verify(connection);
    }

    DatabaseIdentityFacts readIdentity(Connection connection) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(IDENTITY_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()) {
                throw new SQLException("operator identity query returned no row");
            }
            DatabaseIdentityFacts identity = new DatabaseIdentityFacts(
                    row.getString(1),
                    row.getLong(2),
                    row.getString(3),
                    row.getString(4),
                    row.getString(5));
            if (row.next()) {
                throw new SQLException("operator identity query returned multiple rows");
            }
            return identity;
        }
    }

    List<Long> readReservedSourceIds(Connection connection) throws SQLException {
        List<Long> ids = new ArrayList<>();
        try (PreparedStatement statement =
                     connection.prepareStatement(RESERVED_SOURCE_IDS_SQL)) {
            statement.setInt(
                    1, LegacyPersonalBankTagGlobalPreflight
                            .MAX_RESERVED_SOURCE_ROWS + 1);
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    ids.add(row.getLong(1));
                }
            }
        }
        return List.copyOf(ids);
    }

    Optional<SourceSnapshot> readSource(
            Connection connection,
            long sourceRowId
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(SOURCE_SQL)) {
            statement.setInt(
                    1, LegacyPersonalBankTagPreflightParser
                            .MAX_PAYLOAD_UTF8_BYTES);
            statement.setLong(2, sourceRowId);
            statement.setInt(3, MAX_SOURCE_KEY_UTF8_BYTES);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) {
                    return Optional.empty();
                }
                SourceSnapshot source = new SourceSnapshot(
                        row.getLong("id"),
                        row.getLong("user_id"),
                        row.getString("p_key"),
                        row.getString("bounded_data"),
                        row.getObject("data_utf8_bytes", Integer.class));
                if (row.next()) {
                    throw new SQLException("source identity is not unique");
                }
                return Optional.of(source);
            }
        }
    }

    TargetSnapshot readTarget(
            Connection connection,
            long userId,
            int bankId
    ) throws SQLException {
        List<RawTargetFact> raw = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(TARGET_SQL)) {
            statement.setInt(1, MAX_TARGET_TAG_UTF8_BYTES);
            statement.setLong(2, userId);
            statement.setInt(3, bankId);
            statement.setInt(4, MAX_TARGET_ROWS + 1);
            statement.setFetchSize(FETCH_SIZE);
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    raw.add(new RawTargetFact(
                            row.getObject("question_id", Integer.class),
                            row.getString("bounded_tag")));
                }
            }
        }
        List<TagRow> canonical = new ArrayList<>(raw.size());
        boolean valid = raw.size() <= MAX_TARGET_ROWS;
        for (RawTargetFact fact : raw) {
            if (fact.questionId() == null || fact.questionId() < 0
                    || !LegacyPersonalBankTagPreflightParser
                            .isCanonicalTargetTag(fact.tag())) {
                valid = false;
            } else {
                canonical.add(new TagRow(fact.questionId(), fact.tag()));
            }
        }
        canonical.sort(Comparator.comparingInt(TagRow::questionId)
                .thenComparing(TagRow::tag));
        return new TargetSnapshot(
                canonical,
                TagMigrationDigests.legacyPreflightTargetFacts(raw),
                valid ? TagMigrationDigests.targetFacts(canonical) : null,
                raw.size(),
                valid);
    }

    Optional<RunSnapshot> readRun(
            Connection connection,
            UUID migrationId,
            UUID migrationRunUuid,
            boolean forUpdate
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                forUpdate ? RUN_FOR_UPDATE_SQL : RUN_SQL)) {
            statement.setObject(1, migrationId);
            statement.setObject(2, migrationRunUuid);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) {
                    return Optional.empty();
                }
                RunSnapshot run = mapRun(row);
                if (row.next()) {
                    throw new SQLException("migration identity is not unique");
                }
                return Optional.of(run);
            }
        }
    }

    List<ManifestRow> readManifest(
            Connection connection,
            UUID migrationId,
            UUID migrationRunUuid
    ) throws SQLException {
        List<ManifestRow> rows = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(MANIFEST_SQL)) {
            statement.setObject(1, migrationId);
            statement.setObject(2, migrationRunUuid);
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    rows.add(new ManifestRow(
                            row.getLong(1), row.getLong(2), row.getInt(3),
                            row.getString(4), row.getString(5), row.getString(6),
                            row.getString(7), row.getString(8), row.getString(9),
                            row.getString(10),
                            Disposition.valueOf(row.getString(11)),
                            row.getInt(12), row.getInt(13), row.getInt(14),
                            row.getInt(15), row.getInt(16), row.getInt(17)));
                }
            }
        }
        return List.copyOf(rows);
    }

    Optional<ReceiptSnapshot> readReceipt(
            Connection connection,
            UUID migrationId,
            UUID migrationRunUuid,
            long sourceRowId
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(RECEIPT_SQL)) {
            statement.setObject(1, migrationId);
            statement.setObject(2, migrationRunUuid);
            statement.setLong(3, sourceRowId);
            try (ResultSet row = statement.executeQuery()) {
                return row.next() ? Optional.of(mapReceipt(row)) : Optional.empty();
            }
        }
    }

    List<ReceiptSnapshot> readReceipts(
            Connection connection,
            UUID migrationId,
            UUID migrationRunUuid
    ) throws SQLException {
        List<ReceiptSnapshot> receipts = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(RECEIPTS_SQL)) {
            statement.setObject(1, migrationId);
            statement.setObject(2, migrationRunUuid);
            try (ResultSet row = statement.executeQuery()) {
                while (row.next()) {
                    receipts.add(mapReceipt(row));
                }
            }
        }
        return List.copyOf(receipts);
    }

    void insertPreparedRun(
            Connection connection,
            RunManifest manifest,
            String prepareEvidenceReceiptSha256
    ) throws SQLException {
        TagMigrationDigests.requireSha256(
                prepareEvidenceReceiptSha256, "prepareEvidenceReceiptSha256");
        try (PreparedStatement statement = connection.prepareStatement(INSERT_RUN_SQL)) {
            int index = 1;
            statement.setObject(index++, manifest.migrationId());
            statement.setObject(index++, manifest.migrationRunUuid());
            statement.setString(index++, manifest.backupManifestSha256());
            statement.setString(index++, manifest.clusterDatabaseIdentitySha256());
            statement.setString(index++, manifest.runIdentitySha256());
            statement.setString(index++, manifest.preflightDigestSha256());
            statement.setString(index++, manifest.digests().sourceSetDigestSha256());
            statement.setString(index++, manifest.digests().planSetDigestSha256());
            statement.setString(
                    index++, manifest.digests().preapplyTargetSetDigestSha256());
            statement.setString(
                    index++, manifest.digests().finalTargetSetDigestSha256());
            statement.setString(index++, manifest.digests().membershipSetDigestSha256());
            statement.setInt(index++, manifest.rows().size());
            statement.setString(index, prepareEvidenceReceiptSha256);
            requireOne(statement.executeUpdate(), "insert run");
        }
        try (PreparedStatement statement =
                     connection.prepareStatement(INSERT_MANIFEST_SQL)) {
            for (ManifestRow row : manifest.rows()) {
                int index = 1;
                statement.setObject(index++, manifest.migrationId());
                statement.setObject(index++, manifest.migrationRunUuid());
                statement.setLong(index++, row.sourceRowId());
                statement.setLong(index++, row.userId());
                statement.setInt(index++, row.bankId());
                statement.setString(index++, row.keyDigestSha256());
                statement.setString(index++, row.sourceDigestSha256());
                statement.setString(index++, row.planDigestSha256());
                statement.setString(index++, row.preflightTargetDigestSha256());
                statement.setString(index++, row.preapplyTargetDigestSha256());
                statement.setString(index++, row.expectedTargetDigestSha256());
                statement.setString(index++, row.membershipDigestSha256());
                statement.setString(index++, row.disposition().name());
                statement.setInt(index++, row.definitionCount());
                statement.setInt(index++, row.questionBindingCount());
                statement.setInt(index++, row.distinctTagCount());
                statement.setInt(index++, row.planRowCount());
                statement.setInt(index++, row.preapplyTargetRowCount());
                statement.setInt(index, row.expectedFinalTargetRowCount());
                statement.addBatch();
            }
            int[] inserted = statement.executeBatch();
            if (inserted.length != manifest.rows().size()) {
                throw new SQLException("manifest batch count mismatch");
            }
            for (int count : inserted) {
                if (count != 1 && count != PreparedStatement.SUCCESS_NO_INFO) {
                    throw new SQLException("manifest insert did not affect one row");
                }
            }
        }
    }

    int freeze(
            Connection connection,
            RunSnapshot expected,
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256,
            String connectionDrainReceiptSha256,
            String connectionRejectionReceiptSha256,
            String restoredBackupReceiptSha256
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(FREEZE_SQL)) {
            int index = 1;
            statement.setString(index++, sourceWriterStopReceiptSha256);
            statement.setString(index++, targetWriterStopReceiptSha256);
            statement.setString(index++, membershipWriterStopReceiptSha256);
            statement.setString(index++, connectionDrainReceiptSha256);
            statement.setString(index++, connectionRejectionReceiptSha256);
            statement.setString(index++, restoredBackupReceiptSha256);
            index = bindExpectedRun(statement, index, expected);
            statement.setString(index++, State.PLANNED.name());
            statement.setInt(index, 0);
            int changed = statement.executeUpdate();
            return changed;
        }
    }

    int markApplying(
            Connection connection,
            RunSnapshot expected,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256
    ) throws SQLException {
        try (PreparedStatement statement =
                     connection.prepareStatement(MARK_APPLYING_SQL)) {
            int index = 1;
            statement.setString(index++, applyAuthorizationReceiptSha256);
            statement.setString(index++, legacyRuntimeDisabledReceiptSha256);
            index = bindExpectedRun(statement, index, expected);
            statement.setString(index++, State.FROZEN.name());
            statement.setInt(index, 1);
            int changed = statement.executeUpdate();
            return changed;
        }
    }

    int finalizeApplied(
            Connection connection,
            RunSnapshot expected,
            int migratedCount,
            int alreadyPresentCount,
            int emptyNoopCount
    ) throws SQLException {
        try (PreparedStatement statement =
                     connection.prepareStatement(FINALIZE_APPLIED_SQL)) {
            int index = 1;
            statement.setInt(index++, migratedCount);
            statement.setInt(index++, alreadyPresentCount);
            statement.setInt(index++, emptyNoopCount);
            index = bindExpectedRun(statement, index, expected);
            statement.setString(index++, State.APPLYING.name());
            statement.setInt(index, 2);
            int changed = statement.executeUpdate();
            return changed;
        }
    }

    int block(
            Connection connection,
            RunSnapshot expected,
            FailureCode failureCode
    ) throws SQLException {
        if (!failureCode.durableBlockEligible()) {
            throw new IllegalArgumentException(
                    "failure code cannot be persisted as BLOCKED");
        }
        if (expected.state() == State.APPLIED || expected.state() == State.BLOCKED) {
            return 0;
        }
        try (PreparedStatement statement = connection.prepareStatement(BLOCK_SQL)) {
            int index = 1;
            statement.setString(index++, failureCode.name());
            index = bindExpectedRun(statement, index, expected);
            statement.setString(index++, expected.state().name());
            statement.setInt(index, expected.version());
            int changed = statement.executeUpdate();
            return changed;
        }
    }

    void insertReceipt(
            Connection connection,
            RunSnapshot run,
            ManifestRow manifest,
            String actualTargetDigestSha256,
            int insertedTargetRowCount
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(
                INSERT_RECEIPT_SQL)) {
            int index = 1;
            statement.setObject(index++, run.migrationId());
            statement.setObject(index++, run.migrationRunUuid());
            statement.setLong(index++, manifest.sourceRowId());
            statement.setString(index++, manifest.disposition().name());
            statement.setString(index++, run.backupManifestSha256());
            statement.setString(index++, run.clusterDatabaseIdentitySha256());
            statement.setString(index++, run.runIdentitySha256());
            statement.setString(index++, run.preflightDigestSha256());
            statement.setString(
                    index++, run.digests().sourceSetDigestSha256());
            statement.setString(
                    index++, run.digests().planSetDigestSha256());
            statement.setString(
                    index++, run.digests().preapplyTargetSetDigestSha256());
            statement.setString(
                    index++, run.digests().finalTargetSetDigestSha256());
            statement.setString(
                    index++, run.digests().membershipSetDigestSha256());
            statement.setString(
                    index++, run.sourceWriterStopReceiptSha256().orElseThrow());
            statement.setString(
                    index++, run.targetWriterStopReceiptSha256().orElseThrow());
            statement.setString(
                    index++, run.membershipWriterStopReceiptSha256().orElseThrow());
            statement.setString(
                    index++, run.connectionDrainReceiptSha256().orElseThrow());
            statement.setString(
                    index++, run.connectionRejectionReceiptSha256().orElseThrow());
            statement.setString(
                    index++, run.restoredBackupReceiptSha256().orElseThrow());
            statement.setString(
                    index++, run.applyAuthorizationReceiptSha256().orElseThrow());
            statement.setString(
                    index++, run.legacyRuntimeDisabledReceiptSha256().orElseThrow());
            statement.setString(index++, manifest.keyDigestSha256());
            statement.setString(index++, manifest.sourceDigestSha256());
            statement.setString(index++, manifest.planDigestSha256());
            statement.setString(index++, manifest.expectedTargetDigestSha256());
            statement.setString(index++, manifest.membershipDigestSha256());
            statement.setString(index++, actualTargetDigestSha256);
            statement.setInt(index, insertedTargetRowCount);
            requireOne(statement.executeUpdate(), "insert receipt");
        }
    }

    void insertTargetRows(
            Connection connection,
            ManifestRow manifest,
            List<TagRow> rows
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(INSERT_TARGET_SQL)) {
            for (TagRow row : rows) {
                statement.setLong(1, manifest.userId());
                statement.setInt(2, manifest.bankId());
                statement.setInt(3, row.questionId());
                statement.setString(4, row.tag());
                statement.addBatch();
            }
            int[] inserted = statement.executeBatch();
            if (inserted.length != rows.size()) {
                throw new SQLException("target insert batch count mismatch");
            }
            for (int count : inserted) {
                if (count != 1 && count != PreparedStatement.SUCCESS_NO_INFO) {
                    throw new SQLException("target insert did not affect one row");
                }
            }
        }
    }

    private static RunSnapshot mapRun(ResultSet row) throws SQLException {
        return new RunSnapshot(
                row.getObject(1, UUID.class),
                row.getObject(2, UUID.class),
                State.valueOf(row.getString(3)),
                row.getInt(4),
                row.getString(5), row.getString(6), row.getString(7),
                row.getString(8),
                new ManifestDigests(
                        row.getString(9), row.getString(10), row.getString(11),
                        row.getString(12), row.getString(13)),
                row.getInt(14), row.getInt(15), row.getInt(16), row.getInt(17),
                row.getString(18),
                Optional.ofNullable(row.getString(19)),
                Optional.ofNullable(row.getString(20)),
                Optional.ofNullable(row.getString(21)),
                Optional.ofNullable(row.getString(22)),
                Optional.ofNullable(row.getString(23)),
                Optional.ofNullable(row.getString(24)),
                Optional.ofNullable(row.getString(25)),
                Optional.ofNullable(row.getString(26)),
                Optional.ofNullable(row.getString(27))
                        .map(FailureCode::valueOf));
    }

    private static ReceiptSnapshot mapReceipt(ResultSet row) throws SQLException {
        return new ReceiptSnapshot(
                row.getObject(1, UUID.class),
                row.getObject(2, UUID.class),
                row.getLong(3),
                row.getString(4), row.getString(5), row.getString(6),
                row.getString(7),
                new ManifestDigests(
                        row.getString(8), row.getString(9), row.getString(10),
                        row.getString(11), row.getString(12)),
                row.getString(13), row.getString(14), row.getString(15),
                row.getString(16), row.getString(17), row.getString(18),
                row.getString(19), row.getString(20),
                Disposition.valueOf(row.getString(21)),
                row.getString(22), row.getString(23), row.getString(24),
                row.getString(25), row.getString(26), row.getString(27),
                row.getInt(28));
    }

    private static int bindExpectedRun(
            PreparedStatement statement,
            int index,
            RunSnapshot expected
    ) throws SQLException {
        statement.setObject(index++, expected.migrationId());
        statement.setObject(index++, expected.migrationRunUuid());
        statement.setString(index++, expected.backupManifestSha256());
        statement.setString(index++, expected.clusterDatabaseIdentitySha256());
        statement.setString(index++, expected.runIdentitySha256());
        statement.setString(index++, expected.preflightDigestSha256());
        statement.setString(index++, expected.digests().sourceSetDigestSha256());
        statement.setString(index++, expected.digests().planSetDigestSha256());
        statement.setString(
                index++, expected.digests().preapplyTargetSetDigestSha256());
        statement.setString(
                index++, expected.digests().finalTargetSetDigestSha256());
        statement.setString(index++, expected.digests().membershipSetDigestSha256());
        statement.setInt(index++, expected.sourceCount());
        statement.setString(
                index++, expected.sourceWriterStopReceiptSha256().orElse(null));
        statement.setString(
                index++, expected.targetWriterStopReceiptSha256().orElse(null));
        statement.setString(
                index++, expected.membershipWriterStopReceiptSha256().orElse(null));
        statement.setString(
                index++, expected.connectionDrainReceiptSha256().orElse(null));
        statement.setString(
                index++, expected.connectionRejectionReceiptSha256().orElse(null));
        statement.setString(
                index++, expected.restoredBackupReceiptSha256().orElse(null));
        statement.setString(
                index++, expected.applyAuthorizationReceiptSha256().orElse(null));
        statement.setString(
                index++, expected.legacyRuntimeDisabledReceiptSha256().orElse(null));
        return index;
    }

    private static void requireOne(int count, String operation) throws SQLException {
        if (count != 1) {
            throw new SQLException(operation + " did not affect exactly one row");
        }
    }

    static List<String> statementSurface() {
        return List.of(
                TRY_LOCK_SQL, UNLOCK_SQL, IDENTITY_SQL, RESERVED_SOURCE_IDS_SQL,
                SOURCE_SQL, TARGET_SQL, RUN_SQL,
                RUN_FOR_UPDATE_SQL, MANIFEST_SQL, RECEIPT_SQL, RECEIPTS_SQL,
                INSERT_RUN_SQL, INSERT_MANIFEST_SQL, INSERT_RECEIPT_SQL,
                INSERT_TARGET_SQL, FREEZE_SQL, MARK_APPLYING_SQL,
                FINALIZE_APPLIED_SQL, BLOCK_SQL);
    }

    final class OperatorSession implements AutoCloseable {
        private final Connection connection;
        private final int backendProcessId;
        private final DatabaseIdentityFacts databaseIdentity;
        private boolean closed;

        private OperatorSession(
                Connection connection,
                int backendProcessId,
                DatabaseIdentityFacts databaseIdentity
        ) {
            this.connection = connection;
            this.backendProcessId = backendProcessId;
            this.databaseIdentity = databaseIdentity;
        }

        Connection connection() {
            return connection;
        }

        int backendProcessId() {
            return backendProcessId;
        }

        DatabaseIdentityFacts databaseIdentity() {
            return databaseIdentity;
        }

        @Override
        public void close() throws SQLException {
            if (closed) {
                return;
            }
            closed = true;
            Throwable failure = null;
            try (PreparedStatement statement = connection.prepareStatement(UNLOCK_SQL)) {
                statement.setLong(1, ADVISORY_LOCK_KEY);
                try (ResultSet row = statement.executeQuery()) {
                    if (!row.next() || !row.getBoolean(1)) {
                        failure = new SQLException("operator advisory unlock rejected");
                    }
                }
            } catch (SQLException | RuntimeException unlockFailure) {
                failure = unlockFailure;
            }
            try {
                connection.close();
            } catch (SQLException | RuntimeException closeFailure) {
                if (failure == null) {
                    failure = closeFailure;
                } else {
                    failure.addSuppressed(closeFailure);
                }
            }
            if (failure != null) {
                rethrowCleanupFailure(failure);
            }
        }
    }

    static final class ReadOnlyRecoverySession implements AutoCloseable {
        private final Connection connection;
        private final DatabaseIdentityFacts databaseIdentity;
        private boolean completed;
        private boolean closed;

        private ReadOnlyRecoverySession(
                Connection connection,
                DatabaseIdentityFacts databaseIdentity
        ) {
            this.connection = connection;
            this.databaseIdentity = databaseIdentity;
        }

        Connection connection() {
            return connection;
        }

        DatabaseIdentityFacts databaseIdentity() {
            return databaseIdentity;
        }

        void commit() throws SQLException {
            connection.commit();
            completed = true;
        }

        @Override
        public void close() throws SQLException {
            if (closed) {
                return;
            }
            closed = true;
            Throwable failure = null;
            if (!completed) {
                try {
                    connection.rollback();
                } catch (SQLException | RuntimeException rollbackFailure) {
                    failure = rollbackFailure;
                }
            }
            try {
                connection.close();
            } catch (SQLException | RuntimeException closeFailure) {
                if (failure == null) {
                    failure = closeFailure;
                } else {
                    failure.addSuppressed(closeFailure);
                }
            }
            if (failure != null) {
                rethrowCleanupFailure(failure);
            }
        }
    }

    private static void rethrowCleanupFailure(Throwable failure)
            throws SQLException {
        if (failure instanceof SQLException sqlFailure) {
            throw sqlFailure;
        }
        if (failure instanceof RuntimeException runtimeFailure) {
            throw runtimeFailure;
        }
        throw new SQLException("operator cleanup failed", failure);
    }

    record DatabaseIdentityFacts(
            String systemIdentifier,
            long databaseOid,
            String serverVersion,
            String serverAddress,
            String serverPort
    ) {
        DatabaseIdentityFacts {
            systemIdentifier = requireText(systemIdentifier, "systemIdentifier");
            serverVersion = requireText(serverVersion, "serverVersion");
            serverAddress = requireText(serverAddress, "serverAddress");
            serverPort = requireText(serverPort, "serverPort");
            if (databaseOid <= 0) {
                throw new IllegalArgumentException("invalid database identity facts");
            }
        }

        TargetIdentity bind(String backupManifestSha256, UUID migrationRunUuid) {
            return TagMigrationDigests.targetIdentity(
                    systemIdentifier, databaseOid, serverVersion,
                    serverAddress, serverPort,
                    backupManifestSha256, migrationRunUuid);
        }
    }

    record SourceSnapshot(
            long sourceRowId,
            long userId,
            String key,
            String data,
            Integer sourceUtf8Bytes
    ) {
        SourceSnapshot {
            if (sourceRowId <= 0 || userId <= 0) {
                throw new IllegalArgumentException("source identity must be positive");
            }
            key = Objects.requireNonNull(key, "key");
            if (sourceUtf8Bytes != null && sourceUtf8Bytes < 0) {
                throw new IllegalArgumentException("source byte count is negative");
            }
            if (data == null && sourceUtf8Bytes != null
                    && sourceUtf8Bytes
                            <= LegacyPersonalBankTagPreflightParser
                                    .MAX_PAYLOAD_UTF8_BYTES) {
                throw new IllegalArgumentException(
                        "bounded source is inconsistent");
            }
            if (data != null && (sourceUtf8Bytes == null
                    || sourceUtf8Bytes
                            != data.getBytes(StandardCharsets.UTF_8).length)) {
                throw new IllegalArgumentException("source byte count mismatch");
            }
        }

        boolean payloadTooLarge() {
            return data == null && sourceUtf8Bytes != null;
        }

        @Override
        public String toString() {
            return "SourceSnapshot[sourceRowId=" + sourceRowId
                    + ",userId=" + userId + ",redacted=true]";
        }
    }

    record TargetSnapshot(
            List<TagRow> rows,
            String legacyPreflightDigestSha256,
            String operatorDigestSha256,
            int rawRowCount,
            boolean structurallyValid
    ) {
        TargetSnapshot {
            rows = List.copyOf(Objects.requireNonNull(rows, "rows"));
            legacyPreflightDigestSha256 = TagMigrationDigests.requireSha256(
                    legacyPreflightDigestSha256,
                    "legacyPreflightDigestSha256");
            if (structurallyValid) {
                operatorDigestSha256 = TagMigrationDigests.requireSha256(
                        operatorDigestSha256, "operatorDigestSha256");
                if (rows.size() != rawRowCount) {
                    throw new IllegalArgumentException("valid target count mismatch");
                }
            } else if (operatorDigestSha256 != null) {
                throw new IllegalArgumentException("invalid target has an operator digest");
            }
            if (rawRowCount < 0 || rows.size() > rawRowCount) {
                throw new IllegalArgumentException("invalid target row count");
            }
        }

        List<Integer> positiveQuestionIds() {
            TreeSet<Integer> ids = new TreeSet<>();
            rows.stream().map(TagRow::questionId)
                    .filter(questionId -> questionId > 0).forEach(ids::add);
            return List.copyOf(ids);
        }
    }

    record RunManifest(
            UUID migrationId,
            UUID migrationRunUuid,
            String backupManifestSha256,
            String clusterDatabaseIdentitySha256,
            String runIdentitySha256,
            String preflightDigestSha256,
            ManifestDigests digests,
            List<ManifestRow> rows
    ) {
        RunManifest {
            migrationId = Objects.requireNonNull(migrationId, "migrationId");
            migrationRunUuid = Objects.requireNonNull(
                    migrationRunUuid, "migrationRunUuid");
            backupManifestSha256 = TagMigrationDigests.requireSha256(
                    backupManifestSha256, "backupManifestSha256");
            clusterDatabaseIdentitySha256 = TagMigrationDigests.requireSha256(
                    clusterDatabaseIdentitySha256,
                    "clusterDatabaseIdentitySha256");
            runIdentitySha256 = TagMigrationDigests.requireSha256(
                    runIdentitySha256, "runIdentitySha256");
            preflightDigestSha256 = TagMigrationDigests.requireSha256(
                    preflightDigestSha256, "preflightDigestSha256");
            digests = Objects.requireNonNull(digests, "digests");
            rows = List.copyOf(Objects.requireNonNull(rows, "rows")).stream()
                    .sorted(Comparator.comparingLong(ManifestRow::sourceRowId))
                    .toList();
            if (rows.isEmpty()) {
                throw new IllegalArgumentException("manifest must not be empty");
            }
        }
    }

    record ManifestRow(
            long sourceRowId,
            long userId,
            int bankId,
            String keyDigestSha256,
            String sourceDigestSha256,
            String planDigestSha256,
            String preflightTargetDigestSha256,
            String preapplyTargetDigestSha256,
            String expectedTargetDigestSha256,
            String membershipDigestSha256,
            Disposition disposition,
            int definitionCount,
            int questionBindingCount,
            int distinctTagCount,
            int planRowCount,
            int preapplyTargetRowCount,
            int expectedFinalTargetRowCount
    ) {
        ManifestRow {
            if (sourceRowId <= 0 || userId <= 0 || bankId <= 0) {
                throw new IllegalArgumentException("manifest identity must be positive");
            }
            keyDigestSha256 = TagMigrationDigests.requireSha256(
                    keyDigestSha256, "keyDigestSha256");
            sourceDigestSha256 = TagMigrationDigests.requireSha256(
                    sourceDigestSha256, "sourceDigestSha256");
            planDigestSha256 = TagMigrationDigests.requireSha256(
                    planDigestSha256, "planDigestSha256");
            preflightTargetDigestSha256 = TagMigrationDigests.requireSha256(
                    preflightTargetDigestSha256,
                    "preflightTargetDigestSha256");
            preapplyTargetDigestSha256 = TagMigrationDigests.requireSha256(
                    preapplyTargetDigestSha256,
                    "preapplyTargetDigestSha256");
            expectedTargetDigestSha256 = TagMigrationDigests.requireSha256(
                    expectedTargetDigestSha256,
                    "expectedTargetDigestSha256");
            membershipDigestSha256 = TagMigrationDigests.requireSha256(
                    membershipDigestSha256, "membershipDigestSha256");
            disposition = Objects.requireNonNull(disposition, "disposition");
            if (definitionCount < 0 || questionBindingCount < 0
                    || distinctTagCount < 0 || planRowCount < 0
                    || preapplyTargetRowCount < 0
                    || expectedFinalTargetRowCount < 0) {
                throw new IllegalArgumentException("manifest count is negative");
            }
        }
    }

    record RunSnapshot(
            UUID migrationId,
            UUID migrationRunUuid,
            State state,
            int version,
            String backupManifestSha256,
            String clusterDatabaseIdentitySha256,
            String runIdentitySha256,
            String preflightDigestSha256,
            ManifestDigests digests,
            int sourceCount,
            int migratedCount,
            int targetAlreadyPresentCount,
            int emptyNoopCount,
            String prepareEvidenceReceiptSha256,
            Optional<String> sourceWriterStopReceiptSha256,
            Optional<String> targetWriterStopReceiptSha256,
            Optional<String> membershipWriterStopReceiptSha256,
            Optional<String> connectionDrainReceiptSha256,
            Optional<String> connectionRejectionReceiptSha256,
            Optional<String> restoredBackupReceiptSha256,
            Optional<String> applyAuthorizationReceiptSha256,
            Optional<String> legacyRuntimeDisabledReceiptSha256,
            Optional<FailureCode> blockedFailureCode
    ) {
        RunSnapshot {
            migrationId = Objects.requireNonNull(migrationId, "migrationId");
            migrationRunUuid = Objects.requireNonNull(
                    migrationRunUuid, "migrationRunUuid");
            state = Objects.requireNonNull(state, "state");
            if (!state.acceptsVersion(version)) {
                throw new IllegalArgumentException("invalid stored state/version");
            }
            backupManifestSha256 = TagMigrationDigests.requireSha256(
                    backupManifestSha256, "backupManifestSha256");
            clusterDatabaseIdentitySha256 = TagMigrationDigests.requireSha256(
                    clusterDatabaseIdentitySha256,
                    "clusterDatabaseIdentitySha256");
            runIdentitySha256 = TagMigrationDigests.requireSha256(
                    runIdentitySha256, "runIdentitySha256");
            preflightDigestSha256 = TagMigrationDigests.requireSha256(
                    preflightDigestSha256, "preflightDigestSha256");
            digests = Objects.requireNonNull(digests, "digests");
            prepareEvidenceReceiptSha256 = TagMigrationDigests.requireSha256(
                    prepareEvidenceReceiptSha256,
                    "prepareEvidenceReceiptSha256");
            sourceWriterStopReceiptSha256 = requireOptionalSha(
                    sourceWriterStopReceiptSha256,
                    "sourceWriterStopReceiptSha256");
            targetWriterStopReceiptSha256 = requireOptionalSha(
                    targetWriterStopReceiptSha256,
                    "targetWriterStopReceiptSha256");
            membershipWriterStopReceiptSha256 = requireOptionalSha(
                    membershipWriterStopReceiptSha256,
                    "membershipWriterStopReceiptSha256");
            connectionDrainReceiptSha256 = requireOptionalSha(
                    connectionDrainReceiptSha256,
                    "connectionDrainReceiptSha256");
            connectionRejectionReceiptSha256 = requireOptionalSha(
                    connectionRejectionReceiptSha256,
                    "connectionRejectionReceiptSha256");
            restoredBackupReceiptSha256 = requireOptionalSha(
                    restoredBackupReceiptSha256,
                    "restoredBackupReceiptSha256");
            applyAuthorizationReceiptSha256 = requireOptionalSha(
                    applyAuthorizationReceiptSha256,
                    "applyAuthorizationReceiptSha256");
            legacyRuntimeDisabledReceiptSha256 = requireOptionalSha(
                    legacyRuntimeDisabledReceiptSha256,
                    "legacyRuntimeDisabledReceiptSha256");
            blockedFailureCode = Objects.requireNonNull(
                    blockedFailureCode, "blockedFailureCode");
            if ((state == State.BLOCKED) != blockedFailureCode.isPresent()
                    || blockedFailureCode.stream().anyMatch(
                            code -> !code.durableBlockEligible())) {
                throw new IllegalArgumentException(
                        "stored BLOCKED state/failure code is invalid");
            }
            if (sourceCount < 0 || migratedCount < 0
                    || targetAlreadyPresentCount < 0 || emptyNoopCount < 0) {
                throw new IllegalArgumentException("stored count is negative");
            }
        }

        boolean identityMatches(UUID expectedMigrationId, UUID expectedRunUuid) {
            return migrationId.equals(expectedMigrationId)
                    && migrationRunUuid.equals(expectedRunUuid);
        }
    }

    record ReceiptSnapshot(
            UUID migrationId,
            UUID migrationRunUuid,
            long sourceRowId,
            String backupManifestSha256,
            String clusterDatabaseIdentitySha256,
            String runIdentitySha256,
            String preflightDigestSha256,
            ManifestDigests digests,
            String sourceWriterStopReceiptSha256,
            String targetWriterStopReceiptSha256,
            String membershipWriterStopReceiptSha256,
            String connectionDrainReceiptSha256,
            String connectionRejectionReceiptSha256,
            String restoredBackupReceiptSha256,
            String applyAuthorizationReceiptSha256,
            String legacyRuntimeDisabledReceiptSha256,
            Disposition disposition,
            String keyDigestSha256,
            String sourceDigestSha256,
            String planDigestSha256,
            String expectedTargetDigestSha256,
            String membershipDigestSha256,
            String actualTargetDigestSha256,
            int insertedTargetRowCount
    ) {
        ReceiptSnapshot {
            migrationId = Objects.requireNonNull(migrationId, "migrationId");
            migrationRunUuid = Objects.requireNonNull(
                    migrationRunUuid, "migrationRunUuid");
            if (sourceRowId <= 0 || insertedTargetRowCount < 0) {
                throw new IllegalArgumentException("invalid receipt count");
            }
            backupManifestSha256 = TagMigrationDigests.requireSha256(
                    backupManifestSha256, "backupManifestSha256");
            clusterDatabaseIdentitySha256 = TagMigrationDigests.requireSha256(
                    clusterDatabaseIdentitySha256,
                    "clusterDatabaseIdentitySha256");
            runIdentitySha256 = TagMigrationDigests.requireSha256(
                    runIdentitySha256, "runIdentitySha256");
            preflightDigestSha256 = TagMigrationDigests.requireSha256(
                    preflightDigestSha256, "preflightDigestSha256");
            digests = Objects.requireNonNull(digests, "digests");
            sourceWriterStopReceiptSha256 = TagMigrationDigests.requireSha256(
                    sourceWriterStopReceiptSha256,
                    "sourceWriterStopReceiptSha256");
            targetWriterStopReceiptSha256 = TagMigrationDigests.requireSha256(
                    targetWriterStopReceiptSha256,
                    "targetWriterStopReceiptSha256");
            membershipWriterStopReceiptSha256 = TagMigrationDigests.requireSha256(
                    membershipWriterStopReceiptSha256,
                    "membershipWriterStopReceiptSha256");
            connectionDrainReceiptSha256 = TagMigrationDigests.requireSha256(
                    connectionDrainReceiptSha256,
                    "connectionDrainReceiptSha256");
            connectionRejectionReceiptSha256 = TagMigrationDigests.requireSha256(
                    connectionRejectionReceiptSha256,
                    "connectionRejectionReceiptSha256");
            restoredBackupReceiptSha256 = TagMigrationDigests.requireSha256(
                    restoredBackupReceiptSha256,
                    "restoredBackupReceiptSha256");
            applyAuthorizationReceiptSha256 = TagMigrationDigests.requireSha256(
                    applyAuthorizationReceiptSha256,
                    "applyAuthorizationReceiptSha256");
            legacyRuntimeDisabledReceiptSha256 = TagMigrationDigests.requireSha256(
                    legacyRuntimeDisabledReceiptSha256,
                    "legacyRuntimeDisabledReceiptSha256");
            disposition = Objects.requireNonNull(disposition, "disposition");
            keyDigestSha256 = TagMigrationDigests.requireSha256(
                    keyDigestSha256, "keyDigestSha256");
            sourceDigestSha256 = TagMigrationDigests.requireSha256(
                    sourceDigestSha256, "sourceDigestSha256");
            planDigestSha256 = TagMigrationDigests.requireSha256(
                    planDigestSha256, "planDigestSha256");
            expectedTargetDigestSha256 = TagMigrationDigests.requireSha256(
                    expectedTargetDigestSha256,
                    "expectedTargetDigestSha256");
            membershipDigestSha256 = TagMigrationDigests.requireSha256(
                    membershipDigestSha256, "membershipDigestSha256");
            actualTargetDigestSha256 = TagMigrationDigests.requireSha256(
                    actualTargetDigestSha256, "actualTargetDigestSha256");
        }

        boolean matches(RunSnapshot run, ManifestRow manifest) {
            return migrationId.equals(run.migrationId())
                    && migrationRunUuid.equals(run.migrationRunUuid())
                    && backupManifestSha256.equals(
                            run.backupManifestSha256())
                    && clusterDatabaseIdentitySha256.equals(
                            run.clusterDatabaseIdentitySha256())
                    && runIdentitySha256.equals(run.runIdentitySha256())
                    && preflightDigestSha256.equals(
                            run.preflightDigestSha256())
                    && digests.equals(run.digests())
                    && run.sourceWriterStopReceiptSha256().equals(
                            Optional.of(sourceWriterStopReceiptSha256))
                    && run.targetWriterStopReceiptSha256().equals(
                            Optional.of(targetWriterStopReceiptSha256))
                    && run.membershipWriterStopReceiptSha256().equals(
                            Optional.of(membershipWriterStopReceiptSha256))
                    && run.connectionDrainReceiptSha256().equals(
                            Optional.of(connectionDrainReceiptSha256))
                    && run.connectionRejectionReceiptSha256().equals(
                            Optional.of(connectionRejectionReceiptSha256))
                    && run.restoredBackupReceiptSha256().equals(
                            Optional.of(restoredBackupReceiptSha256))
                    && run.applyAuthorizationReceiptSha256().equals(
                            Optional.of(applyAuthorizationReceiptSha256))
                    && run.legacyRuntimeDisabledReceiptSha256().equals(
                            Optional.of(legacyRuntimeDisabledReceiptSha256))
                    && sourceRowId == manifest.sourceRowId()
                    && disposition == manifest.disposition()
                    && keyDigestSha256.equals(manifest.keyDigestSha256())
                    && sourceDigestSha256.equals(manifest.sourceDigestSha256())
                    && planDigestSha256.equals(manifest.planDigestSha256())
                    && expectedTargetDigestSha256.equals(
                            manifest.expectedTargetDigestSha256())
                    && membershipDigestSha256.equals(
                            manifest.membershipDigestSha256())
                    && actualTargetDigestSha256.equals(
                            manifest.expectedTargetDigestSha256())
                    && insertedTargetRowCount == manifest.disposition().insertedRows(
                            manifest.planRowCount());
        }
    }

    enum Disposition {
        MIGRATED,
        TARGET_ALREADY_PRESENT,
        EMPTY_NOOP;

        int insertedRows(int planRowCount) {
            return this == MIGRATED ? planRowCount : 0;
        }
    }

    static final class LockBusyException extends Exception {
        LockBusyException() {
            super("tag migration operator lock is busy");
        }
    }

    private static Optional<String> requireOptionalSha(
            Optional<String> value,
            String name
    ) {
        Optional<String> required = Objects.requireNonNull(value, name);
        required.ifPresent(digest -> TagMigrationDigests.requireSha256(digest, name));
        return required;
    }

    private static String requireText(String value, String name) {
        String required = Objects.requireNonNull(value, name);
        if (required.isBlank() || required.length() > 512) {
            throw new IllegalArgumentException(name + " must be bounded non-blank text");
        }
        return required;
    }
}
