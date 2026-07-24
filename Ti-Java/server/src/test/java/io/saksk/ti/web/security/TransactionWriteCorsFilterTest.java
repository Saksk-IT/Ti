package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import jakarta.servlet.FilterChain;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class TransactionWriteCorsFilterTest {

    private final TransactionWriteRequestResolver routes =
            new TransactionWriteRequestResolver();

    @Test
    void configuredOriginsAreExactSafeAndDevelopmentOriginsAreProfileScoped() {
        MockEnvironment production = new MockEnvironment()
                .withProperty(
                        TransactionWriteCorsFilter.ALLOWED_ORIGINS_PROPERTY,
                        "https://app.example,https://admin.example:8443");
        production.setActiveProfiles("prod");
        TransactionWriteCorsFilter productionFilter =
                new TransactionWriteCorsFilter(routes, production);
        assertThat(productionFilter.allowedOrigins()).containsExactlyInAnyOrder(
                "https://app.example",
                "https://admin.example:8443");

        MockEnvironment local = new MockEnvironment();
        local.setActiveProfiles("local");
        assertThat(new TransactionWriteCorsFilter(routes, local).allowedOrigins())
                .containsExactlyInAnyOrder(
                        "http://localhost:5000",
                        "http://127.0.0.1:5000",
                        "http://localhost:3000",
                        "http://127.0.0.1:3000");

        for (String unsafe : List.of(
                "*",
                "null",
                "https://user@example.com",
                "https://example.com/path",
                "https://example.com?query=1",
                "https://example.com#fragment",
                "file://example.com",
                "https://example.com:99999")) {
            MockEnvironment environment = new MockEnvironment()
                    .withProperty(
                            TransactionWriteCorsFilter.ALLOWED_ORIGINS_PROPERTY,
                            unsafe);
            environment.setActiveProfiles("prod");
            assertThatThrownBy(() ->
                    new TransactionWriteCorsFilter(routes, environment))
                    .as(unsafe)
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessage("Unsafe transaction-write CORS origin");
        }
    }

    @Test
    void exactWriteRouteAllowsConfiguredOriginAndRejectsEveryOtherOrigin()
            throws Exception {
        MockEnvironment environment = new MockEnvironment()
                .withProperty(
                        TransactionWriteCorsFilter.ALLOWED_ORIGINS_PROPERTY,
                        "https://app.example");
        environment.setActiveProfiles("prod");
        TransactionWriteCorsFilter filter =
                new TransactionWriteCorsFilter(routes, environment);

        MockHttpServletRequest allowed =
                new MockHttpServletRequest("POST", "/api/favorite");
        allowed.addHeader(HttpHeaders.ORIGIN, "https://app.example");
        MockHttpServletResponse allowedResponse = new MockHttpServletResponse();
        FilterChain allowedChain = mock(FilterChain.class);

        filter.doFilter(allowed, allowedResponse, allowedChain);

        verify(allowedChain).doFilter(allowed, allowedResponse);
        assertThat(allowedResponse.getHeader(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                .isEqualTo("https://app.example");
        assertThat(allowedResponse.getHeader(
                HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS))
                .isNull();
        assertThat(allowedResponse.getHeader(HttpHeaders.VARY))
                .isEqualTo("Origin, Cookie");

        MockHttpServletRequest rejected =
                new MockHttpServletRequest("POST", "/api/favorite");
        rejected.addHeader(HttpHeaders.ORIGIN, "https://evil.example");
        MockHttpServletResponse rejectedResponse = new MockHttpServletResponse();
        FilterChain rejectedChain = mock(FilterChain.class);

        filter.doFilter(rejected, rejectedResponse, rejectedChain);

        verify(rejectedChain, never()).doFilter(rejected, rejectedResponse);
        assertThat(rejectedResponse.getStatus()).isEqualTo(403);
        assertThat(rejectedResponse.getContentAsByteArray()).isEmpty();
        assertThat(rejectedResponse.getHeader(
                HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isNull();
    }

    @Test
    void preflightRequiresTheExactRouteMethodAndAnAllowedHeaderSubset()
            throws Exception {
        MockEnvironment environment = new MockEnvironment()
                .withProperty(
                        TransactionWriteCorsFilter.ALLOWED_ORIGINS_PROPERTY,
                        "https://app.example");
        environment.setActiveProfiles("prod");
        TransactionWriteCorsFilter filter =
                new TransactionWriteCorsFilter(routes, environment);

        MockHttpServletRequest valid =
                new MockHttpServletRequest("OPTIONS", "/api/quiz/questions/42");
        valid.addHeader(HttpHeaders.ORIGIN, "https://app.example");
        valid.addHeader(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "PUT");
        valid.addHeader(
                HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS,
                "Content-Type, Idempotency-Key, X-Requested-With");
        MockHttpServletResponse validResponse = new MockHttpServletResponse();
        FilterChain validChain = mock(FilterChain.class);

        filter.doFilter(valid, validResponse, validChain);

        verify(validChain, never()).doFilter(valid, validResponse);
        assertThat(validResponse.getStatus()).isEqualTo(204);
        assertThat(validResponse.getHeader(
                HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS))
                .isEqualTo("PUT, OPTIONS");

        for (InvalidPreflight invalid : List.of(
                new InvalidPreflight("https://evil.example", "PUT", "Content-Type"),
                new InvalidPreflight("https://app.example", "POST", "Content-Type"),
                new InvalidPreflight("https://app.example", "PUT", "X-Evil"))) {
            MockHttpServletRequest request = new MockHttpServletRequest(
                    "OPTIONS",
                    "/api/quiz/questions/42");
            request.addHeader(HttpHeaders.ORIGIN, invalid.origin());
            request.addHeader(
                    HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD,
                    invalid.method());
            request.addHeader(
                    HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS,
                    invalid.headers());
            MockHttpServletResponse response = new MockHttpServletResponse();
            FilterChain chain = mock(FilterChain.class);

            filter.doFilter(request, response, chain);

            verify(chain, never()).doFilter(request, response);
            assertThat(response.getStatus()).as(invalid.toString()).isEqualTo(403);
            assertThat(response.getContentAsByteArray()).isEmpty();
        }
    }

    private record InvalidPreflight(
            String origin,
            String method,
            String headers
    ) {}
}
