package io.saksk.ti.web.security;

import io.saksk.ti.web.compat.LegacySubjectSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

public final class SubjectReadRateLimitFilter extends OncePerRequestFilter {

    private final SubjectReadRateLimiter rateLimiter;
    private final LegacySubjectSecurityErrorWriter errorWriter;
    private final SubjectReadRequestResolver routes;

    public SubjectReadRateLimitFilter(
            SubjectReadRateLimiter rateLimiter,
            LegacySubjectSecurityErrorWriter errorWriter,
            SubjectReadRequestResolver routes
    ) {
        this.rateLimiter = rateLimiter;
        this.errorWriter = errorWriter;
        this.routes = routes;
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
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null
                || !(authentication.getPrincipal() instanceof TargetAuthenticatedPrincipal principal)) {
            filterChain.doFilter(request, response);
            return;
        }

        SubjectReadRateLimiter.Decision decision;
        try {
            SubjectReadRateLimiter.Route route = routes.resolve(request)
                    .orElseThrow(() -> new IllegalStateException(
                            "Subject read route changed during request filtering"));
            decision = rateLimiter.acquire(route, principal.identityId());
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

}
