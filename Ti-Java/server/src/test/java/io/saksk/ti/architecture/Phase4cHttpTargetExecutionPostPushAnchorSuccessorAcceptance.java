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

/** Gitless Java mirror for the fixed Phase 4C post-push external anchor. */
final class Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "anchor-contract.json";
    private static final String CONTRACT_SHA256 =
            "1aa86e7cd8fe4f6c6c808eee166ff0ed30f7e228e707941efde87323b9ae057a";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "b38abd80403536c7e6db2ec9b8a8920dc06e9f740ed9c065941e483a0b5a30e2";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-"
                    + "post-push-anchor-contract";
    private static final String CONTRACT_STATUS =
            "target_execution_post_push_checkpoint_externally_anchored_"
                    + "typed_parity_pending_routes_pending";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution-"
                    + "post-push-external-anchor";
    private static final String CAPTURED_AT = "2026-07-18T14:04:12+08:00";
    private static final String NEXT_GATE =
            "typed_parity_real_tomcat_complete_response_headers_redis_refusal_"
                    + "interruption_same_instance_recovery_and_pg16_pg18_termination_"
                    + "identity_sql_nine_table_fingerprints_before_route_migration";

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "3d7208eb2f70b9eb2b559e15acb4cc7882dacecf8cad941f2978678f93b12628";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "c2382550719d97e74f93db97bf74e70e246cca1e35ac6cc9c6c9e8d13b964dba";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-user-counts-http-target-execution-post-push-contract";
    private static final String PREDECESSOR_STATUS =
            "target_execution_anchor_checkpoint_externally_anchored_"
                    + "typed_parity_pending_routes_pending";
    private static final String PREDECESSOR_SCOPE =
            "phase4c-personal-bank-user-counts-http-target-execution-post-push";
    private static final String PREDECESSOR_CAPTURED_AT = "2026-07-18T13:10:47+08:00";
    private static final long PREDECESSOR_BYTE_COUNT = 17_974;

    private static final String COMMIT_OID =
            "1dae013e11c76ad858d6695f166a32631eb1525e";
    private static final String ROOT_TREE_OID =
            "30fd08f8aa8acac5b2b3e2be1e371849ce2adc8d";
    private static final String PARENT_OID =
            "6c1b03dd7fa9cde7a6dcdbf6b555452e9a6d9e53";
    private static final String TI_JAVA_TREE_OID =
            "1d9cc477713f1ff0e58fb9d71cf2e3035cbd314f";
    private static final String COMMIT_TIMESTAMP = "2026-07-18T14:04:12+08:00";
    private static final String COMMIT_SUBJECT =
            "test(java): hand off user counts target anchor";

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

    private static final Map<String, CheckpointChange> CHECKPOINT_CHANGES =
            checkpointChanges();
    private static final Set<String> POST_PUSH_SOURCE_PATHS = Set.of(
            PREDECESSOR_RELATIVE,
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
    private static final Set<String> CURRENT_ANCHOR_SOURCES = Set.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchor"
                    + "ContractParityTest.java",
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_anchor_contract.py",
            "tools/phase4c_http_target_execution_post_push_anchor_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_anchor_contract.py");
    private static final Map<String, SuccessorSource> SUCCESSOR_SOURCES =
            successorSources();

    private Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance() {
    }

    private static Map<String, CheckpointChange> checkpointChanges() {
        return Map.ofEntries(
                change(
                        "README.md", "M",
                        "550bc40705fea9b603a3936de9de366ba49849ef",
                        "b8878d9102157218625945785dcba00526cda5aa",
                        "9c7608803dff193b898d14d13de92095ef001dfeb6099fde2a2ba546d4cd867c",
                        37_695, "100644", "100644"),
                change(
                        "docs/refactor/05-progress.md", "M",
                        "1bcad604184f31cf24a0047bd248d457dda47402",
                        "eef564d6974330fe4c851e0c1a122b99712bd1f6",
                        "9ac3b2edaff690f105326aed3c7a87d4049b7f89a1af541038c8f0b032bf79ec",
                        100_798, "100644", "100644"),
                change(
                        "docs/refactor/phase4c/README.md", "M",
                        "aa989184d7f0c4dea4fb66284346937269891fe2",
                        "e41a660c873e8f5253320d3f9503957368758027",
                        "649ad38f868840edf8ca16ce35156dd18ea7336da9869433bdaa0db2f604fec2",
                        15_137, "100644", "100644"),
                change(
                        PREDECESSOR_RELATIVE, "A",
                        "0000000000000000000000000000000000000000",
                        "79449241fa383c909cedd15f732924f665f11648",
                        PREDECESSOR_SHA256,
                        PREDECESSOR_BYTE_COUNT, "000000", "100644"),
                change(
                        "infra/phase2/README.md", "M",
                        "99a264aa12e44ddf34bda25156877890143d75a3",
                        "673c6b73962605da6af7f7e4593e6cb223f76d6d",
                        "4a5205e57bad5f54b60fd8ad1f21b8f32f5282bb4938a0244ea9f0977c34157e",
                        6_748, "100644", "100644"),
                change(
                        "infra/phase2/verify-static.sh", "M",
                        "c5e3d49701c6e2fa11676fe46b545cc87039b003",
                        "3fd68528c824b522adc285ad82ec0babd7afb7eb",
                        "357cd003b068997cbcb4ed194f785d3a1d1f310871ad1994c5102bcb1839f54d",
                        13_541, "100755", "100755"),
                change(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "Phase4cHttpTargetExecutionPostPush"
                                + "SuccessorAcceptance.java",
                        "A", "0000000000000000000000000000000000000000",
                        "773bca2a7dc42b334b66f9b5b11372cb2298eb53",
                        "5cf9c260bbeac52480e814a0d98317932efe191a6e1ffac8a1c747e7bd0b9e17",
                        43_536, "000000", "100644"),
                change(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "Phase4cHttpTargetExecutionSuccessorAcceptance.java",
                        "M", "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6",
                        "6a98738b1db5de7d3d32cfbafe72e16efe7dbd72",
                        "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578",
                        89_014, "100644", "100644"),
                change(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "Phase4cPersonalBankUserCountsHttpTargetExecution"
                                + "PostPushContractParityTest.java",
                        "A", "0000000000000000000000000000000000000000",
                        "5b4c2e9fe0328e667cd767a0e8696a543c53bcb8",
                        "5805a4517e02ec23af94546e551d4d3994aaed5667fc680f5b603d81e95f9304",
                        15_155, "000000", "100644"),
                change(
                        "tools/build_phase4c_personal_bank_user_counts_http_"
                                + "target_execution_contract.py",
                        "M", "9cac3b5c6a3ecd0b98b71122864b5d706007645f",
                        "c1910a9ccd2cc8e0773bfb0c7cfdd89c31806db1",
                        "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209",
                        61_952, "100644", "100644"),
                change(
                        "tools/build_phase4c_personal_bank_user_counts_http_"
                                + "target_execution_post_push_contract.py",
                        "A", "0000000000000000000000000000000000000000",
                        "02dd94167e32a1ecc980870688d9f558095893b3",
                        "89790dba5376e617128b8b5048f30db8e75f50491ff34f66507654ab3f79ecf3",
                        29_633, "000000", "100644"),
                change(
                        "tools/phase2_wormhole_successor_acceptance.py", "M",
                        "1ccfbe8c3b4837165f83bd8f2a85c5bb4c259cd7",
                        "4fa4e6b00be61e65f2653b3baf35c2d63ea26fce",
                        "b1eabe5dc758e8ff0c2b0d25f7a4878e7a38a4491db7ea3bffbe04018c579464",
                        23_319, "100644", "100644"),
                change(
                        "tools/phase4c_http_target_execution_post_push_"
                                + "successor_acceptance.py",
                        "A", "0000000000000000000000000000000000000000",
                        "81ba7249f09204ee904829413d8ebff2714a2348",
                        "4200844497d67071b1672f00a81ff6309bd6d3d2ac6b355b727e5100f1c9147d",
                        28_435, "000000", "100644"),
                change(
                        "tools/phase4c_http_target_execution_successor_acceptance.py",
                        "M", "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84",
                        "70248a346d5153062625bd124ab3d9a7c2fc019d",
                        "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a",
                        81_902, "100644", "100644"),
                change(
                        "tools/test_phase2_wormhole_successor_acceptance.py", "M",
                        "29f5fed3124d2b76178befed2e53276e3fa6ad75",
                        "a538bc718fb2894054440b22227f8f8d93eef20d",
                        "fae248af8e5b5e61634ac10bb8824d5437fd08c4d168c49faadff3e6983c1b9e",
                        29_314, "100644", "100644"),
                change(
                        "tools/test_phase4c_personal_bank_user_counts_http_"
                                + "target_execution_post_push_contract.py",
                        "A", "0000000000000000000000000000000000000000",
                        "c8462aff9f27889597717a351b1b86226d1fe46a",
                        "5abd19cb1db4f96b59d09f7b0827628a0177d3fdb3b2fd5bcbb80d09208eb158",
                        11_159, "000000", "100644"));
    }

    private static Map<String, SuccessorSource> successorSources() {
        return Map.ofEntries(
                successor("README.md", "b8878d9102157218625945785dcba00526cda5aa",
                        "9c7608803dff193b898d14d13de92095ef001dfeb6099fde2a2ba546d4cd867c",
                        37_695,
                        "9008df17aa8eba4945fde525a304c4d891da20004f18ab86ceda485fffab2b57",
                        37_622, "100644"),
                successor("docs/refactor/05-progress.md",
                        "eef564d6974330fe4c851e0c1a122b99712bd1f6",
                        "9ac3b2edaff690f105326aed3c7a87d4049b7f89a1af541038c8f0b032bf79ec",
                        100_798,
                        "477d2dc0fce4946e511faa2c143fc76367ae6231a932ae204b6858ca5787e1bf",
                        101_162, "100644"),
                successor("docs/refactor/phase4c/README.md",
                        "e41a660c873e8f5253320d3f9503957368758027",
                        "649ad38f868840edf8ca16ce35156dd18ea7336da9869433bdaa0db2f604fec2",
                        15_137,
                        "50f1ee46eddac681b49281c3b348e4017fe6893ec38051a5485317cd766c2f61",
                        15_524, "100644"),
                successor("infra/phase2/README.md",
                        "673c6b73962605da6af7f7e4593e6cb223f76d6d",
                        "4a5205e57bad5f54b60fd8ad1f21b8f32f5282bb4938a0244ea9f0977c34157e",
                        6_748,
                        "7ae3e8a5bb36920039649ffa8a2aef2bd9bb59782fa03f50e4174cee9063b56f",
                        6_786, "100644"),
                successor("infra/phase2/verify-static.sh",
                        "3fd68528c824b522adc285ad82ec0babd7afb7eb",
                        "357cd003b068997cbcb4ed194f785d3a1d1f310871ad1994c5102bcb1839f54d",
                        13_541,
                        "92a3a1ee30ddbb2b5c854dbff7fac23da37e5804e0628211e85725ba4523d835",
                        13_955, "100755"),
                successor(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "Phase4cHttpTargetExecutionPostPush"
                                + "SuccessorAcceptance.java",
                        "773bca2a7dc42b334b66f9b5b11372cb2298eb53",
                        "5cf9c260bbeac52480e814a0d98317932efe191a6e1ffac8a1c747e7bd0b9e17",
                        43_536,
                        "46f68412ea0cf42687133ba87a2184b86fe1b0c29625b1ee3f6e8f7301399efa",
                        45_004, "100644"),
                successor(
                        "server/src/test/java/io/saksk/ti/architecture/"
                                + "Phase4cPersonalBankUserCountsHttpTargetExecution"
                                + "PostPushContractParityTest.java",
                        "5b4c2e9fe0328e667cd767a0e8696a543c53bcb8",
                        "5805a4517e02ec23af94546e551d4d3994aaed5667fc680f5b603d81e95f9304",
                        15_155,
                        "a8e81f0758928eb69c527a9d6bbcf00517160221ea7b1aca4b901b7d5a26cf48",
                        16_704, "100644"),
                successor(
                        "tools/build_phase4c_personal_bank_user_counts_http_"
                                + "target_execution_post_push_contract.py",
                        "02dd94167e32a1ecc980870688d9f558095893b3",
                        "89790dba5376e617128b8b5048f30db8e75f50491ff34f66507654ab3f79ecf3",
                        29_633,
                        "a215e6b65624630de990dcae7e8d718e8a38a1fadae3e00ee0f3ccb81788959f",
                        31_546, "100644"),
                successor("tools/phase2_wormhole_successor_acceptance.py",
                        "4fa4e6b00be61e65f2653b3baf35c2d63ea26fce",
                        "b1eabe5dc758e8ff0c2b0d25f7a4878e7a38a4491db7ea3bffbe04018c579464",
                        23_319,
                        "868d5cebbcc695136083ac892e572483ffc40829f487cb8d9d2b407c2fc763d1",
                        24_199, "100644"),
                successor(
                        "tools/phase4c_http_target_execution_post_push_"
                                + "successor_acceptance.py",
                        "81ba7249f09204ee904829413d8ebff2714a2348",
                        "4200844497d67071b1672f00a81ff6309bd6d3d2ac6b355b727e5100f1c9147d",
                        28_435,
                        "944c925704e1b237a7d8e16c76591a0e8b7965d388bedd9e2a52492e0511c90c",
                        30_640, "100644"),
                successor("tools/test_phase2_wormhole_successor_acceptance.py",
                        "a538bc718fb2894054440b22227f8f8d93eef20d",
                        "fae248af8e5b5e61634ac10bb8824d5437fd08c4d168c49faadff3e6983c1b9e",
                        29_314,
                        "691198f36292c460b6bb516e9deb4e4efe064ae12fe60efb85280a52753cb5cb",
                        36_539, "100644"),
                successor(
                        "tools/test_phase4c_personal_bank_user_counts_http_"
                                + "target_execution_post_push_contract.py",
                        "c8462aff9f27889597717a351b1b86226d1fe46a",
                        "5abd19cb1db4f96b59d09f7b0827628a0177d3fdb3b2fd5bcbb80d09208eb158",
                        11_159,
                        "d99d36f8b17e5072dcd130c4570ac074096a3c9ee2b9bf4f0f49fd2b1cd907e6",
                        11_724, "100644"));
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        Path contractPath = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_SHA256.equals(sha256(contractPath)),
                "post-push anchor contract physical SHA-256 drifted");
        JsonNode contract = readJson(contractPath);
        validate(contract);
        validateLocalFiles(root);
        return contract;
    }

    static void validate(JsonNode contract) {
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status", "scope",
                        "predecessor", "git_checkpoint", "post_push_source_anchor",
                        "historical_source_successors", "junit_execution", "worm_evidence",
                        "authorization", "acceptance", "document_payload_sha256")),
                "unexpected post-push anchor top-level shape");
        require(contract.path("schema_version").asInt() == 1
                        && CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString())
                        && CAPTURED_AT.equals(contract.path("captured_at").asString()),
                "post-push anchor identity drifted");
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "post-push anchor payload drifted");

        validatePredecessorReference(contract.path("predecessor"));
        validateCheckpoint(contract.path("git_checkpoint"));
        validatePostPushSourceAnchor(contract.path("post_push_source_anchor"));
        validateHistoricalSuccessors(contract.path("historical_source_successors"));
        validateJunitReference(contract.path("junit_execution"));
        validateWormReference(contract.path("worm_evidence"));
        validateAuthorization(contract.path("authorization"));
        validateAcceptance(contract.path("acceptance"));
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
        JsonNode contract = loadSuccessorEnvelope(root);
        validateOverride(
                relative,
                source,
                contract.path("historical_source_successors")
                        .path("overrides").path(relative));
        Path path = fixedRegularFile(root, relative);
        String physical = sha256(path);
        require(source.successorSha256().equals(physical)
                        && Files.size(path) == source.successorByteCount(),
                "post-push anchor successor physical bytes drifted: " + relative);
        return physical;
    }

    private static JsonNode loadSuccessorEnvelope(Path root) throws IOException {
        Path contractPath = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(CONTRACT_SHA256.equals(sha256(contractPath)),
                "post-push anchor successor contract hash drifted");
        JsonNode contract = readJson(contractPath);
        validate(contract);
        return contract;
    }

    private static void validatePredecessorReference(JsonNode predecessor) {
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "byte_count", "document_payload_sha256",
                        "contract_id", "status", "scope", "captured_at", "immutable")),
                "unexpected post-push anchor predecessor shape");
        require(PREDECESSOR_RELATIVE.equals(predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(predecessor.path("sha256").asString())
                        && predecessor.path("byte_count").asLong() == PREDECESSOR_BYTE_COUNT
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        predecessor.path("document_payload_sha256").asString())
                        && PREDECESSOR_ID.equals(
                        predecessor.path("contract_id").asString())
                        && PREDECESSOR_STATUS.equals(predecessor.path("status").asString())
                        && PREDECESSOR_SCOPE.equals(predecessor.path("scope").asString())
                        && PREDECESSOR_CAPTURED_AT.equals(
                        predecessor.path("captured_at").asString())
                        && predecessor.path("immutable").asBoolean(),
                "post-push anchor predecessor reference drifted");
    }

    private static void validateCheckpoint(JsonNode checkpoint) {
        require(propertyNames(checkpoint).equals(Set.of(
                        "object_format", "commit_oid", "root_tree_oid", "parent_oid",
                        "ti_java_tree_oid", "authored_at", "committed_at", "subject",
                        "capture_ref_metadata", "capture_ref_is_validation_authority",
                        "diff", "artifacts")),
                "unexpected post-push anchor Git checkpoint shape");
        require("sha1".equals(checkpoint.path("object_format").asString())
                        && COMMIT_OID.equals(checkpoint.path("commit_oid").asString())
                        && ROOT_TREE_OID.equals(checkpoint.path("root_tree_oid").asString())
                        && PARENT_OID.equals(checkpoint.path("parent_oid").asString())
                        && TI_JAVA_TREE_OID.equals(
                        checkpoint.path("ti_java_tree_oid").asString())
                        && COMMIT_TIMESTAMP.equals(
                        checkpoint.path("authored_at").asString())
                        && COMMIT_TIMESTAMP.equals(
                        checkpoint.path("committed_at").asString())
                        && COMMIT_SUBJECT.equals(checkpoint.path("subject").asString())
                        && "origin/main".equals(
                        checkpoint.path("capture_ref_metadata").asString())
                        && !checkpoint.path(
                        "capture_ref_is_validation_authority").asBoolean(),
                "post-push anchor Git checkpoint identity drifted");

        JsonNode diff = checkpoint.path("diff");
        require(propertyNames(diff).equals(Set.of(
                        "added_count", "modified_count", "deleted_count",
                        "non_ti_java_count", "inserted_line_count", "deleted_line_count",
                        "current_total_bytes", "added_total_bytes",
                        "modified_current_total_bytes", "modified_parent_total_bytes",
                        "net_byte_increase", "exact_sixteen_path_delta"))
                        && diff.path("added_count").asInt() == 6
                        && diff.path("modified_count").asInt() == 10
                        && diff.path("deleted_count").asInt() == 0
                        && diff.path("non_ti_java_count").asInt() == 0
                        && diff.path("inserted_line_count").asInt() == 3_799
                        && diff.path("deleted_line_count").asInt() == 89
                        && diff.path("current_total_bytes").asLong() == 605_312
                        && diff.path("added_total_bytes").asLong() == 145_892
                        && diff.path("modified_current_total_bytes").asLong() == 459_420
                        && diff.path("modified_parent_total_bytes").asLong() == 436_774
                        && diff.path("net_byte_increase").asLong() == 168_538
                        && diff.path("exact_sixteen_path_delta").asBoolean(),
                "post-push anchor Git delta drifted");

        JsonNode artifacts = checkpoint.path("artifacts");
        require(propertyNames(artifacts).equals(CHECKPOINT_CHANGES.keySet())
                        && CHECKPOINT_CHANGES.size() == 16
                        && CHECKPOINT_CHANGES.values().stream()
                        .mapToLong(CheckpointChange::byteCount).sum() == 605_312,
                "unexpected post-push anchor checkpoint artifact set");
        CHECKPOINT_CHANGES.forEach((relative, expected) ->
                validateCheckpointChange(relative, expected, artifacts.path(relative)));
    }

    private static void validateCheckpointChange(
            String relative,
            CheckpointChange expected,
            JsonNode actual
    ) {
        require(propertyNames(actual).equals(Set.of(
                        "ti_java_relative_path", "repository_path", "change_type",
                        "previous_mode", "mode", "previous_git_blob_oid", "object_type",
                        "git_blob_oid", "sha256", "byte_count")),
                "unexpected post-push anchor artifact shape: " + relative);
        require(relative.equals(actual.path("ti_java_relative_path").asString())
                        && ("Ti-Java/" + relative).equals(
                        actual.path("repository_path").asString())
                        && expected.changeType().equals(
                        actual.path("change_type").asString())
                        && expected.previousMode().equals(
                        actual.path("previous_mode").asString())
                        && expected.mode().equals(actual.path("mode").asString())
                        && expected.previousBlobOid().equals(
                        actual.path("previous_git_blob_oid").asString())
                        && "blob".equals(actual.path("object_type").asString())
                        && expected.blobOid().equals(
                        actual.path("git_blob_oid").asString())
                        && expected.sha256().equals(actual.path("sha256").asString())
                        && expected.byteCount() == actual.path("byte_count").asLong(),
                "post-push anchor artifact descriptor drifted: " + relative);
    }

    private static void validatePostPushSourceAnchor(JsonNode anchor) {
        require(propertyNames(anchor).equals(Set.of(
                        "accepted_checkpoint_commit_oid", "source_paths",
                        "source_path_allowlist_exact", "source_count",
                        "source_total_bytes", "artifacts",
                        "predecessor_current_sources_external_git_anchor_complete",
                        "predecessor_false_claim_preserved",
                        "whole_commit_root_parent_and_ti_java_tree_fixed",
                        "exact_sixteen_change_blobs_fixed",
                        "arbitrary_git_object_lookup_forbidden",
                        "dynamic_source_discovery_forbidden", "current_anchor_sources",
                        "current_anchor_sources_excluded_from_self_authority",
                        "current_anchor_source_bytes_external_git_anchor_complete",
                        "independently_signed_provenance", "tamper_evident_scope")),
                "unexpected post-push source-anchor shape");
        require(COMMIT_OID.equals(
                        anchor.path("accepted_checkpoint_commit_oid").asString())
                        && strings(anchor.path("source_paths")).equals(
                        POST_PUSH_SOURCE_PATHS.stream().sorted().toList())
                        && anchor.path("source_path_allowlist_exact").asBoolean()
                        && anchor.path("source_count").asInt() == 6
                        && anchor.path("source_total_bytes").asLong() == 145_892
                        && anchor.path(
                        "predecessor_current_sources_external_git_anchor_complete")
                        .asBoolean()
                        && anchor.path("predecessor_false_claim_preserved").asBoolean()
                        && anchor.path(
                        "whole_commit_root_parent_and_ti_java_tree_fixed").asBoolean()
                        && anchor.path("exact_sixteen_change_blobs_fixed").asBoolean()
                        && anchor.path("arbitrary_git_object_lookup_forbidden").asBoolean()
                        && anchor.path("dynamic_source_discovery_forbidden").asBoolean()
                        && strings(anchor.path("current_anchor_sources")).equals(
                        CURRENT_ANCHOR_SOURCES.stream().sorted().toList())
                        && anchor.path(
                        "current_anchor_sources_excluded_from_self_authority").asBoolean()
                        && !anchor.path(
                        "current_anchor_source_bytes_external_git_anchor_complete")
                        .asBoolean()
                        && !anchor.path("independently_signed_provenance").asBoolean()
                        && "fixed_git_commit_tree_delta_and_explicit_blobs".equals(
                        anchor.path("tamper_evident_scope").asString()),
                "post-push source-anchor boundary drifted");

        JsonNode artifacts = anchor.path("artifacts");
        require(propertyNames(artifacts).equals(POST_PUSH_SOURCE_PATHS),
                "unexpected externally anchored post-push source set");
        POST_PUSH_SOURCE_PATHS.forEach(relative -> validateCheckpointChange(
                relative, CHECKPOINT_CHANGES.get(relative), artifacts.path(relative)));
    }

    private static void validateHistoricalSuccessors(JsonNode history) {
        require(propertyNames(history).equals(Set.of(
                        "accepted_checkpoint_commit_oid", "successor_allowlist",
                        "successor_allowlist_exact", "arbitrary_source_lookup_forbidden",
                        "accepted_hashes_from_fixed_git_blobs",
                        "successor_hashes_code_fixed", "successor_transitions_settled",
                        "predecessor_historical_successor_allowlist_count",
                        "second_hop_successor_allowlist_count", "overrides",
                        "current_successor_bytes_external_git_anchor_complete")),
                "unexpected post-push anchor historical-successor shape");
        require(COMMIT_OID.equals(
                        history.path("accepted_checkpoint_commit_oid").asString())
                        && strings(history.path("successor_allowlist")).equals(
                        SUCCESSOR_SOURCES.keySet().stream().sorted().toList())
                        && history.path("successor_allowlist_exact").asBoolean()
                        && history.path("arbitrary_source_lookup_forbidden").asBoolean()
                        && history.path("accepted_hashes_from_fixed_git_blobs").asBoolean()
                        && history.path("successor_hashes_code_fixed").asBoolean()
                        && history.path("successor_transitions_settled").asBoolean()
                        && history.path(
                        "predecessor_historical_successor_allowlist_count").asInt() == 10
                        && history.path(
                        "second_hop_successor_allowlist_count").asInt() == 12
                        && !history.path(
                        "current_successor_bytes_external_git_anchor_complete").asBoolean(),
                "post-push anchor historical-successor boundary drifted");
        JsonNode overrides = history.path("overrides");
        require(propertyNames(overrides).equals(SUCCESSOR_SOURCES.keySet())
                        && SUCCESSOR_SOURCES.size() == 12,
                "unexpected post-push anchor successor override set");
        SUCCESSOR_SOURCES.forEach((relative, expected) ->
                validateOverride(relative, expected, overrides.path(relative)));
    }

    private static void validateOverride(
            String relative,
            SuccessorSource expected,
            JsonNode actual
    ) {
        require(propertyNames(actual).equals(Set.of(
                        "source", "repository_path", "accepted_git_commit_oid",
                        "accepted_git_blob_oid", "accepted_sha256", "accepted_byte_count",
                        "mode", "successor_sha256", "successor_byte_count")),
                "unexpected post-push anchor successor override shape: " + relative);
        require(relative.equals(actual.path("source").asString())
                        && ("Ti-Java/" + relative).equals(
                        actual.path("repository_path").asString())
                        && COMMIT_OID.equals(
                        actual.path("accepted_git_commit_oid").asString())
                        && expected.acceptedBlobOid().equals(
                        actual.path("accepted_git_blob_oid").asString())
                        && expected.acceptedSha256().equals(
                        actual.path("accepted_sha256").asString())
                        && expected.acceptedByteCount()
                        == actual.path("accepted_byte_count").asLong()
                        && expected.mode().equals(actual.path("mode").asString())
                        && expected.successorSha256().equals(
                        actual.path("successor_sha256").asString())
                        && expected.successorByteCount()
                        == actual.path("successor_byte_count").asLong(),
                "post-push anchor successor override drifted: " + relative);
    }

    private static void validateJunitReference(JsonNode junit) {
        require(propertyNames(junit).equals(Set.of(
                        "source", "sha256", "document_payload_sha256",
                        "leaf_payload_sha256", "raw_report_sha256",
                        "raw_report_byte_count", "case_leaf_count",
                        "supplementary_leaf_count", "total_leaf_count", "failures",
                        "errors", "skipped", "manifest_blob_external_git_anchor_complete",
                        "historical_manifest_document_rewritten")),
                "unexpected post-push anchor JUnit shape");
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
                "post-push anchor JUnit boundary drifted");
    }

    private static void validateWormReference(JsonNode worm) {
        require(propertyNames(worm).equals(Set.of(
                        "source", "sha256", "predecessor_sha256",
                        "fixed_chain_node_count", "reused", "new_worm_report_created",
                        "java_build_context_sha256", "dockerfile_sha256",
                        "canonical_schema_dump_sha256")),
                "unexpected post-push anchor WORM shape");
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
                "post-push anchor WORM boundary drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        Set<String> trueFlags = Set.of(
                "target_dispositions_executed",
                "all_59_target_dispositions_executed",
                "post_push_checkpoint_and_six_excluded_sources_"
                        + "external_git_anchor_complete",
                "historical_successor_transitions_settled");
        Set<String> falseFlags = Set.of(
                "current_anchor_source_bytes_external_git_anchor_complete",
                "typed_parity_review_complete", "full_target_parity_closed",
                "route_migration_eligible", "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated",
                "operator_migration_implementation", "production_schema_or_index",
                "real_data_migration_execution", "client_change",
                "gateway_or_proxy_change", "production_cutover");
        Set<String> expectedKeys = new LinkedHashSet<>(trueFlags);
        expectedKeys.addAll(falseFlags);
        require(propertyNames(authorization).equals(expectedKeys),
                "unexpected post-push anchor authorization shape");
        trueFlags.forEach(flag -> require(authorization.path(flag).asBoolean(),
                "post-push anchor authorization is unexpectedly closed: " + flag));
        falseFlags.forEach(flag -> require(!authorization.path(flag).asBoolean(),
                "post-push anchor authorization overclaims: " + flag));
    }

    private static void validateAcceptance(JsonNode acceptance) {
        require(propertyNames(acceptance).equals(Set.of(
                        "checkpoint_changed_path_count", "checkpoint_added_count",
                        "checkpoint_modified_count", "checkpoint_current_total_bytes",
                        "post_push_source_anchor_count",
                        "post_push_source_anchor_total_bytes", "junit_leaf_test_count",
                        "target_case_count", "http_execution_count",
                        "typed_postgresql_disposition_count",
                        "mocked_application_result_case_count", "bound_only_case_count",
                        "typed_parity_review_complete", "full_target_parity_closed",
                        "route_migration_eligible", "implemented_pending_get_count",
                        "migrated_operation_count", "pending_operation_count",
                        "production_cutover_operation_count", "production_cutover",
                        "current_anchor_is_successor_bootstrap", "next_gate")),
                "unexpected post-push anchor acceptance shape");
        require(acceptance.path("checkpoint_changed_path_count").asInt() == 16
                        && acceptance.path("checkpoint_added_count").asInt() == 6
                        && acceptance.path("checkpoint_modified_count").asInt() == 10
                        && acceptance.path("checkpoint_current_total_bytes").asLong()
                        == 605_312
                        && acceptance.path("post_push_source_anchor_count").asInt() == 6
                        && acceptance.path("post_push_source_anchor_total_bytes").asLong()
                        == 145_892
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
                        && acceptance.path(
                        "current_anchor_is_successor_bootstrap").asBoolean()
                        && NEXT_GATE.equals(acceptance.path("next_gate").asString()),
                "post-push anchor acceptance boundary drifted");
    }

    private static void validateLocalFiles(Path root) throws IOException {
        Path predecessorPath = fixedRegularFile(root, PREDECESSOR_RELATIVE);
        require(PREDECESSOR_SHA256.equals(sha256(predecessorPath))
                        && Files.size(predecessorPath) == PREDECESSOR_BYTE_COUNT,
                "post-push anchor predecessor physical bytes drifted");
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
                "post-push anchor predecessor identity or payload drifted");
        JsonNode predecessorHistory = predecessor.path("historical_source_successors");
        require(strings(predecessorHistory.path("current_post_push_sources")).equals(
                        POST_PUSH_SOURCE_PATHS.stream().sorted().toList())
                        && predecessorHistory.path(
                        "current_post_push_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !predecessorHistory.path(
                        "current_successor_bytes_external_git_anchor_complete")
                        .asBoolean(),
                "post-push anchor predecessor self-authority boundary drifted");

        Path manifestPath = fixedRegularFile(root, MANIFEST_RELATIVE);
        require(MANIFEST_SHA256.equals(sha256(manifestPath)),
                "post-push anchor JUnit manifest physical hash drifted");
        JsonNode manifest = readJson(manifestPath);
        require(MANIFEST_PAYLOAD_SHA256.equals(
                        manifest.path("document_payload_sha256").asString())
                        && MANIFEST_PAYLOAD_SHA256.equals(payloadSha256(manifest))
                        && LEAF_PAYLOAD_SHA256.equals(manifest.path("result")
                        .path("leaf_payload_sha256").asString())
                        && manifest.path("result").path("leaves").size() == 60
                        && RAW_REPORT_SHA256.equals(manifest.path("raw_report")
                        .path("sha256").asString())
                        && manifest.path("raw_report").path("byte_count").asInt()
                        == 63_450,
                "post-push anchor JUnit manifest payload drifted");

        Path wormPath = fixedRegularFile(root, WORM_RELATIVE);
        require(WORM_SHA256.equals(sha256(wormPath)),
                "post-push anchor fifth WORM physical hash drifted");
        JsonNode worm = readJson(wormPath);
        require(BUILD_CONTEXT_SHA256.equals(
                        worm.path("java").path("buildContextSha256").asString())
                        && DOCKERFILE_SHA256.equals(
                        worm.path("java").path("dockerfileSha256").asString())
                        && CANONICAL_SCHEMA_SHA256.equals(worm.path("restore")
                        .path("canonicalSchemaDumpSha256").asString())
                        && !worm.path("flywayBaselineCreated").asBoolean(),
                "post-push anchor fifth WORM boundary drifted");

        for (Map.Entry<String, SuccessorSource> entry : SUCCESSOR_SOURCES.entrySet()) {
            Path path = fixedRegularFile(root, entry.getKey());
            SuccessorSource expected = entry.getValue();
            require(expected.successorSha256().equals(sha256(path))
                            && Files.size(path) == expected.successorByteCount(),
                    "post-push anchor successor source drifted: " + entry.getKey());
        }
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
                "fixed post-push anchor path escaped Ti-Java: " + relative);
        Path cursor = root;
        for (Path part : candidate) {
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "fixed post-push anchor path contains a symlink: " + relative);
        }
        Path resolved = root.resolve(candidate).toRealPath();
        require(resolved.startsWith(root)
                        && Files.isRegularFile(resolved, LinkOption.NOFOLLOW_LINKS),
                "fixed post-push anchor path is not a regular Ti-Java file: " + relative);
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

    private static Map.Entry<String, CheckpointChange> change(
            String relative,
            String changeType,
            String previousBlobOid,
            String blobOid,
            String sha256,
            long byteCount,
            String previousMode,
            String mode
    ) {
        return Map.entry(relative, new CheckpointChange(
                changeType, previousBlobOid, blobOid, sha256,
                byteCount, previousMode, mode));
    }

    private static Map.Entry<String, SuccessorSource> successor(
            String relative,
            String acceptedBlobOid,
            String acceptedSha256,
            long acceptedByteCount,
            String successorSha256,
            long successorByteCount,
            String mode
    ) {
        return Map.entry(relative, new SuccessorSource(
                acceptedBlobOid, acceptedSha256, acceptedByteCount,
                successorSha256, successorByteCount, mode));
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

    private record CheckpointChange(
            String changeType,
            String previousBlobOid,
            String blobOid,
            String sha256,
            long byteCount,
            String previousMode,
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
