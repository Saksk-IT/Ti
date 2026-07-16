package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

class PublicBankRateLimitContractTest {

    private final ObjectMapper json = new ObjectMapper();

    @Test
    void machineReadableContractCannotDriftFromRoutesLimitsHeadersOrResetPolicy()
            throws Exception {
        JsonNode contract = json.readTree(Files.readString(contractPath()));

        assertThat(contract.path("schema_version").asInt()).isOne();
        assertThat(contract.path("legacy_evidence").path("repository_commit").asString())
                .isEqualTo("7931a7763fc8adb3df54b6cac5e1c3da27a3cefc");
        assertThat(contract.path("legacy_evidence").path("flask_limiter_version").asString())
                .isEqualTo("3.11.0");
        assertThat(contract.path("legacy_evidence").path("limits_version").asString())
                .isEqualTo("4.2");

        Map<String, String> documentedRoutes = new LinkedHashMap<>();
        contract.path("endpoints").forEach(endpoint -> documentedRoutes.put(
                endpoint.path("route").asString(),
                endpoint.path("redis_scope").asString()));
        assertThat(documentedRoutes).containsExactly(
                Map.entry("LEGACY_LIST", "legacy-list"),
                Map.entry("BOARDS", "boards"),
                Map.entry("CARD_DETAIL", "card-detail"),
                Map.entry("HOT", "hot"),
                Map.entry("PLAZA_LIST", "plaza-list"),
                Map.entry("SUMMARY", "summary"),
                Map.entry("DETAIL", "detail"));
        for (PublicBankReadRequestResolver.Route route
                : PublicBankReadRequestResolver.Route.values()) {
            assertThat(documentedRoutes.get(route.name()))
                    .isEqualTo(RedisPublicBankReadRateLimiter.routeKey(route));
        }

        List<Integer> limits = values(contract.path("windows"))
                .map(node -> node.path("base_limit").asInt())
                .toList();
        List<Long> durations = values(contract.path("windows"))
                .map(node -> node.path("duration_millis").asLong())
                .toList();
        assertThat(limits).containsExactly(10, 500, 5_000);
        assertThat(durations).containsExactly(1_000L, 3_600_000L, 86_400_000L);
        PublicBankReadRateLimitProperties properties = new PublicBankReadRateLimitProperties(
                "contract:public-bank-rate", limits.get(0), limits.get(1), limits.get(2), 1);
        assertThat(List.of(
                properties.requestsPerSecond(),
                properties.requestsPerHour(),
                properties.requestsPerDay())).isEqualTo(limits);

        assertThat(values(contract.path("fixed_window").path("evaluation_order"))
                .map(JsonNode::asString).toList())
                .containsExactly("second", "hour", "day");
        assertThat(contract.path("fixed_window").path("fail_on_first_breach").asBoolean())
                .isTrue();
        assertThat(contract.path("fixed_window")
                .path("short_window_rejection_deducts_longer_windows").asBoolean())
                .isFalse();
        assertThat(contract.path("fixed_window")
                .path("arbitrary_precision_path_id_consumes_limit").asBoolean())
                .isTrue();
        assertThat(contract.path("fixed_window").path("reset_at_expression").asString())
                .isEqualTo("floor((now_epoch_millis + redis_pttl_millis) / 1000) + 1");
        assertThat(contract.path("fixed_window").path("retry_after_expression").asString())
                .isEqualTo("max(1, int(reset_at_epoch_second - now_epoch_seconds))");
        assertThat(values(contract.path("headers")).map(JsonNode::asString).toList())
                .containsExactly(
                        "X-RateLimit-Limit",
                        "X-RateLimit-Remaining",
                        "X-RateLimit-Reset",
                        "Retry-After");
        assertThat(contract.path("responses").path("converter_404").path("counted").asBoolean())
                .isFalse();
        assertThat(contract.path("responses").path("business_404").path("counted").asBoolean())
                .isTrue();
        assertThat(contract.path("responses").path("arbitrary_precision_path_id_500")
                .path("approved_difference").asString()).isEqualTo("P4A-CATALOG-007");
        assertThat(contract.path("responses").path("arbitrary_precision_path_id_500")
                .path("rate_limit_headers").asBoolean()).isTrue();
        assertThat(contract.path("responses").path("arbitrary_precision_path_id_500")
                .path("catalog_called").asBoolean()).isFalse();
        assertThat(contract.path("responses").path("rate_limited_429")
                .path("code_field_present").asBoolean()).isFalse();
        assertThat(contract.path("multiplier").path("java_shadow_default").asInt()).isOne();
        assertThat(contract.path("multiplier").path("java_production_default").asInt())
                .isEqualTo(100);
    }

    private static Path contractPath() {
        return Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .getParent()
                .resolve("docs/refactor/phase4a/public-bank-rate-limit-contract.json");
    }

    private static Stream<JsonNode> values(JsonNode array) {
        return StreamSupport.stream(array.spliterator(), false);
    }
}
