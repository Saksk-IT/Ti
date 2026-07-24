package io.saksk.ti.web.security;

import io.saksk.ti.web.compat.LegacyTransactionWriteSecurityErrorWriter;
import io.saksk.ti.web.security.TransactionWriteRequestResolver.Resolution;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Objects;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

public final class TransactionWriteRateLimitFilter extends OncePerRequestFilter {

    private final TransactionWriteRateLimiter limiter;
    private final TransactionWriteRequestResolver routes;
    private final ClientAddressResolver addresses;
    private final LegacyTransactionWriteSecurityErrorWriter errors;

    public TransactionWriteRateLimitFilter(
            TransactionWriteRateLimiter limiter,
            TransactionWriteRequestResolver routes,
            ClientAddressResolver addresses,
            LegacyTransactionWriteSecurityErrorWriter errors
    ) {
        this.limiter = Objects.requireNonNull(limiter, "limiter");
        this.routes = Objects.requireNonNull(routes, "routes");
        this.addresses = Objects.requireNonNull(addresses, "addresses");
        this.errors = Objects.requireNonNull(errors, "errors");
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return routes.resolve(request).isEmpty();
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        Resolution route = routes.resolve(request).orElseThrow();
        TransactionWriteRateLimiter.Decision decision;
        try {
            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
            if (authentication != null
                    && authentication.isAuthenticated()
                    && authentication.getPrincipal()
                            instanceof TargetAuthenticatedPrincipal principal
                    && principal.identityId() > 0) {
                decision = limiter.acquireForIdentity(
                        route.route(),
                        principal.identityId());
            } else {
                decision = limiter.acquireForAddress(
                        route.route(),
                        addresses.resolve(request));
            }
        } catch (RuntimeException exception) {
            errors.writeServiceUnavailable(request, response);
            return;
        }
        errors.writeRateHeaders(response, decision);
        if (!decision.allowed()) {
            errors.writeRateLimited(request, response, decision);
            return;
        }
        filterChain.doFilter(request, response);
    }
}
