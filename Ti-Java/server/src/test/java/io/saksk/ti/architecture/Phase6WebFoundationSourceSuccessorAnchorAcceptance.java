package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

import java.io.IOException;
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

/**
 * Gitless Java acceptance for the fixed Phase 6 Web-foundation source-
 * successor external Git anchor.
 */
final class Phase6WebFoundationSourceSuccessorAnchorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase6/"
                    + "web-foundation-source-successor-anchor-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase6.web-foundation-source-successor-anchor-contract";
    private static final String CONTRACT_STATUS =
            "source_successor_checkpoint_externally_anchored_phase6_incomplete";
    private static final String CONTRACT_SCOPE =
            "phase6-web-foundation-source-successor-external-anchor";
    private static final String CONTRACT_CAPTURED_AT =
            "2026-07-19T03:00:00+08:00";
    private static final String CONTRACT_SHA256 =
            "c91b924c027af0099dfec9d8ff36945635b128ba5822c8faca1f6fcfb2167da2";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "87d952b1ba4ca4336c067d8d68ffbe86101ea0263c854541674ac3dbd7feb4af";
    private static final long CONTRACT_BYTES = 29_658L;

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase6/web-foundation-source-successor-contract.json";
    private static final String PREDECESSOR_SHA256 =
            "be652b57cf9e024effbd62d5eb5f438931c4db3c8126e8318e2af077236e4073";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "93e2eccb5bd3cdcc95addac0d09bef26d25ae3676c1ffd1b9c10c337c1b1b693";
    private static final long PREDECESSOR_BYTES = 7_335L;

    private static final String ROUTE_STATUS_RELATIVE =
            "docs/refactor/phase4c/effective-route-parity-successor-status.json";
    private static final String ROUTE_STATUS_SHA256 =
            "c0e96472533d0bbe7d67ac1416a91f3e9a3bfcef8c27e1170b0e9939c46b358a";
    private static final String ROUTE_STATUS_PAYLOAD_SHA256 =
            "3788d541c027ba7f9c397afee1d006ea92da300845557ca35bdd513b920a0637";
    private static final long ROUTE_STATUS_BYTES = 5_340L;

    private static final String HASHER_RELATIVE =
            "infra/phase2/hash-java-build-context.sh";
    private static final String HASHER_SHA256 =
            "e8e618ce08128e4fbf7b090b5b0709ed1d6bc5d1638f1f2838ff6d7409a0dea6";
    private static final long HASHER_BYTES = 1_011L;
    private static final String DOCKERFILE_RELATIVE = "server/Dockerfile";
    private static final String DOCKERFILE_SHA256 =
            "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499";
    private static final long DOCKERFILE_BYTES = 1_850L;
    private static final String JAVA_BUILD_CONTEXT_SHA256 =
            "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3";
    private static final String WORM_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-"
                    + "evidence.json";
    private static final String WORM_SHA256 =
            "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39";
    private static final long WORM_BYTES = 1_442L;

    private static final String GIT_COMMIT =
            "40a27ffdd83ecf240e17f4a5f69106906faaef35";
    private static final String GIT_PARENT =
            "c563ac655077e69306c34d163f63a4da50569e01";
    private static final String GIT_ROOT_TREE =
            "b83b6957736c594066cf18955b8e87b1c91f6b82";
    private static final String GIT_TI_JAVA_TREE =
            "d7c83c3439509ea51e5fa06f3310df91bf0fd5a4";
    private static final String GIT_SERVER_TREE =
            "275dbc7251889ca9fad02688fb4b418e52d2c68a";
    private static final String GIT_SERVER_SRC_MAIN_TREE =
            "7130e1d1fde766030689658cdd508794ab9a12d6";
    private static final String GIT_WEB_TREE =
            "a75f69a8205a56843feb055656ddb015ec5b5215";
    private static final String GIT_RAW_DELTA_SHA256 =
            "0e97aacf626cf528ab4303bc5c61cfc9e359edb66f1a9b227e866dc21c26d2cd";

    private static final String JAVA_ACCEPTANCE =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAcceptance.java";
    private static final String JAVA_PARITY =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java";
    private static final String TYPED_JAVA_ACCEPTANCE =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.java";
    private static final String TYPED_JAVA_PARITY =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchor"
                    + "ContractParityTest.java";

    private static final List<String> PREDECESSOR_CONTROL_SOURCES = List.of(
            PREDECESSOR_RELATIVE,
            JAVA_ACCEPTANCE,
            JAVA_PARITY,
            "tools/build_phase6_web_foundation_source_successor_contract.py",
            "tools/phase6_web_foundation_source_successor_acceptance.py",
            "tools/test_phase6_web_foundation_source_successor_contract.py");

    private static final List<String> TYPED_ANCHOR_BRIDGE_SOURCES = List.of(
            TYPED_JAVA_ACCEPTANCE,
            TYPED_JAVA_PARITY,
            "tools/build_phase4c_personal_bank_user_counts_http_typed_"
                    + "normalization_anchor_contract.py",
            "tools/phase4c_http_typed_normalization_anchor_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_typed_"
                    + "normalization_anchor_contract.py");

    private static final List<String> CURRENT_CONTROL_SOURCES = List.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java",
            "tools/build_phase6_web_foundation_source_successor_anchor_contract.py",
            "tools/phase6_web_foundation_source_successor_anchor_acceptance.py",
            "tools/test_phase6_web_foundation_source_successor_anchor_contract.py");

    private static final Set<String> TAG_PREFLIGHT_DELEGATED_PATHS = Set.of(
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            TYPED_JAVA_ACCEPTANCE,
            TYPED_JAVA_PARITY,
            "tools/phase4c_http_typed_normalization_anchor_"
                    + "successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_typed_"
                    + "normalization_anchor_contract.py",
            "tools/test_phase6_web_foundation_source_successor_contract.py",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java");

    private static final List<String> SOURCE_PATHS = List.of(
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            PREDECESSOR_RELATIVE,
            JAVA_ACCEPTANCE,
            JAVA_PARITY,
            "tools/build_phase6_web_foundation_source_successor_contract.py",
            "tools/phase6_web_foundation_source_successor_acceptance.py",
            "tools/test_phase6_web_foundation_source_successor_contract.py");

    private static final Map<String, CheckpointArtifact> CHECKPOINT_ARTIFACTS =
            checkpointArtifacts();
    private static final Map<String, Successor> SUCCESSORS = successors();

    private Phase6WebFoundationSourceSuccessorAnchorAcceptance() {
    }

    private static Map<String, CheckpointArtifact> checkpointArtifacts() {
        return Map.ofEntries(
                artifact(
                        PREDECESSOR_RELATIVE, "A",
                        "0000000000000000000000000000000000000000",
                        "4e2e267bfcf443139916fdd409b3d6885458c57b",
                        PREDECESSOR_SHA256, PREDECESSOR_BYTES,
                        "000000", "100644"),
                artifact(
                        TYPED_JAVA_ACCEPTANCE, "M",
                        "14a37c3cf9178f0f328d8ebb77bea7ed4ceaed36",
                        "41fedbae3238f0fb2d839e705ad673b65be56ec0",
                        "b762441b9d0537240e231effbe5477b89713e7abc861ff9d5a614fc80008848c",
                        43_848L, "100644", "100644"),
                artifact(
                        TYPED_JAVA_PARITY, "M",
                        "201a87ace6f96552be458571efc1195daedb956b",
                        "078eb34c6bc7bee1989697ca08f1c4ada0117a26",
                        "f0f57fbd1c24e8f26878209eba298645c63bd962381d26d2505fb76ee495cda8",
                        14_962L, "100644", "100644"),
                artifact(
                        JAVA_ACCEPTANCE, "A",
                        "0000000000000000000000000000000000000000",
                        "c7094e9cbd6a90e57f16596421ada26abfd2734d",
                        "dbdb33fdcba228d45ee72a560dccc11baee489c3780864caa1e649e2e9aa489b",
                        29_043L, "000000", "100644"),
                artifact(
                        JAVA_PARITY, "A",
                        "0000000000000000000000000000000000000000",
                        "d918f07417f6362e8ee07534762efe83cd5edcff",
                        "e17f062b1cd960289aa5a56cd3fc7b0aa65a649b16f48c7d802d51fab81a89ec",
                        11_378L, "000000", "100644"),
                artifact(
                        "tools/build_phase4c_personal_bank_user_counts_http_"
                                + "typed_normalization_anchor_contract.py",
                        "M", "a1a07b4f2b8d8524862cb907807ffa09f226546f",
                        "f2cb5c04f9dc8e6563c45d63164648ffc9556643",
                        "1b0064f9ce37fd41156b9eb74574d11e022ef88e889fd9c965fa514a4d0eba23",
                        45_854L, "100644", "100644"),
                artifact(
                        "tools/build_phase6_web_foundation_source_successor_contract.py",
                        "A", "0000000000000000000000000000000000000000",
                        "aa1785ab315e19eb6832e31c45f7ad821480dab7",
                        "f9fc6c70ad12e98ceb4d1bf27bb448085807c91fc390c56e451b905403b263c6",
                        21_526L, "000000", "100644"),
                artifact(
                        "tools/phase4c_http_typed_normalization_anchor_"
                                + "successor_acceptance.py",
                        "M", "795476b3231b5a26c4c9f4220681b446038cedec",
                        "3ea8170b0a9392b332f2794269c8f30a390b72ee",
                        "cf434c2dc8e33c0b60d09646292fc358bc2df678bfe2f83d04edae79c7bd4aee",
                        41_725L, "100644", "100644"),
                artifact(
                        "tools/phase6_web_foundation_source_successor_acceptance.py",
                        "A", "0000000000000000000000000000000000000000",
                        "779adedd4b894ede7b215371b7ae5f661fd71c1a",
                        "1904fae55218791fdc7c66490bcff0d9d9702a4d769ceb919542670bb6e32974",
                        18_420L, "000000", "100644"),
                artifact(
                        "tools/test_phase4c_personal_bank_user_counts_http_typed_"
                                + "normalization_anchor_contract.py",
                        "M", "43683440f7c3b5befb7696bf3226f711996461c3",
                        "3c7af81193452fc00a2d98458025431f4ca7ad73",
                        "a96c4431b258b15d367250b668602fcb0ca04cab9555f13a4abfaa8914b0edec",
                        11_128L, "100644", "100644"),
                artifact(
                        "tools/test_phase6_web_foundation_source_successor_contract.py",
                        "A", "0000000000000000000000000000000000000000",
                        "233930c91cd111c6d45e28141b0df876d26d98c9",
                        "08058702a694a380e16a3a385293396f5f13f88b1cfb36209ffff16818c2a471",
                        9_084L, "000000", "100644"));
    }

    private static Map<String, Successor> successors() {
        return Map.ofEntries(
                successor(
                        "README.md",
                        "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
                        40_323L, "a18ef8e66e1213b4e7ab47e20fb63278c264ba4e",
                        "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
                        40_323L, false),
                successor(
                        "docs/refactor/05-progress.md",
                        "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
                        105_423L, "74974ed6ca408e90846ab90b90e965d8fc9faa5b",
                        "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
                        105_423L, false),
                successor(
                        "docs/refactor/phase4c/README.md",
                        "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
                        23_309L, "8659b84a26ea0b7182c4e375bcb1a1ee185e58b6",
                        "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
                        23_309L, false),
                successor(
                        PREDECESSOR_RELATIVE, PREDECESSOR_SHA256,
                        PREDECESSOR_BYTES,
                        "4e2e267bfcf443139916fdd409b3d6885458c57b",
                        PREDECESSOR_SHA256, PREDECESSOR_BYTES, false),
                successor(
                        JAVA_ACCEPTANCE,
                        "dbdb33fdcba228d45ee72a560dccc11baee489c3780864caa1e649e2e9aa489b",
                        29_043L, "c7094e9cbd6a90e57f16596421ada26abfd2734d",
                        "288e85ace1a4fc3e2a74e03d4390533044678604fef71fe6707c3e840c2b5d85",
                        29_642L, true),
                successor(
                        JAVA_PARITY,
                        "e17f062b1cd960289aa5a56cd3fc7b0aa65a649b16f48c7d802d51fab81a89ec",
                        11_378L, "d918f07417f6362e8ee07534762efe83cd5edcff",
                        "34d6b638cf40667a2c0b1ce1214cc04b8e149321f3137ea8d5d09ee44290d694",
                        11_770L, true),
                successor(
                        "tools/build_phase6_web_foundation_source_successor_contract.py",
                        "f9fc6c70ad12e98ceb4d1bf27bb448085807c91fc390c56e451b905403b263c6",
                        21_526L, "aa1785ab315e19eb6832e31c45f7ad821480dab7",
                        "ed3a711cf9e0b15cb7facfcaa76a63ca2d6509eda84dc617afbfc8b033a1079a",
                        22_788L, true),
                successor(
                        "tools/phase6_web_foundation_source_successor_acceptance.py",
                        "1904fae55218791fdc7c66490bcff0d9d9702a4d769ceb919542670bb6e32974",
                        18_420L, "779adedd4b894ede7b215371b7ae5f661fd71c1a",
                        "19190c0053c1313f5b481c5ce85db8d905e959f6ada10745848c7dcce4f57e59",
                        19_222L, true),
                successor(
                        "tools/test_phase6_web_foundation_source_successor_contract.py",
                        "08058702a694a380e16a3a385293396f5f13f88b1cfb36209ffff16818c2a471",
                        9_084L, "233930c91cd111c6d45e28141b0df876d26d98c9",
                        "fb553e8d15c8b748dc62eb6517f775614132657a60b13716449ad1a72606685d",
                        9_139L, true));
    }

    private static Map.Entry<String, CheckpointArtifact> artifact(
            String relative,
            String changeType,
            String previousBlob,
            String blob,
            String sha256,
            long bytes,
            String previousMode,
            String mode) {
        return Map.entry(relative, new CheckpointArtifact(
                changeType, previousBlob, blob, sha256, bytes,
                previousMode, mode));
    }

    private static Map.Entry<String, Successor> successor(
            String relative,
            String acceptedSha256,
            long acceptedBytes,
            String acceptedGitBlobOid,
            String successorSha256,
            long successorBytes,
            boolean changedAfterCheckpoint) {
        return Map.entry(relative, new Successor(
                acceptedSha256, acceptedBytes, acceptedGitBlobOid,
                successorSha256, successorBytes, changedAfterCheckpoint));
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static Set<String> successorPaths() {
        return SUCCESSORS.keySet();
    }

    static String acceptedSha256(String relative) {
        Successor successor = SUCCESSORS.get(relative);
        return successor == null ? null : successor.acceptedSha256();
    }

    static String successorSha256(Path tiJavaRoot, String relative)
            throws IOException {
        Successor successor = SUCCESSORS.get(relative);
        if (successor == null) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        Path path = fixedRegularFile(root, relative);
        String physicalSha256 = sha256(path);
        if (Files.size(path) == successor.successorBytes()
                && successor.successorSha256().equals(physicalSha256)) {
            return physicalSha256;
        }
        require(TAG_PREFLIGHT_DELEGATED_PATHS.contains(relative),
                "Phase6 source-successor anchor bytes drifted: " + relative);
        return tagPreflightSuccessorSha256(
                root, relative, successor.successorSha256(), physicalSha256);
    }

    static String acceptedHash(String relative) {
        return acceptedSha256(relative);
    }

    static String successorHash(Path tiJavaRoot, String relative)
            throws IOException {
        return successorSha256(tiJavaRoot, relative);
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(PREDECESSOR_RELATIVE);
        paths.add(ROUTE_STATUS_RELATIVE);
        paths.add(HASHER_RELATIVE);
        paths.add(DOCKERFILE_RELATIVE);
        paths.add(WORM_RELATIVE);
        paths.addAll(SOURCE_PATHS);
        paths.addAll(TYPED_ANCHOR_BRIDGE_SOURCES);
        paths.add(
                Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                        .contractRelative());
        paths.add(
                Phase4cTagMigrationOperatorCoreSuccessorAcceptance
                        .contractRelative());
        paths.add(
                Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                        .contractRelative());
        return Set.copyOf(paths);
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = validateContractPhysicalBytes(root);
        validate(contract, root);
        return contract;
    }

    static void validate(JsonNode contract, Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status",
                        "scope", "predecessor_source_successor", "git_checkpoint",
                        "predecessor_control_source_anchor",
                        "typed_anchor_bridge_source_anchor", "source_successors",
                        "java_build_context_boundary", "effective_authority",
                        "authorization", "current_node_trust_boundary",
                        "acceptance", "document_payload_sha256")),
                "Phase6 source-successor anchor contract shape drifted");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && contract.path("schema_version").asInt() == 1
                        && CONTRACT_CAPTURED_AT.equals(
                        contract.path("captured_at").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "Phase6 source-successor anchor identity drifted");

        validatePredecessor(contract.path("predecessor_source_successor"), root);
        validateCheckpoint(contract.path("git_checkpoint"));
        validateSourceAnchor(
                contract.path("predecessor_control_source_anchor"),
                PREDECESSOR_CONTROL_SOURCES,
                "predecessor_control_sources_external_git_anchor_complete");
        validateSourceAnchor(
                contract.path("typed_anchor_bridge_source_anchor"),
                TYPED_ANCHOR_BRIDGE_SOURCES,
                "typed_anchor_bridge_sources_external_git_anchor_complete");
        validateCurrentTypedBridgeSources(
                contract.path("typed_anchor_bridge_source_anchor"), root);
        validateSuccessors(contract.path("source_successors"), root);
        validateJavaBoundary(contract.path("java_build_context_boundary"), root);
        validateAuthority(contract.path("effective_authority"), root);
        validateAuthorization(contract.path("authorization"));
        validateTrustBoundary(contract.path("current_node_trust_boundary"));
        validateAcceptance(contract.path("acceptance"));
    }

    private static JsonNode validateContractPhysicalBytes(Path root)
            throws IOException {
        Path path = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(Files.size(path) == CONTRACT_BYTES
                        && CONTRACT_SHA256.equals(sha256(path)),
                "Phase6 source-successor anchor contract physical bytes drifted");
        JsonNode contract = JSON.readTree(Files.readAllBytes(path));
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "Phase6 source-successor anchor contract payload drifted");
        return contract;
    }

    private static void validatePredecessor(JsonNode predecessor, Path root)
            throws IOException {
        require(propertyNames(predecessor).equals(Set.of(
                        "source", "sha256", "byte_count", "contract_id",
                        "status", "document_payload_sha256", "immutable"))
                        && PREDECESSOR_RELATIVE.equals(
                        predecessor.path("source").asString())
                        && PREDECESSOR_SHA256.equals(
                        predecessor.path("sha256").asString())
                        && predecessor.path("byte_count").asLong()
                        == PREDECESSOR_BYTES
                        && "ti.phase6.web-foundation-source-successor-contract"
                        .equals(predecessor.path("contract_id").asString())
                        && "bootstrap_complete_external_git_anchor_pending"
                        .equals(predecessor.path("status").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(predecessor
                        .path("document_payload_sha256").asString())
                        && predecessor.path("immutable").asBoolean(),
                "Phase6 source-successor anchor predecessor drifted");
        JsonNode fixed = readFixedJson(
                root, PREDECESSOR_RELATIVE, PREDECESSOR_SHA256,
                PREDECESSOR_BYTES);
        require("ti.phase6.web-foundation-source-successor-contract".equals(
                        fixed.path("contract_id").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        fixed.path("document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(payloadSha256(fixed)),
                "Phase6 source-successor anchor predecessor payload drifted");
    }

    private static void validateCheckpoint(JsonNode checkpoint) {
        require(propertyNames(checkpoint).equals(Set.of(
                        "object_format", "commit_oid", "parent_oid",
                        "root_tree_oid", "ti_java_tree_oid", "server_tree_oid",
                        "server_src_main_tree_oid", "web_tree_oid", "authored_at",
                        "committed_at", "subject", "raw_delta_sha256",
                        "changed_path_count", "added_count", "modified_count",
                        "deleted_count", "inserted_line_count",
                        "deleted_line_count", "current_total_bytes",
                        "added_total_bytes", "modified_current_bytes",
                        "modified_parent_bytes", "net_byte_increase",
                        "exact_eleven_path_delta", "artifacts")),
                "Phase6 source-successor anchor checkpoint shape drifted");
        require("sha1".equals(checkpoint.path("object_format").asString())
                        && GIT_COMMIT.equals(checkpoint.path("commit_oid").asString())
                        && GIT_PARENT.equals(checkpoint.path("parent_oid").asString())
                        && GIT_ROOT_TREE.equals(
                        checkpoint.path("root_tree_oid").asString())
                        && GIT_TI_JAVA_TREE.equals(
                        checkpoint.path("ti_java_tree_oid").asString())
                        && GIT_SERVER_TREE.equals(
                        checkpoint.path("server_tree_oid").asString())
                        && GIT_SERVER_SRC_MAIN_TREE.equals(checkpoint
                        .path("server_src_main_tree_oid").asString())
                        && GIT_WEB_TREE.equals(
                        checkpoint.path("web_tree_oid").asString())
                        && "2026-07-19T02:41:02+08:00".equals(
                        checkpoint.path("authored_at").asString())
                        && "2026-07-19T02:41:02+08:00".equals(
                        checkpoint.path("committed_at").asString())
                        && "test(java): bridge phase6 source successor".equals(
                        checkpoint.path("subject").asString())
                        && GIT_RAW_DELTA_SHA256.equals(
                        checkpoint.path("raw_delta_sha256").asString())
                        && checkpoint.path("changed_path_count").asInt() == 11
                        && checkpoint.path("added_count").asInt() == 6
                        && checkpoint.path("modified_count").asInt() == 5
                        && checkpoint.path("deleted_count").asInt() == 0
                        && checkpoint.path("inserted_line_count").asInt() == 2_297
                        && checkpoint.path("deleted_line_count").asInt() == 28
                        && checkpoint.path("current_total_bytes").asLong()
                        == 254_303L
                        && checkpoint.path("added_total_bytes").asLong()
                        == 96_786L
                        && checkpoint.path("modified_current_bytes").asLong()
                        == 157_517L
                        && checkpoint.path("modified_parent_bytes").asLong()
                        == 148_725L
                        && checkpoint.path("net_byte_increase").asLong()
                        == 105_578L
                        && checkpoint.path("exact_eleven_path_delta").asBoolean(),
                "Phase6 source-successor anchor checkpoint drifted");

        JsonNode artifacts = checkpoint.path("artifacts");
        require(propertyNames(artifacts).equals(CHECKPOINT_ARTIFACTS.keySet()),
                "Phase6 source-successor anchor exact delta drifted");
        CHECKPOINT_ARTIFACTS.forEach((relative, expected) ->
                validateArtifact(artifacts.path(relative), relative, expected));
    }

    private static void validateSourceAnchor(
            JsonNode anchor,
            List<String> expectedPaths,
            String completionField) {
        require(propertyNames(anchor).equals(Set.of(
                        "source_paths", "source_count", "source_allowlist_exact",
                        completionField, "artifacts"))
                        && strings(anchor.path("source_paths")).equals(expectedPaths)
                        && anchor.path("source_count").asInt()
                        == expectedPaths.size()
                        && anchor.path("source_allowlist_exact").asBoolean()
                        && anchor.path(completionField).asBoolean(),
                "Phase6 source-successor anchored source allowlist drifted");
        JsonNode artifacts = anchor.path("artifacts");
        require(propertyNames(artifacts).equals(Set.copyOf(expectedPaths)),
                "Phase6 source-successor anchored artifact set drifted");
        for (String relative : expectedPaths) {
            CheckpointArtifact expected = CHECKPOINT_ARTIFACTS.get(relative);
            require(expected != null,
                    "Phase6 anchored source absent from checkpoint: " + relative);
            validateArtifact(artifacts.path(relative), relative, expected);
        }
    }

    private static void validateArtifact(
            JsonNode actual,
            String relative,
            CheckpointArtifact expected) {
        require(propertyNames(actual).equals(Set.of(
                        "ti_java_relative_path", "repository_path", "change_type",
                        "previous_mode", "mode", "previous_git_blob_oid",
                        "git_blob_oid", "object_type", "sha256", "byte_count"))
                        && relative.equals(
                        actual.path("ti_java_relative_path").asString())
                        && ("Ti-Java/" + relative).equals(
                        actual.path("repository_path").asString())
                        && expected.changeType().equals(
                        actual.path("change_type").asString())
                        && expected.previousMode().equals(
                        actual.path("previous_mode").asString())
                        && expected.mode().equals(actual.path("mode").asString())
                        && expected.previousGitBlobOid().equals(
                        actual.path("previous_git_blob_oid").asString())
                        && expected.gitBlobOid().equals(
                        actual.path("git_blob_oid").asString())
                        && "blob".equals(actual.path("object_type").asString())
                        && expected.sha256().equals(
                        actual.path("sha256").asString())
                        && expected.byteCount()
                        == actual.path("byte_count").asLong(),
                "Phase6 source-successor checkpoint artifact drifted: "
                        + relative);
    }

    private static void validateCurrentTypedBridgeSources(
            JsonNode sourceAnchor,
            Path root
    ) throws IOException {
        for (String relative : TYPED_ANCHOR_BRIDGE_SOURCES) {
            CheckpointArtifact accepted = CHECKPOINT_ARTIFACTS.get(relative);
            Path path = fixedRegularFile(root, relative);
            String physicalSha256 = sha256(path);
            if (accepted.sha256().equals(physicalSha256)
                    && accepted.byteCount() == Files.size(path)) {
                continue;
            }
            require(TAG_PREFLIGHT_DELEGATED_PATHS.contains(relative),
                    "Phase6 source-successor typed bridge bytes drifted: "
                            + relative);
            require(physicalSha256.equals(tagPreflightSuccessorSha256(
                            root, relative, accepted.sha256(), physicalSha256)),
                    "Phase6 source-successor typed bridge was not fixed: "
                            + relative);
        }
    }

    private static String tagPreflightSuccessorSha256(
            Path root,
            String relative,
            String acceptedSha256,
            String physicalSha256
    ) throws IOException {
        require(acceptedSha256.equals(
                        Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                                .acceptedSha256(relative)),
                "tag-preflight successor rejected Phase6 accepted bytes: "
                        + relative);
        String terminal;
        try {
            terminal =
                    Phase4cTagMigrationGlobalPreflightSuccessorAcceptance
                            .successorSha256(root, relative);
        } catch (AssertionError error) {
            throw new AssertionError(
                    "tag-preflight successor rejected Phase6 current bytes: "
                            + relative,
                    error);
        }
        require(physicalSha256.equals(terminal),
                "tag-preflight successor did not bind Phase6 current bytes: "
                        + relative);
        return physicalSha256;
    }

    private static void validateSuccessors(JsonNode successors, Path root)
            throws IOException {
        require(propertyNames(successors).equals(Set.of(
                        "paths", "path_count", "path_allowlist_exact",
                        "dynamic_source_discovery_forbidden", "overrides"))
                        && strings(successors.path("paths")).equals(SOURCE_PATHS)
                        && successors.path("path_count").asInt() == 9
                        && successors.path("path_allowlist_exact").asBoolean()
                        && successors.path(
                        "dynamic_source_discovery_forbidden").asBoolean(),
                "Phase6 source-successor anchor allowlist drifted");
        JsonNode overrides = successors.path("overrides");
        require(propertyNames(overrides).equals(SUCCESSORS.keySet()),
                "Phase6 source-successor anchor override set drifted");
        for (Map.Entry<String, Successor> entry : SUCCESSORS.entrySet()) {
            String relative = entry.getKey();
            Successor expected = entry.getValue();
            JsonNode actual = overrides.path(relative);
            require(propertyNames(actual).equals(Set.of(
                            "source", "accepted_git_commit_oid",
                            "accepted_git_blob_oid", "accepted_sha256",
                            "accepted_byte_count", "successor_sha256",
                            "successor_byte_count", "changed_after_checkpoint",
                            "current_successor_bytes_external_git_anchor_complete"))
                            && relative.equals(actual.path("source").asString())
                            && GIT_COMMIT.equals(actual
                            .path("accepted_git_commit_oid").asString())
                            && expected.acceptedGitBlobOid().equals(actual
                            .path("accepted_git_blob_oid").asString())
                            && expected.acceptedSha256().equals(
                            actual.path("accepted_sha256").asString())
                            && expected.acceptedBytes()
                            == actual.path("accepted_byte_count").asLong()
                            && expected.successorSha256().equals(
                            actual.path("successor_sha256").asString())
                            && expected.successorBytes()
                            == actual.path("successor_byte_count").asLong()
                            && expected.changedAfterCheckpoint()
                            == actual.path("changed_after_checkpoint").asBoolean()
                            && !actual.path(
                            "current_successor_bytes_external_git_anchor_complete")
                            .asBoolean()
                            && expected.changedAfterCheckpoint()
                            == !expected.acceptedSha256().equals(
                            expected.successorSha256()),
                    "Phase6 source-successor anchor descriptor drifted: "
                            + relative);
            Path path = fixedRegularFile(root, relative);
            String physicalSha256 = sha256(path);
            require(physicalSha256.equals(successorSha256(root, relative)),
                    "Phase6 source-successor anchor physical bytes drifted: "
                            + relative);
        }
    }

    private static void validateJavaBoundary(JsonNode boundary, Path root)
            throws IOException {
        require(propertyNames(boundary).equals(Set.of(
                        "hasher_source", "hasher_sha256", "hasher_byte_count",
                        "dockerfile_source", "dockerfile_sha256",
                        "dockerfile_byte_count", "java_build_context_sha256",
                        "worm_source", "worm_sha256", "worm_byte_count",
                        "server_src_main_tree_unchanged_from_parent",
                        "web_tree_unchanged_from_parent", "new_worm_node_required"))
                        && HASHER_RELATIVE.equals(
                        boundary.path("hasher_source").asString())
                        && HASHER_SHA256.equals(
                        boundary.path("hasher_sha256").asString())
                        && boundary.path("hasher_byte_count").asLong()
                        == HASHER_BYTES
                        && DOCKERFILE_RELATIVE.equals(
                        boundary.path("dockerfile_source").asString())
                        && DOCKERFILE_SHA256.equals(
                        boundary.path("dockerfile_sha256").asString())
                        && boundary.path("dockerfile_byte_count").asLong()
                        == DOCKERFILE_BYTES
                        && JAVA_BUILD_CONTEXT_SHA256.equals(boundary
                        .path("java_build_context_sha256").asString())
                        && WORM_RELATIVE.equals(
                        boundary.path("worm_source").asString())
                        && WORM_SHA256.equals(
                        boundary.path("worm_sha256").asString())
                        && boundary.path("worm_byte_count").asLong()
                        == WORM_BYTES
                        && boundary.path(
                        "server_src_main_tree_unchanged_from_parent").asBoolean()
                        && boundary.path(
                        "web_tree_unchanged_from_parent").asBoolean()
                        && !boundary.path("new_worm_node_required").asBoolean(),
                "Phase6 source-successor Java boundary drifted");
        validatePhysical(root, HASHER_RELATIVE, HASHER_SHA256, HASHER_BYTES);
        validatePhysical(
                root, DOCKERFILE_RELATIVE, DOCKERFILE_SHA256, DOCKERFILE_BYTES);
        JsonNode worm = readFixedJson(
                root, WORM_RELATIVE, WORM_SHA256, WORM_BYTES);
        require(JAVA_BUILD_CONTEXT_SHA256.equals(
                        worm.path("java").path("buildContextSha256").asString()),
                "Phase6 source-successor WORM build-context drifted");
    }

    private static void validateAuthority(JsonNode authority, Path root)
            throws IOException {
        require(propertyNames(authority).equals(Set.of(
                        "source", "sha256", "byte_count",
                        "document_payload_sha256", "migrated_operation_count",
                        "pending_operation_count",
                        "production_cutover_operation_count",
                        "legacy_flask_remains_production_owner"))
                        && ROUTE_STATUS_RELATIVE.equals(
                        authority.path("source").asString())
                        && ROUTE_STATUS_SHA256.equals(
                        authority.path("sha256").asString())
                        && authority.path("byte_count").asLong()
                        == ROUTE_STATUS_BYTES
                        && ROUTE_STATUS_PAYLOAD_SHA256.equals(authority
                        .path("document_payload_sha256").asString())
                        && authority.path("migrated_operation_count").asInt() == 13
                        && authority.path("pending_operation_count").asInt() == 598
                        && authority.path(
                        "production_cutover_operation_count").asInt() == 0
                        && authority.path(
                        "legacy_flask_remains_production_owner").asBoolean(),
                "Phase6 source-successor effective authority drifted");
        JsonNode route = readFixedJson(
                root, ROUTE_STATUS_RELATIVE, ROUTE_STATUS_SHA256,
                ROUTE_STATUS_BYTES);
        require(ROUTE_STATUS_PAYLOAD_SHA256.equals(
                        route.path("document_payload_sha256").asString())
                        && ROUTE_STATUS_PAYLOAD_SHA256.equals(payloadSha256(route))
                        && route.path("effective").path("migration_status")
                        .path("migrated").asInt() == 13
                        && route.path("effective").path("migration_status")
                        .path("pending").asInt() == 598
                        && route.path("effective")
                        .path("production_cutover_operation_count").asInt() == 0,
                "Phase6 source-successor route authority drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        require(propertyNames(authorization).equals(Set.of(
                        "current_successor_bytes_external_git_anchor_complete",
                        "gateway_authorized", "operator_authorized",
                        "phase6_complete", "production_cutover",
                        "predecessor_source_successor_checkpoint_"
                                + "external_git_anchor_complete",
                        "real_data_migration_authorized", "route_delta_created",
                        "schema_or_index_change_authorized")),
                "Phase6 source-successor authorization shape drifted");
        for (Map.Entry<String, JsonNode> entry : authorization.properties()) {
            boolean expected = "predecessor_source_successor_checkpoint_"
                    .concat("external_git_anchor_complete")
                    .equals(entry.getKey());
            require(entry.getValue().isBoolean()
                            && entry.getValue().asBoolean() == expected,
                    "Phase6 source-successor authorization drifted: "
                            + entry.getKey());
        }
    }

    private static void validateTrustBoundary(JsonNode trust) {
        require(propertyNames(trust).equals(Set.of(
                        "control_sources", "control_source_count",
                        "control_source_allowlist_exact",
                        "control_sources_excluded_from_self_authority",
                        "control_sources_external_git_anchor_complete",
                        "independently_signed_provenance", "tamper_evident_scope"))
                        && strings(trust.path("control_sources"))
                        .equals(CURRENT_CONTROL_SOURCES)
                        && trust.path("control_source_count").asInt() == 6
                        && trust.path("control_source_allowlist_exact").asBoolean()
                        && trust.path(
                        "control_sources_excluded_from_self_authority").asBoolean()
                        && !trust.path(
                        "control_sources_external_git_anchor_complete").asBoolean()
                        && !trust.path(
                        "independently_signed_provenance").asBoolean()
                        && "fixed_predecessor_commit_tree_delta_blobs_and_"
                        .concat("explicit_successors")
                        .equals(trust.path("tamper_evident_scope").asString())
                        && CURRENT_CONTROL_SOURCES.stream()
                        .noneMatch(SUCCESSORS::containsKey),
                "Phase6 source-successor current trust boundary drifted");
    }

    private static void validateAcceptance(JsonNode acceptance) {
        require(propertyNames(acceptance).equals(Set.of(
                        "checkpoint_changed_path_count",
                        "predecessor_control_source_count",
                        "typed_anchor_bridge_source_count",
                        "source_successor_path_count", "phase6_complete",
                        "migrated_operation_count", "pending_operation_count",
                        "production_cutover_operation_count",
                        "production_cutover"))
                        && acceptance.path(
                        "checkpoint_changed_path_count").asInt() == 11
                        && acceptance.path(
                        "predecessor_control_source_count").asInt() == 6
                        && acceptance.path(
                        "typed_anchor_bridge_source_count").asInt() == 5
                        && acceptance.path(
                        "source_successor_path_count").asInt() == 9
                        && !acceptance.path("phase6_complete").asBoolean()
                        && acceptance.path("migrated_operation_count").asInt()
                        == 13
                        && acceptance.path("pending_operation_count").asInt()
                        == 598
                        && acceptance.path(
                        "production_cutover_operation_count").asInt() == 0
                        && !acceptance.path("production_cutover").asBoolean(),
                "Phase6 source-successor acceptance summary drifted");
    }

    private static JsonNode readFixedJson(
            Path root, String relative, String expectedSha256, long expectedBytes)
            throws IOException {
        Path path = fixedRegularFile(root, relative);
        require(Files.size(path) == expectedBytes
                        && expectedSha256.equals(sha256(path)),
                "Phase6 source-successor fixed bytes drifted: " + relative);
        return JSON.readTree(Files.readAllBytes(path));
    }

    private static void validatePhysical(
            Path root, String relative, String expectedSha256, long expectedBytes)
            throws IOException {
        Path path = fixedRegularFile(root, relative);
        require(Files.size(path) == expectedBytes
                        && expectedSha256.equals(sha256(path)),
                "Phase6 source-successor fixed bytes drifted: " + relative);
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path canonicalRoot = root.toRealPath();
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute(),
                "Phase6 source-successor path escapes root: " + relative);
        Path cursor = canonicalRoot;
        for (Path part : candidate) {
            String value = part.toString();
            require(!value.isEmpty() && !".".equals(value) && !"..".equals(value),
                    "Phase6 source-successor path escapes root: " + relative);
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "Phase6 source-successor path is a symlink: " + relative);
        }
        Path resolved = canonicalRoot.resolve(candidate).toRealPath();
        require(resolved.startsWith(canonicalRoot)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "Phase6 source-successor path is not regular: " + relative);
        return resolved;
    }

    private static Set<String> propertyNames(JsonNode object) {
        Set<String> names = new LinkedHashSet<>();
        object.properties().forEach(entry -> names.add(entry.getKey()));
        return Set.copyOf(names);
    }

    private static List<String> strings(JsonNode values) {
        List<String> result = new ArrayList<>();
        values.forEach(value -> result.add(value.asString()));
        return List.copyOf(result);
    }

    private static String payloadSha256(JsonNode value) {
        ObjectNode copy = (ObjectNode) value.deepCopy();
        copy.remove("document_payload_sha256");
        return sha256(JSON.writeValueAsBytes(canonicalNode(copy)));
    }

    private static JsonNode canonicalNode(JsonNode value) {
        if (value.isObject()) {
            ObjectNode object = JSON.createObjectNode();
            TreeMap<String, JsonNode> sorted = new TreeMap<>();
            value.properties().forEach(entry ->
                    sorted.put(entry.getKey(), canonicalNode(entry.getValue())));
            sorted.forEach(object::set);
            return object;
        }
        if (value.isArray()) {
            ArrayNode array = JSON.createArrayNode();
            value.forEach(item -> array.add(canonicalNode(item)));
            return array;
        }
        return value;
    }

    private static String sha256(Path path) throws IOException {
        return sha256(Files.readAllBytes(path));
    }

    private static String sha256(byte[] value) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private record CheckpointArtifact(
            String changeType,
            String previousGitBlobOid,
            String gitBlobOid,
            String sha256,
            long byteCount,
            String previousMode,
            String mode) {
    }

    private record Successor(
            String acceptedSha256,
            long acceptedBytes,
            String acceptedGitBlobOid,
            String successorSha256,
            long successorBytes,
            boolean changedAfterCheckpoint) {
    }
}
