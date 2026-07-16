package io.saksk.ti.web.security;

import io.saksk.ti.web.compat.LegacyPublicBankSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

public final class PublicBankReadRateLimitFilter extends OncePerRequestFilter {

    private final PublicBankReadRateLimiter rateLimiter;
    private final LegacyPublicBankSecurityErrorWriter errorWriter;
    private final PublicBankReadRequestResolver routes;
    private final ClientAddressResolver clientAddresses;

    public PublicBankReadRateLimitFilter(
            PublicBankReadRateLimiter rateLimiter,
            LegacyPublicBankSecurityErrorWriter errorWriter,
            PublicBankReadRequestResolver routes,
            ClientAddressResolver clientAddresses
    ) {
        this.rateLimiter = rateLimiter;
        this.errorWriter = errorWriter;
        this.routes = routes;
        this.clientAddresses = clientAddresses;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return routes.resolveRateLimitedRoute(request).isEmpty();
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        PublicBankReadRateLimiter.Decision decision;
        try {
            PublicBankReadRequestResolver.Route route = routes.resolveRateLimitedRoute(request)
                    .orElseThrow(() -> new IllegalStateException(
                            "Public-bank route changed during request filtering"));
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (hasValidTargetPrincipal(authentication)) {
                TargetAuthenticatedPrincipal principal =
                        (TargetAuthenticatedPrincipal) authentication.getPrincipal();
                decision = rateLimiter.acquireForIdentity(route, principal.identityId());
            } else {
                decision = rateLimiter.acquireForAddress(
                        route,
                        clientAddresses.resolve(request));
            }
        } catch (RuntimeException exception) {
            errorWriter.writeServiceUnavailable(request, response);
            return;
        }

        errorWriter.writeRateLimitHeaders(response, decision);
        if (!decision.allowed()) {
            errorWriter.writeRateLimited(request, response, decision);
            return;
        }
        filterChain.doFilter(request, response);
    }

    private static boolean hasValidTargetPrincipal(Authentication authentication) {
        return authentication != null
                && authentication.isAuthenticated()
                && authentication.getPrincipal() instanceof TargetAuthenticatedPrincipal principal
                && principal.identityId() > 0;
    }
}
