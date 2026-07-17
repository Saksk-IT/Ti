package io.saksk.ti.web.security;

import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Resolution;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Enumeration;
import java.util.Objects;
import org.springframework.http.HttpHeaders;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

public final class PersonalBankUserCountsReadRateLimitFilter extends OncePerRequestFilter {

    public static final String BOUNDARY_ENTERED_ATTRIBUTE =
            PersonalBankUserCountsReadRateLimitFilter.class.getName() + ".entered";

    private final PersonalBankUserCountsReadRateLimiter rateLimiter;
    private final LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter;
    private final PersonalBankUserCountsReadRequestResolver routes;
    private final ClientAddressResolver clientAddresses;

    public PersonalBankUserCountsReadRateLimitFilter(
            PersonalBankUserCountsReadRateLimiter rateLimiter,
            LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter,
            PersonalBankUserCountsReadRequestResolver routes,
            ClientAddressResolver clientAddresses
    ) {
        this.rateLimiter = Objects.requireNonNull(rateLimiter, "rateLimiter");
        this.errorWriter = Objects.requireNonNull(errorWriter, "errorWriter");
        this.routes = Objects.requireNonNull(routes, "routes");
        this.clientAddresses = Objects.requireNonNull(clientAddresses, "clientAddresses");
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return routes.resolveRateLimitedRoute(request)
                .filter(resolution -> !(resolution.alias() == Alias.WEB
                        && hasAnyAuthorizationHeader(request)))
                .isEmpty();
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        Resolution resolution = routes.resolveRateLimitedRoute(request)
                .orElseThrow(() -> new IllegalStateException(
                        "User-counts route changed during request filtering"));
        request.setAttribute(BOUNDARY_ENTERED_ATTRIBUTE, Boolean.TRUE);
        Alias alias = resolution.alias();
        PersonalBankUserCountsReadRateLimiter.Decision decision;
        try {
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (usesEffectiveIdentity(alias, request, authentication)) {
                TargetAuthenticatedPrincipal principal =
                        (TargetAuthenticatedPrincipal) authentication.getPrincipal();
                decision = rateLimiter.acquireForIdentity(alias, principal.identityId());
            } else {
                decision = rateLimiter.acquireForAddress(
                        alias,
                        clientAddresses.resolve(request));
            }
        } catch (RuntimeException exception) {
            errorWriter.writeServiceUnavailable(request, response, alias);
            return;
        }

        errorWriter.writeRateLimitHeaders(response, decision);
        if (!decision.allowed()) {
            errorWriter.writeRateLimited(request, response, alias, decision);
            return;
        }
        filterChain.doFilter(request, response);
    }

    private static boolean usesEffectiveIdentity(
            Alias alias,
            HttpServletRequest request,
            Authentication authentication
    ) {
        if (alias == Alias.WEB && hasAnyAuthorizationHeader(request)) {
            return false;
        }
        return authentication != null
                && authentication.isAuthenticated()
                && authentication.getPrincipal() instanceof TargetAuthenticatedPrincipal principal
                && principal.identityId() > 0;
    }

    private static boolean hasAnyAuthorizationHeader(HttpServletRequest request) {
        Enumeration<String> values = request.getHeaders(HttpHeaders.AUTHORIZATION);
        return values != null && values.hasMoreElements();
    }

    /**
     * Terminates Web-alias requests carrying any Authorization header before the global target
     * authentication filter can inspect a Bearer credential.  The legacy endpoint still charges
     * the Web/IP budget first, but Web authentication remains Session-only.
     */
    public static final class WebAuthorizationBoundaryFilter extends OncePerRequestFilter {

        private final PersonalBankUserCountsReadRateLimiter rateLimiter;
        private final LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter;
        private final PersonalBankUserCountsReadRequestResolver routes;
        private final ClientAddressResolver clientAddresses;

        public WebAuthorizationBoundaryFilter(
                PersonalBankUserCountsReadRateLimiter rateLimiter,
                LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter,
                PersonalBankUserCountsReadRequestResolver routes,
                ClientAddressResolver clientAddresses
        ) {
            this.rateLimiter = Objects.requireNonNull(rateLimiter, "rateLimiter");
            this.errorWriter = Objects.requireNonNull(errorWriter, "errorWriter");
            this.routes = Objects.requireNonNull(routes, "routes");
            this.clientAddresses = Objects.requireNonNull(clientAddresses, "clientAddresses");
        }

        @Override
        protected boolean shouldNotFilter(HttpServletRequest request) {
            return routes.resolveRateLimitedRoute(request)
                    .filter(resolution -> resolution.alias() == Alias.WEB)
                    .filter(resolution -> hasAnyAuthorizationHeader(request))
                    .isEmpty();
        }

        @Override
        protected void doFilterInternal(
                HttpServletRequest request,
                HttpServletResponse response,
                FilterChain filterChain
        ) throws IOException {
            PersonalBankUserCountsReadRateLimiter.Decision decision;
            try {
                decision = rateLimiter.acquireForAddress(
                        Alias.WEB,
                        clientAddresses.resolve(request));
            } catch (RuntimeException exception) {
                errorWriter.writeServiceUnavailable(request, response, Alias.WEB);
                return;
            }

            errorWriter.writeRateLimitHeaders(response, decision);
            if (!decision.allowed()) {
                errorWriter.writeRateLimited(request, response, Alias.WEB, decision);
                return;
            }
            errorWriter.writeAuthenticationRequired(request, response, Alias.WEB);
        }
    }
}
