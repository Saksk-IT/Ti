package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.SubjectReadRateLimiter;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import tools.jackson.databind.ObjectMapper;

class LegacySubjectSecurityErrorWriterTest {

    private final ObjectMapper json = new ObjectMapper();
    private final LegacySubjectSecurityErrorWriter writer =
            new LegacySubjectSecurityErrorWriter(json);

    @Test
    void rateLimitEnvelopeRetainsTheExplicitNullPayloadAndAllLegacyHeaders() throws Exception {
        var request = request("phase4a-rate-writer");
        var response = new MockHttpServletResponse();
        var decision = new SubjectReadRateLimiter.Decision(
                false, 60, 0, 17, 1_784_160_018L, "60 per 1 minute");

        writer.writeRateLimitHeaders(response, decision);
        writer.writeRateLimited(request, response, decision);

        assertThat(response.getStatus()).isEqualTo(429);
        assertThat(response.getContentType()).isEqualTo("application/json");
        assertThat(response.getHeader("Vary")).isEqualTo("Origin, Cookie");
        assertThat(response.getHeader("X-RateLimit-Limit")).isEqualTo("60");
        assertThat(response.getHeader("X-RateLimit-Remaining")).isEqualTo("0");
        assertThat(response.getHeader("X-RateLimit-Reset")).isEqualTo("1784160018");
        assertThat(response.getHeader("Retry-After")).isEqualTo("17");
        var body = json.readTree(response.getContentAsByteArray());
        assertThat(body.path("status").asString()).isEqualTo("error");
        assertThat(body.path("message").asString()).isEqualTo("60 per 1 minute");
        assertThat(body.has("payload")).isTrue();
        assertThat(body.path("payload").isNull()).isTrue();
        assertThat(body.path("status_code").asInt()).isEqualTo(429);
        assertThat(body.path("request_id").asString()).isEqualTo("phase4a-rate-writer");
    }

    @Test
    void limiterInfrastructureFailureUsesASafeStableUnavailableEnvelope() throws Exception {
        var request = request("phase4a-rate-unavailable");
        var response = new MockHttpServletResponse();

        writer.writeServiceUnavailable(request, response);

        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getContentType()).isEqualTo("application/json");
        var body = json.readTree(response.getContentAsByteArray());
        assertThat(body.path("status").asString()).isEqualTo("error");
        assertThat(body.path("message").asString()).isEqualTo("服务暂时不可用");
        assertThat(body.has("payload")).isFalse();
        assertThat(body.path("status_code").asInt()).isEqualTo(503);
        assertThat(response.getContentAsString()).doesNotContain("Redis", "exception", "secret");
    }

    private static MockHttpServletRequest request(String requestId) {
        var request = new MockHttpServletRequest();
        request.setAttribute(RequestId.ATTRIBUTE_NAME, requestId);
        return request;
    }
}
