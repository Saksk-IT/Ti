package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.support.ReferenceSchemaAssertions;
import java.sql.Connection;
import java.sql.DriverManager;
import org.junit.jupiter.api.Test;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
class Postgres16CompatibilityIT {

    @Container
    static final PostgreSQLContainer POSTGRES = Phase2PostgresContainers.compatibility16();

    @Test
    void minimalReferenceSchemaAndReadOnlyRoleRemainCompatibleWithPostgres16() throws Exception {
        assertThat(POSTGRES.getDockerImageName()).isEqualTo(Phase2ContainerImages.POSTGRES_16_COMPATIBILITY);
        assertThat(POSTGRES.getMappedPort(PostgreSQLContainer.POSTGRESQL_PORT)).isPositive();

        try (Connection connection = DriverManager.getConnection(
                POSTGRES.getJdbcUrl(),
                Phase2PostgresContainers.READ_ONLY_USER,
                Phase2PostgresContainers.READ_ONLY_PASSWORD)) {
            assertThat(ReferenceSchemaAssertions.queryText(connection, "SHOW server_version"))
                    .isEqualTo("16.14");
            assertThat(ReferenceSchemaAssertions.queryText(connection, "SHOW server_version_num"))
                    .isEqualTo("160014");
            ReferenceSchemaAssertions.assertMinimalFixture(connection);
            ReferenceSchemaAssertions.assertReadOnlyRole(connection);
        }
    }
}
