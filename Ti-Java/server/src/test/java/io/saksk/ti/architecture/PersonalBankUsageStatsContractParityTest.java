package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult.Outcome;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.SharedUserAccess;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.RecordComponent;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Closes the cumulative Phase 4B contract for the HTTP-neutral usage-statistics read. */
class PersonalBankUsageStatsContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final List<String> QUERY_IDS = List.of(
            "personal-bank-usage-stats-bank-probe",
            "personal-bank-usage-stats-shared-users",
            "personal-bank-usage-stats-public-users");
    private static final List<String> ADAPTER_FIELDS = List.of(
            "SELECT_BANK", "SELECT_SHARED_USERS", "SELECT_PUBLIC_USER_IDS");
    private static final List<String> USER_COUNTS_FORWARD_ADDITIONS = List.of(
            "Ti-Java/docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
            "Ti-Java/docs/refactor/phase4b/personal-bank-user-counts-callers.json",
            "Ti-Java/docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json",
            "Ti-Java/docs/refactor/phase4b/personal-bank-user-counts-query-plan-evidence.json",
            "Ti-Java/server/src/test/java/io/saksk/ti/integration/"
                    + "Phase4bPersonalBankUserCountsEvidenceJdbcCompatibilityIT.java",
            "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
                    + "persistence/PersonalBankUserCountsEvidenceSql.java",
            "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
                    + "persistence/PersonalBankUserCountsEvidenceSqlContractTest.java",
            "Ti-Java/server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
                    + "persistence/PersonalBankUserCountsEvidenceSqlManifestTest.java",
            "Ti-Java/server/src/test/resources/db/phase4b/"
                    + "067-personal-bank-user-counts-schema.sql",
            "Ti-Java/server/src/test/resources/db/phase4b/"
                    + "068-personal-bank-user-counts-seed.sql",
            "Ti-Java/tools/capture_phase4b_personal_bank_user_counts_callers.py",
            "Ti-Java/tools/capture_phase4b_personal_bank_user_counts_goldens.py",
            "Ti-Java/tools/capture_phase4b_personal_bank_user_counts_query_plans.py",
            "Ti-Java/tools/test_capture_phase4b_personal_bank_user_counts_callers.py",
            "Ti-Java/tools/test_capture_phase4b_personal_bank_user_counts_goldens.py",
            "Ti-Java/tools/test_capture_phase4b_personal_bank_user_counts_query_plans.py",
            "Ti-Java/tools/test_phase4b_personal_bank_user_counts_entry_contract.py");

    private static Path tiJavaRoot;
    private static JsonNode contract;
    private static JsonNode entry;
    private static JsonNode shape;
    private static JsonNode golden;
    private static JsonNode plan;
    private static JsonNode userCountsEntry;
    private static JsonNode userCountsGolden;
    private static JsonNode phase4cComposition;

    @BeforeAll
    static void loadEvidence() throws Exception {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toRealPath();
        tiJavaRoot = basedir.getParent();
        contract = readJson(
                "docs/refactor/phase4b/personal-bank-usage-stats-read-contract.json");
        entry = readJson(
                "docs/refactor/phase4b/personal-bank-usage-stats-entry-contract.json");
        shape = readJson(
                "docs/refactor/phase4b/"
                        + "personal-bank-usage-stats-application-api-shape.json");
        golden = readJson(
                "docs/refactor/phase4b/golden-personal-bank-usage-stats-reads.json");
        plan = readJson(
                "docs/refactor/phase4b/"
                        + "personal-bank-usage-stats-query-plan-evidence.json");
        userCountsEntry = readJson(
                "docs/refactor/phase4b/personal-bank-user-counts-entry-contract.json");
        userCountsGolden = readJson(
                "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json");
        phase4cComposition = readJson(
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-composition-contract.json");
        Phase4cSuccessorAcceptance.validate(phase4cComposition);
    }

    @Test
    void entryShapeGoldenPlanAndPreimplementationSqlCloseTransitively() throws Exception {
        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-usage-stats-read-contract");
        assertThat(contract.path("schema_version").asInt()).isEqualTo(1);
        assertThat(contract.path("status").asString())
                .isEqualTo("implemented_and_targeted_verified_http_aliases_deferred");
        assertThat(contract.path("predecessor").path("source").asString())
                .isEqualTo(
                        "docs/refactor/phase4b/"
                                + "personal-bank-usage-stats-entry-contract.json");
        assertThat(contract.path("predecessor").path("sha256").asString())
                .isEqualTo(sha256(contract.path("predecessor").path("source").asString()));
        assertThat(entry.path("status").asString())
                .isEqualTo("entry_gate_passed_implementation_not_started");
        assertThat(entry.path("implementation_state").path("implementation_started")
                        .asBoolean())
                .isFalse();

        assertEvidenceHash(
                "application_api_shape",
                "docs/refactor/phase4b/"
                        + "personal-bank-usage-stats-application-api-shape.json");
        assertEvidenceHash(
                "golden",
                "docs/refactor/phase4b/golden-personal-bank-usage-stats-reads.json");
        assertEvidenceHash(
                "preimplementation_sql",
                "server/src/test/java/io/saksk/ti/personalbank/infrastructure/"
                        + "persistence/PersonalBankUsageStatsEvidenceSql.java");
        assertEvidenceHash(
                "query_plan",
                "docs/refactor/phase4b/"
                        + "personal-bank-usage-stats-query-plan-evidence.json");

        assertThat(shape.path("predecessor").path("source").asString())
                .isEqualTo("personal-bank-all-shares-application-api-shape.json");
        assertThat(shape.path("predecessor").path("sha256").asString())
                .isEqualTo(sha256(
                        "docs/refactor/phase4b/"
                                + "personal-bank-all-shares-application-api-shape.json"));
        assertThat(golden.path("case_count").asInt()).isEqualTo(32);
        assertThat(strings(plan.path("engines"), "server_version"))
                .containsExactly("16.14", "18.4");
        assertThat(strings(plan.path("sql_contract").path("query_order")))
                .containsExactlyElementsOf(QUERY_IDS);
    }

    @Test
    void cumulativeShapeMatchesTheExactApiResultViewAndQueryPort() throws Exception {
        assertThat(shape.path("implemented_public_application_method_count").asInt())
                .isEqualTo(23);
        assertThat(shape.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(shape.path("pending_route_count").asInt()).isEqualTo(600);
        assertThat(shape.path("production_cutover_count").asInt()).isZero();
        JsonNode personalbank = shape.path("personalbank");
        assertThat(personalbank.path("methods")).hasSize(4);
        assertThat(strings(personalbank.path("methods"), "name"))
                .containsExactly(
                        "listCategories", "findShares", "listOwnedShares", "findUsageStats");
        assertThat(strings(personalbank.path("implemented_types")))
                .containsExactly(
                        "AuthenticatedPersonalBankViewer",
                        "PersonalBankCategoryView",
                        "PersonalBankOwnedShareView",
                        "PersonalBankShareListView",
                        "PersonalBankShareView",
                        "PersonalBankUsageStatsResult",
                        "PersonalBankUsageStatsView");

        JsonNode application = contract.path("application_contract");
        assertThat(application.path("public_api").asString())
                .isEqualTo(PersonalBankApplicationApi.class.getName());
        assertThat(application.path("method").asString())
                .isEqualTo(
                        "PersonalBankUsageStatsResult findUsageStats("
                                + "AuthenticatedPersonalBankViewer viewer, int bankId)");
        assertThat(application.path("transaction_read_only").asBoolean()).isTrue();
        assertThat(application.path("null_viewer").asString())
                .isEqualTo("requireNonNull_before_port");
        assertThat(strings(application.path("result_outcomes")))
                .containsExactly("AVAILABLE", "NOT_FOUND", "FORBIDDEN");
        assertThat(application.path("result_payload_invariant").asString())
                .isEqualTo("non-null view only for AVAILABLE");

        Method apiMethod = PersonalBankApplicationApi.class.getDeclaredMethod(
                "findUsageStats", AuthenticatedPersonalBankViewer.class, int.class);
        assertThat(apiMethod.getReturnType()).isEqualTo(PersonalBankUsageStatsResult.class);
        assertThat(apiMethod.getParameterTypes())
                .containsExactly(AuthenticatedPersonalBankViewer.class, int.class);

        assertThat(PersonalBankUsageStatsResult.class.isRecord()).isTrue();
        assertThat(componentNames(PersonalBankUsageStatsResult.class))
                .containsExactly("outcome", "view");
        assertThat(componentTypes(PersonalBankUsageStatsResult.class))
                .containsExactly(Outcome.class.getName(), PersonalBankUsageStatsView.class.getName());
        assertThat(Arrays.stream(Outcome.values()).map(Enum::name).toList())
                .containsExactly("AVAILABLE", "NOT_FOUND", "FORBIDDEN");
        assertThat(contract.path("result_contract").path("record").asString())
                .isEqualTo(PersonalBankUsageStatsResult.class.getName());
        assertThat(strings(contract.path("result_contract").path("outcomes")))
                .containsExactly("AVAILABLE", "NOT_FOUND", "FORBIDDEN");

        assertThat(PersonalBankUsageStatsView.class.isRecord()).isTrue();
        assertThat(componentNames(PersonalBankUsageStatsView.class))
                .containsExactlyElementsOf(strings(
                        contract.path("usage_stats_view_components"), "name"));
        assertThat(componentTypes(PersonalBankUsageStatsView.class))
                .containsExactlyElementsOf(strings(
                        contract.path("usage_stats_view_components"), "java_type"));
        assertThat(contract.path("usage_stats_view_components")).hasSize(8);
        contract.path("usage_stats_view_components").forEach(component ->
                assertThat(component.path("nullable").asBoolean())
                        .as(component.path("name").asString())
                        .isFalse());

        JsonNode portContract = contract.path("query_port_contract");
        assertThat(portContract.path("port").asString())
                .isEqualTo(PersonalBankUsageStatsQueryPort.class.getName());
        assertThat(strings(portContract.path("methods"), "name"))
                .containsExactly("findBank", "listSharedUsers", "listPublicUserIds");
        assertPortMethod("findBank", Optional.class, BankAccess.class);
        assertPortMethod("listSharedUsers", List.class, SharedUserAccess.class);
        assertPortMethod("listPublicUserIds", List.class, Object.class);
        assertThat(componentNames(BankAccess.class))
                .containsExactly("bankId", "ownerId", "publicBank", "status");
        assertThat(componentTypes(BankAccess.class))
                .containsExactly("int", "java.lang.Long", "java.lang.Boolean", "java.lang.Integer");
        assertThat(componentNames(SharedUserAccess.class))
                .containsExactly("userId", "expiresAt");
        assertThat(componentTypes(SharedUserAccess.class))
                .containsExactly("java.lang.Object", "java.lang.Object");
    }

    @Test
    void implementationHashesThreeRuntimeStatementsTransactionAndClockMatch()
            throws Exception {
        JsonNode implementation = contract.path("implementation");
        assertThat(propertyNames(implementation.path("main_source_files")))
                .containsExactlyInAnyOrder(
                        "application_api",
                        "usage_stats_result",
                        "usage_stats_view",
                        "application_service",
                        "query_port",
                        "jdbc_adapter");
        assertSourceHashes(
                implementation.path("main_source_files"),
                implementation.path("main_source_sha256"));
        assertSourceHashes(
                implementation.path("verification_source_files"),
                implementation.path("verification_source_sha256"));
        assertMainSourceManifest(
                implementation.path("personalbank_main_source_manifest"));

        JsonNode persistence = contract.path("persistence_contract");
        assertThat(persistence.path("query_count").asInt()).isEqualTo(3);
        assertThat(strings(persistence.path("query_order")))
                .containsExactlyElementsOf(QUERY_IDS);
        assertThat(persistence.path("sequential_execution_required").asBoolean()).isTrue();
        assertThat(persistence.path("short_circuit_after_bank_probe").asBoolean()).isTrue();
        assertThat(persistence.path("optional_query_transaction_boundary").asString())
                .isEqualTo("REQUIRES_NEW read-only transaction per shared/public query");
        assertThat(persistence.path("join_or_query_collapse_authorized").asBoolean())
                .isFalse();
        assertThat(persistence.path("parallel_execution_authorized").asBoolean()).isFalse();
        assertThat(persistence.path("bank_id_jdbc_bind_type").asString())
                .isEqualTo("integer");
        assertThat(persistence.path("schema_or_index_delta").asBoolean()).isFalse();
        assertThat(persistence.path("queries")).hasSize(3);

        Class<?> adapter = Class.forName(
                "io.saksk.ti.personalbank.infrastructure.persistence."
                        + "JdbcPersonalBankUsageStatsQueryAdapter");
        for (String methodName : List.of("listSharedUsers", "listPublicUserIds")) {
            Transactional optionalTransaction = adapter
                    .getDeclaredMethod(methodName, int.class)
                    .getAnnotation(Transactional.class);
            assertThat(optionalTransaction).isNotNull();
            assertThat(optionalTransaction.propagation()).isEqualTo(Propagation.REQUIRES_NEW);
            assertThat(optionalTransaction.readOnly()).isTrue();
        }
        JsonNode plannedQueries = plan.path("sql_contract").path("manifest").path("queries");
        for (int index = 0; index < QUERY_IDS.size(); index++) {
            JsonNode query = persistence.path("queries").get(index);
            assertThat(query.path("query_id").asString()).isEqualTo(QUERY_IDS.get(index));
            assertThat(query.path("adapter_field").asString())
                    .isEqualTo(ADAPTER_FIELDS.get(index));
            assertThat(staticString(adapter, ADAPTER_FIELDS.get(index)))
                    .isEqualTo(query.path("sql").asString())
                    .isEqualTo(plannedQueries.get(index).path("sql").asString());
            assertThat(strings(query.path("parameter_order"))).containsExactly("bank_id");
            assertThat(query.path("parameters").path("bank_id").asString())
                    .isEqualTo("integer");
        }

        Class<?> service = Class.forName(
                "io.saksk.ti.personalbank.application.PersonalBankQueryService");
        Transactional transaction = service.getDeclaredMethod(
                        "findUsageStats", AuthenticatedPersonalBankViewer.class, int.class)
                .getAnnotation(Transactional.class);
        assertThat(transaction).isNotNull();
        assertThat(transaction.readOnly()).isTrue();
        assertThat(service.getDeclaredConstructor(
                        PersonalBankCategoryQueryPort.class,
                        PersonalBankShareQueryPort.class,
                        PersonalBankOwnedShareQueryPort.class,
                        PersonalBankUsageStatsQueryPort.class,
                        Clock.class))
                .isNotNull();
        assertThat(service.getDeclaredField("clock").getType()).isEqualTo(Clock.class);
        assertThat(staticValue(service, "BEIJING")).isEqualTo(ZoneId.of("Asia/Shanghai"));

        JsonNode time = contract.path("time_semantics");
        assertThat(time.path("injectable_clock").asString()).isEqualTo("java.time.Clock");
        assertThat(time.path("zone").asString()).isEqualTo("Asia/Shanghai");
        assertThat(time.path("expired_when").asString()).isEqualTo("expires_at < now");
        assertThat(time.path("equal_to_now").asString()).isEqualTo("valid");
        assertThat(time.path("truthy_malformed_expiry").asString()).isEqualTo("expired");
        assertThat(time.path("aware_vs_naive_comparison_error").asString())
                .isEqualTo("expired");

        JsonNode counts = contract.path("usage_count_semantics");
        assertThat(counts.path("zero_user_id").asString()).isEqualTo("ignored");
        assertThat(counts.path("negative_user_id").asString()).isEqualTo("counted");
        assertThat(counts.path("owner_excluded_from_shared_users").asBoolean()).isTrue();
        assertThat(counts.path("owner_excluded_from_public_users").asBoolean()).isTrue();
        assertThat(counts.path("shared_and_public_categories_count_independently")
                        .asBoolean())
                .isTrue();
        assertThat(counts.path("owner_count").asInt()).isOne();

        JsonNode failure = contract.path("failure_contract");
        assertThat(failure.path("bank_probe_failure").asString()).isEqualTo("propagate");
        assertThat(failure.path("shared_query_failure").asString())
                .isEqualTo("independently degrade to empty set");
        assertThat(failure.path("public_query_failure").asString())
                .isEqualTo("independently degrade to empty set");
        assertThat(failure.path("both_optional_queries_fail").asString())
                .isEqualTo("AVAILABLE owner-only counts");
    }

    @Test
    void bothAliasesStayPendingOpaqueAndEveryForbiddenDeltaRemainsFalse()
            throws Exception {
        JsonNode routeState = contract.path("route_state");
        assertThat(routeState.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(routeState.path("pending_route_count").asInt()).isEqualTo(600);
        assertThat(routeState.path("production_cutover_count").asInt()).isZero();
        assertThat(routeState.path("operations")).hasSize(2);
        assertThat(strings(routeState.path("operations"), "route_id"))
                .containsExactlyInAnyOrder("d67a16965b08", "22aecd49a3c2");

        JsonNode openApi = readJson("contracts/openapi.json");
        for (JsonNode operation : routeState.path("operations")) {
            assertThat(operation.path("migration_status").asString()).isEqualTo("pending");
            assertThat(operation.path("contract_maturity").asString()).isEqualTo("inferred");
            assertThat(operation.path("production_cutover").asBoolean()).isFalse();
            JsonNode base = openApi.path("paths")
                    .path(operation.path("openapi_path").asString())
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

        assertThat(shape.path("route_openapi_delta_authorized").asBoolean()).isFalse();
        contract.path("forbidden_scope").properties().forEach(entry ->
                assertThat(entry.getValue().asBoolean()).as(entry.getKey()).isFalse());
    }

    @Test
    void userCountsSuccessorClosesEvidenceButAuthorizesNoProductionChange()
            throws Exception {
        assertThat(userCountsEntry.path("contract_id").asString())
                .isEqualTo("ti.phase4b.personal-bank-user-counts-entry-contract");
        assertThat(userCountsEntry.path("status").asString())
                .isEqualTo(
                        "evidence_closed_but_production_implementation_blocked_"
                                + "pending_learning_composition");
        assertThat(userCountsEntry.path("predecessor").path("source").asString())
                .isEqualTo(
                        "docs/refactor/phase4b/"
                                + "personal-bank-usage-stats-read-contract.json");
        assertThat(userCountsEntry.path("predecessor").path("sha256").asString())
                .isEqualTo(sha256(
                        "docs/refactor/phase4b/"
                                + "personal-bank-usage-stats-read-contract.json"));

        JsonNode decision = userCountsEntry.path("entry_decision");
        assertThat(decision.path("evidence_closed").asBoolean()).isTrue();
        assertThat(decision.path("implementation_authorized").asBoolean()).isFalse();
        assertThat(decision.path("baseline_route_owner").asString())
                .isEqualTo("personalbank");
        assertThat(decision.path("reviewed_use_case_owner").asString())
                .isEqualTo("learning");
        assertThat(decision.path("reviewed_http_owner").asString())
                .isEqualTo("learning");
        assertThat(propertyNames(decision.path("authorizations")))
                .containsExactlyInAnyOrder(
                        "direct_personalbank_implementation",
                        "learning_composition_implementation",
                        "http_implementation",
                        "production_schema_delta",
                        "production_index_delta",
                        "production_cutover");
        decision.path("authorizations").properties().forEach(entry ->
                assertThat(entry.getValue().asBoolean()).as(entry.getKey()).isFalse());

        JsonNode boundary = userCountsEntry.path("module_boundary_decision");
        assertThat(boundary.path("required_composition_direction").asString())
                .isEqualTo("learning_to_personalbank_api");
        assertThat(boundary.path("complete_use_case_owner").asString())
                .isEqualTo("learning");
        assertThat(boundary.path("personalbank_call_surface").asString())
                .isEqualTo("personalbank::api");
        assertThat(strings(boundary.path("personalbank_forbidden_learning_tables")))
                .containsExactly(
                        "user_bank_favorites",
                        "user_bank_mistakes",
                        "user_progress",
                        "user_question_tag_items");

        JsonNode prerequisites = userCountsEntry.path("entry_prerequisites");
        for (String evidenceName : List.of(
                "caller_attestation", "fixed_commit_golden", "jdbc_and_query_plans")) {
            JsonNode reference = prerequisites.path(evidenceName);
            assertThat(reference.path("file_sha256").asString())
                    .as(evidenceName)
                    .isEqualTo(sha256(reference.path("evidence_source").asString()));
        }
        assertThat(prerequisites.path("fixed_commit_golden").path("case_count").asInt())
                .isEqualTo(59);
        assertThat(prerequisites.path("fixed_commit_golden").path("passed").asBoolean())
                .isTrue();
        assertThat(prerequisites.path("jdbc_and_query_plans").path("passed").asBoolean())
                .isTrue();
        assertThat(userCountsGolden.path("case_count").asInt()).isEqualTo(59);

        JsonNode unchanged = userCountsEntry.path("unchanged_state");
        assertThat(unchanged.path("implemented_public_application_method_count").asInt())
                .isEqualTo(23);
        assertThat(unchanged.path("migrated_route_count").asInt()).isEqualTo(11);
        assertThat(unchanged.path("pending_route_count").asInt()).isEqualTo(600);
        assertThat(unchanged.path("production_cutover_count").asInt()).isZero();

        JsonNode acceptance = userCountsEntry.path("acceptance");
        assertThat(acceptance.path("evidence_closed").asBoolean()).isTrue();
        assertThat(acceptance.path("implementation_authorized").asBoolean()).isFalse();
        assertThat(acceptance.path("next_required_gate").asString())
                .isEqualTo("pending_learning_composition_contract");
        assertThat(acceptance.path("production_cutover").asBoolean()).isFalse();

        assertThat(propertyNames(userCountsEntry.path("change_budget")))
                .containsExactlyInAnyOrder(
                        "production_java_files_added",
                        "production_java_files_modified",
                        "http_controllers_added",
                        "application_methods_added",
                        "production_schema_files_added",
                        "production_indexes_added",
                        "route_delta_rows_added",
                        "openapi_operations_migrated",
                        "production_cutover_operations");
        userCountsEntry.path("change_budget").properties().forEach(entry ->
                assertThat(entry.getValue().asInt()).as(entry.getKey()).isZero());
        assertThat(userCountsEntry.toString()).doesNotContain("PENDING");

        assertThat(strings(contract.path("forward_handoff").path("forward_additions")))
                .hasSize(49)
                .containsAll(USER_COUNTS_FORWARD_ADDITIONS);
    }

    private static void assertEvidenceHash(String name, String expectedSource)
            throws Exception {
        JsonNode reference = contract.path("evidence").path(name);
        assertThat(reference.path("source").asString()).isEqualTo(expectedSource);
        assertThat(reference.path("sha256").asString()).isEqualTo(sha256(expectedSource));
    }

    private static void assertPortMethod(
            String methodName,
            Class<?> rawReturnType,
            Class<?> genericReturnType
    ) throws Exception {
        Method method = PersonalBankUsageStatsQueryPort.class
                .getDeclaredMethod(methodName, int.class);
        assertThat(method.getReturnType()).isEqualTo(rawReturnType);
        assertThat(method.getGenericReturnType()).isInstanceOf(ParameterizedType.class);
        ParameterizedType parameterized = (ParameterizedType) method.getGenericReturnType();
        assertThat(parameterized.getActualTypeArguments()).containsExactly(genericReturnType);
    }

    private static void assertSourceHashes(JsonNode files, JsonNode hashes) throws Exception {
        assertThat(propertyNames(files))
                .containsExactlyInAnyOrderElementsOf(propertyNames(hashes));
        for (String key : propertyNames(files)) {
            String relative = files.path(key).asString();
            String currentHash = sha256(relative);
            String successorHash = phase4cSuccessorHash(relative);
            if (successorHash == null) {
                assertThat(currentHash)
                        .as("source hash for %s", key)
                        .isEqualTo(hashes.path(key).asString());
            } else {
                assertThat(currentHash)
                        .as("Phase4C source hash for %s", key)
                        .isEqualTo(successorHash)
                        .isNotEqualTo(hashes.path(key).asString());
            }
        }
    }

    private static String phase4cSuccessorHash(String relative) {
        return Phase4cSuccessorAcceptance.successorHash(phase4cComposition, relative);
    }

    private static void assertMainSourceManifest(JsonNode manifest) throws Exception {
        Path sourceRoot = resolve("server/src/main/java/io/saksk/ti/personalbank");
        List<String> current = new ArrayList<>();
        try (var paths = Files.walk(sourceRoot)) {
            paths.filter(path -> Files.isRegularFile(path) && path.toString().endsWith(".java"))
                    .sorted()
                    .forEach(path -> current.add(
                            tiJavaRoot.relativize(path).toString().replace('\\', '/')));
        }
        assertThat(propertyNames(manifest)).containsExactlyInAnyOrderElementsOf(current);
        for (String relative : current) {
            assertThat(manifest.path(relative).asString())
                    .as("main source manifest hash for %s", relative)
                    .isEqualTo(sha256(relative));
        }
    }

    private static String staticString(Class<?> type, String fieldName) throws Exception {
        return (String) staticValue(type, fieldName);
    }

    private static Object staticValue(Class<?> type, String fieldName) throws Exception {
        Field field = type.getDeclaredField(fieldName);
        field.setAccessible(true);
        return field.get(null);
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
