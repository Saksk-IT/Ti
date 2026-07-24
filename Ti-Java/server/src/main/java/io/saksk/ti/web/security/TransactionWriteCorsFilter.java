package io.saksk.ti.web.security;

import io.saksk.ti.web.compat.LegacyTransactionWriteSecurityErrorWriter;
import io.saksk.ti.web.security.TransactionWriteRequestResolver.Resolution;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.web.filter.OncePerRequestFilter;

/** Strict route-scoped CORS boundary for the Phase 4C transaction-write endpoints. */
public final class TransactionWriteCorsFilter extends OncePerRequestFilter {

    public static final String ALLOWED_ORIGINS_PROPERTY =
            "ti.security.transaction-write-cors.allowed-origins";

    private static final Set<String> DEVELOPMENT_PROFILES =
            Set.of("dev", "development", "local");
    private static final Set<String> DEVELOPMENT_ORIGINS = Set.of(
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "http://localhost:3000",
            "http://127.0.0.1:3000");
    private static final Set<String> ALLOWED_HEADERS = Set.of(
            "accept",
            "authorization",
            "content-type",
            "idempotency-key",
            "x-request-id",
            "x-requested-with");

    private final TransactionWriteRequestResolver routes;
    private final Set<String> allowedOrigins;

    public TransactionWriteCorsFilter(
            TransactionWriteRequestResolver routes,
            Environment environment
    ) {
        this.routes = Objects.requireNonNull(routes, "routes");
        environment = Objects.requireNonNull(environment, "environment");
        LinkedHashSet<String> origins = new LinkedHashSet<>();
        String configured = environment.getProperty(ALLOWED_ORIGINS_PROPERTY, "");
        if (configured != null) {
            Arrays.stream(configured.split(",", -1))
                    .map(String::strip)
                    .filter(value -> !value.isEmpty())
                    .forEach(value -> {
                        validateOrigin(value);
                        origins.add(value);
                    });
        }
        String[] profiles = environment.getActiveProfiles().length == 0
                ? environment.getDefaultProfiles()
                : environment.getActiveProfiles();
        if (Arrays.stream(profiles)
                .map(value -> value.toLowerCase(Locale.ROOT))
                .anyMatch(DEVELOPMENT_PROFILES::contains)) {
            origins.addAll(DEVELOPMENT_ORIGINS);
        }
        this.allowedOrigins = Set.copyOf(origins);
    }

    Set<String> allowedOrigins() {
        return allowedOrigins;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return routes.resolvePath(request).isEmpty();
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        Resolution resolution = routes.resolvePath(request).orElseThrow();
        LegacyTransactionWriteSecurityErrorWriter.mergeVary(response);
        String origin = request.getHeader(HttpHeaders.ORIGIN);
        if (origin != null) {
            if (!allowedOrigins.contains(origin)) {
                response.setStatus(HttpStatus.FORBIDDEN.value());
                return;
            }
            response.setHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, origin);
        }
        if (!HttpMethod.OPTIONS.matches(request.getMethod())) {
            filterChain.doFilter(request, response);
            return;
        }
        if (origin == null
                || !resolution.route().method().equals(
                        request.getHeader(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD))
                || !allowedRequestHeaders(request)) {
            response.setStatus(HttpStatus.FORBIDDEN.value());
            return;
        }
        response.setHeader(
                HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS,
                resolution.route().method() + ", OPTIONS");
        response.setHeader(
                HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS,
                "Accept, Authorization, Content-Type, Idempotency-Key, X-Request-ID, "
                        + "X-Requested-With");
        response.setStatus(HttpStatus.NO_CONTENT.value());
    }

    private static boolean allowedRequestHeaders(HttpServletRequest request) {
        String requested = request.getHeader(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS);
        if (requested == null || requested.isBlank()) {
            return true;
        }
        for (String raw : requested.split(",")) {
            if (!ALLOWED_HEADERS.contains(raw.strip().toLowerCase(Locale.ROOT))) {
                return false;
            }
        }
        return true;
    }

    private static void validateOrigin(String origin) {
        if (origin.equals("*")
                || origin.equalsIgnoreCase("null")
                || origin.indexOf('\r') >= 0
                || origin.indexOf('\n') >= 0) {
            throw new IllegalArgumentException("Unsafe transaction-write CORS origin");
        }
        try {
            URI parsed = new URI(origin);
            String scheme = parsed.getScheme();
            int port = parsed.getPort();
            if (!("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme))
                    || parsed.getHost() == null
                    || parsed.getRawUserInfo() != null
                    || parsed.getRawPath() != null && !parsed.getRawPath().isEmpty()
                    || parsed.getRawQuery() != null
                    || parsed.getRawFragment() != null
                    || port == 0
                    || port > 65_535) {
                throw new IllegalArgumentException(
                        "Unsafe transaction-write CORS origin");
            }
        } catch (URISyntaxException exception) {
            throw new IllegalArgumentException(
                    "Unsafe transaction-write CORS origin",
                    exception);
        }
    }
}
