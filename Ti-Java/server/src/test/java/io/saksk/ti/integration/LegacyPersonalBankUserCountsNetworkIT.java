package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.redis.testcontainers.RedisContainer;
import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.identity.api.LegacyAuthenticationResult;
import io.saksk.ti.identity.api.LegacyCredentialAuthenticationApi;
import io.saksk.ti.identity.api.SessionAuthorityApi;
import io.saksk.ti.identity.api.SessionAuthorizationResult;
import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.support.Phase2ContainerImages;
import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.config.SecurityConfiguration;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.LegacySessionExchangeGuard;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Decision;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Window;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import io.saksk.ti.web.security.TargetSessionAuthenticationFilter;
import io.saksk.ti.web.security.TargetSessionAttributes;
import io.saksk.ti.web.security.TargetSessionIssuer;
import io.saksk.ti.web.security.TargetSessionRegistry;
import jakarta.servlet.Filter;
import jakarta.servlet.http.HttpServletRequest;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.data.jpa.autoconfigure.DataJpaRepositoriesAutoConfiguration;
import org.springframework.boot.data.redis.autoconfigure.DataRedisRepositoriesAutoConfiguration;
import org.springframework.boot.hibernate.autoconfigure.HibernateJpaAutoConfiguration;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.boot.security.autoconfigure.UserDetailsServiceAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;
import org.springframework.context.annotation.Import;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpHeaders;
import org.springframework.session.web.http.CookieSerializer;
import org.springframework.session.web.http.DefaultCookieSerializer;
import org.springframework.session.web.http.SessionRepositoryFilter;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Runs the user-counts compatibility entry through a real random-port Tomcat connector.
 *
 * <p>This deliberately does not use MockMvc: URI parsing, encoded-path rejection, the Spring
 * Security firewall, filter ordering, and the servlet container's HEAD handling are all part of
 * the evidence.</p>
 */
@SpringBootTest(
        classes = LegacyPersonalBankUserCountsNetworkIT.NetworkApplication.class,
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "management.endpoint.health.validate-group-membership=false")
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@Testcontainers
class LegacyPersonalBankUserCountsNetworkIT {

    private static final String API_PATH = "/api/user/banks/api/41/user-counts";
    private static final String WEB_PATH = "/user/banks/api/41/user-counts";
    private static final String TEST_BEARER = "network-user-counts-bearer";
    private static final String TARGET_SESSION_FIXTURE_HEADER = "X-Test-Target-Session";
    private static final String UNAVAILABLE_SESSION_FIXTURE = "authority-unavailable";
    private static final String ALLOWED_ORIGIN = "https://servicewechat.com";
    private static final String PAIR_REQUEST_ID = "phase4c-network-pair";
    private static final String REQUEST_ID_HEADER = "X-Request-ID";
    private static final String CLIENT_ADDRESS = "198.51.100.84";
    private static final String REDIS_PASSWORD = "phase4c-network-session-redis";
    private static final List<String> SEMANTIC_PARITY_HEADERS = List.of(
            HttpHeaders.LOCATION,
            HttpHeaders.VARY,
            HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN,
            REQUEST_ID_HEADER,
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy");
    private static final List<String> RATE_LIMIT_HEADERS = List.of(
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            HttpHeaders.RETRY_AFTER);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();
    private static final IdentitySummary IDENTITY = new IdentitySummary(
            4101L,
            "network-user-counts",
            false,
            false,
            false,
            7);
    private static final Decision ALLOWED = new Decision(
            true,
            Window.SECOND,
            10,
            9,
            1,
            1_784_260_801L);
    private static final Decision LIMITED = new Decision(
            false,
            Window.SECOND,
            10,
            0,
            1,
            1_784_260_801L);

    @Container
    static final RedisContainer REDIS = new RedisContainer(Phase2ContainerImages.redis7())
            .withCommand(
                    "redis-server",
                    "--requirepass", REDIS_PASSWORD,
                    "--maxmemory", "64mb",
                    "--maxmemory-policy", "noeviction");

    @DynamicPropertySource
    static void redisProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.data.redis.host", REDIS::getRedisHost);
        registry.add("spring.data.redis.port", REDIS::getRedisPort);
        registry.add("spring.data.redis.password", () -> REDIS_PASSWORD);
        registry.add("spring.data.redis.repositories.enabled", () -> "false");
        registry.add("spring.data.redis.connect-timeout", () -> "1s");
        registry.add("spring.data.redis.timeout", () -> "1s");
        registry.add(
                "spring.session.data.redis.namespace",
                () -> "ti-java:phase4c:user-counts-network-sessions");
    }

    @LocalServerPort
    int serverPort;

    @Autowired
    StringRedisTemplate redis;

    @MockitoBean
    LearningApplicationApi learning;

    @MockitoBean
    PersonalBankUserCountsReadRateLimiter rateLimiter;

    @MockitoBean
    ClientAddressResolver clientAddresses;

    @MockitoBean
    SessionAuthorityApi sessionAuthority;

    @MockitoBean
    LegacyCredentialAuthenticationApi legacyCredentials;

    @MockitoBean
    LegacySessionExchangeGuard legacySessionExchanges;

    @MockitoBean
    TargetSessionRegistry targetSessionRegistry;

    @MockitoBean
    TargetSessionIssuer targetSessionIssuer;

    @BeforeEach
    void allowAuthenticatedReadsByDefault() {
        try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
            connection.serverCommands().flushDb();
        }
        when(legacyCredentials.authenticateJwt(TEST_BEARER)).thenReturn(Optional.of(
                new LegacyAuthenticationResult(
                        IDENTITY,
                        false,
                        Optional.of(Instant.parse("2026-07-18T06:00:00Z")))));
        when(clientAddresses.resolve(any())).thenReturn(CLIENT_ADDRESS);
        when(rateLimiter.acquireForIdentity(any(), anyLong())).thenReturn(ALLOWED);
        when(rateLimiter.acquireForAddress(any(), anyString())).thenReturn(ALLOWED);
        when(learning.findPersonalBankUserCounts(any(), any()))
                .thenReturn(PersonalBankUserCountsResult.available(
                        new PersonalBankUserCountsView(
                                9,
                                5,
                                3,
                                List.of("选择题", "多选题"),
                true)));
    }

    @AfterEach
    void ensureRedisIsRunning() throws Exception {
        var inspection = REDIS.getDockerClient().inspectContainerCmd(REDIS.getContainerId()).exec();
        if (Boolean.TRUE.equals(inspection.getState().getPaused())) {
            REDIS.getDockerClient().unpauseContainerCmd(REDIS.getContainerId()).exec();
        }
        awaitRedisHost();
    }

    @Test
    void realNetworkKeepsGetAndHeadStatusParityFor200302401403404And500()
            throws Exception {
        ResponsePair allowedCors = exchangePair(
                API_PATH,
                true,
                Map.of(HttpHeaders.ORIGIN, ALLOWED_ORIGIN));
        assertPair(allowedCors, 200, true);
        assertThat(allowedCors.get().headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).contains(ALLOWED_ORIGIN);
        assertThat(allowedCors.head().headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).contains(ALLOWED_ORIGIN);
        assertGetAndHead(302, WEB_PATH, false, true);
        assertGetAndHead(401, API_PATH, false, true);
        assertGetAndHead(
                403,
                "/api/user/banks/api/0/user-counts",
                true,
                true);
        ResponsePair converterMiss = exchangePair(
                "/api/user/banks/api/not-a-bank/user-counts",
                false,
                Map.of(HttpHeaders.ORIGIN, ALLOWED_ORIGIN));
        assertPair(converterMiss, 404, true);
        assertThat(converterMiss.get().headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEmpty();
        assertThat(converterMiss.head().headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEmpty();
        assertNoRateHeaders(converterMiss.get());
        assertNoRateHeaders(converterMiss.head());

        ResponsePair rejectedCors = exchangePair(
                API_PATH,
                false,
                Map.of(HttpHeaders.ORIGIN, "https://evil.example"));
        assertPair(rejectedCors, 403, false);
        assertThat(rejectedCors.get().headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEmpty();
        assertThat(rejectedCors.head().headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEmpty();
        assertNoRateHeaders(rejectedCors.get());
        assertNoRateHeaders(rejectedCors.head());
        assertGetAndHead(
                500,
                "/api/user/banks/api/9223372036854775808/user-counts",
                true,
                true);

        verify(learning, times(2)).findPersonalBankUserCounts(any(), any());
    }

    @Test
    void webAliasWithValidBearerStillRedirectsAndConsumesOnlyTheIpBudget()
            throws Exception {
        ResponsePair response = exchangePair(WEB_PATH, true, Map.of());

        assertPair(response, 302, true);
        verify(legacyCredentials, never()).authenticateJwt(anyString());
        verify(rateLimiter, times(2)).acquireForAddress(Alias.WEB, CLIENT_ADDRESS);
        verify(rateLimiter, never()).acquireForIdentity(any(), anyLong());
        verifyNoInteractions(learning);
    }

    @Test
    void targetSessionAuthorityUnavailableIs503AndHeadRemainsBodyless()
            throws Exception {
        when(targetSessionRegistry.isActive(anyLong(), anyString())).thenReturn(true);
        when(sessionAuthority.authorize(IDENTITY.id(), IDENTITY.sessionVersion()))
                .thenReturn(SessionAuthorizationResult.unavailable());

        ResponsePair api = exchangePair(
                API_PATH,
                false,
                Map.of(TARGET_SESSION_FIXTURE_HEADER, UNAVAILABLE_SESSION_FIXTURE));
        ResponsePair web = exchangePair(
                WEB_PATH,
                false,
                Map.of(TARGET_SESSION_FIXTURE_HEADER, UNAVAILABLE_SESSION_FIXTURE));

        assertPair(api, 503, true);
        JsonNode apiBody = JSON.readTree(api.get().body());
        assertThat(apiBody.toString()).isEqualTo(
                "{\"status\":\"error\",\"message\":\"服务暂时不可用\","
                        + "\"status_code\":503,\"request_id\":\""
                        + PAIR_REQUEST_ID + "\"}");
        assertThat(api.get().headers().firstValue("Content-Type"))
                .contains("application/json");
        assertThat(api.get().headers().allValues("Vary"))
                .flatMap(value -> List.of(value.split(",\\s*")))
                .containsExactlyInAnyOrder("Origin", "Cookie");

        assertPair(web, 503, true);
        assertThat(new String(web.get().body(), java.nio.charset.StandardCharsets.UTF_8))
                .isEqualTo("<h1>503 - 服务不可用</h1><p>服务暂时不可用，请稍后再试。</p>");
        assertThat(web.get().headers().firstValue("Content-Type"))
                .contains("text/html;charset=utf-8");
        assertThat(web.get().headers().allValues("Vary"))
                .flatMap(value -> List.of(value.split(",\\s*")))
                .containsExactly("Cookie");

        verify(sessionAuthority, times(4))
                .authorize(IDENTITY.id(), IDENTITY.sessionVersion());
        verify(rateLimiter, never()).acquireForIdentity(any(), anyLong());
        verify(rateLimiter, never()).acquireForAddress(any(), anyString());
        verifyNoInteractions(learning);
    }

    @Test
    void realSpringSessionRedisOutageIsAliasSpecificAndRecoversOnTheSameService()
            throws Exception {
        when(targetSessionRegistry.isActive(anyLong(), anyString())).thenReturn(true);
        when(sessionAuthority.authorize(IDENTITY.id(), IDENTITY.sessionVersion()))
                .thenReturn(SessionAuthorizationResult.unavailable());
        HttpResponse<byte[]> primed = exchange(
                "GET",
                API_PATH,
                false,
                Map.of(TARGET_SESSION_FIXTURE_HEADER, UNAVAILABLE_SESSION_FIXTURE));
        assertThat(primed.statusCode()).isEqualTo(503);
        String targetCookie = primed.headers().firstValue(HttpHeaders.SET_COOKIE)
                .orElseThrow()
                .split(";", 2)[0];
        assertThat(targetCookie).startsWith("ti_dev_session=");

        REDIS.getDockerClient().pauseContainerCmd(REDIS.getContainerId()).exec();
        try {
            ResponsePair api = exchangePair(
                    API_PATH,
                    false,
                    Map.of(HttpHeaders.COOKIE, targetCookie));
            ResponsePair web = exchangePair(
                    WEB_PATH,
                    false,
                    Map.of(HttpHeaders.COOKIE, targetCookie));

            assertPair(api, 503, true);
            assertThat(JSON.readTree(api.get().body()).toString()).isEqualTo(
                    "{\"status\":\"error\",\"message\":\"服务暂时不可用\","
                            + "\"status_code\":503,"
                            + "\"request_id\":\"" + PAIR_REQUEST_ID + "\"}");
            assertPair(web, 503, true);
            assertThat(new String(web.get().body(), java.nio.charset.StandardCharsets.UTF_8))
                    .isEqualTo(
                            "<h1>503 - 服务不可用</h1><p>服务暂时不可用，请稍后再试。</p>");
            for (HttpResponse<byte[]> response : List.of(
                    api.get(), api.head(), web.get(), web.head())) {
                assertThat(response.headers().firstValue("X-RateLimit-Limit")).isEmpty();
            }
            verifyNoInteractions(rateLimiter, learning);
        } finally {
            REDIS.getDockerClient().unpauseContainerCmd(REDIS.getContainerId()).exec();
            awaitRedisHost();
        }

        when(sessionAuthority.authorize(IDENTITY.id(), IDENTITY.sessionVersion()))
                .thenReturn(SessionAuthorizationResult.authorized(IDENTITY));
        HttpResponse<byte[]> recovered = exchange(
                "GET",
                API_PATH,
                false,
                Map.of(
                        HttpHeaders.COOKIE, targetCookie,
                        REQUEST_ID_HEADER, "phase4c-network-session-recovered"));

        assertThat(recovered.statusCode()).isEqualTo(200);
        assertThat(JSON.readTree(recovered.body()).path("status").asString())
                .isEqualTo("success");
        assertThat(recovered.headers().firstValue(REQUEST_ID_HEADER))
                .contains("phase4c-network-session-recovered");
        assertThat(recovered.headers().firstValue("X-RateLimit-Limit")).contains("10");
        assertSecurityHeaders(recovered);
        verify(rateLimiter).acquireForIdentity(Alias.API, IDENTITY.id());
        verify(learning).findPersonalBankUserCounts(any(), any());
    }

    @Test
    void flaskSessionExchangeThrottleUsesTheDistinctAliasEnvelope() throws Exception {
        when(legacySessionExchanges.beginAttempt(CLIENT_ADDRESS))
                .thenReturn(new LegacySessionExchangeGuard.AttemptDecision(
                        false,
                        10,
                        0,
                        25));
        Map<String, String> cookie = Map.of(HttpHeaders.COOKIE, "session=legacy-network-cookie");

        ResponsePair api = exchangePair(API_PATH, false, cookie);
        ResponsePair web = exchangePair(WEB_PATH, false, cookie);

        assertPair(api, 429, true);
        assertThat(JSON.readTree(api.get().body()).path("message").asString())
                .isEqualTo("请求过于频繁");
        assertPair(web, 429, true);
        assertThat(new String(web.get().body(), java.nio.charset.StandardCharsets.UTF_8))
                .isEqualTo(
                        "<h1>429 - Too Many Requests</h1>"
                                + "<p>请求过于频繁，请稍后再试。</p>");
        for (HttpResponse<byte[]> response : List.of(
                api.get(), api.head(), web.get(), web.head())) {
            assertThat(response.headers().firstValue(HttpHeaders.RETRY_AFTER)).contains("25");
            assertThat(response.headers().firstValue("X-RateLimit-Limit")).contains("10");
            assertThat(response.headers().firstValue("X-RateLimit-Remaining")).contains("0");
            assertThat(response.headers().firstValue("X-RateLimit-Reset"))
                    .contains("1784347225");
        }
        verifyNoInteractions(rateLimiter, learning);
    }

    @Test
    void realNetworkKeeps429And503BodylessForHeadAndDoesNotReachLearning()
            throws Exception {
        when(rateLimiter.acquireForIdentity(any(), anyLong())).thenReturn(LIMITED);
        ResponsePair limited = exchangePair(API_PATH, true, Map.of());
        assertPair(limited, 429, true);
        assertThat(limited.get().headers().firstValue("X-RateLimit-Limit"))
                .contains("10");
        assertThat(limited.head().headers().firstValue("X-RateLimit-Limit"))
                .isEqualTo(limited.get().headers().firstValue("X-RateLimit-Limit"));

        when(rateLimiter.acquireForIdentity(any(), anyLong()))
                .thenThrow(new IllegalStateException("redis-network-secret-must-not-leak"));
        ResponsePair unavailable = exchangePair(API_PATH, true, Map.of());
        assertPair(unavailable, 503, true);
        assertThat(new String(unavailable.get().body(), java.nio.charset.StandardCharsets.UTF_8))
                .doesNotContain("redis-network-secret-must-not-leak");
        assertThat(unavailable.get().headers().firstValue("X-RateLimit-Limit")).isEmpty();
        assertThat(unavailable.head().headers().firstValue("X-RateLimit-Limit")).isEmpty();

        verify(learning, never()).findPersonalBankUserCounts(any(), any());
    }

    @Test
    void realTomcatAndFirewallRejectEncodedSlashAndSemicolonsBeforeRouteSideEffects()
            throws Exception {
        for (String path : List.of(
                "/api/user/banks/api/41%2F42/user-counts",
                "/api/user/banks/api/41;ignored/user-counts",
                "/api/user/banks/api/41%3Bignored/user-counts")) {
            assertGetAndHead(400, path, true, false);
        }

        verifyNoInteractions(rateLimiter, learning, legacyCredentials, sessionAuthority);
    }

    @Test
    void realNetworkOptionsTerminatesBeforeAuthenticationAndRateLimiting()
            throws Exception {
        HttpResponse<byte[]> apiBare = exchange("OPTIONS", API_PATH, false, Map.of());
        assertOptionsBase(apiBare, 204, "Origin", "Cookie");
        assertNoCorsResponseHeaders(apiBare);

        HttpResponse<byte[]> webBare = exchange("OPTIONS", WEB_PATH, false, Map.of());
        assertOptionsBase(webBare, 204, "Cookie");
        assertNoCorsResponseHeaders(webBare);

        HttpResponse<byte[]> preflight = exchange(
                "OPTIONS",
                API_PATH,
                false,
                Map.of(
                        HttpHeaders.ORIGIN, ALLOWED_ORIGIN,
                        HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "HEAD",
                        HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS,
                        "Authorization, X-Request-ID"));
        assertOptionsBase(
                preflight,
                204,
                "Origin",
                "Cookie",
                HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD,
                HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS);
        assertThat(preflight.headers().firstValue(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                .contains(ALLOWED_ORIGIN);
        assertThat(preflight.headers().firstValue(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS))
                .contains("GET, HEAD, OPTIONS");
        assertThat(preflight.headers().firstValue(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS))
                .contains("Authorization, X-Request-ID");

        HttpResponse<byte[]> rejectedPreflight = exchange(
                "OPTIONS",
                API_PATH,
                false,
                Map.of(
                        HttpHeaders.ORIGIN, "https://evil.example",
                        HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "GET"));
        assertOptionsBase(
                rejectedPreflight,
                403,
                "Origin",
                "Cookie",
                HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD,
                HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS);
        assertNoCorsResponseHeaders(rejectedPreflight);

        Map<String, List<String>> converterMisses = Map.of(
                "/api/user/banks/api/not-a-bank/user-counts",
                List.of("Origin", "Cookie"),
                "/user/banks/api/not-a-bank/user-counts",
                List.of("Cookie"));
        for (Map.Entry<String, List<String>> entry : converterMisses.entrySet()) {
            String path = entry.getKey();
            HttpResponse<byte[]> converterMiss = exchange("OPTIONS", path, false, Map.of());
            assertThat(converterMiss.statusCode()).isEqualTo(404);
            assertSecurityHeaders(converterMiss);
            assertVary(converterMiss, entry.getValue().toArray(String[]::new));
            assertThat(converterMiss.headers().firstValue(REQUEST_ID_HEADER))
                    .contains("phase4c-network-options");
            assertThat(converterMiss.headers().firstValue(HttpHeaders.ALLOW)).isEmpty();
            assertNoCorsResponseHeaders(converterMiss);
            assertNoRateHeaders(converterMiss);
            assertThat(converterMiss.headers().firstValue(HttpHeaders.SET_COOKIE)).isEmpty();
        }

        verifyNoInteractions(
                sessionAuthority,
                legacyCredentials,
                legacySessionExchanges,
                targetSessionRegistry,
                targetSessionIssuer,
                rateLimiter,
                clientAddresses,
                learning);
    }

    private void assertGetAndHead(
            int expectedStatus,
            String path,
            boolean authenticated,
            boolean getHasBody
    ) throws Exception {
        assertPair(exchangePair(path, authenticated, Map.of()), expectedStatus, getHasBody);
    }

    private void assertPair(
            ResponsePair pair,
            int expectedStatus,
            boolean getHasBody
    ) {
        assertThat(pair.get().statusCode()).isEqualTo(expectedStatus);
        assertThat(pair.head().statusCode()).isEqualTo(pair.get().statusCode());
        if (getHasBody) {
            assertThat(pair.get().body()).isNotEmpty();
        }
        assertThat(pair.head().body()).isEmpty();
        assertThat(pair.head().headers().firstValue("Content-Type"))
                .isEqualTo(pair.get().headers().firstValue("Content-Type"));
        for (String header : SEMANTIC_PARITY_HEADERS) {
            assertThat(pair.head().headers().allValues(header))
                    .as("HEAD %s must equal GET", header)
                    .isEqualTo(pair.get().headers().allValues(header));
        }
        for (String header : RATE_LIMIT_HEADERS) {
            List<String> getValues = pair.get().headers().allValues(header);
            if (getValues.isEmpty()) {
                assertThat(pair.head().headers().allValues(header))
                        .as("HEAD must not invent %s", header)
                        .isEmpty();
            } else {
                assertThat(pair.head().headers().allValues(header))
                        .as("HEAD %s must equal GET", header)
                        .isEqualTo(getValues);
            }
        }
        assertSetCookieSemantics(pair);
        if (expectedStatus == 400) {
            var getRequestId = pair.get().headers().firstValue(REQUEST_ID_HEADER);
            var headRequestId = pair.head().headers().firstValue(REQUEST_ID_HEADER);
            assertThat(headRequestId).isEqualTo(getRequestId);
            getRequestId.ifPresent(requestId -> assertThat(requestId)
                    .isEqualTo(PAIR_REQUEST_ID));
            assertNoSecurityHeaders(pair.get());
            assertNoSecurityHeaders(pair.head());
        } else {
            assertThat(pair.get().headers().firstValue(REQUEST_ID_HEADER))
                    .contains(PAIR_REQUEST_ID);
            assertThat(pair.head().headers().firstValue(REQUEST_ID_HEADER))
                    .contains(PAIR_REQUEST_ID);
            assertSecurityHeaders(pair.get());
            assertSecurityHeaders(pair.head());
        }
    }

    private static void assertSetCookieSemantics(ResponsePair pair) {
        List<CookieSemantics> getCookies = cookieSemantics(pair.get());
        List<CookieSemantics> headCookies = cookieSemantics(pair.head());
        if (getCookies.isEmpty() && headCookies.isEmpty()) {
            assertThat(headCookies)
                    .as("GET and HEAD explicitly expose the same empty Set-Cookie semantics")
                    .isEqualTo(getCookies);
            return;
        }
        assertThat(headCookies)
                .as("HEAD Set-Cookie semantics must equal GET while session ids may differ")
                .containsExactlyInAnyOrderElementsOf(getCookies);
    }

    private static List<CookieSemantics> cookieSemantics(HttpResponse<byte[]> response) {
        return response.headers().allValues(HttpHeaders.SET_COOKIE).stream()
                .map(CookieSemantics::parse)
                .toList();
    }

    private ResponsePair exchangePair(
            String path,
            boolean authenticated,
            Map<String, String> headers
    ) throws Exception {
        Map<String, String> pairHeaders = new LinkedHashMap<>(headers);
        pairHeaders.put(REQUEST_ID_HEADER, PAIR_REQUEST_ID);
        return new ResponsePair(
                exchange("GET", path, authenticated, pairHeaders),
                exchange("HEAD", path, authenticated, pairHeaders));
    }

    private HttpResponse<byte[]> exchange(
            String method,
            String path,
            boolean authenticated,
            Map<String, String> headers
    ) throws Exception {
        String requestId = headers.getOrDefault(
                REQUEST_ID_HEADER,
                "phase4c-network-" + method.toLowerCase());
        HttpRequest.Builder request = HttpRequest.newBuilder(
                        URI.create("http://127.0.0.1:" + serverPort + path))
                .timeout(Duration.ofSeconds(10))
                .header("Accept-Encoding", "identity")
                .header(REQUEST_ID_HEADER, requestId)
                .method(method, HttpRequest.BodyPublishers.noBody());
        if (authenticated) {
            request.header("Authorization", "Bearer " + TEST_BEARER);
        }
        headers.forEach((name, value) -> {
            if (!REQUEST_ID_HEADER.equalsIgnoreCase(name)) {
                request.header(name, value);
            }
        });
        return HTTP.send(request.build(), HttpResponse.BodyHandlers.ofByteArray());
    }

    private static void assertOptionsBase(
            HttpResponse<byte[]> response,
            int expectedStatus,
            String... expectedVary
    ) {
        assertThat(response.statusCode()).isEqualTo(expectedStatus);
        assertThat(response.body()).isEmpty();
        assertThat(response.headers().firstValue(HttpHeaders.ALLOW))
                .contains("GET, HEAD, OPTIONS");
        assertThat(response.headers().firstValue(REQUEST_ID_HEADER))
                .contains("phase4c-network-options");
        assertSecurityHeaders(response);
        assertVary(response, expectedVary);
        assertNoRateHeaders(response);
        assertThat(response.headers().firstValue(HttpHeaders.SET_COOKIE)).isEmpty();
        assertThat(response.headers().firstValue(
                HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS)).isEmpty();
        assertThat(response.headers().firstValue(HttpHeaders.ACCESS_CONTROL_MAX_AGE))
                .isEmpty();
    }

    private static void assertSecurityHeaders(HttpResponse<byte[]> response) {
        assertThat(response.headers().firstValue("X-Content-Type-Options"))
                .contains("nosniff");
        assertThat(response.headers().firstValue("X-Frame-Options"))
                .contains("SAMEORIGIN");
        assertThat(response.headers().firstValue("Referrer-Policy"))
                .contains("strict-origin-when-cross-origin");
    }

    private static void assertNoSecurityHeaders(HttpResponse<byte[]> response) {
        for (String header : List.of(
                "X-Content-Type-Options",
                "X-Frame-Options",
                "Referrer-Policy")) {
            assertThat(response.headers().firstValue(header)).isEmpty();
        }
    }

    private static void assertVary(
            HttpResponse<byte[]> response,
            String... expectedTokens
    ) {
        assertThat(response.headers().allValues(HttpHeaders.VARY))
                .flatMap(value -> List.of(value.split(",\\s*")))
                .containsExactlyInAnyOrder(expectedTokens);
    }

    private static void assertNoRateHeaders(HttpResponse<byte[]> response) {
        for (String header : RATE_LIMIT_HEADERS) {
            assertThat(response.headers().firstValue(header)).isEmpty();
        }
    }

    private static void assertNoCorsResponseHeaders(HttpResponse<byte[]> response) {
        for (String header : List.of(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN,
                HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS,
                HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS,
                HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS,
                HttpHeaders.ACCESS_CONTROL_MAX_AGE)) {
            assertThat(response.headers().firstValue(header)).isEmpty();
        }
    }

    private void awaitRedisHost() throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        RuntimeException lastFailure = null;
        while (System.nanoTime() < deadline) {
            try (RedisConnection connection = redis.getConnectionFactory().getConnection()) {
                if ("PONG".equals(connection.ping())) {
                    return;
                }
            } catch (RuntimeException failure) {
                lastFailure = failure;
            }
            Thread.sleep(100);
        }
        throw new IllegalStateException(
                "Session Redis did not recover on its published host port",
                lastFailure);
    }

    private record ResponsePair(
            HttpResponse<byte[]> get,
            HttpResponse<byte[]> head
    ) {
    }

    private record CookieSemantics(
            String name,
            String value,
            Optional<String> maxAge,
            Optional<String> path,
            Optional<String> domain,
            boolean httpOnly,
            boolean secure,
            Optional<String> sameSite,
            Optional<String> expires,
            Map<String, String> extensions
    ) {

        private static CookieSemantics parse(String header) {
            String[] segments = header.split(";", -1);
            int valueSeparator = segments[0].indexOf('=');
            if (valueSeparator <= 0) {
                throw new IllegalArgumentException("Invalid Set-Cookie name/value pair");
            }
            String name = segments[0].substring(0, valueSeparator).strip();
            String rawValue = segments[0].substring(valueSeparator + 1).strip();
            if (name.isEmpty()) {
                throw new IllegalArgumentException("Set-Cookie name must not be empty");
            }

            Map<String, String> attributes = new TreeMap<>();
            for (int index = 1; index < segments.length; index++) {
                String segment = segments[index].strip();
                if (segment.isEmpty()) {
                    continue;
                }
                int separator = segment.indexOf('=');
                String attributeName = (separator < 0
                                ? segment
                                : segment.substring(0, separator))
                        .strip()
                        .toLowerCase(Locale.ROOT);
                String attributeValue = separator < 0
                        ? ""
                        : segment.substring(separator + 1).strip();
                if (attributeName.isEmpty()
                        || attributes.putIfAbsent(attributeName, attributeValue) != null) {
                    throw new IllegalArgumentException(
                            "Invalid or duplicate Set-Cookie attribute");
                }
            }

            Optional<String> maxAge = optionalAttribute(attributes, "max-age")
                    .map(CookieSemantics::canonicalLong);
            Optional<String> expires = optionalAttribute(attributes, "expires")
                    .map(value -> maxAge.isPresent() ? "present-with-max-age" : value);
            Map<String, String> extensions = new TreeMap<>(attributes);
            for (String standard : List.of(
                    "max-age", "path", "domain", "httponly", "secure", "samesite", "expires")) {
                extensions.remove(standard);
            }
            return new CookieSemantics(
                    name,
                    normalizedCookieValue(name, rawValue),
                    maxAge,
                    optionalAttribute(attributes, "path"),
                    optionalAttribute(attributes, "domain")
                            .map(value -> value.startsWith(".") ? value.substring(1) : value)
                            .map(value -> value.toLowerCase(Locale.ROOT)),
                    attributes.containsKey("httponly"),
                    attributes.containsKey("secure"),
                    optionalAttribute(attributes, "samesite")
                            .map(value -> value.toLowerCase(Locale.ROOT)),
                    expires,
                    Map.copyOf(extensions));
        }

        private static Optional<String> optionalAttribute(
                Map<String, String> attributes,
                String name
        ) {
            return Optional.ofNullable(attributes.get(name));
        }

        private static String canonicalLong(String value) {
            try {
                return Long.toString(Long.parseLong(value));
            } catch (NumberFormatException exception) {
                throw new IllegalArgumentException("Invalid Set-Cookie Max-Age", exception);
            }
        }

        private static String normalizedCookieValue(String name, String value) {
            return name.equals("ti_dev_session") && !value.isEmpty()
                    ? "<dynamic-session-id>"
                    : value;
        }
    }

    @SpringBootConfiguration
    @EnableAutoConfiguration(exclude = {
            DataSourceAutoConfiguration.class,
            HibernateJpaAutoConfiguration.class,
            DataJpaRepositoriesAutoConfiguration.class,
            DataRedisRepositoriesAutoConfiguration.class,
            UserDetailsServiceAutoConfiguration.class
    })
    @ComponentScan(
            basePackages = "io.saksk.ti.web.compat",
            useDefaultFilters = false,
            includeFilters = @ComponentScan.Filter(
                    type = FilterType.REGEX,
                    pattern = "io\\.saksk\\.ti\\.web\\.compat\\."
                            + "LegacyPersonalBankUserCountsController"))
    @Import({
            SecurityConfiguration.class,
            SafeSecurityErrorWriter.class,
            LegacyPersonalBankUserCountsSecurityErrorWriter.class,
            PersonalBankUserCountsReadRequestResolver.class,
            TargetSessionAuthenticationFilter.class,
            RequestIdFilter.class
    })
    static class NetworkApplication {

        @Bean
        Clock fixedNetworkClock() {
            return Clock.fixed(
                    Instant.parse("2026-07-18T04:00:00Z"),
                    ZoneOffset.UTC);
        }

        @Bean
        CookieSerializer networkTargetSessionCookieSerializer() {
            DefaultCookieSerializer serializer = new DefaultCookieSerializer();
            serializer.setCookieName("ti_dev_session");
            serializer.setCookiePath("/");
            serializer.setUseSecureCookie(false);
            serializer.setUseHttpOnlyCookie(true);
            serializer.setUseBase64Encoding(true);
            serializer.setSameSite("Lax");
            return serializer;
        }

        @Bean
        FilterRegistrationBean<TargetSessionAuthenticationFilter>
                disableDuplicateServletAuthenticationFilter(
                        TargetSessionAuthenticationFilter filter
                ) {
            FilterRegistrationBean<TargetSessionAuthenticationFilter> registration =
                    new FilterRegistrationBean<>(filter);
            registration.setEnabled(false);
            return registration;
        }

        @Bean
        FilterRegistrationBean<Filter> targetSessionFixtureFilter() {
            Filter fixture = (request, response, chain) -> {
                if (request instanceof HttpServletRequest httpRequest
                        && UNAVAILABLE_SESSION_FIXTURE.equals(
                                httpRequest.getHeader(TARGET_SESSION_FIXTURE_HEADER))) {
                    var session = httpRequest.getSession(true);
                    session.setAttribute(TargetSessionAttributes.IDENTITY_ID, IDENTITY.id());
                    session.setAttribute(
                            TargetSessionAttributes.SESSION_VERSION,
                            IDENTITY.sessionVersion());
                }
                chain.doFilter(request, response);
            };
            FilterRegistrationBean<Filter> registration =
                    new FilterRegistrationBean<>(fixture);
            registration.setName("targetSessionNetworkFixture");
            registration.setOrder(SessionRepositoryFilter.DEFAULT_ORDER + 1);
            return registration;
        }
    }
}
