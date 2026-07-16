package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.web.compat.LegacySubjectSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

class SubjectReadRateLimitFilterTest {

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void authenticatedEncodedUnreservedSubjectGetConsumesTheIdentityBudgetAndContinues()
            throws Exception {
        SubjectReadRateLimiter limiter = mock(SubjectReadRateLimiter.class);
        LegacySubjectSecurityErrorWriter errors = mock(LegacySubjectSecurityErrorWriter.class);
        SubjectReadRateLimitFilter filter = filter(limiter, errors);
        var request = new MockHttpServletRequest("GET", "/api/quiz/subjects/%6deta");
        request.setServletPath("/api/quiz/subjects/meta");
        var response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        var principal = new TargetAuthenticatedPrincipal(4101, "redacted");
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(principal, null, List.of()));
        var decision = new SubjectReadRateLimiter.Decision(
                true, 60, 59, 30, 1_784_160_061L, "60 per 1 minute");
        when(limiter.acquire(SubjectReadRateLimiter.Route.SUBJECTS_META, 4101))
                .thenReturn(decision);

        filter.doFilter(request, response, chain);

        verify(errors).writeRateLimitHeaders(response, decision);
        verify(chain).doFilter(request, response);
    }

    @Test
    void exhaustedBudgetFailsBeforeTheControllerAndRedisFailureFailsClosed() throws Exception {
        SubjectReadRateLimiter limiter = mock(SubjectReadRateLimiter.class);
        LegacySubjectSecurityErrorWriter errors = mock(LegacySubjectSecurityErrorWriter.class);
        SubjectReadRateLimitFilter filter = filter(limiter, errors);
        var request = new MockHttpServletRequest("GET", "/api/quiz/subjects");
        request.setServletPath("/api/quiz/subjects");
        var principal = new TargetAuthenticatedPrincipal(4101, "redacted");
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(principal, null, List.of()));
        var limited = new SubjectReadRateLimiter.Decision(
                false, 60, 0, 30, 1_784_160_061L, "60 per 1 minute");
        var limitedResponse = new MockHttpServletResponse();
        FilterChain limitedChain = mock(FilterChain.class);
        when(limiter.acquire(SubjectReadRateLimiter.Route.SUBJECTS, 4101))
                .thenReturn(limited);

        filter.doFilter(request, limitedResponse, limitedChain);

        verify(errors).writeRateLimitHeaders(limitedResponse, limited);
        verify(errors).writeRateLimited(request, limitedResponse, limited);
        verify(limitedChain, never()).doFilter(request, limitedResponse);

        var unavailableResponse = new MockHttpServletResponse();
        FilterChain unavailableChain = mock(FilterChain.class);
        when(limiter.acquire(SubjectReadRateLimiter.Route.SUBJECTS, 4101))
                .thenThrow(new IllegalStateException("secret infrastructure detail"));

        filter.doFilter(request, unavailableResponse, unavailableChain);

        verify(errors).writeServiceUnavailable(request, unavailableResponse);
        verify(unavailableChain, never()).doFilter(request, unavailableResponse);
    }

    @Test
    void anonymousOrUnrelatedRequestsNeverConsumeSubjectBudgets() throws Exception {
        SubjectReadRateLimiter limiter = mock(SubjectReadRateLimiter.class);
        LegacySubjectSecurityErrorWriter errors = mock(LegacySubjectSecurityErrorWriter.class);
        SubjectReadRateLimitFilter filter = filter(limiter, errors);
        FilterChain anonymousChain = mock(FilterChain.class);
        var anonymous = new MockHttpServletRequest("GET", "/api/quiz/subjects");
        anonymous.setServletPath("/api/quiz/subjects");

        filter.doFilter(anonymous, new MockHttpServletResponse(), anonymousChain);

        verify(anonymousChain).doFilter(
                org.mockito.ArgumentMatchers.eq(anonymous),
                org.mockito.ArgumentMatchers.any());
        verifyNoInteractions(limiter, errors);

        FilterChain unrelatedChain = mock(FilterChain.class);
        var unrelated = new MockHttpServletRequest("GET", "/api/quiz/subjects/4201");
        unrelated.setServletPath("/api/quiz/subjects/4201");
        filter.doFilter(unrelated, new MockHttpServletResponse(), unrelatedChain);
        verify(unrelatedChain).doFilter(
                org.mockito.ArgumentMatchers.eq(unrelated),
                org.mockito.ArgumentMatchers.any());
        verifyNoInteractions(limiter, errors);

        FilterChain ambiguousChain = mock(FilterChain.class);
        var ambiguous = new MockHttpServletRequest(
                "GET", "/api/quiz/subjects%2fmeta");
        ambiguous.setServletPath("/api/quiz/subjects/meta");
        filter.doFilter(ambiguous, new MockHttpServletResponse(), ambiguousChain);
        verify(ambiguousChain).doFilter(
                org.mockito.ArgumentMatchers.eq(ambiguous),
                org.mockito.ArgumentMatchers.any());
        verifyNoInteractions(limiter, errors);
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
    }

    private static SubjectReadRateLimitFilter filter(
            SubjectReadRateLimiter limiter,
            LegacySubjectSecurityErrorWriter errors
    ) {
        return new SubjectReadRateLimitFilter(
                limiter,
                errors,
                new SubjectReadRequestResolver());
    }
}
