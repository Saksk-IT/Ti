package io.saksk.ti.integration;

import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@Testcontainers
class Phase4cTransactionWriteReceiptMigrationIT {

    @Container
    static final PostgreSQLContainer POSTGRES_18 =
            Phase2PostgresContainers.reference18();

    @Container
    static final PostgreSQLContainer POSTGRES_16 =
            Phase2PostgresContainers.compatibility16();

    @Test
    void migrationAndConstraintsRunOnPostgres18() {
        assertMigration(
                POSTGRES_18,
                Phase2ContainerImages.POSTGRES_18_REFERENCE,
                "18.4");
    }

    @Test
    void migrationAndConstraintsRunOnPostgres16() {
        assertMigration(
                POSTGRES_16,
                Phase2ContainerImages.POSTGRES_16_COMPATIBILITY,
                "16.14");
    }

    private static void assertMigration(
            PostgreSQLContainer postgres,
            String expectedImage,
            String expectedVersion
    ) {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(),
                postgres.getUsername(),
                postgres.getPassword());
        Flyway flyway = Flyway.configure()
                .dataSource(dataSource)
                .locations("classpath:db/migration")
                .baselineOnMigrate(true)
                .baselineVersion("0")
                .validateMigrationNaming(true)
                .load();

        assertThat(flyway.migrate().migrationsExecuted).isEqualTo(1);
        assertThat(flyway.validateWithResult().validationSuccessful).isTrue();

        JdbcClient jdbc = JdbcClient.create(dataSource);
        assertThat(postgres.getDockerImageName()).isEqualTo(expectedImage);
        assertThat(jdbc.sql("SHOW server_version").query(String.class).single())
                .isEqualTo(expectedVersion);
        assertThat(tableCount(jdbc, "learning_idempotency_receipts")).isZero();
        assertThat(tableCount(jdbc, "catalog_question_edit_commands")).isZero();
        assertThat(indexExists(
                jdbc, "ix_learning_idempotency_receipts_expiry")).isTrue();
        assertThat(indexExists(
                jdbc, "ix_catalog_question_edit_commands_expiry")).isTrue();

        OffsetDateTime now = OffsetDateTime.of(
                2026, 7, 23, 12, 0, 0, 0, ZoneOffset.UTC);
        byte[] key = new byte[32];
        byte[] request = new byte[32];
        key[0] = 1;
        request[0] = 2;
        assertThat(jdbc.sql("""
                        INSERT INTO learning_idempotency_receipts (
                            actor_id, operation, key_hmac, request_sha256,
                            state, response_status, response_body,
                            completed_at, expires_at
                        ) VALUES (
                            :actor_id, :operation, :key_hmac, :request_sha256,
                            'COMPLETED', 200, CAST(:response_body AS jsonb),
                            :completed_at, :expires_at
                        )
                        """)
                .param("actor_id", 91_001L)
                .param("operation", "favorite")
                .param("key_hmac", key)
                .param("request_sha256", request)
                .param("response_body", "{\"status\":\"success\"}")
                .param("completed_at", now)
                .param("expires_at", now.plusSeconds(86_400))
                .update()).isEqualTo(1);
        assertThat(tableCount(jdbc, "learning_idempotency_receipts"))
                .isEqualTo(1);

        assertThatThrownBy(() -> jdbc.sql("""
                        INSERT INTO learning_idempotency_receipts (
                            actor_id, operation, key_hmac, request_sha256,
                            state, expires_at
                        ) VALUES (
                            91002, 'unknown', :key_hmac, :request_sha256,
                            'PENDING', :expires_at
                        )
                        """)
                .param("key_hmac", key)
                .param("request_sha256", request)
                .param("expires_at", now.plusSeconds(86_400))
                .update()).isInstanceOf(DataIntegrityViolationException.class);
        assertThatThrownBy(() -> jdbc.sql("""
                        INSERT INTO catalog_question_edit_commands (
                            actor_id, key_hmac, request_sha256, question_id,
                            state, expires_at
                        ) VALUES (
                            91002, :key_hmac, :request_sha256, 0,
                            'PENDING', :expires_at
                        )
                        """)
                .param("key_hmac", key)
                .param("request_sha256", request)
                .param("expires_at", now.plusSeconds(86_400))
                .update()).isInstanceOf(DataIntegrityViolationException.class);
    }

    private static long tableCount(JdbcClient jdbc, String table) {
        return jdbc.sql("SELECT COUNT(*) FROM " + table)
                .query(Long.class)
                .single();
    }

    private static boolean indexExists(JdbcClient jdbc, String index) {
        return jdbc.sql("""
                        SELECT EXISTS (
                            SELECT 1
                              FROM pg_indexes
                             WHERE schemaname = current_schema()
                               AND indexname = :index_name
                        )
                        """)
                .param("index_name", index)
                .query(Boolean.class)
                .single();
    }
}
