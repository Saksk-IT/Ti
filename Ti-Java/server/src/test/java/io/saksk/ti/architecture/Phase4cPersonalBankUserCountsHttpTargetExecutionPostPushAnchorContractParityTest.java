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
import tools.jackson.databind.node.ObjectNode;

/** Java parity gate for the fixed Phase 4C post-push external anchor. */
class Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchorContractParityTest {

    private static final String CONTRACT_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-"
                    + "anchor-contract.json";
    private static final String PREDECESSOR_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-target-execution-post-push-contract.json";
    private static final String MANIFEST_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-target-execution-junit-manifest.json";
    private static final String WORM_PATH =
            "docs/refactor/phase4c/"
                    + "personal-bank-user-counts-http-implementation-worm-evidence.json";
    private static final String OLD_JAVA_POST_PUSH_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushSuccessorAcceptance.java";
    private static final String NEW_JAVA_ACCEPTANCE_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.java";
    private static final String NEW_JAVA_PARITY_PATH =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase4cPersonalBankUserCountsHttpTargetExecutionPostPushAnchor"
                    + "ContractParityTest.java";

    private static final Map<String, HashPair> SUCCESSORS = Map.ofEntries(
            successor("README.md",
                    "9c7608803dff193b898d14d13de92095ef001dfeb6099fde2a2ba546d4cd867c",
                    "9008df17aa8eba4945fde525a304c4d891da20004f18ab86ceda485fffab2b57"),
            successor("docs/refactor/05-progress.md",
                    "9ac3b2edaff690f105326aed3c7a87d4049b7f89a1af541038c8f0b032bf79ec",
                    "477d2dc0fce4946e511faa2c143fc76367ae6231a932ae204b6858ca5787e1bf"),
            successor("docs/refactor/phase4c/README.md",
                    "649ad38f868840edf8ca16ce35156dd18ea7336da9869433bdaa0db2f604fec2",
                    "50f1ee46eddac681b49281c3b348e4017fe6893ec38051a5485317cd766c2f61"),
            successor("infra/phase2/README.md",
                    "4a5205e57bad5f54b60fd8ad1f21b8f32f5282bb4938a0244ea9f0977c34157e",
                    "7ae3e8a5bb36920039649ffa8a2aef2bd9bb59782fa03f50e4174cee9063b56f"),
            successor("infra/phase2/verify-static.sh",
                    "357cd003b068997cbcb4ed194f785d3a1d1f310871ad1994c5102bcb1839f54d",
                    "92a3a1ee30ddbb2b5c854dbff7fac23da37e5804e0628211e85725ba4523d835"),
            successor(OLD_JAVA_POST_PUSH_PATH,
                    "5cf9c260bbeac52480e814a0d98317932efe191a6e1ffac8a1c747e7bd0b9e17",
                    "46f68412ea0cf42687133ba87a2184b86fe1b0c29625b1ee3f6e8f7301399efa"),
            successor(
                    "server/src/test/java/io/saksk/ti/architecture/"
                            + "Phase4cPersonalBankUserCountsHttpTargetExecution"
                    + "PostPushContractParityTest.java",
                    "5805a4517e02ec23af94546e551d4d3994aaed5667fc680f5b603d81e95f9304",
                    "a8e81f0758928eb69c527a9d6bbcf00517160221ea7b1aca4b901b7d5a26cf48"),
            successor(
                    "tools/build_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    "89790dba5376e617128b8b5048f30db8e75f50491ff34f66507654ab3f79ecf3",
                    "a215e6b65624630de990dcae7e8d718e8a38a1fadae3e00ee0f3ccb81788959f"),
            successor("tools/phase2_wormhole_successor_acceptance.py",
                    "b1eabe5dc758e8ff0c2b0d25f7a4878e7a38a4491db7ea3bffbe04018c579464",
                    "868d5cebbcc695136083ac892e572483ffc40829f487cb8d9d2b407c2fc763d1"),
            successor(
                    "tools/phase4c_http_target_execution_post_push_"
                            + "successor_acceptance.py",
                    "4200844497d67071b1672f00a81ff6309bd6d3d2ac6b355b727e5100f1c9147d",
                    "944c925704e1b237a7d8e16c76591a0e8b7965d388bedd9e2a52492e0511c90c"),
            successor("tools/test_phase2_wormhole_successor_acceptance.py",
                    "fae248af8e5b5e61634ac10bb8824d5437fd08c4d168c49faadff3e6983c1b9e",
                    "691198f36292c460b6bb516e9deb4e4efe064ae12fe60efb85280a52753cb5cb"),
            successor(
                    "tools/test_phase4c_personal_bank_user_counts_http_"
                            + "target_execution_post_push_contract.py",
                    "5abd19cb1db4f96b59d09f7b0827628a0177d3fdb3b2fd5bcbb80d09208eb158",
                    "d99d36f8b17e5072dcd130c4570ac074096a3c9ee2b9bf4f0f49fd2b1cd907e6"));

    @Test
    void loadsTheFixedAnchorAndExactSixteenPathCheckpoint() throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-"
                        + "post-push-anchor-contract");
        assertThat(contract.path("document_payload_sha256").asString()).isEqualTo(
                "b38abd80403536c7e6db2ec9b8a8920dc06e9f740ed9c065941e483a0b5a30e2");
        JsonNode checkpoint = contract.path("git_checkpoint");
        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo(
                "1dae013e11c76ad858d6695f166a32631eb1525e");
        assertThat(checkpoint.path("root_tree_oid").asString()).isEqualTo(
                "30fd08f8aa8acac5b2b3e2be1e371849ce2adc8d");
        assertThat(checkpoint.path("parent_oid").asString()).isEqualTo(
                "6c1b03dd7fa9cde7a6dcdbf6b555452e9a6d9e53");
        assertThat(checkpoint.path("ti_java_tree_oid").asString()).isEqualTo(
                "1d9cc477713f1ff0e58fb9d71cf2e3035cbd314f");
        assertThat(checkpoint.path("artifacts")).hasSize(16);
        assertThat(checkpoint.path("diff").path("added_count").asInt()).isEqualTo(6);
        assertThat(checkpoint.path("diff").path("modified_count").asInt()).isEqualTo(10);
        assertThat(checkpoint.path("diff")
                .path("exact_sixteen_path_delta").asBoolean()).isTrue();
        assertThat(checkpoint.path("diff").path("current_total_bytes").asLong())
                .isEqualTo(605_312);
    }

    @Test
    void externallyAnchorsExactlyTheSixPreviouslyExcludedSources() throws Exception {
        JsonNode anchor = contract().path("post_push_source_anchor");
        assertThat(anchor.path("source_paths")).hasSize(6);
        assertThat(anchor.path("artifacts")).hasSize(6);
        assertThat(anchor.path("source_total_bytes").asLong()).isEqualTo(145_892);
        assertThat(anchor.path(
                "predecessor_current_sources_external_git_anchor_complete").asBoolean())
                .isTrue();
        assertThat(anchor.path(
                "current_anchor_sources_excluded_from_self_authority").asBoolean())
                .isTrue();
        assertThat(anchor.path(
                "current_anchor_source_bytes_external_git_anchor_complete").asBoolean())
                .isFalse();
        assertThat(strings(anchor.path("current_anchor_sources"))).containsExactlyElementsOf(
                Set.of(
                        CONTRACT_PATH,
                        NEW_JAVA_ACCEPTANCE_PATH,
                        NEW_JAVA_PARITY_PATH,
                        "tools/build_phase4c_personal_bank_user_counts_http_"
                                + "target_execution_post_push_anchor_contract.py",
                        "tools/phase4c_http_target_execution_post_push_anchor_"
                                + "successor_acceptance.py",
                        "tools/test_phase4c_personal_bank_user_counts_http_"
                                + "target_execution_post_push_anchor_contract.py")
                        .stream().sorted().toList());
    }

    @Test
    void exposesOnlyTheExactTwelveHistoricalToSuccessorTransitions() throws Exception {
        assertThat(contract().path("historical_source_successors")
                .path("successor_allowlist")).hasSize(12);
        assertThat(contract().path("historical_source_successors")
                .path("predecessor_historical_successor_allowlist_count").asInt())
                .isEqualTo(10);
        assertThat(contract().path("historical_source_successors")
                .path("second_hop_successor_allowlist_count").asInt())
                .isEqualTo(12);
        for (Map.Entry<String, HashPair> entry : SUCCESSORS.entrySet()) {
            assertThat(Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                    .acceptedHash(entry.getKey())).as(entry.getKey())
                    .isEqualTo(entry.getValue().accepted());
            String expectedSuccessor =
                    Phase4cHttpTypedNormalizationSuccessorAcceptance
                            .acceptedHash(entry.getKey()) == null
                    ? entry.getValue().successor()
                    : Phase4cHttpTypedNormalizationSuccessorAcceptance
                            .successorHash(root(), entry.getKey());
            assertThat(Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                    .successorHash(root(), entry.getKey())).as(entry.getKey())
                    .isEqualTo(expectedSuccessor);
        }
        for (String forbidden : Set.of(
                CONTRACT_PATH,
                NEW_JAVA_ACCEPTANCE_PATH,
                NEW_JAVA_PARITY_PATH,
                "tools/build_phase4c_personal_bank_user_counts_http_"
                        + "target_execution_post_push_anchor_contract.py",
                "tools/phase4c_http_target_execution_post_push_anchor_"
                        + "successor_acceptance.py",
                "unknown/self-authorized")) {
            assertThat(Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                    .acceptedHash(forbidden)).as(forbidden).isNull();
            assertThat(Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                    .successorHash(root(), forbidden)).as(forbidden).isNull();
        }
    }

    @Test
    void handsTheExactTransitionBackToTheHistoricalPostPushBridge() throws Exception {
        JsonNode historical = Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                .load(root());
        assertThat(historical.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-"
                        + "post-push-contract");
        assertThat(Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                .successorHash(root(), "README.md"))
                .isEqualTo(Phase4cHttpTypedNormalizationSuccessorAcceptance
                        .successorHash(root(), "README.md"));
        assertThat(Phase4cHttpTargetExecutionPostPushSuccessorAcceptance
                .successorHash(root(), "unknown/source")).isNull();
    }

    @Test
    void keepsTypedParityRoutesWormAndCutoverClosed() throws Exception {
        JsonNode contract = contract();
        assertThat(contract.path("junit_execution").path("total_leaf_count").asInt())
                .isEqualTo(60);
        assertThat(contract.path("worm_evidence")
                .path("fixed_chain_node_count").asInt()).isEqualTo(5);
        assertThat(contract.path("worm_evidence")
                .path("new_worm_report_created").asBoolean()).isFalse();
        JsonNode authorization = contract.path("authorization");
        for (String field : List.of(
                "current_anchor_source_bytes_external_git_anchor_complete",
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
        assertThat(temporary.resolve(NEW_JAVA_ACCEPTANCE_PATH)).doesNotExist();
        assertThat(Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                .load(temporary).path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-target-execution-"
                        + "post-push-anchor-contract");
    }

    @Test
    void rejectsSuccessorTamperingInAGitlessCopy(@TempDir Path temporary)
            throws Exception {
        copyMinimalFixture(temporary);
        Files.writeString(
                temporary.resolve("README.md"),
                "tampered",
                StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class);
    }

    @Test
    void rejectsCheckpointSelfAuthorizationAndEveryPrematureOverclaim()
            throws Exception {
        JsonNode fixed = contract();
        List<Mutation> mutations = List.of(
                new Mutation("commit", value -> ((ObjectNode) value
                        .path("git_checkpoint")).put("commit_oid", "0".repeat(40))),
                new Mutation("delta", value -> ((ObjectNode) value
                        .path("git_checkpoint").path("diff"))
                        .put("modified_count", 9)),
                new Mutation("blob", value -> ((ObjectNode) value
                        .path("git_checkpoint").path("artifacts").path(PREDECESSOR_PATH))
                        .put("git_blob_oid", "0".repeat(40))),
                new Mutation("source anchor", value -> ((ObjectNode) value
                        .path("post_push_source_anchor")).put(
                        "predecessor_current_sources_external_git_anchor_complete", false)),
                new Mutation("self authority", value -> ((ObjectNode) value
                        .path("post_push_source_anchor")).put(
                        "current_anchor_source_bytes_external_git_anchor_complete", true)),
                new Mutation("successor", value -> ((ObjectNode) value
                        .path("historical_source_successors").path("overrides")
                        .path("README.md")).put("successor_sha256", "f".repeat(64))),
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
                    Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance
                            .validate(changed))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    private static JsonNode contract() throws Exception {
        return Phase4cHttpTargetExecutionPostPushAnchorSuccessorAcceptance.load(root());
    }

    private static void copyMinimalFixture(Path targetRoot) throws Exception {
        Set<String> relatives = new LinkedHashSet<>(Set.of(
                CONTRACT_PATH, PREDECESSOR_PATH, MANIFEST_PATH, WORM_PATH));
        relatives.addAll(SUCCESSORS.keySet());
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

    private static List<String> strings(JsonNode values) {
        List<String> result = new ArrayList<>();
        values.forEach(value -> result.add(value.asString()));
        return List.copyOf(result);
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
