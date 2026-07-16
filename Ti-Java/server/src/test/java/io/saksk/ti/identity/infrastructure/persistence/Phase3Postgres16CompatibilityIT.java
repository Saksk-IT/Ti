package io.saksk.ti.identity.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.identity.domain.LoginIdentifier;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import java.sql.Connection;
import java.sql.DriverManager;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

@Testcontainers
class Phase3Postgres16CompatibilityIT {

    private static final String VALID_WERKZEUG_TARGET_HASH =
            "scrypt:32768:8:1$y9957JKY7tK4WiY3$85d82f576fe5658f71e4199e483ce5383413efd0be6450cd982d615ec7f5ba316f18f4845999fbd5864c10fac367aaddce5cd9caab1a732a2f6b9d4f599f9341";

    @Container
    static final PostgreSQLContainer POSTGRES = Phase2PostgresContainers.compatibility16()
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                    "/docker-entrypoint-initdb.d/030-auth-schema.sql")
            .withCopyFileToContainer(
                    MountableFile.forClasspathResource("db/phase3/031-auth-seed.sql"),
                    "/docker-entrypoint-initdb.d/031-auth-seed.sql");

    @Test
    void phase3IdentityQueriesAndAtomicPasswordUpgradeRunOnPostgres16() throws Exception {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword());
        JdbcClient jdbc = JdbcClient.create(dataSource);
        JdbcIdentityCredentialStore credentials = new JdbcIdentityCredentialStore(jdbc);
        JdbcAuthoritativeIdentityStateStore authority = new JdbcAuthoritativeIdentityStateStore(jdbc);

        var email = LoginIdentifier.parse("phase3@example.test").orElseThrow();
        var candidates = credentials.findForAuthentication(email);
        assertThat(candidates).hasSize(1);
        var credential = candidates.getFirst();
        assertThat(credential.id()).isEqualTo(1);
        assertThat(credential.locked()).isFalse();
        assertThat(credential.summary().sessionVersion()).isEqualTo(7);
        assertThat(authority.findById(1).orElseThrow().acceptsLegacyJwtOpenid(
                "o-public-test-only-openid-0001")).isTrue();

        assertThat(credentials.replacePasswordHashAndMarkSet(
                1, credential.passwordHash(), 7, VALID_WERKZEUG_TARGET_HASH)).isTrue();
        assertThat(credentials.replacePasswordHashAndMarkSet(
                1, credential.passwordHash(), 7, VALID_WERKZEUG_TARGET_HASH)).isFalse();
        assertThat(credentials.confirmSuccessfulAuthentication(1, VALID_WERKZEUG_TARGET_HASH, 7))
                .contains(credential.summary());
        assertThat(jdbc.sql("SELECT password_hash FROM users WHERE id = 1")
                .query(String.class)
                .single()).isEqualTo(VALID_WERKZEUG_TARGET_HASH)
                .startsWith("scrypt:32768:8:1$")
                .doesNotContain("{scrypt@");
        assertThat(jdbc.sql("SELECT has_password_set FROM users WHERE id = 1")
                .query(Boolean.class)
                .single()).isTrue();

        assertThat(credentials.findForAuthentication(
                LoginIdentifier.parse("duplicate@example.test").orElseThrow())).hasSize(2);
        try (Connection connection = DriverManager.getConnection(
                POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword())) {
            assertThat(queryText(connection, "SHOW server_version")).isEqualTo("16.14");
        }
        assertThat(POSTGRES.getDockerImageName())
                .isEqualTo(Phase2ContainerImages.POSTGRES_16_COMPATIBILITY);
    }

    private static String queryText(Connection connection, String sql) throws Exception {
        try (var statement = connection.createStatement(); var result = statement.executeQuery(sql)) {
            assertThat(result.next()).isTrue();
            return result.getString(1);
        }
    }
}
