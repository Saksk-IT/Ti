package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.databind.JsonNode;

/** Cross-language parity for the Phase 4C Node B post-push Git anchor. */
class Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorContractParityTest {

    @Test
    void fixesCanonicalPhysicalAndPayloadIdentity() throws Exception {
        JsonNode contract = contract();

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-tag-migration-durable-ledger-"
                        + "freeze-design-post-push-anchor-contract");
        assertThat(contract.path("captured_at").asString())
                .isEqualTo("2026-07-19T13:33:45+08:00");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                                .payloadSha256());
        assertThat(Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                .physicalSha256()).isEqualTo(
                        "2d65af0c4fd725dceef5d99d2b2dd06804f78f0250f0136a662ca6fb184ccaa6");
        assertThat(Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                .byteCount()).isEqualTo(15_550L);
        assertThat(contract.properties()).hasSize(15);
    }

    @Test
    void fixesUniqueParentTreesAndExactEightAddedPaths() throws Exception {
        JsonNode checkpoint = contract().path("git_checkpoint");

        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo(
                "ea894b3a02787a91b688d7295cace37139f7f486");
        assertThat(checkpoint.path("parent_oid").asString()).isEqualTo(
                "345deff63d2d3e867926f1e0d05d5e6d90885c4a");
        assertThat(checkpoint.path("root_tree_oid").asString()).isEqualTo(
                "57cfc3b195600b38a73e09673267143de346474d");
        assertThat(checkpoint.path("parent_root_tree_oid").asString()).isEqualTo(
                "a59ee94d6cf533555d5d853ef11fa39e7612a22b");
        assertThat(checkpoint.path("ti_java_tree_oid").asString()).isEqualTo(
                "cd5de2cb7f73400cd3d3fe2aa2d7bf48db21a3c8");
        assertThat(checkpoint.path("server_tree_oid").asString()).isEqualTo(
                "fd7ccc66962e691eaaadc31e3dad409dbe392273");
        assertThat(checkpoint.path("server_src_main_tree_oid").asString())
                .isEqualTo(checkpoint.path(
                        "parent_server_src_main_tree_oid").asString());
        assertThat(checkpoint.path("web_tree_oid").asString())
                .isEqualTo(checkpoint.path("parent_web_tree_oid").asString());
        assertThat(checkpoint.path("raw_delta_sha256").asString()).isEqualTo(
                "a064ee789e91a047a1727deb181f7512408db66e822849e4145d35213ff6abbb");
        assertThat(checkpoint.path("numstat_sha256").asString()).isEqualTo(
                "21c2cb87a853bd1d702209f2868dd398b3798e53cdf94f9d3aa13f83cb70de04");
        assertThat(checkpoint.path("changed_path_count").asInt()).isEqualTo(8);
        assertThat(checkpoint.path("added_count").asInt()).isEqualTo(8);
        assertThat(checkpoint.path("modified_count").asInt()).isZero();
        assertThat(checkpoint.path("deleted_count").asInt()).isZero();
        assertThat(checkpoint.path("inserted_line_count").asInt())
                .isEqualTo(5_362);
        assertThat(checkpoint.path("current_total_bytes").asLong())
                .isEqualTo(233_639L);
        assertThat(checkpoint.path("artifacts")).hasSize(8);
    }

    @Test
    void eightCheckpointBlobsExactlyAnchorNodeBControls() throws Exception {
        JsonNode contract = contract();
        JsonNode artifacts = contract.path("git_checkpoint").path("artifacts");
        Map<String, String> accepted =
                Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                        .acceptedSourceSha256();
        List<String> anchoredControls = strings(contract.path(
                "node_b_control_source_anchor").path("control_sources"));

        assertThat(anchoredControls).containsExactlyElementsOf(accepted.keySet());
        assertThat(properties(artifacts)).containsExactlyElementsOf(
                accepted.keySet());
        accepted.forEach((path, sha256) -> {
            JsonNode artifact = artifacts.path(path);
            assertThat(artifact.path("change_type").asString()).as(path)
                    .isEqualTo("A");
            assertThat(artifact.path("previous_mode").asString()).as(path)
                    .isEqualTo("000000");
            assertThat(artifact.path("mode").asString()).as(path)
                    .isEqualTo("100644");
            assertThat(artifact.path("previous_git_blob_oid").asString())
                    .as(path).isEqualTo("0".repeat(40));
            assertThat(artifact.path("sha256").asString()).as(path)
                    .isEqualTo(sha256);
        });
        JsonNode anchor = contract.path("node_b_control_source_anchor");
        assertThat(anchor.path("control_source_path_manifest_sha256").asString())
                .isEqualTo(
                        "752e8f4665e6bab412ee7f19e04c772ee08e7c6ff3f1a57a6eed99955f058a52");
        assertThat(anchor.path("all_controls_absent_from_parent").asBoolean())
                .isTrue();
        assertThat(anchor.path(
                "predecessor_control_sources_external_git_anchor_complete")
                .asBoolean()).isTrue();
        for (Map.Entry<String, String> entry : accepted.entrySet()) {
            assertThat(
                    Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                            .acceptedSha256(root(), entry.getKey()))
                    .as(entry.getKey()).isEqualTo(entry.getValue());
        }
        assertThat(
                Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                        .acceptedSha256(root(), "tools/unknown.py"))
                .isNull();
    }

    @Test
    void retainsNodeAChainAndConservativeProductionBoundary() throws Exception {
        JsonNode contract = contract();
        JsonNode predecessor = contract.path("predecessor");
        JsonNode nodeA = contract.path("transitive_node_a_anchor");

        assertThat(predecessor.path("sha256").asString()).isEqualTo(
                "995e964a32d4be1438945024acf9af7f0fb9a9ecfdab7134685e36c4d6a90041");
        assertThat(predecessor.path("document_payload_sha256").asString())
                .isEqualTo(
                        "fba73f917a285b85cb8fcd7afd22a94f60bac960beb508f173caf0ea96079ffa");
        assertThat(predecessor.path("byte_count").asLong()).isEqualTo(23_110L);
        assertThat(nodeA.path("sha256").asString()).isEqualTo(
                "66394e93b15088c4fbcd3db1dd190306c10b816b504b85e3dca8c89b1c3980d3");
        assertThat(nodeA.path("external_anchor_checkpoint_commit_oid").asString())
                .isEqualTo("345deff63d2d3e867926f1e0d05d5e6d90885c4a");
        assertThat(nodeA.path("external_anchor_artifacts")).hasSize(6);

        JsonNode authorization =
                contract.path("inherited_evidence_and_authorization");
        for (String field : List.of(
                "migration_global_preflight_evidence_closed",
                "migration_durable_ledger_freeze_design_evidence_closed",
                "source_successor_external_git_anchor_complete",
                "semantic_successor_external_git_anchor_complete",
                "bootstrap_control_sources_external_git_anchor_complete",
                "node_b_control_sources_external_git_anchor_complete")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isTrue();
        }
        for (String field : List.of(
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
                "production_cutover")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        JsonNode route = contract.path("route_state");
        assertThat(route.path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(contract.path("acceptance")
                .path("anchor_closes_no_functional_gate").asBoolean()).isTrue();
    }

    @Test
    void sixNewControlsRemainGitlessAndCannotAuthorizeThemselves()
            throws Exception {
        JsonNode contract = contract();
        JsonNode current = contract.path("current_node_trust_boundary");
        List<String> controls = strings(current.path("control_sources"));
        Set<String> anchored = new LinkedHashSet<>(strings(contract.path(
                "node_b_control_source_anchor").path("control_sources")));

        assertThat(controls).containsExactlyElementsOf(
                Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                        .currentControlSources());
        assertThat(controls).doesNotContainAnyElementsOf(anchored);
        assertThat(current.path("control_source_count").asInt()).isEqualTo(6);
        assertThat(current.path("control_sources_excluded_from_self_authority")
                .asBoolean()).isTrue();
        assertThat(current.path("control_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();
        assertThat(current.path("independently_signed_provenance").asBoolean())
                .isFalse();

        String acceptanceSource = Files.readString(root().resolve(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cTagMigrationDurableLedgerFreezeDesignPostPush"
                        + "AnchorSuccessorAcceptance.java"));
        assertThat(acceptanceSource).doesNotContain(
                "ProcessBuilder", "Runtime.getRuntime().exec", "org.eclipse.jgit");
    }

    @Test
    void minimalGitlessFixturePassesAndPhysicalTamperFails(
            @TempDir Path temporary
    ) throws Exception {
        Path fixture = temporary.resolve("Ti-Java");
        Files.createDirectories(fixture);
        for (String relative : List.of(
                Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                        .contractRelative(),
                "docs/refactor/phase4c/personal-bank-tag-migration-durable-"
                        + "ledger-freeze-design-contract.json",
                "docs/refactor/phase4c/personal-bank-tag-migration-global-"
                        + "preflight-post-push-anchor-contract.json")) {
            Path target = fixture.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(relative), target);
        }
        assertThat(temporary.resolve(".git")).doesNotExist();
        Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                .load(fixture);
        Path contract = fixture.resolve(
                Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                        .contractRelative());
        Files.writeString(contract, "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes");
    }

    private static JsonNode contract() throws Exception {
        return Phase4cTagMigrationDurableLedgerFreezeDesignPostPushAnchorSuccessorAcceptance
                .load(root());
    }

    private static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        array.forEach(value -> result.add(value.asString()));
        return result;
    }

    private static List<String> properties(JsonNode object) {
        List<String> result = new ArrayList<>();
        object.properties().forEach(entry -> result.add(entry.getKey()));
        return result;
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }
}
