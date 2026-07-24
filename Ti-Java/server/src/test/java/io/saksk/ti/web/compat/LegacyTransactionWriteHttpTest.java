package io.saksk.ti.web.compat;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.saksk.ti.catalog.api.QuestionEditApplicationApi;
import io.saksk.ti.learning.api.CheckinApplicationApi;
import io.saksk.ti.learning.api.LearningWriteApplicationApi;
import io.saksk.ti.learning.api.QuestionLearningStatusApplicationApi;
import io.saksk.ti.learning.api.RecordResultApplicationApi;
import io.saksk.ti.learning.api.StudyWriteApplicationApi;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import io.saksk.ti.operations.api.QuizLimitPolicyApplicationApi;
import io.saksk.ti.web.config.SecurityConfiguration;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import io.saksk.ti.web.security.TargetSessionAuthenticationFilter;
import io.saksk.ti.web.security.TargetSessionReconciliationFilter;
import io.saksk.ti.web.security.TransactionWriteRateLimiter;
import io.saksk.ti.web.security.TransactionWriteRequestResolver;
import io.saksk.ti.web.security.TransactionWriteRequestResolver.Route;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;
import org.springframework.context.annotation.Import;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(
        controllers = LegacyTransactionWriteController.class,
        excludeFilters = @ComponentScan.Filter(
                type = FilterType.ASSIGNABLE_TYPE,
                classes = {
                        TargetSessionAuthenticationFilter.class,
                        TargetSessionReconciliationFilter.class
                }))
@Import({
        SecurityConfiguration.class,
        SafeSecurityErrorWriter.class,
        LegacyTransactionWriteSecurityErrorWriter.class,
        TransactionWriteRequestResolver.class,
        RequestIdFilter.class,
        LegacyTransactionWriteHttpTest.FixedClockConfiguration.class
})
class LegacyTransactionWriteHttpTest {

    private static final String ADDRESS = "198.51.100.88";
    private static final TransactionWriteRateLimiter.Decision ALLOWED =
            new TransactionWriteRateLimiter.Decision(
                    true,
                    30,
                    29,
                    42,
                    1_784_347_242L);

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    LearningWriteApplicationApi favorites;

    @MockitoBean
    RecordResultApplicationApi recordResults;

    @MockitoBean
    StudyWriteApplicationApi study;

    @MockitoBean
    CheckinApplicationApi checkins;

    @MockitoBean
    QuestionEditApplicationApi questionEdits;

    @MockitoBean
    QuestionLearningStatusApplicationApi statuses;

    @MockitoBean
    QuizLimitPolicyApplicationApi quizLimits;

    @MockitoBean
    TransactionWriteRateLimiter limiter;

    @MockitoBean
    ClientAddressResolver addresses;

    @BeforeEach
    void defaults() {
        when(addresses.resolve(any())).thenReturn(ADDRESS);
        when(limiter.acquireForAddress(any(), any())).thenReturn(ALLOWED);
        when(limiter.acquireForIdentity(any(), anyLong())).thenReturn(ALLOWED);
    }

    @Test
    void authenticatedSessionXhrUsesIdentityBudgetAndCompatibilityHeaders()
            throws Exception {
        when(favorites.toggleFavorite(any()))
                .thenReturn(ToggleFavoriteResult.success(true, false));

        mockMvc.perform(post("/api/favorite")
                        .with(targetAuthentication())
                        .header("X-Requested-With", "XMLHttpRequest")
                        .header("X-Request-ID", "phase4c-write-http-session")
                        .contentType("application/json")
                        .content("{\"question_id\":93001}"))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/json; charset=utf-8"))
                .andExpect(header().string("X-RateLimit-Limit", "30"))
                .andExpect(header().string("X-RateLimit-Remaining", "29"))
                .andExpect(header().string("X-Frame-Options", "SAMEORIGIN"))
                .andExpect(header().string(
                        "Referrer-Policy",
                        "strict-origin-when-cross-origin"))
                .andExpect(header().string("X-Content-Type-Options", "nosniff"))
                .andExpect(jsonPath("$.status").value("success"))
                .andExpect(jsonPath("$.data.is_favorite").value(true))
                .andExpect(jsonPath("$.request_id")
                        .value("phase4c-write-http-session"));

        verify(limiter).acquireForIdentity(Route.FAVORITE_WEB, 99_451L);
        verifyNoInteractions(addresses);
    }

    @Test
    void authenticatedSessionWithoutXhrConsumesBudgetThenFailsClosed()
            throws Exception {
        mockMvc.perform(post("/api/quiz/favorite")
                        .with(targetAuthentication())
                        .header("X-Request-ID", "phase4c-write-http-no-xhr")
                        .contentType("application/json")
                        .content("{\"question_id\":93001}"))
                .andExpect(status().isForbidden())
                .andExpect(header().string("X-RateLimit-Limit", "30"))
                .andExpect(jsonPath("$.message")
                        .value("请求被拒绝（缺少安全标头）"))
                .andExpect(jsonPath("$.request_id")
                        .value("phase4c-write-http-no-xhr"));

        verify(limiter).acquireForIdentity(Route.FAVORITE_API, 99_451L);
        verifyNoInteractions(favorites);
    }

    @Test
    void bearerAttributeAllowsTheWriteWithoutXhr() throws Exception {
        mockMvc.perform(post("/api/quiz/favorite")
                        .with(targetAuthentication())
                        .requestAttr(
                                TargetSessionAuthenticationFilter
                                        .LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE,
                                Boolean.TRUE)
                        .header("X-Request-ID", "phase4c-write-http-bearer")
                        .contentType("application/json")
                        .content("{\"question_id\":\"not-an-integer\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(header().string("X-RateLimit-Limit", "30"))
                .andExpect(jsonPath("$.message").value("question_id 参数错误"));

        verify(limiter).acquireForIdentity(Route.FAVORITE_API, 99_451L);
    }

    @Test
    void anonymousXhrUsesIpBudgetBeforeRouteSpecificAuthenticationEnvelope()
            throws Exception {
        mockMvc.perform(post("/api/favorite")
                        .header("X-Requested-With", "XMLHttpRequest")
                        .header("X-Request-ID", "phase4c-write-http-anonymous")
                        .contentType("application/json")
                        .content("{\"question_id\":\"not-an-integer\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("X-RateLimit-Limit", "30"))
                .andExpect(jsonPath("$.status").value("unauthorized"))
                .andExpect(jsonPath("$.message")
                        .value("请先登录后使用此功能"));

        verify(limiter).acquireForAddress(Route.FAVORITE_WEB, ADDRESS);
        verifyNoInteractions(favorites);
    }

    @Test
    void exhaustedRouteBudgetTerminatesBeforeSafetyAndApplication() throws Exception {
        when(limiter.acquireForIdentity(Route.FAVORITE_API, 99_451L))
                .thenReturn(new TransactionWriteRateLimiter.Decision(
                        false,
                        30,
                        0,
                        27,
                        1_784_347_227L));

        mockMvc.perform(post("/api/quiz/favorite")
                        .with(targetAuthentication())
                        .header("X-Request-ID", "phase4c-write-http-limited")
                        .contentType("application/json")
                        .content("{\"question_id\":93001}"))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string("X-RateLimit-Remaining", "0"))
                .andExpect(header().string("Retry-After", "27"))
                .andExpect(jsonPath("$.message").value("30 per 1 minute"))
                .andExpect(jsonPath("$.payload").isEmpty());

        verifyNoInteractions(favorites);
    }

    @Test
    void corsPreflightTerminatesBeforeAuthenticationRateAndApplication()
            throws Exception {
        mockMvc.perform(options("/api/quiz/study/review/master")
                        .header("Origin", "http://127.0.0.1:3000")
                        .header("Access-Control-Request-Method", "POST")
                        .header(
                                "Access-Control-Request-Headers",
                                "Content-Type, Authorization, X-Requested-With"))
                .andExpect(status().isNoContent())
                .andExpect(content().bytes(new byte[0]))
                .andExpect(header().string(
                        "Access-Control-Allow-Origin",
                        "http://127.0.0.1:3000"))
                .andExpect(header().string(
                        "Access-Control-Allow-Methods",
                        "POST, OPTIONS"));

        verifyNoInteractions(limiter, favorites, study);
    }

    @Test
    void malformedJsonUsesRouteSpecificCompatibility400InsteadOfGlobal500()
            throws Exception {
        mockMvc.perform(post("/api/favorite")
                        .with(targetAuthentication())
                        .header("X-Requested-With", "XMLHttpRequest")
                        .header("X-Request-ID", "phase4c-write-malformed-favorite")
                        .contentType("application/json")
                        .content("{"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("question_id 参数错误"))
                .andExpect(jsonPath("$.request_id")
                        .value("phase4c-write-malformed-favorite"));

        mockMvc.perform(post("/api/quiz/study/review/record")
                        .with(targetAuthentication())
                        .header("X-Requested-With", "XMLHttpRequest")
                        .header("X-Request-ID", "phase4c-write-malformed-review")
                        .contentType("application/json")
                        .content("{"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("rating 参数错误"));

        mockMvc.perform(put("/api/quiz/questions/93006")
                        .with(targetAuthentication())
                        .header("X-Requested-With", "XMLHttpRequest")
                        .header("X-Request-ID", "phase4c-write-malformed-edit")
                        .contentType("application/json")
                        .content("{"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("请求数据格式错误"));

        verifyNoInteractions(favorites, study, questionEdits);
    }

    @Test
    void oversizedIdempotencyKeyIsAStable400BeforeAnyApplicationMutation()
            throws Exception {
        String oversized = "x".repeat(256);

        mockMvc.perform(post("/api/quiz/favorite")
                        .with(targetAuthentication())
                        .requestAttr(
                                TargetSessionAuthenticationFilter
                                        .LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE,
                                Boolean.TRUE)
                        .header("Idempotency-Key", oversized)
                        .contentType("application/json")
                        .content("{\"question_id\":93001}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message")
                        .value("Idempotency-Key 参数错误"));

        mockMvc.perform(put("/api/quiz/questions/93006")
                        .with(targetAuthentication())
                        .requestAttr(
                                TargetSessionAuthenticationFilter
                                        .LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE,
                                Boolean.TRUE)
                        .header("Idempotency-Key", oversized)
                        .contentType("application/json")
                        .content("{\"content\":\"valid\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message")
                        .value("Idempotency-Key 参数错误"));

        verifyNoInteractions(favorites, questionEdits, statuses);
    }

    private static org.springframework.test.web.servlet.request.RequestPostProcessor
            targetAuthentication() {
        TargetAuthenticatedPrincipal principal =
                new TargetAuthenticatedPrincipal(99_451L, "redacted");
        return authentication(new UsernamePasswordAuthenticationToken(
                principal,
                null,
                List.of(new SimpleGrantedAuthority("ROLE_USER"))));
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class FixedClockConfiguration {

        @Bean
        Clock clock() {
            return Clock.fixed(
                    Instant.parse("2026-07-18T04:00:00Z"),
                    ZoneOffset.UTC);
        }
    }
}
