package io.saksk.ti.architecture;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/** Java mirror for the fixed Phase 4C target-execution Git/JUnit anchor. */
final class Phase4cHttpTargetExecutionAnchorSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-anchor-contract.json";
    private static final String CONTRACT_SHA256 =
            "f966f9229949a37811da2402d3baf05dd78643ec4104a8f921dee10188bcd203";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "dbfe37e3e0d9b80ebb378a58b58aa7b15371d737b389f06f24f3018adb6b311e";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-anchor-contract";
    private static final String CONTRACT_STATUS =
            "target_execution_bootstrap_externally_anchored_"
                    + "normalized_junit_manifest_bootstrap_bound_routes_pending";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution-external-anchor";
    private static final String CAPTURED_AT = "2026-07-18T12:14:52+08:00";
    private static final String NEXT_GATE =
            "commit_and_push_this_anchor_checkpoint_then_git_anchor_the_normalized_"
                    + "junit_manifest_bytes_before_typed_parity_network_redis_identity_"
                    + "review_or_route_migration";

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "331c82ad941f4eeb3e07d1701271310f2b1dea91132794e4e5d1eb1b466fc458";
    private static final String PREDECESSOR_TRUST_SHA256 =
            "0634daf8ba1489a3f4fa6f1f958ee5042113fb2e62e2af9f864159c14fd92500";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-contract";
    private static final String PREDECESSOR_STATUS =
            "target_dispositions_executed_typed_parity_review_pending_routes_pending";
    private static final String PREDECESSOR_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution";
    private static final String BRIDGE_SENTINEL = "<bridge-self-provenance-sha256>";

    private static final String COMMIT_OID =
            "0531b3c9272f9743a374edcf5c8bbeb72643eb1b";
    private static final String ROOT_TREE_OID =
            "816e2a7376d147f4a4d1478586cd384edf2c2a8a";
    private static final String PARENT_OID =
            "67dddb831bac8499e80f4af57c959e9c6b244519";
    private static final String TI_JAVA_TREE_OID =
            "1d24e46d33c25170caddf6e25247a7b2945390e4";
    private static final String COMMIT_TIMESTAMP = "2026-07-18T12:14:52+08:00";
    private static final String COMMIT_SUBJECT =
            "test(java): record user counts target execution bootstrap";

    private static final String MANIFEST_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-target-execution-junit-manifest.json";
    private static final String MANIFEST_SHA256 =
            "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b";
    private static final String MANIFEST_PAYLOAD_SHA256 =
            "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c";
    private static final String LEAF_PAYLOAD_SHA256 =
            "77b0f4955931f2ad3206b7a1c0f9c9649b25a18c49bf1b259c452d169e5f0e04";
    private static final String RAW_REPORT_SHA256 =
            "bb114a5571ef645ba37864dae1862a3657d92755a60479d734ce3c72f8de24ab";
    private static final String TEST_CLASS =
            "io.saksk.ti.integration.LegacyPersonalBankUserCountsGoldenTargetExecutionIT";

    private static final String WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String WORM_SHA256 =
            "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39";
    private static final String WORM_PREDECESSOR_SHA256 =
            "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6";
    private static final String CANONICAL_SCHEMA_SHA256 =
            "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b";
    private static final String DOCKERFILE_SHA256 =
            "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499";
    private static final String BUILD_CONTEXT_SHA256 =
            "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3";

    private static final Map<String, Artifact> ARTIFACTS = Map.ofEntries(
            artifact(
                    "target_execution_contract",
                    PREDECESSOR_RELATIVE,
                    "575f05d4da531822e013d68eb6fb16a00f2bf8e0",
                    PREDECESSOR_SHA256,
                    74_597),
            artifact(
                    "python_successor_bridge",
                    "tools/phase4c_http_target_execution_successor_acceptance.py",
                    "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84",
                    "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c",
                    78_481),
            artifact(
                    "java_successor_bridge",
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
                    "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6",
                    "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15",
                    88_021),
            artifact(
                    "target_execution_test",
                    "server/src/test/java/io/saksk/ti/integration/"
                            + "LegacyPersonalBankUserCountsGoldenTargetExecutionIT.java",
                    "31a98f33aa2c8eb15a3476096965eb85d4912e06",
                    "45b1a96fcc66a436551a8ce7604b304f2a479cece87c431a3a3c003da01d5ca1",
                    44_479),
            artifact(
                    "target_execution_evidence",
                    "docs/refactor/phase4c/"
                            + "personal-bank-user-counts-golden-target-execution-evidence.json",
                    "bb07875497bc51179a3d7023ca6abf485bd11559",
                    "947737b496168385b07db3d71a3bcf99d0940b1b52da4188ebf64516257b4002",
                    173_397),
            artifact(
                    "phase4b_golden",
                    "docs/refactor/phase4b/golden-personal-bank-user-counts-reads.json",
                    "6421851f917765549c8b4df2b50f5be505f7d87c",
                    "71f3be3e1ac821c7d3287ab2fbb19ce166828b0ca4da44716d540597eb380bd1",
                    1_200_690),
            artifact(
                    "historical_mapping",
                    "docs/refactor/phase4c/"
                            + "personal-bank-user-counts-golden-target-mapping-evidence.json",
                    "77a8dedfceaf14beeca2236e98092462a3be8eea",
                    "d039193c2ecfb644fdd356b196f6551440e63ee27eba0645d9f8e5bef923b4d3",
                    24_595),
            artifact(
                    "maven_runner",
                    "infra/phase2/verify-in-maven-container.sh",
                    "22f1479dbf9124d9ce95762f9fac4ddaebf3a8f6",
                    "2a9fa5d2e7b17f2f8d691b3d8e9e7e615e6c960c12c351525baae4251a56090e",
                    3_131),
            artifact(
                    "maven_project",
                    "server/pom.xml",
                    "ce9264784f7a9394d567458b7dba8a1648bdbc21",
                    "24b45d68c44c64a6b2fda2fbf6f342889640f7c3dbc088015703cd1a68ff916b",
                    9_582),
            artifact(
                    "maven_wrapper",
                    "server/.mvn/wrapper/maven-wrapper.properties",
                    "6b152042d1fd9f6218a72c60b449abbd3f149b2d",
                    "ec15e462d862b9ba5dc9d8cdf249576bfdad7c70ccd441d64117d9abcd808dab",
                    446));

    private Phase4cHttpTargetExecutionAnchorSuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Path contractPath = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_SHA256.equals(sha256(contractPath)),
                "target-execution anchor contract physical hash drifted");
        JsonNode contract = readJson(contractPath);
        validate(contract);
        validatePredecessor(root);
        validateManifest(root);
        validateWorm(root);
        return contract;
    }

    static void validate(JsonNode contract) {
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status", "scope",
                        "predecessor", "git_anchor", "external_anchor", "junit_manifest",
                        "worm_evidence", "authorization", "acceptance",
                        "document_payload_sha256")),
                "unexpected target-execution anchor top-level shape");
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString())
                        && CAPTURED_AT.equals(contract.path("captured_at").asString()),
                "target-execution anchor identity drifted");

        validatePredecessorReference(contract.path("predecessor"));
        validateGitAnchor(contract.path("git_anchor"));
        validateExternalAnchor(contract.path("external_anchor"));
        validateManifestReference(contract.path("junit_manifest"));
        validateWormReference(contract.path("worm_evidence"));
        validateBoundaries(contract.path("authorization"), contract.path("acceptance"));
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "target-execution anchor payload drifted");
    }

    static String anchoredSha256(String tiJavaRelativePath) {
        return ARTIFACTS.values().stream()
                .filter(artifact -> artifact.relative().equals(tiJavaRelativePath))
                .map(Artifact::sha256)
                .findFirst()
                .orElse(null);
    }

    static String anchoredBlobOid(String tiJavaRelativePath) {
        return ARTIFACTS.values().stream()
                .filter(artifact -> artifact.relative().equals(tiJavaRelativePath))
                .map(Artifact::blobOid)
                .findFirst()
                .orElse(null);
    }

    private static void validatePredecessorReference(JsonNode predecessor) {
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "trust_payload_sha256", "contract_id", "status", "scope",
                        "immutable")),
                "unexpected external-anchor predecessor shape");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_TRUST_SHA256.equals(
                        predecessor.path("trust_payload_sha256").asString())
                        && PREDECESSOR_ID.equals(predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString())
                        && predecessor.path("immutable").asBoolean(),
                "external-anchor predecessor reference drifted");
    }

    private static void validateGitAnchor(JsonNode anchor) {
        require(propertyNames(anchor).equals(Set.of(
                        "state", "object_format", "commit_oid", "root_tree_oid",
                        "parent_oid", "ti_java_subtree", "ti_java_tree_oid",
                        "authored_at", "committed_at", "subject", "remote_ref_at_capture",
                        "mutable_ref_is_not_validation_authority",
                        "artifact_paths_are_code_fixed", "artifacts")),
                "unexpected Git anchor shape");
        require("fixed_pushed_bootstrap_commit_objects_verified".equals(
                        anchor.path("state").asString())
                        && "sha1".equals(anchor.path("object_format").asString())
                        && COMMIT_OID.equals(anchor.path("commit_oid").asString())
                        && ROOT_TREE_OID.equals(anchor.path("root_tree_oid").asString())
                        && PARENT_OID.equals(anchor.path("parent_oid").asString())
                        && "Ti-Java".equals(anchor.path("ti_java_subtree").asString())
                        && TI_JAVA_TREE_OID.equals(anchor.path("ti_java_tree_oid").asString())
                        && COMMIT_TIMESTAMP.equals(anchor.path("authored_at").asString())
                        && COMMIT_TIMESTAMP.equals(anchor.path("committed_at").asString())
                        && COMMIT_SUBJECT.equals(anchor.path("subject").asString())
                        && "origin/main".equals(anchor.path("remote_ref_at_capture").asString())
                        && anchor.path("mutable_ref_is_not_validation_authority").asBoolean()
                        && anchor.path("artifact_paths_are_code_fixed").asBoolean(),
                "fixed Git anchor identity drifted");

        JsonNode artifacts = anchor.path("artifacts");
        require(propertyNames(artifacts).equals(ARTIFACTS.keySet()),
                "unexpected fixed Git artifact set");
        ARTIFACTS.forEach((name, expected) -> {
            JsonNode actual = artifacts.path(name);
            require(propertyNames(actual).equals(Set.of(
                            "ti_java_relative_path", "repository_path", "object_type",
                            "git_blob_oid", "sha256", "byte_count")),
                    "unexpected Git artifact shape: " + name);
            require(expected.relative().equals(
                            actual.path("ti_java_relative_path").asString())
                            && ("Ti-Java/" + expected.relative()).equals(
                            actual.path("repository_path").asString())
                            && "blob".equals(actual.path("object_type").asString())
                            && expected.blobOid().equals(
                            actual.path("git_blob_oid").asString())
                            && expected.sha256().equals(actual.path("sha256").asString())
                            && expected.byteCount() == actual.path("byte_count").asLong(),
                    "fixed Git artifact descriptor drifted: " + name);
        });
    }

    private static void validateExternalAnchor(JsonNode anchor) {
        require(propertyNames(anchor).equals(Set.of(
                        "state", "anchored_artifact_count", "anchored_artifact_keys",
                        "external_git_and_bridge_bytes_anchor_complete",
                        "predecessor_rewrite_forbidden",
                        "arbitrary_git_object_lookup_forbidden",
                        "dynamic_source_discovery_forbidden",
                        "current_anchor_bridge_self_authorization_forbidden")),
                "unexpected external anchor boundary shape");
        require("target_execution_bootstrap_contract_and_bridge_bytes_anchored".equals(
                        anchor.path("state").asString())
                        && anchor.path("anchored_artifact_count").asInt() == ARTIFACTS.size()
                        && strings(anchor.path("anchored_artifact_keys")).equals(
                        ARTIFACTS.keySet().stream().sorted().toList()),
                "external anchor artifact index drifted");
        for (String flag : List.of(
                "external_git_and_bridge_bytes_anchor_complete",
                "predecessor_rewrite_forbidden",
                "arbitrary_git_object_lookup_forbidden",
                "dynamic_source_discovery_forbidden",
                "current_anchor_bridge_self_authorization_forbidden")) {
            require(anchor.path(flag).asBoolean(),
                    "external anchor guard is open: " + flag);
        }
    }

    private static void validateManifestReference(JsonNode manifest) {
        require(propertyNames(manifest).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "leaf_payload_sha256", "raw_report_sha256",
                        "raw_report_byte_count", "tests", "passed", "failures", "errors",
                        "skipped", "flakes", "normalized_junit_manifest_bound",
                        "manifest_bytes_external_git_anchor_complete",
                        "post_push_successor_anchor_required",
                        "raw_report_not_tracked_or_embedded",
                        "independently_signed_provenance")),
                "unexpected normalized JUnit manifest reference shape");
        require(MANIFEST_RELATIVE.equals(manifest.path("source").asString())
                        && MANIFEST_SHA256.equals(manifest.path("sha256").asString())
                        && MANIFEST_PAYLOAD_SHA256.equals(
                        manifest.path("document_payload_sha256").asString())
                        && LEAF_PAYLOAD_SHA256.equals(
                        manifest.path("leaf_payload_sha256").asString())
                        && RAW_REPORT_SHA256.equals(
                        manifest.path("raw_report_sha256").asString())
                        && manifest.path("raw_report_byte_count").asInt() == 63_450
                        && manifest.path("tests").asInt() == 60
                        && manifest.path("passed").asInt() == 60
                        && manifest.path("failures").asInt() == 0
                        && manifest.path("errors").asInt() == 0
                        && manifest.path("skipped").asInt() == 0
                        && manifest.path("flakes").asInt() == 0
                        && manifest.path("normalized_junit_manifest_bound").asBoolean()
                        && !manifest.path(
                        "manifest_bytes_external_git_anchor_complete").asBoolean()
                        && manifest.path("post_push_successor_anchor_required").asBoolean()
                        && manifest.path("raw_report_not_tracked_or_embedded").asBoolean()
                        && !manifest.path("independently_signed_provenance").asBoolean(),
                "normalized JUnit manifest reference drifted");
    }

    private static void validateWormReference(JsonNode worm) {
        require(propertyNames(worm).equals(Set.of(
                        "source", "sha256", "fixed_chain_node_count",
                        "predecessor_sha256", "canonical_schema_dump_sha256",
                        "dockerfile_sha256", "java_build_context_sha256",
                        "phase2_fixed_acceptance_closed", "new_worm",
                        "new_worm_report_created", "production_build_context_unchanged",
                        "read_role_closed", "temporary_privilege",
                        "sensitive_information_scan_passed", "hibernate_schema_mode",
                        "production_schema_or_index_changed", "operator_migration_executed",
                        "real_data_migration_executed", "production_cutover")),
                "unexpected fifth WORM reference shape");
        require(WORM_RELATIVE.equals(worm.path("source").asString())
                        && WORM_SHA256.equals(worm.path("sha256").asString())
                        && worm.path("fixed_chain_node_count").asInt() == 5
                        && WORM_PREDECESSOR_SHA256.equals(
                        worm.path("predecessor_sha256").asString())
                        && CANONICAL_SCHEMA_SHA256.equals(
                        worm.path("canonical_schema_dump_sha256").asString())
                        && DOCKERFILE_SHA256.equals(
                        worm.path("dockerfile_sha256").asString())
                        && BUILD_CONTEXT_SHA256.equals(
                        worm.path("java_build_context_sha256").asString())
                        && worm.path("phase2_fixed_acceptance_closed").asBoolean()
                        && !worm.path("new_worm").asBoolean()
                        && !worm.path("new_worm_report_created").asBoolean()
                        && worm.path("production_build_context_unchanged").asBoolean()
                        && worm.path("read_role_closed").asBoolean()
                        && !worm.path("temporary_privilege").asBoolean()
                        && worm.path("sensitive_information_scan_passed").asBoolean()
                        && "validate".equals(worm.path("hibernate_schema_mode").asString())
                        && !worm.path("production_schema_or_index_changed").asBoolean()
                        && !worm.path("operator_migration_executed").asBoolean()
                        && !worm.path("real_data_migration_executed").asBoolean()
                        && !worm.path("production_cutover").asBoolean(),
                "fifth WORM reference drifted");
    }

    private static void validateBoundaries(JsonNode authorization, JsonNode acceptance) {
        Set<String> authorizationKeys = Set.of(
                "external_git_and_bridge_bytes_anchor_complete",
                "normalized_junit_manifest_bound", "junit_manifest_tests_passed",
                "typed_parity_review_complete", "full_target_parity_closed",
                "route_migration_eligible", "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated", "production_schema_or_index",
                "operator_migration_implementation", "real_data_migration_execution",
                "migration_global_preflight_closed", "client_change",
                "gateway_or_proxy_change", "production_cutover",
                "junit_manifest_bytes_external_git_anchor_complete",
                "post_push_junit_manifest_successor_anchor_required");
        require(propertyNames(authorization).equals(authorizationKeys),
                "unexpected external-anchor authorization shape");
        for (String flag : Set.of(
                "external_git_and_bridge_bytes_anchor_complete",
                "normalized_junit_manifest_bound", "junit_manifest_tests_passed",
                "post_push_junit_manifest_successor_anchor_required")) {
            require(authorization.path(flag).asBoolean(),
                    "external-anchor authorization is unexpectedly closed: " + flag);
        }
        for (String flag : authorizationKeys) {
            if (!Set.of(
                    "external_git_and_bridge_bytes_anchor_complete",
                    "normalized_junit_manifest_bound",
                    "junit_manifest_tests_passed",
                    "post_push_junit_manifest_successor_anchor_required").contains(flag)) {
                require(!authorization.path(flag).asBoolean(),
                        "external-anchor authorization overclaims: " + flag);
            }
        }

        require(propertyNames(acceptance).equals(Set.of(
                        "external_git_and_bridge_bytes_anchor_complete",
                        "normalized_junit_manifest_bound", "junit_manifest_tests",
                        "junit_manifest_passed", "typed_parity_review_complete",
                        "junit_manifest_bytes_external_git_anchor_complete",
                        "post_push_junit_manifest_successor_anchor_required",
                        "full_target_parity_closed", "route_migration_eligible",
                        "implemented_pending_get_count", "migrated_operation_count",
                        "pending_operation_count", "production_cutover_operation_count",
                        "production_cutover", "new_worm",
                        "production_build_context_unchanged",
                        "operator_and_real_migration_remain_blocked", "next_gate")),
                "unexpected external-anchor acceptance shape");
        require(acceptance.path("external_git_and_bridge_bytes_anchor_complete").asBoolean()
                        && acceptance.path("normalized_junit_manifest_bound").asBoolean()
                        && acceptance.path("junit_manifest_tests").asInt() == 60
                        && acceptance.path("junit_manifest_passed").asInt() == 60
                        && !acceptance.path(
                        "junit_manifest_bytes_external_git_anchor_complete").asBoolean()
                        && acceptance.path(
                        "post_push_junit_manifest_successor_anchor_required").asBoolean()
                        && !acceptance.path("typed_parity_review_complete").asBoolean()
                        && !acceptance.path("full_target_parity_closed").asBoolean()
                        && !acceptance.path("route_migration_eligible").asBoolean()
                        && acceptance.path("implemented_pending_get_count").asInt() == 2
                        && acceptance.path("migrated_operation_count").asInt() == 11
                        && acceptance.path("pending_operation_count").asInt() == 600
                        && acceptance.path("production_cutover_operation_count").asInt() == 0
                        && !acceptance.path("production_cutover").asBoolean()
                        && !acceptance.path("new_worm").asBoolean()
                        && acceptance.path("production_build_context_unchanged").asBoolean()
                        && acceptance.path(
                        "operator_and_real_migration_remain_blocked").asBoolean()
                        && NEXT_GATE.equals(acceptance.path("next_gate").asString()),
                "external-anchor acceptance boundary drifted");
    }

    private static void validatePredecessor(Path root) throws IOException {
        Path path = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(PREDECESSOR_SHA256.equals(sha256(path)),
                "physical target-execution predecessor drifted");
        JsonNode predecessor = readJson(path);
        require(PREDECESSOR_ID.equals(predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString()),
                "physical target-execution predecessor identity drifted");
        require(PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(payloadSha256(predecessor)),
                "physical target-execution predecessor payload drifted");
        require(PREDECESSOR_TRUST_SHA256.equals(predecessorTrustSha256(predecessor)),
                "physical target-execution predecessor trust payload drifted");
    }

    private static void validateManifest(Path root) throws IOException {
        Path path = fixedRegularFile(root, MANIFEST_RELATIVE);
        require(MANIFEST_SHA256.equals(sha256(path)),
                "physical normalized JUnit manifest drifted");
        JsonNode manifest = readJson(path);
        require(propertyNames(manifest).equals(Set.of(
                        "schema_version", "artifact_id", "status", "scope", "source_anchor",
                        "source_inputs", "runner", "raw_report", "normalization_policy",
                        "result", "confidentiality", "document_payload_sha256")),
                "unexpected normalized JUnit manifest shape");
        require(manifest.path("schema_version").asInt() == 1
                        && "ti.phase4c.personal-bank-user-counts-target-execution-junit-manifest"
                        .equals(manifest.path("artifact_id").asString())
                        && "passed_normalized_sensitive_runtime_output_removed".equals(
                        manifest.path("status").asString())
                        && "phase4c-personal-bank-user-counts-target-execution-junit".equals(
                        manifest.path("scope").asString()),
                "normalized JUnit manifest identity drifted");

        JsonNode sourceAnchor = manifest.path("source_anchor");
        require(COMMIT_OID.equals(sourceAnchor.path("git_commit_sha1").asString())
                        && PARENT_OID.equals(sourceAnchor.path("git_parent_sha1").asString())
                        && ROOT_TREE_OID.equals(
                        sourceAnchor.path("git_root_tree_sha1").asString())
                        && TI_JAVA_TREE_OID.equals(
                        sourceAnchor.path("ti_java_tree_sha1").asString())
                        && sourceAnchor.path("commit_was_pushed_before_capture").asBoolean()
                        && sourceAnchor.path("head_equaled_origin_main_at_capture").asBoolean()
                        && sourceAnchor.path("ti_java_tracked_clean_at_capture").asBoolean()
                        && sourceAnchor.path("ti_java_untracked_file_count_at_capture").asInt()
                        == 0
                        && sourceAnchor.path("capture_state_is_declared_metadata").asBoolean()
                        && sourceAnchor.path(
                        "normalizer_does_not_revalidate_mutable_remote_ref").asBoolean(),
                "normalized JUnit source anchor drifted");

        JsonNode inputs = manifest.path("source_inputs");
        require(propertyNames(inputs).equals(ARTIFACTS.keySet()),
                "normalized JUnit source-input set drifted");
        ARTIFACTS.forEach((name, descriptor) -> {
            JsonNode input = inputs.path(name);
            require(descriptor.relative().equals(input.path("path").asString())
                            && descriptor.sha256().equals(input.path("sha256").asString()),
                    "normalized JUnit source-input drifted: " + name);
        });

        JsonNode runner = manifest.path("runner");
        require(TEST_CLASS.equals(runner.path("test_class").asString())
                        && "maven-failsafe-junit-xml".equals(
                        runner.path("report_format").asString())
                        && "3.0.2".equals(runner.path("report_schema_version").asString()),
                "normalized JUnit runner drifted");
        require("single_execution_binding_not_cross_run_stability".equals(
                        manifest.path("normalization_policy")
                                .path("raw_report_hash_role").asString()),
                "normalized JUnit raw-hash claim boundary drifted");
        JsonNode raw = manifest.path("raw_report");
        require(RAW_REPORT_SHA256.equals(raw.path("sha256").asString())
                        && raw.path("byte_count").asInt() == 63_450
                        && !raw.path("tracked").asBoolean()
                        && !raw.path("committed").asBoolean()
                        && !raw.path("content_embedded").asBoolean(),
                "normalized raw JUnit report boundary drifted");

        JsonNode result = manifest.path("result");
        JsonNode totals = result.path("totals");
        require(totals.path("tests").asInt() == 60
                        && totals.path("passed").asInt() == 60
                        && totals.path("failures").asInt() == 0
                        && totals.path("errors").asInt() == 0
                        && totals.path("skipped").asInt() == 0
                        && totals.path("flakes").asInt() == 0,
                "normalized JUnit totals drifted");
        JsonNode leaves = result.path("leaves");
        require(leaves.isArray() && leaves.size() == 60
                        && LEAF_PAYLOAD_SHA256.equals(canonicalSha256(leaves))
                        && LEAF_PAYLOAD_SHA256.equals(
                        result.path("leaf_payload_sha256").asString()),
                "normalized JUnit leaf payload drifted");
        for (int index = 0; index < leaves.size(); index++) {
            require(leaves.path(index).path("ordinal").asInt() == index + 1
                            && "passed".equals(
                            leaves.path(index).path("outcome").asString()),
                    "normalized JUnit leaf order/outcome drifted");
        }

        JsonNode confidentiality = manifest.path("confidentiality");
        for (String flag : List.of(
                "properties_removed", "stdout_removed", "stderr_removed",
                "timings_removed", "absolute_paths_removed",
                "credentials_tokens_cookies_and_urls_removed",
                "sensitive_output_scan_passed",
                "post_push_successor_anchor_required")) {
            require(confidentiality.path(flag).asBoolean(),
                    "normalized JUnit confidentiality guard is open: " + flag);
        }
        require(!confidentiality.path("repository_tamper_evident").asBoolean()
                        && !confidentiality.path(
                        "manifest_bytes_external_git_anchor_complete").asBoolean(),
                "normalized JUnit manifest overclaims its own Git anchor");
        require(!confidentiality.path("independently_signed_provenance").asBoolean(),
                "normalized JUnit manifest overclaims signed provenance");
        require(MANIFEST_PAYLOAD_SHA256.equals(
                        manifest.path("document_payload_sha256").asString())
                        && MANIFEST_PAYLOAD_SHA256.equals(payloadSha256(manifest)),
                "normalized JUnit document payload drifted");
    }

    private static void validateWorm(Path root) throws IOException {
        Path path = fixedRegularFile(root, WORM_RELATIVE);
        require(WORM_SHA256.equals(sha256(path)), "physical fifth WORM drifted");
        JsonNode worm = readJson(path);
        require(worm.path("schemaVersion").asInt() == 1
                        && "18.4".equals(worm.path("source").path("serverVersion").asString())
                        && "18.4".equals(worm.path("restore").path("serverVersion").asString())
                        && CANONICAL_SCHEMA_SHA256.equals(worm.path("restore")
                        .path("canonicalSchemaDumpSha256").asString())
                        && !worm.path("restore").path("schemaDumpPersisted").asBoolean(),
                "fifth WORM schema evidence drifted");
        JsonNode readRole = worm.path("readRole");
        for (String flag : List.of(
                "selectPassed", "defaultTransactionReadOnly",
                "aclVerifiedWithReadOnlyDefaultDisabled", "insertRejected",
                "updateRejected", "deleteRejected", "ddlRejected",
                "temporaryDdlRejected")) {
            require(readRole.path(flag).asBoolean(),
                    "fifth WORM read-role guard is open: " + flag);
        }
        require(!readRole.path("temporaryPrivilege").asBoolean(),
                "fifth WORM unexpectedly permits TEMP");
        JsonNode java = worm.path("java");
        require(DOCKERFILE_SHA256.equals(java.path("dockerfileSha256").asString())
                        && BUILD_CONTEXT_SHA256.equals(
                        java.path("buildContextSha256").asString())
                        && "validate".equals(java.path("hibernateDdlAuto").asString())
                        && java.path("startupPassed").asBoolean()
                        && java.path("readinessPassed").asBoolean()
                        && !worm.path("flywayBaselineCreated").asBoolean(),
                "fifth WORM Java boundary drifted");
    }

    private static String predecessorTrustSha256(JsonNode predecessor) {
        ObjectNode payload = (ObjectNode) predecessor.deepCopy();
        payload.remove("document_payload_sha256");
        ObjectNode sources = (ObjectNode) payload.path("source_contracts");
        for (String bridge : List.of("python_successor_bridge", "java_successor_bridge")) {
            JsonNode candidate = sources.path(bridge);
            require(candidate.isObject(),
                    "target-execution predecessor bridge reference is missing: " + bridge);
            ObjectNode reference = (ObjectNode) candidate;
            reference.put("sha256", BRIDGE_SENTINEL);
        }
        return canonicalSha256(payload);
    }

    private static String payloadSha256(JsonNode document) {
        ObjectNode payload = (ObjectNode) document.deepCopy();
        payload.remove("document_payload_sha256");
        return canonicalSha256(payload);
    }

    private static String canonicalSha256(JsonNode value) {
        return sha256(JSON.writeValueAsBytes(canonicalNode(value)));
    }

    private static JsonNode canonicalNode(JsonNode node) {
        if (node.isObject()) {
            ObjectNode result = JSON.createObjectNode();
            TreeMap<String, JsonNode> sorted = new TreeMap<>();
            node.properties().forEach(entry -> sorted.put(entry.getKey(), entry.getValue()));
            sorted.forEach((key, value) -> result.set(key, canonicalNode(value)));
            return result;
        }
        if (node.isArray()) {
            ArrayNode result = JSON.createArrayNode();
            node.forEach(item -> result.add(canonicalNode(item)));
            return result;
        }
        return node.deepCopy();
    }

    private static JsonNode readJson(Path path) throws IOException {
        return JSON.readTree(Files.readString(path, StandardCharsets.UTF_8));
    }

    private static Path fixedRegularFile(Path root, String relative) throws IOException {
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute() && !candidate.normalize().startsWith(".."),
                "fixed external-anchor path escaped Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : candidate) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed external-anchor path contains a symlink: " + relative);
        }
        Path resolved = root.resolve(candidate).toRealPath();
        require(resolved.startsWith(root) && Files.isRegularFile(resolved),
                "fixed external-anchor path is not a regular Ti-Java file: " + relative);
        return resolved;
    }

    private static Set<String> propertyNames(JsonNode node) {
        Set<String> names = new LinkedHashSet<>();
        node.properties().forEach(entry -> names.add(entry.getKey()));
        return Set.copyOf(names);
    }

    private static List<String> strings(JsonNode array) {
        List<String> values = new ArrayList<>();
        array.forEach(value -> values.add(value.asString()));
        return List.copyOf(values);
    }

    private static Map.Entry<String, Artifact> artifact(
            String name,
            String relative,
            String blobOid,
            String sha256,
            long byteCount
    ) {
        return Map.entry(name, new Artifact(relative, blobOid, sha256, byteCount));
    }

    private static String sha256(Path path) throws IOException {
        return sha256(Files.readAllBytes(path));
    }

    private static String sha256(byte[] payload) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 unavailable", exception);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private record Artifact(
            String relative,
            String blobOid,
            String sha256,
            long byteCount
    ) {
    }
}
