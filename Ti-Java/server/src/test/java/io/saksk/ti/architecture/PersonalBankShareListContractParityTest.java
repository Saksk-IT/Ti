package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankShareListView;
import io.saksk.ti.personalbank.api.PersonalBankShareView;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import java.lang.reflect.Field;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Closes the cumulative Phase 4B contract for the HTTP-neutral share-list read. */
class PersonalBankShareListContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String ENTRY_SHA256 =
            "c6c24dd1b5279b8b850b5521c97e47498e0a6966f196ea286e107694ff23110a";
    private static final String SHAPE_SHA256 =
            "7d2cc27f5ab288d7c968f1936a7b88b00b588bf87605ceb7e98bf99005de5c61";
    private static final String GOLDEN_SHA256 =
            "3d5ad616c5dcb644f2247582ce3680345ac2683ffbee67167f98b02bc61061ff";
    private static final String PLAN_SHA256 =
            "860fb6c91ccdde82852b919ef55ef690d96443683235dab9178edd5a079aec06";

    private static Path tiJavaRoot;
    private static JsonNode contract;
    private static JsonNode entry;
    private static JsonNode shape;
    private static JsonNode golden;
    private static JsonNode plan;
    private static JsonNode allSharesEntry;

    @BeforeAll
    static void loadEvidence() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toRealPath();
        tiJavaRoot = basedir.getParent();
        contract = readJson(
                "docs/refactor/phase4b/personal-bank-share-list-read-contract.json");
        entry = readJson(
                "docs/refactor/phase4b/personal-bank-share-list-entry-contract.json");
        shape = readJson(
                "docs/refactor/phase4b/"
                        + "personal-bank-share-list-application-api-shape.json");
        golden = readJson(
                "docs/refactor/phase4b/golden-personal-bank-share-list-reads.json");
        plan = readJson(
                "docs/refactor/phase4b/personal-bank-share-list-query-plan-evidence.json");
        allSharesEntry = readJson(
                "docs/refactor/phase4b/personal-bank-all-shares-entry-contract.json");
    }

    @Test
    void entryGoldenPlanAndShapeCloseTransitively() throws Exception {
        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-share-list-read-contract");
        assertThat(contract.path("schema_version").asInt()).isEqualTo(1);
        assertThat(contract.path("legacy_commit").asString())
                .isEqualTo("700006dfdfa063deb4387be572911e782bcea0d9");
        assertThat(contract.path("status").asString())
                .isEqualTo("implemented_and_targeted_verified_http_aliases_deferred");

        assertThat(sha256(
                        "docs/refactor/phase4b/personal-bank-share-list-entry-contract.json"))
                .isEqualTo(ENTRY_SHA256)
                .isEqualTo(contract.path("predecessor").path("sha256").asString());
        assertThat(entry.path("status").asString())
                .isEqualTo("entry_gate_passed_implementation_not_started");
        assertThat(entry.path("implementation_state").path("implementation_started")
                        .asBoolean())
                .isFalse();
        assertThat(entry.path("entry_gate").path("passed").asBoolean()).isTrue();
        assertThat(contract.path("predecessor").path("historical_implementation_started")
                        .asBoolean())
                .isFalse();

        assertThat(sha256(
                        "docs/refactor/phase4b/"
                                + "personal-bank-share-list-application-api-shape.json"))
                .isEqualTo(SHAPE_SHA256)
                .isEqualTo(contract.path("evidence").path("application_api_shape")
                        .path("sha256").asString());
        assertThat(sha256(
                        "docs/refactor/phase4b/golden-personal-bank-share-list-reads.json"))
                .isEqualTo(GOLDEN_SHA256)
                .isEqualTo(contract.path("evidence").path("golden")
                        .path("sha256").asString());
        assertThat(sha256(
                        "docs/refactor/phase4b/"
                                + "personal-bank-share-list-query-plan-evidence.json"))
                .isEqualTo(PLAN_SHA256)
                .isEqualTo(contract.path("evidence").path("query_plan")
                        .path("sha256").asString());

        assertThat(golden.path("case_count").asInt()).isEqualTo(40);
        assertThat(golden.path("case_payload_sha256").asString())
                .isEqualTo("f497b8100603deb5d842b814f4c79c27e2f3f02f629428cd3755e49cf36d2dc8");
        assertThat(golden.path("document_payload_sha256").asString())
                .isEqualTo("4ff264b57bcb42dcaaa23953a07d06dc0ab8224c16ce7f132a67ef662d0b6d97");
        assertThat(plan.path("engines")).hasSize(2);

        JsonNode handoff = allSharesEntry.path("source_contracts")
                .path("share_list_java_forward_handoff_test");
        assertThat(handoff.path("source").asString())
                .isEqualTo(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "PersonalBankShareListContractParityTest.java");
        assertThat(sha256(handoff.path("source").asString()))
                .isEqualTo(handoff.path("sha256").asString());
        assertThat(allSharesEntry.path("predecessor").path("sha256").asString())
                .isEqualTo(sha256(
                        "docs/refactor/phase4b/personal-bank-share-list-read-contract.json"));
    }

    @Test
    void cumulativeShapeMatchesTheExactApiAndRecords() throws Exception {
        assertThat(shape.path("predecessor").path("sha256").asString())
                .isEqualTo("6efda6464411c6a355ea29ab51f0afa63804ea5110a862b9269c4e30e5f8adb6");
        assertThat(shape.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(shape.path("implemented_route_backed_operation_count").asInt())
                .isEqualTo(11);
        assertThat(shape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(21);
        assertThat(shape.path("pending_route_count").asInt()).isEqualTo(600);
        assertThat(shape.path("production_cutover_count").asInt()).isZero();

        JsonNode personalbank = shape.path("personalbank");
        assertThat(personalbank.path("methods")).hasSize(2);
        assertThat(strings(personalbank.path("implemented_types")))
                .containsExactly(
                        "AuthenticatedPersonalBankViewer",
                        "PersonalBankCategoryView",
                        "PersonalBankShareListView",
                        "PersonalBankShareView");
        assertThat(strings(personalbank.path("deferred_share_list_http_route_ids")))
                .containsExactly("e817f8083d74", "c50102968322");

        var method = PersonalBankApplicationApi.class.getDeclaredMethod(
                "findShares", AuthenticatedPersonalBankViewer.class, int.class);
        assertThat(method.getGenericReturnType().getTypeName())
                .isEqualTo(
                        "java.util.Optional<io.saksk.ti.personalbank.api.PersonalBankShareListView>");
        assertThat(method.getParameterTypes())
                .containsExactly(AuthenticatedPersonalBankViewer.class, int.class);

        assertThat(PersonalBankShareListView.class.isRecord()).isTrue();
        assertThat(componentNames(PersonalBankShareListView.class)).containsExactly("shares");
        assertThat(componentTypes(PersonalBankShareListView.class))
                .containsExactly(
                        "java.util.List<io.saksk.ti.personalbank.api.PersonalBankShareView>");
        assertThat(componentNames(PersonalBankShareView.class))
                .containsExactlyElementsOf(componentNamesFromContract());
        assertThat(componentTypes(PersonalBankShareView.class))
                .containsExactlyElementsOf(componentTypesFromContract());

        var portMethod = PersonalBankShareQueryPort.class.getDeclaredMethod(
                "findShares", long.class, int.class);
        assertThat(portMethod.getGenericReturnType().getTypeName())
                .isEqualTo(
                        "java.util.Optional<java.util.List<io.saksk.ti.personalbank.api.PersonalBankShareView>>");
    }

    @Test
    void implementationHashesAndExactRuntimeStatementsMatchTheContract() throws Exception {
        assertSourceHashes(
                contract.path("implementation").path("main_source_files"),
                contract.path("implementation").path("main_source_sha256"));
        assertSourceHashesWithForwardHandoff(
                contract.path("implementation").path("verification_source_files"),
                contract.path("implementation").path("verification_source_sha256"));

        Class<?> adapter = Class.forName(
                "io.saksk.ti.personalbank.infrastructure.persistence."
                        + "JdbcPersonalBankShareQueryAdapter");
        assertThat(staticString(adapter, "SELECT_OWNER_ACTIVE_BANK"))
                .isEqualTo(contract.path("persistence_contract")
                        .path("owner_probe_sql").asString());
        assertThat(staticString(adapter, "SELECT_PERSONAL_BANK_SHARES"))
                .isEqualTo(contract.path("persistence_contract")
                        .path("share_list_sql").asString());

        JsonNode persistence = contract.path("persistence_contract");
        assertThat(persistence.path("sequential_execution").asBoolean()).isTrue();
        assertThat(persistence.path("second_query_on_probe_miss").asBoolean()).isFalse();
        assertThat(persistence.path("exceptions_translated").asBoolean()).isFalse();
        assertThat(persistence.path("join_or_parallelization").asBoolean()).isFalse();
        assertThat(persistence.path("java_secondary_sorting").asBoolean()).isFalse();
        assertThat(persistence.path("extra_filters").asBoolean()).isFalse();
        assertThat(persistence.path("pagination").asBoolean()).isFalse();
        assertThat(persistence.path("schema_or_index_delta").asBoolean()).isFalse();
        assertThat(persistence.path("bind_types").path("bank_id").asString())
                .isEqualTo("integer");
        assertThat(persistence.path("bind_types").path("viewer_id").asString())
                .isEqualTo("bigint");

        Class<?> service = Class.forName(
                "io.saksk.ti.personalbank.application.PersonalBankQueryService");
        Transactional transaction = service.getDeclaredMethod(
                        "findShares", AuthenticatedPersonalBankViewer.class, int.class)
                .getAnnotation(Transactional.class);
        assertThat(transaction).isNotNull();
        assertThat(transaction.readOnly()).isTrue();
    }

    @Test
    void optionalAndRawValueSemanticsRemainDistinctAndImmutable() {
        var row = new PersonalBankShareView(
                -2, 0, Long.MAX_VALUE, null, " token ", "unexpected-value",
                null, -1, -2, null, null);
        var mutable = new ArrayList<>(List.of(row));
        var present = Optional.of(new PersonalBankShareListView(mutable));
        mutable.clear();

        assertThat(Optional.<PersonalBankShareListView>empty()).isNotEqualTo(present);
        assertThat(present.orElseThrow().shares()).containsExactly(row);
        assertThat(row.id()).isEqualTo(-2);
        assertThat(row.bankId()).isZero();
        assertThat(row.ownerId()).isEqualTo(Long.MAX_VALUE);
        assertThat(row.shareCode()).isNull();
        assertThat(row.shareToken()).isEqualTo(" token ");
        assertThat(row.permission()).isEqualTo("unexpected-value");
        assertThat(row.maxUses()).isEqualTo(-1);
        assertThat(row.currentUses()).isEqualTo(-2);
        assertThat(row.isActive()).isNull();
    }

    @Test
    void bothAliasesStayPendingOpaqueAndWithoutCutover() throws Exception {
        JsonNode routeState = contract.path("route_state");
        assertThat(routeState.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(routeState.path("pending_route_count").asInt()).isEqualTo(600);
        assertThat(routeState.path("production_cutover_count").asInt()).isZero();

        JsonNode openApi = readJson("contracts/openapi.json");
        Map<String, JsonNode> operations = indexBy(routeState.path("operations"), "route_id");
        assertThat(operations.keySet())
                .containsExactlyInAnyOrder("e817f8083d74", "c50102968322");
        for (JsonNode operation : operations.values()) {
            assertThat(operation.path("migration_status").asString()).isEqualTo("pending");
            assertThat(operation.path("contract_maturity").asString()).isEqualTo("inferred");
            assertThat(operation.path("openapi_response_schema_status").asString())
                    .isEqualTo("unknown");
            assertThat(operation.path("production_cutover").asBoolean()).isFalse();

            String openApiPath = operation.path("path").asString()
                    .replace("<int:bank_id>", "{bank_id}");
            JsonNode base = openApi.path("paths").path(openApiPath).path("get");
            assertThat(base.path("operationId").asString())
                    .isEqualTo("legacy_" + operation.path("route_id").asString() + "_get");
            assertThat(base.path("x-ti-migration").path("status").asString())
                    .isEqualTo("pending");
            assertThat(base.path("x-ti-migration").path("targetModule").asString())
                    .isEqualTo("personalbank");
            assertThat(base.path("x-ti-contract-maturity").asString())
                    .isEqualTo("inferred");
            assertThat(base.path("responses").path("default").path("content")
                            .path("*/*").path("schema").path("$ref").asString())
                    .isEqualTo("#/components/schemas/LegacyOpaquePayload");
        }

        JsonNode forbidden = contract.path("forbidden_scope");
        forbidden.properties().forEach(entry ->
                assertThat(entry.getValue().asBoolean()).as(entry.getKey()).isFalse());
    }

    private static void assertSourceHashes(JsonNode files, JsonNode hashes) throws Exception {
        assertThat(propertyNames(files))
                .containsExactlyInAnyOrderElementsOf(propertyNames(hashes));
        for (String key : propertyNames(files)) {
            assertThat(sha256(files.path(key).asString()))
                    .as("source hash for %s", key)
                    .isEqualTo(hashes.path(key).asString());
        }
    }

    private static void assertSourceHashesWithForwardHandoff(
            JsonNode files,
            JsonNode hashes
    ) throws Exception {
        assertThat(propertyNames(files))
                .containsExactlyInAnyOrderElementsOf(propertyNames(hashes));
        for (String key : propertyNames(files)) {
            String relative = files.path(key).asString();
            String currentHash = sha256(relative);
            if (key.equals("share_read_contract_test")) {
                JsonNode handoff = allSharesEntry.path("source_contracts")
                        .path("share_list_read_forward_handoff_test");
                assertThat(handoff.path("source").asString()).isEqualTo(relative);
                assertThat(handoff.path("sha256").asString()).isEqualTo(currentHash);
                assertThat(hashes.path(key).asString()).isNotEqualTo(currentHash);
            } else {
                assertThat(currentHash)
                        .as("source hash for %s", key)
                        .isEqualTo(hashes.path(key).asString());
            }
        }
    }

    private static String staticString(Class<?> type, String fieldName) throws Exception {
        Field field = type.getDeclaredField(fieldName);
        field.setAccessible(true);
        return (String) field.get(null);
    }

    private static List<String> componentNamesFromContract() {
        List<String> names = new ArrayList<>();
        contract.path("share_record_components")
                .forEach(component -> names.add(component.path("name").asString()));
        return names;
    }

    private static List<String> componentTypesFromContract() {
        List<String> types = new ArrayList<>();
        contract.path("share_record_components")
                .forEach(component -> types.add(component.path("java_type").asString()));
        return types;
    }

    private static List<String> componentNames(Class<?> recordType) {
        return Arrays.stream(recordType.getRecordComponents())
                .map(RecordComponent::getName)
                .toList();
    }

    private static List<String> componentTypes(Class<?> recordType) {
        return Arrays.stream(recordType.getRecordComponents())
                .map(component -> component.getGenericType().getTypeName())
                .toList();
    }

    private static Map<String, JsonNode> indexBy(JsonNode array, String key) {
        Map<String, JsonNode> result = new LinkedHashMap<>();
        array.forEach(node -> result.put(node.path(key).asString(), node));
        return result;
    }

    private static List<String> propertyNames(JsonNode object) {
        List<String> names = new ArrayList<>();
        names.addAll(object.propertyNames());
        return names;
    }

    private static List<String> strings(JsonNode array) {
        List<String> values = new ArrayList<>();
        array.forEach(node -> values.add(node.asString()));
        return values;
    }

    private static JsonNode readJson(String relative) throws Exception {
        return JSON.readTree(Files.readString(resolve(relative), StandardCharsets.UTF_8));
    }

    private static String sha256(String relative) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(Files.readAllBytes(resolve(relative))));
    }

    private static Path resolve(String relative) {
        Path path = tiJavaRoot.resolve(relative).normalize();
        if (!path.startsWith(tiJavaRoot)) {
            throw new IllegalArgumentException("Path escapes Ti-Java: " + relative);
        }
        return path;
    }
}
