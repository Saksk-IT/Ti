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
import java.util.List;
import java.util.Map;
import java.util.Set;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ObjectNode;

/** Gitless Java acceptance for the Phase 4C Node B post-push anchor. */
final class Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String CONTRACT_RELATIVE =
            "docs/refactor/phase4c/personal-bank-tag-migration-durable-ledger-"
                    + "freeze-design-post-push-anchor-contract.json";
    private static final String PREDECESSOR_RELATIVE =
            "docs/refactor/phase4c/personal-bank-tag-migration-durable-ledger-"
                    + "freeze-design-contract.json";
    private static final String NODE_A_RELATIVE =
            "docs/refactor/phase4c/personal-bank-tag-migration-global-"
                    + "preflight-post-push-anchor-contract.json";
    private static final String CONTRACT_SHA256 =
            "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6";
    private static final String CONTRACT_PAYLOAD_SHA256 =
            "840d8e06a755fc6c01f5357411023fd875ec5dd87e322608252782b1bbc39542";
    private static final long CONTRACT_BYTE_COUNT = 15_550L;
    private static final String PREDECESSOR_SHA256 =
            "995e964a32d4be1438945024acf9af7f0fb9a9ecfdab7134685e36c4d6a90041";
    private static final String PREDECESSOR_PAYLOAD_SHA256 =
            "fba73f917a285b85cb8fcd7afd22a94f60bac960beb508f173caf0ea96079ffa";
    private static final long PREDECESSOR_BYTE_COUNT = 23_110L;
    private static final String NODE_A_SHA256 =
            "66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3";
    private static final String NODE_A_PAYLOAD_SHA256 =
            "85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e";
    private static final long NODE_A_BYTE_COUNT = 66_318L;
    private static final Map<String, AcceptedSource> ACCEPTED_SOURCES =
            acceptedSources();
    private static final List<String> CURRENT_CONTROL_SOURCES = List.of(
            CONTRACT_RELATIVE,
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationDurableLedgerFreezeDesignPostPush"
                    + "AnchorContractParityTest.java",
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cTagMigrationDurableLedgerFreezeDesignPostPush"
                    + "AnchorSuccessorAcceptance.java",
            "tools/build_phase4c_tag_migration_durable_ledger_freeze_design_"
                    + "post_push_anchor_contract.py",
            "tools/phase4c_tag_migration_durable_ledger_freeze_design_"
                    + "post_push_anchor_successor_acceptance.py",
            "tools/test_phase4c_tag_migration_durable_ledger_freeze_design_"
                    + "post_push_anchor_contract.py");
    private static final List<String> PRODUCTION_FALSE_FIELDS = List.of(
            "migration_design_closed",
            "production_durable_ledger_or_tombstone",
            "production_source_write_freeze_evidence_closed",
            "production_target_write_freeze_evidence_closed",
            "production_membership_write_freeze_or_digest_recheck_evidence_closed",
            "production_connection_drain_evidence_closed",
            "bounded_40001_40P01_retry_implemented",
            "operator_migration_implementation",
            "production_schema_or_index",
            "flyway_baseline_or_migration",
            "backup_and_rollback_evidence_closed",
            "real_data_migration_execution",
            "legacy_runtime_permanently_disabled",
            "route_or_openapi_delta",
            "client_gateway_or_proxy_change",
            "production_cutover");

    private Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance() {
    }

    static JsonNode load(Path root) throws IOException {
        byte[] contractBytes = fixedRegularFile(
                root, CONTRACT_RELATIVE, Set.of(
                        CONTRACT_RELATIVE, PREDECESSOR_RELATIVE,
                        NODE_A_RELATIVE));
        require(contractBytes.length == CONTRACT_BYTE_COUNT
                        && sha256(contractBytes).equals(CONTRACT_SHA256),
                "Node B anchor contract fixed bytes drifted");
        JsonNode contract = JSON.readTree(contractBytes);
        require(contract.isObject(), "Node B anchor contract must be an object");
        require(contract.path("document_payload_sha256").asString()
                        .equals(CONTRACT_PAYLOAD_SHA256)
                        && payloadSha256(contract).equals(CONTRACT_PAYLOAD_SHA256),
                "Node B anchor contract payload identity drifted");
        validatePredecessors(root);
        validateContract(contract);
        return contract;
    }

    static String acceptedSha256(Path root, String relative) throws IOException {
        AcceptedSource accepted = ACCEPTED_SOURCES.get(relative);
        if (accepted == null) {
            return null;
        }
        Path base = root.toRealPath();
        Path candidate = base.resolve(relative).normalize();
        if (!candidate.startsWith(base) || Files.isSymbolicLink(candidate)
                || !Files.isRegularFile(candidate, LinkOption.NOFOLLOW_LINKS)) {
            return null;
        }
        Path resolved = candidate.toRealPath();
        if (!resolved.startsWith(base)) {
            return null;
        }
        byte[] payload = Files.readAllBytes(resolved);
        if (payload.length != accepted.byteCount()
                || !sha256(payload).equals(accepted.sha256())) {
            return null;
        }
        return accepted.sha256();
    }

    static String contractRelative() {
        return CONTRACT_RELATIVE;
    }

    static List<String> currentControlSources() {
        return CURRENT_CONTROL_SOURCES;
    }

    static Map<String, String> acceptedSourceSha256() {
        Map<String, String> result = new LinkedHashMap<>();
        ACCEPTED_SOURCES.forEach((path, source) ->
                result.put(path, source.sha256()));
        return Collections.unmodifiableMap(result);
    }

    static String physicalSha256() {
        return CONTRACT_SHA256;
    }

    static String payloadSha256() {
        return CONTRACT_PAYLOAD_SHA256;
    }

    static long byteCount() {
        return CONTRACT_BYTE_COUNT;
    }

    private static void validatePredecessors(Path root) throws IOException {
        byte[] predecessorBytes = fixedRegularFile(
                root, PREDECESSOR_RELATIVE, Set.of(
                        CONTRACT_RELATIVE, PREDECESSOR_RELATIVE,
                        NODE_A_RELATIVE));
        require(predecessorBytes.length == PREDECESSOR_BYTE_COUNT
                        && sha256(predecessorBytes).equals(PREDECESSOR_SHA256),
                "Node B anchor predecessor physical bytes drifted");
        JsonNode predecessor = JSON.readTree(predecessorBytes);
        require(predecessor.path("document_payload_sha256").asString()
                        .equals(PREDECESSOR_PAYLOAD_SHA256)
                        && payloadSha256(predecessor)
                        .equals(PREDECESSOR_PAYLOAD_SHA256),
                "Node B anchor predecessor payload drifted");
        require(strings(predecessor.path("source_authority")
                        .path("control_sources"))
                        .equals(new ArrayList<>(ACCEPTED_SOURCES.keySet())),
                "Node B anchor predecessor control allowlist drifted");

        byte[] nodeABytes = fixedRegularFile(
                root, NODE_A_RELATIVE, Set.of(
                        CONTRACT_RELATIVE, PREDECESSOR_RELATIVE,
                        NODE_A_RELATIVE));
        require(nodeABytes.length == NODE_A_BYTE_COUNT
                        && sha256(nodeABytes).equals(NODE_A_SHA256),
                "Node B anchor transitive Node A physical bytes drifted");
        JsonNode nodeA = JSON.readTree(nodeABytes);
        require(nodeA.path("document_payload_sha256").asString()
                        .equals(NODE_A_PAYLOAD_SHA256)
                        && payloadSha256(nodeA).equals(NODE_A_PAYLOAD_SHA256),
                "Node B anchor transitive Node A payload drifted");
    }

    private static void validateContract(JsonNode contract) {
        require(contract.path("contract_id").asString().equals(
                        "ti.phase4c.personal-bank-tag-migration-durable-ledger-"
                                + "freeze-design-post-push-anchor-contract")
                        && contract.path("captured_at").asString()
                        .equals("2026-07-19T13:33:45+08:00")
                        && contract.properties().size() == 15,
                "Node B anchor identity drifted");
        JsonNode predecessor = contract.path("predecessor");
        require(predecessor.path("sha256").asString()
                        .equals(PREDECESSOR_SHA256)
                        && predecessor.path("byte_count").asLong()
                        == PREDECESSOR_BYTE_COUNT
                        && predecessor.path("document_payload_sha256").asString()
                        .equals(PREDECESSOR_PAYLOAD_SHA256)
                        && predecessor.path("immutable").asBoolean(),
                "Node B anchor predecessor descriptor drifted");

        JsonNode checkpoint = contract.path("git_checkpoint");
        require(checkpoint.path("commit_oid").asString().equals(
                        "ea894b3a02787a91b688d7295cace37139f7f486")
                        && checkpoint.path("parent_oid").asString().equals(
                        "345deff63d2d3e867926f1e0d05d5e6d90885c4a")
                        && checkpoint.path("root_tree_oid").asString().equals(
                        "57cfc3b195600b38a73e09673267143de346474d")
                        && checkpoint.path("ti_java_tree_oid").asString().equals(
                        "cd5de2cb7f73400cd3d3fe2aa2d7bf48db21a3c8")
                        && checkpoint.path("server_tree_oid").asString().equals(
                        "fd7ccc66962e691eaaadc31e3dad409dbe392273")
                        && checkpoint.path("server_src_main_tree_oid").asString()
                        .equals(checkpoint.path(
                                "parent_server_src_main_tree_oid").asString())
                        && checkpoint.path("web_tree_oid").asString()
                        .equals(checkpoint.path("parent_web_tree_oid").asString())
                        && checkpoint.path("raw_delta_sha256").asString().equals(
                        "a064ee789e91a047a1727deb181f7512408db66e822849e4145d35213ff6abbb")
                        && checkpoint.path("numstat_sha256").asString().equals(
                        "21c2cb87a853bd1d702209f2868dd398b3798e53cdf94f9d3aa13f83cb70de04")
                        && checkpoint.path("changed_path_count").asInt() == 8
                        && checkpoint.path("added_count").asInt() == 8
                        && checkpoint.path("modified_count").asInt() == 0
                        && checkpoint.path("deleted_count").asInt() == 0
                        && checkpoint.path("non_ti_java_count").asInt() == 0
                        && checkpoint.path("inserted_line_count").asInt() == 5_362
                        && checkpoint.path("deleted_line_count").asInt() == 0
                        && checkpoint.path("current_total_bytes").asLong()
                        == 233_639L,
                "Node B anchor checkpoint drifted");
        JsonNode artifacts = checkpoint.path("artifacts");
        require(artifacts.properties().size() == 8,
                "Node B anchor artifact count drifted");
        ACCEPTED_SOURCES.forEach((path, expected) -> {
            JsonNode artifact = artifacts.path(path);
            require(artifact.path("change_type").asString().equals("A")
                            && artifact.path("previous_mode").asString()
                            .equals("000000")
                            && artifact.path("mode").asString().equals("100644")
                            && artifact.path("git_blob_oid").asString()
                            .equals(expected.blobOid())
                            && artifact.path("sha256").asString()
                            .equals(expected.sha256())
                            && artifact.path("byte_count").asLong()
                            == expected.byteCount(),
                    "Node B anchor artifact drifted: " + path);
        });

        JsonNode sourceAnchor = contract.path("node_b_control_source_anchor");
        require(strings(sourceAnchor.path("control_sources"))
                        .equals(new ArrayList<>(ACCEPTED_SOURCES.keySet()))
                        && sourceAnchor.path("control_source_count").asInt() == 8
                        && sourceAnchor.path(
                        "predecessor_control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && sourceAnchor.path(
                        "all_controls_are_exact_commit_delta_blobs").asBoolean()
                        && sourceAnchor.path("all_controls_absent_from_parent")
                        .asBoolean(),
                "Node B control source anchor drifted");
        JsonNode nodeA = contract.path("transitive_node_a_anchor");
        require(nodeA.path("sha256").asString().equals(NODE_A_SHA256)
                        && nodeA.path("document_payload_sha256").asString()
                        .equals(NODE_A_PAYLOAD_SHA256)
                        && nodeA.path("byte_count").asLong() == NODE_A_BYTE_COUNT
                        && nodeA.path("external_anchor_checkpoint_commit_oid")
                        .asString().equals(
                                "345deff63d2d3e867926f1e0d05d5e6d90885c4a")
                        && nodeA.path("external_anchor_artifact_count").asInt() == 6
                        && nodeA.path("immutable").asBoolean(),
                "Node B transitive Node A anchor drifted");

        JsonNode authorization =
                contract.path("inherited_evidence_and_authorization");
        for (String field : List.of(
                "migration_global_preflight_evidence_closed",
                "migration_durable_ledger_freeze_design_evidence_closed",
                "source_successor_external_git_anchor_complete",
                "semantic_successor_external_git_anchor_complete",
                "bootstrap_control_sources_external_git_anchor_complete",
                "node_b_control_sources_external_git_anchor_complete")) {
            require(authorization.path(field).asBoolean(),
                    "Node B inherited true gate drifted: " + field);
        }
        for (String field : PRODUCTION_FALSE_FIELDS) {
            require(!authorization.path(field).asBoolean(),
                    "Node B production boundary drifted: " + field);
        }
        JsonNode route = contract.path("route_state");
        require(route.path("migrated_operation_count").asInt() == 13
                        && route.path("pending_operation_count").asInt() == 598
                        && route.path("production_cutover_operation_count").asInt()
                        == 0
                        && route.path("total_operation_count").asInt() == 611
                        && route.path("legacy_flask_remains_production_owner")
                        .asBoolean(),
                "Node B anchor route drifted");
        JsonNode current = contract.path("current_node_trust_boundary");
        require(strings(current.path("control_sources"))
                        .equals(CURRENT_CONTROL_SOURCES)
                        && current.path("control_source_count").asInt() == 6
                        && current.path("control_sources_excluded_from_self_authority")
                        .asBoolean()
                        && !current.path("control_sources_external_git_anchor_complete")
                        .asBoolean()
                        && !current.path("independently_signed_provenance")
                        .asBoolean(),
                "Node B anchor current self-authority drifted");
        require(contract.path("acceptance")
                        .path("anchor_closes_no_functional_gate").asBoolean(),
                "Node B anchor functional gate boundary drifted");
    }

    private static byte[] fixedRegularFile(
            Path root,
            String relative,
            Set<String> allowlist
    ) throws IOException {
        require(allowlist.contains(relative) && !Path.of(relative).isAbsolute(),
                "Node B anchor Java unknown or absolute source");
        Path base = root.toRealPath();
        Path candidate = base.resolve(relative).normalize();
        require(candidate.startsWith(base) && !Files.isSymbolicLink(candidate)
                        && Files.isRegularFile(
                                candidate, LinkOption.NOFOLLOW_LINKS),
                "Node B anchor Java source escaped, linked or is not regular");
        Path resolved = candidate.toRealPath();
        require(resolved.startsWith(base),
                "Node B anchor Java source escaped root");
        return Files.readAllBytes(resolved);
    }

    private static String payloadSha256(JsonNode document) throws IOException {
        ObjectNode copy = (ObjectNode) document.deepCopy();
        copy.remove("document_payload_sha256");
        return sha256(JSON.writeValueAsString(copy)
                .getBytes(StandardCharsets.UTF_8));
    }

    private static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        array.forEach(value -> result.add(value.asString()));
        return result;
    }

    private static String sha256(byte[] payload) {
        try {
            return HexFormat.of().formatHex(
                    MessageDigest.getInstance("SHA-256").digest(payload));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    private static Map<String, AcceptedSource> acceptedSources() {
        Map<String, AcceptedSource> sources = new LinkedHashMap<>();
        sources.put(
                "docs/refactor/phase4c/personal-bank-tag-migration-durable-"
                        + "ledger-freeze-design-contract.json",
                new AcceptedSource(
                        "6eccdd897ff9b14735e5aa3f91774b7f704f1174",
                        "995e964a32d4be1438945024acf9af7f0fb9a9ecfdab7134685e36c4d6a90041",
                        23_110L));
        sources.put(
                "docs/refactor/phase4c/personal-bank-tag-migration-durable-"
                        + "ledger-freeze-design.md",
                new AcceptedSource(
                        "aee5f4d29cd33249690fed378bcf4ec005e8b230",
                        "8a220b44b9d08cde628e5bb33e599ae58bbbce8adbc6c32961da3b17535d2b4e",
                        9_656L));
        sources.put(
                "server/src/test/java/io/saksk/ti/integration/"
                        + "Phase4cLegacyPersonalBankTagDurableLedgerFreezeDesignIT.java",
                new AcceptedSource(
                        "f0090b18ed3bb9aa3559434444337532cfd96a20",
                        "7131f32bbdd69e61876908fcc6ce5fa6eb87ff682e241d279192f876b1969124",
                        103_360L));
        sources.put(
                "server/src/test/resources/db/phase4c/074-legacy-personal-"
                        + "bank-tag-durable-ledger-freeze-design-schema.sql",
                new AcceptedSource(
                        "57abe91aee7261e46bc7d1ac0c3df62ed210bde2",
                        "544cc31e81b77466ac491192534a8b0e4bab40933d2f71bb39096ea5441a3147",
                        27_251L));
        sources.put(
                "server/src/test/resources/db/phase4c/075-legacy-personal-"
                        + "bank-tag-durable-ledger-freeze-design-seed.sql",
                new AcceptedSource(
                        "16d0c701d5ebdeb9cdfb14f9dc86790beba2ab0a",
                        "6818a460dc1d860dc246df4d5106d398f18b2c2198bafdf297fefdd01b78738c",
                        872L));
        sources.put(
                "tools/build_phase4c_tag_migration_durable_ledger_"
                        + "freeze_design_contract.py",
                new AcceptedSource(
                        "7bd549e10bcea029e4490e0d3bf7067cd2dda884",
                        "5431e95dbbf2107be6174c772f44d18418afb5703362982974c3dfdba6320054",
                        39_397L));
        sources.put(
                "tools/phase4c_tag_migration_durable_ledger_freeze_design_"
                        + "successor_acceptance.py",
                new AcceptedSource(
                        "1ccf0aac9ca8c036dcde517efc8927397b3ef737",
                        "3786c17b48cc1225c66fa5f618e3843430fc283af96e4fcd142dbf64968a527d",
                        9_656L));
        sources.put(
                "tools/test_phase4c_tag_migration_durable_ledger_"
                        + "freeze_design_contract.py",
                new AcceptedSource(
                        "59fe0e9ec082dbc8c931b8e4a415b5cebc793034",
                        "3ba4ee246d266c8a25890acc158640cbaf4405666de2f89837c9bbad9c3a2363",
                        20_337L));
        return Collections.unmodifiableMap(sources);
    }

    private record AcceptedSource(
            String blobOid,
            String sha256,
            long byteCount
    ) {
    }
}
