package io.saksk.ti.web.security;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.web.compat.LegacyPublicBankSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

class PublicBankReadRateLimitFilterTest {

    private static final PublicBankReadRateLimiter.Decision ALLOWED =
            new PublicBankReadRateLimiter.Decision(
                    true, 10, 9, 2, 1_784_174_402L, "10 per 1 second");
    private static final PublicBankReadRateLimiter.Decision REJECTED =
            new PublicBankReadRateLimiter.Decision(
                    false, 10, 0, 2, 1_784_174_402L, "10 per 1 second");

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void validTargetPrincipalTakesPriorityOverTheResolvedClientAddress() throws Exception {
        PublicBankReadRateLimiter limiter = mock(PublicBankReadRateLimiter.class);
        LegacyPublicBankSecurityErrorWriter errors =
                mock(LegacyPublicBankSecurityErrorWriter.class);
        ClientAddressResolver addresses = mock(ClientAddressResolver.class);
        PublicBankReadRateLimitFilter filter = filter(limiter, errors, addresses);
        var principal = new TargetAuthenticatedPrincipal(4101, "redacted");
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(principal, null, List.of()));
        var request = request("/api/public/banks/summary");
        var response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        when(limiter.acquireForIdentity(
                PublicBankReadRequestResolver.Route.SUMMARY, 4101)).thenReturn(ALLOWED);

        filter.doFilter(request, response, chain);

        verify(limiter).acquireForIdentity(
                PublicBankReadRequestResolver.Route.SUMMARY, 4101);
        verifyNoInteractions(addresses);
        verify(errors).writeRateLimitHeaders(response, ALLOWED);
        verify(chain).doFilter(request, response);
    }

    @Test
    void anonymousReadUsesTrustedProxyAddressAndStopsOn429() throws Exception {
        PublicBankReadRateLimiter limiter = mock(PublicBankReadRateLimiter.class);
        LegacyPublicBankSecurityErrorWriter errors =
                mock(LegacyPublicBankSecurityErrorWriter.class);
        ClientAddressResolver addresses = mock(ClientAddressResolver.class);
        PublicBankReadRateLimitFilter filter = filter(limiter, errors, addresses);
        var request = request("/api/public/banks/card/user/5401");
        var response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        when(addresses.resolve(request)).thenReturn("198.51.100.41");
        when(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.CARD_DETAIL,
                "198.51.100.41")).thenReturn(REJECTED);

        filter.doFilter(request, response, chain);

        verify(errors).writeRateLimitHeaders(response, REJECTED);
        verify(errors).writeRateLimited(request, response, REJECTED);
        verify(chain, never()).doFilter(request, response);
    }

    @Test
    void redisFailureFailsClosedBeforeTheController() throws Exception {
        PublicBankReadRateLimiter limiter = mock(PublicBankReadRateLimiter.class);
        LegacyPublicBankSecurityErrorWriter errors =
                mock(LegacyPublicBankSecurityErrorWriter.class);
        ClientAddressResolver addresses = mock(ClientAddressResolver.class);
        PublicBankReadRateLimitFilter filter = filter(limiter, errors, addresses);
        var request = request("/api/public/banks/boards");
        var response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        when(addresses.resolve(request)).thenReturn("198.51.100.42");
        when(limiter.acquireForAddress(
                PublicBankReadRequestResolver.Route.BOARDS,
                "198.51.100.42"))
                .thenThrow(new IllegalStateException("redis://secret-host"));

        filter.doFilter(request, response, chain);

        verify(errors).writeServiceUnavailable(request, response);
        verify(chain, never()).doFilter(request, response);
    }

    @Test
    void converter404AndUnrelatedPathsNeverConsumeABudget() throws Exception {
        PublicBankReadRateLimiter limiter = mock(PublicBankReadRateLimiter.class);
        LegacyPublicBankSecurityErrorWriter errors =
                mock(LegacyPublicBankSecurityErrorWriter.class);
        ClientAddressResolver addresses = mock(ClientAddressResolver.class);
        PublicBankReadRateLimitFilter filter = filter(limiter, errors, addresses);

        for (String path : List.of(
                "/api/public/banks/-1",
                "/api/public/banks/not-an-int",
                "/api/public/banks/card/user/-1",
                "/api/public/banks/card/user/not-an-int",
                "/api/public/banks/joined")) {
            var request = request(path);
            var response = new MockHttpServletResponse();
            FilterChain chain = mock(FilterChain.class);
            filter.doFilter(request, response, chain);
            verify(chain).doFilter(request, response);
        }

        verifyNoInteractions(limiter, errors, addresses);
    }

    private static PublicBankReadRateLimitFilter filter(
            PublicBankReadRateLimiter limiter,
            LegacyPublicBankSecurityErrorWriter errors,
            ClientAddressResolver addresses
    ) {
        return new PublicBankReadRateLimitFilter(
                limiter,
                errors,
                new PublicBankReadRequestResolver(),
                addresses);
    }

    private static MockHttpServletRequest request(String path) {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", path);
        request.setServletPath(path);
        return request;
    }
}
