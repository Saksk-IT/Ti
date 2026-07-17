package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.learning.api.PersonalBankUserCountsQuery;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.Principal;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;
import org.mockito.ArgumentCaptor;
import org.springframework.core.MethodParameter;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.converter.json.JacksonJsonHttpMessageConverter;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.method.support.ModelAndViewContainer;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.PropertyNamingStrategies;
import tools.jackson.databind.json.JsonMapper;

/** Executes the HTTP-adapter portion of every representable Phase 4B golden case. */
class LegacyPersonalBankUserCountsGoldenTargetMappingTest {

    private static final String GOLDEN_PATH =
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json";
    private static final String EVIDENCE_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-mapping-evidence.json";
    private static final String ROUTE_DELTA_PATH =
            "docs/refactor/phase4c/route-parity-delta.csv";
    private static final Set<String> HTTP_DIFFERENCES = Set.of(
            "P4C-LEARNING-007",
            "P4C-LEARNING-008",
            "P4C-LEARNING-009",
            "P4C-LEARNING-010",
            "P4C-LEARNING-011",
            "P4C-LEARNING-012");
    private static final JsonMapper JSON = JsonMapper.builder()
            .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .build();
    private static final String FIXED_EXPECTATION_TABLE = """
            auth-session-owner-api-alias|MOCKMVC_AVAILABLE|200|-
            auth-bearer-owner-api-alias|MOCKMVC_AVAILABLE|200|-
            auth-bearer-precedes-session-api-alias|MOCKMVC_DENIED|403|-
            auth-invalid-bearer-falls-back-session-api-alias|BOUND_AUTHENTICATION_ONLY|401|-
            auth-state-invalid-bearer-does-not-fallback-session-api-alias|BOUND_AUTHENTICATION_ONLY|401|-
            auth-anonymous-api-alias|BOUND_AUTHENTICATION_ONLY|401|-
            data-empty-api-alias|MOCKMVC_AVAILABLE|200|-
            access-status-zero-api-alias|MOCKMVC_DENIED|403|-
            access-missing-api-alias|MOCKMVC_DENIED|403|-
            access-public-other-api-alias|MOCKMVC_AVAILABLE|200|-
            filter-source-favorites-api-alias|MOCKMVC_AVAILABLE|200|-
            tag-normalized-sa2-empty-api-alias|MOCKMVC_AVAILABLE|200|-
            fault-total-default-api-alias|MOCKMVC_FAILURE|500|-
            fault-total-json-api-alias|MOCKMVC_FAILURE|500|-
            auth-session-owner-web-alias|MOCKMVC_AVAILABLE|200|-
            auth-bearer-owner-web-alias|BOUND_AUTHENTICATION_ONLY|302|-
            auth-bearer-precedes-session-web-alias|BOUND_AUTHENTICATION_ONLY|302|-
            auth-invalid-bearer-falls-back-session-web-alias|BOUND_AUTHENTICATION_ONLY|302|-
            auth-state-invalid-bearer-does-not-fallback-session-web-alias|BOUND_AUTHENTICATION_ONLY|302|-
            auth-anonymous-web-alias|BOUND_AUTHENTICATION_ONLY|302|-
            data-empty-web-alias|MOCKMVC_AVAILABLE|200|-
            access-status-zero-web-alias|MOCKMVC_DENIED|403|-
            access-missing-web-alias|MOCKMVC_DENIED|403|-
            access-public-other-web-alias|MOCKMVC_AVAILABLE|200|-
            filter-source-favorites-web-alias|MOCKMVC_AVAILABLE|200|-
            tag-normalized-sa2-empty-web-alias|MOCKMVC_AVAILABLE|200|-
            fault-total-default-web-alias|MOCKMVC_FAILURE|500|-
            fault-total-json-web-alias|MOCKMVC_FAILURE|500|-
            access-status-null-owner|MOCKMVC_AVAILABLE|200|-
            access-status-two-owner|MOCKMVC_AVAILABLE|200|-
            access-private-other-forbidden|MOCKMVC_DENIED|403|-
            access-shared-future|MOCKMVC_AVAILABLE|200|-
            access-shared-null-expiry|MOCKMVC_AVAILABLE|200|-
            access-shared-equal-now-forbidden|MOCKMVC_DENIED|403|-
            access-shared-expired-forbidden|MOCKMVC_DENIED|403|-
            access-shared-inactive-forbidden|MOCKMVC_DENIED|403|-
            access-shared-malformed-expiry-value-error|BOUND_TYPED_DATABASE_ONLY|-|-
            access-shared-aware-expiry-type-error|BOUND_TYPED_DATABASE_ONLY|-|-
            access-shared-empty-expiry|BOUND_TYPED_DATABASE_ONLY|200|access-shared-null-expiry
            access-shared-fetchone-first-row|MOCKMVC_AVAILABLE|200|access-shared-future
            access-shared-cross-bank-record|MOCKMVC_DENIED|403|-
            filter-q-type-choice|MOCKMVC_AVAILABLE|200|-
            filter-q-type-all-uppercase|MOCKMVC_AVAILABLE|200|-
            filter-q-type-unknown-maps-essay|MOCKMVC_AVAILABLE|200|-
            filter-source-mistakes|MOCKMVC_AVAILABLE|200|-
            filter-source-case-sensitive-fallback|MOCKMVC_AVAILABLE|200|-
            filter-q-type-duplicate-first-wins|MOCKMVC_AVAILABLE|200|-
            filter-source-duplicate-first-wins|MOCKMVC_AVAILABLE|200|-
            tag-all-bypasses-store|MOCKMVC_AVAILABLE|200|-
            filter-tag-duplicate-first-all-wins|MOCKMVC_AVAILABLE|200|-
            tag-case-sensitive-all-enters-store|MOCKMVC_AVAILABLE|200|-
            tag-legacy-migration-sa2-empty|MOCKMVC_AVAILABLE|200|-
            fault-favorites-sqlite-continues|MOCKMVC_AVAILABLE|200|-
            fault-favorites-postgresql-poison-simulation|MOCKMVC_AVAILABLE|200|-
            fault-mistakes-sqlite-continues|MOCKMVC_AVAILABLE|200|-
            fault-mistakes-postgresql-poison-simulation|MOCKMVC_AVAILABLE|200|-
            fault-types-degrades|MOCKMVC_AVAILABLE|200|-
            fault-source-favorites-second-count-postgresql-poison-simulation|MOCKMVC_AVAILABLE|200|-
            fault-share-access-hard-failure|MOCKMVC_FAILURE|500|-
            """;
    private static final Map<String, TargetExpectation> FIXED_TARGET_EXPECTATIONS =
            fixedTargetExpectations();

    @Test
    void evidenceMapsTheExactGoldenSetWithoutPromotingTrackedCasesToParity()
            throws Exception {
        JsonNode golden = readJson(GOLDEN_PATH);
        JsonNode evidence = readJson(EVIDENCE_PATH);

        assertThat(evidence.path("claim").path("classification").asString())
                .isEqualTo("PARTIAL_EXECUTION_MAPPING_LEDGER");
        assertThat(evidence.path("claim").path("full_target_parity_closed").asBoolean())
                .isFalse();
        assertThat(evidence.path("claim").path("cutover_evidence").asBoolean())
                .isFalse();
        assertThat(evidence.path("claim").has("route_migration_eligible")).isTrue();
        assertThat(evidence.path("claim").path("route_migration_eligible").isBoolean())
                .isTrue();
        assertThat(evidence.path("claim").path("route_migration_eligible").asBoolean())
                .as("a partial execution ledger cannot authorize a migrated route")
                .isFalse();
        assertThat(sha256(resolve(GOLDEN_PATH)))
                .isEqualTo(evidence.path("source_golden").path("sha256").asString());
        assertThat(evidence.path("source_golden").path("case_payload_sha256").asString())
                .isEqualTo(golden.path("case_payload_sha256").asString());
        assertThat(golden.path("cases").size()).isEqualTo(59);
        assertThat(evidence.path("cases").size()).isEqualTo(59);
        assertThat(FIXED_TARGET_EXPECTATIONS).hasSize(59);

        Map<String, JsonNode> goldens = casesById(golden.path("cases"));
        Map<String, JsonNode> mappings = casesById(evidence.path("cases"));
        assertThat(mappings.keySet()).containsExactlyElementsOf(goldens.keySet());
        assertThat(mappings.values())
                .allSatisfy(mapping -> assertThat(strings(mapping.path("bindings")))
                        .isNotEmpty());

        long mockMvcCases = FIXED_TARGET_EXPECTATIONS.values().stream()
                .filter(expectation -> expectation.mode().name().startsWith("MOCKMVC_"))
                .count();
        long authenticationOnly = fixedModeCount(ExecutionMode.BOUND_AUTHENTICATION_ONLY);
        long typedDatabaseOnly = fixedModeCount(ExecutionMode.BOUND_TYPED_DATABASE_ONLY);
        assertThat(mockMvcCases).isEqualTo(48);
        assertThat(authenticationOnly).isEqualTo(8);
        assertThat(typedDatabaseOnly).isEqualTo(3);
        assertThat(evidence.path("summary").path("mockmvc_case_count").asLong())
                .isEqualTo(mockMvcCases);
        assertThat(evidence.path("summary").path("bound_only_case_count").asLong())
                .isEqualTo(authenticationOnly + typedDatabaseOnly);

        for (Map.Entry<String, JsonNode> entry : mappings.entrySet()) {
            JsonNode goldenCase = goldens.get(entry.getKey());
            JsonNode mapping = entry.getValue();
            TargetExpectation expectation = fixedExpectation(entry.getKey());
            assertThat(mapping.path("adapter_execution").asString())
                    .as("fixed execution mode for %s", entry.getKey())
                    .isEqualTo(expectation.mode().name());
            if (expectation.targetStatus() == null) {
                assertThat(mapping.path("target_status").isNull())
                        .as("no invented target status for %s", entry.getKey())
                        .isTrue();
            } else {
                assertThat(mapping.path("target_status").asInt())
                        .as("fixed target status for %s", entry.getKey())
                        .isEqualTo(expectation.targetStatus());
            }
            String mappedSource = mapping.path("target_data_source_case").isTextual()
                    ? mapping.path("target_data_source_case").asString()
                    : null;
            assertThat(mappedSource)
                    .as("fixed target data source for %s", entry.getKey())
                    .isEqualTo(expectation.targetDataSourceCase());
            List<String> differences = strings(mapping.path("http_slice_difference_ids"));
            assertThat(differences).allMatch(HTTP_DIFFERENCES::contains);
            assertBindings(evidence, mapping);

            if (goldenCase.path("observed_get_effects").path("sql")
                    .path("user_last_active_dml_attempts").asInt() > 0) {
                assertThat(differences)
                        .as("%s must disclose the removed legacy last_active DML", entry.getKey())
                        .contains("P4C-LEARNING-008");
            }
            if (goldenCase.path("request").path("path").asString().startsWith("/api/")
                    && goldenCase.path("request").path("headers").path("Origin").isMissingNode()
                    && goldenCase.path("response").path("headers")
                            .has("Access-Control-Allow-Origin")) {
                assertThat(differences)
                        .as("%s must disclose the no-Origin CORS header delta", entry.getKey())
                        .contains("P4C-LEARNING-010");
            }
        }

        assertThat(mappings.values().stream()
                .filter(mapping -> mapping.has("inherited_predecessor_difference_id"))
                .map(mapping -> mapping.path("case_id").asString())
                .toList()).containsExactly(
                        "access-shared-fetchone-first-row",
                        "access-shared-cross-bank-record");
        assertThat(mappings.values().stream()
                .filter(mapping -> mapping.has("inherited_predecessor_difference_id")))
                .allSatisfy(mapping -> assertThat(mapping
                        .path("inherited_predecessor_difference_id").asString())
                        .isEqualTo("P4C-LEARNING-006"));
        assertThat(strings(mappings.get("auth-anonymous-web-alias").path("bindings")))
                .containsExactly("http_web_anonymous");
    }

    @Test
    void partialLedgerForcesBothRouteDeltaRowsToRemainPending() throws Exception {
        JsonNode evidence = readJson(EVIDENCE_PATH);
        assertThat(evidence.path("claim").path("route_migration_eligible").asBoolean())
                .isFalse();

        List<String> rows = Files.readAllLines(resolve(ROUTE_DELTA_PATH));
        for (String routeId : List.of("6858f6fa506f", "006913d0d956")) {
            String row = rows.stream()
                    .filter(candidate -> candidate.startsWith(routeId + ","))
                    .findFirst()
                    .orElseThrow(() -> new AssertionError("missing route delta " + routeId));
            String[] columns = row.split(",", 8);
            assertThat(columns).hasSize(8);
            assertThat(columns[6])
                    .as("partial golden ledger cannot migrate route %s", routeId)
                    .isEqualTo("pending");
        }
    }

    @TestFactory
    Stream<DynamicTest> executesOrTracksAllFiftyNineGoldenCases() throws Exception {
        JsonNode golden = readJson(GOLDEN_PATH);
        JsonNode evidence = readJson(EVIDENCE_PATH);
        Map<String, JsonNode> goldens = casesById(golden.path("cases"));

        return StreamSupport.stream(evidence.path("cases").spliterator(), false)
                .map(mapping -> DynamicTest.dynamicTest(
                        mapping.path("case_id").asString()
                                + " [" + mapping.path("adapter_execution").asString() + "]",
                        () -> executeOrTrack(golden, goldens, evidence, mapping)));
    }

    private static void executeOrTrack(
            JsonNode golden,
            Map<String, JsonNode> goldens,
            JsonNode evidence,
            JsonNode mapping
    ) throws Exception {
        assertBindings(evidence, mapping);
        String mode = mapping.path("adapter_execution").asString();
        if (mode.startsWith("BOUND_")) {
            assertThat(mapping.path("tracking_note").isTextual()
                    || mode.equals("BOUND_AUTHENTICATION_ONLY"))
                    .isTrue();
            return;
        }

        JsonNode goldenCase = goldens.get(mapping.path("case_id").asString());
        Harness harness = harness();
        PersonalBankUserCountsView targetView = null;
        if (mode.equals("MOCKMVC_AVAILABLE")) {
            String sourceId = mapping.path("target_data_source_case").isTextual()
                    ? mapping.path("target_data_source_case").asString()
                    : mapping.path("case_id").asString();
            targetView = viewFrom(goldens.get(sourceId));
            when(harness.learning().findPersonalBankUserCounts(any(), any()))
                    .thenReturn(PersonalBankUserCountsResult.available(targetView));
        } else if (mode.equals("MOCKMVC_DENIED")) {
            when(harness.learning().findPersonalBankUserCounts(any(), any()))
                    .thenReturn(PersonalBankUserCountsResult.denied());
        } else if (mode.equals("MOCKMVC_FAILURE")) {
            when(harness.learning().findPersonalBankUserCounts(any(), any()))
                    .thenThrow(new DataAccessResourceFailureException(
                            "synthetic golden adapter failure"));
        } else {
            throw new AssertionError("Unknown adapter execution mode: " + mode);
        }

        MockHttpServletRequestBuilder request = get(
                        goldenCase.path("request").path("path").asString())
                .header(HttpHeaders.ACCEPT,
                        goldenCase.path("request").path("headers")
                                .path("Accept").asString())
                .requestAttr(
                        RequestId.ATTRIBUTE_NAME,
                        goldenCase.path("request").path("headers")
                                .path("X-Request-ID").asString())
                .principal(new TargetAuthenticatedPrincipal(
                        effectiveActorId(golden, goldenCase),
                        "phase4c-golden-target"));
        goldenCase.path("request").path("query").forEach(pair ->
                request.param(pair.path(0).asString(), pair.path(1).asString()));

        MvcResult result = harness.http().perform(request).andReturn();
        if (!mode.equals("MOCKMVC_FAILURE")) {
            assertThat(result.getResolvedException()).isNull();
        }
        assertThat(result.getResponse().getStatus())
                .isEqualTo(mapping.path("target_status").asInt());
        assertApplicationCall(harness.learning(), golden, goldenCase);

        if (mode.equals("MOCKMVC_AVAILABLE")) {
            JsonNode body = JSON.readTree(result.getResponse().getContentAsByteArray());
            assertThat(body.path("status").asString()).isEqualTo("success");
            assertThat(body.path("code").asInt()).isZero();
            JsonNode data = body.path("data");
            assertThat(data.path("total").asLong()).isEqualTo(targetView.total());
            assertThat(data.path("favorites").asLong()).isEqualTo(targetView.favorites());
            assertThat(data.path("mistakes").asLong()).isEqualTo(targetView.mistakes());
            assertThat(strings(data.path("types")))
                    .containsExactlyElementsOf(targetView.types());
            assertThat(data.path("shuffle_options_available").asBoolean())
                    .isEqualTo(targetView.shuffleOptionsAvailable());
            assertThat(body.path("request_id").asString())
                    .isEqualTo(goldenCase.path("request").path("headers")
                            .path("X-Request-ID").asString());
        } else if (mode.equals("MOCKMVC_DENIED")) {
            JsonNode body = JSON.readTree(result.getResponse().getContentAsByteArray());
            assertThat(body.path("message").asString()).isEqualTo("无权访问此题库");
            assertThat(body.has("data")).isFalse();
            assertThat(body.has("payload")).isFalse();
        } else {
            assertSafeFailure(goldenCase, result);
        }
    }

    private static void assertApplicationCall(
            LearningApplicationApi learning,
            JsonNode golden,
            JsonNode goldenCase
    ) {
        ArgumentCaptor<AuthenticatedLearningViewer> viewer =
                ArgumentCaptor.forClass(AuthenticatedLearningViewer.class);
        ArgumentCaptor<PersonalBankUserCountsQuery> query =
                ArgumentCaptor.forClass(PersonalBankUserCountsQuery.class);
        verify(learning).findPersonalBankUserCounts(viewer.capture(), query.capture());
        assertThat(viewer.getValue().identityId()).isEqualTo(effectiveActorId(golden, goldenCase));
        assertThat(query.getValue()).isEqualTo(new PersonalBankUserCountsQuery(
                goldenCase.path("bank_id").asInt(),
                firstQueryValue(goldenCase, "q_type", ""),
                firstQueryValue(goldenCase, "source", "all"),
                firstQueryValue(goldenCase, "tag", "")));
    }

    private static void assertSafeFailure(JsonNode goldenCase, MvcResult result)
            throws Exception {
        boolean api = goldenCase.path("request").path("path").asString().startsWith("/api/");
        String accept = goldenCase.path("request").path("headers").path("Accept").asString();
        if (!api && !accept.startsWith("application/json")) {
            assertThat(result.getResponse().getContentAsString())
                    .contains("500 - 服务器错误")
                    .doesNotContain("synthetic golden adapter failure");
            return;
        }
        JsonNode body = JSON.readTree(result.getResponse().getContentAsByteArray());
        assertThat(body.path("status").asString()).isEqualTo("error");
        assertThat(body.path("status_code").asInt()).isEqualTo(500);
        assertThat(body.toString()).doesNotContain("synthetic golden adapter failure");
    }

    private static long effectiveActorId(JsonNode golden, JsonNode goldenCase) {
        String bearer = goldenCase.path("bearer_actor").asString();
        String actor = !Set.of("", "none", "invalid", "revoked").contains(bearer)
                ? bearer
                : goldenCase.path("session_actor").asString();
        long identityId = golden.path("fixture").path("actors").path(actor).asLong();
        assertThat(identityId).as("effective actor for %s", goldenCase.path("case_id").asString())
                .isPositive();
        return identityId;
    }

    private static String firstQueryValue(
            JsonNode goldenCase,
            String name,
            String fallback
    ) {
        for (JsonNode pair : goldenCase.path("request").path("query")) {
            if (pair.path(0).asString().equals(name)) {
                return pair.path(1).asString();
            }
        }
        return fallback;
    }

    private static PersonalBankUserCountsView viewFrom(JsonNode goldenCase) {
        assertThat(goldenCase).isNotNull();
        JsonNode data = goldenCase.path("response").path("body").path("data");
        assertThat(data.isObject()).as(goldenCase.path("case_id").asString()).isTrue();
        return new PersonalBankUserCountsView(
                data.path("total").asLong(),
                data.path("favorites").asLong(),
                data.path("mistakes").asLong(),
                strings(data.path("types")),
                data.path("shuffle_options_available").asBoolean());
    }

    private static Harness harness() {
        LearningApplicationApi learning = mock(LearningApplicationApi.class);
        var controller = new LegacyPersonalBankUserCountsController(
                learning,
                new PersonalBankUserCountsReadRequestResolver(),
                new LegacyPersonalBankUserCountsSecurityErrorWriter(JSON));
        MockMvc http = MockMvcBuilders.standaloneSetup(controller)
                .setCustomArgumentResolvers(new TargetPrincipalArgumentResolver())
                .setMessageConverters(new JacksonJsonHttpMessageConverter(JSON))
                .build();
        return new Harness(learning, http);
    }

    private static void assertBindings(JsonNode evidence, JsonNode mapping)
            throws Exception {
        Set<String> bindingIds = new LinkedHashSet<>(strings(mapping.path("bindings")));
        for (String differenceId : strings(mapping.path("http_slice_difference_ids"))) {
            bindingIds.addAll(strings(evidence.path("difference_bindings").path(differenceId)));
        }
        for (String bindingId : bindingIds) {
            JsonNode binding = evidence.path("bindings").path(bindingId);
            assertThat(binding.isObject()).as(bindingId).isTrue();
            Class<?> testClass = Class.forName(
                    binding.path("class").asString(),
                    false,
                    LegacyPersonalBankUserCountsGoldenTargetMappingTest.class.getClassLoader());
            Method method = testClass.getDeclaredMethod(binding.path("method").asString());
            assertThat(method.isAnnotationPresent(Test.class)
                    || method.isAnnotationPresent(TestFactory.class))
                    .as(bindingId)
                    .isTrue();
        }
    }

    private static Map<String, JsonNode> casesById(JsonNode cases) {
        Map<String, JsonNode> result = new LinkedHashMap<>();
        cases.forEach(item -> assertThat(result.put(item.path("case_id").asString(), item))
                .as("duplicate case_id " + item.path("case_id").asString())
                .isNull());
        return result;
    }

    private static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        array.forEach(item -> result.add(item.asString()));
        return List.copyOf(result);
    }

    private static TargetExpectation fixedExpectation(String caseId) {
        TargetExpectation expectation = FIXED_TARGET_EXPECTATIONS.get(caseId);
        if (expectation == null) {
            throw new AssertionError("No fixed target expectation for " + caseId);
        }
        return expectation;
    }

    private static long fixedModeCount(ExecutionMode mode) {
        return FIXED_TARGET_EXPECTATIONS.values().stream()
                .filter(expectation -> expectation.mode() == mode)
                .count();
    }

    private static Map<String, TargetExpectation> fixedTargetExpectations() {
        Map<String, TargetExpectation> result = new LinkedHashMap<>();
        FIXED_EXPECTATION_TABLE.lines()
                .map(String::strip)
                .filter(line -> !line.isEmpty())
                .forEach(line -> {
                    String[] columns = line.split("\\|", -1);
                    if (columns.length != 4) {
                        throw new IllegalStateException(
                                "Invalid fixed target expectation: " + line);
                    }
                    Integer status = columns[2].equals("-")
                            ? null
                            : Integer.valueOf(columns[2]);
                    String dataSource = columns[3].equals("-") ? null : columns[3];
                    TargetExpectation previous = result.put(
                            columns[0],
                            new TargetExpectation(
                                    ExecutionMode.valueOf(columns[1]),
                                    status,
                                    dataSource));
                    if (previous != null) {
                        throw new IllegalStateException(
                                "Duplicate fixed target expectation: " + columns[0]);
                    }
                });
        return Map.copyOf(result);
    }

    private static JsonNode readJson(String relativePath) throws Exception {
        return JSON.readTree(Files.readAllBytes(resolve(relativePath)));
    }

    private static Path resolve(String relativePath) {
        for (Path candidate : new LinkedHashSet<>(List.of(
                Path.of(relativePath),
                Path.of("..").resolve(relativePath)))) {
            if (Files.isRegularFile(candidate)) {
                return candidate;
            }
        }
        throw new IllegalStateException("Cannot resolve " + relativePath);
    }

    private static String sha256(Path path) throws Exception {
        return HexFormat.of().formatHex(
                MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
    }

    private record Harness(LearningApplicationApi learning, MockMvc http) {}

    private record TargetExpectation(
            ExecutionMode mode,
            Integer targetStatus,
            String targetDataSourceCase
    ) {}

    private enum ExecutionMode {
        MOCKMVC_AVAILABLE,
        MOCKMVC_DENIED,
        MOCKMVC_FAILURE,
        BOUND_AUTHENTICATION_ONLY,
        BOUND_TYPED_DATABASE_ONLY
    }

    private static final class TargetPrincipalArgumentResolver
            implements HandlerMethodArgumentResolver {

        @Override
        public boolean supportsParameter(MethodParameter parameter) {
            return parameter.getParameterType() == TargetAuthenticatedPrincipal.class
                    && parameter.hasParameterAnnotation(AuthenticationPrincipal.class);
        }

        @Override
        public Object resolveArgument(
                MethodParameter parameter,
                ModelAndViewContainer modelAndViewContainer,
                NativeWebRequest webRequest,
                WebDataBinderFactory binderFactory
        ) {
            Principal principal = webRequest.getUserPrincipal();
            return principal instanceof TargetAuthenticatedPrincipal target ? target : null;
        }
    }
}
