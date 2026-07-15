package io.saksk.ti.support;

import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;

/** Factory for disposable databases; no fixed host port and no container reuse. */
public final class Phase2PostgresContainers {

    public static final String DATABASE = "ti_phase2_fixture";
    public static final String OWNER = "ti_phase2_fixture_owner";
    public static final String OWNER_PASSWORD = "phase2-ephemeral-owner";
    public static final String READ_ONLY_USER = "ti_phase2_read";
    public static final String READ_ONLY_PASSWORD = "phase2-ephemeral-readonly";

    private Phase2PostgresContainers() {
    }

    public static PostgreSQLContainer reference18() {
        return fixture(Phase2ContainerImages.postgres18());
    }

    public static PostgreSQLContainer compatibility16() {
        return fixture(Phase2ContainerImages.postgres16());
    }

    private static PostgreSQLContainer fixture(DockerImageName image) {
        PostgreSQLContainer container = new PostgreSQLContainer(image)
                .withDatabaseName(DATABASE)
                .withUsername(OWNER)
                .withPassword(OWNER_PASSWORD);
        container.withCopyFileToContainer(
                MountableFile.forClasspathResource("db/phase2/minimal-reference-schema.sql"),
                "/docker-entrypoint-initdb.d/010-minimal-reference-schema.sql");
        container.withCopyFileToContainer(
                MountableFile.forClasspathResource("db/phase2/020-test-readonly-role.sql"),
                "/docker-entrypoint-initdb.d/020-test-readonly-role.sql");
        return container;
    }
}
