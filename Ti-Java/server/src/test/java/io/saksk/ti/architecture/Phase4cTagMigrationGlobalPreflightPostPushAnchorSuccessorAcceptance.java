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
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeMap;

/** Gitless Java acceptance for the Phase 4C tag-preflight Node A Git anchor. */
final class Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();

    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/personal-bank-tag-migration-global-"
                    + "preflight-post-push-anchor-contract.json";
    private static final String CONTRACT_ID =
            "ti.phase4c.personal-bank-tag-migration-global-preflight-"
                    + "post-push-anchor-contract";
    private static final String CONTRACT_CAPTURED_AT =
            "2026-07-19T11:15:25+08:00";
    private static final String CONTRACT_STATUS =
            "global_preflight_checkpoint_externally_anchored_"
                    + "migration_design_operator_apply_and_cutover_unauthorized";
    private static final String CONTRACT_SCOPE =
            "phase4c-personal-bank-tag-migration-global-preflight-"
                    + "post-push-external-anchor";
    private static final String CONTRACT_SHA256 =
            "66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e";
    private static final long CONTRACT_BYTES = 66_318L;

    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/personal-bank-tag-migration-global-"
                    + "preflight-contract.json";
    private static final String PREDECESSOR_ID =
            "ti.phase4c.personal-bank-tag-migration-global-preflight-contract";
    private static final String PREDECESSOR_SHA256 =
            "65803c1aacc50592eb04404e1b16d4d139a844022e37198df23453ad61dc598e";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "c7a94e88772a2453743f9821b165ae10f52650a41bf6dab78006d7058951159e";
    private static final long PREDECESSOR_BYTES = 102_931L;

    private static final String SOURCE_MANIFEST_SHA256 =
            "d1ab1bf37de977c934968a6d07cd711b6bec06e1b3bc22bbaa9978d8a3764b4a";
    private static final String SEMANTIC_MANIFEST_SHA256 =
            "1fba3c51e73af84e21b54e6930272dc6cc1c058dbf7ceadaff8d73d1af1698db";
    private static final String FIXED_MANIFEST_SHA256 =
            "ec95c0105bf8f6d5e2c4b1cf3a32178a379b4efa17e1020cf4e320d49f0facbf";

    private static final List<String> CURRENT_CONTROL_SOURCES = List.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightPostPushAnchor"
                    + "SuccessorAcceptance.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationGlobalPreflightPostPushAnchor"
                    + "ContractParityTest.java",
            "tools/build_phase4c_tag_migration_global_preflight_"
                    + "post_push_anchor_contract.py",
            "tools/phase4c_tag_migration_global_preflight_"
                    + "post_push_anchor_successor_acceptance.py",
            "tools/test_phase4c_tag_migration_global_preflight_"
                    + "post_push_anchor_contract.py");

    private Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance() {
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static List<String> currentControlSources() {
        return CURRENT_CONTROL_SOURCES;
    }

    static JsonNode load(Path tiJavaRoot) throws IOException {
        Path root = tiJavaRoot.toRealPath();
        JsonNode contract = readFixedJson(
                root, CONTRACT_RELATIVE, CONTRACT_SHA256, CONTRACT_BYTES);
        require(CONTRACT_PAYLOAD_SHA256.equals(
                        contract.path("document_payload_sha256").asString())
                        && CONTRACT_PAYLOAD_SHA256.equals(payloadSha256(contract)),
                "Node A anchor contract payload drifted");
        validate(contract, root);
        return contract;
    }

    static String acceptedSha256(Path tiJavaRoot, String relative)
            throws IOException {
        JsonNode artifact = load(tiJavaRoot).path("git_checkpoint")
                .path("artifacts").path(relative);
        return artifact.isMissingNode() ? null : artifact.path("sha256").asString();
    }

    private static void validate(JsonNode contract, Path root) throws IOException {
        require(propertyNames(contract).equals(Set.of(
                        "contract_id", "schema_version", "captured_at", "status",
                        "scope", "predecessor", "git_checkpoint",
                        "node_a_authority_anchor", "route_state",
                        "production_and_worm_boundary", "authorization",
                        "current_node_trust_boundary", "acceptance",
                        "document_payload_sha256"))
                        && CONTRACT_ID.equals(contract.path("contract_id").asString())
                        && contract.path("schema_version").asInt() == 1
                        && CONTRACT_CAPTURED_AT.equals(
                        contract.path("captured_at").asString())
                        && CONTRACT_STATUS.equals(contract.path("status").asString())
                        && CONTRACT_SCOPE.equals(contract.path("scope").asString()),
                "Node A anchor contract identity/shape drifted");
        JsonNode predecessor = readFixedJson(
                root, PREDECESSOR_RELATIVE, PREDECESSOR_SHA256,
                PREDECESSOR_BYTES);
        require(PREDECESSOR_ID.equals(
                        predecessor.path("contract_id").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(predecessor
                        .path("document_payload_sha256").asString())
                        && PREDECESSOR_PAYLOAD_SHA256.equals(
                        payloadSha256(predecessor))
                        && PREDECESSOR_RELATIVE.equals(contract.path("predecessor")
                        .path("source").asString())
                        && PREDECESSOR_SHA256.equals(contract.path("predecessor")
                        .path("sha256").asString())
                        && contract.path("predecessor")
                        .path("byte_count").asLong() == PREDECESSOR_BYTES,
                "Node A anchor predecessor drifted");
        validateCheckpoint(contract.path("git_checkpoint"));
        validateAuthority(
                contract.path("node_a_authority_anchor"), predecessor,
                contract.path("git_checkpoint").path("artifacts"));
        validateBoundaries(contract);
    }

    private static void validateCheckpoint(JsonNode checkpoint) {
        JsonNode artifacts = checkpoint.path("artifacts");
        require("256d5b347e2e5266eef084221807337427ceb16f".equals(
                        checkpoint.path("commit_oid").asString())
                        && "08328c3fe18e074f581bb9e782ee4ae86cf46c53".equals(
                        checkpoint.path("parent_oid").asString())
                        && "efcd304e85f597ac22840110630d9fc0ae9a8fb0".equals(
                        checkpoint.path("root_tree_oid").asString())
                        && "e47d851f451fdf045d2c456065ae6913c69229d2".equals(
                        checkpoint.path("ti_java_tree_oid").asString())
                        && "0adfaa0bf6e0edeba2aceebce6c267421e3b8144".equals(
                        checkpoint.path("server_tree_oid").asString())
                        && "21fe4902d57a11998502e63041b5a56fb039a090".equals(
                        checkpoint.path("server_src_main_tree_oid").asString())
                        && "a75f69a8205a56843feb055656ddb015ec5b5215".equals(
                        checkpoint.path("web_tree_oid").asString())
                        && "035e51e17ce5b2596b604e479c244a1b2af711f14940730095a268257209ebcf"
                        .equals(checkpoint.path("raw_delta_sha256").asString())
                        && "8f06547f62f829b0b3c20f7596f0e5879377a76d08b5ee03ff5860f74792c7dd"
                        .equals(checkpoint.path("numstat_sha256").asString())
                        && checkpoint.path("changed_path_count").asInt() == 63
                        && checkpoint.path("added_count").asInt() == 17
                        && checkpoint.path("modified_count").asInt() == 46
                        && checkpoint.path("deleted_count").asInt() == 0
                        && artifacts.isObject() && artifacts.size() == 63
                        && checkpoint.path("exact_sixty_three_path_delta")
                        .asBoolean(),
                "Node A anchor checkpoint drifted");
        artifacts.properties().forEach(entry -> {
            JsonNode value = entry.getValue();
            require(("A".equals(value.path("change_type").asString())
                            || "M".equals(value.path("change_type").asString()))
                            && "blob".equals(value.path("object_type").asString())
                            && entry.getKey().equals(value
                            .path("ti_java_relative_path").asString())
                            && ("Ti-Java/" + entry.getKey()).equals(value
                            .path("repository_path").asString())
                            && value.path("git_blob_oid").asString().length() == 40
                            && value.path("previous_git_blob_oid")
                            .asString().length() == 40
                            && value.path("sha256").asString().length() == 64
                            && value.path("byte_count").asLong() > 0,
                    "Node A anchor artifact drifted: " + entry.getKey());
        });
    }

    private static void validateAuthority(
            JsonNode node, JsonNode predecessor, JsonNode artifacts) {
        JsonNode bridges = predecessor.path("source_successor_bridges");
        JsonNode authority = predecessor.path("source_authority");
        Set<String> transitions = strings(node.path("source_successor_paths"));
        Set<String> semantic = strings(node.path("semantic_consumer_paths"));
        Set<String> fixed = strings(node.path("fixed_source_paths"));
        Set<String> controls = strings(node.path("control_sources"));
        Set<String> delta = propertyNames(artifacts);
        Set<String> changedFixed = new LinkedHashSet<>(delta);
        changedFixed.retainAll(fixed);
        Set<String> partition = new LinkedHashSet<>(controls);
        partition.addAll(changedFixed);
        require(node.path("source_successor_path_count").asInt() == 42
                        && node.path("semantic_consumer_path_count").asInt() == 26
                        && node.path("fixed_source_count").asInt() == 72
                        && node.path("control_source_count").asInt() == 11
                        && transitions.equals(strings(bridges.path("paths")))
                        && semantic.equals(strings(
                        bridges.path("semantic_consumer_paths")))
                        && controls.equals(strings(authority.path("control_sources")))
                        && semantic.size() < transitions.size()
                        && transitions.containsAll(semantic)
                        && changedFixed.containsAll(transitions)
                        && partition.equals(delta)
                        && changedFixed.size() == 52
                        && disjoint(controls, transitions)
                        && disjoint(controls, fixed)
                        && SOURCE_MANIFEST_SHA256.equals(
                        canonicalSha256(bridges.path("overrides")))
                        && FIXED_MANIFEST_SHA256.equals(
                        canonicalSha256(authority.path("fixed_sources")))
                        && SOURCE_MANIFEST_SHA256.equals(node
                        .path("source_successor_manifest_sha256").asString())
                        && SEMANTIC_MANIFEST_SHA256.equals(node
                        .path("semantic_consumer_manifest_sha256").asString())
                        && FIXED_MANIFEST_SHA256.equals(node
                        .path("fixed_source_manifest_sha256").asString()),
                "Node A anchor authority sets drifted");
        JsonNode bytes = node.path("delta_partition");
        require(bytes.path("control_path_count").asInt() == 11
                        && bytes.path("changed_fixed_path_count").asInt() == 52
                        && bytes.path("changed_fixed_modified_count").asInt() == 42
                        && bytes.path("transition_accepted_total_bytes").asLong()
                        == 1_697_108L
                        && bytes.path("transition_current_total_bytes").asLong()
                        == 1_777_881L
                        && bytes.path("semantic_accepted_total_bytes").asLong()
                        == 1_137_011L
                        && bytes.path("semantic_current_total_bytes").asLong()
                        == 1_179_001L
                        && bytes.path("exact_disjoint_partition").asBoolean()
                        && bytes.path("accepted_parent_and_successor_current_"
                        + "bytes_fixed").asBoolean(),
                "Node A anchor authority byte partition drifted");
        for (String relative : transitions) {
            JsonNode artifact = artifacts.path(relative);
            JsonNode override = bridges.path("overrides").path(relative);
            require("M".equals(artifact.path("change_type").asString())
                            && artifact.path("sha256").asString().equals(
                            override.path("successor_sha256").asString())
                            && artifact.path("byte_count").asLong() ==
                            override.path("successor_byte_count").asLong(),
                    "Node A anchor transition drifted: " + relative);
        }
        require(CURRENT_CONTROL_SOURCES.stream().noneMatch(
                        relative -> transitions.contains(relative)
                                || fixed.contains(relative)
                                || controls.contains(relative)),
                "Node A current controls self-authorize");
    }

    private static void validateBoundaries(JsonNode contract) {
        JsonNode route = contract.path("route_state");
        require(route.path("migrated_operation_count").asInt() == 13
                        && route.path("pending_operation_count").asInt() == 598
                        && route.path("production_cutover_operation_count")
                        .asInt() == 0
                        && route.path("legacy_flask_remains_production_owner")
                        .asBoolean(),
                "Node A anchor route boundary drifted");
        JsonNode production = contract.path("production_and_worm_boundary");
        require("93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344"
                        .equals(production.path("terminal_worm_sha256").asString())
                        && "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17"
                        .equals(production.path("java_build_context_sha256")
                                .asString())
                        && production.path("main_addition_count").asInt() == 3
                        && production.path("existing_main_modified_count")
                        .asInt() == 0
                        && production.path("existing_main_deleted_count")
                        .asInt() == 0
                        && production.path("web_tree_unchanged_from_parent")
                        .asBoolean()
                        && !production.path("operator_or_apply_entrypoint_added")
                        .asBoolean(),
                "Node A anchor production/WORM boundary drifted");
        JsonNode authorization = contract.path("authorization");
        require(authorization.path("migration_global_preflight_evidence_closed")
                        .asBoolean()
                        && authorization.path("source_successor_external_git_"
                        + "anchor_complete").asBoolean()
                        && authorization.path("semantic_successor_external_git_"
                        + "anchor_complete").asBoolean()
                        && authorization.path("bootstrap_control_sources_external_"
                        + "git_anchor_complete").asBoolean()
                        && !authorization.path("migration_durable_ledger_freeze_"
                        + "design_evidence_closed").asBoolean()
                        && !authorization.path("migration_design_closed").asBoolean()
                        && !authorization.path("operator_migration_implementation")
                        .asBoolean()
                        && !authorization.path("production_schema_or_index")
                        .asBoolean()
                        && !authorization.path("real_data_migration_execution")
                        .asBoolean()
                        && !authorization.path("production_cutover").asBoolean(),
                "Node A anchor authorization overclaim drifted");
        JsonNode trust = contract.path("current_node_trust_boundary");
        require(listStrings(trust.path("control_sources"))
                        .equals(CURRENT_CONTROL_SOURCES)
                        && trust.path("control_source_count").asInt() == 6
                        && trust.path("control_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !trust.path("control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && !trust.path("independently_signed_provenance").asBoolean(),
                "Node A anchor current trust boundary drifted");
    }

    private static JsonNode readFixedJson(
            Path root, String relative, String expectedSha256, long expectedBytes)
            throws IOException {
        Path path = fixedRegularFile(root, relative);
        require(Files.size(path) == expectedBytes
                        && expectedSha256.equals(sha256(Files.readAllBytes(path))),
                "Node A anchor fixed bytes drifted: " + relative);
        return JSON.readTree(Files.readAllBytes(path));
    }

    private static Path fixedRegularFile(Path root, String relative)
            throws IOException {
        Path canonicalRoot = root.toRealPath();
        Path candidate = Path.of(relative);
        require(!candidate.isAbsolute(),
                "Node A anchor path escapes root: " + relative);
        Path cursor = canonicalRoot;
        for (Path part : candidate) {
            String value = part.toString();
            require(!value.isEmpty() && !".".equals(value) && !"..".equals(value),
                    "Node A anchor path escapes root: " + relative);
            cursor = cursor.resolve(part);
            require(!Files.isSymbolicLink(cursor),
                    "Node A anchor path is a symlink: " + relative);
        }
        Path resolved = canonicalRoot.resolve(candidate).toRealPath();
        require(resolved.startsWith(canonicalRoot)
                        && Files.isRegularFile(resolved, LinkOption.NOFOLLOW_LINKS),
                "Node A anchor path is not regular: " + relative);
        return resolved;
    }

    private static Set<String> propertyNames(JsonNode object) {
        Set<String> names = new LinkedHashSet<>();
        object.properties().forEach(entry -> names.add(entry.getKey()));
        return Set.copyOf(names);
    }

    private static Set<String> strings(JsonNode array) {
        Set<String> result = new LinkedHashSet<>();
        array.forEach(value -> result.add(value.asString()));
        return Set.copyOf(result);
    }

    private static List<String> listStrings(JsonNode array) {
        List<String> result = new java.util.ArrayList<>();
        array.forEach(value -> result.add(value.asString()));
        return List.copyOf(result);
    }

    private static boolean disjoint(Set<String> left, Set<String> right) {
        return left.stream().noneMatch(right::contains);
    }

    private static String payloadSha256(JsonNode value) {
        ObjectNode copy = (ObjectNode) value.deepCopy();
        copy.remove("document_payload_sha256");
        return canonicalSha256(copy);
    }

    private static String canonicalSha256(JsonNode value) {
        return sha256(JSON.writeValueAsBytes(canonicalNode(value)));
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
}
