package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRateLimiter;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

class LegacyPersonalBankUserCountsSecurityErrorWriterTest {

    private final ObjectMapper json = new ObjectMapper();
    private final LegacyPersonalBankUserCountsSecurityErrorWriter writer =
            new LegacyPersonalBankUserCountsSecurityErrorWriter(json);

    @Test
    void apiAuthenticationFailureHasTheEnumerationResistantEnvelopeAndMergedVary()
            throws Exception {
        MockHttpServletRequest request = request(
                "GET",
                "phase4c-writer-auth-api",
                null);
        MockHttpServletResponse response = new MockHttpServletResponse();
        response.addHeader(HttpHeaders.VARY, "Access-Control-Request-Headers");
        response.addHeader(HttpHeaders.VARY, "origin");

        writer.writeAuthenticationRequired(request, response, Alias.API);

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentType()).isEqualTo("application/json; charset=utf-8");
        assertThat(response.getHeader(HttpHeaders.VARY))
                .isEqualTo("Access-Control-Request-Headers, origin, Cookie");
        JsonNode body = body(response);
        assertThat(body.size()).isEqualTo(4);
        assertThat(body.path("status").asString()).isEqualTo("unauthorized");
        assertThat(body.path("message").asString()).isEqualTo("请先登录");
        assertThat(body.path("status_code").asInt()).isEqualTo(401);
        assertThat(body.path("request_id").asString()).isEqualTo("phase4c-writer-auth-api");
    }

    @Test
    void webAuthenticationFailureRedirectsButAHeadResponseNeverWritesTheHtmlBody()
            throws Exception {
        MockHttpServletRequest request = request(
                "HEAD",
                "phase4c-writer-auth-web",
                null);
        MockHttpServletResponse response = new MockHttpServletResponse();

        writer.writeAuthenticationRequired(request, response, Alias.WEB);

        assertThat(response.getStatus()).isEqualTo(302);
        assertThat(response.getHeader(HttpHeaders.LOCATION)).isEqualTo("/login");
        assertThat(response.getHeader(HttpHeaders.VARY)).isEqualTo("Cookie");
        assertThat(response.getContentType()).isEqualTo("text/html; charset=utf-8");
        assertThat(response.getContentAsByteArray()).isEmpty();
    }

    @Test
    void denialHasNoDataOrPayloadAndHeadDenialHasNoBody() throws Exception {
        MockHttpServletRequest get = request("GET", "phase4c-writer-denied", null);
        MockHttpServletResponse getResponse = new MockHttpServletResponse();

        writer.writeDenied(get, getResponse, Alias.WEB);

        JsonNode body = body(getResponse);
        assertThat(getResponse.getStatus()).isEqualTo(403);
        assertThat(body.size()).isEqualTo(5);
        assertThat(body.path("code").asInt()).isEqualTo(403);
        assertThat(body.path("message").asString()).isEqualTo("无权访问此题库");
        assertThat(body.has("data")).isFalse();
        assertThat(body.has("payload")).isFalse();

        MockHttpServletRequest head = request("HEAD", "phase4c-writer-denied-head", null);
        MockHttpServletResponse headResponse = new MockHttpServletResponse();
        writer.writeDenied(head, headResponse, Alias.API);
        assertThat(headResponse.getStatus()).isEqualTo(403);
        assertThat(headResponse.getContentAsByteArray()).isEmpty();
    }

    @Test
    void webNotFoundAndInternalFailureHonorOnlyTheRawApplicationJsonPrefix()
            throws Exception {
        MockHttpServletRequest html = request(
                "GET",
                "phase4c-writer-not-found-html",
                "text/html");
        MockHttpServletResponse htmlResponse = new MockHttpServletResponse();
        writer.writeNotFound(html, htmlResponse, Alias.WEB);
        assertThat(htmlResponse.getStatus()).isEqualTo(404);
        assertThat(htmlResponse.getContentAsString()).startsWith("<h1>404 - 页面未找到</h1>");

        MockHttpServletRequest jsonRequest = request(
                "GET",
                "phase4c-writer-internal-json",
                "application/json, text/html");
        MockHttpServletResponse jsonResponse = new MockHttpServletResponse();
        writer.writeInternalFailure(jsonRequest, jsonResponse, Alias.WEB);
        assertThat(jsonResponse.getStatus()).isEqualTo(500);
        assertThat(jsonResponse.getContentType()).isEqualTo("application/json");
        JsonNode jsonBody = body(jsonResponse);
        assertThat(jsonBody.path("message").asString())
                .isEqualTo("An unexpected server error occurred.");
        assertThat(jsonBody.path("payload").isNull()).isTrue();

        MockHttpServletRequest leadingSpace = request(
                "GET",
                "phase4c-writer-internal-raw-prefix",
                " application/json");
        MockHttpServletResponse leadingSpaceResponse = new MockHttpServletResponse();
        writer.writeInternalFailure(leadingSpace, leadingSpaceResponse, Alias.WEB);
        assertThat(leadingSpaceResponse.getContentType())
                .isEqualTo("text/html; charset=utf-8");
    }

    @Test
    void rateLimitedResponseKeepsAllFourHeadersAndNegotiatesPerAlias() throws Exception {
        PersonalBankUserCountsReadRateLimiter.Decision decision = decision();
        MockHttpServletRequest api = request("GET", "phase4c-writer-rate-api", "text/html");
        MockHttpServletResponse apiResponse = new MockHttpServletResponse();

        writer.writeRateLimitHeaders(apiResponse, decision);
        writer.writeRateLimited(api, apiResponse, Alias.API, decision);

        assertThat(apiResponse.getStatus()).isEqualTo(429);
        assertThat(apiResponse.getHeader("X-RateLimit-Limit")).isEqualTo("10");
        assertThat(apiResponse.getHeader("X-RateLimit-Remaining")).isEqualTo("0");
        assertThat(apiResponse.getHeader("X-RateLimit-Reset")).isEqualTo("1784174402");
        assertThat(apiResponse.getHeader(HttpHeaders.RETRY_AFTER)).isEqualTo("2");
        JsonNode apiBody = body(apiResponse);
        assertThat(apiBody.size()).isEqualTo(5);
        assertThat(apiBody.path("message").asString()).isEqualTo("10 per 1 second");
        assertThat(apiBody.path("payload").isNull()).isTrue();

        MockHttpServletRequest web = request("GET", "phase4c-writer-rate-web", "text/html");
        MockHttpServletResponse webResponse = new MockHttpServletResponse();
        writer.writeRateLimitHeaders(webResponse, decision);
        writer.writeRateLimited(web, webResponse, Alias.WEB, decision);
        assertThat(webResponse.getContentAsString())
                .isEqualTo("<h1>429 - Too Many Requests</h1><p>10 per 1 second</p>");
    }

    @Test
    void authenticationExchangeThrottleHasItsOwnSafeAliasEnvelope() throws Exception {
        MockHttpServletRequest api = request(
                "GET", "phase4c-writer-auth-rate-api", "text/html");
        MockHttpServletResponse apiResponse = new MockHttpServletResponse();
        apiResponse.setHeader(HttpHeaders.RETRY_AFTER, "25");
        apiResponse.setHeader("X-RateLimit-Reset", "1784174425");

        writer.writeAuthenticationRateLimited(api, apiResponse, Alias.API);

        assertThat(apiResponse.getStatus()).isEqualTo(429);
        assertThat(apiResponse.getHeader(HttpHeaders.RETRY_AFTER)).isEqualTo("25");
        assertThat(apiResponse.getHeader("X-RateLimit-Reset")).isEqualTo("1784174425");
        assertThat(apiResponse.getHeader("X-RateLimit-Limit")).isNull();
        JsonNode apiBody = body(apiResponse);
        assertThat(apiBody.path("message").asString()).isEqualTo("请求过于频繁");
        assertThat(apiBody.path("payload").isNull()).isTrue();

        MockHttpServletRequest web = request(
                "GET", "phase4c-writer-auth-rate-web", "text/html");
        MockHttpServletResponse webResponse = new MockHttpServletResponse();
        webResponse.setHeader(HttpHeaders.RETRY_AFTER, "25");

        writer.writeAuthenticationRateLimited(web, webResponse, Alias.WEB);

        assertThat(webResponse.getStatus()).isEqualTo(429);
        assertThat(webResponse.getContentAsString())
                .isEqualTo("<h1>429 - Too Many Requests</h1>"
                        + "<p>请求过于频繁，请稍后再试。</p>");
        assertThat(webResponse.getHeader(HttpHeaders.VARY)).isEqualTo("Cookie");
    }

    @Test
    void redisFailureIsSafeHasNoInventedRateHeadersAndSuppressesHeadBody()
            throws Exception {
        MockHttpServletRequest request = request(
                "HEAD",
                "phase4c-writer-rate-store",
                "application/json");
        MockHttpServletResponse response = new MockHttpServletResponse();

        writer.writeServiceUnavailable(request, response, Alias.API);

        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getHeader("X-RateLimit-Limit")).isNull();
        assertThat(response.getHeader("X-RateLimit-Remaining")).isNull();
        assertThat(response.getHeader("X-RateLimit-Reset")).isNull();
        assertThat(response.getHeader(HttpHeaders.RETRY_AFTER)).isNull();
        assertThat(response.getContentAsByteArray()).isEmpty();
        assertThat(response.getContentType()).isEqualTo("application/json");
    }

    private static PersonalBankUserCountsReadRateLimiter.Decision decision() {
        PersonalBankUserCountsReadRateLimiter.Decision decision =
                mock(PersonalBankUserCountsReadRateLimiter.Decision.class);
        when(decision.limit()).thenReturn(10);
        when(decision.remaining()).thenReturn(0);
        when(decision.retryAfterSeconds()).thenReturn(2L);
        when(decision.resetAtEpochSecond()).thenReturn(1_784_174_402L);
        when(decision.legacyLimitDescription()).thenReturn("10 per 1 second");
        return decision;
    }

    private JsonNode body(MockHttpServletResponse response) throws Exception {
        return json.readTree(response.getContentAsByteArray());
    }

    private static MockHttpServletRequest request(
            String method,
            String requestId,
            String accept
    ) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, "/user-counts");
        request.setAttribute(RequestId.ATTRIBUTE_NAME, requestId);
        if (accept != null) {
            request.addHeader(HttpHeaders.ACCEPT, accept);
        }
        return request;
    }
}
