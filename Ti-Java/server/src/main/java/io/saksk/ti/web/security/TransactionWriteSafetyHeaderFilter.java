package io.saksk.ti.web.security;

import io.saksk.ti.web.compat.LegacyTransactionWriteSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Objects;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Preserves the legacy session-write safety boundary: Bearer requests are exempt while
 * authenticated Session requests must carry the exact XHR marker.
 */
public final class TransactionWriteSafetyHeaderFilter extends OncePerRequestFilter {

    private final TransactionWriteRequestResolver routes;
    private final LegacyTransactionWriteSecurityErrorWriter errors;

    public TransactionWriteSafetyHeaderFilter(
            TransactionWriteRequestResolver routes,
            LegacyTransactionWriteSecurityErrorWriter errors
    ) {
        this.routes = Objects.requireNonNull(routes, "routes");
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
        if (Boolean.TRUE.equals(request.getAttribute(
                        TargetSessionAuthenticationFilter
                                .LEGACY_BEARER_AUTHENTICATED_ATTRIBUTE))
                || "XMLHttpRequest".equals(request.getHeader("X-Requested-With"))
                || !hasTargetAuthentication()) {
            filterChain.doFilter(request, response);
            return;
        }
        errors.writeMissingSafetyHeader(request, response);
    }

    private static boolean hasTargetAuthentication() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        return authentication != null
                && authentication.isAuthenticated()
                && authentication.getPrincipal() instanceof TargetAuthenticatedPrincipal;
    }
}
