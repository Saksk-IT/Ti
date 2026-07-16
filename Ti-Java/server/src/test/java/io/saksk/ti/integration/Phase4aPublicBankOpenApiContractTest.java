package io.saksk.ti.integration;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

class Phase4aPublicBankOpenApiContractTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Map<String, OperationContract> OPERATIONS = operations();

    @Test
    void deltaCoversExactlySevenLegacyRoutesAndAllLocalReferencesResolve() throws Exception {
        JsonNode openApi = read("openapi/phase4a-public-bank.openapi.json");
        JsonNode golden = read("docs/refactor/phase4a/golden-public-bank-reads.json");

        assertThat(openApi.path("openapi").asString()).isEqualTo("3.1.2");
        assertThat(fieldNames(openApi.path("paths"))).containsExactlyInAnyOrderElementsOf(
                OPERATIONS.keySet());

        Set<String> routeIds = new LinkedHashSet<>();
        OPERATIONS.forEach((path, expected) -> {
            JsonNode operation = openApi.path("paths").path(path).path("get");
            assertThat(operation.path("operationId").asString()).isEqualTo(expected.operationId());
            assertThat(operation.path("x-ti-route-id").asString()).isEqualTo(expected.routeId());
            assertThat(operation.path("x-ti-application-api").asString())
                    .isEqualTo(expected.applicationApi());
            assertThat(operation.path("x-ti-migration").path("status").asString())
                    .isEqualTo("migrated");
            assertThat(operation.path("x-ti-migration").path("productionCutover").asBoolean())
                    .isFalse();
            assertOptionalSecurity(operation.path("security"));
            Set<String> expectedStatuses = path.contains("{bank_id}")
                    ? Set.of("200", "400", "404", "429", "500", "503")
                    : Set.of("200", "400", "429", "500", "503");
            assertThat(fieldNames(operation.path("responses")))
                    .containsExactlyInAnyOrderElementsOf(expectedStatuses);
            assertThat(operation.path("x-ti-query-budget")
                            .path("growthWithResultCount").asInt())
                    .isZero();
            assertThat(operation.path("x-ti-query-budget")
                            .path("nPlusOneForbidden").asBoolean())
                    .isTrue();
            routeIds.add(expected.routeId());
        });

        Set<String> goldenRouteIds = new LinkedHashSet<>();
        golden.path("covered_routes").forEach(route ->
                goldenRouteIds.add(route.path("route_id").asString()));
        assertThat(goldenRouteIds).containsExactlyInAnyOrderElementsOf(routeIds);
        assertThat(golden.path("case_count").asInt())
                .isEqualTo(openApi.path("x-ti-evidence").path("legacyGolden")
                        .path("caseCount").asInt())
                .isEqualTo(46);
        assertThat(golden.path("cases")).hasSize(46);

        assertLocalReferencesResolve(openApi, openApi);
    }

    @Test
    void responseSchemasPinObservedGoldenFieldPresenceAndNullAwareShapes() throws Exception {
        JsonNode openApi = read("openapi/phase4a-public-bank.openapi.json");
        JsonNode golden = read("docs/refactor/phase4a/golden-public-bank-reads.json");
        JsonNode schemas = openApi.path("components").path("schemas");

        assertThat(fieldNames(caseBody(golden, "legacy-list-newest")
                        .path("data").path("banks").get(0)))
                .containsExactlyInAnyOrderElementsOf(required(schemas, "LegacyBank"));
        assertThat(fieldNames(caseBody(golden, "boards-anonymous")
                        .path("data").path("items").get(0)))
                .containsExactlyInAnyOrderElementsOf(required(schemas, "PublicBankBoard"));
        assertThat(fieldNames(caseBody(golden, "hot-anonymous-limit-two")
                        .path("data").path("items").get(0)))
                .containsExactlyInAnyOrderElementsOf(required(schemas, "PublicBankCardFields"));
        assertThat(fieldNames(caseBody(golden, "list-tab-latest").path("data")))
                .containsExactlyInAnyOrderElementsOf(required(schemas, "PlazaListData"));
        assertThat(fieldNames(caseBody(golden, "summary-anonymous").path("data")))
                .containsExactlyInAnyOrderElementsOf(required(schemas, "PublicBankSummary"));

        Set<String> systemDetail = new LinkedHashSet<>(required(schemas, "PublicBankCardFields"));
        systemDetail.addAll(requiredAt(
                schemas.path("SystemPublicBankDetail").path("allOf").get(1)));
        assertThat(fieldNames(caseBody(golden, "detail-system-joined").path("data")))
                .containsExactlyInAnyOrderElementsOf(systemDetail);

        Set<String> userDetail = new LinkedHashSet<>(required(schemas, "PublicBankCardFields"));
        userDetail.addAll(requiredAt(
                schemas.path("UserPublicBankDetail").path("allOf").get(1)));
        assertThat(fieldNames(caseBody(golden, "detail-user-anonymous").path("data")))
                .containsExactlyInAnyOrderElementsOf(userDetail);

        assertThat(fieldNames(caseBody(golden, "detail-business-404")))
                .containsExactlyInAnyOrderElementsOf(required(schemas, "BusinessNotFoundError"));
        assertThat(fieldNames(caseBody(golden, "detail-converter-404")))
                .containsExactlyInAnyOrderElementsOf(required(schemas, "ConverterNotFoundError"));

        Set<String> overflowCases = Set.of(
                "detail-arbitrary-precision-id",
                "card-arbitrary-precision-id");
        JsonNode bankIdEvidence = openApi.path("components").path("parameters")
                .path("BankId").path("x-ti-observed-48-digit-cases");
        assertThat(textValues(bankIdEvidence.path("caseIds")))
                .containsExactlyInAnyOrderElementsOf(overflowCases);
        for (String caseId : overflowCases) {
            JsonNode goldenCase = goldenCase(golden, caseId);
            assertThat(goldenCase.path("request").path("path").asString())
                    .contains("999999999999999999999999999999999999999999999999");
            assertThat(goldenCase.path("response").path("status").asInt()).isEqualTo(500);
            assertThat(goldenCase.path("response").path("headers")
                            .path("Content-Type").asString())
                    .isEqualTo("application/json");
            assertThat(goldenCase.path("database_evidence").path("effects")
                            .path("sql_statement_count").asInt())
                    .isEqualTo(2);
            assertThat(goldenCase.path("database_evidence").path("effects")
                            .path("write_statement_count").asInt())
                    .isZero();
        }
        assertThat(required(schemas, "SafeInternalError"))
                .containsExactlyInAnyOrder(
                        "status", "code", "message", "status_code", "request_id");
    }

    @Test
    void bankIdPinsWerkzeugUnicodeDecimalSemanticsAndNormalization() throws Exception {
        JsonNode openApi = read("openapi/phase4a-public-bank.openapi.json");
        JsonNode golden = read("docs/refactor/phase4a/golden-public-bank-reads.json");
        JsonNode bankId = openApi.path("components").path("parameters").path("BankId");

        String expression = bankId.path("schema").path("pattern").asString();
        assertThat(expression).isEqualTo("^\\p{Nd}+$");
        Pattern unicodeDecimal = Pattern.compile(expression);
        for (String accepted : List.of("5401", "٥٤٠١", "５３０１", "𝟝𝟜𝟘𝟙")) {
            assertThat(unicodeDecimal.matcher(accepted).matches()).as(accepted).isTrue();
        }
        for (String rejected : List.of("-1", "²", "Ⅻ", "54A1")) {
            assertThat(unicodeDecimal.matcher(rejected).matches()).as(rejected).isFalse();
        }

        Map<String, UnicodeDecimalCase> unicodeCases = Map.of(
                "detail-unicode-decimal-id",
                new UnicodeDecimalCase("٥٤٠١", "5401", "detail-user-anonymous"),
                "card-unicode-decimal-id",
                new UnicodeDecimalCase("５３０１", "5301", "card-system-joined"));
        JsonNode evidence = bankId.path("x-ti-observed-unicode-decimal-cases");
        assertThat(textValues(evidence.path("caseIds")))
                .containsExactlyInAnyOrderElementsOf(unicodeCases.keySet());
        unicodeCases.forEach((caseId, expected) -> {
            JsonNode goldenCase = goldenCase(golden, caseId);
            assertThat(goldenCase.path("request").path("path").asString())
                    .contains(expected.input());
            assertThat(goldenCase.path("response").path("status").asInt()).isEqualTo(200);
            assertThat(goldenCase.path("response").path("body"))
                    .isEqualTo(caseBody(golden, expected.asciiCaseId()));
            assertThat(goldenCase.path("response").path("body")
                            .path("data").path("id").asLong())
                    .isEqualTo(Long.parseLong(expected.normalizedId()));
            assertThat(goldenCase.path("response").path("headers")
                            .path("X-RateLimit-Limit").asString())
                    .isEqualTo("10");
            assertThat(evidence.path("normalizedIds").path(caseId).asString())
                    .isEqualTo(expected.normalizedId());
        });

        for (String caseId : List.of("detail-converter-404", "card-converter-404")) {
            JsonNode goldenCase = goldenCase(golden, caseId);
            assertThat(goldenCase.path("request").path("path").asString()).contains("/-1");
            assertThat(goldenCase.path("response").path("status").asInt()).isEqualTo(404);
            assertThat(goldenCase.path("response").path("headers")
                            .has("X-RateLimit-Limit"))
                    .isFalse();
            assertThat(goldenCase.path("database_evidence").path("effects")
                            .path("sql_statement_count").asInt())
                    .isZero();
        }
    }

    @Test
    void evidenceHashesAreClosedOverTheReferencedArtifacts() throws Exception {
        JsonNode openApi = read("openapi/phase4a-public-bank.openapi.json");
        JsonNode golden = read("docs/refactor/phase4a/golden-public-bank-reads.json");

        assertEvidenceHash(openApi, "legacyGolden");
        assertEvidenceHash(openApi, "readContract");
        assertEvidenceHash(openApi, "rateLimitContract");
        assertEvidenceHash(openApi, "queryPlan");
        assertEvidenceHash(openApi, "approvedDifferences");

        JsonNode legacyGolden = openApi.path("x-ti-evidence").path("legacyGolden");
        assertThat(canonicalSha256(golden.path("cases")))
                .isEqualTo(legacyGolden.path("casesSha256").asString());

        JsonNode base = openApi.path("x-ti-base-contract");
        assertThat(sha256(resolve(base.path("path").asString())))
                .isEqualTo(base.path("sha256").asString());
        assertThat(base.path("immutable").asBoolean()).isTrue();
    }

    private static void assertEvidenceHash(JsonNode openApi, String evidenceName)
            throws Exception {
        JsonNode evidence = openApi.path("x-ti-evidence").path(evidenceName);
        assertThat(evidence.hasNonNull("path")).as(evidenceName).isTrue();
        assertThat(sha256(resolve(evidence.path("path").asString())))
                .as(evidenceName)
                .isEqualTo(evidence.path("sha256").asString());
    }

    private static void assertOptionalSecurity(JsonNode security) {
        assertThat(security).hasSize(4);
        assertThat(security.get(0).isObject() && security.get(0).isEmpty()).isTrue();
        assertThat(fieldNames(security.get(1))).containsExactly("targetSession");
        assertThat(fieldNames(security.get(2))).containsExactly("legacyBearer");
        assertThat(fieldNames(security.get(3))).containsExactly("legacyFlaskSession");
    }

    private static void assertLocalReferencesResolve(JsonNode document, JsonNode node) {
        if (node.isObject()) {
            JsonNode ref = node.get("$ref");
            if (ref != null && ref.isTextual() && ref.asString().startsWith("#/")) {
                String pointer = ref.asString().substring(1);
                assertThat(document.at(pointer).isMissingNode())
                        .as("local reference %s", ref.asString())
                        .isFalse();
            }
            List<String> names = new ArrayList<>();
            node.propertyNames().forEach(names::add);
            names.forEach(name -> assertLocalReferencesResolve(document, node.get(name)));
            return;
        }
        if (node.isArray()) {
            node.forEach(child -> assertLocalReferencesResolve(document, child));
        }
    }

    private static JsonNode caseBody(JsonNode golden, String caseId) {
        return goldenCase(golden, caseId).path("response").path("body");
    }

    private static JsonNode goldenCase(JsonNode golden, String caseId) {
        for (JsonNode candidate : golden.path("cases")) {
            if (caseId.equals(candidate.path("case_id").asString())) {
                return candidate;
            }
        }
        throw new IllegalArgumentException("Missing golden case " + caseId);
    }

    private static Set<String> required(JsonNode schemas, String schemaName) {
        return requiredAt(schemas.path(schemaName));
    }

    private static Set<String> requiredAt(JsonNode schema) {
        Set<String> values = new LinkedHashSet<>();
        schema.path("required").forEach(value -> values.add(value.asString()));
        return values;
    }

    private static Set<String> fieldNames(JsonNode object) {
        Set<String> names = new LinkedHashSet<>();
        object.propertyNames().forEach(names::add);
        return names;
    }

    private static List<String> textValues(JsonNode array) {
        List<String> values = new ArrayList<>();
        array.forEach(value -> values.add(value.asString()));
        return values;
    }

    private static JsonNode read(String relativePath) throws IOException {
        return JSON.readTree(Files.readString(resolve(relativePath), StandardCharsets.UTF_8));
    }

    private static Path resolve(String relativePath) {
        return Path.of(Objects.requireNonNull(System.getProperty("basedir")))
                .getParent()
                .resolve(relativePath);
    }

    private static String sha256(Path path) throws IOException {
        return sha256(Files.readAllBytes(path));
    }

    private static String canonicalSha256(JsonNode value) throws IOException {
        StringBuilder canonical = new StringBuilder();
        appendCanonicalJson(value, canonical);
        return sha256(canonical.toString().getBytes(StandardCharsets.UTF_8));
    }

    private static void appendCanonicalJson(JsonNode value, StringBuilder target)
            throws IOException {
        if (value.isObject()) {
            List<String> names = new ArrayList<>();
            value.propertyNames().forEach(names::add);
            names.sort(String::compareTo);
            target.append('{');
            for (int index = 0; index < names.size(); index++) {
                if (index > 0) {
                    target.append(',');
                }
                String name = names.get(index);
                target.append(JSON.writeValueAsString(name)).append(':');
                appendCanonicalJson(value.get(name), target);
            }
            target.append('}');
            return;
        }
        if (value.isArray()) {
            target.append('[');
            for (int index = 0; index < value.size(); index++) {
                if (index > 0) {
                    target.append(',');
                }
                appendCanonicalJson(value.get(index), target);
            }
            target.append(']');
            return;
        }
        target.append(JSON.writeValueAsString(value));
    }

    private static String sha256(byte[] value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private static Map<String, OperationContract> operations() {
        Map<String, OperationContract> operations = new LinkedHashMap<>();
        operations.put(
                "/api/public/banks",
                new OperationContract(
                        "14642ebe7c1d",
                        "legacy_14642ebe7c1d_get",
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#search"));
        operations.put(
                "/api/public/banks/boards",
                new OperationContract(
                        "db1ac691d6fb",
                        "legacy_db1ac691d6fb_get",
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#boards"));
        operations.put(
                "/api/public/banks/card/{source_type}/{bank_id}",
                new OperationContract(
                        "8cfb837021af",
                        "legacy_8cfb837021af_get",
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#detail"));
        operations.put(
                "/api/public/banks/hot",
                new OperationContract(
                        "a473896ff467",
                        "legacy_a473896ff467_get",
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#hot"));
        operations.put(
                "/api/public/banks/list",
                new OperationContract(
                        "b7e49e77a026",
                        "legacy_b7e49e77a026_get",
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#search"));
        operations.put(
                "/api/public/banks/summary",
                new OperationContract(
                        "f3644c1474f3",
                        "legacy_f3644c1474f3_get",
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#summary"));
        operations.put(
                "/api/public/banks/{bank_id}",
                new OperationContract(
                        "37cd782b28dc",
                        "legacy_37cd782b28dc_get",
                        "io.saksk.ti.catalog.api.PublicBankCatalogApi#detail"));
        return Map.copyOf(operations);
    }

    private record UnicodeDecimalCase(String input, String normalizedId, String asciiCaseId) {}

    private record OperationContract(String routeId, String operationId, String applicationApi) {}
}
