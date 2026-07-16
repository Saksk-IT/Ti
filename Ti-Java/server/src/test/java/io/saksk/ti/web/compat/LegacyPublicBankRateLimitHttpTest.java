package io.saksk.ti.web.compat;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.saksk.ti.catalog.api.PublicBankCatalogApi;
import io.saksk.ti.web.config.SecurityConfiguration;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.ClientAddressResolver;
import io.saksk.ti.web.security.PublicBankReadRateLimiter;
import io.saksk.ti.web.security.PublicBankReadRequestResolver;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import io.saksk.ti.web.security.TargetSessionAuthenticationFilter;
import io.saksk.ti.web.security.TargetSessionReconciliationFilter;
import java.net.URI;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
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
        controllers = LegacyPublicBankCatalogController.class,
        excludeFilters = @ComponentScan.Filter(
                type = FilterType.ASSIGNABLE_TYPE,
                classes = {
                        TargetSessionAuthenticationFilter.class,
                        TargetSessionReconciliationFilter.class
                }))
@Import({
        SecurityConfiguration.class,
        SafeSecurityErrorWriter.class,
        LegacyPublicBankSecurityErrorWriter.class,
        PublicBankReadRequestResolver.class,
        RequestIdFilter.class,
        LegacyPublicBankRateLimitHttpTest.FixedClockConfiguration.class
})
class LegacyPublicBankRateLimitHttpTest {

    private static final String ADDRESS = "198.51.100.41";
    private static final PublicBankReadRateLimiter.Decision ALLOWED =
            new PublicBankReadRateLimiter.Decision(
                    true, 10, 9, 2, 1_784_174_402L, "10 per 1 second");
    private static final PublicBankReadRateLimiter.Decision REJECTED =
            new PublicBankReadRateLimiter.Decision(
                    false, 10, 0, 2, 1_784_174_402L, "10 per 1 second");

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    PublicBankCatalogApi catalog;

    @MockitoBean
    PublicBankReadRateLimiter rateLimiter;

    @MockitoBean
    ClientAddressResolver clientAddresses;

    @Test
    void anonymousSuccessUsesTheResolvedAddressAndCarriesAllFourHeaders() throws Exception {
        when(clientAddresses.resolve(any())).thenReturn(ADDRESS);
        when(rateLimiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, ADDRESS)).thenReturn(ALLOWED);
        when(catalog.boards(any())).thenReturn(List.of());

        mockMvc.perform(get("/api/public/banks/boards")
                        .header("X-Request-ID", "public-bank-address-success"))
                .andExpect(status().isOk())
                .andExpect(header().string("X-RateLimit-Limit", "10"))
                .andExpect(header().string("X-RateLimit-Remaining", "9"))
                .andExpect(header().string("X-RateLimit-Reset", "1784174402"))
                .andExpect(header().string("Retry-After", "2"));

        verify(rateLimiter).acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS, ADDRESS);
    }

    @Test
    void authenticatedTargetIdentityTakesPriorityOverTheClientAddress() throws Exception {
        when(rateLimiter.acquireForIdentity(
                PublicBankReadRequestResolver.Route.BOARDS, 4101)).thenReturn(ALLOWED);
        when(catalog.boards(any())).thenReturn(List.of());

        mockMvc.perform(get("/api/public/banks/boards")
                        .with(targetAuthentication())
                        .header("X-Request-ID", "public-bank-identity-success"))
                .andExpect(status().isOk())
                .andExpect(header().string("X-RateLimit-Remaining", "9"));

        verify(rateLimiter).acquireForIdentity(
                PublicBankReadRequestResolver.Route.BOARDS, 4101);
        verifyNoInteractions(clientAddresses);
    }

    @Test
    void everyEndpointHasAnIndependentRouteBudgetAndExact429Envelope() throws Exception {
        when(clientAddresses.resolve(any())).thenReturn(ADDRESS);
        when(rateLimiter.acquireForAddress(any(), eq(ADDRESS))).thenReturn(REJECTED);
        Map<String, PublicBankReadRequestResolver.Route> routes = new LinkedHashMap<>();
        routes.put("/api/public/banks", PublicBankReadRequestResolver.Route.LEGACY_LIST);
        routes.put("/api/public/banks/boards", PublicBankReadRequestResolver.Route.BOARDS);
        routes.put(
                "/api/public/banks/card/user/5401",
                PublicBankReadRequestResolver.Route.CARD_DETAIL);
        routes.put("/api/public/banks/hot", PublicBankReadRequestResolver.Route.HOT);
        routes.put("/api/public/banks/list", PublicBankReadRequestResolver.Route.PLAZA_LIST);
        routes.put("/api/public/banks/summary", PublicBankReadRequestResolver.Route.SUMMARY);
        routes.put("/api/public/banks/5401", PublicBankReadRequestResolver.Route.DETAIL);

        for (Map.Entry<String, PublicBankReadRequestResolver.Route> route : routes.entrySet()) {
            mockMvc.perform(get(URI.create(route.getKey()))
                            .header("X-Request-ID", "public-bank-429"))
                    .andExpect(status().isTooManyRequests())
                    .andExpect(content().contentType("application/json"))
                    .andExpect(header().string("X-RateLimit-Limit", "10"))
                    .andExpect(header().string("X-RateLimit-Remaining", "0"))
                    .andExpect(header().string("X-RateLimit-Reset", "1784174402"))
                    .andExpect(header().string("Retry-After", "2"))
                    .andExpect(jsonPath("$.status").value("error"))
                    .andExpect(jsonPath("$.message").value("10 per 1 second"))
                    .andExpect(jsonPath("$.code").doesNotExist())
                    .andExpect(jsonPath("$.payload").isEmpty())
                    .andExpect(jsonPath("$.status_code").value(429))
                    .andExpect(jsonPath("$.request_id").value("public-bank-429"));
            verify(rateLimiter).acquireForAddress(route.getValue(), ADDRESS);
        }
        verifyNoInteractions(catalog);
    }

    @Test
    void matchedBusiness404ConsumesBudgetButConverter404DoesNot() throws Exception {
        when(clientAddresses.resolve(any())).thenReturn(ADDRESS);
        when(rateLimiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.DETAIL, ADDRESS)).thenReturn(ALLOWED);
        when(catalog.detail(any(), any())).thenReturn(Optional.empty());

        mockMvc.perform(get("/api/public/banks/5401")
                        .header("X-Request-ID", "public-bank-business-404"))
                .andExpect(status().isNotFound())
                .andExpect(header().string("X-RateLimit-Limit", "10"))
                .andExpect(header().string("X-RateLimit-Remaining", "9"))
                .andExpect(jsonPath("$.message").value("题库不存在或未公开"));

        verify(rateLimiter).acquireForAddress(
                PublicBankReadRequestResolver.Route.DETAIL, ADDRESS);
    }

    @Test
    void converter404PathsKeepNoLimiterHeadersAndNeverReserveAnActor() throws Exception {
        for (String path : List.of(
                "/api/public/banks/-1",
                "/api/public/banks/not-an-int",
                "/api/public/banks/card/user/-1",
                "/api/public/banks/card/user/not-an-int")) {
            mockMvc.perform(get(URI.create(path))
                            .header("X-Request-ID", "public-bank-converter-404"))
                    .andExpect(status().isNotFound())
                    .andExpect(content().contentType("application/json"))
                    .andExpect(header().doesNotExist("X-RateLimit-Limit"))
                    .andExpect(header().doesNotExist("X-RateLimit-Remaining"))
                    .andExpect(header().doesNotExist("X-RateLimit-Reset"))
                    .andExpect(header().doesNotExist("Retry-After"));
        }

        verifyNoInteractions(rateLimiter, clientAddresses, catalog);
    }

    @Test
    void arbitraryPrecisionDetailAndCardIdsConsumeTheirBudgetsBeforeTheApprovedSafe500()
            throws Exception {
        String arbitraryPrecisionId = "999999999999999999999999999999999999999999999999";
        when(clientAddresses.resolve(any())).thenReturn(ADDRESS);
        when(rateLimiter.acquireForAddress(any(), eq(ADDRESS))).thenReturn(ALLOWED);
        Map<String, PublicBankReadRequestResolver.Route> routes = new LinkedHashMap<>();
        routes.put(
                "/api/public/banks/" + arbitraryPrecisionId,
                PublicBankReadRequestResolver.Route.DETAIL);
        routes.put(
                "/api/public/banks/card/user/" + arbitraryPrecisionId,
                PublicBankReadRequestResolver.Route.CARD_DETAIL);

        for (Map.Entry<String, PublicBankReadRequestResolver.Route> route : routes.entrySet()) {
            mockMvc.perform(get(URI.create(route.getKey()))
                            .header("X-Request-ID", "public-bank-arbitrary-precision-500"))
                    .andExpect(status().isInternalServerError())
                    .andExpect(content().contentType("application/json; charset=utf-8"))
                    .andExpect(header().string("X-RateLimit-Limit", "10"))
                    .andExpect(header().string("X-RateLimit-Remaining", "9"))
                    .andExpect(header().string("X-RateLimit-Reset", "1784174402"))
                    .andExpect(header().string("Retry-After", "2"))
                    .andExpect(jsonPath("$.status").value("error"))
                    .andExpect(jsonPath("$.code").value(1))
                    .andExpect(jsonPath("$.message").value("服务暂时不可用"))
                    .andExpect(jsonPath("$.payload").doesNotExist())
                    .andExpect(jsonPath("$.status_code").value(500))
                    .andExpect(jsonPath("$.request_id")
                            .value("public-bank-arbitrary-precision-500"));
            verify(rateLimiter).acquireForAddress(route.getValue(), ADDRESS);
        }

        verifyNoInteractions(catalog);
    }

    @Test
    void unicodeDecimalDetailAndCardIdsConsumeBudgetsAndReachTheHandlers() throws Exception {
        when(clientAddresses.resolve(any())).thenReturn(ADDRESS);
        when(rateLimiter.acquireForAddress(any(), eq(ADDRESS))).thenReturn(ALLOWED);
        when(catalog.detail(any(), any())).thenReturn(Optional.empty());
        Map<String, PublicBankReadRequestResolver.Route> routes = new LinkedHashMap<>();
        routes.put("/api/public/banks/٥٤٠١", PublicBankReadRequestResolver.Route.DETAIL);
        routes.put(
                "/api/public/banks/card/system/５３０１",
                PublicBankReadRequestResolver.Route.CARD_DETAIL);

        for (Map.Entry<String, PublicBankReadRequestResolver.Route> route : routes.entrySet()) {
            URI encodedUri = URI.create(URI.create(route.getKey()).toASCIIString());
            mockMvc.perform(get(encodedUri)
                            .header("X-Request-ID", "public-bank-unicode-decimal"))
                    .andExpect(status().isNotFound())
                    .andExpect(header().string("X-RateLimit-Limit", "10"))
                    .andExpect(header().string("X-RateLimit-Remaining", "9"))
                    .andExpect(jsonPath("$.message").value("题库不存在或未公开"));
            verify(rateLimiter).acquireForAddress(route.getValue(), ADDRESS);
        }

        verify(catalog, org.mockito.Mockito.times(2)).detail(any(), any());
    }

    @Test
    void limiterInfrastructureFailureReturnsTheApprovedStable503() throws Exception {
        when(clientAddresses.resolve(any())).thenReturn(ADDRESS);
        when(rateLimiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.SUMMARY, ADDRESS))
                .thenThrow(new IllegalStateException("redis://secret-host"));

        mockMvc.perform(get("/api/public/banks/summary")
                        .header("X-Request-ID", "public-bank-rate-503"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(content().contentType("application/json; charset=utf-8"))
                .andExpect(header().doesNotExist("X-RateLimit-Limit"))
                .andExpect(header().doesNotExist("Retry-After"))
                .andExpect(jsonPath("$.status").value("error"))
                .andExpect(jsonPath("$.code").value(1))
                .andExpect(jsonPath("$.message").value("服务暂时不可用"))
                .andExpect(jsonPath("$.status_code").value(503))
                .andExpect(jsonPath("$.request_id").value("public-bank-rate-503"));

        verifyNoInteractions(catalog);
        verify(rateLimiter, never()).acquireForIdentity(any(), anyLong());
    }

    private static org.springframework.test.web.servlet.request.RequestPostProcessor
            targetAuthentication() {
        var principal = new TargetAuthenticatedPrincipal(4101, "redacted");
        return authentication(new UsernamePasswordAuthenticationToken(
                principal,
                null,
                List.of()));
    }

    @TestConfiguration(proxyBeanMethods = false)
    static class FixedClockConfiguration {

        @Bean
        Clock clock() {
            return Clock.fixed(Instant.parse("2026-07-16T04:00:00Z"), ZoneOffset.UTC);
        }
    }
}
