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
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Closes the machine contract for the HTTP-neutral subject-inventory capability. */
class SubjectInventoryContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String LEGACY_COMMIT =
            "700006dfdfa063deb4387be572911e782bcea0d9";
    private static final String GOLDEN_SHA256 =
            "6ce049b13741c2f095ca988fe4f02afc58951389ebdc9c40cf092555d9bb5d07";
    private static final String GOLDEN_CASE_SHA256 =
            "f1ae276b9922cc66b1e8d2c613f060d7f30a4700cfac41a4b8a05f54adcaf0f9";
    private static final String PLAN_SHA256 =
            "f7c684273579e676b9da0024f76593ae9fb69bde47309e6d396c6fdf5a1cfb0c";
    private static final String RUNTIME_MANIFEST_SHA256 =
            "3c514f7f1ac79fe8d393f973fa19f136023be70e06968676f6a584d6199f09d7";
    private static final String RUNTIME_SQL_SHA256 =
            "16f06c965f73013065ade620b908c8e015f1265f64e7d40f2ab409f94402adb5";

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
        contract = readJson("docs/refactor/phase4a/subject-inventory-read-contract.json");
        golden = readJson("docs/refactor/phase4a/golden-subject-inventory-reads.json");
        plan = readJson(
                "docs/refactor/phase4a/subject-inventory-query-plan-evidence.json");
    }

    @Test
    void machineContractClosesEveryEvidenceHashAndCatalogBoundary() throws Exception {
        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4a.subject-inventory-read-contract");
        assertThat(contract.path("schema_version").asInt()).isEqualTo(1);
        assertThat(contract.path("status").asString())
                .isEqualTo("catalog_internal_capability_implemented_http_operation_deferred");
        assertThat(contract.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);

        JsonNode goldenEvidence = contract.path("evidence").path("golden");
        assertThat(goldenEvidence.path("source").asString())
                .isEqualTo("golden-subject-inventory-reads.json");
        assertThat(goldenEvidence.path("file_sha256").asString()).isEqualTo(GOLDEN_SHA256);
        assertThat(goldenEvidence.path("case_count").asInt()).isEqualTo(11);
        assertThat(goldenEvidence.path("case_payload_sha256").asString())
                .isEqualTo(GOLDEN_CASE_SHA256);
        assertThat(sha256("docs/refactor/phase4a/golden-subject-inventory-reads.json"))
                .isEqualTo(GOLDEN_SHA256);

        JsonNode planEvidence = contract.path("evidence").path("query_plan");
        assertThat(planEvidence.path("source").asString())
                .isEqualTo("subject-inventory-query-plan-evidence.json");
        assertThat(planEvidence.path("file_sha256").asString()).isEqualTo(PLAN_SHA256);
        assertThat(planEvidence.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(RUNTIME_MANIFEST_SHA256);
        assertThat(planEvidence.path("runtime_sql_sha256").asString())
                .isEqualTo(RUNTIME_SQL_SHA256);
        assertThat(planEvidence.path("runtime_query_count").asInt()).isEqualTo(1);
        assertThat(sha256(
                        "docs/refactor/phase4a/subject-inventory-query-plan-evidence.json"))
                .isEqualTo(PLAN_SHA256);

        JsonNode planInputs = plan.path("inputs");
        assertThat(planInputs.path("adapter").asString())
                .isEqualTo("server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
                        + "JdbcSubjectInventoryQueryAdapter.java");
        assertThat(sha256(planInputs.path("adapter").asString()))
                .isEqualTo(planInputs.path("adapter_sha256").asString())
                .isEqualTo(planEvidence.path("adapter_sha256").asString());
        assertThat(planInputs.path("runtime_sql_manifest").asString())
                .isEqualTo("server/target/phase4a-subject-inventory-runtime-sql.json");
        assertThat(planInputs.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(planEvidence.path("runtime_sql_manifest_sha256").asString());
        assertThat(planInputs.path("runtime_sql_exporter").asString())
                .isEqualTo("server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
                        + "SubjectInventoryRuntimeSqlManifestTest.java");
        assertThat(sha256(planInputs.path("runtime_sql_exporter").asString()))
                .isEqualTo(planInputs.path("runtime_sql_exporter_sha256").asString())
                .isEqualTo(planEvidence.path("runtime_sql_exporter_sha256").asString());
        assertThat(planInputs.path("capture_tool").asString())
                .isEqualTo("tools/capture_phase4a_subject_inventory_query_plan.py");
        assertThat(sha256(planInputs.path("capture_tool").asString()))
                .isEqualTo(planInputs.path("capture_tool_sha256").asString())
                .isEqualTo(planEvidence.path("capture_tool_sha256").asString());
        assertThat(planInputs.path("capture_tool_test").asString())
                .isEqualTo("tools/test_capture_phase4a_subject_inventory_query_plan.py");
        assertThat(sha256(planInputs.path("capture_tool_test").asString()))
                .isEqualTo(planInputs.path("capture_tool_test_sha256").asString())
                .isEqualTo(planEvidence.path("capture_tool_test_sha256").asString());

        JsonNode planObservation = plan.path("measurement").path("observation");
        assertThat(planObservation.path("source").asString())
                .isEqualTo(planInputs.path("adapter").asString());
        assertThat(sha256Utf8(planObservation.path("sql").asString()))
                .isEqualTo(planObservation.path("sql_sha256").asString())
                .isEqualTo(planEvidence.path("runtime_sql_sha256").asString());

        assertThat(sha256("docs/refactor/02-route-parity-matrix.csv"))
                .isEqualTo(contract.path("evidence").path("frozen_route_matrix")
                        .path("sha256").asString());
        assertThat(sha256("docs/refactor/03-data-ownership.csv"))
                .isEqualTo(contract.path("evidence").path("data_ownership")
                        .path("sha256").asString());
        assertThat(sha256("docs/refactor/phase4a/approved-differences.md"))
                .isEqualTo(contract.path("evidence").path("approved_differences")
                        .path("sha256").asString());
        assertThat(strings(contract.path("module_boundary").path("catalog_owned_tables")))
                .containsExactly("subjects", "questions");
        assertThat(contract.path("evidence").path("data_ownership")
                        .path("delta_required").asBoolean())
                .isFalse();
        assertThat(contract.path("evidence").path("approved_differences")
                        .path("new_difference_ids"))
                .isEmpty();
    }

    @Test
    void routeAndApplicationShapeRemainInternalAndPending() throws Exception {
        JsonNode operation = contract.path("route_status").path("operation");
        assertThat(operation.path("route_id").asString()).isEqualTo("6e1a36f5052d");
        assertThat(operation.path("method").asString()).isEqualTo("GET");
        assertThat(operation.path("path").asString()).isEqualTo("/admin/api/subjects");
        assertThat(operation.path("target_module").asString()).isEqualTo("operations");
        assertThat(operation.path("migration_status").asString()).isEqualTo("pending");
        assertThat(operation.path("contract_maturity").asString()).isEqualTo("observed");
        assertThat(operation.path("production_cutover").asBoolean()).isFalse();
        assertThat(contract.path("route_status").path("migrated_route_count_after").asInt())
                .isEqualTo(11);
        assertThat(contract.path("route_status").path("pending_route_count_after").asInt())
                .isEqualTo(600);

        JsonNode openApi = readJson("contracts/openapi.json");
        JsonNode openApiOperation = openApi.path("paths")
                .path("/admin/api/subjects").path("get");
        assertThat(openApiOperation.path("operationId").asString())
                .isEqualTo("legacy_6e1a36f5052d_get");
        assertThat(openApiOperation.path("x-ti-contract-maturity").asString())
                .isEqualTo("observed");
        assertThat(openApiOperation.path("x-ti-migration").path("status").asString())
                .isEqualTo("pending");
        assertThat(openApiOperation.path("x-ti-migration").path("targetModule").asString())
                .isEqualTo("operations");

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
                .doesNotContain("6e1a36f5052d");
        assertThat(Files.readString(
                        resolve("docs/refactor/phase4a/route-parity-delta.csv"),
                        StandardCharsets.UTF_8))
                .doesNotContain("6e1a36f5052d");

        JsonNode shape = readJson(
                "docs/refactor/phase4a/application-api-shape-status.json");
        assertThat(shape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(17);
        JsonNode catalog = findBy(shape.path("modules"), "module_id", "catalog");
        assertThat(strings(catalog.path("implemented_route_ids")))
                .doesNotContain("6e1a36f5052d");
        JsonNode apiShape = findBy(
                catalog.path("additional_public_apis"),
                "java_api",
                "io.saksk.ti.catalog.api.SubjectMetadataApplicationApi");
        assertThat(apiShape.path("lifecycle").asString())
                .isEqualTo("catalog_subject_inventory_query_boundary");
        assertThat(apiShape.path("direct_http_operation").asBoolean()).isFalse();
        assertThat(strings(apiShape.path("deferred_http_route_ids")))
                .containsExactly("6e1a36f5052d");
        assertThat(apiShape.path("deferred_http_owner").asString())
                .isEqualTo("operations");
        assertThat(apiShape.path("deferred_http_phase").asString()).isEqualTo("4H");
        assertThat(apiShape.path("methods")).hasSize(1);

        Class<?> api = Class.forName(
                "io.saksk.ti.catalog.api.SubjectMetadataApplicationApi");
        Class<?> view = Class.forName(
                "io.saksk.ti.catalog.api.SubjectInventorySummaryView");
        assertThat(api.getDeclaredMethod("listSubjectInventorySummaries")
                        .getGenericReturnType().getTypeName())
                .isEqualTo("java.util.List<io.saksk.ti.catalog.api.SubjectInventorySummaryView>");
        assertThat(Arrays.stream(view.getRecordComponents()).map(RecordComponent::getName))
                .containsExactly("id", "name", "isLocked", "questionCount");
        assertThat(Arrays.stream(view.getRecordComponents())
                        .map(component -> component.getGenericType().getTypeName()))
                .containsExactly("int", "java.lang.String", "java.lang.Boolean", "long");
    }

    @Test
    void goldenClosesAuthDataFailureEffectsAndAllAuditedWebCallers() {
        assertThat(golden.path("contract_id").asString())
                .isEqualTo("ti.phase4a.subject-inventory-read-goldens");
        assertThat(golden.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);
        assertThat(golden.path("case_count").asInt()).isEqualTo(11);
        assertThat(golden.path("case_payload_sha256").asString())
                .isEqualTo(GOLDEN_CASE_SHA256);
        assertThat(golden.path("cases")).hasSize(11);

        Map<String, JsonNode> cases = indexBy(golden.path("cases"), "case_id");
        assertThat(cases.keySet()).containsExactlyInAnyOrder(
                "auth-administrator",
                "auth-subject-admin",
                "auth-ordinary",
                "auth-anonymous",
                "auth-bearer-only",
                "auth-ordinary-session-plus-admin-bearer",
                "data-empty-tables",
                "data-single-subject",
                "data-multi-subject-edges",
                "fault-html",
                "fault-json");

        for (String id : List.of("auth-administrator", "auth-subject-admin")) {
            assertThat(cases.get(id).path("response").path("status").asInt()).isEqualTo(200);
            assertThat(cases.get(id).path("observed_get_effects").path("sql")
                            .path("subject_inventory_select_attempts").asInt())
                    .isEqualTo(1);
        }
        assertThat(cases.get("auth-ordinary").path("response").path("status").asInt())
                .isEqualTo(403);
        assertThat(cases.get("auth-ordinary").path("observed_get_effects").path("sql")
                        .path("subject_inventory_select_attempts").asInt())
                .isZero();
        assertThat(cases.get("auth-ordinary").path("observed_get_effects")
                        .path("surrounding_session_activity_write_observed").asBoolean())
                .isTrue();
        for (String id : List.of(
                "auth-anonymous",
                "auth-bearer-only",
                "auth-ordinary-session-plus-admin-bearer")) {
            JsonNode sample = cases.get(id);
            assertThat(sample.path("response").path("status").asInt()).isEqualTo(302);
            assertThat(strings(sample.path("response").path("headers").path("Location")))
                    .containsExactly("/login");
            assertThat(sample.path("observed_get_effects").path("sql")
                            .path("statement_count").asInt())
                    .isZero();
        }

        JsonNode multi = cases.get("data-multi-subject-edges").path("response").path("body");
        assertThat(ints(multi, "id")).containsExactly(-9, 0, 95001, 95002);
        assertThat(ints(multi, "question_count")).containsExactly(1, 0, 2, 1);
        assertThat(multi.get(0).path("is_locked").asInt()).isZero();
        assertThat(multi.get(1).path("is_locked").isNull()).isTrue();
        assertThat(multi.get(1).path("name").asString()).isEmpty();
        assertThat(multi.get(2).path("is_locked").asInt()).isEqualTo(1);
        assertThat(cases.get("data-empty-tables").path("response").path("body"))
                .isEmpty();
        assertThat(cases.get("fault-html").path("response").path("status").asInt())
                .isEqualTo(500);
        assertThat(cases.get("fault-json").path("response").path("status").asInt())
                .isEqualTo(500);

        for (JsonNode sample : golden.path("cases")) {
            JsonNode effects = sample.path("observed_get_effects");
            assertThat(effects.path("subjects_unchanged").asBoolean()).isTrue();
            assertThat(effects.path("questions_unchanged").asBoolean()).isTrue();
            assertThat(effects.path("subjects_before").path("column_count").asInt())
                    .isEqualTo(9);
            assertThat(effects.path("questions_before").path("column_count").asInt())
                    .isEqualTo(15);
            assertThat(effects.path("sql").path("subjects_dml_attempts").asInt()).isZero();
            assertThat(effects.path("sql").path("questions_dml_attempts").asInt()).isZero();
            assertThat(effects.path("sql").path("ddl_attempts").asInt()).isZero();
        }

        Set<String> attestedSources = new LinkedHashSet<>();
        golden.path("legacy_source_attestation").path("subject_inventory_key_sources")
                .properties().forEach(entry -> attestedSources.add(entry.getKey()));
        for (JsonNode caller : contract.path("evidence").path("audited_web_callers")) {
            assertThat(attestedSources).contains(caller.path("source").asString());
            assertThat(golden.path("legacy_source_attestation")
                            .path("subject_inventory_key_sources")
                            .path(caller.path("source").asString())
                            .path("sha256").asString())
                    .isEqualTo(caller.path("legacy_source_sha256").asString());
        }
    }

    @Test
    void postgresPlanClosesJavaSqlResultJoinCountsAndNoNPlusOne() {
        assertThat(plan.path("evidence_id").asString())
                .isEqualTo("ti.phase4a.subject-inventory-query-plan");
        assertThat(plan.path("schema_version").asInt()).isEqualTo(1);
        assertThat(strings(plan.path("route_migration_status").path("route_ids")))
                .containsExactly("6e1a36f5052d");
        assertThat(plan.path("route_migration_status").path("status").asString())
                .isEqualTo("pending");
        assertThat(plan.path("route_migration_status").path("production_cutover")
                        .asBoolean())
                .isFalse();
        assertThat(plan.path("inputs").path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(RUNTIME_MANIFEST_SHA256);

        JsonNode actual = plan.path("data_set").path("actual");
        assertThat(actual.path("subjects").asInt()).isEqualTo(5002);
        assertThat(actual.path("questions").asInt()).isEqualTo(150000);
        assertThat(actual.path("minimum_subject_id").asInt()).isEqualTo(-1);
        assertThat(actual.path("maximum_subject_id").asInt()).isEqualTo(5000);
        assertThat(actual.path("zero_question_subjects").asInt()).isEqualTo(1001);
        assertThat(actual.path("null_question_assignments").asInt()).isEqualTo(151);
        assertThat(actual.path("orphan_question_assignments").asInt()).isEqualTo(1);
        assertThat(actual.path("assigned_question_count").asInt()).isEqualTo(149848);

        JsonNode measurement = plan.path("measurement");
        assertThat(measurement.path("query_count").asInt()).isEqualTo(1);
        assertThat(measurement.path("sql_statement_count").asInt()).isEqualTo(1);
        assertThat(measurement.path("growth_with_result_count").asInt()).isZero();
        assertThat(measurement.path("n_plus_one_forbidden").asBoolean()).isTrue();
        JsonNode observation = measurement.path("observation");
        assertThat(observation.path("runtime_query_id").asString())
                .isEqualTo("subject-inventory-summaries");
        assertThat(observation.path("sql_sha256").asString()).isEqualTo(RUNTIME_SQL_SHA256);
        assertThat(observation.path("binding").path("bound_parameter_count").asInt())
                .isZero();
        assertThat(observation.path("binding").path("named_parameter_count").asInt())
                .isZero();

        JsonNode result = observation.path("runtime_result");
        assertThat(result.path("row_count").asInt()).isEqualTo(5002);
        assertThat(result.path("row_column_count").asInt()).isEqualTo(4);
        assertThat(intValues(result.path("first_ids_asc"))).containsExactly(-1, 0, 1);
        assertThat(intValues(result.path("last_ids_asc")))
                .containsExactly(4998, 4999, 5000);
        assertThat(result.path("strictly_ascending_by_id").asBoolean()).isTrue();
        assertThat(result.path("lock_value_counts").path("false").asInt())
                .isEqualTo(4500);
        assertThat(result.path("lock_value_counts").path("null").asInt())
                .isEqualTo(251);
        assertThat(result.path("lock_value_counts").path("true").asInt())
                .isEqualTo(251);
        assertThat(result.path("question_count_sum").asInt()).isEqualTo(149848);

        JsonNode summary = observation.path("plan_summary");
        assertThat(summary.path("result_row_count").asInt()).isEqualTo(5002);
        assertThat(summary.path("root_actual_loops").asInt()).isEqualTo(1);
        assertThat(summary.path("maximum_actual_loops").asInt()).isEqualTo(1);
        assertThat(summary.path("relation_scan_occurrences").path("subjects").asInt())
                .isEqualTo(1);
        assertThat(summary.path("relation_scan_occurrences").path("questions").asInt())
                .isEqualTo(1);
        assertThat(summary.path("node_type_counts").path("Aggregate").asInt())
                .isEqualTo(1);
        assertThat(summary.path("node_type_counts").path("Hash Join").asInt())
                .isEqualTo(1);
        assertThat(summary.path("node_count").asInt()).isLessThanOrEqualTo(8);
        assertThat(summary.path("maximum_depth").asInt()).isLessThanOrEqualTo(5);
        assertThat(observation.path("temp_blocks_observed").path("Temp Read Blocks")
                        .asDouble())
                .isZero();
        assertThat(observation.path("temp_blocks_observed").path("Temp Written Blocks")
                        .asDouble())
                .isZero();
        assertThat(plan.path("interpretation").path("status").asString())
                .isEqualTo("observational_evidence_only");
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

    private static List<Integer> intValues(JsonNode values) {
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .map(JsonNode::asInt)
                .toList();
    }

    private static List<String> fieldValues(JsonNode values, String field) {
        return java.util.stream.StreamSupport.stream(values.spliterator(), false)
                .map(value -> value.path(field).asString())
                .toList();
    }

    private static List<Integer> ints(JsonNode rows, String field) {
        return java.util.stream.StreamSupport.stream(rows.spliterator(), false)
                .map(row -> row.path(field).asInt())
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
