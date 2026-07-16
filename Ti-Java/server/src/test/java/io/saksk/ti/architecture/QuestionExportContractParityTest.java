package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

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
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Closes the machine contract for the HTTP-neutral question-export snapshot. */
class QuestionExportContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String LEGACY_COMMIT =
            "700006dfdfa063deb4387be572911e782bcea0d9";
    private static final String GOLDEN_SHA256 =
            "89ce148cb32d1ca26d2f9d617385ae86243cf264f6d33dede97018435d00530d";
    private static final String GOLDEN_CASE_SHA256 =
            "e1471ea32eb6e0e6ea5819f7df391a423ec3c036574205b801dab6fa09ba1584";
    private static final String GOLDEN_DOCUMENT_SHA256 =
            "6c818e96ff2fdc547920a532884c5e868628a06ad2ccca08ab514240dbdbcfea";
    private static final String PLAN_SHA256 =
            "96f04c1018f5c3a826c48972c2273096f8507e45900616ca6c842ee0318ae541";
    private static final String RUNTIME_MANIFEST_SHA256 =
            "1b29fce339b455d35ca2a11b4c445a898201f588610cc4fa0a96c676247f4fb0";
    private static final String SELECT_ALL_SHA256 =
            "bee0615897acb6a23e29d83b22853d13a80943c1fd964811a1f48b5f76a3b713";
    private static final String SELECT_BY_SUBJECT_SHA256 =
            "fb68333e48eda511974b5c0c956031e59d3f7f3942ec2230a3839841e9386a38";
    private static final String POSTGRES_COMPATIBILITY_TEST_SHA256 =
            "892198746dfd4eb0df58231208fe224ada0bc9c7cc5264342e9b9bf1601c901c";
    private static final String POSTGRES_FIXTURE_SHA256 =
            "63014c8b2ef876a14648d740e96a24c412d2160e14ca95618052cd96c39ba0c1";
    private static final String SQLITE_ENGINE =
            "SQLite from archived Flask testing configuration";
    private static final List<String> ROUTE_IDS =
            List.of("4a33d8e15da5", "712a47789f1d");

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
        contract = readJson("docs/refactor/phase4a/question-export-read-contract.json");
        golden = readJson("docs/refactor/phase4a/golden-question-export-reads.json");
        plan = readJson(
                "docs/refactor/phase4a/question-export-query-plan-evidence.json");
    }

    @Test
    void machineContractClosesGoldenPlanSourceSqlAndImplementationHashes() throws Exception {
        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4a.question-export-read-contract");
        assertThat(contract.path("schema_version").asInt()).isEqualTo(1);
        assertThat(contract.path("status").asString())
                .isEqualTo("catalog_raw_snapshot_implemented_http_operations_deferred");
        assertThat(contract.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);

        JsonNode goldenEvidence = contract.path("evidence").path("golden");
        assertThat(goldenEvidence.path("source").asString())
                .isEqualTo("golden-question-export-reads.json");
        assertThat(goldenEvidence.path("file_sha256").asString()).isEqualTo(GOLDEN_SHA256);
        assertThat(goldenEvidence.path("case_count").asInt()).isEqualTo(44);
        assertThat(goldenEvidence.path("case_payload_sha256").asString())
                .isEqualTo(GOLDEN_CASE_SHA256);
        assertThat(goldenEvidence.path("document_payload_sha256").asString())
                .isEqualTo(GOLDEN_DOCUMENT_SHA256);
        assertThat(sha256("docs/refactor/phase4a/golden-question-export-reads.json"))
                .isEqualTo(GOLDEN_SHA256);
        assertThat(sha256("tools/capture_phase4a_question_export_goldens.py"))
                .isEqualTo(goldenEvidence.path("capture_tool_sha256").asString());
        assertThat(sha256("tools/test_capture_phase4a_question_export_goldens.py"))
                .isEqualTo(goldenEvidence.path("capture_tool_test_sha256").asString());

        JsonNode planEvidence = contract.path("evidence").path("query_plan");
        assertThat(planEvidence.path("source").asString())
                .isEqualTo("question-export-query-plan-evidence.json");
        assertThat(planEvidence.path("file_sha256").asString()).isEqualTo(PLAN_SHA256);
        assertThat(planEvidence.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(RUNTIME_MANIFEST_SHA256);
        assertThat(planEvidence.path("runtime_query_count").asInt()).isEqualTo(2);
        assertThat(planEvidence.path("observation_count").asInt()).isEqualTo(9);
        assertThat(sha256(
                        "docs/refactor/phase4a/question-export-query-plan-evidence.json"))
                .isEqualTo(PLAN_SHA256);

        JsonNode inputs = plan.path("inputs");
        assertThat(inputs.path("runtime_sql_manifest").asString())
                .isEqualTo("server/target/phase4a-question-export-runtime-sql.json");
        assertThat(inputs.path("runtime_sql_manifest_sha256").asString())
                .isEqualTo(RUNTIME_MANIFEST_SHA256)
                .isEqualTo(planEvidence.path("runtime_sql_manifest_sha256").asString());
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

        JsonNode runtime = plan.path("runtime_sql_contract");
        assertThat(strings(runtime.path("query_ids_in_manifest_order")))
                .containsExactly("question-export-all", "question-export-by-subject");
        assertThat(runtime.path("explicit_column_count").asInt()).isEqualTo(10);
        assertThat(runtime.path("fixed_order").asString()).isEqualTo("q.id ASC");
        assertSqlHashClosed(
                runtime, planEvidence, "question-export-all", SELECT_ALL_SHA256);
        assertSqlHashClosed(
                runtime,
                planEvidence,
                "question-export-by-subject",
                SELECT_BY_SUBJECT_SHA256);

        Map<String, String> implementationPaths = Map.ofEntries(
                Map.entry(
                        "query_sha256",
                        "server/src/main/java/io/saksk/ti/catalog/api/QuestionExportQuery.java"),
                Map.entry(
                        "view_sha256",
                        "server/src/main/java/io/saksk/ti/catalog/api/QuestionExportRecordView.java"),
                Map.entry(
                        "application_api_sha256",
                        "server/src/main/java/io/saksk/ti/catalog/api/"
                                + "QuestionMetadataApplicationApi.java"),
                Map.entry(
                        "application_service_sha256",
                        "server/src/main/java/io/saksk/ti/catalog/application/"
                                + "QuestionMetadataQueryService.java"),
                Map.entry(
                        "query_port_sha256",
                        "server/src/main/java/io/saksk/ti/catalog/application/port/"
                                + "QuestionExportQueryPort.java"),
                Map.entry(
                        "jdbc_adapter_sha256",
                        "server/src/main/java/io/saksk/ti/catalog/infrastructure/persistence/"
                                + "JdbcQuestionExportQueryAdapter.java"),
                Map.entry(
                        "sql_contract_test_sha256",
                        "server/src/test/java/io/saksk/ti/catalog/infrastructure/persistence/"
                                + "QuestionExportSqlContractTest.java"),
                Map.entry(
                        "postgres_compatibility_test_sha256",
                        "server/src/test/java/io/saksk/ti/integration/"
                                + "Phase4aQuestionExportJdbcCompatibilityIT.java"),
                Map.entry(
                        "postgres_fixture_sha256",
                        "server/src/test/resources/db/phase4a/050-question-export-seed.sql"));
        JsonNode implementation = contract.path("evidence").path("implementation");
        for (Map.Entry<String, String> entry : implementationPaths.entrySet()) {
            assertThat(sha256(entry.getValue()))
                    .as(entry.getKey())
                    .isEqualTo(implementation.path(entry.getKey()).asString());
        }
        assertThat(implementation.path("postgres_compatibility_test_sha256").asString())
                .isEqualTo(POSTGRES_COMPATIBILITY_TEST_SHA256);
        assertThat(implementation.path("postgres_fixture_sha256").asString())
                .isEqualTo(POSTGRES_FIXTURE_SHA256);
        assertThat(inputs.path("fixture_sql_sha256").asString())
                .isEqualTo(plan.path("data_set").path("fixture_sql_sha256").asString());

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
    }

    @Test
    void routesShapeAndJavaApiRemainInternalAndPending() throws Exception {
        JsonNode routeStatus = contract.path("route_status");
        assertThat(routeStatus.path("migrated_route_count_before").asInt()).isEqualTo(11);
        assertThat(routeStatus.path("migrated_route_count_after").asInt()).isEqualTo(11);
        assertThat(routeStatus.path("pending_route_count_before").asInt()).isEqualTo(600);
        assertThat(routeStatus.path("pending_route_count_after").asInt()).isEqualTo(600);
        assertThat(routeStatus.path("production_cutover_count").asInt()).isZero();
        assertThat(routeStatus.path("operations")).hasSize(2);

        Map<String, JsonNode> operations = indexBy(routeStatus.path("operations"), "route_id");
        assertThat(operations.keySet()).containsExactlyInAnyOrderElementsOf(ROUTE_IDS);
        for (JsonNode operation : operations.values()) {
            assertThat(operation.path("method").asString()).isEqualTo("GET");
            assertThat(operation.path("target_module").asString()).isEqualTo("operations");
            assertThat(operation.path("migration_status").asString()).isEqualTo("pending");
            assertThat(operation.path("contract_maturity").asString()).isEqualTo("inferred");
            assertThat(operation.path("production_cutover").asBoolean()).isFalse();
        }

        JsonNode openApi = readJson("contracts/openapi.json");
        for (JsonNode operation : operations.values()) {
            String routeId = operation.path("route_id").asString();
            JsonNode openApiOperation = openApi.path("paths")
                    .path(operation.path("path").asString()).path("get");
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
                .doesNotContainAnyElementsOf(ROUTE_IDS);
        assertThat(Files.readString(
                        resolve("docs/refactor/phase4a/route-parity-delta.csv"),
                        StandardCharsets.UTF_8))
                .doesNotContain(ROUTE_IDS.get(0), ROUTE_IDS.get(1));

        JsonNode shape = readJson(
                "docs/refactor/phase4a/application-api-shape-status.json");
        assertThat(shape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(19);
        JsonNode catalog = findBy(shape.path("modules"), "module_id", "catalog");
        assertThat(strings(catalog.path("implemented_route_ids")))
                .doesNotContainAnyElementsOf(ROUTE_IDS);
        JsonNode apiShape = findBy(
                catalog.path("additional_public_apis"),
                "java_api",
                "io.saksk.ti.catalog.api.QuestionMetadataApplicationApi");
        assertThat(apiShape.path("lifecycle").asString())
                .isEqualTo("catalog_question_metadata_count_detail_summary_and_export_query_boundary");
        assertThat(apiShape.path("direct_http_operation").asBoolean()).isFalse();
        assertThat(strings(apiShape.path("deferred_question_export_http_route_ids")))
                .containsExactlyInAnyOrderElementsOf(ROUTE_IDS);
        assertThat(apiShape.path("deferred_question_export_http_owner").asString())
                .isEqualTo("operations");
        assertThat(apiShape.path("deferred_question_export_phase").asString())
                .isEqualTo("4H");
        assertThat(apiShape.path("methods")).hasSize(5);
        JsonNode methodShape = findBy(
                apiShape.path("methods"), "name", "listQuestionExportRecords");
        assertThat(methodShape.path("generic_return_type").asString())
                .isEqualTo("java.util.List<io.saksk.ti.catalog.api.QuestionExportRecordView>");
        assertThat(strings(methodShape.path("parameter_types")))
                .containsExactly("io.saksk.ti.catalog.api.QuestionExportQuery");

        Class<?> query = Class.forName("io.saksk.ti.catalog.api.QuestionExportQuery");
        Class<?> view = Class.forName("io.saksk.ti.catalog.api.QuestionExportRecordView");
        Class<?> api = Class.forName("io.saksk.ti.catalog.api.QuestionMetadataApplicationApi");
        assertThat(Arrays.stream(query.getRecordComponents()).map(RecordComponent::getName))
                .containsExactly("subjectId");
        assertThat(Arrays.stream(query.getRecordComponents())
                        .map(component -> component.getGenericType().getTypeName()))
                .containsExactly("java.util.Optional<java.lang.Integer>");
        assertThat(Arrays.stream(view.getRecordComponents()).map(RecordComponent::getName))
                .containsExactly(
                        "id",
                        "subjectId",
                        "subjectName",
                        "type",
                        "content",
                        "optionsRaw",
                        "answerRaw",
                        "analysis",
                        "difficulty",
                        "tagsRaw");
        assertThat(Arrays.stream(view.getRecordComponents())
                        .map(component -> component.getGenericType().getTypeName()))
                .containsExactly(
                        "long",
                        "java.lang.Long",
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.String",
                        "java.lang.Integer",
                        "java.lang.String");
        assertThat(api.getDeclaredMethods()).hasSize(5);
        assertThat(api.getDeclaredMethod("listQuestionExportRecords", query)
                        .getGenericReturnType().getTypeName())
                .isEqualTo("java.util.List<io.saksk.ti.catalog.api.QuestionExportRecordView>");
    }

    @Test
    void goldenClosesAllCasesAuthenticationStopsAndReadOnlyEffects() {
        assertThat(golden.path("contract_id").asString())
                .isEqualTo("ti.phase4a.question-export-read-goldens");
        assertThat(golden.path("schema_version").asInt()).isEqualTo(1);
        assertThat(golden.path("legacy_commit").asString()).isEqualTo(LEGACY_COMMIT);
        assertThat(golden.path("case_count").asInt()).isEqualTo(44);
        assertThat(golden.path("case_payload_sha256").asString())
                .isEqualTo(GOLDEN_CASE_SHA256);
        assertThat(golden.path("document_payload_sha256").asString())
                .isEqualTo(GOLDEN_DOCUMENT_SHA256);
        assertThat(golden.path("cases")).hasSize(44);

        Map<String, JsonNode> cases = indexBy(golden.path("cases"), "case_id");
        assertThat(cases.keySet())
                .containsExactlyInAnyOrderElementsOf(expectedGoldenCaseIds());
        for (String suffix : List.of("modern", "legacy")) {
            for (String prefix : List.of(
                    "auth-administrator-session",
                    "auth-subject-admin-session")) {
                JsonNode sample = cases.get(prefix + "-" + suffix);
                assertThat(sample.path("response").path("status").asInt()).isEqualTo(200);
                assertThat(sample.path("observed_get_effects").path("sql")
                                .path("export_select_attempts").asInt())
                        .isEqualTo(1);
                assertThat(sample.path("observed_get_effects")
                                .path("user_last_active_changed_user_ids"))
                        .hasSize(1);
            }
            for (String prefix : List.of(
                    "auth-ordinary-session-forbidden",
                    "auth-notification-admin-session-forbidden")) {
                JsonNode sample = cases.get(prefix + "-" + suffix);
                assertThat(sample.path("response").path("status").asInt()).isEqualTo(403);
                assertThat(sample.path("response").path("body").path("status").asString())
                        .isEqualTo("forbidden");
                assertThat(sample.path("observed_get_effects").path("sql")
                                .path("export_select_attempts").asInt())
                        .isZero();
                assertThat(sample.path("observed_get_effects")
                                .path("user_last_active_changed_user_ids"))
                        .hasSize(1);
            }
            for (String prefix : List.of(
                    "auth-anonymous-redirect-login",
                    "auth-administrator-bearer-only-redirect-login",
                    "auth-ordinary-session-plus-administrator-bearer-redirect-login")) {
                JsonNode sample = cases.get(prefix + "-" + suffix);
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

            JsonNode htmlFault = cases.get("fault-html-" + suffix);
            JsonNode jsonFault = cases.get("fault-json-" + suffix);
            assertThat(htmlFault.path("response").path("status").asInt()).isEqualTo(500);
            assertThat(htmlFault.path("response").path("body").asString())
                    .contains("500 - 服务器错误").doesNotContain("synthetic");
            assertThat(jsonFault.path("response").path("status").asInt()).isEqualTo(500);
            assertThat(jsonFault.path("response").path("body").path("message").asString())
                    .isEqualTo("An unexpected server error occurred.");
        }

        for (JsonNode sample : golden.path("cases")) {
            JsonNode effects = sample.path("observed_get_effects");
            assertThat(effects.path("engine").asString()).isEqualTo(SQLITE_ENGINE);
            assertThat(effects.path("facts_match_case_fixture").asBoolean()).isTrue();
            assertThat(effects.path("facts_unchanged").asBoolean()).isTrue();
            assertThat(effects.path("facts_before").path("questions")
                            .path("column_count").asInt())
                    .isEqualTo(15);
            assertThat(effects.path("facts_before").path("subjects")
                            .path("column_count").asInt())
                    .isEqualTo(9);
            assertThat(effects.path("facts_before").path("user_identity")
                            .path("column_count").asInt())
                    .isEqualTo(7);
            assertThat(effects.path("sql").path("fact_dml_attempts").asInt()).isZero();
            assertThat(effects.path("sql").path("ddl_attempts").asInt()).isZero();
        }
    }

    @Test
    void goldenClosesIgnoredTypeLockedSubjectsRawProjectionEnvelopesAndEngineBoundary() {
        Map<String, JsonNode> cases = indexBy(golden.path("cases"), "case_id");
        for (String suffix : List.of("modern", "legacy")) {
            JsonNode exact = body(cases, "subject-exact-" + suffix);
            JsonNode ignored = body(cases, "subject-exact-type-ignored-" + suffix);
            assertThat(ignored.path("count").asInt()).isEqualTo(8);
            assertThat(ignored.path("questions")).isEqualTo(exact.path("questions"));
            assertThat(cases.get("subject-exact-type-ignored-" + suffix)
                            .path("request").path("query"))
                    .hasSize(2);
            assertThat(fieldValues(
                            cases.get("subject-exact-type-ignored-" + suffix)
                                    .path("request").path("query"),
                            "name"))
                    .containsExactly("subject_id", "type");

            JsonNode all = body(cases, "subject-missing-default-" + suffix);
            Map<Long, JsonNode> questions = indexByLong(all.path("questions"), "id");
            assertThat(golden.path("fixture").path("locked_subject_ids"))
                    .hasSize(1);
            assertThat(golden.path("fixture").path("locked_subject_ids").get(0).asInt())
                    .isEqualTo(98203);
            assertThat(questions.get(98312L).path("subject_id").asInt()).isEqualTo(98203);
            assertThat(questions.get(98312L).path("subject_name").asString())
                    .isEqualTo("其他科目");

            assertThat(body(cases, "subject-empty-" + suffix).path("count").asInt())
                    .isEqualTo(14);
            assertThat(body(cases, "subject-empty-" + suffix)
                            .path("meta").has("subject_id"))
                    .isFalse();
            Map<String, String> sqliteRawBoundaries = Map.of(
                    "subject-blank", " ",
                    "subject-invalid", "not-an-integer",
                    "subject-unicode-nd", "٩٨٢٠١",
                    "subject-int4-out-of-range", "2147483648");
            for (Map.Entry<String, String> boundary : sqliteRawBoundaries.entrySet()) {
                JsonNode boundaryBody = body(cases, boundary.getKey() + "-" + suffix);
                assertThat(boundaryBody.path("count").asInt()).isZero();
                assertThat(boundaryBody.path("meta").path("subject_id").asString())
                        .isEqualTo(boundary.getValue());
            }
        }

        JsonNode modern = body(cases, "subject-missing-default-modern");
        JsonNode legacy = body(cases, "subject-missing-default-legacy");
        assertThat(fieldNames(modern)).containsExactlyInAnyOrder(
                "count", "meta", "questions", "status", "request_id", "message", "data");
        assertThat(modern.path("status").asString()).isEqualTo("success");
        assertThat(modern.path("message").asString()).isEmpty();
        assertThat(modern.path("data").path("count")).isEqualTo(modern.path("count"));
        assertThat(modern.path("data").path("meta")).isEqualTo(modern.path("meta"));
        assertThat(modern.path("data").path("questions"))
                .isEqualTo(modern.path("questions"));
        assertThat(fieldNames(legacy))
                .containsExactlyInAnyOrder("count", "meta", "questions", "request_id");
        assertThat(legacy.has("status")).isFalse();
        assertThat(legacy.has("message")).isFalse();
        assertThat(legacy.has("data")).isFalse();
        assertThat(legacy.path("questions")).isEqualTo(modern.path("questions"));

        Map<Long, JsonNode> questions = indexByLong(modern.path("questions"), "id");
        JsonNode defaults = questions.get(98302L);
        assertThat(defaults.path("type").asString()).isEmpty();
        assertThat(defaults.path("content").asString()).isEmpty();
        assertThat(defaults.path("analysis").asString()).isEmpty();
        assertThat(defaults.path("difficulty").asInt()).isEqualTo(1);
        assertEmptyArrays(defaults, "options", "answer", "tags");
        assertThat(questions.get(0L).path("difficulty").asInt()).isEqualTo(1);

        JsonNode jsonNull = questions.get(98303L);
        assertThat(jsonNull.path("options").isNull()).isTrue();
        assertThat(jsonNull.path("answer").isNull()).isTrue();
        assertThat(jsonNull.path("tags").isNull()).isTrue();
        assertEmptyArrays(questions.get(98304L), "options", "answer", "tags");
        assertEmptyArrays(questions.get(98305L), "options", "answer", "tags");
        assertThat(questions.get(98306L).path("options")).hasSize(2);
        assertThat(questions.get(98306L).path("answer")).hasSize(3);
        assertThat(questions.get(98306L).path("tags")).hasSize(2);
        assertThat(questions.get(98307L).path("options").path("A").asString())
                .isEqualTo("甲");
        assertThat(questions.get(98307L).path("answer").path("value").asString())
                .isEqualTo("A");
        assertThat(questions.get(98307L).path("tags").path("topic").asString())
                .isEqualTo("代数");
        assertThat(questions.get(98308L).path("options").asString()).isEqualTo("单值");
        assertThat(questions.get(98308L).path("answer").asInt()).isEqualTo(7);
        assertThat(questions.get(98308L).path("tags").asBoolean()).isFalse();
        for (long id : List.of(98309L, 98310L, 98311L)) {
            assertThat(questions.get(id).path("subject_name").asString())
                    .isEqualTo("默认科目");
        }

        assertThat(golden.path("engine_scope").path("captured").asString())
                .contains("SQLite");
        assertThat(golden.path("engine_scope").path("engine_specific_edges"))
                .hasSize(4);
        assertThat(golden.path("engine_scope").path("non_claim").asString())
                .contains("not claimed as PostgreSQL behavior");
        assertThat(contract.path("engine_boundary").path("engine_specific_claims"))
                .hasSize(4);
        assertThat(contract.path("engine_boundary").path("required_phase4h_evidence")
                        .asString())
                .contains("PostgreSQL 16.14 and 18.4");
    }

    @Test
    void postgresPlanClosesTwoSqlVariantsNineTypedObservationsAndZeroTemp() {
        assertThat(plan.path("evidence_id").asString())
                .isEqualTo("ti.phase4a.question-export-query-plan");
        assertThat(plan.path("schema_version").asInt()).isEqualTo(1);
        assertThat(plan.path("scope").asString())
                .isEqualTo("catalog-owned-question-export-snapshot-internal-read-primitive");

        JsonNode runtime = plan.path("runtime_sql_contract");
        assertThat(runtime.path("adapter_class").asString())
                .isEqualTo("io.saksk.ti.catalog.infrastructure.persistence."
                        + "JdbcQuestionExportQueryAdapter");
        assertThat(runtime.path("explicit_column_count").asInt()).isEqualTo(10);
        assertThat(strings(runtime.path("explicit_columns"))).containsExactly(
                "q.id",
                "q.subject_id",
                "s.name as subject_name",
                "q.type",
                "q.content",
                "q.options",
                "q.answer",
                "q.analysis",
                "q.difficulty",
                "q.tags");
        assertThat(runtime.path("fixed_order").asString()).isEqualTo("q.id ASC");
        assertThat(runtime.path("sql_statement_count_per_execution").asInt())
                .isEqualTo(1);
        assertThat(runtime.path("parameter_postgres_types")
                        .path("question-export-all"))
                .isEmpty();
        assertThat(runtime.path("parameter_postgres_types")
                        .path("question-export-by-subject")
                        .path("subject_id").asString())
                .isEqualTo("integer");

        JsonNode measurement = plan.path("measurement");
        assertThat(measurement.path("runtime_query_count").asInt()).isEqualTo(2);
        assertThat(measurement.path("observation_count").asInt()).isEqualTo(9);
        assertThat(measurement.path("sql_statement_count_per_execution").asInt())
                .isEqualTo(1);
        assertThat(measurement.path("required_root_actual_loops").asInt()).isEqualTo(1);
        assertThat(measurement.path("required_temp_blocks").asInt()).isZero();

        Map<String, JsonNode> observations =
                indexBy(measurement.path("observations"), "observation_id");
        assertThat(observations.keySet()).containsExactlyInAnyOrder(
                "all-questions",
                "first-subject",
                "middle-subject",
                "last-subject",
                "zero-subject",
                "negative-subject",
                "missing-subject-reference",
                "integer-min-subject",
                "integer-max-subject");
        Map<String, Integer> filteredSubjectLoops = Map.of(
                "first-subject", 1,
                "middle-subject", 1,
                "last-subject", 1,
                "zero-subject", 1,
                "negative-subject", 1,
                "missing-subject-reference", 1,
                "integer-min-subject", 0,
                "integer-max-subject", 0);
        for (JsonNode observation : observations.values()) {
            assertThat(observation.path("sql_statement_count").asInt()).isEqualTo(1);
            JsonNode binding = observation.path("binding");
            assertThat(binding.path("mode").asString()).isEqualTo("prepare-execute");
            assertThat(binding.path("runtime_statement_count").asInt()).isEqualTo(1);
            if (observation.path("runtime_query_id").asString()
                    .equals("question-export-all")) {
                assertThat(binding.path("bound_parameter_count").asInt()).isZero();
                assertThat(binding.path("named_parameter_count").asInt()).isZero();
                assertThat(binding.path("parameters")).isEmpty();
            } else {
                assertThat(observation.path("runtime_query_id").asString())
                        .isEqualTo("question-export-by-subject");
                assertThat(binding.path("bound_parameter_count").asInt()).isEqualTo(1);
                assertThat(binding.path("named_parameter_count").asInt()).isEqualTo(1);
                assertThat(strings(binding.path("occurrence_names")))
                        .containsExactly("subject_id");
                assertThat(binding.path("parameters").path("subject_id")
                                .path("bind_kind").asString())
                        .isEqualTo("jdbc-scalar");
                assertThat(binding.path("parameters").path("subject_id")
                                .path("postgres_type").asString())
                        .isEqualTo("integer");
            }

            JsonNode result = observation.path("runtime_result");
            assertThat(result.path("row_column_count").asInt()).isEqualTo(10);
            assertThat(result.path("strictly_ascending_by_id").asBoolean()).isTrue();
            assertThat(observation.path("plan_summary").path("result_row_count").asInt())
                    .isEqualTo(result.path("row_count").asInt());
            assertThat(observation.path("plan_summary").path("root_actual_loops").asInt())
                    .isEqualTo(1);
            assertThat(observation.path("plan_summary").path("relation_scan_occurrences")
                            .path("questions").asInt())
                    .isEqualTo(1);
            assertThat(observation.path("plan_summary").path("relation_scan_occurrences")
                            .path("subjects").asInt())
                    .isEqualTo(1);
            assertThat(observation.path("plan_summary").path("relation_scan_actual_loops")
                            .path("questions"))
                    .hasSize(1);
            assertThat(observation.path("plan_summary").path("relation_scan_actual_loops")
                            .path("questions").get(0).asInt())
                    .isEqualTo(1);
            assertThat(observation.path("plan_summary").path("join_nodes"))
                    .hasSize(1);
            assertThat(observation.path("plan_summary").path("join_nodes").get(0)
                            .path("join_type").asString())
                    .isEqualTo("Left");
            assertThat(observation.path("plan_summary").path("join_nodes").get(0)
                            .path("actual_loops").asInt())
                    .isEqualTo(1);
            assertThat(observation.path("temp_blocks_observed")
                            .path("Temp Read Blocks").asDouble())
                    .isZero();
            assertThat(observation.path("temp_blocks_observed")
                            .path("Temp Written Blocks").asDouble())
                    .isZero();
        }

        JsonNode allQuestions = observations.get("all-questions");
        assertThat(allQuestions.path("plan_summary").path("node_type_counts")
                        .path("Memoize").asInt())
                .isEqualTo(1);
        assertThat(allQuestions.path("plan_summary").path("relation_scan_actual_loops")
                        .path("subjects"))
                .hasSize(1);
        assertThat(allQuestions.path("plan_summary").path("relation_scan_actual_loops")
                        .path("subjects").get(0).asInt())
                .isEqualTo(5004);
        JsonNode memoize = findBy(
                allQuestions.path("normalized_explain_analyze").path("Plan").path("Plans"),
                "Node Type",
                "Memoize");
        assertThat(memoize.path("Cache Misses").asInt()).isEqualTo(5004);
        assertThat(memoize.path("Cache Hits").asInt()).isEqualTo(144996);
        for (Map.Entry<String, Integer> entry : filteredSubjectLoops.entrySet()) {
            JsonNode subjectLoops = observations.get(entry.getKey())
                    .path("plan_summary").path("relation_scan_actual_loops")
                    .path("subjects");
            assertThat(subjectLoops).as(entry.getKey()).hasSize(1);
            assertThat(subjectLoops.get(0).asInt())
                    .as(entry.getKey())
                    .isEqualTo(entry.getValue());
        }

        JsonNode cross = plan.path("cross_observation_assertions");
        assertThat(cross.path("status").asString()).isEqualTo("passed");
        assertThat(strings(cross.path("runtime_variant_coverage")))
                .containsExactlyInAnyOrder("question-export-all", "question-export-by-subject");
        assertThat(cross.path("bind_count_independent_of_result_row_count").asBoolean())
                .isTrue();
        assertThat(cross.path("strict_id_asc_all_nontrivial_results").asBoolean())
                .isTrue();
        assertThat(cross.path("ten_columns_all_observations").asBoolean()).isTrue();
        assertThat(cross.path("zero_temp_blocks_all_observations").asBoolean()).isTrue();

        JsonNode planContract = contract.path("query_plan_contract");
        assertThat(planContract.path("environment").asString())
                .isEqualTo("PostgreSQL 18.4 pinned digest on ARM64 with network none, "
                        + "parallel gather disabled and public deterministic synthetic data");
        assertThat(planContract.path("data_set").path("questions").asInt())
                .isEqualTo(150000);
        assertThat(planContract.path("data_set").path("subjects").asInt())
                .isEqualTo(5002);
        assertThat(planContract.path("data_set").path("production_index_approval")
                        .asBoolean())
                .isFalse();

        JsonNode allContract = planContract.path("runtime_queries")
                .path("question-export-all");
        assertThat(allContract.path("result_rows").asInt()).isEqualTo(150000);
        assertThat(allContract.path("result_columns").asInt()).isEqualTo(10);
        assertThat(allContract.path("statement_count").asInt()).isEqualTo(1);
        assertThat(allContract.path("bind_count").asInt()).isZero();
        assertThat(allContract.path("strict_id_asc").asBoolean()).isTrue();
        assertThat(allContract.path("subject_probe_shape").asString())
                .isEqualTo("one Memoize node with 5004 distinct subject-key misses/probes "
                        + "across the full result");

        JsonNode filteredContract = planContract.path("runtime_queries")
                .path("question-export-by-subject");
        assertThat(filteredContract.path("observation_count").asInt()).isEqualTo(8);
        assertThat(filteredContract.path("result_columns").asInt()).isEqualTo(10);
        assertThat(filteredContract.path("statement_count").asInt()).isEqualTo(1);
        assertThat(filteredContract.path("bind_count").asInt()).isEqualTo(1);
        assertThat(filteredContract.path("bind_postgres_type").asString())
                .isEqualTo("integer");
        assertThat(filteredContract.path("strict_id_asc").asBoolean()).isTrue();
        assertThat(filteredContract.path("subject_probe_shape").asString())
                .isEqualTo("zero subject probes for an empty filtered result and one subject "
                        + "probe for a non-empty filtered result");

        JsonNode gates = planContract.path("gates");
        assertThat(gates.path("runtime_query_count").asInt()).isEqualTo(2);
        assertThat(gates.path("observation_count").asInt()).isEqualTo(9);
        assertThat(gates.path("sql_statement_count_per_execution").asInt()).isEqualTo(1);
        assertThat(gates.path("explicit_result_columns").asInt()).isEqualTo(10);
        assertThat(gates.path("questions_scan_nodes_per_observation").asInt())
                .isEqualTo(1);
        assertThat(gates.path("subjects_scan_nodes_per_observation").asInt())
                .isEqualTo(1);
        assertThat(gates.path("left_join_nodes_per_observation").asInt()).isEqualTo(1);
        assertThat(gates.path("root_actual_loops").asInt()).isEqualTo(1);
        assertThat(gates.path("full_result_memoize_distinct_subject_probes").asInt())
                .isEqualTo(5004);
        assertThat(gates.path("filtered_result_subject_probe_minimum").asInt()).isZero();
        assertThat(gates.path("filtered_result_subject_probe_maximum").asInt())
                .isEqualTo(1);
        assertThat(gates.path("temp_read_blocks").asInt()).isZero();
        assertThat(gates.path("temp_written_blocks").asInt()).isZero();
        assertThat(gates.path("strict_id_asc_for_every_nontrivial_result").asBoolean())
                .isTrue();
        assertThat(planContract.path("interpretation").asString())
                .isEqualTo("bounded PostgreSQL 18.4 synthetic evidence only; it is not a "
                        + "production latency SLA, capacity claim, production index "
                        + "recommendation or route migration authorization");
        assertThat(plan.path("interpretation").path("status").asString())
                .isEqualTo("bounded_synthetic_plan_evidence_only");
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

    private static void assertSqlHashClosed(
            JsonNode runtime,
            JsonNode contractEvidence,
            String queryId,
            String expectedHash
    ) {
        assertThat(runtime.path("query_sql_sha256").path(queryId).asString())
                .isEqualTo(expectedHash)
                .isEqualTo(contractEvidence.path("runtime_sql_sha256")
                        .path(queryId).asString());
    }

    private static void assertEmptyArrays(JsonNode value, String... fields) {
        for (String field : fields) {
            assertThat(value.path(field).isArray()).as(field).isTrue();
            assertThat(value.path(field)).as(field).isEmpty();
        }
    }

    private static JsonNode body(Map<String, JsonNode> cases, String caseId) {
        JsonNode sample = Objects.requireNonNull(cases.get(caseId), caseId);
        JsonNode body = sample.path("response").path("body");
        assertThat(body.isObject()).as(caseId).isTrue();
        return body;
    }

    private static List<String> expectedGoldenCaseIds() {
        List<String> baseIds = List.of(
                "auth-administrator-session",
                "auth-subject-admin-session",
                "auth-ordinary-session-forbidden",
                "auth-notification-admin-session-forbidden",
                "auth-anonymous-redirect-login",
                "auth-administrator-bearer-only-redirect-login",
                "auth-ordinary-session-plus-administrator-bearer-redirect-login",
                "data-empty-table",
                "subject-missing-default",
                "subject-empty",
                "subject-blank",
                "subject-zero",
                "subject-negative",
                "subject-exact",
                "subject-exact-type-ignored",
                "subject-no-match",
                "subject-repeated-first-value",
                "subject-invalid",
                "subject-unicode-nd",
                "subject-int4-out-of-range",
                "fault-html",
                "fault-json");
        List<String> expected = new ArrayList<>(44);
        for (String suffix : List.of("modern", "legacy")) {
            for (String baseId : baseIds) {
                expected.add(baseId + "-" + suffix);
            }
        }
        return expected;
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

    private static List<String> fieldNames(JsonNode value) {
        List<String> names = new ArrayList<>();
        value.properties().forEach(entry -> names.add(entry.getKey()));
        return names;
    }

    private static Map<String, JsonNode> indexBy(JsonNode values, String field) {
        Map<String, JsonNode> indexed = new LinkedHashMap<>();
        for (JsonNode value : values) {
            JsonNode previous = indexed.put(value.path(field).asString(), value);
            assertThat(previous).as("duplicate %s", field).isNull();
        }
        return indexed;
    }

    private static Map<Long, JsonNode> indexByLong(JsonNode values, String field) {
        Map<Long, JsonNode> indexed = new LinkedHashMap<>();
        for (JsonNode value : values) {
            JsonNode previous = indexed.put(value.path(field).asLong(), value);
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
