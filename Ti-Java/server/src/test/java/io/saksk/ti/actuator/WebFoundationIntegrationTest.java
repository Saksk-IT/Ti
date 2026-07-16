package io.saksk.ti.actuator;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;

import jakarta.servlet.DispatcherType;
import jakarta.servlet.RequestDispatcher;
import io.saksk.ti.web.contract.ApiSuccess;
import io.saksk.ti.web.contract.ApiError;
import io.saksk.ti.web.contract.ApiErrorDetail;
import io.saksk.ti.web.contract.PaginationMeta;
import io.saksk.ti.web.config.SecurityConfiguration;
import io.saksk.ti.web.config.TimeConfiguration;
import io.saksk.ti.web.error.GlobalExceptionHandler;
import io.saksk.ti.web.error.SafeErrorController;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.request.RequestIdFilter;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringBootConfiguration;
import org.springframework.boot.autoconfigure.EnableAutoConfiguration;
import org.springframework.boot.data.jpa.autoconfigure.DataJpaRepositoriesAutoConfiguration;
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.boot.hibernate.autoconfigure.HibernateJpaAutoConfiguration;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
import org.springframework.boot.security.autoconfigure.UserDetailsServiceAutoConfiguration;
import org.springframework.boot.session.data.redis.autoconfigure.SessionDataRedisAutoConfiguration;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Import;
import org.springframework.core.env.Environment;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.security.core.userdetails.UserDetailsService;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest(classes = WebFoundationIntegrationTest.TestApplication.class)
@AutoConfigureMockMvc
class WebFoundationIntegrationTest {

    @SpringBootConfiguration
    @EnableAutoConfiguration(exclude = {
            DataSourceAutoConfiguration.class,
            HibernateJpaAutoConfiguration.class,
            DataJpaRepositoriesAutoConfiguration.class,
            SessionDataRedisAutoConfiguration.class,
            UserDetailsServiceAutoConfiguration.class
    })
    @Import({
            SecurityConfiguration.class,
            TimeConfiguration.class,
            RequestIdFilter.class,
            SafeSecurityErrorWriter.class,
            SafeErrorController.class,
            GlobalExceptionHandler.class
    })
    static class TestApplication {

        @Bean(name = "dbHealthContributor")
        HealthIndicator unavailableDatabase() {
            return () -> Health.down().build();
        }
    }

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private Clock clock;

    @Autowired
    private Environment environment;

    @Autowired
    private ApplicationContext applicationContext;

    @Test
    void livenessStaysUpWhileReadinessReportsDatabaseFailureWithoutDetails() throws Exception {
        mockMvc.perform(get("/actuator/health/liveness"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.components").doesNotExist());

        mockMvc.perform(get("/actuator/health/readiness"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.status").value("DOWN"))
                .andExpect(jsonPath("$.components").doesNotExist());

        mockMvc.perform(get("/livez"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));

        mockMvc.perform(get("/readyz"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.status").value("DOWN"))
                .andExpect(jsonPath("$.components").doesNotExist());
    }

    @Test
    void metricsAreScrapableWhileUndeclaredEndpointsRemainDenied() throws Exception {
        mockMvc.perform(get("/actuator/prometheus")
                        .header(RequestId.HEADER_NAME, "security-test-01"))
                .andExpect(status().isOk())
                .andExpect(header().string(RequestId.HEADER_NAME, "security-test-01"))
                .andExpect(content().string(containsString("jvm_")));

        mockMvc.perform(get("/not-declared"))
                .andExpect(status().isUnauthorized())
                .andExpect(header().string(
                        RequestId.HEADER_NAME,
                        matchesPattern("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")))
                .andExpect(jsonPath("$.error.code").value("AUTHENTICATION_REQUIRED"));

        mockMvc.perform(post("/not-declared")
                        .header(RequestId.HEADER_NAME, "csrf-test-01"))
                .andExpect(status().isForbidden())
                .andExpect(header().string(RequestId.HEADER_NAME, "csrf-test-01"))
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("FORBIDDEN"))
                .andExpect(jsonPath("$.meta.request_id").value("csrf-test-01"));
    }

    @Test
    void internalErrorDispatchUsesSafeEnvelopeInsteadOfProblemDetail() throws Exception {
        mockMvc.perform(get("/error")
                        .with(request -> {
                            request.setDispatcherType(DispatcherType.ERROR);
                            return request;
                        })
                        .requestAttr(RequestDispatcher.ERROR_STATUS_CODE, 500)
                        .requestAttr(RequestDispatcher.ERROR_MESSAGE, "database-password-secret")
                        .header(RequestId.HEADER_NAME, "error-dispatch-01"))
                .andExpect(status().isInternalServerError())
                .andExpect(header().string(RequestId.HEADER_NAME, "error-dispatch-01"))
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.error.code").value("INTERNAL_ERROR"))
                .andExpect(jsonPath("$.meta.request_id").value("error-dispatch-01"))
                .andExpect(jsonPath("$.detail").doesNotExist())
                .andExpect(jsonPath("$.instance").doesNotExist());
    }

    @Test
    void timeAndJsonContractAreUtcAndSnakeCase() throws Exception {
        assertThat(clock.getZone()).isEqualTo(ZoneOffset.UTC);

        String instantJson = objectMapper.writeValueAsString(
                Map.of("created_at", Instant.parse("2026-07-15T16:00:00Z")));
        assertThat(instantJson).isEqualTo("{\"created_at\":\"2026-07-15T16:00:00Z\"}");

        String offsetJson = objectMapper.writeValueAsString(
                Map.of("created_at", OffsetDateTime.parse("2026-07-16T00:00:00+08:00")));
        assertThat(offsetJson).isEqualTo("{\"created_at\":\"2026-07-15T16:00:00Z\"}");

        String envelopeJson = objectMapper.writeValueAsString(
                ApiSuccess.of(Map.of("value", 1), "serialization-test-01"));
        assertThat(envelopeJson)
                .contains("\"success\":true")
                .contains("\"request_id\":\"serialization-test-01\"")
                .doesNotContain("pagination");

        String paginatedEnvelopeJson = objectMapper.writeValueAsString(
                ApiSuccess.of(
                        Map.of("items", 2),
                        "pagination-test-01",
                        PaginationMeta.of(2, 20, 45)));
        assertThat(paginatedEnvelopeJson)
                .contains("\"request_id\":\"pagination-test-01\"")
                .contains("\"page\":2")
                .contains("\"page_size\":20")
                .contains("\"total_items\":45")
                .contains("\"total_pages\":3")
                .contains("\"has_next\":true")
                .contains("\"has_previous\":true");
    }

    @Test
    void successAndPaginationFactoriesRejectContradictoryEnvelopes() {
        assertThatThrownBy(() -> ApiSuccess.of(null, "null-data-test-01"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("HTTP 204");

        assertThat(PaginationMeta.of(1, 20, 0))
                .isEqualTo(new PaginationMeta(1, 20, 0, 0, false, false));
        assertThat(PaginationMeta.of(1, 100, 101))
                .isEqualTo(new PaginationMeta(1, 100, 101, 2, true, false));

        assertThatThrownBy(() -> new PaginationMeta(1, 20, 0, 0, true, true))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PaginationMeta.of(1, 101, 1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("pageSize");
        assertThatThrownBy(() -> new ApiError("not_stable", "bad", java.util.List.of()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ApiErrorDetail(null, "INVALID", null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(new ApiErrorDetail(null, "INVALID", "安全摘要").field()).isNull();
    }

    @Test
    void loggingIsStructuredAndRequestDetailLoggingStaysDisabled() {
        assertThat(environment.getProperty("server.port", Integer.class)).isEqualTo(8080);
        assertThat(environment.getProperty("logging.structured.format.console")).isEqualTo("logstash");
        assertThat(environment.getProperty("spring.mvc.log-request-details", Boolean.class)).isFalse();
        assertThat(environment.getProperty("server.tomcat.accesslog.enabled", Boolean.class)).isFalse();
        assertThat(applicationContext.getBeansOfType(UserDetailsService.class)).isEmpty();
    }
}
