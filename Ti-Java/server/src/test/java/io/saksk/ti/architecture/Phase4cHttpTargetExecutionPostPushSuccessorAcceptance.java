package io.saksk.ti.architecture;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
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

/** Gitless Java mirror for the fixed Phase 4C target-execution post-push handoff. */
final class Phase4cHttpTargetExecutionPostPushSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-contract.json";
    private static final String CONTRACT_SHA256 =
            "3d7208eb2f70b9eb2b559e15acb4cc7882dacecf8cad941f2978678f93b12628";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "c2382550719d97e74f93db97bf74e70e246cca1e35ac6cc9c6c9e8d13b964dba";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-post-push-contract";
    private static final String CONTRACT_STATUS =
            "target_execution_anchor_checkpoint_externally_anchored_"
                    + "typed_parity_pending_routes_pending";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution-post-push";
    private static final String CAPTURED_AT = "2026-07-18T13:10:47+08:00";
    private static final String NEXT_GATE =
            "typed_parity_real_tomcat_complete_response_headers_redis_refusal_"
                    + "interruption_same_instance_recovery_and_pg16_pg18_termination_identity_"
                    + "sql_nine_table_fingerprints_before_route_migration";

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-anchor-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "f966f9229949a37811da2402d3baf05dd78643ec4104a8f921dee10188bcd203";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "dbfe37e3e0d9b80ebb378a58b58aa7b15371d737b389f06f24f3018adb6b311e";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-anchor-contract";
    private static final String PREDECESSOR_STATUS =
            "target_execution_bootstrap_externally_anchored_"
                    + "normalized_junit_manifest_bootstrap_bound_routes_pending";
    private static final String PREDECESSOR_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution-external-anchor";
    private static final String PREDECESSOR_CAPTURED_AT = "2026-07-18T12:14:52+08:00";

    private static final String COMMIT_OID =
            "6c1b03dd7fa9cde7a6dcdbf6b555452e9a6d9e53";
    private static final String ROOT_TREE_OID =
            "47a1df74676ff2838bec7d01f371787720aea559";
    private static final String PARENT_OID =
            "0531b3c9272f9743a374edcf5c8bbeb72643eb1b";
    private static final String TI_JAVA_TREE_OID =
            "7c0e65fa52ffa95567b0d7e266bd4e590af22f5a";
    private static final String COMMIT_TIMESTAMP = "2026-07-18T13:10:47+08:00";
    private static final String COMMIT_SUBJECT =
            "test(java): anchor user counts target execution";

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

    private static final Map<String, CheckpointArtifact> CHECKPOINT_ARTIFACTS =
            Map.ofEntries(
                    checkpointArtifact(
                            "anchor_builder",
                            "tools/build_phase4c_personal_bank_user_counts_http_"
                                    + "target_execution_anchor_contract.py",
                            "b3af05cc0a086122e4dd9b0a61f0389bcbe880c3",
                            "b87133b5c187561970c322a92eb22f84cb7a768a9168870cc7517dd973616667",
                            34_518),
                    checkpointArtifact(
                            "anchor_contract",
                            PREDECESSOR_RELATIVE,
                            "75a25eacdea16cc2d3349eadad24b1370a9ae4bd",
                            PREDECESSOR_SHA256,
                            10_974),
                    checkpointArtifact(
                            "java_anchor_acceptance",
                            "server/src/test/java/io/saksk/ti/architecture/"
                                    + "Phase4cHttpTargetExecutionAnchorSuccessorAcceptance.java",
                            "4434b28df67afdd682d09e7c091c2007a34a0187",
                            "1e2bd94c5e13389375cee448615149d8409cc311ca97e2fc78ebcafa33cd1030",
                            41_210),
                    checkpointArtifact(
                            "java_anchor_parity_test",
                            "server/src/test/java/io/saksk/ti/architecture/"
                                    + "Phase4cPersonalBankUserCountsHttpTargetExecution"
                                    + "AnchorContractParityTest.java",
                            "ac82ead5ba1bce096bcbfa363f1500a447981755",
                            "9b4e885f8c3727081c0cfcd6cd5901f1bf7a1f9059c81e9badd1273133a4676c",
                            12_996),
                    checkpointArtifact(
                            "junit_manifest",
                            MANIFEST_RELATIVE,
                            "da3cef8743dbf436b4d631f081b706c705961bdd",
                            MANIFEST_SHA256,
                            33_246),
                    checkpointArtifact(
                            "junit_normalizer",
                            "tools/normalize_phase4c_personal_bank_user_counts_"
                                    + "target_execution_junit.py",
                            "470c36c6b18b3573ac4e3aecb6443a1fb5290349",
                            "f6d90113c69d9c1bef2e3d53f839539a481bbcd674c7b598b2fb4aff88a3879a",
                            27_174),
                    checkpointArtifact(
                            "junit_normalizer_test",
                            "tools/test_normalize_phase4c_personal_bank_user_counts_"
                                    + "target_execution_junit.py",
                            "5e36f76fdca87d1f5fc83e2a1cab1dc3285cb684",
                            "f2397e35c76f063f356edfb9f2491f17157cfaa07cfbc0d3a39a28b4e2957d5d",
                            12_068),
                    checkpointArtifact(
                            "python_anchor_acceptance",
                            "tools/phase4c_http_target_execution_anchor_successor_acceptance.py",
                            "14cfc16aad7fbae8df09a46c846d890a43663587",
                            "03b411be87bd9f8d4dbb94ddcfb9495ec7523fb5c9482f3c1fb4098d1ab7e455",
                            34_568),
                    checkpointArtifact(
                            "python_anchor_contract_test",
                            "tools/test_phase4c_personal_bank_user_counts_http_"
                                    + "target_execution_anchor_contract.py",
                            "78ba394d3a5b9b833e5496d685a31f5375280bb0",
                            "3306aed29941fd9703f36443f43bbb65646b48bed1f6f848d6109683057769e5",
                            15_921));

    private static final Map<String, SuccessorSource> SUCCESSOR_SOURCES = Map.ofEntries(
            successorSource(
                    "README.md",
                    "550bc40705fea9b603a3936de9de366ba49849ef",
                    "321d23e47d0df0714ea632b2c8c1d3d05d0e67bf69d53e3a52e387e4a949bda4",
                    37_209,
                    "9c7608803dff193b898d14d13de92095ef001dfeb6099fde2a2ba546d4cd867c",
                    37_695,
                    "100644"),
            successorSource(
                    "docs/refactor/05-progress.md",
                    "1bcad604184f31cf24a0047bd248d457dda47402",
                    "e2363a603e9b82368185b6fef3e9882a3e586ce5b5eca14a8b5cddcbca7d6faf",
                    98_860,
                    "9ac3b2edaff690f105326aed3c7a87d4049b7f89a1af541038c8f0b032bf79ec",
                    100_798,
                    "100644"),
            successorSource(
                    "docs/refactor/phase4c/README.md",
                    "aa989184d7f0c4dea4fb66284346937269891fe2",
                    "f43ae7ca31038fcc45a05874cfc5c8a460edfe2833936bf4418f37706771d472",
                    13_854,
                    "649ad38f868840edf8ca16ce35156dd18ea7336da9869433bdaa0db2f604fec2",
                    15_137,
                    "100644"),
            successorSource(
                    "infra/phase2/README.md",
                    "99a264aa12e44ddf34bda25156877890143d75a3",
                    "55f9d05fa583e581d6a5b92ec4f1e3e53690a40b5087da456a84ef996b4d3f7b",
                    6_378,
                    "4a5205e57bad5f54b60fd8ad1f21b8f32f5282bb4938a0244ea9f0977c34157e",
                    6_748,
                    "100644"),
            successorSource(
                    "infra/phase2/verify-static.sh",
                    "c5e3d49701c6e2fa11676fe46b545cc87039b003",
                    "eb01988f26a56293338a7bcd8bc83487b2d8cd0c1c081ae75272bc73dfa28a94",
                    13_155,
                    "357cd003b068997cbcb4ed194f785d3a1d1f310871ad1994c5102bcb1839f54d",
                    13_541,
                    "100755"),
            successorSource(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
                    "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6",
                    "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15",
                    88_021,
                    "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578",
                    89_014,
                    "100644"),
            successorSource(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py",
                    "9cac3b5c6a3ecd0b98b71122864b5d706007645f",
                    "51d3c9bf425319e7a0cd7a49e7244f058e09f14ac363f9278000192cb4a69d3b",
                    59_991,
                    "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209",
                    61_952,
                    "100644"),
            successorSource(
                    "tools/phase2_wormhole_successor_acceptance.py",
                    "1ccfbe8c3b4837165f83bd8f2a85c5bb4c259cd7",
                    "f3a56bd684b508f69bc387d741f1c0277d0c4a7f4130aec984fd359fa8dc0f3a",
                    21_178,
                    "b1eabe5dc758e8ff0c2b0d25f7a4878e7a38a4491db7ea3bffbe04018c579464",
                    23_319,
                    "100644"),
            successorSource(
                    "tools/phase4c_http_target_execution_successor_acceptance.py",
                    "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84",
                    "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c",
                    78_481,
                    "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a",
                    81_902,
                    "100644"),
            successorSource(
                    "tools/test_phase2_wormhole_successor_acceptance.py",
                    "29f5fed3124d2b76178befed2e53276e3fa6ad75",
                    "ce70d5f35c7725d0f93f27619c5828f294ac259fc20f8594a3ac71b5f5f6f72d",
                    19_647,
                    "fae248af8e5b5e61634ac10bb8824d5437fd08c4d168c49faadff3e6983c1b9e",
                    29_314,
                    "100644"));

    private static final Set<String> CURRENT_POST_PUSH_SOURCES = Set.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPush"
                    + "ContractParityTest.java",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py");

    private Phase4cHttpTargetExecutionPostPushSuccessorAcceptance() {
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Path contractPath = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_SHA256.equals(sha256(contractPath)),
                "post-push contract physical SHA-256 drifted");
        JsonNode contract = readJson(contractPath);
        validate(contract, root);
        return contract;
    }

    static void validate(JsonNode contract, Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status", "scope",
                        "predecessor", "git_checkpoint", "checkpoint_anchor",
                        "historical_source_successors", "junit_execution", "worm_evidence",
                        "authorization", "acceptance", "document_payload_sha256")),
                "unexpected post-push contract top-level shape");
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString())
                        && CAPTURED_AT.equals(contract.path("captured_at").asString()),
                "post-push contract identity drifted");
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "post-push contract payload drifted");

        validatePredecessorReference(contract.path("predecessor"));
        validateCheckpoint(contract.path("git_checkpoint"));
        validateCheckpointAnchor(contract.path("checkpoint_anchor"));
        validateHistoricalSuccessors(contract.path("historical_source_successors"));
        validateJunitReference(contract.path("junit_execution"));
        validateWormReference(contract.path("worm_evidence"));
        validateAuthorization(contract.path("authorization"));
        validateAcceptance(contract.path("acceptance"));
        validateLocalFiles(root);
    }

    static String acceptedHash(String relative) {
        SuccessorSource source = SUCCESSOR_SOURCES.get(relative);
        return source == null ? null : source.acceptedSha256();
    }

    static String successorHash(Path tiJavaRoot, String relative) throws IOException {
        SuccessorSource source = SUCCESSOR_SOURCES.get(relative);
        if (source == null) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = load(root);
        validateOverride(
                relative,
                source,
                contract.path("historical_source_successors")
                        .path("overrides").path(relative));
        Path path = fixedRegularFile(root, relative);
        String physical = sha256(path);
        if (source.successorSha256().equals(physical)) {
            require(Files.size(path) == source.successorByteCount(),
                    "post-push successor physical byte count drifted: " + relative);
            return physical;
        }
        return currentOrPostPushAnchorOrTagPreflightSuccessor(
                root,
                relative,
                source.successorSha256(),
                physical,
                "successor");
    }

    private static void validatePredecessorReference(JsonNode predecessor) {
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "document_payload_sha256", "contract_id",
                        "status", "scope", "captured_at", "immutable")),
                "unexpected post-push predecessor shape");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_ID.equals(predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString())
                        && PREDECESSOR_CAPTURED_AT.equals(
                        predecessor.path("captured_at").asString())
                        && predecessor.path("immutable").asBoolean(),
                "post-push predecessor reference drifted");
    }

    private static void validateCheckpoint(JsonNode checkpoint) {
        require(propertyNames(checkpoint).equals(Set.of(
                        "object_format", "commit_oid", "root_tree_oid", "parent_oid",
                        "ti_java_tree_oid", "authored_at", "committed_at", "subject",
                        "capture_ref_metadata", "capture_ref_is_validation_authority",
                        "diff", "artifacts")),
                "unexpected post-push Git checkpoint shape");
        require("sha1".equals(checkpoint.path("object_format").asString())
                        && COMMIT_OID.equals(checkpoint.path("commit_oid").asString())
                        && ROOT_TREE_OID.equals(checkpoint.path("root_tree_oid").asString())
                        && PARENT_OID.equals(checkpoint.path("parent_oid").asString())
                        && TI_JAVA_TREE_OID.equals(
                        checkpoint.path("ti_java_tree_oid").asString())
                        && COMMIT_TIMESTAMP.equals(checkpoint.path("authored_at").asString())
                        && COMMIT_TIMESTAMP.equals(checkpoint.path("committed_at").asString())
                        && COMMIT_SUBJECT.equals(checkpoint.path("subject").asString())
                        && "origin/main".equals(
                        checkpoint.path("capture_ref_metadata").asString())
                        && !checkpoint.path(
                        "capture_ref_is_validation_authority").asBoolean(),
                "post-push Git checkpoint identity drifted");

        JsonNode diff = checkpoint.path("diff");
        require(propertyNames(diff).equals(Set.of(
                        "added_count", "modified_count", "deleted_count",
                        "non_ti_java_count", "added_total_bytes", "exact_add_only_delta"))
                        && diff.path("added_count").asInt() == 9
                        && diff.path("modified_count").asInt() == 0
                        && diff.path("deleted_count").asInt() == 0
                        && diff.path("non_ti_java_count").asInt() == 0
                        && diff.path("added_total_bytes").asLong() == 222_675
                        && diff.path("exact_add_only_delta").asBoolean(),
                "post-push Git checkpoint delta drifted");

        JsonNode artifacts = checkpoint.path("artifacts");
        require(propertyNames(artifacts).equals(CHECKPOINT_ARTIFACTS.keySet())
                        && CHECKPOINT_ARTIFACTS.size() == 9
                        && CHECKPOINT_ARTIFACTS.values().stream()
                        .mapToLong(CheckpointArtifact::byteCount).sum() == 222_675,
                "unexpected post-push checkpoint artifact set");
        CHECKPOINT_ARTIFACTS.forEach((name, expected) -> {
            JsonNode actual = artifacts.path(name);
            require(propertyNames(actual).equals(Set.of(
                            "ti_java_relative_path", "repository_path", "object_type",
                            "git_blob_oid", "sha256", "byte_count", "mode")),
                    "unexpected post-push checkpoint artifact shape: " + name);
            require(expected.relative().equals(
                            actual.path("ti_java_relative_path").asString())
                            && ("Ti-Java/" + expected.relative()).equals(
                            actual.path("repository_path").asString())
                            && "blob".equals(actual.path("object_type").asString())
                            && expected.blobOid().equals(
                            actual.path("git_blob_oid").asString())
                            && expected.sha256().equals(actual.path("sha256").asString())
                            && expected.byteCount() == actual.path("byte_count").asLong()
                            && expected.mode().equals(actual.path("mode").asString()),
                    "post-push checkpoint artifact descriptor drifted: " + name);
        });
    }

    private static void validateCheckpointAnchor(JsonNode anchor) {
        require(propertyNames(anchor).equals(Set.of(
                        "whole_commit_object_fixed",
                        "root_tree_parent_and_ti_java_subtree_fixed",
                        "exact_nine_artifact_blobs_fixed",
                        "normalized_junit_manifest_blob_external_git_anchor_complete",
                        "anchor_contract_builder_acceptances_and_tests_"
                                + "external_git_anchor_complete",
                        "historical_manifest_false_claim_preserved",
                        "current_post_push_contract_and_validator_bytes_excluded",
                        "origin_ref_is_metadata_not_authority",
                        "independently_signed_provenance", "tamper_evident_scope")),
                "unexpected post-push checkpoint anchor shape");
        for (String flag : Set.of(
                "whole_commit_object_fixed",
                "root_tree_parent_and_ti_java_subtree_fixed",
                "exact_nine_artifact_blobs_fixed",
                "normalized_junit_manifest_blob_external_git_anchor_complete",
                "anchor_contract_builder_acceptances_and_tests_external_git_anchor_complete",
                "historical_manifest_false_claim_preserved",
                "current_post_push_contract_and_validator_bytes_excluded",
                "origin_ref_is_metadata_not_authority")) {
            require(anchor.path(flag).asBoolean(),
                    "post-push checkpoint anchor guard is open: " + flag);
        }
        require(!anchor.path("independently_signed_provenance").asBoolean()
                        && "fixed_git_commit_tree_and_explicit_blobs".equals(
                        anchor.path("tamper_evident_scope").asString()),
                "post-push checkpoint anchor boundary drifted");
    }

    private static void validateHistoricalSuccessors(JsonNode history) {
        require(propertyNames(history).equals(Set.of(
                        "accepted_checkpoint_commit_oid", "successor_allowlist",
                        "successor_allowlist_exact", "arbitrary_source_lookup_forbidden",
                        "accepted_hashes_from_fixed_git_blobs", "overrides",
                        "current_post_push_sources",
                        "current_post_push_sources_excluded_from_self_authority",
                        "current_successor_bytes_external_git_anchor_complete")),
                "unexpected post-push historical successor shape");
        require(COMMIT_OID.equals(
                        history.path("accepted_checkpoint_commit_oid").asString())
                        && strings(history.path("successor_allowlist")).equals(
                        SUCCESSOR_SOURCES.keySet().stream().sorted().toList())
                        && history.path("successor_allowlist_exact").asBoolean()
                        && history.path("arbitrary_source_lookup_forbidden").asBoolean()
                        && history.path("accepted_hashes_from_fixed_git_blobs").asBoolean()
                        && strings(history.path("current_post_push_sources")).equals(
                        CURRENT_POST_PUSH_SOURCES.stream().sorted().toList())
                        && history.path(
                        "current_post_push_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !history.path(
                        "current_successor_bytes_external_git_anchor_complete")
                        .asBoolean(),
                "post-push historical successor boundary drifted");
        JsonNode overrides = history.path("overrides");
        require(propertyNames(overrides).equals(SUCCESSOR_SOURCES.keySet())
                        && SUCCESSOR_SOURCES.size() == 10,
                "unexpected post-push successor override set");
        SUCCESSOR_SOURCES.forEach((relative, expected) ->
                validateOverride(relative, expected, overrides.path(relative)));
    }

    private static void validateOverride(
            String relative,
            SuccessorSource expected,
            JsonNode actual
    ) {
        require(propertyNames(actual).equals(Set.of(
                        "source", "accepted_git_commit_oid", "accepted_git_blob_oid",
                        "accepted_sha256", "accepted_byte_count", "successor_sha256",
                        "successor_byte_count", "mode")),
                "unexpected post-push successor override shape: " + relative);
        require(relative.equals(actual.path("source").asString())
                        && COMMIT_OID.equals(
                        actual.path("accepted_git_commit_oid").asString())
                        && expected.acceptedBlobOid().equals(
                        actual.path("accepted_git_blob_oid").asString())
                        && expected.acceptedSha256().equals(
                        actual.path("accepted_sha256").asString())
                        && expected.acceptedByteCount()
                        == actual.path("accepted_byte_count").asLong()
                        && expected.successorSha256().equals(
                        actual.path("successor_sha256").asString())
                        && expected.successorByteCount()
                        == actual.path("successor_byte_count").asLong()
                        && expected.mode().equals(actual.path("mode").asString()),
                "post-push successor override drifted: " + relative);
    }

    private static void validateJunitReference(JsonNode junit) {
        require(propertyNames(junit).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "leaf_payload_sha256", "raw_report_sha256",
                        "raw_report_byte_count", "case_leaf_count",
                        "supplementary_leaf_count", "total_leaf_count", "failures",
                        "errors", "skipped", "manifest_blob_external_git_anchor_complete",
                        "historical_manifest_document_rewritten")),
                "unexpected post-push JUnit execution shape");
        require(MANIFEST_RELATIVE.equals(junit.path("source").asString())
                        && MANIFEST_SHA256.equals(junit.path("sha256").asString())
                        && MANIFEST_PAYLOAD_SHA256.equals(
                        junit.path("document_payload_sha256").asString())
                        && LEAF_PAYLOAD_SHA256.equals(
                        junit.path("leaf_payload_sha256").asString())
                        && RAW_REPORT_SHA256.equals(
                        junit.path("raw_report_sha256").asString())
                        && junit.path("raw_report_byte_count").asInt() == 63_450
                        && junit.path("case_leaf_count").asInt() == 59
                        && junit.path("supplementary_leaf_count").asInt() == 1
                        && junit.path("total_leaf_count").asInt() == 60
                        && junit.path("failures").asInt() == 0
                        && junit.path("errors").asInt() == 0
                        && junit.path("skipped").asInt() == 0
                        && junit.path(
                        "manifest_blob_external_git_anchor_complete").asBoolean()
                        && !junit.path(
                        "historical_manifest_document_rewritten").asBoolean(),
                "post-push JUnit execution boundary drifted");
    }

    private static void validateWormReference(JsonNode worm) {
        require(propertyNames(worm).equals(Set.of(
                        "source", "sha256", "predecessor_sha256",
                        "fixed_chain_node_count", "reused", "new_worm_report_created",
                        "java_build_context_sha256", "dockerfile_sha256",
                        "canonical_schema_dump_sha256")),
                "unexpected post-push WORM shape");
        require(WORM_RELATIVE.equals(worm.path("source").asString())
                        && WORM_SHA256.equals(worm.path("sha256").asString())
                        && WORM_PREDECESSOR_SHA256.equals(
                        worm.path("predecessor_sha256").asString())
                        && worm.path("fixed_chain_node_count").asInt() == 5
                        && worm.path("reused").asBoolean()
                        && !worm.path("new_worm_report_created").asBoolean()
                        && BUILD_CONTEXT_SHA256.equals(
                        worm.path("java_build_context_sha256").asString())
                        && DOCKERFILE_SHA256.equals(
                        worm.path("dockerfile_sha256").asString())
                        && CANONICAL_SCHEMA_SHA256.equals(
                        worm.path("canonical_schema_dump_sha256").asString()),
                "post-push WORM boundary drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        Set<String> trueFlags = Set.of(
                "target_dispositions_executed",
                "all_59_target_dispositions_executed",
                "bootstrap_and_anchor_checkpoint_bytes_external_git_anchor_complete",
                "junit_manifest_bytes_external_git_anchor_complete");
        Set<String> falseFlags = Set.of(
                "current_handoff_successor_bytes_external_git_anchor_complete",
                "typed_parity_review_complete", "full_target_parity_closed",
                "route_migration_eligible", "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated",
                "operator_migration_implementation", "production_schema_or_index",
                "real_data_migration_execution", "client_change",
                "gateway_or_proxy_change", "production_cutover");
        Set<String> expectedKeys = new LinkedHashSet<>(trueFlags);
        expectedKeys.addAll(falseFlags);
        require(propertyNames(authorization).equals(expectedKeys),
                "unexpected post-push authorization shape");
        trueFlags.forEach(flag -> require(authorization.path(flag).asBoolean(),
                "post-push authorization is unexpectedly closed: " + flag));
        falseFlags.forEach(flag -> require(!authorization.path(flag).asBoolean(),
                "post-push authorization overclaims: " + flag));
    }

    private static void validateAcceptance(JsonNode acceptance) {
        require(propertyNames(acceptance).equals(Set.of(
                        "checkpoint_artifact_count", "checkpoint_added_total_bytes",
                        "junit_leaf_test_count", "target_case_count",
                        "http_execution_count", "typed_postgresql_disposition_count",
                        "mocked_application_result_case_count", "bound_only_case_count",
                        "typed_parity_review_complete", "full_target_parity_closed",
                        "route_migration_eligible", "implemented_pending_get_count",
                        "migrated_operation_count", "pending_operation_count",
                        "production_cutover_operation_count", "production_cutover",
                        "current_handoff_is_bootstrap", "next_gate")),
                "unexpected post-push acceptance shape");
        require(acceptance.path("checkpoint_artifact_count").asInt() == 9
                        && acceptance.path("checkpoint_added_total_bytes").asLong()
                        == 222_675
                        && acceptance.path("junit_leaf_test_count").asInt() == 60
                        && acceptance.path("target_case_count").asInt() == 59
                        && acceptance.path("http_execution_count").asInt() == 57
                        && acceptance.path(
                        "typed_postgresql_disposition_count").asInt() == 2
                        && acceptance.path(
                        "mocked_application_result_case_count").asInt() == 0
                        && acceptance.path("bound_only_case_count").asInt() == 0
                        && !acceptance.path("typed_parity_review_complete").asBoolean()
                        && !acceptance.path("full_target_parity_closed").asBoolean()
                        && !acceptance.path("route_migration_eligible").asBoolean()
                        && acceptance.path("implemented_pending_get_count").asInt() == 2
                        && acceptance.path("migrated_operation_count").asInt() == 11
                        && acceptance.path("pending_operation_count").asInt() == 600
                        && acceptance.path(
                        "production_cutover_operation_count").asInt() == 0
                        && !acceptance.path("production_cutover").asBoolean()
                        && acceptance.path("current_handoff_is_bootstrap").asBoolean()
                        && NEXT_GATE.equals(acceptance.path("next_gate").asString()),
                "post-push acceptance boundary drifted");
    }

    private static void validateLocalFiles(Path root) throws IOException {
        Path predecessorPath = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(PREDECESSOR_SHA256.equals(sha256(predecessorPath)),
                "post-push predecessor physical hash drifted");
        JsonNode predecessor = readJson(predecessorPath);
        require(PREDECESSOR_ID.equals(predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(
                        predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString())
                        && PREDECESSOR_CAPTURED_AT.equals(
                        predecessor.path("captured_at").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(payloadSha256(predecessor)),
                "post-push predecessor identity or payload drifted");

        Path manifestPath = fixedRegularFile(root, MANIFEST_RELATIVE);
        require(MANIFEST_SHA256.equals(sha256(manifestPath)),
                "post-push JUnit manifest physical hash drifted");
        JsonNode manifest = readJson(manifestPath);
        require(MANIFEST_PAYLOAD_SHA256.equals(
                        manifest.path("document_payload_sha256").asString())
                        && MANIFEST_PAYLOAD_SHA256.equals(payloadSha256(manifest)),
                "post-push JUnit manifest payload drifted");
        JsonNode confidentiality = manifest.path("confidentiality");
        require(!confidentiality.path(
                        "manifest_bytes_external_git_anchor_complete").asBoolean()
                        && confidentiality.path(
                        "post_push_successor_anchor_required").asBoolean(),
                "historical JUnit manifest was rewritten");

        Path wormPath = fixedRegularFile(root, WORM_RELATIVE);
        require(WORM_SHA256.equals(sha256(wormPath)),
                "post-push fifth WORM physical hash drifted");
        JsonNode worm = readJson(wormPath);
        require(BUILD_CONTEXT_SHA256.equals(
                        worm.path("java").path("buildContextSha256").asString())
                        && DOCKERFILE_SHA256.equals(
                        worm.path("java").path("dockerfileSha256").asString())
                        && CANONICAL_SCHEMA_SHA256.equals(worm.path("restore")
                        .path("canonicalSchemaDumpSha256").asString()),
                "post-push fifth WORM boundary drifted");

        for (Map.Entry<String, SuccessorSource> entry : SUCCESSOR_SOURCES.entrySet()) {
            validateTerminalSuccessor(root, entry.getKey(), entry.getValue());
        }
    }

    private static String validateTerminalSuccessor(
            Path root,
            String relative,
            SuccessorSource expected
    ) throws IOException {
        Path path = fixedRegularFile(root, relative);
        String physical = sha256(path);
        if (expected.successorSha256().equals(physical)) {
            require(Files.size(path) == expected.successorByteCount(),
                    "post-push successor source byte count drifted: " + relative);
            return physical;
        }
        return currentOrPostPushAnchorOrTagPreflightSuccessor(
                root,
                relative,
                expected.successorSha256(),
                physical,
                "source");
    }

    private static String currentOrPostPushAnchorOrTagPreflightSuccessor(
            Path root,
            String relative,
            String declaredSha256,
            String physicalSha256,
            String label
    ) throws IOException {
        if (declaredSha256.equals(physicalSha256)) {
            return physicalSha256;
        }
        String anchorAccepted =
                Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                        .acceptedHash(relative);
        if (anchorAccepted != null) {
            require(declaredSha256.equals(anchorAccepted),
                    "post-push external anchor did not accept exact " + label + ": "
                            + relative);
            String anchored =
                    Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                            .successorHash(root, relative);
            require(physicalSha256.equals(anchored),
                    "post-push external anchor did not bind current " + label + ": "
                            + relative);
            return physicalSha256;
        }
        require(declaredSha256.equals(
                        Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                                .acceptedSha256(relative)),
                "tag-preflight successor did not accept exact " + label + ": "
                        + relative);
        String tagPreflightSuccessor =
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance.successorSha256(
                        root, relative);
        require(physicalSha256.equals(tagPreflightSuccessor),
                "tag-preflight successor did not bind current " + label + ": "
                        + relative);
        return physicalSha256;
    }

    private static JsonNode readJson(Path path) throws IOException {
        return JSON.readTree(Files.readString(path, StandardCharsets.UTF_8));
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

    private static Path fixedRegularFile(Path root, String relative) throws IOException {
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute() && !candidate.normalize().startsWith(".."),
                "fixed post-push path escaped Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : candidate) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed post-push path contains a symlink: " + relative);
        }
        Path resolved = root.resolve(candidate).toRealPath();
        require(resolved.startsWith(root)
                        && Files.isRegularFile(resolved, LinkOption.NOFOLLOW_LINKS),
                "fixed post-push path is not a regular Ti-Java file: " + relative);
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

    private static Map.Entry<String, CheckpointArtifact> checkpointArtifact(
            String name,
            String relative,
            String blobOid,
            String sha256,
            long byteCount
    ) {
        return Map.entry(
                name,
                new CheckpointArtifact(relative, blobOid, sha256, byteCount, "100644"));
    }

    private static Map.Entry<String, SuccessorSource> successorSource(
            String relative,
            String acceptedBlobOid,
            String acceptedSha256,
            long acceptedByteCount,
            String successorSha256,
            long successorByteCount,
            String mode
    ) {
        return Map.entry(relative, new SuccessorSource(
                acceptedBlobOid,
                acceptedSha256,
                acceptedByteCount,
                successorSha256,
                successorByteCount,
                mode));
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

    private record CheckpointArtifact(
            String relative,
            String blobOid,
            String sha256,
            long byteCount,
            String mode
    ) {
    }

    private record SuccessorSource(
            String acceptedBlobOid,
            String acceptedSha256,
            long acceptedByteCount,
            String successorSha256,
            long successorByteCount,
            String mode
    ) {
    }

}
