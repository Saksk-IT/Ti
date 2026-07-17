package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Java parity gate for the fixed Phase 4C user-counts HTTP implementation successor. */
class Phase4cPersonalBankUserCountsHttpImplementationContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-contract.json";
    private static final String GOLDEN_PATH =
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json";
    private static final String MAPPING_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-mapping-evidence.json";
    private static final Set<String> HTTP_DIFFERENCES = Set.of(
            "P4C-LEARNING-007", "P4C-LEARNING-008", "P4C-LEARNING-009",
            "P4C-LEARNING-010", "P4C-LEARNING-011", "P4C-LEARNING-012");

    @Test
    void loadsTheFixedSuccessorWithoutRewritingTheHttpEntryPredecessor()
            throws Exception {
        JsonNode contract = Phase4cHttpImplementationSuccessorAcceptance.load(root());
        assertThat(contract.path("contract_id").asString())
                .isEqualTo("ti.phase4c.personal-bank-user-counts-http-implementation-contract");
        assertThat(contract.path("status").asString())
                .isEqualTo("implementation_present_parity_incomplete_routes_pending");
        assertThat(contract.path("predecessor").path("sha256").asString())
                .isEqualTo("d91d4ce6ccae982ded22a83ca9a7663042102c257565d3973b125e535f9c6676");
        assertThat(contract.path("predecessor")
                .path("document_payload_sha256").asString())
                .isEqualTo("ca430ec715d3b673e00f72fd8e290bed4b228970b9940864745e9c6d560a7402");
        assertThat(contract.path("predecessor").path("immutable").asBoolean()).isTrue();
        assertThat(readJson(CONTRACT_PATH)).isEqualTo(contract);
    }

    @Test
    void recordsOnlyTheAuthorized288To297ProductionDelta() throws Exception {
        JsonNode transition = contract().path("implementation")
                .path("production_runtime_transition");
        assertThat(transition.path("predecessor").path("file_count").asInt())
                .isEqualTo(288);
        assertThat(transition.path("predecessor").path("manifest_sha256").asString())
                .isEqualTo("145bcd8d5e662cffb87744b39b8eae03cdf5761b7fc9096d90300dd4742905dc");
        assertThat(transition.path("current").path("file_count").asInt())
                .isEqualTo(297);

        JsonNode delta = transition.path("exact_delta");
        assertThat(delta.path("added_file_count").asInt()).isEqualTo(9);
        assertThat(delta.path("new_main_source_count").asInt()).isEqualTo(8);
        assertThat(delta.path("new_openapi_file_count").asInt()).isEqualTo(1);
        assertThat(delta.path("changed_file_count").asInt()).isEqualTo(6);
        assertThat(delta.path("changed_main_source_count").asInt()).isEqualTo(2);
        assertThat(delta.path("changed_configuration_file_count").asInt()).isEqualTo(4);
        assertThat(delta.path("deleted_file_count").asInt()).isZero();
        assertThat(delta.path("deleted_files")).isEmpty();

        JsonNode modules = transition.path("learning_and_personalbank");
        assertThat(modules.path("file_count").asInt()).isEqualTo(40);
        assertThat(modules.path("manifest_sha256").asString())
                .isEqualTo("d20c124c587dff562781dd6b9f7978300b292ff07d5f8fb4463d5a0448b197a1");
        assertThat(modules.path("unchanged_from_read_predecessor").asBoolean()).isTrue();
        JsonNode api = transition.path("public_application_api");
        assertThat(api.path("method_count").asInt()).isEqualTo(27);
        assertThat(api.path("methods_sha256").asString())
                .isEqualTo("c3b6b2eb984c1f910605bdf08c389484e5a675969c7e4ab71e5208c40d45530d");
        assertThat(api.path("unchanged_from_http_entry_predecessor").asBoolean()).isTrue();
        assertThat(transition.path("forbidden_main_sources")
                .path("unchanged").asBoolean()).isTrue();
        assertThat(transition.path("forbidden_main_sources").path("files").size())
                .isEqualTo(7);
    }

    @Test
    void keepsTheTwoImplementedLegacyGetRoutesPendingUntilParityCloses() throws Exception {
        JsonNode routes = contract().path("implementation").path("routes_and_openapi");
        assertThat(routes.path("implemented_pending_get_count").asInt()).isEqualTo(2);
        assertThat(routes.path("migrated_operation_count").asInt()).isEqualTo(11);
        assertThat(routes.path("pending_operation_count").asInt()).isEqualTo(600);
        assertThat(routes.path("production_cutover_operation_count").asInt()).isZero();
        assertThat(routes.path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(strings(routes.path("counted_methods"))).containsExactly("GET");
        assertThat(strings(routes.path("derived_methods")))
                .containsExactly("HEAD", "OPTIONS");
        assertThat(routes.path("routes")).hasSize(2);
        Set<String> routeIds = new LinkedHashSet<>();
        routes.path("routes").forEach(route -> {
            routeIds.add(route.path("route_id").asString());
            assertThat(route.path("method").asString()).isEqualTo("GET");
            assertThat(route.path("target_module").asString()).isEqualTo("learning");
            assertThat(route.path("migration_status").asString()).isEqualTo("pending");
            assertThat(route.path("production_cutover").asBoolean()).isFalse();
        });
        assertThat(routeIds).containsExactlyInAnyOrder("6858f6fa506f", "006913d0d956");
    }

    @Test
    void assignsTheNewRateLimitNamespaceToOneLearningOwner() throws Exception {
        JsonNode ownership = contract().path("data_ownership");
        assertThat(ownership.path("predecessor").path("resource_count").asInt())
                .isEqualTo(159);
        assertThat(ownership.path("predecessor").path("immutable").asBoolean()).isTrue();
        assertThat(ownership.path("delta").path("new_resource_count").asInt())
                .isEqualTo(1);
        JsonNode effective = ownership.path("effective");
        assertThat(effective.path("resource_count").asInt()).isEqualTo(160);
        assertThat(effective.path("resources_with_exactly_one_owner").asInt())
                .isEqualTo(160);
        assertThat(effective.path(
                "canonical_owner_manifest_recomputed").asBoolean()).isTrue();
        assertThat(contract().path("acceptance")
                .path("new_rate_limit_resource_has_one_learning_owner").asBoolean())
                .isTrue();
        assertThat(contract().path("acceptance")
                .path("effective_resource_count").asInt()).isEqualTo(160);
        assertThat(effective.path("new_resources")).hasSize(1);
        JsonNode resource = effective.path("new_resources").path(0);
        assertThat(resource.path("resource_kind").asString()).isEqualTo("redis_key");
        assertThat(resource.path("resource_name").asString()).isEqualTo(
                "ti-java:learning:personal-bank-user-counts-read-rate:"
                        + "<api|web>:<identity:v1|ip:v1>:<hmac_sha256>:"
                        + "<second|hour|day>");
        assertThat(resource.path("owner").asString()).isEqualTo("learning");
        assertThat(resource.path("persistence_role").asString())
                .isEqualTo("runtime_rate_limit");
        assertThat(resource.path("business_fact").asBoolean()).isFalse();
        assertThat(resource.path("production_cutover").asBoolean()).isFalse();
    }

    @Test
    void bindsRealNetworkPostgresRedisAndThePartialFiftyNineCaseLedger()
            throws Exception {
        JsonNode evidence = contract().path("verification_evidence");
        assertThat(evidence.path("real_network_tomcat").path("mock_mvc").asBoolean())
                .isFalse();
        assertThat(evidence.path("real_network_tomcat").path("transport").asString())
                .isEqualTo("random-port Tomcat with java.net.http.HttpClient");
        assertThat(strings(evidence.path("postgresql_16_14_and_18_4")
                .path("versions"))).containsExactly("16.14", "18.4");
        assertThat(evidence.path("postgresql_16_14_and_18_4")
                .path("http_sql_fingerprint_parity").asBoolean()).isTrue();
        assertThat(evidence.path("redis_7").path("real_lua").asBoolean()).isTrue();
        assertThat(evidence.path("redis_7")
                .path("atomic_concurrency_and_ttl").asBoolean()).isTrue();
        assertThat(evidence.path("redis_7").path("alias_isolation").asBoolean()).isTrue();

        JsonNode summary = evidence.path("phase4b_59_case_mapping");
        assertThat(summary.path("claim_classification").asString())
                .isEqualTo("PARTIAL_EXECUTION_MAPPING_LEDGER");
        assertThat(summary.path("full_target_parity_closed").asBoolean()).isFalse();
        assertThat(summary.path("cutover_evidence").asBoolean()).isFalse();
        assertThat(summary.path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(summary.path("case_count").asInt()).isEqualTo(59);
        assertThat(summary.path("mockmvc_case_count").asInt()).isEqualTo(48);
        assertThat(summary.path("bound_only_case_count").asInt()).isEqualTo(11);
        assertThat(summary.path("inherited_difference_id").asString())
                .isEqualTo("P4C-LEARNING-006");
        assertThat(strings(summary.path("inherited_case_ids"))).containsExactly(
                "access-shared-fetchone-first-row",
                "access-shared-cross-bank-record");
        assertThat(strings(summary.path("http_difference_ids")))
                .containsExactlyElementsOf(HTTP_DIFFERENCES.stream().sorted().toList());

        JsonNode golden = readJson(GOLDEN_PATH);
        JsonNode mapping = readJson(MAPPING_PATH);
        assertThat(caseIds(mapping.path("cases")))
                .containsExactlyElementsOf(caseIds(golden.path("cases")));
        assertThat(mapping.path("cases")).hasSize(59);
        List<String> inheritedCases = new ArrayList<>();
        mapping.path("cases").forEach(item -> {
            List<String> differences = strings(item.path("http_slice_difference_ids"));
            assertThat(new LinkedHashSet<>(differences)).hasSameSizeAs(differences);
            assertThat(differences)
                    .allMatch(HTTP_DIFFERENCES::contains)
                    .doesNotContain("P4C-LEARNING-006");
            if (item.has("inherited_predecessor_difference_id")) {
                assertThat(item.path("inherited_predecessor_difference_id").asString())
                        .isEqualTo("P4C-LEARNING-006");
                inheritedCases.add(item.path("case_id").asString());
            }
        });
        assertThat(inheritedCases).containsExactly(
                "access-shared-fetchone-first-row",
                "access-shared-cross-bank-record");

        JsonNode adapter = evidence.path("http_adapter_security");
        assertThat(adapter.path("mock_mvc").asBoolean()).isTrue();
        assertThat(adapter.path("full_authentication_filter_chain").asBoolean()).isFalse();
        assertThat(strings(adapter.path("excluded_filters"))).containsExactly(
                "TargetSessionAuthenticationFilter",
                "TargetSessionReconciliationFilter");
    }

    @Test
    void successorAllowlistCannotAuthorizeItsOwnBridgeOrProductionCutover()
            throws Exception {
        assertThat(Phase4cHttpImplementationSuccessorAcceptance.acceptedHash(
                "tools/phase4c_http_entry_successor_acceptance.py")).isNotNull();
        assertThat(Phase4cHttpImplementationSuccessorAcceptance.acceptedHash(
                "tools/phase4c_http_implementation_successor_acceptance.py")).isNull();
        assertThat(Phase4cHttpImplementationSuccessorAcceptance.acceptedHash(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpImplementationSuccessorAcceptance.java")).isNull();

        JsonNode contract = contract();
        JsonNode authorization = contract.path("authorization");
        assertThat(authorization.path("implementation_present").asBoolean()).isTrue();
        assertThat(authorization.has("http_implementation_complete")).isFalse();
        for (String field : Set.of(
                "full_target_parity_closed", "route_migration_eligible",
                "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated",
                "identity_api_or_global_auth_filter_change",
                "learning_or_personalbank_persistence_change",
                "production_schema_or_index", "operator_migration_implementation",
                "real_data_migration_execution", "migration_global_preflight_closed",
                "client_change", "gateway_or_proxy_change", "production_cutover")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        JsonNode acceptance = contract.path("acceptance");
        assertThat(acceptance.path("implementation_present").asBoolean()).isTrue();
        assertThat(acceptance.path("full_target_parity_closed").asBoolean()).isFalse();
        assertThat(acceptance.path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(acceptance.path("implemented_pending_get_count").asInt()).isEqualTo(2);
        assertThat(acceptance.path("migrated_operation_count").asInt()).isEqualTo(11);
        assertThat(acceptance.path("pending_operation_count").asInt()).isEqualTo(600);
        assertThat(acceptance.path("next_gate").asString()).isEqualTo(
                "close_59_case_target_execution_and_full_authentication_chain_"
                        + "before_route_migration");
        JsonNode worm = contract.path("worm_evidence");
        assertThat(worm.path("source").asString())
                .isEqualTo("docs/refactor/phase4c/"
                        + "personal-bank-user-counts-http-implementation-worm-evidence.json");
        assertThat(worm.path("production_schema_or_index_changed").asBoolean()).isFalse();
        assertThat(worm.path("operator_migration_executed").asBoolean()).isFalse();
        assertThat(worm.path("real_data_migration_executed").asBoolean()).isFalse();
        assertThat(worm.path("production_cutover").asBoolean()).isFalse();
    }

    private static JsonNode contract() throws Exception {
        return Phase4cHttpImplementationSuccessorAcceptance.load(root());
    }

    private static JsonNode readJson(String relative) throws Exception {
        return JSON.readTree(Files.readString(
                root().resolve(relative), StandardCharsets.UTF_8));
    }

    private static List<String> caseIds(JsonNode cases) {
        List<String> ids = new ArrayList<>();
        cases.forEach(item -> ids.add(item.path("case_id").asString()));
        assertThat(new LinkedHashSet<>(ids)).hasSameSizeAs(ids);
        return List.copyOf(ids);
    }

    private static List<String> strings(JsonNode array) {
        List<String> values = new ArrayList<>();
        array.forEach(item -> values.add(item.asString()));
        return List.copyOf(values);
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }
}
