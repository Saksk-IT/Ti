package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
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
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Closes the Phase 4B machine contract for the HTTP-neutral category query. */
class PersonalBankCategoryContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String LEGACY_COMMIT =
            "700006dfdfa063deb4387be572911e782bcea0d9";
    private static final String PHASE4A_FINAL_SHA256 =
            "9eeec781af91c0994c750ea2641653183f36eb4492d4ff9bd6809679c723620f";
    private static final String PHASE4A_SHAPE_SHA256 =
            "74782a5a26b1f32f85869cafa931acf4a7c7e1398b3b2e9dab0d0ded93c448ca";
    private static final String PHASE4B_SHAPE_SHA256 =
            "6efda6464411c6a355ea29ab51f0afa63804ea5110a862b9269c4e30e5f8adb6";
    private static final String GOLDEN_SHA256 =
            "c81ad22b70e1e9e25eed96e2f06a475ba590eb7ae00b7a106c6bcedac3818515";
    private static final String GOLDEN_CASE_SHA256 =
            "66590670726216ad48cb5e5b2f858da16529c2a1ff976c70dbb92f2ca2e6e6cc";
    private static final String GOLDEN_DOCUMENT_SHA256 =
            "ef04369ba1ba04768bc75a88c254e1b1ae3af9f0cdefc16272d331ad9f5982fc";
    private static final String QUERY_PLAN_SHA256 =
            "0b23e9af5cdbaec543fb798a45dd3c6fcd5c8a11cd9f7d27aeb92550cc80cffc";
    private static final String READ_CONTRACT_SHA256 =
            "8ef4b9a1eafeff9813f009a406d6863ac25b92ff438415ed674c758a5a2ff2c7";
    private static final String RUNTIME_SQL_MANIFEST_SHA256 =
            "d9e55d45d46fe8ea223bfe1c5d85a3602befd10e92c9f274900c9f4a924526f5";
    private static final String RUNTIME_SQL_SHA256 =
            "81d455611c86bd51ad637130ffaeee82cdbf2a4b49f5e269a08fba8c280c6bee";
    private static final String ADAPTER_SHA256 =
            "749a70cad4c83acdca9ef5a68ef31a48901e394718a95363ae910a0d2102a2ad";

    private static final List<String> ROUTE_IDS =
            List.of("19b37a262989", "e32aec766730");
    private static final List<String> ROUTE_PATHS = List.of(
            "/api/user/banks/api/categories",
            "/user/banks/api/categories");

    private static Path tiJavaRoot;
    private static JsonNode phase4aFinal;
    private static JsonNode phase4aShape;
    private static JsonNode shape;
    private static JsonNode golden;
    private static JsonNode queryPlan;
    private static JsonNode contract;
    private static JsonNode shareListContract;
    private static JsonNode allSharesContract;
    private static JsonNode usageStatsContract;

    @BeforeAll
    static void loadMachineEvidence() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toRealPath();
        tiJavaRoot = basedir.getParent();
        phase4aFinal = readJson("docs/refactor/phase4a/phase4a-final-acceptance.json");
        phase4aShape = readJson("docs/refactor/phase4a/application-api-shape-status.json");
        shape = readJson("docs/refactor/phase4b/application-api-shape-status.json");
        golden = readJson("docs/refactor/phase4b/golden-personal-bank-category-reads.json");
        queryPlan = readJson(
                "docs/refactor/phase4b/personal-bank-category-query-plan-evidence.json");
        contract = readJson(
                "docs/refactor/phase4b/personal-bank-category-read-contract.json");
        shareListContract = readJson(
                "docs/refactor/phase4b/personal-bank-share-list-read-contract.json");
        allSharesContract = readJson(
                "docs/refactor/phase4b/personal-bank-all-shares-read-contract.json");
        usageStatsContract = readJson(
                "docs/refactor/phase4b/personal-bank-usage-stats-read-contract.json");
    }

    @Test
    void predecessorAndPhase4bEvidenceHashesCloseTransitively() throws Exception {
        assertThat(sha256("docs/refactor/phase4a/phase4a-final-acceptance.json"))
                .isEqualTo(PHASE4A_FINAL_SHA256);
        assertThat(sha256("docs/refactor/phase4a/application-api-shape-status.json"))
                .isEqualTo(PHASE4A_SHAPE_SHA256);
        assertThat(sha256("docs/refactor/phase4b/application-api-shape-status.json"))
                .isEqualTo(PHASE4B_SHAPE_SHA256);
        assertThat(sha256(
                        "docs/refactor/phase4b/golden-personal-bank-category-reads.json"))
                .isEqualTo(GOLDEN_SHA256);
        assertThat(sha256(
                        "docs/refactor/phase4b/personal-bank-category-query-plan-evidence.json"))
                .isEqualTo(QUERY_PLAN_SHA256);
        assertThat(sha256(
                        "docs/refactor/phase4b/personal-bank-category-read-contract.json"))
                .isEqualTo(READ_CONTRACT_SHA256);

        assertThat(phase4aFinal.path("contract_id").asString())
                .isEqualTo("ti.phase4a.final-acceptance");
        assertThat(phase4aFinal.path("status").asString()).isEqualTo("passed");
        assertThat(phase4aFinal.path("phase4a_closure").path("phase4a_closed")
                        .asBoolean())
                .isTrue();
        assertThat(phase4aFinal.path("phase4a_closure").path("next_phase").asString())
                .isEqualTo("4B");
        assertThat(phase4aFinal.path("phase4a_closure").path("production_cutover")
                        .asBoolean())
                .isFalse();
        assertThat(strings(phase4aFinal.path("authorized_next_slice")
                        .path("only_operation_keys")))
                .containsExactly(
                        "19b37a262989|GET|/api/user/banks/api/categories",
                        "e32aec766730|GET|/user/banks/api/categories");
        assertThat(phase4aFinal.path("authorized_next_slice")
                        .path("route_openapi_delta_authorized").asBoolean())
                .isFalse();

        assertThat(phase4aShape.path("contract_id").asString())
                .isEqualTo("ti.phase4a.application-api-shape-status");
        assertThat(shape.path("contract_id").asString())
                .isEqualTo("ti.phase4b.application-api-shape-status");
        assertThat(shape.path("previous_shape_status").asString())
                .isEqualTo("../phase4a/application-api-shape-status.json");

        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-category-read-contract");
        assertThat(contract.path("schema_version").asInt()).isEqualTo(1);
        assertThat(contract.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);
        assertThat(contract.path("status").asString())
                .isEqualTo(
                        "personalbank_internal_category_read_implemented_http_aliases_deferred");

        JsonNode finalEvidence = contract.path("evidence").path("phase4a_final_acceptance");
        assertThat(finalEvidence.path("source").asString())
                .isEqualTo("../phase4a/phase4a-final-acceptance.json");
        assertThat(finalEvidence.path("sha256").asString())
                .isEqualTo(PHASE4A_FINAL_SHA256);
        assertThat(finalEvidence.path("status").asString())
                .isEqualTo("passed_and_immutable_input");

        JsonNode shapeEvidence = contract.path("evidence").path("application_api_shape");
        assertThat(shapeEvidence.path("source").asString())
                .isEqualTo("application-api-shape-status.json");
        assertThat(shapeEvidence.path("sha256").asString())
                .isEqualTo(PHASE4B_SHAPE_SHA256);
        assertThat(shapeEvidence.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(shapeEvidence.path("implemented_route_backed_operation_count").asInt())
                .isEqualTo(11);
        assertThat(shapeEvidence.path("implemented_public_application_method_count").asInt())
                .isEqualTo(20);
        assertThat(shapeEvidence.path("personalbank_public_method_count").asInt())
                .isEqualTo(1);

        JsonNode goldenEvidence = contract.path("evidence").path("golden");
        assertThat(goldenEvidence.path("source").asString())
                .isEqualTo("golden-personal-bank-category-reads.json");
        assertThat(goldenEvidence.path("file_sha256").asString()).isEqualTo(GOLDEN_SHA256);
        assertThat(goldenEvidence.path("case_count").asInt()).isEqualTo(22);
        assertThat(goldenEvidence.path("case_payload_sha256").asString())
                .isEqualTo(GOLDEN_CASE_SHA256)
                .isEqualTo(golden.path("case_payload_sha256").asString());
        assertThat(goldenEvidence.path("document_payload_sha256").asString())
                .isEqualTo(GOLDEN_DOCUMENT_SHA256)
                .isEqualTo(golden.path("document_payload_sha256").asString());
        assertThat(golden.path("contract_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-category-read-goldens");
        assertThat(golden.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);
        assertThat(golden.path("case_count").asInt()).isEqualTo(22);
        assertThat(golden.path("cases")).hasSize(22);

        JsonNode planEvidence = contract.path("evidence").path("query_plan");
        assertThat(planEvidence.path("source").asString())
                .isEqualTo("personal-bank-category-query-plan-evidence.json");
        assertThat(planEvidence.path("file_sha256").asString())
                .isEqualTo(QUERY_PLAN_SHA256);
        assertThat(planEvidence.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(RUNTIME_SQL_MANIFEST_SHA256);
        assertThat(planEvidence.path("runtime_sql_sha256").asString())
                .isEqualTo(RUNTIME_SQL_SHA256);
        assertThat(planEvidence.path("adapter_sha256").asString())
                .isEqualTo(ADAPTER_SHA256);
        assertThat(planEvidence.path("runtime_query_count").asInt()).isEqualTo(1);
        assertThat(planEvidence.path("observation_count").asInt()).isEqualTo(1);
        assertThat(queryPlan.path("evidence_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-category-query-plan");
        assertThat(queryPlan.path("schema_version").asInt()).isEqualTo(1);
    }

    @Test
    void shapeAddsOnlyTheReviewedHttpNeutralPersonalbankMethodAndExactDtos()
            throws Exception {
        assertThat(shape.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(shape.path("implemented_route_backed_operation_count").asInt())
                .isEqualTo(11);
        assertThat(shape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(20);

        JsonNode personalbank = findBy(shape.path("modules"), "module_id", "personalbank");
        assertThat(personalbank.path("java_api").asString())
                .isEqualTo("io.saksk.ti.personalbank.api.PersonalBankApplicationApi");
        assertThat(personalbank.path("shape_status").asString())
                .isEqualTo("partially_implemented");
        assertThat(personalbank.path("implemented_route_ids")).isEmpty();
        assertThat(personalbank.path("direct_http_operation").asBoolean()).isFalse();
        assertThat(strings(personalbank.path("deferred_http_route_ids")))
                .containsExactlyElementsOf(ROUTE_IDS);
        assertThat(personalbank.path("deferred_http_owner").asString())
                .isEqualTo("personalbank");
        assertThat(personalbank.path("deferred_http_phase").asString()).isEqualTo("4B");
        assertThat(strings(personalbank.path("implemented_types")))
                .containsExactly("AuthenticatedPersonalBankViewer", "PersonalBankCategoryView");
        assertThat(personalbank.path("methods")).hasSize(1);

        JsonNode methodShape = personalbank.path("methods").get(0);
        assertThat(methodShape.path("name").asString()).isEqualTo("listCategories");
        assertThat(methodShape.path("return_type").asString()).isEqualTo("java.util.List");
        assertThat(methodShape.path("generic_return_type").asString())
                .isEqualTo(
                        "java.util.List<io.saksk.ti.personalbank.api.PersonalBankCategoryView>");
        assertThat(strings(methodShape.path("parameter_types")))
                .containsExactly(
                        "io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer");

        var method = PersonalBankApplicationApi.class.getDeclaredMethod(
                "listCategories", AuthenticatedPersonalBankViewer.class);
        assertThat(method.getGenericReturnType().getTypeName())
                .isEqualTo(methodShape.path("generic_return_type").asString());

        assertThat(AuthenticatedPersonalBankViewer.class.isRecord()).isTrue();
        assertThat(recordComponentNames(AuthenticatedPersonalBankViewer.class))
                .containsExactly("identityId");
        assertThat(recordComponentTypes(AuthenticatedPersonalBankViewer.class))
                .containsExactly("long");
        assertThat(PersonalBankCategoryView.class.isRecord()).isTrue();
        assertThat(recordComponentNames(PersonalBankCategoryView.class))
                .containsExactly(
                        "id",
                        "userId",
                        "name",
                        "description",
                        "sortOrder",
                        "createdAt",
                        "updatedAt",
                        "bankCount");
        assertThat(recordComponentTypes(PersonalBankCategoryView.class))
                .containsExactly(
                        "int",
                        "long",
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.Integer",
                        "java.time.LocalDateTime",
                        "java.time.LocalDateTime",
                        "long");

        assertThat(contract.path("module_boundary").path("method").asString())
                .isEqualTo(
                        "List<PersonalBankCategoryView> listCategories(AuthenticatedPersonalBankViewer viewer)");
        assertThat(contract.path("module_boundary").path("viewer_shape").asString())
                .isEqualTo("long identityId");
        assertThat(strings(contract.path("module_boundary").path("result_field_order")))
                .containsExactlyElementsOf(recordComponentNames(PersonalBankCategoryView.class));

        List<String> contractFieldNames = new ArrayList<>();
        List<String> contractFieldTypes = new ArrayList<>();
        for (JsonNode field : contract.path("personalbank_application_contract")
                .path("result_fields")) {
            contractFieldNames.add(field.path("name").asString());
            contractFieldTypes.add(field.path("java_type").asString());
        }
        assertThat(contractFieldNames)
                .containsExactlyElementsOf(recordComponentNames(PersonalBankCategoryView.class));
        assertThat(contractFieldTypes)
                .containsExactly(
                        "int", "long", "String", "String", "Integer",
                        "LocalDateTime", "LocalDateTime", "long");
    }

    @Test
    void bothAliasesRemainPendingAndTheBaseOpenapiStaysInferredAndOpaque()
            throws Exception {
        JsonNode routeStatus = contract.path("route_status");
        assertThat(routeStatus.path("migrated_route_count_before").asInt()).isEqualTo(11);
        assertThat(routeStatus.path("migrated_route_count_after").asInt()).isEqualTo(11);
        assertThat(routeStatus.path("implemented_route_backed_operation_count_before")
                        .asInt())
                .isEqualTo(11);
        assertThat(routeStatus.path("implemented_route_backed_operation_count_after")
                        .asInt())
                .isEqualTo(11);
        assertThat(routeStatus.path("pending_route_count_before").asInt()).isEqualTo(600);
        assertThat(routeStatus.path("pending_route_count_after").asInt()).isEqualTo(600);
        assertThat(routeStatus.path("production_cutover_count").asInt()).isZero();

        Map<String, JsonNode> operations = indexBy(routeStatus.path("operations"), "route_id");
        assertThat(operations.keySet()).containsExactlyInAnyOrderElementsOf(ROUTE_IDS);
        JsonNode openApi = readJson("contracts/openapi.json");
        for (int index = 0; index < ROUTE_IDS.size(); index++) {
            String routeId = ROUTE_IDS.get(index);
            String path = ROUTE_PATHS.get(index);
            JsonNode operation = operations.get(routeId);
            assertThat(operation.path("method").asString()).isEqualTo("GET");
            assertThat(operation.path("path").asString()).isEqualTo(path);
            assertThat(operation.path("target_module").asString()).isEqualTo("personalbank");
            assertThat(operation.path("migration_status").asString()).isEqualTo("pending");
            assertThat(operation.path("contract_maturity").asString()).isEqualTo("inferred");
            assertThat(operation.path("openapi_response_schema_status").asString())
                    .isEqualTo("unknown");
            assertThat(operation.path("production_cutover").asBoolean()).isFalse();

            JsonNode baseOperation = openApi.path("paths").path(path).path("get");
            assertThat(baseOperation.path("operationId").asString())
                    .isEqualTo("legacy_" + routeId + "_get");
            assertThat(strings(baseOperation.path("tags"))).containsExactly("personalbank");
            assertThat(baseOperation.path("x-ti-contract-maturity").asString())
                    .isEqualTo("inferred");
            assertThat(baseOperation.path("x-ti-legacy").path("routeId").asString())
                    .isEqualTo(routeId);
            assertThat(baseOperation.path("x-ti-migration").path("status").asString())
                    .isEqualTo("pending");
            assertThat(baseOperation.path("x-ti-migration").path("targetModule").asString())
                    .isEqualTo("personalbank");
            assertThat(baseOperation.path("responses").path("default")
                            .path("x-ti-schema-status").asString())
                    .isEqualTo("unknown");
            assertThat(baseOperation.path("responses").path("default")
                            .path("content").path("*/*").path("schema").path("$ref")
                            .asString())
                    .isEqualTo("#/components/schemas/LegacyOpaquePayload");
        }

        assertThat(sha256("docs/refactor/02-route-parity-matrix.csv"))
                .isEqualTo(contract.path("evidence").path("frozen_route_matrix")
                        .path("sha256").asString());
        Map<String, Map<String, String>> baselineRoutes = routeRowsById();
        for (String routeId : ROUTE_IDS) {
            assertThat(baselineRoutes.get(routeId).get("target_module"))
                    .isEqualTo("personalbank");
            assertThat(baselineRoutes.get(routeId).get("migration_status"))
                    .isEqualTo("pending");
        }

        assertThat(golden.path("route_status").path("migration_status").asString())
                .isEqualTo("pending");
        assertThat(golden.path("route_status").path("production_cutover").asBoolean())
                .isFalse();
        assertThat(golden.path("route_status").path("controller_added").asBoolean())
                .isFalse();
        assertThat(golden.path("route_status").path("openapi_delta").asBoolean())
                .isFalse();
        assertThat(golden.path("route_status").path("route_delta").asBoolean())
                .isFalse();

        JsonNode guard = contract.path("cutover_guard");
        for (String field : List.of(
                "controller_added",
                "security_matcher_added",
                "openapi_delta_added",
                "route_parity_delta_added",
                "production_cutover",
                "legacy_writer_changed",
                "phase4a_acceptance_changed")) {
            assertThat(guard.path(field).asBoolean()).as(field).isFalse();
        }
        assertThat(contract.path("module_boundary").path("http_adapter_status").asString())
                .isEqualTo("not_implemented");
        assertThat(contract.path("module_boundary").path("security_matcher_status").asString())
                .isEqualTo("not_implemented");
        assertThat(contract.path("module_boundary").path("openapi_delta_status").asString())
                .isEqualTo("not_authorized_or_implemented");
        assertThat(contract.path("module_boundary").path("route_delta_status").asString())
                .isEqualTo("not_authorized_or_implemented");

        assertThat(Files.exists(unresolved("docs/refactor/phase4b/route-parity-delta.csv")))
                .isFalse();
        assertThat(shape.path("route_status_delta").isNull()).isTrue();
        assertThat(mainJavaSourcesContainingRouteMarkers()).isEmpty();
        assertThat(openApiDeltasContainingRouteMarkers()).isEmpty();
    }

    @Test
    void ownershipImplementationHashesAndRuntimeSqlCloseAgainstActualSources()
            throws Exception {
        JsonNode ownershipEvidence = contract.path("evidence").path("data_ownership");
        assertThat(ownershipEvidence.path("source").asString())
                .isEqualTo("../03-data-ownership.csv");
        assertThat(sha256("docs/refactor/03-data-ownership.csv"))
                .isEqualTo(ownershipEvidence.path("sha256").asString());
        assertThat(strings(ownershipEvidence.path("resources")))
                .containsExactly("table:user_bank_categories", "table:user_question_banks");
        assertThat(ownershipEvidence.path("target_owner").asString())
                .isEqualTo("personalbank");
        assertThat(ownershipEvidence.path("delta_required").asBoolean()).isFalse();

        Map<String, String> owners = ownershipByTable();
        assertThat(owners)
                .containsEntry("user_bank_categories", "personalbank")
                .containsEntry("user_question_banks", "personalbank");
        assertThat(strings(contract.path("module_boundary").path("owned_tables_read")))
                .containsExactly("user_bank_categories", "user_question_banks");

        JsonNode implementation = contract.path("evidence").path("implementation");
        JsonNode sourceFiles = implementation.path("source_files");
        JsonNode sourceHashes = implementation.path("source_sha256");
        Set<String> expectedSourceKeys = Set.of(
                "viewer",
                "view",
                "application_api",
                "application_service",
                "query_port",
                "jdbc_adapter",
                "test_access",
                "sql_manifest_test",
                "sql_contract_test",
                "postgres_compatibility_test",
                "postgres_schema",
                "postgres_fixture");
        assertThat(propertyNames(sourceFiles))
                .containsExactlyInAnyOrderElementsOf(expectedSourceKeys);
        assertThat(propertyNames(sourceHashes))
                .containsExactlyInAnyOrderElementsOf(expectedSourceKeys);
        assertThat(shareListContract.path("status").asString())
                .isEqualTo("implemented_and_targeted_verified_http_aliases_deferred");
        assertThat(sha256(
                        "docs/refactor/phase4b/personal-bank-share-list-entry-contract.json"))
                .isEqualTo(shareListContract.path("predecessor").path("sha256").asString());
        assertThat(allSharesContract.path("predecessor").path("source").asString())
                .isEqualTo(
                        "docs/refactor/phase4b/"
                                + "personal-bank-all-shares-entry-contract.json");
        assertThat(sha256(allSharesContract.path("predecessor").path("source").asString()))
                .isEqualTo(allSharesContract.path("predecessor").path("sha256").asString());
        for (String key : expectedSourceKeys) {
            String source = sourceFiles.path(key).asString();
            assertThat(source).as("implementation path for %s", key).isNotBlank();
            if (key.equals("application_api") || key.equals("application_service")) {
                JsonNode successorFiles = usageStatsContract.path("implementation")
                        .path("main_source_files");
                JsonNode successorHashes = usageStatsContract.path("implementation")
                        .path("main_source_sha256");
                assertThat(successorFiles.path(key).asString()).isEqualTo(source);
                assertThat(sha256(source))
                        .as("successor implementation SHA-256 for %s", key)
                        .isEqualTo(successorHashes.path(key).asString())
                        .isNotEqualTo(sourceHashes.path(key).asString());
            } else {
                assertThat(sha256(source))
                        .as("implementation SHA-256 for %s", key)
                        .isEqualTo(sourceHashes.path(key).asString());
            }
        }
        assertThat(sourceHashes.path("jdbc_adapter").asString()).isEqualTo(ADAPTER_SHA256);

        JsonNode inputs = queryPlan.path("inputs");
        assertThat(inputs.path("adapter").asString())
                .isEqualTo(sourceFiles.path("jdbc_adapter").asString());
        assertThat(inputs.path("adapter_sha256").asString())
                .isEqualTo(ADAPTER_SHA256)
                .isEqualTo(sourceHashes.path("jdbc_adapter").asString());
        assertThat(inputs.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(RUNTIME_SQL_MANIFEST_SHA256)
                .isEqualTo(contract.path("evidence").path("query_plan")
                        .path("runtime_sql_manifest_sha256").asString());
        assertThat(inputs.path("runtime_sql_exporter").asString())
                .isEqualTo(sourceFiles.path("sql_manifest_test").asString());
        assertThat(inputs.path("runtime_sql_exporter_sha256").asString())
                .isEqualTo(sourceHashes.path("sql_manifest_test").asString());
        assertThat(inputs.path("postgres_compatibility_test").asString())
                .isEqualTo(sourceFiles.path("postgres_compatibility_test").asString());
        assertThat(inputs.path("postgres_compatibility_test_sha256").asString())
                .isEqualTo(sourceHashes.path("postgres_compatibility_test").asString());
        assertThat(inputs.path("postgres_schema").asString())
                .isEqualTo(sourceFiles.path("postgres_schema").asString());
        assertThat(inputs.path("postgres_schema_sha256").asString())
                .isEqualTo(sourceHashes.path("postgres_schema").asString());
        assertThat(inputs.path("postgres_fixture").asString())
                .isEqualTo(sourceFiles.path("postgres_fixture").asString());
        assertThat(inputs.path("postgres_fixture_sha256").asString())
                .isEqualTo(sourceHashes.path("postgres_fixture").asString());
        for (String inputKey : List.of("capture_tool", "capture_tool_test")) {
            assertThat(sha256(inputs.path(inputKey).asString()))
                    .isEqualTo(inputs.path(inputKey + "_sha256").asString())
                    .isEqualTo(contract.path("evidence").path("query_plan")
                            .path(inputKey + "_sha256").asString());
        }

        JsonNode observation = queryPlan.path("measurement").path("observation");
        String adapterSql = runtimeAdapterSql();
        assertThat(observation.path("source").asString())
                .isEqualTo(inputs.path("adapter").asString());
        assertThat(observation.path("runtime_query_id").asString())
                .isEqualTo("personal-bank-category-list");
        assertThat(adapterSql).isEqualTo(observation.path("sql").asString());
        assertThat(sha256Utf8(adapterSql))
                .isEqualTo(RUNTIME_SQL_SHA256)
                .isEqualTo(observation.path("sql_sha256").asString())
                .isEqualTo(contract.path("evidence").path("query_plan")
                        .path("runtime_sql_sha256").asString());
        assertThat(queryPlan.path("measurement").path("query_count").asInt())
                .isEqualTo(1);
        assertThat(queryPlan.path("measurement").path("sql_statement_count").asInt())
                .isEqualTo(1);
        assertThat(observation.path("binding").path("bound_parameter_count").asInt())
                .isEqualTo(1);
        assertThat(observation.path("binding").path("mode").asString())
                .isEqualTo("postgresql-prepare-execute");
        assertThat(observation.path("binding").path("parameters").path("user_id")
                        .path("postgres_type").asString())
                .isEqualTo("bigint");
        assertThat(observation.path("binding").path("parameters").path("user_id")
                        .path("bind_kind").asString())
                .isEqualTo("postgresql-prepared-statement-parameter");

        JsonNode compatibility = implementation.path("postgres_compatibility");
        assertThat(strings(compatibility.path("engines")))
                .containsExactly("PostgreSQL 16.14", "PostgreSQL 18.4");
        assertThat(compatibility.path("test_count").asInt()).isEqualTo(2);
        assertThat(compatibility.path("result").asString()).isEqualTo("passed");
        JsonNode verification = compatibility.path("verification_record");
        assertThat(verification.path("status").asString()).isEqualTo("passed");
        assertThat(verification.path("exit_code").asInt()).isZero();
        assertThat(verification.path("scope").asString())
                .contains("JDBC adapter", "not HTTP route parity", "production cutover");
        assertThat(verification.path("runner_totals").path("surefire")
                        .path("tests").asInt())
                .isEqualTo(4);
        assertThat(verification.path("runner_totals").path("failsafe")
                        .path("tests").asInt())
                .isEqualTo(2);
        for (String runner : List.of("surefire", "failsafe")) {
            JsonNode total = verification.path("runner_totals").path(runner);
            assertThat(total.path("failures").asInt()).isZero();
            assertThat(total.path("errors").asInt()).isZero();
            assertThat(total.path("skipped").asInt()).isZero();
        }
        assertThat(contract.path("query_plan_contract").path("environment").asString())
                .startsWith("PostgreSQL 18.4")
                .doesNotContain("PostgreSQL 16");

        JsonNode result = observation.path("runtime_result");
        assertThat(result.path("row_count").asInt()).isEqualTo(5002);
        assertThat(result.path("row_column_count").asInt()).isEqualTo(8);
        assertThat(result.path("all_current_user").asBoolean()).isTrue();
        assertThat(result.path("strict_sort_order_asc_nulls_last_then_id_asc")
                        .asBoolean())
                .isTrue();
        assertThat(result.path("active_bank_count_sum").asInt()).isEqualTo(132364);
        JsonNode summary = observation.path("plan_summary");
        assertThat(summary.path("root_actual_loops").asInt()).isEqualTo(1);
        assertThat(summary.path("maximum_relation_scan_actual_loops").asInt())
                .isEqualTo(1);
        assertThat(summary.path("relation_scan_occurrences")
                        .path("user_bank_categories").asInt())
                .isEqualTo(1);
        assertThat(summary.path("relation_scan_occurrences")
                        .path("user_question_banks").asInt())
                .isEqualTo(1);
        assertThat(observation.path("temp_blocks_observed").path("Temp Read Blocks")
                        .asDouble())
                .isZero();
        assertThat(observation.path("temp_blocks_observed").path("Temp Written Blocks")
                        .asDouble())
                .isZero();
    }

    private static JsonNode readJson(String relative) throws Exception {
        return JSON.readTree(Files.readString(resolve(relative), StandardCharsets.UTF_8));
    }

    private static Path resolve(String relative) throws Exception {
        Path resolved = unresolved(relative).toRealPath();
        if (!resolved.startsWith(tiJavaRoot)) {
            throw new IllegalArgumentException("path escaped Ti-Java: " + relative);
        }
        return resolved;
    }

    private static Path unresolved(String relative) {
        Path resolved = tiJavaRoot.resolve(relative).normalize();
        if (!resolved.startsWith(tiJavaRoot)) {
            throw new IllegalArgumentException("path escaped Ti-Java: " + relative);
        }
        return resolved;
    }

    private static String sha256(String relative) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(Files.readAllBytes(resolve(relative))));
    }

    private static String sha256Utf8(String value) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(value.getBytes(StandardCharsets.UTF_8)));
    }

    private static List<String> strings(JsonNode values) {
        if (!values.isArray()) {
            return List.of();
        }
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .map(JsonNode::asString)
                .toList();
    }

    private static JsonNode findBy(JsonNode values, String field, String expected) {
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .filter(value -> value.path(field).asString().equals(expected))
                .findFirst()
                .orElseThrow();
    }

    private static Map<String, JsonNode> indexBy(JsonNode values, String field) {
        Map<String, JsonNode> indexed = new LinkedHashMap<>();
        for (JsonNode value : values) {
            JsonNode previous = indexed.put(value.path(field).asString(), value);
            assertThat(previous).as("duplicate %s", field).isNull();
        }
        return indexed;
    }

    private static List<String> recordComponentNames(Class<?> recordType) {
        return Arrays.stream(recordType.getRecordComponents())
                .map(RecordComponent::getName)
                .toList();
    }

    private static List<String> recordComponentTypes(Class<?> recordType) {
        return Arrays.stream(recordType.getRecordComponents())
                .map(component -> component.getGenericType().getTypeName())
                .toList();
    }

    private static Set<String> propertyNames(JsonNode object) {
        Set<String> names = new LinkedHashSet<>();
        object.propertyNames().forEach(names::add);
        return Set.copyOf(names);
    }

    private static Map<String, String> ownershipByTable() throws Exception {
        List<String> lines = Files.readAllLines(
                resolve("docs/refactor/03-data-ownership.csv"), StandardCharsets.UTF_8);
        List<String> header = parseCsvLine(lines.getFirst());
        assertThat(header)
                .startsWith(
                        "resource_kind",
                        "resource_name",
                        "legacy_owner",
                        "legacy_source",
                        "target_owner");
        Map<String, String> owners = new LinkedHashMap<>();
        for (String line : lines.subList(1, lines.size())) {
            if (line.isBlank()) {
                continue;
            }
            List<String> columns = parseCsvLine(line);
            assertThat(columns).hasSameSizeAs(header);
            if (columns.get(0).equals("table")) {
                assertThat(owners.put(columns.get(1), columns.get(4)))
                        .as("duplicate table owner for %s", columns.get(1))
                        .isNull();
            }
        }
        return Map.copyOf(owners);
    }

    private static Map<String, Map<String, String>> routeRowsById() throws Exception {
        List<String> lines = Files.readAllLines(
                resolve("docs/refactor/02-route-parity-matrix.csv"), StandardCharsets.UTF_8);
        List<String> header = parseCsvLine(lines.getFirst());
        Map<String, Map<String, String>> routes = new LinkedHashMap<>();
        for (String line : lines.subList(1, lines.size())) {
            if (line.isBlank()) {
                continue;
            }
            List<String> columns = parseCsvLine(line);
            assertThat(columns).hasSameSizeAs(header);
            Map<String, String> row = new LinkedHashMap<>();
            for (int index = 0; index < header.size(); index++) {
                row.put(header.get(index), columns.get(index));
            }
            if (ROUTE_IDS.contains(row.get("route_id"))) {
                assertThat(routes.put(row.get("route_id"), Map.copyOf(row)))
                        .as("duplicate selected route %s", row.get("route_id"))
                        .isNull();
            }
        }
        assertThat(routes.keySet()).containsExactlyInAnyOrderElementsOf(ROUTE_IDS);
        return Map.copyOf(routes);
    }

    private static List<String> parseCsvLine(String line) {
        List<String> columns = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int index = 0; index < line.length(); index++) {
            char character = line.charAt(index);
            if (character == '"') {
                if (quoted && index + 1 < line.length() && line.charAt(index + 1) == '"') {
                    current.append('"');
                    index++;
                } else {
                    quoted = !quoted;
                }
            } else if (character == ',' && !quoted) {
                columns.add(current.toString());
                current.setLength(0);
            } else {
                current.append(character);
            }
        }
        if (quoted) {
            throw new IllegalArgumentException("unterminated CSV quote: " + line);
        }
        columns.add(current.toString());
        return List.copyOf(columns);
    }

    private static String runtimeAdapterSql() throws Exception {
        Class<?> adapter = Class.forName(
                "io.saksk.ti.personalbank.infrastructure.persistence."
                        + "JdbcPersonalBankCategoryQueryAdapter");
        Field sql = adapter.getDeclaredField("SELECT_PERSONAL_BANK_CATEGORIES");
        assertThat(sql.trySetAccessible()).isTrue();
        return (String) sql.get(null);
    }

    private static List<String> mainJavaSourcesContainingRouteMarkers() throws Exception {
        Path sourceRoot = resolve("server/src/main/java");
        try (var sources = Files.walk(sourceRoot)) {
            return sources.filter(Files::isRegularFile)
                    .filter(path -> path.getFileName().toString().endsWith(".java"))
                    .filter(path -> containsAnyRouteMarker(readUnchecked(path)))
                    .map(sourceRoot::relativize)
                    .map(Path::toString)
                    .sorted()
                    .toList();
        }
    }

    private static List<String> openApiDeltasContainingRouteMarkers() throws Exception {
        Path openApiRoot = resolve("openapi");
        try (var sources = Files.walk(openApiRoot)) {
            return sources.filter(Files::isRegularFile)
                    .filter(path -> containsAnyRouteMarker(readUnchecked(path)))
                    .map(openApiRoot::relativize)
                    .map(Path::toString)
                    .sorted()
                    .toList();
        }
    }

    private static boolean containsAnyRouteMarker(String source) {
        return ROUTE_IDS.stream().anyMatch(source::contains)
                || ROUTE_PATHS.stream().anyMatch(source::contains);
    }

    private static String readUnchecked(Path path) {
        try {
            return Files.readString(path, StandardCharsets.UTF_8);
        } catch (java.io.IOException exception) {
            throw new IllegalStateException("failed to read " + path, exception);
        }
    }
}
