package io.saksk.ti.web.compat;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.saksk.ti.catalog.api.PublicBankCatalogApi;
import io.saksk.ti.web.config.SecurityConfiguration;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.PublicBankReadRequestResolver;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import io.saksk.ti.web.security.TargetSessionAuthenticationFilter;
import io.saksk.ti.web.security.TargetSessionReconciliationFilter;
import java.net.URI;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
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
        PublicBankReadRequestResolver.class,
        RequestIdFilter.class,
        LegacyPublicBankRouteSecurityHttpTest.FixedClockConfiguration.class
})
class LegacyPublicBankRouteSecurityHttpTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    PublicBankCatalogApi catalog;

    @Test
    void literalMatrixParameterRoutesAreRejectedByTheFullSecurityFilterChain() throws Exception {
        for (String path : List.of(
                "/api/public/banks;v=1",
                "/api/public/banks/list;v=1",
                "/api/public/banks/41;v=1",
                "/api/public/banks/card;v=1/user/41",
                "/api/public/banks/card/user;v=1/41",
                "/api/public/banks/card/user/41;v=1")) {
            mockMvc.perform(get(URI.create(path))
                            .with(targetAuthentication())
                            .header("X-Request-ID", "matrix-parameter-denied"))
                    .andExpect(status().isBadRequest());
        }

        verifyNoInteractions(catalog);
    }

    @Test
    void converter404KeepsExactJsonContentTypeAndReservesNoRateLimitHeaders()
            throws Exception {
        mockMvc.perform(get(URI.create("/api/public/banks/-1"))
                        .header("X-Request-ID", "converter-404"))
                .andExpect(status().isNotFound())
                .andExpect(header().string("Content-Type", "application/json"))
                .andExpect(header().string("Vary", "Origin, Cookie"))
                .andExpect(header().doesNotExist("X-RateLimit-Limit"))
                .andExpect(header().doesNotExist("X-RateLimit-Remaining"))
                .andExpect(header().doesNotExist("X-RateLimit-Reset"))
                .andExpect(header().doesNotExist("Retry-After"))
                .andExpect(jsonPath("$.status").value("error"))
                .andExpect(jsonPath("$.status_code").value(404))
                .andExpect(jsonPath("$.payload").isEmpty())
                .andExpect(jsonPath("$.request_id").value("converter-404"));

        verifyNoInteractions(catalog);
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
            return Clock.fixed(Instant.parse("2026-07-16T01:00:00Z"), ZoneOffset.UTC);
        }
    }
}
