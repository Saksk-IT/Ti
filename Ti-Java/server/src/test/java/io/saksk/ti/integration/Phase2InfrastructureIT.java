package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.TiApplication;
import io.saksk.ti.catalog.application.port.SubjectReadPort;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.support.ReferenceSchemaAssertions;
import java.sql.Connection;
import java.sql.DriverManager;
import java.time.LocalDateTime;
import jakarta.persistence.EntityManagerFactory;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
@ActiveProfiles("test")
@SpringBootTest(classes = TiApplication.class, webEnvironment = SpringBootTest.WebEnvironment.MOCK)
class Phase2InfrastructureIT {

    private static final String REDIS_PASSWORD = "phase2-ephemeral-redis";

    @Container
    static final PostgreSQLContainer POSTGRES = Phase2PostgresContainers.reference18();

    @Container
    static final RedisContainer REDIS = new RedisContainer(Phase2ContainerImages.redis7())
            .withCommand(
                    "redis-server",
                    "--requirepass", REDIS_PASSWORD,
                    "--maxmemory", "64mb",
                    "--maxmemory-policy", "allkeys-lru");

    @DynamicPropertySource
    static void infrastructureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> Phase2PostgresContainers.READ_ONLY_USER);
        registry.add("spring.datasource.password", () -> Phase2PostgresContainers.READ_ONLY_PASSWORD);
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "validate");
        registry.add("spring.jpa.generate-ddl", () -> "false");
        registry.add("spring.data.redis.host", REDIS::getRedisHost);
        registry.add("spring.data.redis.port", REDIS::getRedisPort);
        registry.add("spring.data.redis.password", () -> REDIS_PASSWORD);
    }

    @Autowired
    EntityManagerFactory entityManagerFactory;

    @Autowired
    StringRedisTemplate redis;

    @Autowired
    SubjectReadPort subjects;

    @Test
    void postgres18SchemaIsHibernateValidatedAndReadOnly() throws Exception {
        assertThat(entityManagerFactory.isOpen()).isTrue();
        assertThat(POSTGRES.getDockerImageName()).isEqualTo(Phase2ContainerImages.POSTGRES_18_REFERENCE);
        assertThat(POSTGRES.getMappedPort(PostgreSQLContainer.POSTGRESQL_PORT)).isPositive();

        try (Connection connection = DriverManager.getConnection(
                POSTGRES.getJdbcUrl(),
                Phase2PostgresContainers.READ_ONLY_USER,
                Phase2PostgresContainers.READ_ONLY_PASSWORD)) {
            assertThat(ReferenceSchemaAssertions.queryText(connection, "SHOW server_version"))
                    .isEqualTo("18.4");
            assertThat(ReferenceSchemaAssertions.queryText(connection, "SHOW server_version_num"))
                    .isEqualTo("180004");
            ReferenceSchemaAssertions.assertMinimalFixture(connection);
            ReferenceSchemaAssertions.assertReadOnlyRole(connection);
        }

        var subject = subjects.findById(1).orElseThrow();
        assertThat(subject.id()).isEqualTo(1);
        assertThat(subject.name()).isEqualTo("Phase 2 reference subject");
        assertThat(subject.description()).isEqualTo("Schema-only fixture; never a production baseline");
        assertThat(subject.locked()).isFalse();
        assertThat(subject.plazaBoardId()).isEqualTo(1);
        assertThat(subject.plazaFeatured()).isTrue();
        assertThat(subject.plazaFeaturedWeight()).isEqualTo(10);
        assertThat(subject.plazaFeaturedAt()).isEqualTo(LocalDateTime.of(2026, 7, 16, 0, 0));
        assertThat(subject.createdAt()).isNotNull();
        assertThat(subjects.findAllByName()).containsExactly(subject);
    }

    @Test
    void redisUsesARealRandomPortContainerAndRemainsRebuildable() {
        assertThat(REDIS.getDockerImageName()).isEqualTo(Phase2ContainerImages.REDIS_7);
        assertThat(REDIS.getRedisPort()).isPositive();
        assertThat(redis.getConnectionFactory()).isNotNull();
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            assertThat(connection.ping()).isEqualTo("PONG");
        }

        String key = "phase2:integration:ephemeral";
        redis.delete(key);
        redis.opsForValue().set(key, "rebuildable-cache");
        assertThat(redis.opsForValue().get(key)).isEqualTo("rebuildable-cache");
        assertThat(redis.delete(key)).isTrue();
        assertThat(redis.hasKey(key)).isFalse();
    }
}
