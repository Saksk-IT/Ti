package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankOwnedShareView;
import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import java.lang.reflect.Field;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Closes the cumulative Phase 4B contract for the HTTP-neutral all-shares read. */
class PersonalBankAllSharesContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static Path tiJavaRoot;
    private static JsonNode contract;
    private static JsonNode entry;
    private static JsonNode shape;
    private static JsonNode golden;
    private static JsonNode plan;
    private static JsonNode usageStatsEntry;
    private static JsonNode usageStatsContract;

    @BeforeAll
    static void loadEvidence() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toRealPath();
        tiJavaRoot = basedir.getParent();
        contract = readJson(
                "docs/refactor/phase4b/personal-bank-all-shares-read-contract.json");
        entry = readJson(
                "docs/refactor/phase4b/personal-bank-all-shares-entry-contract.json");
        shape = readJson(
                "docs/refactor/phase4b/"
                        + "personal-bank-all-shares-application-api-shape.json");
        golden = readJson(
                "docs/refactor/phase4b/golden-personal-bank-all-shares-reads.json");
        plan = readJson(
                "docs/refactor/phase4b/personal-bank-all-shares-query-plan-evidence.json");
        usageStatsEntry = readJson(
                "docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json");
        usageStatsContract = readJson(
                "docs/refactor/phase4b/personal-bank-usage-stats-read-contract.json");
    }

    @Test
    void entryShapeGoldenAndPlanCloseTransitively() throws Exception {
        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-all-shares-read-contract");
        assertThat(contract.path("schema_version").asInt()).isEqualTo(1);
        assertThat(contract.path("status").asString())
                .isEqualTo("implemented_and_targeted_verified_http_aliases_deferred");
        assertThat(contract.path("predecessor").path("source").asString())
                .isEqualTo(
                        "docs/refactor/phase4b/"
                                + "personal-bank-all-shares-entry-contract.json");
        assertThat(contract.path("predecessor").path("sha256").asString())
                .isEqualTo(sha256(contract.path("predecessor").path("source").asString()));
        assertThat(entry.path("status").asString())
                .isEqualTo("entry_gate_passed_implementation_not_started");
        assertThat(entry.path("implementation_state").path("implementation_started")
                        .asBoolean())
                .isFalse();

        assertEvidenceHash("application_api_shape");
        assertEvidenceHash("golden");
        assertEvidenceHash("query_plan");
        assertThat(golden.path("case_count").asInt()).isEqualTo(20);
        assertThat(plan.path("engines")).hasSize(2);
        assertThat(strings(plan.path("engines"), "server_version"))
                .containsExactly("16.14", "18.4");

        assertThat(usageStatsEntry.path("contract_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-usage-stats-entry-contract");
        assertThat(usageStatsEntry.path("status").asString())
                .isEqualTo("entry_gate_passed_implementation_not_started");
        assertThat(usageStatsEntry.path("predecessor").path("source").asString())
                .isEqualTo(
                        "docs/refactor/phase4b/"
                                + "personal-bank-all-shares-read-contract.json");
        assertThat(usageStatsEntry.path("predecessor").path("sha256").asString())
                .isEqualTo(sha256(
                        "docs/refactor/phase4b/"
                                + "personal-bank-all-shares-read-contract.json"));
        assertThat(strings(usageStatsEntry.path("authorized_slice")
                        .path("only_operation_keys")))
                .containsExactlyInAnyOrder(
                        "d67a16965b08|GET|/api/user/banks/api/"
                                + "<int:bank_id>/usage-stats",
                        "22aecd49a3c2|GET|/user/banks/api/"
                                + "<int:bank_id>/usage-stats");

        JsonNode verification = contract.path("verification");
        assertThat(verification.path("full_source_tools").path("tests").asInt())
                .isEqualTo(317);
        assertThat(verification.path("full_source_tools").path("failures").asInt())
                .isZero();
        assertThat(verification.path("full_source_tools").path("errors").asInt())
                .isZero();
        assertThat(verification.path("full_maven").path("surefire").asInt())
                .isEqualTo(465);
        assertThat(verification.path("full_maven").path("failsafe").asInt())
                .isEqualTo(68);
        assertThat(verification.path("full_maven").path("failures").asInt())
                .isZero();
        assertThat(verification.path("full_maven").path("errors").asInt())
                .isZero();
        assertThat(verification.path("full_maven").path("skipped").asInt())
                .isZero();
    }

    @Test
    void cumulativeShapeMatchesTheExactApiPortAndRecord() throws Exception {
        assertThat(shape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(22);
        assertThat(shape.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(shape.path("pending_route_count").asInt()).isEqualTo(600);
        assertThat(shape.path("production_cutover_count").asInt()).isZero();
        JsonNode personalbank = shape.path("personalbank");
        assertThat(personalbank.path("methods")).hasSize(3);
        assertThat(strings(personalbank.path("methods"), "name"))
                .containsExactly("listCategories", "findShares", "listOwnedShares");
        assertThat(strings(personalbank.path("implemented_types")))
                .containsExactly(
                        "AuthenticatedPersonalBankViewer",
                        "PersonalBankCategoryView",
                        "PersonalBankOwnedShareView",
                        "PersonalBankShareListView",
                        "PersonalBankShareView");

        var method = PersonalBankApplicationApi.class.getDeclaredMethod(
                "listOwnedShares", AuthenticatedPersonalBankViewer.class);
        assertThat(method.getGenericReturnType().getTypeName())
                .isEqualTo(
                        "java.util.List<io.saksk.ti.personalbank.api.PersonalBankOwnedShareView>");
        assertThat(method.getParameterTypes())
                .containsExactly(AuthenticatedPersonalBankViewer.class);

        assertThat(PersonalBankOwnedShareView.class.isRecord()).isTrue();
        assertThat(componentNames(PersonalBankOwnedShareView.class))
                .containsExactlyElementsOf(componentValues("name"));
        assertThat(componentTypes(PersonalBankOwnedShareView.class))
                .containsExactlyElementsOf(componentValues("java_type"));

        var portMethod = PersonalBankOwnedShareQueryPort.class.getDeclaredMethod(
                "listOwnedShares", long.class);
        assertThat(portMethod.getGenericReturnType().getTypeName())
                .isEqualTo(
                        "java.util.List<io.saksk.ti.personalbank.api.PersonalBankOwnedShareView>");
    }

    @Test
    void implementationHashesAndExactRuntimeStatementMatchTheContract() throws Exception {
        assertSourceHashesWithTerminalHandoff(
                contract.path("implementation").path("main_source_files"),
                contract.path("implementation").path("main_source_sha256"),
                "main_source_files",
                "main_source_sha256");
        assertSourceHashesWithTerminalHandoff(
                contract.path("implementation").path("verification_source_files"),
                contract.path("implementation").path("verification_source_sha256"),
                "verification_source_files",
                "verification_source_sha256");

        Class<?> adapter = Class.forName(
                "io.saksk.ti.personalbank.infrastructure.persistence."
                        + "JdbcPersonalBankOwnedShareQueryAdapter");
        assertThat(staticString(adapter, "SELECT_OWNED_SHARES"))
                .isEqualTo(contract.path("persistence_contract").path("sql").asString());
        JsonNode persistence = contract.path("persistence_contract");
        assertThat(persistence.path("query_count").asInt()).isOne();
        assertThat(persistence.path("viewer_jdbc_bind_type").asString())
                .isEqualTo("bigint");
        assertThat(persistence.path("java_secondary_sorting").asBoolean()).isFalse();
        assertThat(persistence.path("share_link_synthesis").asBoolean()).isFalse();
        assertThat(persistence.path("extra_filters").asBoolean()).isFalse();
        assertThat(persistence.path("pagination").asBoolean()).isFalse();
        assertThat(persistence.path("schema_or_index_delta").asBoolean()).isFalse();

        Class<?> service = Class.forName(
                "io.saksk.ti.personalbank.application.PersonalBankQueryService");
        Transactional transaction = service.getDeclaredMethod(
                        "listOwnedShares", AuthenticatedPersonalBankViewer.class)
                .getAnnotation(Transactional.class);
        assertThat(transaction).isNotNull();
        assertThat(transaction.readOnly()).isTrue();
    }

    @Test
    void bothAliasesStayPendingOpaqueAndWithoutCutover() throws Exception {
        JsonNode routeState = contract.path("route_state");
        assertThat(routeState.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(routeState.path("pending_route_count").asInt()).isEqualTo(600);
        assertThat(routeState.path("production_cutover_count").asInt()).isZero();
        assertThat(routeState.path("operations")).hasSize(2);

        JsonNode openApi = readJson("contracts/openapi.json");
        for (JsonNode operation : routeState.path("operations")) {
            assertThat(operation.path("migration_status").asString()).isEqualTo("pending");
            assertThat(operation.path("contract_maturity").asString()).isEqualTo("inferred");
            assertThat(operation.path("production_cutover").asBoolean()).isFalse();
            JsonNode base = openApi.path("paths")
                    .path(operation.path("path").asString())
                    .path("get");
            assertThat(base.path("operationId").asString())
                    .isEqualTo("legacy_" + operation.path("route_id").asString() + "_get");
            assertThat(base.path("x-ti-migration").path("status").asString())
                    .isEqualTo("pending");
            assertThat(base.path("x-ti-contract-maturity").asString())
                    .isEqualTo("inferred");
            assertThat(base.path("responses").path("default").path("content")
                            .path("*/*").path("schema").path("$ref").asString())
                    .isEqualTo("#/components/schemas/LegacyOpaquePayload");
        }

        contract.path("forbidden_scope").properties().forEach(entry ->
                assertThat(entry.getValue().asBoolean()).as(entry.getKey()).isFalse());
    }

    private static void assertEvidenceHash(String name) throws Exception {
        JsonNode reference = contract.path("evidence").path(name);
        assertThat(reference.path("sha256").asString())
                .isEqualTo(sha256(reference.path("source").asString()));
    }

    private static void assertSourceHashesWithTerminalHandoff(
            JsonNode files,
            JsonNode hashes,
            String terminalFilesKey,
            String terminalHashesKey
    ) throws Exception {
        assertThat(propertyNames(files))
                .containsExactlyInAnyOrderElementsOf(propertyNames(hashes));
        for (String key : propertyNames(files)) {
            String relative = files.path(key).asString();
            String currentHash = sha256(relative);
            String terminalHash = terminalHash(
                    terminalFilesKey, terminalHashesKey, relative);
            if (terminalHash == null) {
                assertThat(currentHash)
                        .as("source hash for %s", key)
                        .isEqualTo(hashes.path(key).asString());
                continue;
            }
            assertThat(currentHash).as("terminal source hash for %s", key)
                    .isEqualTo(terminalHash);
            assertThat(hashes.path(key).asString()).isNotEqualTo(currentHash);
        }
    }

    private static String terminalHash(
            String filesKey,
            String hashesKey,
            String relative
    ) {
        JsonNode files = usageStatsContract.path("implementation").path(filesKey);
        JsonNode hashes = usageStatsContract.path("implementation").path(hashesKey);
        for (String key : propertyNames(files)) {
            if (files.path(key).asString().equals(relative)) {
                return hashes.path(key).asString();
            }
        }
        return null;
    }

    private static String staticString(Class<?> type, String fieldName) throws Exception {
        Field field = type.getDeclaredField(fieldName);
        field.setAccessible(true);
        return (String) field.get(null);
    }

    private static List<String> componentValues(String field) {
        return strings(contract.path("owned_share_record_components"), field);
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

    private static List<String> strings(JsonNode array, String field) {
        List<String> values = new ArrayList<>();
        array.forEach(node -> values.add(node.path(field).asString()));
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
