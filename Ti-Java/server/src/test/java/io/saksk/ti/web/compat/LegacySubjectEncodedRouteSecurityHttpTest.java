package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.authentication;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import io.saksk.ti.catalog.api.CatalogApplicationApi;
import io.saksk.ti.catalog.api.SubjectCatalogView;
import io.saksk.ti.catalog.api.SubjectSummaryView;
import io.saksk.ti.web.config.SecurityConfiguration;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.request.RequestIdFilter;
import io.saksk.ti.web.security.SubjectReadRateLimiter;
import io.saksk.ti.web.security.SubjectReadRequestResolver;
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
        controllers = LegacySubjectCatalogController.class,
        excludeFilters = @ComponentScan.Filter(
                type = FilterType.ASSIGNABLE_TYPE,
                classes = {
                        TargetSessionAuthenticationFilter.class,
                        TargetSessionReconciliationFilter.class
                }))
@Import({
        SecurityConfiguration.class,
        LegacySubjectSecurityErrorWriter.class,
        SafeSecurityErrorWriter.class,
        SubjectReadRequestResolver.class,
        RequestIdFilter.class,
        LegacySubjectEncodedRouteSecurityHttpTest.FixedClockConfiguration.class
})
class LegacySubjectEncodedRouteSecurityHttpTest {

    private static final SubjectReadRateLimiter.Decision ALLOWED =
            new SubjectReadRateLimiter.Decision(
                    true, 60, 59, 30, 1_784_160_061L, "60 per 1 minute");
    private static final SubjectReadRateLimiter.Decision REJECTED =
            new SubjectReadRateLimiter.Decision(
                    false, 60, 0, 30, 1_784_160_061L, "60 per 1 minute");

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    CatalogApplicationApi catalog;

    @MockitoBean
    SubjectReadRateLimiter rateLimiter;

    @Test
    void encodedUnreservedSubjectReadsUseTheExactLegacy401EntryPoint() throws Exception {
        for (String path : List.of(
                "/api/quiz/%73ubjects",
                "/api/quiz/subjects/%6deta")) {
            mockMvc.perform(get(URI.create(path))
                            .header("X-Request-ID", "encoded-subject-401"))
                    .andExpect(status().isUnauthorized())
                    .andExpect(content().contentType("application/json; charset=utf-8"))
                    .andExpect(header().string("Vary", "Origin, Cookie"))
                    .andExpect(jsonPath("$.status").value("unauthorized"))
                    .andExpect(jsonPath("$.message").value("请先登录"))
                    .andExpect(jsonPath("$.status_code").value(401))
                    .andExpect(jsonPath("$.request_id").value("encoded-subject-401"));
        }
    }

    @Test
    void encodedUnreservedReadsConsumeTheirRouteBudgetForSuccessAnd429() throws Exception {
        when(catalog.subjectCatalog(any())).thenReturn(new SubjectCatalogView(
                List.of(new SubjectSummaryView(7, "算法", 2)),
                2));
        when(rateLimiter.acquire(SubjectReadRateLimiter.Route.SUBJECTS, 4101))
                .thenReturn(ALLOWED);
        when(rateLimiter.acquire(SubjectReadRateLimiter.Route.SUBJECTS_META, 4101))
                .thenReturn(REJECTED);

        mockMvc.perform(get(URI.create("/api/quiz/%73ubjects"))
                        .with(targetAuthentication())
                        .header("X-Request-ID", "encoded-subject-ok"))
                .andExpect(status().isOk())
                .andExpect(header().string("X-RateLimit-Limit", "60"))
                .andExpect(header().string("X-RateLimit-Remaining", "59"))
                .andExpect(jsonPath("$.subjects[0]").value("算法"));

        mockMvc.perform(get(URI.create("/api/quiz/subjects/%6deta"))
                        .with(targetAuthentication())
                        .header("X-Request-ID", "encoded-subject-429"))
                .andExpect(status().isTooManyRequests())
                .andExpect(content().contentType("application/json"))
                .andExpect(header().string("X-RateLimit-Limit", "60"))
                .andExpect(header().string("X-RateLimit-Remaining", "0"))
                .andExpect(jsonPath("$.status").value("error"))
                .andExpect(jsonPath("$.message").value("60 per 1 minute"))
                .andExpect(jsonPath("$.payload").isEmpty())
                .andExpect(jsonPath("$.status_code").value(429));

        verify(rateLimiter).acquire(SubjectReadRateLimiter.Route.SUBJECTS, 4101);
        verify(rateLimiter).acquire(SubjectReadRateLimiter.Route.SUBJECTS_META, 4101);
    }

    @Test
    void encodedMetaInfrastructureFailureKeepsTheMeta500Shape() throws Exception {
        when(rateLimiter.acquire(SubjectReadRateLimiter.Route.SUBJECTS_META, 4101))
                .thenReturn(ALLOWED);
        when(catalog.subjectCatalog(any()))
                .thenThrow(new IllegalStateException("database-password=secret"));

        var result = mockMvc.perform(get(URI.create("/api/quiz/subjects/%6deta"))
                        .with(targetAuthentication())
                        .header("X-Request-ID", "encoded-meta-500"))
                .andExpect(status().isInternalServerError())
                .andExpect(content().contentType("application/json; charset=utf-8"))
                .andExpect(jsonPath("$.status").value("error"))
                .andExpect(jsonPath("$.message").value("服务暂时不可用"))
                .andExpect(jsonPath("$.data.quiz_count").value(0))
                .andExpect(jsonPath("$.data.subjects").isArray())
                .andExpect(jsonPath("$.request_id").value("encoded-meta-500"))
                .andReturn();

        assertThat(result.getResponse().getContentAsString())
                .doesNotContain("secret", "database-password");
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
