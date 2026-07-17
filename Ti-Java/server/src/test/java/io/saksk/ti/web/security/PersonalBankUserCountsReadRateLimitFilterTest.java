package io.saksk.ti.web.security;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.same;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Decision;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter.Window;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import jakarta.servlet.FilterChain;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;

class PersonalBankUserCountsReadRateLimitFilterTest {

    private static final Decision ALLOWED =
            new Decision(true, Window.SECOND, 10, 9, 2, 1_784_260_802L);
    private static final Decision REJECTED =
            new Decision(false, Window.SECOND, 10, 0, 2, 1_784_260_802L);

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void apiEffectiveBearerPrincipalUsesItsIdentityDespiteAuthorizationHeader()
            throws Exception {
        Fixture fixture = fixture(Alias.API);
        installPrincipal(4202);
        fixture.request().addHeader("Authorization", "Bearer accepted");
        when(fixture.limiter().acquireForIdentity(Alias.API, 4202)).thenReturn(ALLOWED);

        fixture.filter().doFilter(fixture.request(), fixture.response(), fixture.chain());

        verify(fixture.limiter()).acquireForIdentity(Alias.API, 4202);
        verifyNoInteractions(fixture.addresses());
        verify(fixture.errors()).writeRateLimitHeaders(fixture.response(), ALLOWED);
        verify(fixture.chain()).doFilter(fixture.request(), fixture.response());
    }

    @Test
    void webAnyAuthorizationUsesTheTrustedAddressEvenWithAnInstalledPrincipal()
            throws Exception {
        Fixture fixture = fixture(Alias.WEB);
        installPrincipal(4202);
        fixture.request().addHeader("Authorization", "Bearer accepted-but-forbidden-on-web");
        when(fixture.addresses().resolve(fixture.request())).thenReturn("198.51.100.41");
        when(fixture.limiter().acquireForAddress(Alias.WEB, "198.51.100.41"))
                .thenReturn(ALLOWED);

        fixture.webAuthorizationFilter()
                .doFilter(fixture.request(), fixture.response(), fixture.chain());

        verify(fixture.limiter()).acquireForAddress(Alias.WEB, "198.51.100.41");
        verify(fixture.limiter(), never()).acquireForIdentity(Alias.WEB, 4202);
        verify(fixture.errors()).writeRateLimitHeaders(fixture.response(), ALLOWED);
        verify(fixture.errors()).writeAuthenticationRequired(
                fixture.request(), fixture.response(), Alias.WEB);
        verify(fixture.chain(), never()).doFilter(fixture.request(), fixture.response());
    }

    @Test
    void postAuthenticationLimiterSkipsWebAuthorizationHandledByTheEarlyBoundary()
            throws Exception {
        Fixture fixture = fixture(Alias.WEB);
        fixture.request().addHeader("Authorization", "not-even-a-bearer");

        fixture.filter().doFilter(fixture.request(), fixture.response(), fixture.chain());

        verify(fixture.chain()).doFilter(fixture.request(), fixture.response());
        verifyNoInteractions(fixture.limiter(), fixture.errors(), fixture.addresses());
    }

    @Test
    void webSessionPrincipalWithoutAuthorizationUsesItsIdentity() throws Exception {
        Fixture fixture = fixture(Alias.WEB);
        installPrincipal(4101);
        when(fixture.limiter().acquireForIdentity(Alias.WEB, 4101)).thenReturn(ALLOWED);

        fixture.filter().doFilter(fixture.request(), fixture.response(), fixture.chain());

        verify(fixture.limiter()).acquireForIdentity(Alias.WEB, 4101);
        verifyNoInteractions(fixture.addresses());
        verify(fixture.chain()).doFilter(fixture.request(), fixture.response());
    }

    @Test
    void anonymousOrRejectedCredentialUsesAddressAndStopsOn429() throws Exception {
        Fixture fixture = fixture(Alias.API);
        fixture.request().addHeader("Authorization", "Bearer rejected");
        when(fixture.addresses().resolve(fixture.request())).thenReturn("198.51.100.42");
        when(fixture.limiter().acquireForAddress(Alias.API, "198.51.100.42"))
                .thenReturn(REJECTED);

        fixture.filter().doFilter(fixture.request(), fixture.response(), fixture.chain());

        verify(fixture.errors()).writeRateLimitHeaders(fixture.response(), REJECTED);
        verify(fixture.errors()).writeRateLimited(
                fixture.request(), fixture.response(), Alias.API, REJECTED);
        verify(fixture.chain(), never()).doFilter(fixture.request(), fixture.response());
    }

    @Test
    void redisFailureFailsClosedWithoutInventingRateHeaders() throws Exception {
        Fixture fixture = fixture(Alias.WEB);
        when(fixture.addresses().resolve(fixture.request())).thenReturn("198.51.100.43");
        when(fixture.limiter().acquireForAddress(Alias.WEB, "198.51.100.43"))
                .thenThrow(new IllegalStateException("redis://secret-host"));

        fixture.filter().doFilter(fixture.request(), fixture.response(), fixture.chain());

        verify(fixture.errors()).writeServiceUnavailable(
                fixture.request(), fixture.response(), Alias.WEB);
        verify(fixture.errors(), never()).writeRateLimitHeaders(
                same(fixture.response()), any(Decision.class));
        verify(fixture.chain(), never()).doFilter(fixture.request(), fixture.response());
    }

    @Test
    void headConsumesTheSameBudgetWhileOptionsAndConverterMissSkipTheLimiter()
            throws Exception {
        Fixture head = fixture(Alias.API, "HEAD");
        installPrincipal(4101);
        when(head.limiter().acquireForIdentity(Alias.API, 4101)).thenReturn(ALLOWED);
        head.filter().doFilter(head.request(), head.response(), head.chain());
        verify(head.limiter()).acquireForIdentity(Alias.API, 4101);

        for (String method : List.of("OPTIONS", "GET")) {
            Fixture skipped = skippedFixture(method);
            skipped.filter().doFilter(skipped.request(), skipped.response(), skipped.chain());
            verify(skipped.chain()).doFilter(skipped.request(), skipped.response());
            verifyNoInteractions(skipped.limiter(), skipped.errors(), skipped.addresses());
        }
    }

    private static Fixture fixture(Alias alias) {
        return fixture(alias, "GET");
    }

    private static Fixture fixture(Alias alias, String method) {
        PersonalBankUserCountsReadRateLimiter limiter =
                mock(PersonalBankUserCountsReadRateLimiter.class);
        LegacyPersonalBankUserCountsSecurityErrorWriter errors =
                mock(LegacyPersonalBankUserCountsSecurityErrorWriter.class);
        PersonalBankUserCountsReadRequestResolver routes =
                new PersonalBankUserCountsReadRequestResolver();
        ClientAddressResolver addresses = mock(ClientAddressResolver.class);
        String path = alias == Alias.API
                ? "/api/user/banks/api/99551/user-counts"
                : "/user/banks/api/99551/user-counts";
        MockHttpServletRequest request = new MockHttpServletRequest(
                method, path);
        request.setServletPath(request.getRequestURI());
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        return new Fixture(
                new PersonalBankUserCountsReadRateLimitFilter(
                        limiter, errors, routes, addresses),
                new PersonalBankUserCountsReadRateLimitFilter.WebAuthorizationBoundaryFilter(
                        limiter, errors, routes, addresses),
                limiter,
                errors,
                addresses,
                request,
                response,
                chain);
    }

    private static Fixture skippedFixture(String method) {
        PersonalBankUserCountsReadRateLimiter limiter =
                mock(PersonalBankUserCountsReadRateLimiter.class);
        LegacyPersonalBankUserCountsSecurityErrorWriter errors =
                mock(LegacyPersonalBankUserCountsSecurityErrorWriter.class);
        PersonalBankUserCountsReadRequestResolver routes =
                new PersonalBankUserCountsReadRequestResolver();
        ClientAddressResolver addresses = mock(ClientAddressResolver.class);
        String bankSegment = method.equals("OPTIONS") ? "99551" : "not-an-int";
        MockHttpServletRequest request = new MockHttpServletRequest(
                method, "/api/user/banks/api/" + bankSegment + "/user-counts");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        return new Fixture(
                new PersonalBankUserCountsReadRateLimitFilter(
                        limiter, errors, routes, addresses),
                new PersonalBankUserCountsReadRateLimitFilter.WebAuthorizationBoundaryFilter(
                        limiter, errors, routes, addresses),
                limiter,
                errors,
                addresses,
                request,
                response,
                chain);
    }

    private static void installPrincipal(long identityId) {
        var principal = new TargetAuthenticatedPrincipal(identityId, "redacted");
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(principal, null, List.of()));
    }

    private record Fixture(
            PersonalBankUserCountsReadRateLimitFilter filter,
            PersonalBankUserCountsReadRateLimitFilter.WebAuthorizationBoundaryFilter
                    webAuthorizationFilter,
            PersonalBankUserCountsReadRateLimiter limiter,
            LegacyPersonalBankUserCountsSecurityErrorWriter errors,
            ClientAddressResolver addresses,
            MockHttpServletRequest request,
            MockHttpServletResponse response,
            FilterChain chain
    ) {
    }
}
