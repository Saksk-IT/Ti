package io.saksk.ti.web.compat;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.head;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.web.config.SecurityConfiguration;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Decision;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Window;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import io.saksk.ti.web.security.TargetSessionAuthenticationFilter;
import io.saksk.ti.web.security.TargetSessionReconciliationFilter;
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
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(
        controllers = LegacyPersonalBankUserCountsController.class,
        excludeFilters = @ComponentScan.Filter(
                type = FilterType.ASSIGNABLE_TYPE,
                classes = {
                        TargetSessionAuthenticationFilter.class,
                        TargetSessionReconciliationFilter.class
                }))
@Import({
        SecurityConfiguration.class,
        SafeSecurityErrorWriter.class,
        LegacyPersonalBankUserCountsSecurityErrorWriter.class,
        PersonalBankUserCountsReadRequestResolver.class,
        RequestIdFilter.class,
        LegacyPersonalBankUserCountsHttpTest.FixedClockConfiguration.class
})
class LegacyPersonalBankUserCountsHttpTest {

    private static final String ADDRESS = "198.51.100.41";
    private static final Decision ALLOWED =
            new Decision(true, Window.SECOND, 10, 9, 2, 1_784_347_202L);

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    LearningApplicationApi learning;

    @MockitoBean
    PersonalBankUserCountsReadRateLimiter rateLimiter;

    @MockitoBean
    ClientAddressResolver clientAddresses;

    @BeforeEach
    void defaults() {
        when(clientAddresses.resolve(any())).thenReturn(ADDRESS);
        when(rateLimiter.acquireForAddress(any(), any())).thenReturn(ALLOWED);
        when(rateLimiter.acquireForIdentity(any(), anyLong())).thenReturn(ALLOWED);
    }

    @Test
    void authenticatedApiReadUsesIdentityBudgetAndExactCompatibilityEnvelope() throws Exception {
        when(learning.findPersonalBankUserCounts(any(), any()))
                .thenReturn(PersonalBankUserCountsResult.available(
                        new PersonalBankUserCountsView(
                                9, 5, 3, List.of("选择题", "简答题"), false)));

        mockMvc.perform(get("/api/user/banks/api/99551/user-counts")
                        .with(targetAuthentication())
                        .header("X-Request-ID", "phase4c-http-success"))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/json; charset=utf-8"))
                .andExpect(header().string("X-RateLimit-Limit", "10"))
                .andExpect(header().string("X-RateLimit-Remaining", "9"))
                .andExpect(header().string("X-Frame-Options", "SAMEORIGIN"))
                .andExpect(header().string(
                        "Referrer-Policy", "strict-origin-when-cross-origin"))
                .andExpect(header().string("X-Content-Type-Options", "nosniff"))
                .andExpect(jsonPath("$.status").value("success"))
                .andExpect(jsonPath("$.code").value(0))
                .andExpect(jsonPath("$.data.total").value(9))
                .andExpect(jsonPath("$.data.favorites").value(5))
                .andExpect(jsonPath("$.data.mistakes").value(3))
                .andExpect(jsonPath("$.data.shuffle_options_available").value(false))
                .andExpect(jsonPath("$.message").value(""))
                .andExpect(jsonPath("$.request_id").value("phase4c-http-success"));

        verify(rateLimiter).acquireForIdentity(Alias.API, 99_451L);
        verifyNoInteractions(clientAddresses);
    }

    @Test
    void anonymousApiReadUsesIpBudgetBeforeTheUniform401() throws Exception {
        mockMvc.perform(get("/api/user/banks/api/41/user-counts")
                        .header("X-Request-ID", "phase4c-http-anonymous"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string("X-RateLimit-Limit", "10"))
                .andExpect(jsonPath("$.status").value("unauthorized"))
                .andExpect(jsonPath("$.message").value("请先登录"))
                .andExpect(jsonPath("$.status_code").value(401))
                .andExpect(jsonPath("$.request_id").value("phase4c-http-anonymous"));

        verify(rateLimiter).acquireForAddress(Alias.API, ADDRESS);
        verifyNoInteractions(learning);
    }

    @Test
    void webAuthorizationAlwaysRedirectsAndUsesIpEvenWithAnEffectivePrincipal()
            throws Exception {
        mockMvc.perform(get("/user/banks/api/41/user-counts")
                        .with(targetAuthentication())
                        .header("Authorization", "Bearer valid-but-web-forbidden")
                        .header("X-Request-ID", "phase4c-http-web-authorization"))
                .andExpect(status().isFound())
                .andExpect(header().string("Location", "/login"))
                .andExpect(header().string("X-RateLimit-Limit", "10"));

        verify(rateLimiter).acquireForAddress(Alias.WEB, ADDRESS);
        verify(rateLimiter, never()).acquireForIdentity(Alias.WEB, 99_451L);
        verifyNoInteractions(learning);
    }

    @Test
    void zeroAndOverflowAuthenticateAndConsumeBudgetWithoutCallingTheApplication()
            throws Exception {
        mockMvc.perform(get("/api/user/banks/api/0/user-counts")
                        .with(targetAuthentication())
                        .header("X-Request-ID", "phase4c-http-zero"))
                .andExpect(status().isForbidden())
                .andExpect(header().string("X-RateLimit-Limit", "10"))
                .andExpect(jsonPath("$.message").value("无权访问此题库"));
        mockMvc.perform(get("/api/user/banks/api/999999999999999999999999/user-counts")
                        .with(targetAuthentication())
                        .header("X-Request-ID", "phase4c-http-overflow"))
                .andExpect(status().isInternalServerError())
                .andExpect(header().string("X-RateLimit-Limit", "10"))
                .andExpect(jsonPath("$.message")
                        .value("An unexpected server error occurred."));

        verify(rateLimiter, org.mockito.Mockito.times(2))
                .acquireForIdentity(Alias.API, 99_451L);
        verifyNoInteractions(learning);
    }

    @Test
    void converterAndShapeMissesAreUncountedCompatibility404s() throws Exception {
        for (String path : List.of(
                "/api/user/banks/api/-1/user-counts",
                "/api/user/banks/api/not-a-bank/user-counts",
                "/api/user/banks/api/41/user-counts/extra")) {
            mockMvc.perform(get(path)
                            .header("Origin", "https://evil.example")
                            .header("X-Request-ID", "phase4c-http-converter-miss"))
                    .andExpect(status().isNotFound())
                    .andExpect(header().doesNotExist("X-RateLimit-Limit"))
                    .andExpect(header().doesNotExist("Access-Control-Allow-Origin"))
                    .andExpect(jsonPath("$.status").value("error"))
                    .andExpect(jsonPath("$.status_code").value(404));
        }

        verifyNoInteractions(rateLimiter, learning);
    }

    @Test
    void corsAndBareOptionsTerminateBeforeAuthenticationRateOrApplication() throws Exception {
        mockMvc.perform(get("/api/user/banks/api/41/user-counts")
                        .header("Origin", "https://evil.example"))
                .andExpect(status().isForbidden())
                .andExpect(content().bytes(new byte[0]))
                .andExpect(header().doesNotExist("X-RateLimit-Limit"));

        mockMvc.perform(options("/api/user/banks/api/41/user-counts")
                        .header("Origin", "https://servicewechat.com")
                        .header("Access-Control-Request-Method", "GET")
                        .header("Access-Control-Request-Headers", "Authorization"))
                .andExpect(status().isNoContent())
                .andExpect(content().bytes(new byte[0]))
                .andExpect(header().string(
                        "Access-Control-Allow-Origin", "https://servicewechat.com"))
                .andExpect(header().string("Allow", "GET, HEAD, OPTIONS"));

        mockMvc.perform(options("/user/banks/api/0/user-counts")
                        .header("Origin", "https://evil.example"))
                .andExpect(status().isNoContent())
                .andExpect(header().doesNotExist("Access-Control-Allow-Origin"));

        verifyNoInteractions(rateLimiter, learning);
    }

    @Test
    void headExecutesTheSameApplicationAndRatePathButHasNoBodyBytes() throws Exception {
        when(learning.findPersonalBankUserCounts(any(), any()))
                .thenReturn(PersonalBankUserCountsResult.available(
                        new PersonalBankUserCountsView(1, 0, 0, List.of(), false)));

        mockMvc.perform(head("/api/user/banks/api/41/user-counts")
                        .with(targetAuthentication())
                        .header("X-Request-ID", "phase4c-http-head"))
                .andExpect(status().isOk())
                .andExpect(header().string("X-RateLimit-Limit", "10"))
                .andExpect(content().bytes(new byte[0]));

        verify(rateLimiter).acquireForIdentity(Alias.API, 99_451L);
        verify(learning).findPersonalBankUserCounts(any(), any());
    }

    private static org.springframework.test.web.servlet.request.RequestPostProcessor
            targetAuthentication() {
        TargetAuthenticatedPrincipal principal =
                new TargetAuthenticatedPrincipal(99_451L, "redacted");
        return authentication(new UsernamePasswordAuthenticationToken(
                principal,
                null,
                List.of()));
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class FixedClockConfiguration {

        @Bean
        Clock clock() {
            return Clock.fixed(Instant.parse("2026-07-18T04:00:00Z"), ZoneOffset.UTC);
        }
    }
}
