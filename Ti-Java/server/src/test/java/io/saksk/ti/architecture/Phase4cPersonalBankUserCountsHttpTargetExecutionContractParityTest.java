package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

/** Java parity gate for the fixed Phase 4C user-counts target-execution successor. */
class Phase4cPersonalBankUserCountsHttpTargetExecutionContractParityTest {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-contract.json";
    private static final String EVIDENCE_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-execution-evidence.json";
    private static final String GOLDEN_PATH =
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json";
    private static final String MAPPING_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-mapping-evidence.json";
    private static final List<String> CASE_IDS = List.of(
            "auth-session-owner-api-alias",
            "auth-bearer-owner-api-alias",
            "auth-bearer-precedes-session-api-alias",
            "auth-invalid-bearer-falls-back-session-api-alias",
            "auth-state-invalid-bearer-does-not-fallback-session-api-alias",
            "auth-anonymous-api-alias",
            "data-empty-api-alias",
            "access-status-zero-api-alias",
            "access-missing-api-alias",
            "access-public-other-api-alias",
            "filter-source-favorites-api-alias",
            "tag-normalized-sa2-empty-api-alias",
            "fault-total-default-api-alias",
            "fault-total-json-api-alias",
            "auth-session-owner-web-alias",
            "auth-bearer-owner-web-alias",
            "auth-bearer-precedes-session-web-alias",
            "auth-invalid-bearer-falls-back-session-web-alias",
            "auth-state-invalid-bearer-does-not-fallback-session-web-alias",
            "auth-anonymous-web-alias",
            "data-empty-web-alias",
            "access-status-zero-web-alias",
            "access-missing-web-alias",
            "access-public-other-web-alias",
            "filter-source-favorites-web-alias",
            "tag-normalized-sa2-empty-web-alias",
            "fault-total-default-web-alias",
            "fault-total-json-web-alias",
            "access-status-null-owner",
            "access-status-two-owner",
            "access-private-other-forbidden",
            "access-shared-future",
            "access-shared-null-expiry",
            "access-shared-equal-now-forbidden",
            "access-shared-expired-forbidden",
            "access-shared-inactive-forbidden",
            "access-shared-malformed-expiry-value-error",
            "access-shared-aware-expiry-type-error",
            "access-shared-empty-expiry",
            "access-shared-fetchone-first-row",
            "access-shared-cross-bank-record",
            "filter-q-type-choice",
            "filter-q-type-all-uppercase",
            "filter-q-type-unknown-maps-essay",
            "filter-source-mistakes",
            "filter-source-case-sensitive-fallback",
            "filter-q-type-duplicate-first-wins",
            "filter-source-duplicate-first-wins",
            "tag-all-bypasses-store",
            "filter-tag-duplicate-first-all-wins",
            "tag-case-sensitive-all-enters-store",
            "tag-legacy-migration-sa2-empty",
            "fault-favorites-sqlite-continues",
            "fault-favorites-postgresql-poison-simulation",
            "fault-mistakes-sqlite-continues",
            "fault-mistakes-postgresql-poison-simulation",
            "fault-types-degrades",
            "fault-source-favorites-second-count-postgresql-poison-simulation",
            "fault-share-access-hard-failure");

    @Test
    void loadsTheFixedTargetExecutionSuccessorWithItsImmutableImplementationPredecessor()
            throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-contract");
        assertThat(contract.path("status").asString()).isEqualTo(
                "target_dispositions_executed_typed_parity_review_pending_routes_pending");
        assertThat(contract.path("scope").asString()).isEqualTo(
                "phase4c-personal-bank-user-counts-http-target-execution");
        JsonNode predecessor = contract.path("predecessor");
        assertThat(predecessor.path("sha256").asString()).isEqualTo(
                "c6a977f260bdd0ab4af6dace1b4c7d48803b5e8f9bc5299723b662226e45cfbd");
        assertThat(predecessor.path("document_payload_sha256").asString()).isEqualTo(
                "f6eff86bea6a1d04bc43bfe8a532ff952f295c6aa2d1d89f6b40f6fe02dc91f9");
        assertThat(predecessor.path("trust_payload_sha256").asString()).isEqualTo(
                "624bb2b801a51e0fd19ae4d4583d77c6b6195355685b202b4c5ac3aa56d2cf8f");
        assertThat(predecessor.path("immutable").asBoolean()).isTrue();
        assertThat(readJson(CONTRACT_PATH)).isEqualTo(contract);
    }

    @Test
    void preservesTheExactFiftyNineCaseGoldenOrderAndFourDispositions()
            throws Exception {
        JsonNode evidence = readJson(EVIDENCE_PATH);
        JsonNode golden = readJson(GOLDEN_PATH);
        assertThat(caseIds(golden.path("cases"))).containsExactlyElementsOf(CASE_IDS);
        assertThat(caseIds(evidence.path("cases"))).containsExactlyElementsOf(CASE_IDS);
        assertThat(evidence.path("cases")).hasSize(59);

        Map<String, Integer> dispositions = counts(
                evidence.path("cases"), "execution_disposition");
        assertThat(dispositions).containsExactlyInAnyOrderEntriesOf(Map.of(
                "EXECUTED_FULL_CONTEXT_HTTP", 46,
                "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT", 11,
                "EXECUTED_TYPED_REJECTION", 1,
                "EXECUTED_TYPED_COLLAPSE", 1));
        JsonNode summary = evidence.path("summary");
        assertThat(summary.path("case_count").asInt()).isEqualTo(59);
        assertThat(summary.path("http_execution_count").asInt()).isEqualTo(57);
        assertThat(summary.path("non_fault_http_execution_count").asInt()).isEqualTo(46);
        assertThat(summary.path("fault_http_execution_count").asInt()).isEqualTo(11);
        assertThat(summary.path("typed_postgresql_disposition_count").asInt())
                .isEqualTo(2);
        assertThat(summary.path("bound_only_case_count").asInt()).isZero();
        assertThat(summary.path("mocked_application_result_case_count").asInt()).isZero();
        assertThat(summary.path("api_alias_http_execution_count").asInt()).isEqualTo(43);
        assertThat(summary.path("web_alias_http_execution_count").asInt()).isEqualTo(14);
        assertThat(textIntegerMap(summary.path("http_status_counts")))
                .containsExactlyInAnyOrderEntriesOf(Map.of(
                        "200", 34, "302", 5, "401", 3, "403", 10, "500", 5));
    }

    @Test
    void keepsEveryDifferenceAndTypedSubstitutionBoundToTheHistoricalMapping()
            throws Exception {
        JsonNode evidence = readJson(EVIDENCE_PATH);
        JsonNode mapping = readJson(MAPPING_PATH);
        Map<String, JsonNode> mappings = casesById(mapping.path("cases"));
        List<String> inherited = new ArrayList<>();
        evidence.path("cases").forEach(item -> {
            String caseId = item.path("case_id").asString();
            JsonNode historical = mappings.get(caseId);
            assertThat(item.path("http_slice_difference_ids"))
                    .as(caseId)
                    .isEqualTo(historical.path("http_slice_difference_ids"));
            assertOptionalEqual(item, historical,
                    "inherited_predecessor_difference_id", caseId);
            assertOptionalEqual(item, historical, "target_data_source_case", caseId);
            assertOptionalEqual(item, historical, "tracking_note", caseId);
            if (item.has("inherited_predecessor_difference_id")) {
                assertThat(item.path("inherited_predecessor_difference_id").asString())
                        .isEqualTo("P4C-LEARNING-006");
                inherited.add(caseId);
            }
        });
        assertThat(inherited).containsExactly(
                "access-shared-fetchone-first-row",
                "access-shared-cross-bank-record");
        assertThat(evidence.path("cases").path(38)
                .path("target_data_source_case").asString())
                .isEqualTo("access-shared-null-expiry");
        assertThat(evidence.path("cases").path(39)
                .path("target_data_source_case").asString())
                .isEqualTo("access-shared-future");
    }

    @Test
    void provesSixtyJUnitLeavesAreFiftyNineDispositionsPlusOneSupplement()
            throws Exception {
        JsonNode evidence = readJson(EVIDENCE_PATH);
        JsonNode summary = evidence.path("summary");
        assertThat(summary.path("junit_leaf_test_count").asInt()).isEqualTo(60);
        assertThat(summary.path("supplementary_junit_test_count").asInt()).isEqualTo(1);
        assertThat(summary.path("case_count").asInt()
                + summary.path("supplementary_junit_test_count").asInt())
                .isEqualTo(summary.path("junit_leaf_test_count").asInt());
        assertThat(evidence.path("execution_harness").path("supplementary_junit")
                .path("http_probe_count").asInt()).isEqualTo(2);
        assertThat(evidence.path("execution_harness").path("supplementary_junit")
                .path("counted_as_golden_dispositions").asBoolean()).isFalse();

        Set<Integer> executionOrdinals = new LinkedHashSet<>();
        Set<Integer> leafOrdinals = new LinkedHashSet<>();
        evidence.path("cases").forEach(item -> {
            int execution = item.path("execution_ordinal").asInt();
            executionOrdinals.add(execution);
            leafOrdinals.add(item.path("junit").path("disposition_leaf_ordinal").asInt());
            assertThat(item.path("junit").path("disposition_leaf_ordinal").asInt())
                    .isEqualTo(execution + 1);
        });
        assertThat(executionOrdinals).containsExactlyInAnyOrderElementsOf(
                java.util.stream.IntStream.rangeClosed(1, 59).boxed().toList());
        assertThat(leafOrdinals).containsExactlyInAnyOrderElementsOf(
                java.util.stream.IntStream.rangeClosed(2, 60).boxed().toList());
    }

    @Test
    void bindsElevenRealPostgresAbortsAndTwoExplicitTypedDispositions()
            throws Exception {
        JsonNode evidence = readJson(EVIDENCE_PATH);
        List<JsonNode> faults = new ArrayList<>();
        evidence.path("cases").forEach(item -> {
            if (item.path("execution_disposition").asString().equals(
                    "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT")) {
                faults.add(item);
            }
        });
        assertThat(faults).hasSize(11);
        faults.forEach(item -> {
            JsonNode fault = item.path("fault_evidence");
            assertThat(fault.path("initial_sqlstate").asString()).isEqualTo("42703");
            assertThat(fault.path("poisoned_transaction_sqlstate").asString())
                    .isEqualTo("25P02");
            assertThat(fault.path("fault_connection_read_only").asBoolean()).isTrue();
            assertThat(fault.path("rollback_after_fault_on_same_connection").asBoolean())
                    .isTrue();
            assertThat(fault.path(
                    "failed_family_occurrence_has_no_success_record").asBoolean()).isTrue();
        });

        JsonNode malformed = caseById(evidence.path("cases"),
                "access-shared-malformed-expiry-value-error");
        assertThat(malformed.path("target_status").isNull()).isTrue();
        assertThat(malformed.path("typed_evidence").path("sqlstate").asString())
                .isEqualTo("22007");
        assertThat(malformed.path("typed_evidence")
                .path("persisted_bank_share_row_count").asInt()).isZero();
        JsonNode aware = caseById(evidence.path("cases"),
                "access-shared-aware-expiry-type-error");
        assertThat(aware.path("target_status").isNull()).isTrue();
        assertThat(aware.path("typed_evidence")
                .path("source_offset_provenance_erased").asBoolean()).isTrue();
        assertThat(aware.path("typed_evidence")
                .path("approved_null_expiry_is_sql_null").asBoolean()).isTrue();
    }

    @Test
    void reusesTheFifthWormAndKeepsProductionAndBothGetRoutesUnchanged()
            throws Exception {
        JsonNode contract = contract();
        JsonNode production = contract.path("production_surface");
        assertThat(production.path("file_count").asInt()).isEqualTo(297);
        assertThat(production.path("manifest_sha256").asString()).isEqualTo(
                "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79");
        assertThat(production.path("unchanged_from_predecessor").asBoolean()).isTrue();
        JsonNode worm = contract.path("worm_evidence");
        assertThat(worm.path("sha256").asString()).isEqualTo(
                "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39");
        assertThat(worm.path("java_build_context_sha256").asString()).isEqualTo(
                "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3");
        assertThat(worm.path("new_worm").asBoolean()).isFalse();
        assertThat(worm.path("new_worm_report_created").asBoolean()).isFalse();
        assertThat(worm.path("production_build_context_unchanged").asBoolean()).isTrue();

        JsonNode routes = contract.path("routes_and_openapi");
        assertThat(routes.path("implemented_pending_get_count").asInt()).isEqualTo(2);
        assertThat(routes.path("migrated_operation_count").asInt()).isEqualTo(11);
        assertThat(routes.path("pending_operation_count").asInt()).isEqualTo(600);
        assertThat(routes.path("production_cutover_operation_count").asInt()).isZero();
        assertThat(routes.path("route_migration_eligible").asBoolean()).isFalse();
        JsonNode bridge = contract.path("bridge_provenance");
        assertThat(bridge.path("state").asString()).isEqualTo(
                "bootstrap_pending_post_push_external_git_anchor");
        assertThat(bridge.path(
                "source_hashes_normalized_to_break_recursive_cycle").asBoolean())
                .isTrue();
        assertThat(bridge.path("external_bridge_bytes_anchor_complete").asBoolean())
                .isFalse();
        assertThat(bridge.path(
                "post_push_external_git_anchor_required_before_route_promotion")
                .asBoolean()).isTrue();
        assertThat(contract.path("authorization")
                .path("full_target_parity_closed").asBoolean()).isFalse();
        assertThat(contract.path("authorization")
                .path("external_bridge_bytes_anchor_complete").asBoolean()).isFalse();
        assertThat(contract.path("authorization")
                .path("route_promotion_blocked_by_bridge_bootstrap").asBoolean())
                .isTrue();
        assertThat(contract.path("authorization")
                .path("production_cutover").asBoolean()).isFalse();
        assertThat(contract.path("authorization")
                .path("all_59_target_dispositions_executed").asBoolean()).isTrue();
        assertThat(contract.path("authorization")
                .path("typed_parity_review_complete").asBoolean()).isFalse();
        assertThat(contract.path("acceptance")
                .path("all_59_target_dispositions_executed").asBoolean()).isTrue();
        assertThat(contract.path("acceptance")
                .path("business_jdbc_reached_http_count").asInt()).isEqualTo(49);
        assertThat(contract.path("acceptance")
                .path("pre_business_jdbc_termination_http_count").asInt()).isEqualTo(8);
        assertThat(contract.path("acceptance")
                .path("typed_parity_review_complete").asBoolean()).isFalse();
        assertThat(contract.path("acceptance")
                .path("post_push_external_git_anchor_required_before_route_migration")
                .asBoolean()).isTrue();
        assertThat(contract.path("acceptance")
                .path("production_cutover").asBoolean()).isFalse();
        assertThat(contract.path("acceptance")
                .path("new_worm_report_created").asBoolean()).isFalse();
        assertThat(contract.path("acceptance")
                .path("production_build_context_unchanged").asBoolean()).isTrue();
    }

    @Test
    void rejectsParityOverclaimAndAnyUnknownSuccessorSource() throws Exception {
        JsonNode fixed = contract();
        ObjectNode overclaim = (ObjectNode) fixed.deepCopy();
        ((ObjectNode) overclaim.path("authorization"))
                .put("full_target_parity_closed", true);
        assertThatThrownBy(() ->
                Phase4cHttpTargetExecutionSuccessorAcceptance.validate(overclaim))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("overclaims full_target_parity_closed");

        ObjectNode anchorOverclaim = (ObjectNode) fixed.deepCopy();
        ((ObjectNode) anchorOverclaim.path("authorization"))
                .put("external_bridge_bytes_anchor_complete", true);
        assertThatThrownBy(() ->
                Phase4cHttpTargetExecutionSuccessorAcceptance.validate(anchorOverclaim))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("external_bridge_bytes_anchor_complete");

        ObjectNode postPushRemoved = (ObjectNode) fixed.deepCopy();
        ((ObjectNode) postPushRemoved.path("acceptance"))
                .put("post_push_external_git_anchor_required_before_route_migration", false);
        assertThatThrownBy(() ->
                Phase4cHttpTargetExecutionSuccessorAcceptance.validate(postPushRemoved))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("acceptance boundary");

        ObjectNode unknownSource = (ObjectNode) fixed.deepCopy();
        ObjectNode sources = (ObjectNode) unknownSource.path("source_contracts");
        sources.set("unknown_self_authorized_source",
                sources.path("predecessor").deepCopy());
        assertThatThrownBy(() ->
                Phase4cHttpTargetExecutionSuccessorAcceptance.validate(unknownSource))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("source contract set");

        assertThat(Phase4cHttpTargetExecutionSuccessorAcceptance.acceptedHash(
                "docs/refactor/phase4c/route-parity-delta.csv")).isNotNull();
        assertThat(Phase4cHttpTargetExecutionSuccessorAcceptance.acceptedHash(
                "tools/phase4c_http_target_execution_successor_acceptance.py")).isNull();
        assertThat(Phase4cHttpTargetExecutionSuccessorAcceptance.acceptedHash(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpTargetExecutionSuccessorAcceptance.java")).isNull();
        assertThat(Phase4cHttpTargetExecutionSuccessorAcceptance.acceptedHash(
                "unknown/self-authorized-source")).isNull();
    }

    private static JsonNode contract() throws Exception {
        return Phase4cHttpTargetExecutionSuccessorAcceptance.load(root());
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

    private static Map<String, JsonNode> casesById(JsonNode cases) {
        Map<String, JsonNode> values = new LinkedHashMap<>();
        cases.forEach(item -> assertThat(values.put(
                item.path("case_id").asString(), item)).isNull());
        return Map.copyOf(values);
    }

    private static JsonNode caseById(JsonNode cases, String caseId) {
        return casesById(cases).get(caseId);
    }

    private static Map<String, Integer> counts(JsonNode cases, String field) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        cases.forEach(item -> counts.merge(
                item.path(field).asString(), 1, Integer::sum));
        return Map.copyOf(counts);
    }

    private static Map<String, Integer> textIntegerMap(JsonNode object) {
        Map<String, Integer> values = new LinkedHashMap<>();
        object.properties().forEach(entry -> values.put(
                entry.getKey(), entry.getValue().asInt()));
        return Map.copyOf(values);
    }

    private static void assertOptionalEqual(
            JsonNode target,
            JsonNode historical,
            String field,
            String caseId
    ) {
        assertThat(target.has(field)).as(caseId + ":" + field)
                .isEqualTo(historical.has(field));
        if (target.has(field)) {
            assertThat(target.path(field)).as(caseId + ":" + field)
                    .isEqualTo(historical.path(field));
        }
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }
}
