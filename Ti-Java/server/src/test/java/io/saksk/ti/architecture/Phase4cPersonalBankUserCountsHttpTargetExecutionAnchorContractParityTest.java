package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

/** Java parity gate for the fixed Phase 4C external Git/JUnit anchor. */
class Phase4cPersonalBankUserCountsHttpTargetExecutionAnchorContractParityTest {

    private static final String CONTRACT_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-anchor-contract.json";
    private static final String PREDECESSOR_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-contract.json";
    private static final String MANIFEST_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-target-execution-junit-manifest.json";
    private static final String WORM_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String PYTHON_BRIDGE_PATH =
            "tools/phase4c_http_target_execution_successor_acceptance.py";
    private static final String JAVA_BRIDGE_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java";

    @Test
    void loadsTheFixedAnchorAndItsHonestBootstrapBoundary() throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-anchor-contract");
        assertThat(contract.path("status").asString()).isEqualTo(
                "target_execution_bootstrap_externally_anchored_"
                        + "normalized_junit_manifest_bootstrap_bound_routes_pending");
        assertThat(contract.path("predecessor").path("sha256").asString()).isEqualTo(
                "9f6c37c4217da83199403da8207ed4f89a3999fafd149f069afb520dee4d2460");
        assertThat(contract.path("predecessor").path("immutable").asBoolean()).isTrue();
        assertThat(contract.path("junit_manifest")
                .path("normalized_junit_manifest_bound").asBoolean()).isTrue();
        assertThat(contract.path("junit_manifest")
                .path("manifest_bytes_external_git_anchor_complete").asBoolean()).isFalse();
        assertThat(contract.path("junit_manifest")
                .path("post_push_successor_anchor_required").asBoolean()).isTrue();
    }

    @Test
    void fixesThePushedCommitTreeParentSubtreeAndTenBlobDescriptors() throws Exception {
        JsonNode anchor = contract().path("git_anchor");
        assertThat(anchor.path("object_format").asString()).isEqualTo("sha1");
        assertThat(anchor.path("commit_oid").asString()).isEqualTo(
                "0531b3c9272f9743a374edcf5c8bbeb72643eb1b");
        assertThat(anchor.path("root_tree_oid").asString()).isEqualTo(
                "816e2a7376d147f4a4d1478586cd384edf2c2a8a");
        assertThat(anchor.path("parent_oid").asString()).isEqualTo(
                "67dddb831bac8499e80f4af57c959e9c6b244519");
        assertThat(anchor.path("ti_java_tree_oid").asString()).isEqualTo(
                "1d24e46d33c25170caddf6e25247a7b2945390e4");
        assertThat(anchor.path("artifacts")).hasSize(10);
        assertThat(anchor.path("artifacts").path("python_successor_bridge")
                .path("git_blob_oid").asString()).isEqualTo(
                "8c782bafed4b87abe90fb4f4c1f3510d9b4c7c84");
        assertThat(anchor.path("artifacts").path("java_successor_bridge")
                .path("git_blob_oid").asString()).isEqualTo(
                "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6");
        assertThat(contract().path("external_anchor")
                .path("external_git_and_bridge_bytes_anchor_complete").asBoolean()).isTrue();
    }

    @Test
    void bindsSixtyPassingLeavesWithoutEmbeddingOrExternallyAnchoringTheRawReport()
            throws Exception {
        JsonNode manifest = contract().path("junit_manifest");
        assertThat(manifest.path("sha256").asString()).isEqualTo(
                "64ff60cd56bf60f585af3d55b4ed4b4f7ee30b6a4c9e3e840688a1caaa45664b");
        assertThat(manifest.path("document_payload_sha256").asString()).isEqualTo(
                "9f53234730888c5e3bcd682390093331daca61814c1111c195ea3def4fbe543c");
        assertThat(manifest.path("leaf_payload_sha256").asString()).isEqualTo(
                "77b0f4955931f2ad3206b7a1c0f9c9649b25a18c49bf1b259c452d169e5f0e04");
        assertThat(manifest.path("raw_report_sha256").asString()).isEqualTo(
                "bb114a5571ef645ba37864dae1862a3657d92755a60479d734ce3c72f8de24ab");
        assertThat(manifest.path("raw_report_byte_count").asInt()).isEqualTo(63_450);
        assertThat(manifest.path("tests").asInt()).isEqualTo(60);
        assertThat(manifest.path("passed").asInt()).isEqualTo(60);
        assertThat(manifest.path("failures").asInt()).isZero();
        assertThat(manifest.path("errors").asInt()).isZero();
        assertThat(manifest.path("skipped").asInt()).isZero();
        assertThat(manifest.path("flakes").asInt()).isZero();
        assertThat(manifest.path("raw_report_not_tracked_or_embedded").asBoolean()).isTrue();
        assertThat(manifest.path("independently_signed_provenance").asBoolean()).isFalse();
    }

    @Test
    void reusesTheExactFiveNodeWormAndKeepsEveryMigrationBoundaryClosed()
            throws Exception {
        JsonNode contract = contract();
        JsonNode worm = contract.path("worm_evidence");
        assertThat(worm.path("fixed_chain_node_count").asInt()).isEqualTo(5);
        assertThat(worm.path("canonical_schema_dump_sha256").asString()).isEqualTo(
                "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b");
        assertThat(worm.path("phase2_fixed_acceptance_closed").asBoolean()).isTrue();
        assertThat(worm.path("temporary_privilege").asBoolean()).isFalse();
        assertThat(worm.path("sensitive_information_scan_passed").asBoolean()).isTrue();
        assertThat(worm.path("new_worm").asBoolean()).isFalse();

        JsonNode authorization = contract.path("authorization");
        for (String field : List.of(
                "typed_parity_review_complete",
                "full_target_parity_closed",
                "route_migration_eligible",
                "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated",
                "production_schema_or_index",
                "operator_migration_implementation",
                "real_data_migration_execution",
                "migration_global_preflight_closed",
                "client_change",
                "gateway_or_proxy_change",
                "production_cutover")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        JsonNode acceptance = contract.path("acceptance");
        assertThat(acceptance.path("implemented_pending_get_count").asInt()).isEqualTo(2);
        assertThat(acceptance.path("migrated_operation_count").asInt()).isEqualTo(11);
        assertThat(acceptance.path("pending_operation_count").asInt()).isEqualTo(600);
        assertThat(acceptance.path("production_cutover_operation_count").asInt()).isZero();
    }

    @Test
    void loadsFromAMinimalGitlessCopyWithoutReadingCurrentBridgeBytes(
            @TempDir Path temporary
    ) throws Exception {
        for (String relative : List.of(
                CONTRACT_PATH, PREDECESSOR_PATH, MANIFEST_PATH, WORM_PATH)) {
            Path source = root().resolve(relative);
            Path target = temporary.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(source, target);
        }
        assertThat(temporary.resolve(PYTHON_BRIDGE_PATH)).doesNotExist();
        assertThat(temporary.resolve(JAVA_BRIDGE_PATH)).doesNotExist();
        assertThat(Phase4cHttpTargetExecutionAnchorSuccessorAcceptance.load(temporary)
                .path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-anchor-contract");
    }

    @Test
    void exposesOnlyTheTenHistoricalArtifactHashesAndNeverSelfAuthorizes() {
        assertThat(Phase4cHttpTargetExecutionAnchorSuccessorAcceptance
                .anchoredSha256(PYTHON_BRIDGE_PATH)).isEqualTo(
                "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c");
        assertThat(Phase4cHttpTargetExecutionAnchorSuccessorAcceptance
                .anchoredBlobOid(JAVA_BRIDGE_PATH)).isEqualTo(
                "e9ba94d27cb0ec6a999998518ebeef1b47e4e8f6");
        for (String forbidden : Set.of(
                CONTRACT_PATH,
                "tools/phase4c_http_target_execution_anchor_successor_acceptance.py",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cHttpTargetExecutionAnchorSuccessorAcceptance.java",
                "unknown/self-authorized")) {
            assertThat(Phase4cHttpTargetExecutionAnchorSuccessorAcceptance
                    .anchoredSha256(forbidden)).as(forbidden).isNull();
        }
    }

    @Test
    void rejectsGitDescriptorSelfAuthorizationAndEveryPrematureOverclaim()
            throws Exception {
        JsonNode fixed = contract();
        List<Mutation> mutations = List.of(
                new Mutation("commit", value -> ((ObjectNode) value.path("git_anchor"))
                        .put("commit_oid", "0".repeat(40))),
                new Mutation("tree", value -> ((ObjectNode) value.path("git_anchor"))
                        .put("root_tree_oid", "0".repeat(40))),
                new Mutation("parent", value -> ((ObjectNode) value.path("git_anchor"))
                        .put("parent_oid", "0".repeat(40))),
                new Mutation("blob", value -> ((ObjectNode) value.path("git_anchor")
                        .path("artifacts").path("target_execution_contract"))
                        .put("git_blob_oid", "0".repeat(40))),
                new Mutation("artifact path", value -> ((ObjectNode) value.path("git_anchor")
                        .path("artifacts").path("target_execution_contract"))
                        .put("repository_path", "Ti-Java/unknown")),
                new Mutation("extra artifact", value -> ((ObjectNode) value.path("git_anchor")
                        .path("artifacts")).set("self_authorized", value.path("git_anchor")
                        .path("artifacts").path("target_execution_contract").deepCopy())),
                new Mutation("typed parity", value -> ((ObjectNode) value.path("authorization"))
                        .put("typed_parity_review_complete", true)),
                new Mutation("full parity", value -> ((ObjectNode) value.path("authorization"))
                        .put("full_target_parity_closed", true)),
                new Mutation("route", value -> ((ObjectNode) value.path("authorization"))
                        .put("route_migration_eligible", true)),
                new Mutation("manifest external anchor", value -> ((ObjectNode) value.path(
                        "authorization")).put(
                        "junit_manifest_bytes_external_git_anchor_complete", true)),
                new Mutation("manifest successor gate", value -> ((ObjectNode) value.path(
                        "acceptance")).put(
                        "post_push_junit_manifest_successor_anchor_required", false)),
                new Mutation("cutover", value -> ((ObjectNode) value.path("authorization"))
                        .put("production_cutover", true)));
        for (Mutation mutation : mutations) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase4cHttpTargetExecutionAnchorSuccessorAcceptance.validate(changed))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    private static JsonNode contract() throws Exception {
        return Phase4cHttpTargetExecutionAnchorSuccessorAcceptance.load(root());
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }

    private record Mutation(String label, MutationAction action) {
    }

    @FunctionalInterface
    private interface MutationAction {
        void apply(JsonNode value);
    }
}
