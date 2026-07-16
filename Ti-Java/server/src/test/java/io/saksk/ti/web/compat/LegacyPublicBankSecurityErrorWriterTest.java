package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.PublicBankReadRateLimiter;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import tools.jackson.databind.ObjectMapper;

class LegacyPublicBankSecurityErrorWriterTest {

    private final ObjectMapper json = new ObjectMapper();
    private final LegacyPublicBankSecurityErrorWriter writer =
            new LegacyPublicBankSecurityErrorWriter(json);

    @Test
    void rateLimitEnvelopeHasTheExactLegacyNullPayloadAndFourHeaders() throws Exception {
        var request = request("public-bank-429");
        var response = new MockHttpServletResponse();
        var decision = new PublicBankReadRateLimiter.Decision(
                false, 10, 0, 2, 1_784_174_402L, "10 per 1 second");

        writer.writeRateLimitHeaders(response, decision);
        writer.writeRateLimited(request, response, decision);

        assertThat(response.getStatus()).isEqualTo(429);
        assertThat(response.getContentType()).isEqualTo("application/json");
        assertThat(response.getHeader("Vary")).isEqualTo("Origin, Cookie");
        assertThat(response.getHeader("X-RateLimit-Limit")).isEqualTo("10");
        assertThat(response.getHeader("X-RateLimit-Remaining")).isEqualTo("0");
        assertThat(response.getHeader("X-RateLimit-Reset")).isEqualTo("1784174402");
        assertThat(response.getHeader("Retry-After")).isEqualTo("2");
        var body = json.readTree(response.getContentAsByteArray());
        assertThat(body.path("status").asString()).isEqualTo("error");
        assertThat(body.path("message").asString()).isEqualTo("10 per 1 second");
        assertThat(body.has("code")).isFalse();
        assertThat(body.has("payload")).isTrue();
        assertThat(body.path("payload").isNull()).isTrue();
        assertThat(body.path("status_code").asInt()).isEqualTo(429);
        assertThat(body.path("request_id").asString()).isEqualTo("public-bank-429");
    }

    @Test
    void redisFailureUsesTheApprovedStablePublicBank503Envelope() throws Exception {
        var request = request("public-bank-503");
        var response = new MockHttpServletResponse();

        writer.writeServiceUnavailable(request, response);

        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getContentType()).isEqualTo("application/json; charset=utf-8");
        assertThat(response.getHeader("X-RateLimit-Limit")).isNull();
        assertThat(response.getHeader("Retry-After")).isNull();
        var body = json.readTree(response.getContentAsByteArray());
        assertThat(body.path("status").asString()).isEqualTo("error");
        assertThat(body.path("code").asInt()).isOne();
        assertThat(body.path("message").asString()).isEqualTo("服务暂时不可用");
        assertThat(body.path("status_code").asInt()).isEqualTo(503);
        assertThat(body.path("request_id").asString()).isEqualTo("public-bank-503");
        assertThat(response.getContentAsString())
                .doesNotContain("Redis", "exception", "secret");
    }

    private static MockHttpServletRequest request(String requestId) {
        var request = new MockHttpServletRequest();
        request.setAttribute(RequestId.ATTRIBUTE_NAME, requestId);
        return request;
    }
}
