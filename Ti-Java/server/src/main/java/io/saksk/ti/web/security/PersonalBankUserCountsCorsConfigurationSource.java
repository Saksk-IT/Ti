package io.saksk.ti.web.security;

import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.BankIdKind;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.CandidateKind;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Resolution;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.RouteCandidate;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.WriteListener;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpServletResponseWrapper;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.Writer;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

/**
 * Route-scoped CORS policy and pre-authentication boundary for the two user-counts aliases.
 *
 * <p>The filter is created explicitly by Spring Security and is deliberately not a component:
 * servlet-container auto-registration would place it outside {@code StrictHttpFirewall} and make
 * raw-path rejection order ambiguous.</p>
 */
public final class PersonalBankUserCountsCorsConfigurationSource
        implements CorsConfigurationSource {

    public static final String ALLOWED_ORIGINS_PROPERTY =
            "ti.security.personal-bank-user-counts-cors.allowed-origins";

    private static final String SERVICE_WECHAT_ORIGIN = "https://servicewechat.com";
    private static final Set<String> DEVELOPMENT_PROFILES = Set.of(
            "dev", "development", "local");
    private static final List<String> DEVELOPMENT_ORIGINS = List.of(
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "http://localhost:3000",
            "http://127.0.0.1:3000");
    private static final List<String> ALLOWED_METHODS = List.of(
            HttpMethod.GET.name(),
            HttpMethod.HEAD.name(),
            HttpMethod.OPTIONS.name());
    private static final Map<String, String> ALLOWED_REQUEST_HEADERS = Map.of(
            "content-type", HttpHeaders.CONTENT_TYPE,
            "authorization", HttpHeaders.AUTHORIZATION,
            "x-request-id", "X-Request-ID");
    private static final String ALLOW_VALUE = "GET, HEAD, OPTIONS";

    private final PersonalBankUserCountsReadRequestResolver routes;
    private final Set<String> allowedOrigins;

    public PersonalBankUserCountsCorsConfigurationSource(
            PersonalBankUserCountsReadRequestResolver routes,
            Environment environment
    ) {
        this(
                routes,
                Objects.requireNonNull(environment, "environment")
                        .getProperty(ALLOWED_ORIGINS_PROPERTY, ""),
                isDevelopment(environment));
    }

    public PersonalBankUserCountsCorsConfigurationSource(
            PersonalBankUserCountsReadRequestResolver routes,
            String configuredOrigins,
            boolean development
    ) {
        this.routes = Objects.requireNonNull(routes, "routes");
        LinkedHashSet<String> origins = new LinkedHashSet<>();
        origins.add(SERVICE_WECHAT_ORIGIN);
        addConfiguredOrigins(origins, configuredOrigins);
        if (development) {
            origins.addAll(DEVELOPMENT_ORIGINS);
        }
        this.allowedOrigins = Set.copyOf(origins);
    }

    @Override
    public CorsConfiguration getCorsConfiguration(HttpServletRequest request) {
        Optional<Resolution> resolution = converterValidResolution(request);
        if (resolution.isEmpty() || resolution.orElseThrow().alias() != Alias.API) {
            return null;
        }
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(new ArrayList<>(allowedOrigins));
        configuration.setAllowedMethods(ALLOWED_METHODS);
        configuration.setAllowedHeaders(new ArrayList<>(ALLOWED_REQUEST_HEADERS.values()));
        configuration.setAllowCredentials(false);
        return configuration;
    }

    public Filter securityFilter(
            LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter
    ) {
        return new RouteBoundaryFilter(
                this,
                routes,
                Objects.requireNonNull(errorWriter, "errorWriter"));
    }

    Set<String> allowedOrigins() {
        return allowedOrigins;
    }

    private Optional<Resolution> converterValidResolution(HttpServletRequest request) {
        Optional<Resolution> read = routes.resolveRead(request);
        if (read.isPresent()) {
            return read.filter(PersonalBankUserCountsCorsConfigurationSource::converterValid);
        }
        return routes.resolveBareOptions(request)
                .filter(PersonalBankUserCountsCorsConfigurationSource::converterValid);
    }

    private static boolean converterValid(Resolution resolution) {
        return resolution.bankIdKind() != BankIdKind.CONVERTER_MISS;
    }

    private static boolean isDevelopment(Environment environment) {
        String[] profiles = environment.getActiveProfiles();
        if (profiles.length == 0) {
            profiles = environment.getDefaultProfiles();
        }
        return Arrays.stream(profiles)
                .map(profile -> profile.toLowerCase(Locale.ROOT))
                .anyMatch(DEVELOPMENT_PROFILES::contains);
    }

    private static void addConfiguredOrigins(
            Set<String> origins,
            String configuredOrigins
    ) {
        if (configuredOrigins == null || configuredOrigins.isBlank()) {
            return;
        }
        for (String rawOrigin : configuredOrigins.split(",", -1)) {
            String origin = rawOrigin.strip();
            if (origin.isEmpty()) {
                continue;
            }
            validateOrigin(origin);
            origins.add(origin);
        }
    }

    private static void validateOrigin(String origin) {
        if (origin.equals("*")
                || origin.equalsIgnoreCase("null")
                || origin.indexOf('\r') >= 0
                || origin.indexOf('\n') >= 0) {
            throw new IllegalArgumentException("Unsafe user-counts CORS origin");
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
                throw new IllegalArgumentException("Unsafe user-counts CORS origin");
            }
        } catch (URISyntaxException exception) {
            throw new IllegalArgumentException("Unsafe user-counts CORS origin", exception);
        }
    }

    private static final class RouteBoundaryFilter extends CorsFilter {

        private final PersonalBankUserCountsCorsConfigurationSource source;
        private final PersonalBankUserCountsReadRequestResolver routes;
        private final LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter;

        private RouteBoundaryFilter(
                PersonalBankUserCountsCorsConfigurationSource source,
                PersonalBankUserCountsReadRequestResolver routes,
                LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter
        ) {
            super(source);
            this.source = source;
            this.routes = routes;
            this.errorWriter = errorWriter;
        }

        @Override
        protected void doFilterInternal(
                HttpServletRequest request,
                HttpServletResponse response,
                FilterChain filterChain
        ) throws ServletException, IOException {
            Optional<RouteCandidate> candidate = routes.resolveCandidate(request);
            if (candidate.isEmpty()) {
                filterChain.doFilter(request, response);
                return;
            }

            RouteCandidate route = candidate.orElseThrow();
            HttpServletResponse downstream = HttpMethod.HEAD.matches(request.getMethod())
                    ? new HeadBodySuppressingResponse(response)
                    : response;
            LegacyPersonalBankUserCountsSecurityErrorWriter.mergeVary(
                    downstream,
                    route.alias());

            if (route.kind() == CandidateKind.NEAR_MISS) {
                errorWriter.writeNotFound(request, downstream, route.alias());
                return;
            }

            Optional<Resolution> read = routes.resolveRead(request);
            if (read.isPresent()
                    && read.orElseThrow().bankIdKind() == BankIdKind.CONVERTER_MISS) {
                errorWriter.writeNotFound(request, downstream, route.alias());
                return;
            }

            Optional<Resolution> options = routes.resolveOptions(request);
            if (options.isPresent()) {
                Resolution option = options.orElseThrow();
                if (option.bankIdKind() == BankIdKind.CONVERTER_MISS) {
                    errorWriter.writeNotFound(request, downstream, option.alias());
                    return;
                }
                handleOptions(request, downstream, option);
                return;
            }

            if (route.alias() == Alias.API && hasHeader(request, HttpHeaders.ORIGIN)) {
                HeaderValue origin = singleHeader(request, HttpHeaders.ORIGIN, false);
                if (!origin.valid() || !source.allowedOrigins.contains(origin.value())) {
                    reject(downstream);
                    return;
                }
                downstream.setHeader(
                        HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN,
                        origin.value());
            }
            try {
                filterChain.doFilter(request, downstream);
            } catch (RuntimeException exception) {
                if (!downstream.isCommitted()
                        && request.getAttribute(
                                PersonalBankUserCountsReadRateLimitFilter
                                        .BOUNDARY_ENTERED_ATTRIBUTE) == null) {
                    downstream.resetBuffer();
                    errorWriter.writeServiceUnavailable(
                            request,
                            downstream,
                            route.alias());
                    return;
                }
                throw exception;
            }
        }

        private void handleOptions(
                HttpServletRequest request,
                HttpServletResponse response,
                Resolution resolution
        ) {
            response.setHeader(HttpHeaders.ALLOW, ALLOW_VALUE);
            if (resolution.alias() == Alias.WEB) {
                noContent(response);
                return;
            }

            boolean corsSignal = hasHeader(request, HttpHeaders.ORIGIN)
                    || hasHeader(request, HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD)
                    || hasHeader(request, HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS);
            if (!corsSignal) {
                noContent(response);
                return;
            }

            LegacyPersonalBankUserCountsSecurityErrorWriter.mergeVaryTokens(
                    response,
                    "Origin",
                    "Cookie",
                    HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD,
                    HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS);
            HeaderValue origin = singleHeader(request, HttpHeaders.ORIGIN, false);
            HeaderValue method = singleHeader(
                    request,
                    HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD,
                    false);
            Optional<List<String>> requestedHeaders = requestedHeaders(request);
            if (!origin.valid()
                    || !source.allowedOrigins.contains(origin.value())
                    || !method.valid()
                    || !(HttpMethod.GET.matches(method.value())
                            || HttpMethod.HEAD.matches(method.value()))
                    || requestedHeaders.isEmpty()) {
                reject(response);
                return;
            }

            response.setHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, origin.value());
            response.setHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS, ALLOW_VALUE);
            List<String> headers = requestedHeaders.orElseThrow();
            if (!headers.isEmpty()) {
                response.setHeader(
                        HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS,
                        String.join(", ", headers));
            }
            noContent(response);
        }

        private static Optional<List<String>> requestedHeaders(HttpServletRequest request) {
            if (!hasHeader(request, HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS)) {
                return Optional.of(List.of());
            }
            HeaderValue raw = singleHeader(
                    request,
                    HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS,
                    true);
            if (!raw.valid()) {
                return Optional.empty();
            }
            if (raw.value().isBlank()) {
                return Optional.of(List.of());
            }
            LinkedHashMap<String, String> headers = new LinkedHashMap<>();
            for (String token : raw.value().split(",", -1)) {
                String normalized = token.strip().toLowerCase(Locale.ROOT);
                String allowed = ALLOWED_REQUEST_HEADERS.get(normalized);
                if (normalized.isEmpty() || allowed == null) {
                    return Optional.empty();
                }
                headers.putIfAbsent(normalized, allowed);
            }
            return Optional.of(List.copyOf(headers.values()));
        }

        private static HeaderValue singleHeader(
                HttpServletRequest request,
                String name,
                boolean allowBlank
        ) {
            Enumeration<String> values = request.getHeaders(name);
            if (values == null || !values.hasMoreElements()) {
                return HeaderValue.missing();
            }
            String value = values.nextElement();
            if (values.hasMoreElements()
                    || value == null
                    || !value.equals(value.strip())
                    || !allowBlank && value.isBlank()) {
                return HeaderValue.invalid();
            }
            return HeaderValue.present(value);
        }

        private static boolean hasHeader(HttpServletRequest request, String name) {
            Enumeration<String> values = request.getHeaders(name);
            return values != null && values.hasMoreElements();
        }

        private static void noContent(HttpServletResponse response) {
            response.setStatus(HttpStatus.NO_CONTENT.value());
            response.setContentLength(0);
        }

        private static void reject(HttpServletResponse response) {
            response.setStatus(HttpStatus.FORBIDDEN.value());
            response.setContentLength(0);
        }
    }

    private record HeaderValue(boolean present, boolean valid, String value) {
        private static HeaderValue missing() {
            return new HeaderValue(false, false, "");
        }

        private static HeaderValue invalid() {
            return new HeaderValue(true, false, "");
        }

        private static HeaderValue present(String value) {
            return new HeaderValue(true, true, value);
        }
    }

    private static final class HeadBodySuppressingResponse
            extends HttpServletResponseWrapper {

        private final ServletOutputStream outputStream = new NullServletOutputStream();
        private PrintWriter writer;
        private boolean outputStreamRequested;
        private boolean writerRequested;

        private HeadBodySuppressingResponse(HttpServletResponse response) {
            super(response);
        }

        @Override
        public ServletOutputStream getOutputStream() {
            if (writerRequested) {
                throw new IllegalStateException("getWriter() has already been called");
            }
            outputStreamRequested = true;
            return outputStream;
        }

        @Override
        public PrintWriter getWriter() {
            if (outputStreamRequested) {
                throw new IllegalStateException("getOutputStream() has already been called");
            }
            writerRequested = true;
            if (writer == null) {
                writer = new PrintWriter(Writer.nullWriter());
            }
            return writer;
        }

        @Override
        public void sendError(int status) {
            setStatus(status);
        }

        @Override
        public void sendError(int status, String message) {
            setStatus(status);
        }

        @Override
        public void sendRedirect(String location) {
            setStatus(HttpStatus.FOUND.value());
            setHeader(HttpHeaders.LOCATION, encodeRedirectURL(location));
        }
    }

    private static final class NullServletOutputStream extends ServletOutputStream {

        @Override
        public boolean isReady() {
            return true;
        }

        @Override
        public void setWriteListener(WriteListener writeListener) {
            // Writes are intentionally discarded for HEAD while headers and status pass through.
        }

        @Override
        public void write(int value) {
            // Discard the body byte.
        }

        @Override
        public void write(byte[] bytes, int offset, int length) {
            // Discard the body bytes.
        }
    }
}
