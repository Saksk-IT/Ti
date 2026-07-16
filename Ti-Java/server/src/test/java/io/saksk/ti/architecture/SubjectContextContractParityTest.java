package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Closes the machine contract for the HTTP-neutral subject-context capability. */
class SubjectContextContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String LEGACY_COMMIT =
            "700006dfdfa063deb4387be572911e782bcea0d9";
    private static final String GOLDEN_SHA256 =
            "95cec51d9a687caf210cf52b9958f351a37fc077d457abea2ab89d87c99eea70";
    private static final String GOLDEN_CASE_SHA256 =
            "9fc1e0659dc21f715aa9c27be98b5eae6be38c901adb8c9e5b7874cf8226ac1f";
    private static final String GOLDEN_DOCUMENT_SHA256 =
            "76d35a53590ee11813c19c6d8dfbc6e06ae1eb0a7bebfa35ae38b2b6ba858f51";
    private static final String PLAN_SHA256 =
            "5c83272b2b0ab46c626846afc760330c4aa0a742f0475abbc727c600973ba8e5";
    private static final String RUNTIME_MANIFEST_SHA256 =
            "3949b7cf9d1f73c989198bf1278c5c6c3e558950af69051ecb7ab229e317515e";
    private static final String RUNTIME_SQL_SHA256 =
            "fb24b0e11aef5bc34e0e26f6d17ecd654a423cd6f5c96cbee646cecb89294631";

    private static Path tiJavaRoot;
    private static JsonNode contract;
    private static JsonNode golden;
    private static JsonNode plan;

    @BeforeAll
    static void loadEvidence() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toRealPath();
        tiJavaRoot = basedir.getParent();
        contract = readJson("docs/refactor/phase4a/subject-context-read-contract.json");
        golden = readJson("docs/refactor/phase4a/golden-subject-context-reads.json");
        plan = readJson(
                "docs/refactor/phase4a/subject-context-query-plan-evidence.json");
    }

    @Test
    void machineContractClosesEvidenceSourceAndImplementationHashes() throws Exception {
        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4a.subject-context-read-contract");
        assertThat(contract.path("schema_version").asInt()).isEqualTo(1);
        assertThat(contract.path("status").asString())
                .isEqualTo("catalog_internal_capability_implemented_http_operations_deferred");
        assertThat(contract.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);

        JsonNode goldenEvidence = contract.path("evidence").path("golden");
        assertThat(goldenEvidence.path("source").asString())
                .isEqualTo("golden-subject-context-reads.json");
        assertThat(goldenEvidence.path("file_sha256").asString()).isEqualTo(GOLDEN_SHA256);
        assertThat(goldenEvidence.path("case_count").asInt()).isEqualTo(44);
        assertThat(goldenEvidence.path("case_payload_sha256").asString())
                .isEqualTo(GOLDEN_CASE_SHA256);
        assertThat(goldenEvidence.path("document_payload_sha256").asString())
                .isEqualTo(GOLDEN_DOCUMENT_SHA256);
        assertThat(sha256("docs/refactor/phase4a/golden-subject-context-reads.json"))
                .isEqualTo(GOLDEN_SHA256);
        assertThat(sha256("tools/capture_phase4a_subject_context_goldens.py"))
                .isEqualTo(goldenEvidence.path("capture_tool_sha256").asString());
        assertThat(sha256("tools/test_capture_phase4a_subject_context_goldens.py"))
                .isEqualTo(goldenEvidence.path("capture_tool_test_sha256").asString());

        JsonNode planEvidence = contract.path("evidence").path("query_plan");
        assertThat(planEvidence.path("source").asString())
                .isEqualTo("subject-context-query-plan-evidence.json");
        assertThat(planEvidence.path("file_sha256").asString()).isEqualTo(PLAN_SHA256);
        assertThat(planEvidence.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(RUNTIME_MANIFEST_SHA256);
        assertThat(planEvidence.path("runtime_sql_sha256").asString())
                .isEqualTo(RUNTIME_SQL_SHA256);
        assertThat(planEvidence.path("runtime_query_count").asInt()).isEqualTo(1);
        assertThat(planEvidence.path("observation_count").asInt()).isEqualTo(8);
        assertThat(sha256(
                        "docs/refactor/phase4a/subject-context-query-plan-evidence.json"))
                .isEqualTo(PLAN_SHA256);

        JsonNode inputs = plan.path("inputs");
        assertHashClosed(inputs, planEvidence, "adapter", "adapter_sha256");
        assertHashClosed(
                inputs,
                planEvidence,
                "runtime_sql_exporter",
                "runtime_sql_exporter_sha256");
        assertHashClosed(inputs, planEvidence, "capture_tool", "capture_tool_sha256");
        assertHashClosed(
                inputs,
                planEvidence,
                "capture_tool_test",
                "capture_tool_test_sha256");
        assertThat(inputs.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(planEvidence.path("runtime_sql_manifest_sha256").asString());
        assertThat(plan.path("runtime_sql_contract").path("sql_sha256").asString())
                .isEqualTo(RUNTIME_SQL_SHA256);

        Map<String, String> implementationPaths = Map.of(
                "view_sha256",
                "server/src/main/java/io/saksk/ti/catalog/api/SubjectCatalogRecordView.java",
                "application_api_sha256",
                "server/src/main/java/io/saksk/ti/catalog/api/SubjectMetadataApplicationApi.java",
                "application_service_sha256",
                "server/src/main/java/io/saksk/ti/catalog/application/SubjectMetadataQueryService.java",
                "query_port_sha256",
                "server/src/main/java/io/saksk/ti/catalog/application/port/SubjectDetailQueryPort.java",
                "jdbc_adapter_sha256",
                "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
                        + "JdbcSubjectDetailQueryAdapter.java",
                "postgres_compatibility_test_sha256",
                "server/src/test/java/io/saksk/ti/integration/"
                        + "Phase4aSubjectContextJdbcCompatibilityIT.java",
                "postgres_fixture_sha256",
                "server/src/test/resources/db/phase4a/049-subject-context-seed.sql");
        JsonNode implementation = contract.path("evidence").path("implementation");
        for (Map.Entry<String, String> entry : implementationPaths.entrySet()) {
            assertThat(sha256(entry.getValue()))
                    .as(entry.getKey())
                    .isEqualTo(implementation.path(entry.getKey()).asString());
        }

        assertThat(sha256("docs/refactor/02-route-parity-matrix.csv"))
                .isEqualTo(contract.path("evidence").path("frozen_route_matrix")
                        .path("sha256").asString());
        assertThat(golden.path("legacy_source_attestation").path("frozen_route_matrix")
                        .path("selected_rows_sha256").asString())
                .isEqualTo(contract.path("evidence").path("frozen_route_matrix")
                        .path("selected_rows_sha256").asString());
        assertThat(sha256("docs/refactor/03-data-ownership.csv"))
                .isEqualTo(contract.path("evidence").path("data_ownership")
                        .path("sha256").asString());
        assertThat(sha256("docs/refactor/phase4a/approved-differences.md"))
                .isEqualTo(contract.path("evidence").path("approved_differences")
                        .path("sha256").asString());
        assertThat(contract.path("evidence").path("data_ownership")
                        .path("delta_required").asBoolean())
                .isFalse();
        assertThat(contract.path("evidence").path("approved_differences")
                        .path("new_difference_ids"))
                .isEmpty();

        JsonNode sources = golden.path("legacy_source_attestation")
                .path("subject_context_key_sources");
        for (JsonNode source : contract.path("evidence").path("legacy_sources")) {
            assertThat(sources.path(source.path("source").asString())
                            .path("sha256").asString())
                    .isEqualTo(source.path("sha256").asString());
        }
    }

    @Test
    void routesApplicationShapeAndJavaApiRemainInternalAndPending() throws Exception {
        JsonNode routeStatus = contract.path("route_status");
        assertThat(routeStatus.path("migrated_route_count_before").asInt()).isEqualTo(11);
        assertThat(routeStatus.path("migrated_route_count_after").asInt()).isEqualTo(11);
        assertThat(routeStatus.path("pending_route_count_before").asInt()).isEqualTo(600);
        assertThat(routeStatus.path("pending_route_count_after").asInt()).isEqualTo(600);
        assertThat(routeStatus.path("production_cutover_count").asInt()).isZero();
        assertThat(routeStatus.path("operations")).hasSize(2);

        Map<String, JsonNode> operations = indexBy(routeStatus.path("operations"), "route_id");
        assertThat(operations.keySet())
                .containsExactlyInAnyOrder("52ad8f899d66", "5548b24849ed");
        for (JsonNode operation : operations.values()) {
            assertThat(operation.path("method").asString()).isEqualTo("GET");
            assertThat(operation.path("target_module").asString()).isEqualTo("operations");
            assertThat(operation.path("migration_status").asString()).isEqualTo("pending");
            assertThat(operation.path("contract_maturity").asString()).isEqualTo("inferred");
            assertThat(operation.path("production_cutover").asBoolean()).isFalse();
        }

        JsonNode openApi = readJson("contracts/openapi.json");
        for (JsonNode operation : operations.values()) {
            JsonNode openApiOperation = openApi.path("paths")
                    .path(operation.path("path").asString()).path("get");
            String routeId = operation.path("route_id").asString();
            assertThat(openApiOperation.path("operationId").asString())
                    .isEqualTo("legacy_" + routeId + "_get");
            assertThat(openApiOperation.path("x-ti-contract-maturity").asString())
                    .isEqualTo("inferred");
            assertThat(openApiOperation.path("x-ti-migration").path("status").asString())
                    .isEqualTo("pending");
            assertThat(openApiOperation.path("x-ti-migration")
                            .path("targetModule").asString())
                    .isEqualTo("operations");
        }

        JsonNode effective = readJson(
                "docs/refactor/phase4a/effective-route-parity-status.json");
        assertThat(effective.path("effective").path("migration_status")
                        .path("migrated").asInt())
                .isEqualTo(11);
        assertThat(effective.path("effective").path("migration_status")
                        .path("pending").asInt())
                .isEqualTo(600);
        assertThat(fieldValues(
                        effective.path("effective").path("migrated_operations"), "route_id"))
                .doesNotContain("52ad8f899d66", "5548b24849ed");
        assertThat(Files.readString(
                        resolve("docs/refactor/phase4a/route-parity-delta.csv"),
                        StandardCharsets.UTF_8))
                .doesNotContain("52ad8f899d66", "5548b24849ed");

        JsonNode shape = readJson(
                "docs/refactor/phase4a/application-api-shape-status.json");
        assertThat(shape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(18);
        JsonNode catalog = findBy(shape.path("modules"), "module_id", "catalog");
        assertThat(strings(catalog.path("implemented_route_ids")))
                .doesNotContain("52ad8f899d66", "5548b24849ed");
        JsonNode apiShape = findBy(
                catalog.path("additional_public_apis"),
                "java_api",
                "io.saksk.ti.catalog.api.SubjectMetadataApplicationApi");
        assertThat(apiShape.path("lifecycle").asString())
                .isEqualTo("catalog_subject_inventory_and_context_query_boundary");
        assertThat(apiShape.path("direct_http_operation").asBoolean()).isFalse();
        assertThat(strings(apiShape.path("deferred_subject_context_http_route_ids")))
                .containsExactlyInAnyOrder("52ad8f899d66", "5548b24849ed");
        assertThat(apiShape.path("deferred_subject_context_http_owner").asString())
                .isEqualTo("operations");
        assertThat(apiShape.path("deferred_subject_context_http_phase").asString())
                .isEqualTo("4H");
        assertThat(apiShape.path("methods")).hasSize(2);

        Class<?> api = Class.forName("io.saksk.ti.catalog.api.SubjectMetadataApplicationApi");
        Class<?> view = Class.forName("io.saksk.ti.catalog.api.SubjectCatalogRecordView");
        assertThat(api.getDeclaredMethods()).hasSize(2);
        assertThat(api.getDeclaredMethod("findSubjectById", long.class)
                        .getGenericReturnType().getTypeName())
                .isEqualTo("java.util.Optional<io.saksk.ti.catalog.api.SubjectCatalogRecordView>");
        assertThat(Arrays.stream(view.getRecordComponents()).map(RecordComponent::getName))
                .containsExactly("id", "name");
        assertThat(Arrays.stream(view.getRecordComponents())
                        .map(component -> component.getGenericType().getTypeName()))
                .containsExactly("int", "java.lang.String");
    }

    @Test
    void goldenClosesAuthDataBoundariesRenderingFailureAndRequestEffects() {
        assertThat(golden.path("contract_id").asString())
                .isEqualTo("ti.phase4a.subject-context-read-goldens");
        assertThat(golden.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);
        assertThat(golden.path("case_count").asInt()).isEqualTo(44);
        assertThat(golden.path("case_payload_sha256").asString())
                .isEqualTo(GOLDEN_CASE_SHA256);
        assertThat(golden.path("document_payload_sha256").asString())
                .isEqualTo(GOLDEN_DOCUMENT_SHA256);
        assertThat(golden.path("cases")).hasSize(44);
        assertThat(golden.path("case_matrix").path("per_route").asInt()).isEqualTo(22);
        assertThat(golden.path("case_matrix").path("categories_per_route")
                        .path("data").asInt())
                .isEqualTo(13);

        Map<String, JsonNode> cases = indexBy(golden.path("cases"), "case_id");
        for (String route : List.of("questions-page", "duplicate-check-page")) {
            for (String prefix : List.of(
                    "auth-admin-session-found",
                    "auth-subject-admin-session-found")) {
                JsonNode sample = cases.get(prefix + "-" + route);
                assertThat(sample.path("response").path("status").asInt()).isEqualTo(200);
                assertThat(sample.path("observed_get_effects").path("sql")
                                .path("subject_context_select_attempts").asInt())
                        .isEqualTo(1);
                assertThat(sample.path("observed_get_effects")
                                .path("user_last_active_changed_user_ids"))
                        .hasSize(1);
            }
            for (String prefix : List.of(
                    "auth-ordinary-session-forbidden",
                    "auth-notification-admin-session-forbidden")) {
                JsonNode sample = cases.get(prefix + "-" + route);
                assertThat(sample.path("response").path("status").asInt()).isEqualTo(403);
                assertThat(sample.path("response").path("body").path("status").asString())
                        .isEqualTo("forbidden");
                assertThat(sample.path("observed_get_effects").path("sql")
                                .path("subject_context_select_attempts").asInt())
                        .isZero();
                assertThat(sample.path("observed_get_effects")
                                .path("user_last_active_changed_user_ids"))
                        .hasSize(1);
            }
            for (String prefix : List.of(
                    "auth-anonymous-redirect-login",
                    "auth-admin-bearer-only-redirect-login",
                    "auth-ordinary-session-plus-admin-bearer-redirect-login")) {
                JsonNode sample = cases.get(prefix + "-" + route);
                assertThat(sample.path("response").path("status").asInt()).isEqualTo(302);
                assertThat(strings(sample.path("response").path("headers").path("Location")))
                        .containsExactly("/login");
                assertThat(sample.path("observed_get_effects").path("sql")
                                .path("statement_count").asInt())
                        .isZero();
                assertThat(sample.path("observed_get_effects")
                                .path("user_last_active_changed_user_ids"))
                        .isEmpty();
            }

            assertThat(cases.get("data-zero-id-found-" + route)
                            .path("response").path("status").asInt())
                    .isEqualTo(200);
            assertThat(cases.get("data-zero-id-found-" + route)
                            .path("request").path("path_parameter")
                            .path("handler_subject_id").asInt())
                    .isZero();
            assertThat(cases.get("data-unicode-nd-id-found-" + route)
                            .path("request").path("path_parameter")
                            .path("python_int_value").asInt())
                    .isEqualTo(97204);
            assertThat(cases.get("data-leading-zero-id-found-" + route)
                            .path("response").path("status").asInt())
                    .isEqualTo(200);
            for (String prefix : List.of(
                    "data-missing-positive-id",
                    "data-int-max-missing",
                    "data-int-max-plus-one-missing",
                    "data-long-max-missing")) {
                JsonNode response = cases.get(prefix + "-" + route).path("response");
                assertThat(response.path("status").asInt()).isEqualTo(404);
                assertThat(response.path("body_kind").asString()).isEqualTo("text");
                assertThat(response.path("body").asString()).isEqualTo("科目不存在");
            }
            JsonNode overflow = cases.get(
                    "data-long-max-plus-one-bind-failure-" + route);
            assertThat(overflow.path("response").path("status").asInt()).isEqualTo(500);
            assertThat(overflow.path("response").path("body").path("message").asString())
                    .isEqualTo("An unexpected server error occurred.");
            assertThat(overflow.path("observed_get_effects").path("sql")
                            .path("subject_context_select_attempts").asInt())
                    .isEqualTo(1);

            for (String prefix : List.of(
                    "data-negative-route-miss",
                    "data-nonnumeric-route-miss")) {
                JsonNode routeMiss = cases.get(prefix + "-" + route);
                assertThat(routeMiss.path("response").path("status").asInt())
                        .isEqualTo(404);
                assertThat(routeMiss.path("response").path("body").asString())
                        .contains("404 - 页面未找到");
                assertThat(routeMiss.path("request").path("path_parameter")
                                .path("handler_subject_id").isNull())
                        .isTrue();
                assertThat(routeMiss.path("observed_get_effects").path("sql")
                                .path("subject_context_select_attempts").asInt())
                        .isZero();
                assertThat(routeMiss.path("observed_get_effects")
                                .path("user_last_active_changed_user_ids"))
                        .hasSize(1);
            }

            JsonNode htmlFault = cases.get("fault-injected-db-failure-html-" + route);
            JsonNode jsonFault = cases.get("fault-injected-db-failure-json-" + route);
            assertThat(htmlFault.path("response").path("status").asInt()).isEqualTo(500);
            assertThat(htmlFault.path("response").path("body").asString())
                    .contains("500 - 服务器错误").doesNotContain("synthetic");
            assertThat(jsonFault.path("response").path("status").asInt()).isEqualTo(500);
            assertThat(jsonFault.path("response").path("body_text").asString())
                    .doesNotContain("synthetic");
        }

        for (JsonNode sample : golden.path("cases")) {
            JsonNode effects = sample.path("observed_get_effects");
            assertThat(effects.path("subjects_unchanged").asBoolean()).isTrue();
            assertThat(effects.path("questions_unchanged").asBoolean()).isTrue();
            assertThat(effects.path("users_identity_unchanged").asBoolean()).isTrue();
            assertThat(effects.path("subjects_before").path("column_count").asInt())
                    .isEqualTo(9);
            assertThat(effects.path("questions_before").path("column_count").asInt())
                    .isEqualTo(15);
            assertThat(effects.path("sql").path("questions_select_attempts").asInt())
                    .isZero();
            assertThat(effects.path("sql").path("subjects_dml_attempts").asInt())
                    .isZero();
            assertThat(effects.path("sql").path("questions_dml_attempts").asInt())
                    .isZero();
            assertThat(effects.path("sql").path("ddl_attempts").asInt()).isZero();
            assertThat(effects.path("sql").path("unexpected_dml_attempts").asInt())
                    .isZero();
        }

        assertThat(golden.path("legacy_source_attestation")
                        .path("audited_template_callers"))
                .hasSize(4);
        assertThat(intValues(golden.path("legacy_source_attestation")
                        .path("audited_template_callers"), "line"))
                .containsExactly(347, 268, 788, 789);
    }

    @Test
    void postgresPlanClosesExactSqlBigintBindingAndPrimaryKeyPlan() {
        assertThat(plan.path("evidence_id").asString())
                .isEqualTo("ti.phase4a.subject-context-query-plan");
        assertThat(plan.path("schema_version").asInt()).isEqualTo(1);
        assertThat(strings(plan.path("route_migration_status").path("route_ids")))
                .containsExactly("52ad8f899d66", "5548b24849ed");
        assertThat(plan.path("route_migration_status").path("status").asString())
                .isEqualTo("pending");
        assertThat(plan.path("route_migration_status").path("production_cutover")
                        .asBoolean())
                .isFalse();

        JsonNode runtime = plan.path("runtime_sql_contract");
        assertThat(runtime.path("adapter_class").asString())
                .isEqualTo("io.saksk.ti.catalog.infrastructure.persistence."
                        + "JdbcSubjectDetailQueryAdapter");
        assertThat(runtime.path("sql_sha256").asString()).isEqualTo(RUNTIME_SQL_SHA256);
        assertThat(runtime.path("parameter_names")).hasSize(1);
        assertThat(runtime.path("parameter_postgres_types")
                        .path("subject_id").asString())
                .isEqualTo("bigint");
        assertThat(runtime.path("sql_statement_count").asInt()).isEqualTo(1);
        assertThat(runtime.path("maximum_result_rows").asInt()).isEqualTo(1);

        JsonNode environment = plan.path("environment");
        assertThat(environment.path("container_image").asString())
                .startsWith("postgres:18.4-alpine@sha256:");
        assertThat(environment.path("architecture").asString()).isEqualTo("arm64");
        assertThat(environment.path("network").asString()).isEqualTo("none");
        assertThat(environment.path("postgresql").path("server_version").asString())
                .isEqualTo("18.4");

        JsonNode actual = plan.path("data_set").path("actual");
        assertThat(actual.path("subjects").asInt()).isEqualTo(150002);
        assertThat(actual.path("minimum_subject_id").asInt()).isZero();
        assertThat(actual.path("maximum_subject_id").asInt())
                .isEqualTo(Integer.MAX_VALUE);
        assertThat(plan.path("data_set").path("index_definitions")).hasSize(1);
        assertThat(plan.path("data_set").path("index_definitions").get(0)
                        .path("name").asString())
                .isEqualTo("subjects_pkey");

        JsonNode measurement = plan.path("measurement");
        assertThat(measurement.path("observation_count").asInt()).isEqualTo(8);
        assertThat(measurement.path("runtime_query_count").asInt()).isEqualTo(1);
        assertThat(measurement.path("sql_statement_count_per_observation").asInt())
                .isEqualTo(1);
        assertThat(measurement.path("bound_parameter_count_per_observation").asInt())
                .isEqualTo(1);
        assertThat(measurement.path("maximum_result_rows_per_observation").asInt())
                .isEqualTo(1);
        assertThat(measurement.path("required_index").asString())
                .isEqualTo("subjects_pkey");

        List<Long> expectedIds = List.of(
                0L,
                1L,
                75000L,
                150000L,
                (long) Integer.MAX_VALUE,
                150001L,
                (long) Integer.MAX_VALUE + 1,
                Long.MAX_VALUE);
        List<Integer> expectedRows = List.of(1, 1, 1, 1, 1, 0, 0, 0);
        JsonNode observations = measurement.path("observations");
        assertThat(observations).hasSize(8);
        for (int index = 0; index < expectedIds.size(); index++) {
            JsonNode observation = observations.get(index);
            assertThat(observation.path("subject_id").asLong())
                    .isEqualTo(expectedIds.get(index));
            assertThat(observation.path("expected_rows").asInt())
                    .isEqualTo(expectedRows.get(index));
            assertThat(observation.path("sql_statement_count").asInt()).isEqualTo(1);
            assertThat(observation.path("binding").path("bound_parameter_count").asInt())
                    .isEqualTo(1);
            assertThat(observation.path("binding").path("named_parameter_count").asInt())
                    .isEqualTo(1);
            assertThat(observation.path("binding").path("parameters")
                            .path("subject_id").path("postgres_type").asString())
                    .isEqualTo("bigint");

            JsonNode summary = observation.path("plan_summary");
            assertThat(summary.path("root_node_type").asString()).isEqualTo("Index Scan");
            assertThat(summary.path("result_row_count").asInt())
                    .isEqualTo(expectedRows.get(index));
            assertThat(summary.path("root_actual_loops").asInt()).isEqualTo(1);
            assertThat(summary.path("maximum_actual_loops").asInt()).isEqualTo(1);
            assertThat(summary.path("node_count").asInt()).isLessThanOrEqualTo(2);
            assertThat(summary.path("maximum_depth").asInt()).isLessThanOrEqualTo(1);
            assertThat(summary.path("relation_scan_occurrences")
                            .path("subjects").asInt())
                    .isEqualTo(1);
            assertThat(strings(summary.path("index_names")))
                    .containsExactly("subjects_pkey");
            assertThat(observation.path("temp_blocks_observed")
                            .path("Temp Read Blocks").asDouble())
                    .isZero();
            assertThat(observation.path("temp_blocks_observed")
                            .path("Temp Written Blocks").asDouble())
                    .isZero();
        }
        assertThat(plan.path("interpretation").path("status").asString())
                .isEqualTo("observational_evidence_only");
    }

    private static void assertHashClosed(
            JsonNode inputs,
            JsonNode contractEvidence,
            String pathField,
            String hashField
    ) throws Exception {
        assertThat(sha256(inputs.path(pathField).asString()))
                .isEqualTo(inputs.path(hashField).asString())
                .isEqualTo(contractEvidence.path(hashField).asString());
    }

    private static JsonNode readJson(String relative) throws Exception {
        return JSON.readTree(Files.readString(resolve(relative), StandardCharsets.UTF_8));
    }

    private static Path resolve(String relative) throws Exception {
        Path resolved = tiJavaRoot.resolve(relative).normalize().toRealPath();
        if (!resolved.startsWith(tiJavaRoot)) {
            throw new IllegalArgumentException("path escaped Ti-Java: " + relative);
        }
        return resolved;
    }

    private static String sha256(String relative) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(Files.readAllBytes(resolve(relative))));
    }

    private static List<String> strings(JsonNode values) {
        if (!values.isArray()) {
            return List.of();
        }
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .map(JsonNode::asString)
                .toList();
    }

    private static List<String> fieldValues(JsonNode values, String field) {
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .map(value -> value.path(field).asString())
                .toList();
    }

    private static List<Integer> intValues(JsonNode values, String field) {
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .map(value -> value.path(field).asInt())
                .toList();
    }

    private static Map<String, JsonNode> indexBy(JsonNode values, String field) {
        Map<String, JsonNode> indexed = new LinkedHashMap<>();
        for (JsonNode value : values) {
            JsonNode previous = indexed.put(value.path(field).asString(), value);
            assertThat(previous).as("duplicate %s", field).isNull();
        }
        return indexed;
    }

    private static JsonNode findBy(JsonNode values, String field, String expected) {
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .filter(value -> value.path(field).asString().equals(expected))
                .findFirst()
                .orElseThrow();
    }
}
