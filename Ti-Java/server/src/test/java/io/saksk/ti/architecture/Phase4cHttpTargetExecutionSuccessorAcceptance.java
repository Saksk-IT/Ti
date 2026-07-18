package io.saksk.ti.architecture;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** Bootstrap validator for the reviewed Phase 4C HTTP target-execution successor. */
final class Phase4cHttpTargetExecutionSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-contract";
    private static final String CONTRACT_STATUS =
            "target_dispositions_executed_typed_parity_review_pending_routes_pending";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution";
    private static final String CONTRACT_CAPTURED_AT = "2026-07-18T10:00:00+08:00";
    private static final String NEXT_GATE =
            "commit_and_push_this_bootstrap_checkpoint_then_anchor_its_git_commit_"
                    + "contract_sha256_and_both_bridge_sha256_in_the_next_node_before_"
                    + "typed_parity_network_redis_identity_review_or_route_migration";
    private static final List<String> EXPECTED_PRE_BUSINESS_FAMILIES = List.of(
            "BANK_ACCESS",
            "SHARE_ACCESS",
            "TAG_MEMBERSHIP",
            "FAVORITE_MEMBERSHIP",
            "MISTAKE_MEMBERSHIP",
            "QUESTION_SUMMARY");

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-contract.json";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-user-counts-http-implementation-contract";
    private static final String PREDECESSOR_STATUS =
            "implementation_present_parity_incomplete_routes_pending";
    private static final String PREDECESSOR_SCOPE =
            "phase4c-personal-bank-user-counts-http-implementation";
    private static final String PREDECESSOR_SHA256 =
            "c6a977f260bdd0ab4af6dace1b4c7d48803b5e8f9bc5299723b662226e45cfbd";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "f6eff86bea6a1d04bc43bfe8a532ff952f295c6aa2d1d89f6b40f6fe02dc91f9";
    private static final String PREDECESSOR_TRUST_PAYLOAD_SHA256 =
            "624bb2b801a51e0fd19ae4d4583d77c6b6195355685b202b4c5ac3aa56d2cf8f";
    private static final String READ_PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/personal-bank-user-counts-read-contract.json";
    private static final String READ_PREDECESSOR_SHA256 =
            "458ba5aafe10a451ab05d05f1edf2ac1d5e20a93e01c20fc1b8fe1d2eb750f73";
    private static final String READ_PREDECESSOR_PAYLOAD_SHA256 =
            "216cf664c4d74e67169f4f5c8091f80296964938d31911e3a32aeb3630a3d7a5";
    private static final String ALL_SHARES_ENTRY_RELATIVE =
            "docs/refactor/phase4b/personal-bank-all-shares-entry-contract.json";
    private static final String ALL_SHARES_ENTRY_SHA256 =
            "b4311e170cde6657a9ddd30885f17cd847f56a61e8e8f24c159be425d5931fbb";
    private static final String ALL_SHARES_ENTRY_PAYLOAD_SHA256 =
            "f99637c5efa2eddc3c26beced868002da8b145c3eb022aba0355316bbe4b97ae";

    // Replace only after the contract and both successor bridges are final.
    private static final String TRUST_PAYLOAD_SHA256 =
            "0634daf8ba1489a3f4fa6f1f958ee5042113fb2e62e2af9f864159c14fd92500";
    private static final String BRIDGE_PROVENANCE_SENTINEL =
            "<bridge-self-provenance-sha256>";
    private static final Set<String> BRIDGE_SOURCE_KEYS = Set.of(
            "python_successor_bridge", "java_successor_bridge");

    private static final String GOLDEN_RELATIVE =
            "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json";
    private static final String GOLDEN_SHA256 =
            "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1";
    private static final String GOLDEN_CASE_PAYLOAD_SHA256 =
            "0ace2f642523a62e802db3dc3d045d601743a277e7edf7e2cf214d00619a51bf";
    private static final String GOLDEN_ORDERED_CASE_IDS_SHA256 =
            "d8c9aa1c8fdcfd833f2d7bbba3e21adcc3e696954b8756ace69405428bbdfad8";
    private static final String MAPPING_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-mapping-evidence.json";
    private static final String MAPPING_SHA256 =
            "d039193c2ecfb644fdd356b196f6551440e63ee27eba0645d9f8e5bef923b4d3";
    private static final String EVIDENCE_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-golden-target-execution-evidence.json";
    private static final String EVIDENCE_ID =
            "ti.phase4c.personal-bank-user-counts-golden-target-execution-evidence";
    private static final String EVIDENCE_SHA256 =
            "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002";
    private static final String EVIDENCE_CASE_PAYLOAD_SHA256 =
            "75be10b21c2c006d978575dda314003536ac8920ecd6c6fbe64cfdd264d2b17f";
    private static final String EVIDENCE_PAYLOAD_SHA256 =
            "5ca521f808aa67ea4589d044d04a0037e448dc9d2a519e3b6af7d776b2cb89de";
    private static final String SOURCE_CHECKPOINT_COMMIT =
            "67dddb831bac8499e80f4af57c959e9c6b244519";
    private static final String SOURCE_CHECKPOINT_COMMITTED_AT =
            "2026-07-18T09:57:07+08:00";
    private static final String SOURCE_CHECKPOINT_SUBJECT =
            "test(java): remove legacy credential expiry bombs";

    private static final String WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String WORM_SHA256 =
            "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39";
    private static final String BUILD_CONTEXT_SHA256 =
            "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3";
    private static final String PRODUCTION_MANIFEST_SHA256 =
            "d327a5ef85fa47abc6417527d7bfd99a01f29de6ea3c2f08205cbf30a6e38f79";
    private static final int PRODUCTION_FILE_COUNT = 297;

    private static final String TYPED_REJECTION_CASE =
            "access-shared-malformed-expiry-value-error";
    private static final String TYPED_COLLAPSE_CASE =
            "access-shared-aware-expiry-type-error";
    private static final Set<String> HTTP_DIFFERENCE_IDS = Set.of(
            "P4C-LEARNING-007", "P4C-LEARNING-008", "P4C-LEARNING-009",
            "P4C-LEARNING-010", "P4C-LEARNING-011", "P4C-LEARNING-012");
    private static final Map<String, Integer> DISPOSITION_COUNTS = Map.of(
            "EXECUTED_FULL_CONTEXT_HTTP", 46,
            "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT", 11,
            "EXECUTED_TYPED_REJECTION", 1,
            "EXECUTED_TYPED_COLLAPSE", 1);
    private static final Map<Integer, Integer> HTTP_STATUS_COUNTS = Map.of(
            200, 34, 302, 5, 401, 3, 403, 10, 500, 5);
    private static final Map<String, String> SOURCE_PATHS = sourcePaths();
    private static final Map<String, String> ACCEPTED_SOURCES = acceptedSources();

    private Phase4cHttpTargetExecutionSuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = readFixedJson(root, CONTRACT_RELATIVE);
        validate(contract);
        JsonNode predecessor = validatePredecessor(root, contract);
        validateFixedSources(root, contract);
        validateHistoricalSuccessors(root, contract, predecessor);
        validateProductionSurface(root, contract, predecessor);
        validateExecutionEvidence(root, contract);
        validateRoutesOwnershipAndWorm(root, contract);
        return contract;
    }

    static void validate(JsonNode contract) {
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status",
                        "scope", "predecessor", "source_contracts",
                        "historical_successor_acceptance", "bridge_provenance",
                        "production_surface",
                        "verification_evidence", "routes_and_openapi",
                        "data_ownership", "worm_evidence", "authorization",
                        "acceptance", "document_payload_sha256")),
                "unexpected target-execution top-level shape");
        require(contract.path("schema_version").asInt() == 1,
                "unexpected target-execution schema version");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString()),
                "unexpected target-execution contract id");
        require(CONTRACT_STATUS.equals(contract.path("status").asString()),
                "unexpected target-execution contract status");
        require(CONTRACT_SCOPE.equals(contract.path("scope").asString()),
                "unexpected target-execution contract scope");
        require(CONTRACT_CAPTURED_AT.equals(contract.path("captured_at").asString()),
                "unexpected target-execution capture timestamp");

        JsonNode predecessor = contract.path("predecessor");
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "trust_payload_sha256", "contract_id", "status",
                        "scope", "immutable")),
                "unexpected target-execution predecessor shape");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_TRUST_PAYLOAD_SHA256.equals(
                        predecessor.path("trust_payload_sha256").asString())
                        && PREDECESSOR_ID.equals(predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString())
                        && predecessor.path("immutable").asBoolean(),
                "target-execution predecessor reference drifted");

        JsonNode sources = contract.path("source_contracts");
        require(propertyNames(sources).equals(SOURCE_PATHS.keySet()),
                "unexpected target-execution source contract set");
        SOURCE_PATHS.forEach((name, relative) -> {
            JsonNode reference = sources.path(name);
            require(propertyNames(reference).equals(Set.of("source", "sha256")),
                    "unexpected target-execution source shape: " + name);
            require(relative.equals(reference.path("source").asString()),
                    "target-execution source path drifted: " + name);
            require(isSha256(reference.path("sha256").asString()),
                    "unsettled target-execution source hash: " + name);
        });

        validateHistoricalShape(contract.path("historical_successor_acceptance"));
        validateBridgeProvenance(contract.path("bridge_provenance"));
        validateProductionShape(contract.path("production_surface"));
        require(propertyNames(contract.path("verification_evidence")).equals(Set.of(
                        "target_execution", "historical_partial_mapping",
                        "junit", "postgresql")),
                "unexpected target-execution verification shape");
        validateRouteShape(contract.path("routes_and_openapi"));
        require(propertyNames(contract.path("data_ownership")).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "resource_count", "resources_with_exactly_one_owner",
                        "canonical_owner_manifest_sha256",
                        "unchanged_from_predecessor")),
                "unexpected target-execution data-ownership shape");
        validateWormShape(contract.path("worm_evidence"));
        validateClaimBoundaries(contract);

        require(contract.path("document_payload_sha256").asString().equals(
                        canonicalPayloadSha256(contract, false)),
                "invalid target-execution document payload hash");
        require(isSha256(TRUST_PAYLOAD_SHA256),
                "unsettled target-execution trust payload SHA-256");
        require(TRUST_PAYLOAD_SHA256.equals(canonicalPayloadSha256(contract, true)),
                "target-execution bridge-normalized trust payload drifted");
    }

    static String acceptedHash(String relative) {
        return ACCEPTED_SOURCES.get(relative);
    }

    static String successorHash(Path tiJavaRoot, String relative) throws IOException {
        String accepted = ACCEPTED_SOURCES.get(relative);
        if (accepted == null) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = loadSuccessorEnvelope(root);
        JsonNode reference = contract.path("historical_successor_acceptance")
                .path("anchored_source_overrides")
                .path(relative);
        require(relative.equals(reference.path("source").asString())
                        && accepted.equals(
                        reference.path("accepted_sha256").asString()),
                "target-execution successor entry drifted: " + relative);
        String successor = reference.path("successor_sha256").asString();
        require(isSha256(successor),
                "target-execution successor hash is invalid: " + relative);
        return validateTerminalSource(
                root, relative, successor, "target-execution successor");
    }

    private static JsonNode loadSuccessorEnvelope(Path root) throws IOException {
        JsonNode contract = readFixedJson(root, CONTRACT_RELATIVE);
        validate(contract);
        return contract;
    }

    private static JsonNode validatePredecessor(Path root, JsonNode contract)
            throws IOException {
        validateTerminalSource(
                root,
                PREDECESSOR_RELATIVE,
                PREDECESSOR_SHA256,
                "target-execution predecessor");
        JsonNode predecessor = readFixedJson(root, PREDECESSOR_RELATIVE);
        require(PREDECESSOR_ID.equals(predecessor.path("contract_id").asString()),
                "unexpected physical implementation predecessor id");
        require(PREDECESSOR_STATUS.equals(predecessor.path("status").asString()),
                "unexpected physical implementation predecessor status");
        require(PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString()),
                "unexpected physical implementation predecessor scope");
        require(PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        canonicalPayloadSha256(predecessor, false)),
                "implementation predecessor payload drifted");
        require(PREDECESSOR_TRUST_PAYLOAD_SHA256.equals(
                        canonicalPayloadSha256(predecessor, true)),
                "implementation predecessor independent trust payload drifted");
        validateTerminalSource(
                root,
                PREDECESSOR_RELATIVE,
                contract.path("predecessor").path("sha256").asString(),
                "contract implementation predecessor binding");
        return predecessor;
    }

    private static void validateFixedSources(Path root, JsonNode contract)
            throws IOException {
        JsonNode sources = contract.path("source_contracts");
        for (Map.Entry<String, String> entry : SOURCE_PATHS.entrySet()) {
            validateTerminalSource(
                    root,
                    entry.getValue(),
                    sources.path(entry.getKey()).path("sha256").asString(),
                    "fixed target-execution source " + entry.getKey());
        }
    }

    private static void validateHistoricalShape(JsonNode history) {
        require(propertyNames(history).equals(Set.of(
                        "predecessor_sha256", "predecessor_trust_payload_sha256",
                        "anchored_source_overrides",
                        "successor_allowlist", "successor_allowlist_exact",
                        "accepted_hashes_independently_located",
                        "predecessor_rewrite_forbidden",
                        "arbitrary_source_hash_lookup_forbidden",
                        "current_bridges_excluded_from_historical_accepted_hash_allowlist")),
                "unexpected target-execution historical successor shape");
        require(PREDECESSOR_SHA256.equals(
                        history.path("predecessor_sha256").asString())
                        && PREDECESSOR_TRUST_PAYLOAD_SHA256.equals(
                        history.path("predecessor_trust_payload_sha256").asString()),
                "historical successor predecessor binding drifted");
        List<String> allowlist = strings(history.path("successor_allowlist"));
        require(allowlist.equals(ACCEPTED_SOURCES.keySet().stream().sorted().toList()),
                "historical successor allowlist drifted");
        require(propertyNames(history.path(
                        "anchored_source_overrides"))
                        .equals(ACCEPTED_SOURCES.keySet()),
                "historical successor override set drifted");
        for (String flag : Set.of(
                "successor_allowlist_exact",
                "accepted_hashes_independently_located",
                "predecessor_rewrite_forbidden",
                "arbitrary_source_hash_lookup_forbidden",
                "current_bridges_excluded_from_historical_accepted_hash_allowlist")) {
            require(history.path(flag).asBoolean(),
                    "historical successor guard is open: " + flag);
        }
    }

    private static void validateBridgeProvenance(JsonNode provenance) {
        require(propertyNames(provenance).equals(Set.of(
                        "state", "normalized_source_keys", "normalization_sentinel",
                        "source_hashes_normalized_to_break_recursive_cycle",
                        "physical_hash_binding_scope",
                        "external_bridge_bytes_anchor_complete",
                        "post_push_external_git_anchor_required_before_route_promotion")),
                "unexpected target-execution bridge provenance shape");
        require("bootstrap_pending_post_push_external_git_anchor".equals(
                        provenance.path("state").asString())
                        && strings(provenance.path("normalized_source_keys")).equals(
                        BRIDGE_SOURCE_KEYS.stream().sorted().toList())
                        && BRIDGE_PROVENANCE_SENTINEL.equals(
                        provenance.path("normalization_sentinel").asString())
                        && provenance.path(
                        "source_hashes_normalized_to_break_recursive_cycle").asBoolean()
                        && "current_contract_and_worktree_only".equals(
                        provenance.path("physical_hash_binding_scope").asString())
                        && !provenance.path(
                        "external_bridge_bytes_anchor_complete").asBoolean()
                        && provenance.path(
                        "post_push_external_git_anchor_required_before_route_promotion")
                        .asBoolean(),
                "target-execution bridge bootstrap boundary drifted");
    }

    private static void validateHistoricalSuccessors(
            Path root,
            JsonNode contract,
            JsonNode predecessor
    ) throws IOException {
        JsonNode readPredecessor = validateAnchorContract(
                root,
                READ_PREDECESSOR_RELATIVE,
                READ_PREDECESSOR_SHA256,
                READ_PREDECESSOR_PAYLOAD_SHA256,
                "ti.phase4c.personal-bank-user-counts-read-contract",
                "implemented_and_targeted_verified_http_aliases_deferred");
        JsonNode allSharesEntry = validateAnchorContract(
                root,
                ALL_SHARES_ENTRY_RELATIVE,
                ALL_SHARES_ENTRY_SHA256,
                ALL_SHARES_ENTRY_PAYLOAD_SHA256,
                "ti.phase4b.personal-bank-all-shares-entry-contract",
                "entry_gate_passed_implementation_not_started");
        Map<String, String> predecessorSources = sourceIndex(
                predecessor.path("source_contracts"));
        Map<String, String> terminalSources = predecessorTerminalIndex(
                predecessor.path("historical_successor_acceptance"));
        Map<String, String> readSources = sourceIndex(
                readPredecessor.path("source_contracts"));
        Map<String, String> allSharesSources = sourceIndex(
                allSharesEntry.path("source_contracts"));
        JsonNode overrides = contract.path("historical_successor_acceptance")
                .path("anchored_source_overrides");
        for (Map.Entry<String, String> acceptedEntry : ACCEPTED_SOURCES.entrySet()) {
            String relative = acceptedEntry.getKey();
            String accepted = acceptedEntry.getValue();
            String provenance;
            if (accepted.equals(predecessorSources.get(relative))) {
                provenance = "predecessor.source_contracts";
            } else if (accepted.equals(terminalSources.get(relative))) {
                provenance = "predecessor.historical_successor_acceptance";
            } else if (accepted.equals(readSources.get(relative))) {
                provenance = "phase4c_read_predecessor.source_contracts";
            } else {
                require(accepted.equals(allSharesSources.get(relative)),
                        "accepted hash is not fixed by an anchor: " + relative);
                provenance = "phase4b_all_shares_entry.source_contracts";
            }
            JsonNode reference = overrides.path(relative);
            require(propertyNames(reference).equals(Set.of(
                            "source", "accepted_sha256",
                            "accepted_hash_provenance", "successor_sha256")),
                    "unexpected historical successor entry: " + relative);
            require(relative.equals(reference.path("source").asString())
                            && accepted.equals(
                            reference.path("accepted_sha256").asString())
                            && provenance.equals(reference.path(
                            "accepted_hash_provenance").asString()),
                    "historical successor entry drifted: " + relative);
            validateTerminalSource(
                    root,
                    relative,
                    reference.path("successor_sha256").asString(),
                    "historical successor override");
        }
    }

    private static JsonNode validateAnchorContract(
            Path root,
            String relative,
            String expectedSha256,
            String expectedPayloadSha256,
            String expectedId,
            String expectedStatus
    ) throws IOException {
        validateTerminalSource(root, relative, expectedSha256, "historical anchor");
        JsonNode document = readFixedJson(root, relative);
        require(expectedId.equals(document.path("contract_id").asString()),
                "historical anchor id drifted: " + relative);
        require(expectedStatus.equals(document.path("status").asString()),
                "historical anchor status drifted: " + relative);
        require(expectedPayloadSha256.equals(
                        document.path("document_payload_sha256").asString())
                        && expectedPayloadSha256.equals(
                        canonicalPayloadSha256(document, false)),
                "historical anchor payload drifted: " + relative);
        return document;
    }

    private static Map<String, String> sourceIndex(JsonNode sources) {
        Map<String, String> index = new LinkedHashMap<>();
        sources.forEach(reference -> {
            String relative = reference.path("source").asString();
            String previous = index.put(
                    relative, reference.path("sha256").asString());
            require(previous == null, "predecessor has duplicate source path: " + relative);
        });
        return Map.copyOf(index);
    }

    private static Map<String, String> predecessorTerminalIndex(JsonNode history) {
        Map<String, String> index = new LinkedHashMap<>();
        history.forEach(group -> {
            if (!group.isObject()) {
                return;
            }
            group.forEach(reference -> {
                if (!reference.isObject()
                        || !reference.has("source")
                        || !reference.has("successor_sha256")) {
                    return;
                }
                String relative = reference.path("source").asString();
                String digest = reference.path("successor_sha256").asString();
                String previous = index.put(relative, digest);
                require(previous == null || previous.equals(digest),
                        "predecessor has conflicting terminal hash: " + relative);
            });
        });
        return Map.copyOf(index);
    }

    private static void validateProductionShape(JsonNode production) {
        require(propertyNames(production).equals(Set.of(
                        "file_count", "manifest_sha256", "files",
                        "unchanged_from_predecessor")),
                "unexpected target-execution production shape");
        require(production.path("file_count").asInt() == PRODUCTION_FILE_COUNT,
                "target-execution production file count drifted");
        require(PRODUCTION_MANIFEST_SHA256.equals(
                        production.path("manifest_sha256").asString()),
                "target-execution production manifest drifted");
        require(production.path("files").isObject()
                        && production.path("files").size() == PRODUCTION_FILE_COUNT,
                "target-execution production file set is incomplete");
        require(production.path("unchanged_from_predecessor").asBoolean(),
                "target execution changed the production runtime");
    }

    private static void validateProductionSurface(
            Path root,
            JsonNode contract,
            JsonNode predecessor
    ) throws IOException {
        JsonNode predecessorCurrent = predecessor.path("implementation")
                .path("production_runtime_transition").path("current");
        require(predecessorCurrent.path("file_count").asInt() == PRODUCTION_FILE_COUNT
                        && PRODUCTION_MANIFEST_SHA256.equals(
                        predecessorCurrent.path("manifest_sha256").asString())
                        && canonicalNodeSha256(predecessorCurrent.path("files"))
                        .equals(PRODUCTION_MANIFEST_SHA256),
                "fixed predecessor production surface drifted");
        JsonNode production = contract.path("production_surface");
        require(production.path("files").equals(predecessorCurrent.path("files")),
                "target-execution contract changed predecessor runtime files");
        Map<String, String> physical = productionRuntimeManifest(root);
        require(physical.size() == PRODUCTION_FILE_COUNT,
                "physical production runtime file count drifted");
        require(PRODUCTION_MANIFEST_SHA256.equals(
                        canonicalNodeSha256(JSON.valueToTree(physical))),
                "physical production runtime manifest drifted");
        require(JSON.valueToTree(physical).equals(production.path("files")),
                "target-execution production surface differs from worktree");
    }

    private static void validateExecutionEvidence(Path root, JsonNode contract)
            throws IOException {
        validateTerminalSource(
                root,
                EVIDENCE_RELATIVE,
                EVIDENCE_SHA256,
                "target-execution evidence");
        JsonNode evidence = readFixedJson(root, EVIDENCE_RELATIVE);
        require(evidence.path("schema_version").asInt() == 1
                        && EVIDENCE_ID.equals(evidence.path("evidence_id").asString()),
                "unexpected target-execution evidence identity");
        require(EVIDENCE_PAYLOAD_SHA256.equals(
                        evidence.path("document_payload_sha256").asString())
                        && EVIDENCE_PAYLOAD_SHA256.equals(
                        canonicalPayloadSha256(evidence, false)),
                "target-execution evidence payload drifted");
        require(SOURCE_CHECKPOINT_COMMIT.equals(
                        evidence.path("source_checkpoint").path("commit").asString())
                        && SOURCE_CHECKPOINT_COMMITTED_AT.equals(
                        evidence.path("source_checkpoint").path(
                        "committed_at").asString())
                        && SOURCE_CHECKPOINT_SUBJECT.equals(
                        evidence.path("source_checkpoint").path("subject").asString()),
                "target-execution source checkpoint drifted");
        Map<String, String> checkpointSources = Map.of(
                "target_execution_test", SOURCE_PATHS.get("target_execution_it"),
                "fault_injecting_data_source",
                SOURCE_PATHS.get("fault_injecting_data_source"),
                "postgresql_seed", SOURCE_PATHS.get("target_execution_seed"));
        JsonNode checkpointArtifacts = evidence.path("source_checkpoint")
                .path("artifacts");
        require(propertyNames(checkpointArtifacts).equals(checkpointSources.keySet()),
                "target-execution checkpoint artifact set drifted");
        for (Map.Entry<String, String> entry : checkpointSources.entrySet()) {
            JsonNode reference = checkpointArtifacts.path(entry.getKey());
            require(entry.getValue().equals(reference.path("path").asString()),
                    "target-execution checkpoint artifact drifted: " + entry.getKey());
            validateTerminalSource(
                    root,
                    entry.getValue(),
                    reference.path("sha256").asString(),
                    "target-execution checkpoint artifact " + entry.getKey());
        }

        JsonNode golden = readFixedJson(root, GOLDEN_RELATIVE);
        validateTerminalSource(root, GOLDEN_RELATIVE, GOLDEN_SHA256, "Phase 4B golden");
        require(GOLDEN_CASE_PAYLOAD_SHA256.equals(
                        golden.path("case_payload_sha256").asString())
                        && GOLDEN_CASE_PAYLOAD_SHA256.equals(
                        canonicalNodeSha256(golden.path("cases"))),
                "Phase 4B golden case payload drifted");
        List<String> goldenIds = caseIds(golden.path("cases"));
        require(goldenIds.size() == 59
                        && GOLDEN_ORDERED_CASE_IDS_SHA256.equals(
                        canonicalNodeSha256(JSON.valueToTree(goldenIds))),
                "Phase 4B golden case order drifted");

        JsonNode mapping = readFixedJson(root, MAPPING_RELATIVE);
        validateTerminalSource(
                root,
                MAPPING_RELATIVE,
                MAPPING_SHA256,
                "historical target mapping");
        require("PARTIAL_EXECUTION_MAPPING_LEDGER".equals(
                        mapping.path("claim").path("classification").asString()),
                "historical target mapping classification drifted");
        require(caseIds(mapping.path("cases")).equals(goldenIds),
                "historical mapping case order drifted");
        Map<String, JsonNode> mappingById = casesById(mapping.path("cases"));

        JsonNode summary = evidence.path("summary");
        requireSummary(summary);
        JsonNode claim = evidence.path("claim");
        require("TARGET_EXECUTION_DISPOSITION_LEDGER".equals(
                        claim.path("classification").asString())
                        && claim.path("full_target_execution_dispositions_closed")
                        .asBoolean()
                        && claim.path("historical_bound_only_cases_remaining").asInt() == 0
                        && !claim.path("mocked_application_results_used").asBoolean()
                        && !claim.path("full_target_parity_closed").asBoolean()
                        && !claim.path("route_migration_eligible").asBoolean()
                        && !claim.path("cutover_evidence").asBoolean(),
                "target-execution evidence claim drifted");

        JsonNode cases = evidence.path("cases");
        require(cases.isArray() && cases.size() == 59
                        && EVIDENCE_CASE_PAYLOAD_SHA256.equals(
                        canonicalNodeSha256(cases))
                        && caseIds(cases).equals(goldenIds),
                "target-execution evidence case payload/order drifted");

        List<String> ordinaryIds = goldenIds.stream()
                .filter(id -> !id.startsWith("fault-"))
                .filter(id -> !Set.of(
                        TYPED_REJECTION_CASE, TYPED_COLLAPSE_CASE).contains(id))
                .toList();
        List<String> faultIds = goldenIds.stream()
                .filter(id -> id.startsWith("fault-"))
                .toList();
        List<String> executionIds = new ArrayList<>(ordinaryIds);
        executionIds.addAll(faultIds);
        executionIds.add(TYPED_REJECTION_CASE);
        executionIds.add(TYPED_COLLAPSE_CASE);
        Map<String, Integer> executionOrdinals = new LinkedHashMap<>();
        for (int index = 0; index < executionIds.size(); index++) {
            executionOrdinals.put(executionIds.get(index), index + 1);
        }

        Map<String, Integer> dispositions = new LinkedHashMap<>();
        Map<String, Integer> aliases = new LinkedHashMap<>();
        Map<Integer, Integer> statuses = new LinkedHashMap<>();
        List<String> inheritedCases = new ArrayList<>();
        int businessJdbcReachedHttpCount = 0;
        int preBusinessJdbcTerminationHttpCount = 0;
        Map<Integer, Integer> preBusinessJdbcTerminationStatuses =
                new LinkedHashMap<>();
        for (int index = 0; index < cases.size(); index++) {
            JsonNode item = cases.path(index);
            JsonNode source = golden.path("cases").path(index);
            String caseId = source.path("case_id").asString();
            JsonNode historical = mappingById.get(caseId);
            require(item.path("canonical_case_ordinal").asInt() == index + 1,
                    "canonical case ordinal drifted: " + caseId);
            int executionOrdinal = executionOrdinals.get(caseId);
            require(item.path("execution_ordinal").asInt() == executionOrdinal
                            && item.path("junit").path("disposition_leaf_ordinal")
                            .asInt() == executionOrdinal + 1,
                    "execution/JUnit ordinal drifted: " + caseId);
            require(source.path("route_id").asString()
                            .equals(item.path("route_id").asString()),
                    "route id drifted: " + caseId);
            String alias = source.path("request").path("path").asString()
                    .startsWith("/api/") ? "api" : "web";
            require(alias.equals(item.path("alias").asString()),
                    "case alias drifted: " + caseId);
            require(historical.path("adapter_execution").asString().equals(
                            item.path("source_case_classification").asString())
                            && historical.path("bindings").equals(
                            item.path("historical_binding_ids")),
                    "historical mapping binding drifted: " + caseId);
            require(historical.path("http_slice_difference_ids").equals(
                            item.path("http_slice_difference_ids")),
                    "HTTP difference binding drifted: " + caseId);
            for (String difference : strings(item.path("http_slice_difference_ids"))) {
                require(HTTP_DIFFERENCE_IDS.contains(difference),
                        "unknown HTTP difference binding: " + caseId);
            }
            requireOptionalEqual(item, historical,
                    "inherited_predecessor_difference_id", caseId);
            requireOptionalEqual(item, historical, "target_data_source_case", caseId);
            requireOptionalEqual(item, historical, "tracking_note", caseId);
            if (item.has("inherited_predecessor_difference_id")) {
                require("P4C-LEARNING-006".equals(item.path(
                                "inherited_predecessor_difference_id").asString()),
                        "unexpected inherited difference: " + caseId);
                inheritedCases.add(caseId);
            }

            String disposition = expectedDisposition(caseId);
            require(disposition.equals(item.path("execution_disposition").asString()),
                    "target disposition drifted: " + caseId);
            dispositions.merge(disposition, 1, Integer::sum);
            boolean typed = disposition.startsWith("EXECUTED_TYPED_");
            require(item.path("http_execution").asBoolean() != typed,
                    "HTTP execution flag drifted: " + caseId);
            if (typed) {
                require(item.has("target_status") && item.path("target_status").isNull(),
                        "typed disposition invented an HTTP status: " + caseId);
                validateTypedCase(item, caseId);
            } else {
                int status = historical.path("target_status").asInt();
                require(item.path("target_status").asInt() == status,
                        "target HTTP status drifted: " + caseId);
                aliases.merge(alias, 1, Integer::sum);
                statuses.merge(status, 1, Integer::sum);
                validateHttpSideEffects(item, caseId);
                JsonNode sqlBoundary = item.path("sql_boundary");
                require(sqlBoundary.path("business_jdbc_reached").isBoolean(),
                        "HTTP business JDBC marker drifted: " + caseId);
                if (sqlBoundary.path("business_jdbc_reached").asBoolean()) {
                    businessJdbcReachedHttpCount++;
                    require(sqlBoundary.path(
                                    "business_connections_read_only").asBoolean(),
                            "HTTP business JDBC read-only marker drifted: " + caseId);
                } else {
                    preBusinessJdbcTerminationHttpCount++;
                    preBusinessJdbcTerminationStatuses.merge(
                            status, 1, Integer::sum);
                    JsonNode executionFamilies = sqlBoundary.path("execution_families");
                    String expectedTermination = status == 302
                            ? "WEB_PRE_AUTHENTICATION"
                            : "AUTHENTICATION";
                    boolean executionFamiliesValid = status == 302
                            ? strings(executionFamilies).isEmpty()
                            : strings(executionFamilies).equals(List.of())
                                    || strings(executionFamilies)
                                    .equals(List.of("AUTHORITY_USERS"));
                    boolean absentFamiliesValid = status != 401
                            || strings(sqlBoundary.path(
                                    "business_execution_families_absent"))
                            .equals(EXPECTED_PRE_BUSINESS_FAMILIES);
                    require((status == 302 || status == 401)
                                    && "EXACT".equals(sqlBoundary.path(
                                    "execution_family_assertion").asString())
                                    && expectedTermination.equals(sqlBoundary.path(
                                    "termination").asString())
                                    && executionFamilies.isArray()
                                    && executionFamiliesValid
                                    && absentFamiliesValid,
                            "HTTP pre-business termination boundary drifted: " + caseId);
                }
                if (caseId.startsWith("fault-")) {
                    validateFaultCase(item, caseId, status);
                } else {
                    require(!item.has("fault_evidence") && !item.has("typed_evidence"),
                            "ordinary HTTP case has specialized evidence: " + caseId);
                }
            }
        }
        require(dispositions.equals(DISPOSITION_COUNTS),
                "target disposition distribution drifted");
        require(aliases.equals(Map.of("api", 43, "web", 14)),
                "target HTTP alias distribution drifted");
        require(statuses.equals(HTTP_STATUS_COUNTS),
                "target HTTP status distribution drifted");
        require(businessJdbcReachedHttpCount == 49
                        && preBusinessJdbcTerminationHttpCount == 8,
                "target business JDBC reach counts drifted");
        require(preBusinessJdbcTerminationStatuses.equals(Map.of(302, 5, 401, 3)),
                "target pre-business status counts drifted");
        require(inheritedCases.equals(List.of(
                        "access-shared-fetchone-first-row",
                        "access-shared-cross-bank-record")),
                "inherited P4C-LEARNING-006 case set drifted");
        validateEvidenceBoundaries(evidence);
        validateContractEvidenceReference(contract, evidence, goldenIds);
    }

    private static void requireSummary(JsonNode summary) {
        Map<String, Integer> integerFields = Map.ofEntries(
                Map.entry("case_count", 59),
                Map.entry("http_execution_count", 57),
                Map.entry("business_jdbc_reached_http_count", 49),
                Map.entry("pre_business_jdbc_termination_http_count", 8),
                Map.entry("non_fault_http_execution_count", 46),
                Map.entry("fault_http_execution_count", 11),
                Map.entry("typed_postgresql_disposition_count", 2),
                Map.entry("api_alias_http_execution_count", 43),
                Map.entry("web_alias_http_execution_count", 14),
                Map.entry("bound_only_case_count", 0),
                Map.entry("mocked_application_result_case_count", 0),
                Map.entry("junit_leaf_test_count", 60),
                Map.entry("supplementary_junit_test_count", 1));
        integerFields.forEach((field, value) -> require(
                summary.path(field).asInt() == value,
                "target-execution summary drifted: " + field));
        require(textIntegerMap(summary.path("http_status_counts")).equals(
                        Map.of("200", 34, "302", 5, "401", 3, "403", 10, "500", 5)),
                "target-execution HTTP status summary drifted");
        require(textIntegerMap(summary.path(
                        "pre_business_jdbc_termination_status_counts")).equals(
                        Map.of("302", 5, "401", 3)),
                "target-execution pre-business status summary drifted");
        require(textIntegerMap(summary.path("execution_disposition_counts"))
                        .equals(DISPOSITION_COUNTS),
                "target-execution disposition summary drifted");
    }

    private static void validateHttpSideEffects(JsonNode item, String caseId) {
        JsonNode effects = item.path("side_effect_assertions");
        require(effects.path("nine_table_database_fingerprint_unchanged").asBoolean()
                        && effects.path("write_dml_count").asInt() == 0
                        && effects.path("users_last_active_write_dml_count").asInt() == 0
                        && effects.path("schema_mutation_count").asInt() == 0
                        && "RESPONSE_HEADER_CONDITIONED".equals(
                        effects.path("rate_limit_assertion_mode").asString()),
                "HTTP side-effect assertion drifted: " + caseId);
    }

    private static void validateFaultCase(JsonNode item, String caseId, int status) {
        FaultPlan plan = faultPlan(caseId);
        JsonNode fault = item.path("fault_evidence");
        require(fault.isObject()
                        && plan.family().equals(fault.path("family").asString())
                        && fault.path("occurrence").asInt() == plan.occurrence()
                        && "42703".equals(fault.path("initial_sqlstate").asString())
                        && "25P02".equals(
                        fault.path("poisoned_transaction_sqlstate").asString())
                        && fault.path("fault_connection_read_only").asBoolean()
                        && fault.path("rollback_after_fault_on_same_connection")
                        .asBoolean()
                        && fault.path("failed_family_occurrence_has_no_success_record")
                        .asBoolean(),
                "PostgreSQL abort evidence drifted: " + caseId);
        boolean laterSuccess = status == 200
                && "QUESTION_SUMMARY".equals(plan.family())
                && plan.occurrence() < 4;
        require(fault.path(
                        "later_same_family_success_after_rollback_on_different_connection_required")
                        .asBoolean() == laterSuccess,
                "PostgreSQL recovery evidence drifted: " + caseId);
        require(!item.has("typed_evidence"),
                "fault case also claims typed evidence: " + caseId);
    }

    private static void validateTypedCase(JsonNode item, String caseId) {
        require(!item.has("fault_evidence") && item.path("typed_evidence").isObject(),
                "typed evidence binding drifted: " + caseId);
        JsonNode typed = item.path("typed_evidence");
        if (TYPED_REJECTION_CASE.equals(caseId)) {
            require("22007".equals(typed.path("sqlstate").asString())
                            && typed.path("attempted_bank_share_id").asInt() == 99656
                            && typed.path("attempted_bank_share_record_id").asInt() == 99676
                            && typed.path("persisted_bank_share_row_count").asInt() == 0
                            && typed.path("bank_shares_total_unchanged").asBoolean()
                            && typed.path("bank_share_records_total_unchanged").asBoolean(),
                    "typed rejection evidence drifted");
        } else {
            require(TYPED_COLLAPSE_CASE.equals(caseId)
                            && "2026-07-17T13:00:00".equals(
                            typed.path("projected_local_datetime").asString())
                            && typed.path("both_inputs_equal_after_projection").asBoolean()
                            && typed.path("source_offset_provenance_erased").asBoolean()
                            && typed.path("approved_null_expiry_bank_share_id").asInt()
                            == 99660
                            && typed.path("approved_null_expiry_is_sql_null").asBoolean()
                            && typed.path("bank_shares_total_unchanged").asBoolean()
                            && typed.path("bank_share_records_total_unchanged").asBoolean(),
                    "typed collapse evidence drifted");
        }
    }

    private static void validateEvidenceBoundaries(JsonNode evidence) {
        JsonNode harness = evidence.path("execution_harness");
        require(harness.path("full_spring_context").asBoolean()
                        && harness.path("full_production_filter_chain").asBoolean()
                        && harness.path("excluded_production_filters").size() == 0
                        && harness.path("mocked_application_or_authentication_ports")
                        .size() == 0
                        && "MockMvc".equals(harness.path("transport").asString())
                        && !harness.path("real_tomcat_transport").asBoolean()
                        && "18.4".equals(
                        harness.path("postgresql").path("version").asString())
                        && harness.path("postgresql").path("real_container").asBoolean()
                        && "7.4.7".equals(
                        harness.path("redis").path("version").asString())
                        && harness.path("redis").path("real_container").asBoolean(),
                "target-execution harness boundary drifted");
        JsonNode boundaries = evidence.path("route_worm_and_parity_boundaries");
        require(BUILD_CONTEXT_SHA256.equals(
                        boundaries.path("implementation_build_context_sha256").asString())
                        && boundaries.path("implementation_chain_node_count").asInt() == 5
                        && !boundaries.path("target_execution_worm_created").asBoolean()
                        && boundaries.path("route_counts").path("migrated").asInt() == 11
                        && boundaries.path("route_counts").path("pending").asInt() == 600
                        && boundaries.path("route_counts").path("cutover").asInt() == 0
                        && !boundaries.path("full_target_parity_closed").asBoolean()
                        && !boundaries.path("route_migration_eligible").asBoolean()
                        && !boundaries.path("production_cutover_evidence").asBoolean(),
                "target-execution route/WORM boundary drifted");
        JsonNode worm = boundaries.path("implementation_worm");
        require(WORM_RELATIVE.equals(worm.path("path").asString())
                        && WORM_SHA256.equals(worm.path("sha256").asString())
                        && worm.path("reused").asBoolean(),
                "target-execution evidence did not reuse the fifth WORM");
    }

    private static void validateContractEvidenceReference(
            JsonNode contract,
            JsonNode evidence,
            List<String> goldenIds
    ) {
        JsonNode verification = contract.path("verification_evidence");
        JsonNode target = verification.path("target_execution");
        require(EVIDENCE_RELATIVE.equals(target.path("source").asString())
                        && EVIDENCE_SHA256.equals(target.path("sha256").asString())
                        && EVIDENCE_ID.equals(target.path("evidence_id").asString())
                        && EVIDENCE_CASE_PAYLOAD_SHA256.equals(
                        target.path("case_payload_sha256").asString())
                        && EVIDENCE_PAYLOAD_SHA256.equals(
                        target.path("document_payload_sha256").asString())
                        && GOLDEN_ORDERED_CASE_IDS_SHA256.equals(
                        target.path("case_ids_sha256").asString()),
                "contract target-execution evidence reference drifted");
        Set<String> expectedSummaryFields = new LinkedHashSet<>(
                propertyNames(evidence.path("summary")));
        expectedSummaryFields.remove("execution_disposition_counts");
        require(propertyNames(target.path("summary")).equals(expectedSummaryFields),
                "contract target-execution summary field set drifted");
        expectedSummaryFields.forEach(field -> require(
                target.path("summary").path(field).equals(
                        evidence.path("summary").path(field)),
                "contract target-execution summary differs: " + field));
        require(textIntegerMap(target.path("disposition_counts"))
                        .equals(DISPOSITION_COUNTS),
                "contract target-execution disposition counts drifted");
        require(canonicalNodeSha256(JSON.valueToTree(goldenIds))
                        .equals(target.path("case_ids_sha256").asString()),
                "contract target-execution case order hash drifted");
        require("PARTIAL_EXECUTION_MAPPING_LEDGER".equals(verification
                        .path("historical_partial_mapping")
                        .path("classification").asString())
                        && verification.path("historical_partial_mapping")
                        .path("case_count").asInt() == 59
                        && verification.path("historical_partial_mapping")
                        .path("immutable").asBoolean(),
                "contract historical mapping reference drifted");
        JsonNode junit = verification.path("junit");
        require(junit.path("case_leaf_count").asInt() == 59
                        && junit.path("supplementary_leaf_count").asInt() == 1
                        && junit.path("total_leaf_count").asInt() == 60,
                "contract JUnit leaf accounting drifted");
        JsonNode postgres = verification.path("postgresql");
        require("18.4".equals(postgres.path("version").asString())
                        && postgres.path("real_container").asBoolean()
                        && postgres.path("read_only").asBoolean()
                        && postgres.path("users_last_active_write_dml_count").asInt() == 0,
                "contract PostgreSQL target-execution boundary drifted");
    }

    private static void validateRouteShape(JsonNode routes) {
        require(propertyNames(routes).equals(Set.of(
                        "routes", "implemented_pending_get_count",
                        "migrated_operation_count", "pending_operation_count",
                        "production_cutover_operation_count",
                        "route_migration_eligible", "counted_methods",
                        "derived_methods", "route_delta", "openapi_overlay")),
                "unexpected target-execution route shape");
        require(routes.path("implemented_pending_get_count").asInt() == 2
                        && routes.path("migrated_operation_count").asInt() == 11
                        && routes.path("pending_operation_count").asInt() == 600
                        && routes.path("production_cutover_operation_count").asInt() == 0
                        && !routes.path("route_migration_eligible").asBoolean()
                        && strings(routes.path("counted_methods")).equals(List.of("GET"))
                        && strings(routes.path("derived_methods"))
                        .equals(List.of("HEAD", "OPTIONS")),
                "target-execution route accounting drifted");
        require(routes.path("routes").isArray() && routes.path("routes").size() == 2,
                "target-execution route set drifted");
        Set<String> ids = new LinkedHashSet<>();
        routes.path("routes").forEach(route -> {
            ids.add(route.path("route_id").asString());
            require("GET".equals(route.path("method").asString())
                            && "learning".equals(route.path("target_module").asString())
                            && "pending".equals(route.path("migration_status").asString())
                            && !route.path("production_cutover").asBoolean(),
                    "target-execution route overclaims migration");
        });
        require(ids.equals(Set.of("6858f6fa506f", "006913d0d956")),
                "target-execution route ids drifted");
    }

    private static void validateWormShape(JsonNode worm) {
        require(propertyNames(worm).equals(Set.of(
                        "source", "sha256", "java_build_context_sha256",
                        "new_worm", "new_worm_report_created",
                        "production_build_context_unchanged", "read_role_closed",
                        "hibernate_schema_mode", "production_schema_or_index_changed",
                        "operator_migration_executed", "real_data_migration_executed",
                        "production_cutover")),
                "unexpected target-execution WORM shape");
        require(WORM_RELATIVE.equals(worm.path("source").asString())
                        && WORM_SHA256.equals(worm.path("sha256").asString())
                        && BUILD_CONTEXT_SHA256.equals(
                        worm.path("java_build_context_sha256").asString())
                        && !worm.path("new_worm").asBoolean()
                        && !worm.path("new_worm_report_created").asBoolean()
                        && worm.path("production_build_context_unchanged").asBoolean()
                        && worm.path("read_role_closed").asBoolean()
                        && "validate".equals(
                        worm.path("hibernate_schema_mode").asString())
                        && !worm.path("production_schema_or_index_changed").asBoolean()
                        && !worm.path("operator_migration_executed").asBoolean()
                        && !worm.path("real_data_migration_executed").asBoolean()
                        && !worm.path("production_cutover").asBoolean(),
                "target-execution WORM boundary drifted");
    }

    private static void validateClaimBoundaries(JsonNode contract) {
        JsonNode authorization = contract.path("authorization");
        require(propertyNames(authorization).equals(Set.of(
                        "target_dispositions_executed",
                        "all_59_target_dispositions_executed",
                        "typed_parity_review_complete", "full_target_parity_closed",
                        "route_migration_eligible",
                        "external_bridge_bytes_anchor_complete",
                        "route_promotion_blocked_by_bridge_bootstrap",
                        "two_legacy_get_routes_migrated",
                        "derived_head_and_options_count_as_migrated",
                        "production_schema_or_index", "operator_migration_implementation",
                        "real_data_migration_execution",
                        "migration_global_preflight_closed", "client_change",
                        "gateway_or_proxy_change", "production_cutover")),
                "unexpected target-execution authorization shape");
        require(authorization.path("target_dispositions_executed").asBoolean()
                        && authorization.path(
                        "all_59_target_dispositions_executed").asBoolean()
                        && !authorization.path("typed_parity_review_complete").asBoolean(),
                "target dispositions are not authorized");
        for (String field : Set.of(
                "full_target_parity_closed", "route_migration_eligible",
                "external_bridge_bytes_anchor_complete",
                "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated",
                "production_schema_or_index", "operator_migration_implementation",
                "real_data_migration_execution", "migration_global_preflight_closed",
                "client_change", "gateway_or_proxy_change", "production_cutover")) {
            require(!authorization.path(field).asBoolean(),
                    "target-execution authorization overclaims " + field);
        }
        require(authorization.path(
                        "route_promotion_blocked_by_bridge_bootstrap").asBoolean(),
                "bridge bootstrap no longer blocks route promotion");
        JsonNode acceptance = contract.path("acceptance");
        require(propertyNames(acceptance).equals(Set.of(
                        "target_dispositions_executed",
                        "all_59_target_dispositions_executed",
                        "typed_parity_review_complete", "case_count",
                        "http_execution_count", "business_jdbc_reached_http_count",
                        "pre_business_jdbc_termination_http_count",
                        "pre_business_jdbc_termination_status_counts",
                        "typed_postgresql_disposition_count",
                        "bound_only_case_count", "mocked_application_result_case_count",
                        "junit_leaf_test_count", "full_target_parity_closed",
                        "route_migration_eligible",
                        "external_bridge_bytes_anchor_complete",
                        "post_push_external_git_anchor_required_before_route_migration",
                        "implemented_pending_get_count",
                        "migrated_operation_count", "pending_operation_count",
                        "production_cutover_operation_count", "production_cutover",
                        "effective_resource_count", "resources_with_exactly_one_owner",
                        "production_runtime_unchanged", "new_worm",
                        "new_worm_report_created",
                        "production_build_context_unchanged",
                        "operator_and_real_migration_remain_blocked", "next_gate")),
                "unexpected target-execution acceptance shape");
        require(acceptance.path("target_dispositions_executed").asBoolean()
                        && acceptance.path(
                        "all_59_target_dispositions_executed").asBoolean()
                        && !acceptance.path("typed_parity_review_complete").asBoolean()
                        && acceptance.path("case_count").asInt() == 59
                        && acceptance.path("http_execution_count").asInt() == 57
                        && acceptance.path(
                        "business_jdbc_reached_http_count").asInt() == 49
                        && acceptance.path(
                        "pre_business_jdbc_termination_http_count").asInt() == 8
                        && textIntegerMap(acceptance.path(
                        "pre_business_jdbc_termination_status_counts")).equals(
                        Map.of("302", 5, "401", 3))
                        && acceptance.path("typed_postgresql_disposition_count").asInt() == 2
                        && acceptance.path("bound_only_case_count").asInt() == 0
                        && acceptance.path("mocked_application_result_case_count").asInt() == 0
                        && acceptance.path("junit_leaf_test_count").asInt() == 60
                        && !acceptance.path("full_target_parity_closed").asBoolean()
                        && !acceptance.path("route_migration_eligible").asBoolean()
                        && !acceptance.path(
                        "external_bridge_bytes_anchor_complete").asBoolean()
                        && acceptance.path(
                        "post_push_external_git_anchor_required_before_route_migration")
                        .asBoolean()
                        && acceptance.path("implemented_pending_get_count").asInt() == 2
                        && acceptance.path("migrated_operation_count").asInt() == 11
                        && acceptance.path("pending_operation_count").asInt() == 600
                        && acceptance.path("production_cutover_operation_count").asInt() == 0
                        && !acceptance.path("production_cutover").asBoolean()
                        && acceptance.path("production_runtime_unchanged").asBoolean()
                        && !acceptance.path("new_worm").asBoolean()
                        && !acceptance.path("new_worm_report_created").asBoolean()
                        && acceptance.path(
                        "production_build_context_unchanged").asBoolean()
                        && acceptance.path(
                        "operator_and_real_migration_remain_blocked").asBoolean(),
                "target-execution acceptance boundary drifted");
        require(NEXT_GATE.equals(acceptance.path("next_gate").asString()),
                "target-execution next gate drifted");
    }

    private static void validateRoutesOwnershipAndWorm(Path root, JsonNode contract)
            throws IOException {
        JsonNode routes = contract.path("routes_and_openapi");
        validateTerminalSource(
                root,
                SOURCE_PATHS.get("route_delta"),
                routes.path("route_delta").path("sha256").asString(),
                "route-delta physical binding");
        validateTerminalSource(
                root,
                SOURCE_PATHS.get("openapi_overlay"),
                routes.path("openapi_overlay").path("sha256").asString(),
                "OpenAPI physical binding");
        JsonNode ownership = contract.path("data_ownership");
        require(ownership.path("resource_count").asInt() == 160
                        && ownership.path("resources_with_exactly_one_owner").asInt() == 160
                        && ownership.path("unchanged_from_predecessor").asBoolean(),
                "target-execution data ownership drifted");
        validateTerminalSource(
                root,
                SOURCE_PATHS.get("ownership_effective"),
                ownership.path("sha256").asString(),
                "target-execution data ownership");
        JsonNode worm = readFixedJson(root, WORM_RELATIVE);
        validateTerminalSource(root, WORM_RELATIVE, WORM_SHA256, "implementation WORM");
        require(BUILD_CONTEXT_SHA256.equals(
                        worm.path("java").path("buildContextSha256").asString())
                        && "validate".equals(
                        worm.path("java").path("hibernateDdlAuto").asString()),
                "physical implementation WORM drifted");
        require(BUILD_CONTEXT_SHA256.equals(javaBuildContextSha256(root)),
                "physical Java build context drifted");
    }

    private static String validateTerminalSource(
            Path root,
            String relative,
            String declaredSha256,
            String label
    ) throws IOException {
        require(isSha256(declaredSha256),
                label + " declared hash is invalid: " + relative);
        String physicalSha256 = sha256(fixedRegularFile(root, relative));
        if (declaredSha256.equals(physicalSha256)) {
            return physicalSha256;
        }
        require(declaredSha256.equals(
                        Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                                .acceptedHash(relative)),
                "post-push successor did not accept exact " + label + ": " + relative);
        String successorSha256 =
                Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.successorHash(
                        root, relative);
        require(physicalSha256.equals(successorSha256),
                "post-push successor file hash drift for " + label + ": " + relative);
        return physicalSha256;
    }

    private static String javaBuildContextSha256(Path root) throws IOException {
        Process process = new ProcessBuilder(
                fixedRegularFile(root, SOURCE_PATHS.get(
                        "phase2_build_context_hasher")).toString())
                .directory(root.toFile())
                .redirectErrorStream(true)
                .start();
        String output = new String(
                process.getInputStream().readAllBytes(), StandardCharsets.UTF_8).strip();
        try {
            require(process.waitFor() == 0,
                    "Java build-context hasher failed: " + output);
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
            throw new IOException("interrupted while hashing Java build context", exception);
        }
        return output;
    }

    private static String expectedDisposition(String caseId) {
        if (TYPED_REJECTION_CASE.equals(caseId)) {
            return "EXECUTED_TYPED_REJECTION";
        }
        if (TYPED_COLLAPSE_CASE.equals(caseId)) {
            return "EXECUTED_TYPED_COLLAPSE";
        }
        if (caseId.startsWith("fault-")) {
            return "EXECUTED_FULL_CONTEXT_HTTP_WITH_POSTGRES_ABORT";
        }
        return "EXECUTED_FULL_CONTEXT_HTTP";
    }

    private static FaultPlan faultPlan(String caseId) {
        if (caseId.contains("share-access")) {
            return new FaultPlan("SHARE_ACCESS", 1);
        }
        if (caseId.contains("total")) {
            return new FaultPlan("QUESTION_SUMMARY", 1);
        }
        if (caseId.contains("favorites") || caseId.contains("source-favorites")) {
            return new FaultPlan("QUESTION_SUMMARY", 2);
        }
        if (caseId.contains("mistakes")) {
            return new FaultPlan("QUESTION_SUMMARY", 3);
        }
        if (caseId.contains("types")) {
            return new FaultPlan("QUESTION_SUMMARY", 4);
        }
        throw new AssertionError("unknown target fault case: " + caseId);
    }

    private static void requireOptionalEqual(
            JsonNode target,
            JsonNode historical,
            String field,
            String caseId
    ) {
        require(target.has(field) == historical.has(field),
                "optional historical field presence drifted: " + caseId + ":" + field);
        if (target.has(field)) {
            require(target.path(field).equals(historical.path(field)),
                    "optional historical field drifted: " + caseId + ":" + field);
        }
    }

    private static Map<String, JsonNode> casesById(JsonNode cases) {
        Map<String, JsonNode> result = new LinkedHashMap<>();
        cases.forEach(item -> require(result.put(
                        item.path("case_id").asString(), item) == null,
                "duplicate case id"));
        return Map.copyOf(result);
    }

    private static List<String> caseIds(JsonNode cases) {
        List<String> ids = new ArrayList<>();
        cases.forEach(item -> ids.add(item.path("case_id").asString()));
        require(new LinkedHashSet<>(ids).size() == ids.size(), "duplicate case id");
        return List.copyOf(ids);
    }

    private static Map<String, Integer> textIntegerMap(JsonNode object) {
        Map<String, Integer> values = new LinkedHashMap<>();
        object.properties().forEach(entry -> values.put(
                entry.getKey(), entry.getValue().asInt()));
        return Map.copyOf(values);
    }

    private static Map<String, String> productionRuntimeManifest(Path root)
            throws IOException {
        Map<String, String> manifest = new TreeMap<>();
        addManifestPath(root, "server/src/main", manifest);
        for (String relative : List.of(
                "server/pom.xml", "server/Dockerfile", "server/.dockerignore",
                "server/.mvn", "server/mvnw", "server/mvnw.cmd",
                "server/build-versions.properties", "compose.dev.yml", ".env.example",
                "contracts", "openapi")) {
            addManifestPath(root, relative, manifest);
        }
        return Collections.unmodifiableMap(new LinkedHashMap<>(manifest));
    }

    private static void addManifestPath(
            Path root,
            String relative,
            Map<String, String> manifest
    ) throws IOException {
        Path path = fixedPath(root, relative);
        if (Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) {
            manifest.put(relative, sha256(path));
            return;
        }
        require(Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS),
                "runtime manifest source is not a file/directory: " + relative);
        try (var paths = Files.walk(path)) {
            for (Path child : paths.sorted().toList()) {
                require(!Files.isSymbolicLink(child),
                        "runtime manifest contains symlink: " + child);
                if (Files.isRegularFile(child, LinkOption.NOFOLLOW_LINKS)) {
                    manifest.put(
                            root.relativize(child).toString().replace('\\', '/'),
                            sha256(child));
                }
            }
        }
    }

    private static JsonNode readFixedJson(Path root, String relative) throws IOException {
        return JSON.readTree(Files.readString(
                fixedRegularFile(root, relative), StandardCharsets.UTF_8));
    }

    private static Path fixedRegularFile(Path root, String relative) throws IOException {
        Path path = fixedPath(root, relative);
        require(Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS),
                "fixed target-execution path is not a regular file: " + relative);
        return path;
    }

    private static Path fixedPath(Path root, String relative) throws IOException {
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute() && !relative.contains(".."),
                "fixed target-execution path escapes Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : candidate) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed target-execution path contains symlink: " + relative);
        }
        Path resolved = root.resolve(candidate).normalize().toRealPath();
        require(resolved.startsWith(root),
                "fixed target-execution path resolves outside Ti-Java: " + relative);
        return resolved;
    }

    private static String sha256(Path path) throws IOException {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(Files.readAllBytes(path)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static String canonicalNodeSha256(JsonNode node) {
        StringBuilder canonical = new StringBuilder();
        appendCanonical(node, canonical, "", false, false);
        return sha256(canonical.toString());
    }

    private static String canonicalPayloadSha256(JsonNode document, boolean trust) {
        StringBuilder canonical = new StringBuilder();
        appendCanonical(document, canonical, "", trust, true);
        return sha256(canonical.toString());
    }

    private static void appendCanonical(
            JsonNode node,
            StringBuilder output,
            String path,
            boolean trust,
            boolean omitDocumentPayloadAtRoot
    ) {
        if (node.isObject()) {
            List<String> names = new ArrayList<>(propertyNames(node));
            if (path.isEmpty() && omitDocumentPayloadAtRoot) {
                names.remove("document_payload_sha256");
            }
            Collections.sort(names);
            output.append('{');
            boolean first = true;
            for (String name : names) {
                if (!first) {
                    output.append(',');
                }
                first = false;
                appendJsonString(name, output);
                output.append(':');
                String childPath = path + "/" + name;
                if (trust && bridgeSourceHashPath(childPath)) {
                    appendJsonString(BRIDGE_PROVENANCE_SENTINEL, output);
                } else {
                    appendCanonical(node.path(name), output, childPath, trust, false);
                }
            }
            output.append('}');
            return;
        }
        if (node.isArray()) {
            output.append('[');
            for (int index = 0; index < node.size(); index++) {
                if (index > 0) {
                    output.append(',');
                }
                appendCanonical(node.path(index), output, path + "/" + index, trust, false);
            }
            output.append(']');
            return;
        }
        if (node.isTextual()) {
            appendJsonString(node.asString(), output);
        } else if (node.isNull()) {
            output.append("null");
        } else {
            output.append(node.toString());
        }
    }

    private static boolean bridgeSourceHashPath(String path) {
        return BRIDGE_SOURCE_KEYS.stream()
                .anyMatch(key -> path.equals("/source_contracts/" + key + "/sha256"));
    }

    private static void appendJsonString(String value, StringBuilder output) {
        output.append('"');
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"' -> output.append("\\\"");
                case '\\' -> output.append("\\\\");
                case '\b' -> output.append("\\b");
                case '\f' -> output.append("\\f");
                case '\n' -> output.append("\\n");
                case '\r' -> output.append("\\r");
                case '\t' -> output.append("\\t");
                default -> {
                    if (character < 0x20) {
                        output.append("\\u")
                                .append(String.format("%04x", (int) character));
                    } else {
                        output.append(character);
                    }
                }
            }
        }
        output.append('"');
    }

    private static String sha256(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static Set<String> propertyNames(JsonNode node) {
        return Set.copyOf(node.propertyNames());
    }

    private static List<String> strings(JsonNode array) {
        List<String> values = new ArrayList<>();
        array.forEach(item -> values.add(item.asString()));
        return List.copyOf(values);
    }

    private static boolean isSha256(String value) {
        return value != null && value.matches("[0-9a-f]{64}");
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static Map<String, String> sourcePaths() {
        Map<String, String> sources = new LinkedHashMap<>();
        sources.put("predecessor", PREDECESSOR_RELATIVE);
        sources.put("phase4c_read_predecessor", READ_PREDECESSOR_RELATIVE);
        sources.put("phase4b_all_shares_entry_anchor", ALL_SHARES_ENTRY_RELATIVE);
        sources.put("phase4b_goldens", GOLDEN_RELATIVE);
        sources.put("historical_partial_mapping", MAPPING_RELATIVE);
        sources.put("target_execution_evidence", EVIDENCE_RELATIVE);
        sources.put("target_execution_it",
                "server/src/test/java/io/saksk/ti/integration/"
                        + "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java");
        sources.put("fault_injecting_data_source",
                "server/src/test/java/io/saksk/ti/support/"
                        + "Phase4cUserCountsFaultInjectingDataSource.java");
        sources.put("target_execution_seed",
                "server/src/test/resources/db/phase4c/"
                        + "071-personal-bank-user-counts-golden-target-seed.sql");
        sources.put("phase3_authentication_it",
                "server/src/test/java/io/saksk/ti/integration/"
                        + "Phase3AuthenticationIT.java");
        sources.put("auth_schema",
                "server/src/test/resources/db/phase3/030-auth-schema.sql");
        sources.put("share_list_schema",
                "server/src/test/resources/db/phase4b/"
                        + "062-personal-bank-share-list-schema.sql");
        sources.put("usage_stats_schema",
                "server/src/test/resources/db/phase4b/"
                        + "065-personal-bank-usage-stats-schema.sql");
        sources.put("user_counts_schema",
                "server/src/test/resources/db/phase4b/"
                        + "067-personal-bank-user-counts-schema.sql");
        sources.put("container_images",
                "server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java");
        sources.put("postgres_containers",
                "server/src/test/java/io/saksk/ti/support/"
                        + "Phase2PostgresContainers.java");
        sources.put("network_it",
                "server/src/test/java/io/saksk/ti/integration/"
                        + "LegacyPersonalBankUserCountsNetworkIT.java");
        sources.put("postgres_it",
                "server/src/test/java/io/saksk/ti/integration/"
                        + "Phase4cPersonalBankUserCountsJdbcCompatibilityIT.java");
        sources.put("redis_it",
                "server/src/test/java/io/saksk/ti/web/security/"
                        + "RedisPersonalBankUserCountsReadRateLimiterIT.java");
        sources.put("openapi_overlay",
                "openapi/phase4c-personal-bank-user-counts.openapi.json");
        sources.put("route_delta", "docs/refactor/phase4c/route-parity-delta.csv");
        sources.put("ownership_effective",
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-http-effective-data-ownership-status.json");
        sources.put("worm_tip", WORM_RELATIVE);
        sources.put("phase2_build_context_hasher",
                "infra/phase2/hash-java-build-context.sh");
        sources.put("approved_differences",
                "docs/refactor/phase4c/approved-differences.md");
        sources.put("application_test_configuration",
                "server/src/main/resources/application-test.yml");
        sources.put("phase2_minimal_reference_schema",
                "server/src/test/resources/db/phase2/minimal-reference-schema.sql");
        sources.put("phase2_readonly_role",
                "server/src/test/resources/db/phase2/020-test-readonly-role.sql");
        sources.put("server_pom", "server/pom.xml");
        sources.put("read_contract_builder",
                "tools/build_phase4c_personal_bank_user_counts_read_contract.py");
        sources.put("contract_builder",
                "tools/build_phase4c_personal_bank_user_counts_http_"
                        + "target_execution_contract.py");
        sources.put("contract_test",
                "tools/test_phase4c_personal_bank_user_counts_http_"
                        + "target_execution_contract.py");
        sources.put("python_successor_bridge",
                "tools/phase4c_http_target_execution_successor_acceptance.py");
        sources.put("java_successor_bridge",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpTargetExecutionSuccessorAcceptance.java");
        sources.put("java_contract_parity_test",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cPersonalBankUserCountsHttpTargetExecutionContractParityTest.java");
        sources.put("project_readme", "README.md");
        sources.put("progress", "docs/refactor/05-progress.md");
        sources.put("phase4c_readme", "docs/refactor/phase4c/README.md");
        sources.put("phase2_readme", "infra/phase2/README.md");
        sources.put("phase2_static_gate", "infra/phase2/verify-static.sh");
        sources.put("phase2_worm_validator",
                "tools/phase2_wormhole_successor_acceptance.py");
        sources.put("phase2_worm_validator_test",
                "tools/test_phase2_wormhole_successor_acceptance.py");
        sources.put("historical_python_implementation_successor_bridge",
                "tools/phase4c_http_implementation_successor_acceptance.py");
        sources.put("historical_implementation_contract_test",
                "tools/test_phase4c_personal_bank_user_counts_"
                        + "http_implementation_contract.py");
        sources.put("historical_java_implementation_successor_bridge",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpImplementationSuccessorAcceptance.java");
        sources.put("historical_python_read_successor_bridge",
                "tools/phase4c_read_successor_acceptance.py");
        sources.put("historical_java_read_successor_bridge",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cReadSuccessorAcceptance.java");
        sources.put("historical_all_shares_entry_contract_test",
                "tools/test_phase4b_personal_bank_all_shares_entry_contract.py");
        sources.put("historical_share_list_read_contract_test",
                "tools/test_phase4b_personal_bank_share_list_read_contract.py");
        sources.put("historical_composition_contract_test",
                "tools/test_phase4c_personal_bank_user_counts_composition_contract.py");
        sources.put("historical_read_contract_test",
                "tools/test_phase4c_personal_bank_user_counts_read_contract.py");
        return Map.copyOf(sources);
    }

    private static Map<String, String> acceptedSources() {
        Map<String, String> sources = new LinkedHashMap<>();
        sources.put("README.md",
                "37d97e57cd8526615d828601dc56fc344b6e9e8cd400da85ebb9bf77b87ca20e");
        sources.put("docs/refactor/05-progress.md",
                "12935066fb4a2c53c78213e2b269028b9e24342034640467cfcb1d4bb47858a9");
        sources.put("docs/refactor/phase4c/README.md",
                "c44612d78bdafa7bc550feed7496588f0d163f8f1dda72fba917a4590f1f7064");
        sources.put("docs/refactor/phase4c/route-parity-delta.csv",
                "fc3c61f84fba411ed2b5509f841c0183c4da7250ecbfc9c6d1ba03cbb3c01f9e");
        sources.put("infra/phase2/README.md",
                "2d5d4fa1f26ce1fde3a273631f309aab5496c64641acba0b26b814e3ec4b64d1");
        sources.put("infra/phase2/verify-static.sh",
                "5e26d01247dce13342972d4b189460f7ae6f788506c57550b42b5b1f4f658821");
        sources.put("tools/phase2_wormhole_successor_acceptance.py",
                "ac0f2adf78f09fd25fa27d2846dd972e877ca00f63dd37eb4efb05935c50cc13");
        sources.put("tools/test_phase2_wormhole_successor_acceptance.py",
                "c30199997348f971f29a9dfd1d87cba67513c56bb9e241dfc23d195a479ff230");
        sources.put("tools/phase4c_http_implementation_successor_acceptance.py",
                "e46e28e065613dec3cedfcadcddaeda91354c8901543dd3f5eeb6d8bff4cd1cd");
        sources.put(
                "tools/test_phase4c_personal_bank_user_counts_http_implementation_contract.py",
                "f4d9ae7fe8b2c48238469a7b53a434d6c10269aadfbc154bea7d30eddfceddc6");
        sources.put("server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpImplementationSuccessorAcceptance.java",
                "cd212636e08ce74efa9efbc3ee988f14b69032f6fc3f7e927a591737b35e29d3");
        sources.put("server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cReadSuccessorAcceptance.java",
                "7b486e7dfe6e6e7e24435854e7c0545b5f9fdaec785974fb44cd0978f8e40fa5");
        sources.put("tools/phase4c_read_successor_acceptance.py",
                "af08c2611bfb4f9a566ac01a644c65807a0b2eb3f60c61ad0344e8c958cda8a9");
        sources.put("tools/test_phase4b_personal_bank_all_shares_entry_contract.py",
                "2ed3c3d1168aeea07d863bcdd6c81522bc59e78d253242b9f36f3808b9ca0b40");
        sources.put("tools/test_phase4b_personal_bank_share_list_read_contract.py",
                "6869964c169b6970df0c9f762957664f2e711c2abb309a4e5a2a3689cb636f29");
        sources.put("server/src/test/java/io/saksk/ti/integration/"
                        + "Phase3AuthenticationIT.java",
                "cbafdbd774ab13429c834b20c7a89eab63f10f35edfc20173181bbbdf0e2e85c");
        sources.put("tools/test_phase4c_personal_bank_user_counts_"
                        + "composition_contract.py",
                "b41ad9f6252ec74c4914ad9bd5652d150bd08359b26fb26498c34fd3a337a186");
        sources.put("tools/test_phase4c_personal_bank_user_counts_read_contract.py",
                "5299925446ed7ef84828ea7de875cfdd070bff260e06a590cad2fd474473dd77");
        return Map.copyOf(sources);
    }

    private record FaultPlan(String family, int occurrence) {
    }
}
