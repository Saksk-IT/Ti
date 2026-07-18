package io.saksk.ti.architecture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

/** Java parity gate for the fixed Phase 4C target-execution post-push handoff. */
class Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushContractParityTest {

    private static final String CONTRACT_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-contract.json";
    private static final String PREDECESSOR_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-anchor-contract.json";
    private static final String MANIFEST_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-target-execution-junit-manifest.json";
    private static final String WORM_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String POST_PUSH_ACCEPTANCE_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java";
    private static final String POST_PUSH_PARITY_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPush"
                    + "ContractParityTest.java";
    private static final String POST_PUSH_ANCHOR_CONTRACT_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "anchor-contract.json";
    private static final String OLD_TARGET_BRIDGE_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionSuccessorAcceptance.java";

    private static final Map<String, HashPair> SUCCESSORS = Map.ofEntries(
            successor(
                    "README.md",
                    "321d23e47d0df0714ea632b2c8c1d3d05d0e67bf69d53e3a52e387e4a949bda4",
                    "9008df17aa8eba4945fde525a304c4d891da20004f18ab86ceda485fffab2b57"),
            successor(
                    "docs/refactor/05-progress.md",
                    "e2363a603e9b82368185b6fef3e9882a3e586ce5b5eca14a8b5cddcbca7d6faf",
                    "477d2dc0fce4946e511faa2c143fc76367ae6231a932ae204b6858ca5787e1bf"),
            successor(
                    "docs/refactor/phase4c/README.md",
                    "f43ae7ca31038fcc45a05874cfc5c8a460edfe2833936bf4418f37706771d472",
                    "50f1ee46eddac681b49281c3b348e4017fe6893ec38051a5485317cd766c2f61"),
            successor(
                    "infra/phase2/README.md",
                    "55f9d05fa583e581d6a5b92ec4f1e3e53690a40b5087da456a84ef996b4d3f7b",
                    "7ae3e8a5bb36920039649ffa8a2aef2bd9bb59782fa03f50e4174cee9063b56f"),
            successor(
                    "infra/phase2/verify-static.sh",
                    "eb01988f26a56293338a7bcd8bc83487b2d8cd0c1c081ae75272bc73dfa28a94",
                    "92a3a1ee30ddbb2b5c854dbff7fac23da37e5804e0628211e85725ba4523d835"),
            successor(
                    OLD_TARGET_BRIDGE_PATH,
                    "76c2c4ef54061f85339ad8f5cb1f1bab21d2f71b7bbcf8fde44cdd4d563cdf15",
                    "945ddfd83ed4f8e0be4db02b1bd58abf74450eaf8996a92a12554ab8b81da578"),
            successor(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_contract.py",
                    "51d3c9bf425319e7a0cd7a49e7244f058e09f14ac363f9278000192cb4a69d3b",
                    "8f729d39a528cf0c5acb93802e9f6d830d8fc79bc80421c2a80d37a6ead58209"),
            successor(
                    "tools/phase2_wormhole_successor_acceptance.py",
                    "f3a56bd684b508f69bc387d741f1c0277d0c4a7f4130aec984fd359fa8dc0f3a",
                    "868d5cebbcc695136083ac892e572483ffc40829f487cb8d9d2b407c2fc763d1"),
            successor(
                    "tools/phase4c_http_target_execution_successor_acceptance.py",
                    "891e4c7c48c76b76697b064e8e6fd55f5cb549b751a7bff3562868f62d76c75c",
                    "95e00e9d136e212cbcb5501d2abae46b9679bb2412d07ba6fcf79cbb9dd4de1a"),
            successor(
                    "tools/test_phase2_wormhole_successor_acceptance.py",
                    "ce70d5f35c7725d0f93f27619c5828f294ac259fc20f8594a3ac71b5f5f6f72d",
                    "691198f36292c460b6bb516e9deb4e4efe064ae12fe60efb85280a52753cb5cb"));

    private static final Set<String> POST_PUSH_ANCHOR_SUCCESSOR_PATHS = Set.of(
            "README.md",
            "docs/refactor/05-progress.md",
            "docs/refactor/phase4c/README.md",
            "infra/phase2/README.md",
            "infra/phase2/verify-static.sh",
            POST_PUSH_ACCEPTANCE_PATH,
            POST_PUSH_PARITY_PATH,
            "tools/build_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py",
            "tools/phase2_wormhole_successor_acceptance.py",
            "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
            "tools/test_phase2_wormhole_successor_acceptance.py",
            "tools/test_phase4c_personal_bank_user_counts_http_"
                    + "target_execution_post_push_contract.py");

    @Test
    void loadsTheFixedCheckedInContractAndExactCheckpoint() throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-post-push-contract");
        assertThat(contract.path("document_payload_sha256").asString()).isEqualTo(
                "c2382550719d97e74f93db97bf74e70e246cca1e35ac6cc9c6c9e8d13b964dba");
        JsonNode checkpoint = contract.path("git_checkpoint");
        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo(
                "6c1b03dd7fa9cde7a6dcdbf6b555452e9a6d9e53");
        assertThat(checkpoint.path("root_tree_oid").asString()).isEqualTo(
                "47a1df74676ff2838bec7d01f371787720aea559");
        assertThat(checkpoint.path("parent_oid").asString()).isEqualTo(
                "0531b3c9272f9743a374edcf5c8bbeb72643eb1b");
        assertThat(checkpoint.path("ti_java_tree_oid").asString()).isEqualTo(
                "7c0e65fa52ffa95567b0d7e266bd4e590af22f5a");
        assertThat(checkpoint.path("artifacts")).hasSize(9);
        assertThat(checkpoint.path("diff").path("exact_add_only_delta").asBoolean())
                .isTrue();
        assertThat(checkpoint.path("diff").path("added_total_bytes").asLong())
                .isEqualTo(222_675);
    }

    @Test
    void exposesOnlyTheExactTenHistoricalToSuccessorTransitions() throws Exception {
        assertThat(contract().path("historical_source_successors")
                .path("successor_allowlist")).hasSize(10);
        for (Map.Entry<String, HashPair> entry : SUCCESSORS.entrySet()) {
            assertThat(Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                    .acceptedHash(entry.getKey())).as(entry.getKey())
                    .isEqualTo(entry.getValue().accepted());
            String expectedSuccessor =
                    Phase4cHttpTypedNormalizationSuccessorAcceptance
                            .acceptedHash(entry.getKey()) == null
                    ? entry.getValue().successor()
                    : Phase4cHttpTypedNormalizationSuccessorAcceptance
                            .successorHash(root(), entry.getKey());
            assertThat(Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                    .successorHash(root(), entry.getKey())).as(entry.getKey())
                    .isEqualTo(expectedSuccessor);
        }
        for (String forbidden : Set.of(
                CONTRACT_PATH,
                POST_PUSH_ACCEPTANCE_PATH,
                POST_PUSH_PARITY_PATH,
                "tools/build_phase4c_personal_bank_user_counts_http_"
                        + "target_execution_post_push_contract.py",
                "tools/phase4c_http_target_execution_post_push_successor_acceptance.py",
                "tools/test_phase4c_personal_bank_user_counts_http_"
                        + "target_execution_post_push_contract.py",
                "unknown/self-authorized")) {
            assertThat(Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                    .acceptedHash(forbidden)).as(forbidden).isNull();
            assertThat(Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                    .successorHash(root(), forbidden)).as(forbidden).isNull();
        }
    }

    @Test
    void handsTheExactTransitionBackToTheHistoricalTargetBridge() throws Exception {
        JsonNode historical = Phase4cHttpTargetExecutionSuccessorAcceptance.load(root());
        assertThat(historical.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-contract");
        assertThat(Phase4cHttpTargetExecutionSuccessorAcceptance
                .successorHash(root(), "README.md")).isEqualTo(
                Phase4cHttpTypedNormalizationSuccessorAcceptance
                        .successorHash(root(), "README.md"));
        assertThat(Phase4cHttpTargetExecutionSuccessorAcceptance
                .successorHash(root(), "unknown/source")).isNull();
        assertThat(Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                .acceptedHash(POST_PUSH_PARITY_PATH)).isEqualTo(
                "5805a4517e02ec23af94546e551d4d3994aaed5667fc680f5b603d81e95f9304");
        assertThat(Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                .successorHash(root(), POST_PUSH_PARITY_PATH)).isNotNull();
    }

    @Test
    void anchorsManifestAndFifthWormWithoutPromotingRoutesOrParity() throws Exception {
        JsonNode contract = contract();
        JsonNode junit = contract.path("junit_execution");
        assertThat(junit.path("total_leaf_count").asInt()).isEqualTo(60);
        assertThat(junit.path("manifest_blob_external_git_anchor_complete").asBoolean())
                .isTrue();
        assertThat(junit.path("historical_manifest_document_rewritten").asBoolean())
                .isFalse();
        JsonNode worm = contract.path("worm_evidence");
        assertThat(worm.path("fixed_chain_node_count").asInt()).isEqualTo(5);
        assertThat(worm.path("reused").asBoolean()).isTrue();
        assertThat(worm.path("new_worm_report_created").asBoolean()).isFalse();

        JsonNode authorization = contract.path("authorization");
        for (String field : List.of(
                "typed_parity_review_complete", "full_target_parity_closed",
                "route_migration_eligible", "two_legacy_get_routes_migrated",
                "derived_head_and_options_count_as_migrated", "production_cutover")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
        JsonNode acceptance = contract.path("acceptance");
        assertThat(acceptance.path("implemented_pending_get_count").asInt()).isEqualTo(2);
        assertThat(acceptance.path("migrated_operation_count").asInt()).isEqualTo(11);
        assertThat(acceptance.path("pending_operation_count").asInt()).isEqualTo(600);
        assertThat(acceptance.path("production_cutover_operation_count").asInt()).isZero();
    }

    @Test
    void loadsFromAMinimalGitlessCopyWithoutHistoricalValidators(@TempDir Path temporary)
            throws Exception {
        copyMinimalFixture(temporary);
        assertThat(temporary.resolve(".git")).doesNotExist();
        assertThat(temporary.resolve(
                "tools/phase4c_http_target_execution_anchor_successor_acceptance.py"))
                .doesNotExist();
        assertThat(temporary.resolve(
                "tools/phase4c_http_target_execution_successor_acceptance.py"))
                .exists();
        assertThat(Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.load(temporary)
                .path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-post-push-contract");
    }

    @Test
    void rejectsPhysicalSuccessorTamperingInAGitlessCopy(@TempDir Path temporary)
            throws Exception {
        copyMinimalFixture(temporary);
        Files.writeString(
                temporary.resolve("README.md"),
                "tampered",
                StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class);
    }

    @Test
    void rejectsCheckpointTamperingAndEveryPrematureOverclaim() throws Exception {
        JsonNode fixed = contract();
        List<Mutation> mutations = List.of(
                new Mutation("commit", value -> ((ObjectNode) value.path("git_checkpoint"))
                        .put("commit_oid", "0".repeat(40))),
                new Mutation("artifact", value -> ((ObjectNode) value
                        .path("git_checkpoint").path("artifacts").path("junit_manifest"))
                        .put("sha256", "0".repeat(64))),
                new Mutation("successor", value -> ((ObjectNode) value
                        .path("historical_source_successors").path("overrides")
                        .path("README.md")).put("successor_sha256", "f".repeat(64))),
                new Mutation("signed provenance", value -> ((ObjectNode) value
                        .path("checkpoint_anchor")).put(
                        "independently_signed_provenance", true)),
                new Mutation("typed parity", value -> ((ObjectNode) value
                        .path("authorization")).put("typed_parity_review_complete", true)),
                new Mutation("full parity", value -> ((ObjectNode) value
                        .path("authorization")).put("full_target_parity_closed", true)),
                new Mutation("route", value -> ((ObjectNode) value
                        .path("authorization")).put("route_migration_eligible", true)),
                new Mutation("migrated", value -> ((ObjectNode) value
                        .path("acceptance")).put("migrated_operation_count", 13)),
                new Mutation("pending", value -> ((ObjectNode) value
                        .path("acceptance")).put("pending_operation_count", 598)),
                new Mutation("cutover", value -> ((ObjectNode) value
                        .path("authorization")).put("production_cutover", true)));
        for (Mutation mutation : mutations) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.validate(
                            changed, root()))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    private static JsonNode contract() throws Exception {
        return Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.load(root());
    }

    private static void copyMinimalFixture(Path targetRoot) throws Exception {
        Set<String> relatives = new LinkedHashSet<>(Set.of(
                CONTRACT_PATH, PREDECESSOR_PATH, MANIFEST_PATH, WORM_PATH,
                POST_PUSH_ANCHOR_CONTRACT_PATH));
        relatives.addAll(SUCCESSORS.keySet());
        relatives.addAll(POST_PUSH_ANCHOR_SUCCESSOR_PATHS);
        relatives.addAll(
                Phase4cHttpTypedNormalizationSuccessorAcceptance.minimalFixturePaths());
        for (String relative : relatives) {
            Path source = root().resolve(relative);
            Path target = targetRoot.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(source, target);
        }
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"), "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }

    private static Map.Entry<String, HashPair> successor(
            String relative,
            String accepted,
            String successor
    ) {
        return Map.entry(relative, new HashPair(accepted, successor));
    }

    private record HashPair(String accepted, String successor) {
    }

    private record Mutation(String label, MutationAction action) {
    }

    @FunctionalInterface
    private interface MutationAction {
        void apply(JsonNode value);
    }
}
