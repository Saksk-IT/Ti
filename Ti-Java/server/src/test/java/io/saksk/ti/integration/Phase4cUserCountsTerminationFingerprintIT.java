package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.TiApplication;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.support.Phase2PostgresContainers;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.ConnectionIdentity;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.DatabaseFingerprint;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.Endpoint;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.Execution;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.ExecutionSuccess;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.Family;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.FaultObservation;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.FaultPlan;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.PgVersion;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.RollbackObservation;
import io.saksk.ti.support.Phase4cUserCountsTerminationFingerprintSupport.TraceSnapshot;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Stream;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestFactory;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Independent PG16/PG18 completion evidence for the Phase 4C termination fingerprint gate. */
@Testcontainers
@ActiveProfiles("test")
@AutoConfigureMockMvc
@SpringBootTest(classes = TiApplication.class)
@Import({
        Phase4cUserCountsTerminationFingerprintIT.FixedTerminationClock.class,
        Phase4cUserCountsTerminationFingerprintIT.DualPostgresConfiguration.class
})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@org.junit.jupiter.api.parallel.Execution(ExecutionMode.SAME_THREAD)
class Phase4cUserCountsTerminationFingerprintIT {

    private static final String REDIS_PASSWORD = "phase4c-termination-fingerprint-redis";
    private static final String LEGACY_SECRET =
            "PUBLIC-TEST-ONLY-ti-legacy-secret-32-bytes-minimum";
    private static final byte[] LEGACY_SECRET_BYTES =
            LEGACY_SECRET.getBytes(StandardCharsets.UTF_8);
    private static final String RATE_NAMESPACE =
            "ti-java:learning:personal-bank-user-counts-termination-fingerprint";
    private static final Instant CAPTURED_NOW =
            Instant.ofEpochSecond(Instant.now().getEpochSecond());
    private static final Instant CREDENTIAL_EXPIRES_AT =
            CAPTURED_NOW.plus(Duration.ofHours(1));
    private static final long SHARED_NULL_EXPIRY_ID = 99_454L;
    private static final long REVOKED_ID = 100_451L;
    private static final long DENIED_ID = 100_452L;
    private static final int BANK_ID = 99_551;
    private static final Set<Family> BUSINESS_FAMILIES =
            Phase4cUserCountsTerminationFingerprintSupport.businessFamilies();

    @Container
    static final PostgreSQLContainer POSTGRES_16 = fixture(
            Phase2PostgresContainers.compatibility16());

    @Container
    static final PostgreSQLContainer POSTGRES_18 = fixture(
            Phase2PostgresContainers.reference18());

    @Container
    static final RedisContainer REDIS = new RedisContainer(Phase2ContainerImages.redis7())
            .withCommand(
                    "redis-server",
                    "--requirepass", REDIS_PASSWORD,
                    "--maxmemory", "128mb",
                    "--maxmemory-policy", "noeviction");

    @DynamicPropertySource
    static void infrastructureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES_18::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES_18::getUsername);
        registry.add("spring.datasource.password", POSTGRES_18::getPassword);
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "validate");
        registry.add("spring.jpa.generate-ddl", () -> "false");
        registry.add("spring.jpa.open-in-view", () -> "false");
        registry.add("spring.data.redis.host", REDIS::getRedisHost);
        registry.add("spring.data.redis.port", REDIS::getRedisPort);
        registry.add("spring.data.redis.password", () -> REDIS_PASSWORD);
        registry.add("spring.data.redis.repositories.enabled", () -> "false");
        registry.add("spring.session.data.redis.namespace",
                () -> "ti-java:phase4c:user-counts-termination-fingerprint-sessions");
        registry.add("ti.security.login-rate-limit.key-secret",
                () -> "phase4c-termination-login-rate-key-secret-0001");
        registry.add("ti.security.legacy-auth.enabled", () -> "true");
        registry.add("ti.security.legacy-auth.accept-until",
                () -> CAPTURED_NOW.plus(Duration.ofDays(1)).toString());
        registry.add("ti.security.legacy-auth.secret", () -> LEGACY_SECRET);
        registry.add("ti.security.personal-bank-user-counts-read-rate-limit.namespace",
                () -> RATE_NAMESPACE);
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-second",
                () -> "1000");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-hour",
                () -> "10000");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.requests-per-day",
                () -> "100000");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.multiplier",
                () -> "1");
        registry.add(
                "ti.security.personal-bank-user-counts-read-rate-limit.key-secret",
                () -> "phase4c-termination-user-counts-rate-key-secret-0001");
        registry.add("ti.security.personal-bank-user-counts-cors.allowed-origins",
                () -> "http://127.0.0.1:3000,https://servicewechat.com");
    }

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ObjectMapper json;

    @Autowired
    StringRedisTemplate redis;

    @Autowired
    Phase4cUserCountsTerminationFingerprintSupport sqlProbe;

    @TestFactory
    Stream<DynamicTest> provesTerminationFingerprintsOnPostgres16And18() {
        return Stream.of(PgVersion.PG16, PgVersion.PG18)
                .map(version -> DynamicTest.dynamicTest(
                        version.label() + "_termination_fingerprint",
                        () -> proveTerminationFingerprint(version)));
    }

    private void proveTerminationFingerprint(PgVersion version) throws Exception {
        sqlProbe.select(version);
        clearRedis();
        assertVersionIdentity(version);

        DatabaseFingerprint before = sqlProbe.fingerprint(version);
        assertThat(before.byTable()).hasSize(9);
        assertThat(sqlProbe.usersWithLastActive(version)).isZero();

        TraceSnapshot anonymous = trace(null, () -> {
            MvcResult api = request("/api/user/banks/api/99551/user-counts", null,
                    version, "anonymous-api");
            assertThat(api.getResponse().getStatus()).isEqualTo(401);
            assertThat(jsonBody(api).path("status").asString()).isEqualTo("unauthorized");

            MvcResult web = request("/user/banks/api/99551/user-counts", null,
                    version, "anonymous-web");
            assertThat(web.getResponse().getStatus()).isEqualTo(302);
            assertThat(web.getResponse().getHeader(HttpHeaders.LOCATION)).isEqualTo("/login");
        });
        assertThat(anonymous.executions())
                .as("anonymous pre-authentication terminations must not use JDBC")
                .isEmpty();

        TraceSnapshot authenticationTermination = trace(null, () -> {
            MvcResult result = request(
                    "/api/user/banks/api/99551/user-counts",
                    jwt(REVOKED_ID, 21),
                    version,
                    "revoked-authority");
            assertThat(result.getResponse().getStatus()).isEqualTo(401);
            assertThat(jsonBody(result).path("status").asString()).isEqualTo("unauthorized");
        });
        ConnectionIdentity authenticationIdentity =
                assertAuthenticationTermination(version, authenticationTermination);

        TraceSnapshot businessDenial = trace(null, () -> {
            MvcResult result = request(
                    "/api/user/banks/api/99551/user-counts",
                    jwt(DENIED_ID, 21),
                    version,
                    "business-denied");
            assertThat(result.getResponse().getStatus()).isEqualTo(403);
            JsonNode body = jsonBody(result);
            assertThat(body.path("status").asString()).isEqualTo("error");
            assertThat(body.path("message").asString()).isEqualTo("无权访问此题库");
        });
        ConnectionIdentity denialIdentity =
                assertBusinessDenial(version, businessDenial);
        assertThat(denialIdentity)
                .as("auth termination and business denial physical backend")
                .isEqualTo(authenticationIdentity);

        TraceSnapshot exceptionalRecovery = trace(
                new FaultPlan(Family.SHARE_ACCESS, 1),
                () -> {
                    MvcResult failed = request(
                            "/api/user/banks/api/99551/user-counts",
                            jwt(SHARED_NULL_EXPIRY_ID, 11),
                            version,
                            "share-fault");
                    assertThat(failed.getResponse().getStatus()).isEqualTo(500);
                    assertThat(failed.getResponse().getContentAsString())
                            .doesNotContain("missing_phase4c_termination_fingerprint_column")
                            .doesNotContain("42703")
                            .doesNotContain("25P02");

                    MvcResult recovered = request(
                            "/api/user/banks/api/99551/user-counts",
                            jwt(SHARED_NULL_EXPIRY_ID, 11),
                            version,
                            "share-recovered");
                    assertThat(recovered.getResponse().getStatus()).isEqualTo(200);
                    assertThat(jsonBody(recovered).path("status").asString())
                            .isEqualTo("success");
                });
        assertExceptionalRollbackAndReuse(
                version, authenticationIdentity, exceptionalRecovery);

        assertNoWrites(
                anonymous,
                authenticationTermination,
                businessDenial,
                exceptionalRecovery);
        assertThat(sqlProbe.usersWithLastActive(version)).isZero();
        assertThat(sqlProbe.fingerprint(version))
                .as("nine-table fingerprint on %s", version.label())
                .isEqualTo(before);
    }

    private void assertVersionIdentity(PgVersion version) {
        assertThat(sqlProbe.selectedVersion()).isEqualTo(version);
        assertThat(sqlProbe.serverVersion(version)).isEqualTo(version.serverVersion());
        if (version == PgVersion.PG16) {
            assertThat(POSTGRES_16.getDockerImageName())
                    .isEqualTo(Phase2ContainerImages.POSTGRES_16_COMPATIBILITY);
        } else {
            assertThat(POSTGRES_18.getDockerImageName())
                    .isEqualTo(Phase2ContainerImages.POSTGRES_18_REFERENCE);
        }
    }

    private static ConnectionIdentity assertAuthenticationTermination(
            PgVersion version,
            TraceSnapshot trace
    ) {
        assertThat(trace.version()).isEqualTo(version);
        assertThat(trace.executions())
                .extracting(Execution::family)
                .containsExactly(Family.AUTHORITY_USERS);
        Execution authority = trace.executions().getFirst();
        assertThat(authority.normalizedSql())
                .contains("select id, username, openid")
                .contains("from users")
                .contains("where id = ?");
        assertThat(authority.connectionReadOnly()).isFalse();
        assertThat(authority.serverTransactionReadOnly()).isFalse();
        assertThat(authority.autoCommit()).isTrue();
        assertThat(authority.connectionIdentity().version()).isEqualTo(version);
        assertThat(authority.connectionIdentity().postgresBackendPid()).isPositive();
        assertThat(trace.successes())
                .extracting(ExecutionSuccess::family)
                .containsExactly(Family.AUTHORITY_USERS);
        assertThat(trace.executions())
                .noneMatch(execution -> BUSINESS_FAMILIES.contains(execution.family()));
        return authority.connectionIdentity();
    }

    private static ConnectionIdentity assertBusinessDenial(
            PgVersion version,
            TraceSnapshot trace
    ) {
        assertThat(trace.version()).isEqualTo(version);
        assertThat(trace.executions())
                .extracting(Execution::family)
                .containsExactly(
                        Family.AUTHORITY_USERS,
                        Family.BANK_ACCESS,
                        Family.SHARE_ACCESS);
        assertThat(trace.executions())
                .anySatisfy(execution -> {
                    assertThat(execution.family()).isEqualTo(Family.BANK_ACCESS);
                    assertThat(execution.normalizedSql())
                            .contains("from user_question_banks requested_bank")
                            .contains("where requested_bank.id = ?");
                })
                .anySatisfy(execution -> {
                    assertThat(execution.family()).isEqualTo(Family.SHARE_ACCESS);
                    assertThat(execution.normalizedSql())
                            .contains("join bank_share_records bsr")
                            .contains("join bank_shares bs");
                });
        assertReadOnlyBusinessExecutions(trace);
        return soleIdentity(trace, BUSINESS_FAMILIES);
    }

    private static void assertExceptionalRollbackAndReuse(
            PgVersion version,
            ConnectionIdentity expectedIdentity,
            TraceSnapshot trace
    ) {
        assertThat(trace.version()).isEqualTo(version);
        assertThat(trace.faults()).singleElement().satisfies(fault -> {
            assertThat(fault.family()).isEqualTo(Family.SHARE_ACCESS);
            assertThat(fault.occurrence()).isEqualTo(1);
            assertThat(fault.initialSqlState()).isEqualTo("42703");
            assertThat(fault.poisonedSqlState()).isEqualTo("25P02");
            assertThat(fault.connectionReadOnly()).isTrue();
            assertThat(fault.serverTransactionReadOnly()).isTrue();
            assertThat(fault.connectionIdentity()).isEqualTo(expectedIdentity);
        });
        FaultObservation fault = trace.faults().getFirst();

        RollbackObservation rollback = trace.rollbacks().stream()
                .filter(observation -> observation.connectionIdentity()
                        .equals(fault.connectionIdentity()))
                .filter(observation -> observation.sequence() > fault.sequence())
                .findFirst()
                .orElseThrow(() -> new AssertionError(
                        "missing same-backend rollback after PostgreSQL abort"));

        assertThat(trace.executions())
                .filteredOn(execution -> execution.family() == Family.AUTHORITY_USERS)
                .anySatisfy(execution -> {
                    assertThat(execution.sequence()).isGreaterThan(rollback.sequence());
                    assertThat(execution.connectionIdentity())
                            .isEqualTo(fault.connectionIdentity());
                    assertThat(execution.connectionReadOnly()).isFalse();
                    assertThat(execution.serverTransactionReadOnly()).isFalse();
                    assertThat(execution.autoCommit()).isTrue();
                });

        ExecutionSuccess reusableSuccess = trace.successes().stream()
                .filter(success -> success.family() == Family.SHARE_ACCESS)
                .filter(success -> success.occurrence() > fault.occurrence())
                .filter(success -> success.sequence() > rollback.sequence())
                .filter(success -> success.connectionIdentity()
                        .equals(fault.connectionIdentity()))
                .findFirst()
                .orElseThrow(() -> new AssertionError(
                        "missing successful same-backend business SQL after rollback"));
        assertThat(reusableSuccess.connectionIdentity()).isEqualTo(expectedIdentity);
        assertThat(trace.successes())
                .noneMatch(success -> success.family() == fault.family()
                        && success.occurrence() == fault.occurrence());
        assertReadOnlyBusinessExecutions(trace);
    }

    private static void assertReadOnlyBusinessExecutions(TraceSnapshot trace) {
        List<Execution> business = trace.executions().stream()
                .filter(execution -> BUSINESS_FAMILIES.contains(execution.family()))
                .toList();
        assertThat(business).isNotEmpty().allSatisfy(execution -> {
            assertThat(execution.connectionReadOnly()).isTrue();
            assertThat(execution.serverTransactionReadOnly()).isTrue();
            assertThat(execution.autoCommit()).isFalse();
        });
    }

    private static ConnectionIdentity soleIdentity(
            TraceSnapshot trace,
            Set<Family> families
    ) {
        List<ConnectionIdentity> identities = trace.executions().stream()
                .filter(execution -> families.contains(execution.family()))
                .map(Execution::connectionIdentity)
                .distinct()
                .toList();
        assertThat(identities).singleElement();
        return identities.getFirst();
    }

    private static void assertNoWrites(TraceSnapshot... traces) {
        assertThat(traces).allSatisfy(trace -> {
            assertThat(trace.writeDmlCount()).isZero();
            assertThat(trace.usersLastActiveWriteDmlCount()).isZero();
            assertThat(trace.schemaMutationCount()).isZero();
            assertThat(trace.executions())
                    .noneMatch(execution -> execution.usersWriteDml()
                            || execution.lastActiveWriteDml());
        });
    }

    private MvcResult request(
            String path,
            String bearer,
            PgVersion version,
            String caseId
    ) throws Exception {
        var request = get(path)
                .header(HttpHeaders.ACCEPT, "application/json")
                .header("X-Request-ID", "phase4c-termination-"
                        + version.label() + "-" + caseId)
                .with(raw -> {
                    raw.setRemoteAddr(version == PgVersion.PG16
                            ? "198.18.16.14"
                            : "198.18.18.4");
                    return raw;
                });
        if (bearer != null) {
            request.header(HttpHeaders.AUTHORIZATION, "Bearer " + bearer);
        }
        return mockMvc.perform(request).andReturn();
    }

    private JsonNode jsonBody(MvcResult result) throws Exception {
        return json.readTree(result.getResponse().getContentAsByteArray());
    }

    private TraceSnapshot trace(FaultPlan faultPlan, CheckedRunnable action)
            throws Exception {
        sqlProbe.start(faultPlan);
        Holder<TraceSnapshot> holder = new Holder<>();
        try {
            action.run();
        } finally {
            holder.value = sqlProbe.stop();
        }
        return Objects.requireNonNull(holder.value, "termination fingerprint trace");
    }

    private void clearRedis() {
        Set<String> keys = redis.keys("*");
        if (keys != null && !keys.isEmpty()) {
            redis.delete(keys);
        }
    }

    private static String jwt(long identityId, int claimVersion) {
        String header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        String payload = "{\"user_id\":" + identityId
                + ",\"openid\":\"\",\"session_version\":" + claimVersion
                + ",\"exp\":" + CREDENTIAL_EXPIRES_AT.getEpochSecond()
                + ",\"iat\":" + CAPTURED_NOW.getEpochSecond()
                + ",\"jti\":\"" + String.format("%032x", identityId) + "\"}";
        String unsigned = base64Url(header) + "." + base64Url(payload);
        return unsigned + "." + encode(hmac(
                "HmacSHA256",
                LEGACY_SECRET_BYTES,
                unsigned.getBytes(StandardCharsets.US_ASCII)));
    }

    private static String base64Url(String value) {
        return encode(value.getBytes(StandardCharsets.UTF_8));
    }

    private static byte[] hmac(String algorithm, byte[] key, byte[] value) {
        try {
            Mac mac = Mac.getInstance(algorithm);
            mac.init(new SecretKeySpec(key, algorithm));
            return mac.doFinal(value);
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException(algorithm + " unavailable", exception);
        }
    }

    private static String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private static PostgreSQLContainer fixture(PostgreSQLContainer container) {
        return container
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource("db/phase3/030-auth-schema.sql"),
                        "/docker-entrypoint-initdb.d/030-auth-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/062-personal-bank-share-list-schema.sql"),
                        "/docker-entrypoint-initdb.d/062-personal-bank-share-list-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/065-personal-bank-usage-stats-schema.sql"),
                        "/docker-entrypoint-initdb.d/065-personal-bank-usage-stats-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4b/067-personal-bank-user-counts-schema.sql"),
                        "/docker-entrypoint-initdb.d/067-personal-bank-user-counts-schema.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/071-personal-bank-user-counts-golden-target-seed.sql"),
                        "/docker-entrypoint-initdb.d/071-personal-bank-user-counts-golden-target-seed.sql")
                .withCopyFileToContainer(
                        MountableFile.forClasspathResource(
                                "db/phase4c/073-personal-bank-user-counts-termination-fingerprint-seed.sql"),
                        "/docker-entrypoint-initdb.d/073-personal-bank-user-counts-termination-fingerprint-seed.sql");
    }

    @FunctionalInterface
    private interface CheckedRunnable {
        void run() throws Exception;
    }

    private static final class Holder<T> {
        private T value;
    }

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class FixedTerminationClock {

        @Bean
        @Primary
        Clock phase4cTerminationFingerprintClock() {
            return Clock.fixed(CAPTURED_NOW, ZoneOffset.UTC);
        }
    }

    @org.springframework.boot.test.context.TestConfiguration(proxyBeanMethods = false)
    static class DualPostgresConfiguration {

        @Bean(destroyMethod = "close")
        @Primary
        Phase4cUserCountsTerminationFingerprintSupport
                phase4cUserCountsTerminationFingerprintDataSource() {
            return new Phase4cUserCountsTerminationFingerprintSupport(
                    new Endpoint(
                            POSTGRES_16.getJdbcUrl(),
                            POSTGRES_16.getUsername(),
                            POSTGRES_16.getPassword()),
                    new Endpoint(
                            POSTGRES_18.getJdbcUrl(),
                            POSTGRES_18.getUsername(),
                            POSTGRES_18.getPassword()));
        }
    }
}
