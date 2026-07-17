package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import io.saksk.ti.web.compat.LegacyPersonalBankUserCountsSecurityErrorWriter;
import io.saksk.ti.web.request.RequestId;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletResponse;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import tools.jackson.databind.ObjectMapper;

class PersonalBankUserCountsCorsConfigurationSourceTest {

    private final PersonalBankUserCountsReadRequestResolver routes =
            new PersonalBankUserCountsReadRequestResolver();
    private final PersonalBankUserCountsCorsConfigurationSource source =
            new PersonalBankUserCountsCorsConfigurationSource(
                    routes,
                    "https://app.example,https://admin.example:8443",
                    true);
    private final Filter filter = source.securityFilter(
            new LegacyPersonalBankUserCountsSecurityErrorWriter(new ObjectMapper()));

    @Test
    void originSetIsExplicitSafeAndDevelopmentProfileScoped() {
        assertThat(source.allowedOrigins()).containsExactlyInAnyOrder(
                "https://servicewechat.com",
                "https://app.example",
                "https://admin.example:8443",
                "http://localhost:5000",
                "http://127.0.0.1:5000",
                "http://localhost:3000",
                "http://127.0.0.1:3000");
        assertThat(new PersonalBankUserCountsCorsConfigurationSource(
                routes, "", false).allowedOrigins())
                .containsExactly("https://servicewechat.com");
        for (String unsafe : List.of(
                "*", "null", "https://user@example.com", "https://example.com/path",
                "https://example.com?query=1", "https://example.com#fragment",
                "file://example.com", "https://example.com:99999")) {
            assertThatThrownBy(() -> new PersonalBankUserCountsCorsConfigurationSource(
                    routes, unsafe, false))
                    .as(unsafe)
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void apiSimpleCorsAllowsOnlyConfiguredOriginsBeforeTheDownstreamChain() throws Exception {
        MockHttpServletRequest allowed = request(
                "GET", "/api/user/banks/api/41/user-counts");
        allowed.addHeader(HttpHeaders.ORIGIN, "https://app.example");
        MockHttpServletResponse allowedResponse = new MockHttpServletResponse();
        FilterChain allowedChain = mock(FilterChain.class);

        filter.doFilter(allowed, allowedResponse, allowedChain);

        verify(allowedChain).doFilter(allowed, allowedResponse);
        assertThat(allowedResponse.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                .isEqualTo("https://app.example");
        assertThat(allowedResponse.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS))
                .isNull();
        assertThat(vary(allowedResponse)).containsExactlyInAnyOrder("Origin", "Cookie");

        MockHttpServletRequest rejected = request(
                "GET", "/api/user/banks/api/41/user-counts");
        rejected.addHeader(HttpHeaders.ORIGIN, "https://evil.example");
        MockHttpServletResponse rejectedResponse = new MockHttpServletResponse();
        FilterChain rejectedChain = mock(FilterChain.class);

        filter.doFilter(rejected, rejectedResponse, rejectedChain);

        verify(rejectedChain, never()).doFilter(rejected, rejectedResponse);
        assertThat(rejectedResponse.getStatus()).isEqualTo(403);
        assertThat(rejectedResponse.getContentAsByteArray()).isEmpty();
        assertThat(rejectedResponse.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isNull();
    }

    @Test
    void webAliasNeverEmitsCorsHeadersEvenWhenAnOriginIsPresent() throws Exception {
        MockHttpServletRequest request = request(
                "GET", "/user/banks/api/41/user-counts");
        request.addHeader(HttpHeaders.ORIGIN, "https://evil.example");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(request, response);
        assertThat(response.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isNull();
        assertThat(vary(response)).containsExactly("Cookie");
    }

    @Test
    void validPreflightIs204AndEchoesOnlyTheRequestedAllowedHeaderSubset()
            throws Exception {
        MockHttpServletRequest request = request(
                "OPTIONS", "/api/user/banks/api/2147483648/user-counts");
        request.addHeader(HttpHeaders.ORIGIN, "https://servicewechat.com");
        request.addHeader(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "HEAD");
        request.addHeader(
                HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS,
                "authorization, X-REQUEST-ID");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        filter.doFilter(request, response, chain);

        verify(chain, never()).doFilter(request, response);
        assertThat(response.getStatus()).isEqualTo(204);
        assertThat(response.getContentAsByteArray()).isEmpty();
        assertThat(response.getHeader(HttpHeaders.ALLOW)).isEqualTo("GET, HEAD, OPTIONS");
        assertThat(response.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN))
                .isEqualTo("https://servicewechat.com");
        assertThat(response.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS))
                .isEqualTo("GET, HEAD, OPTIONS");
        assertThat(response.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS))
                .isEqualTo("Authorization, X-Request-ID");
        assertThat(vary(response)).containsExactlyInAnyOrder(
                "Origin", "Cookie", "Access-Control-Request-Method",
                "Access-Control-Request-Headers");
    }

    @Test
    void malformedPreflightVariantsAreEmpty403s() throws Exception {
        for (Preflight invalid : List.of(
                new Preflight("https://evil.example", "GET", "Authorization"),
                new Preflight("https://app.example", "POST", "Authorization"),
                new Preflight("https://app.example", "OPTIONS", "Authorization"),
                new Preflight("https://app.example", "GET", "X-Evil"),
                new Preflight("", "GET", "Authorization"),
                new Preflight("https://app.example", "", "Authorization"))) {
            MockHttpServletRequest request = request(
                    "OPTIONS", "/api/user/banks/api/41/user-counts");
            if (!invalid.origin().isEmpty()) {
                request.addHeader(HttpHeaders.ORIGIN, invalid.origin());
            }
            if (!invalid.method().isEmpty()) {
                request.addHeader(
                        HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD,
                        invalid.method());
            }
            request.addHeader(
                    HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS,
                    invalid.headers());
            MockHttpServletResponse response = new MockHttpServletResponse();
            FilterChain chain = mock(FilterChain.class);

            filter.doFilter(request, response, chain);

            assertThat(response.getStatus()).as(invalid.toString()).isEqualTo(403);
            assertThat(response.getContentAsByteArray()).isEmpty();
            assertThat(response.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isNull();
            verify(chain, never()).doFilter(request, response);
        }
    }

    @Test
    void bareOptionsForBothAliasesEndsBeforeAuthenticationSideEffects() throws Exception {
        for (String path : List.of(
                "/api/user/banks/api/0/user-counts",
                "/user/banks/api/41/user-counts",
                "/api/user/banks/api/2147483648/user-counts")) {
            MockHttpServletRequest request = request("OPTIONS", path);
            request.addHeader(HttpHeaders.ORIGIN, "https://evil.example");
            MockHttpServletResponse response = new MockHttpServletResponse();
            FilterChain chain = mock(FilterChain.class);

            if (path.startsWith("/api/")) {
                request.removeHeader(HttpHeaders.ORIGIN);
            }
            filter.doFilter(request, response, chain);

            assertThat(response.getStatus()).as(path).isEqualTo(204);
            assertThat(response.getHeader(HttpHeaders.ALLOW)).isEqualTo("GET, HEAD, OPTIONS");
            assertThat(response.getHeader(HttpHeaders.SET_COOKIE)).isNull();
            assertThat(response.getContentAsByteArray()).isEmpty();
            verify(chain, never()).doFilter(request, response);
        }
    }

    @Test
    void converterMissAndNearMissReturnCompatibility404WithoutCorsOrDownstreamWork()
            throws Exception {
        for (MockHttpServletRequest request : List.of(
                request("GET", "/api/user/banks/api/-1/user-counts"),
                request("GET", "/api/user/banks/api/41/user-counts/extra"),
                request("OPTIONS", "/api/user/banks/api/not-a-bank/user-counts"),
                request("OPTIONS", "/user/banks/api/not-a-bank/user-counts"))) {
            String path = request.getRequestURI();
            request.addHeader(HttpHeaders.ORIGIN, "https://evil.example");
            MockHttpServletResponse response = new MockHttpServletResponse();
            FilterChain chain = mock(FilterChain.class);

            filter.doFilter(request, response, chain);

            assertThat(response.getStatus()).as(path).isEqualTo(404);
            assertThat(response.getContentAsString(StandardCharsets.UTF_8))
                    .contains("The requested URL was not found on the server");
            assertThat(response.getHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isNull();
            verify(chain, never()).doFilter(request, response);
        }
    }

    @Test
    void headWrapperPreservesStatusAndHeadersWhileDiscardingEveryDownstreamBodyByte()
            throws Exception {
        MockHttpServletRequest request = request(
                "HEAD", "/api/user/banks/api/41/user-counts");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = (downstreamRequest, downstreamResponse) -> {
            HttpServletResponse servletResponse = (HttpServletResponse) downstreamResponse;
            servletResponse.setStatus(503);
            servletResponse.setHeader("X-Test-Header", "preserved");
            servletResponse.getOutputStream().write("secret".getBytes(StandardCharsets.UTF_8));
        };

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getHeader("X-Test-Header")).isEqualTo("preserved");
        assertThat(response.getContentAsByteArray()).isEmpty();
    }

    @Test
    void preRateAuthenticationInfrastructureFailureUsesTheRoute503Envelope()
            throws Exception {
        for (String path : List.of(
                "/api/user/banks/api/41/user-counts",
                "/user/banks/api/41/user-counts")) {
            MockHttpServletRequest request = request("GET", path);
            MockHttpServletResponse response = new MockHttpServletResponse();
            FilterChain failedSessionLoad = (ignoredRequest, ignoredResponse) -> {
                throw new IllegalStateException("session-store-secret-must-not-leak");
            };

            filter.doFilter(request, response, failedSessionLoad);

            assertThat(response.getStatus()).as(path).isEqualTo(503);
            assertThat(response.getContentAsString(StandardCharsets.UTF_8))
                    .doesNotContain("session-store-secret-must-not-leak");
            assertThat(response.getHeader("X-RateLimit-Limit")).isNull();
        }

        MockHttpServletRequest postRate = request(
                "GET", "/api/user/banks/api/41/user-counts");
        postRate.setAttribute(
                PersonalBankUserCountsReadRateLimitFilter.BOUNDARY_ENTERED_ATTRIBUTE,
                Boolean.TRUE);
        assertThatThrownBy(() -> filter.doFilter(
                postRate,
                new MockHttpServletResponse(),
                (ignoredRequest, ignoredResponse) -> {
                    throw new IllegalStateException("application-failure");
                }))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("application-failure");
    }

    private static List<String> vary(MockHttpServletResponse response) {
        return response.getHeaders(HttpHeaders.VARY).stream()
                .flatMap(line -> List.of(line.split(",")).stream())
                .map(String::strip)
                .filter(token -> !token.isEmpty())
                .toList();
    }

    private static MockHttpServletRequest request(String method, String path) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, path);
        request.setRequestURI(path);
        request.setServletPath(path);
        request.setAttribute(RequestId.ATTRIBUTE_NAME, "phase4c-cors-test");
        return request;
    }

    private record Preflight(String origin, String method, String headers) {}
}
