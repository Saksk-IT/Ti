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
 * Gitless Java acceptance for the fixed Phase 6 Web-foundation source
 * successor. Git replay remains Python-owned; this acceptance independently
 * fixes the bootstrap contract, the three delegated document transitions,
 * route authority, and the unchanged Java build-context boundary.
 */
final class Phase6WebFoundationSourceSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase6/web-foundation-source-successor-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase6.web-foundation-source-successor-contract";
    private static final String CONTRACT_STATUS =
            "bootstrap_complete_external_git_anchor_pending";
    private static final String CONTRACT_SCOPE =
            "phase6-web-foundation-source-successor";
    private static final String CONTRACT_CAPTURED_AT =
            "2026-07-19T01:20:00+08:00";
    private static final String CONTRACT_SHA256 =
            "be652b57cf9e024effbd62d5eb5f438931c4db3c8126e8318e2af077236e4073";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "93e2eccb5bd3cdcc95addac0d09bef26d25ae3676c1ffd1b9c10c337c1b1b693";
    private static final long CONTRACT_BYTES = 7_335L;

    private static final String TYPED_ANCHOR_RELATIVE =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-typed-normalization-"
                    + "anchor-contract.json";
    private static final String TYPED_ANCHOR_SHA256 =
            "c713aa04a82f340ea04fdd5ae870bd5cfae82f099101431c664f047c2d5218ca";
    private static final String TYPED_ANCHOR_PAYLOAD_SHA256 =
            "430ef24103006265001ecd1f2f6aa5e4b24a886e82fcc1391cc516eba5dbde7c";
    private static final long TYPED_ANCHOR_BYTES = 43_737L;

    private static final String PHASE6_ACCEPTANCE_RELATIVE =
            "docs/refactor/phase6/web-foundation-acceptance.json";
    private static final String PHASE6_ACCEPTANCE_SHA256 =
            "6289e15ec68a332566539df46e5b7b3143c3c58ed9c60b35c2d736ed762d8e1f";
    private static final long PHASE6_ACCEPTANCE_BYTES = 4_932L;
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
            "c563ac655077e69306c34d163f63a4da50569e01";
    private static final String GIT_PARENT =
            "bd2ed3946487d27abffc81d966e7adfaab1fe433";
    private static final String GIT_ROOT_TREE =
            "37c0029466f358795c58c5418573fa11ef57bcc6";
    private static final String GIT_TI_JAVA_TREE =
            "f5d5c5f8248213863730e0355780b12512203696";
    private static final String GIT_WEB_TREE =
            "a75f69a8205a56843feb055656ddb015ec5b5215";
    private static final String GIT_SERVER_TREE =
            "57cda4d266fd1416853a6996e395c0fb2fb353eb";
    private static final String GIT_RAW_DELTA_SHA256 =
            "7c1621f8e44520ccb0f04a5250cd7003b5d5a8a0d5cf0db35549a10b6fa4ffd4";

    private static final Map<String, Successor> SUCCESSORS = Map.ofEntries(
            Map.entry("README.md", new Successor(
                    "524f03e89122b4d8a9af4ed805596a3b315a4859dac2777b0ab989ac25e82b47",
                    38_265L,
                    "a18ef8e66e1213b4e7ab47e20fb63278c264ba4e",
                    "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
                    40_323L,
                    true)),
            Map.entry("docs/refactor/05-progress.md", new Successor(
                    "62ff84e2cc3b525855f0a0eb07a1820c231ad50864956329d0da08a3d86b697c",
                    103_256L,
                    "74974ed6ca408e90846ab90b90e965d8fc9faa5b",
                    "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
                    105_423L,
                    true)),
            Map.entry("docs/refactor/phase4c/README.md", new Successor(
                    "dd0f41f78466636d09d3afa7669e507814aa78a04cb94d62bf7e96596c18e85a",
                    19_511L,
                    "8659b84a26ea0b7182c4e375bcb1a1ee185e58b6",
                    "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
                    23_309L,
                    false)));

    private static final List<String> SOURCE_PATHS = List.of(
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md");

    private static final List<String> CONTROL_SOURCES = List.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java",
            "tools/build_phase6_web_foundation_source_successor_contract.py",
            "tools/phase6_web_foundation_source_successor_acceptance.py",
            "tools/test_phase6_web_foundation_source_successor_contract.py");

    private Phase6WebFoundationSourceSuccessorAcceptance() {
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static String acceptedHash(String relative) {
        Successor successor = SUCCESSORS.get(relative);
        return successor == null ? null : successor.acceptedSha256();
    }

    static Set<String> successorPaths() {
        return SUCCESSORS.keySet();
    }

    static String successorHash(Path tiJavaRoot, String relative)
            throws IOException {
        Successor successor = SUCCESSORS.get(relative);
        if (successor == null) {
            return null;
        }
        Path root = tiJavaRoot.toRealPath();
        Path path = fixedRegularFile(root, relative);
        String physical = sha256(path);
        if (Files.size(path) == successor.successorBytes()
                && successor.successorSha256().equals(physical)) {
            return physical;
        }
        require(successor.successorSha256().equals(
                        Phase6WebFoundationSourceSuccessorAnchorAcceptance
                                .acceptedHash(relative)),
                "Phase6 source-successor anchor rejected bootstrap hash: "
                        + relative);
        require(physical.equals(
                        Phase6WebFoundationSourceSuccessorAnchorAcceptance
                                .successorHash(root, relative)),
                "Phase6 source-successor anchor did not bind current bytes: "
                        + relative);
        return physical;
    }

    static Set<String> minimalFixturePaths() {
        Set<String> paths = new LinkedHashSet<>();
        paths.add(CONTRACT_RELATIVE);
        paths.add(TYPED_ANCHOR_RELATIVE);
        paths.add(PHASE6_ACCEPTANCE_RELATIVE);
        paths.add(ROUTE_STATUS_RELATIVE);
        paths.add(HASHER_RELATIVE);
        paths.add(DOCKERFILE_RELATIVE);
        paths.add(WORM_RELATIVE);
        paths.addAll(SOURCE_PATHS);
        paths.addAll(Phase6WebFoundationSourceSuccessorAnchorAcceptance
                .minimalFixturePaths());
        return Set.copyOf(paths);
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = validateContractPhysicalBytes(root);
        validate(contract, root);
        Phase6WebFoundationSourceSuccessorAnchorAcceptance.load(root);
        return contract;
    }

    static void validate(JsonNode contract, Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status",
                        "scope", "predecessor_typed_anchor", "git_checkpoint",
                        "phase6_foundation", "typed_anchor_delegation",
                        "source_successors", "java_build_context_boundary",
                        "effective_authority", "authorization",
                        "current_node_trust_boundary", "document_payload_sha256")),
                "Phase6 source-successor contract shape drifted");
        require(CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && contract.path("schema_version").asInt() == 1
                        && CONTRACT_CAPTURED_AT.equals(
                        contract.path("captured_at").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "Phase6 source-successor identity drifted");

        validatePredecessor(contract.path("predecessor_typed_anchor"), root);
        validateCheckpoint(contract.path("git_checkpoint"));
        validateFoundation(contract.path("phase6_foundation"), root);
        validateDelegation(contract.path("typed_anchor_delegation"));
        validateSuccessors(contract.path("source_successors"), root);
        validateJavaBoundary(contract.path("java_build_context_boundary"), root);
        validateAuthority(contract.path("effective_authority"), root);
        validateAuthorization(contract.path("authorization"));
        validateTrustBoundary(contract.path("current_node_trust_boundary"));
    }

    private static JsonNode validateContractPhysicalBytes(Path root)
            throws IOException {
        Path path = fixedRegularFile(root, CONTRACT_RELATIVE);
        require(Files.size(path) == CONTRACT_BYTES
                        && CONTRACT_SHA256.equals(sha256(path)),
                "Phase6 source-successor contract physical bytes drifted");
        JsonNode contract = JSON.readTree(Files.readAllBytes(path));
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "Phase6 source-successor contract payload drifted");
        return contract;
    }

    private static void validatePredecessor(JsonNode predecessor, Path root)
            throws IOException {
        require(TYPED_ANCHOR_RELATIVE.equals(
                        predecessor.path("source").asString())
                        && TYPED_ANCHOR_SHA256.equals(
                        predecessor.path("sha256").asString())
                        && predecessor.path("byte_count").asLong()
                        == TYPED_ANCHOR_BYTES
                        && TYPED_ANCHOR_PAYLOAD_SHA256.equals(predecessor
                        .path("document_payload_sha256").asString())
                        && predecessor.path("immutable").asBoolean(),
                "Phase6 typed-anchor predecessor descriptor drifted");
        JsonNode typed = readFixedJson(
                root, TYPED_ANCHOR_RELATIVE, TYPED_ANCHOR_SHA256,
                TYPED_ANCHOR_BYTES);
        require("ti.phase4c.personal-bank-user-counts-http-typed-"
                        .concat("normalization-anchor-contract")
                        .equals(typed.path("contract_id").asString())
                        && TYPED_ANCHOR_PAYLOAD_SHA256.equals(
                        typed.path("document_payload_sha256").asString())
                        && TYPED_ANCHOR_PAYLOAD_SHA256.equals(payloadSha256(typed)),
                "Phase6 typed-anchor predecessor payload drifted");
    }

    private static void validateCheckpoint(JsonNode checkpoint) {
        require("sha1".equals(checkpoint.path("object_format").asString())
                        && GIT_COMMIT.equals(
                        checkpoint.path("commit_oid").asString())
                        && GIT_PARENT.equals(
                        checkpoint.path("parent_oid").asString())
                        && GIT_ROOT_TREE.equals(
                        checkpoint.path("root_tree_oid").asString())
                        && GIT_TI_JAVA_TREE.equals(
                        checkpoint.path("ti_java_tree_oid").asString())
                        && GIT_WEB_TREE.equals(
                        checkpoint.path("web_tree_oid").asString())
                        && GIT_SERVER_TREE.equals(
                        checkpoint.path("server_tree_oid").asString())
                        && GIT_SERVER_TREE.equals(
                        checkpoint.path("parent_server_tree_oid").asString())
                        && GIT_RAW_DELTA_SHA256.equals(
                        checkpoint.path("raw_delta_sha256").asString())
                        && checkpoint.path("changed_path_count").asInt() == 107
                        && checkpoint.path("web_changed_path_count").asInt() == 102
                        && checkpoint.path("exact_raw_delta_fixed").asBoolean(),
                "Phase6 fixed Git checkpoint descriptor drifted");
    }

    private static void validateFoundation(JsonNode foundation, Path root)
            throws IOException {
        require(PHASE6_ACCEPTANCE_RELATIVE.equals(
                        foundation.path("source").asString())
                        && PHASE6_ACCEPTANCE_SHA256.equals(
                        foundation.path("sha256").asString())
                        && foundation.path("byte_count").asLong()
                        == PHASE6_ACCEPTANCE_BYTES
                        && "phase6-web-foundation-acceptance-v1".equals(
                        foundation.path("contract_id").asString())
                        && foundation.path("foundation_complete").asBoolean()
                        && !foundation.path("phase6_complete").asBoolean()
                        && foundation.path("web_file_count").asInt() == 102
                        && foundation.path("web_byte_count").asLong() == 558_898L,
                "Phase6 foundation descriptor drifted");
        JsonNode phase6 = readFixedJson(
                root, PHASE6_ACCEPTANCE_RELATIVE, PHASE6_ACCEPTANCE_SHA256,
                PHASE6_ACCEPTANCE_BYTES);
        require("phase6-web-foundation-acceptance-v1".equals(
                        phase6.path("contract_id").asString())
                        && phase6.path("phase6_disposition")
                        .path("foundation_complete").asBoolean()
                        && !phase6.path("phase6_disposition")
                        .path("phase6_complete").asBoolean()
                        && phase6.path("web_content").path("file_count").asInt()
                        == 102
                        && phase6.path("web_content").path("byte_count").asLong()
                        == 558_898L,
                "Phase6 foundation evidence drifted");
    }

    private static void validateDelegation(JsonNode delegation) {
        require(strings(delegation.path("delegated_paths")).equals(SOURCE_PATHS)
                        && delegation.path("delegated_path_count").asInt() == 3
                        && delegation.path("delegation_allowlist_exact").asBoolean()
                        && delegation.path(
                        "dynamic_source_discovery_forbidden").asBoolean()
                        && delegation.path("unknown_path_rejected").asBoolean(),
                "Phase6 source-successor delegation drifted");
    }

    private static void validateSuccessors(JsonNode sourceSuccessors, Path root)
            throws IOException {
        require(strings(sourceSuccessors.path("paths")).equals(SOURCE_PATHS)
                        && sourceSuccessors.path("path_count").asInt() == 3,
                "Phase6 source-successor allowlist drifted");
        JsonNode overrides = sourceSuccessors.path("overrides");
        require(propertyNames(overrides).equals(SUCCESSORS.keySet()),
                "Phase6 source-successor override set drifted");
        for (Map.Entry<String, Successor> entry : SUCCESSORS.entrySet()) {
            String relative = entry.getKey();
            Successor expected = entry.getValue();
            JsonNode actual = overrides.path(relative);
            require(propertyNames(actual).equals(Set.of(
                            "accepted_sha256", "accepted_byte_count",
                            "successor_git_blob_oid", "successor_sha256",
                            "successor_byte_count",
                            "transition_is_direct_parent_delta",
                            "successor_snapshot_fixed_by_checkpoint_tree"))
                            && expected.acceptedSha256().equals(
                            actual.path("accepted_sha256").asString())
                            && expected.acceptedBytes()
                            == actual.path("accepted_byte_count").asLong()
                            && expected.successorGitBlobOid().equals(
                            actual.path("successor_git_blob_oid").asString())
                            && expected.successorSha256().equals(
                            actual.path("successor_sha256").asString())
                            && expected.successorBytes()
                            == actual.path("successor_byte_count").asLong()
                            && expected.directParentDelta()
                            == actual.path("transition_is_direct_parent_delta")
                            .asBoolean()
                            && actual.path(
                            "successor_snapshot_fixed_by_checkpoint_tree")
                            .asBoolean(),
                    "Phase6 source-successor descriptor drifted: " + relative);
            require(successorHash(root, relative) != null,
                    "Phase6 source-successor physical bytes drifted: " + relative);
        }
    }

    private static void validateJavaBoundary(JsonNode boundary, Path root)
            throws IOException {
        require(HASHER_RELATIVE.equals(
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
                        && !boundary.path("web_in_java_build_context").asBoolean()
                        && boundary.path(
                        "server_tree_unchanged_from_parent").asBoolean()
                        && !boundary.path("new_worm_node_required").asBoolean()
                        && WORM_RELATIVE.equals(
                        boundary.path("worm_source").asString())
                        && WORM_SHA256.equals(
                        boundary.path("worm_sha256").asString())
                        && boundary.path("worm_byte_count").asLong()
                        == WORM_BYTES,
                "Phase6 Java build-context boundary drifted");
        validatePhysical(root, HASHER_RELATIVE, HASHER_SHA256, HASHER_BYTES);
        validatePhysical(
                root, DOCKERFILE_RELATIVE, DOCKERFILE_SHA256, DOCKERFILE_BYTES);
        JsonNode worm = readFixedJson(
                root, WORM_RELATIVE, WORM_SHA256, WORM_BYTES);
        require(JAVA_BUILD_CONTEXT_SHA256.equals(
                        worm.path("java").path("buildContextSha256").asString()),
                "Phase6 WORM build-context boundary drifted");
    }

    private static void validateAuthority(JsonNode authority, Path root)
            throws IOException {
        require(ROUTE_STATUS_RELATIVE.equals(
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
                "Phase6 effective authority descriptor drifted");
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
                "Phase6 effective route authority drifted");
    }

    private static void validateAuthorization(JsonNode authorization) {
        require(propertyNames(authorization).equals(Set.of(
                        "gateway_authorized", "operator_authorized",
                        "production_cutover", "real_data_migration_authorized",
                        "route_delta_created",
                        "schema_or_index_change_authorized")),
                "Phase6 authorization shape drifted");
        for (Map.Entry<String, JsonNode> entry : authorization.properties()) {
            require(entry.getValue().isBoolean()
                            && !entry.getValue().asBoolean(),
                    "Phase6 source-successor overclaims " + entry.getKey());
        }
    }

    private static void validateTrustBoundary(JsonNode trust) {
        require(strings(trust.path("control_sources")).equals(CONTROL_SOURCES)
                        && trust.path("control_source_count").asInt() == 6
                        && trust.path("control_source_allowlist_exact").asBoolean()
                        && trust.path(
                        "control_sources_excluded_from_self_authority").asBoolean()
                        && !trust.path(
                        "control_sources_external_git_anchor_complete").asBoolean()
                        && !trust.path(
                        "independently_signed_provenance").asBoolean()
                        && "fixed_post_push_external_git_anchor".equals(
                        trust.path("next_gate").asString()),
                "Phase6 source-successor trust boundary drifted");
    }

    private static JsonNode readFixedJson(
            Path root, String relative, String expectedSha256, long expectedBytes)
            throws IOException {
        Path path = fixedRegularFile(root, relative);
        require(Files.size(path) == expectedBytes
                        && expectedSha256.equals(sha256(path)),
                "Phase6 fixed bytes drifted: " + relative);
        return JSON.readTree(Files.readAllBytes(path));
    }

    private static void validatePhysical(
            Path root, String relative, String expectedSha256, long expectedBytes)
            throws IOException {
        Path path = fixedRegularFile(root, relative);
        require(Files.size(path) == expectedBytes
                        && expectedSha256.equals(sha256(path)),
                "Phase6 fixed bytes drifted: " + relative);
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path canonicalRoot = root.toRealPath();
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute(),
                "Phase6 source path escapes root: " + relative);
        Path cursor = canonicalRoot;
        for (Path part : candidate) {
            String value = part.toString();
            require(!value.isEmpty() && !".".equals(value) && !"..".equals(value),
                    "Phase6 source path escapes root: " + relative);
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "Phase6 source path is a symlink: " + relative);
        }
        Path resolved = canonicalRoot.resolve(candidate).toRealPath();
        require(resolved.startsWith(canonicalRoot)
                        && Files.isRegularFile(
                        resolved, LinkOption.NOFOLLOW_LINKS),
                "Phase6 source path is not regular: " + relative);
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

    private record Successor(
            String acceptedSha256,
            long acceptedBytes,
            String successorGitBlobOid,
            String successorSha256,
            long successorBytes,
            boolean directParentDelta) {
    }
}
