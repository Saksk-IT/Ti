package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity gate for the fixed Phase 6 source-successor anchor. */
class Phase6WebFoundationSourceSuccessorAnchorContractParityTest {

    private static final String PREDECESSOR =
            "docs/refactor/phase6/web-foundation-source-successor-contract.json";
    private static final String STAGE_A_JAVA_ACCEPTANCE =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAcceptance.java";
    private static final String STAGE_A_JAVA_PARITY =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorContractParityTest.java";
    private static final String STAGE_B_JAVA_ACCEPTANCE =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java";
    private static final String STAGE_B_JAVA_PARITY =
            "server/src/test/java/io/saksk/ti/architecture/"
                    + "Phase6WebFoundationSourceSuccessorAnchorContractParityTest.java";

    private static final Map<String, HashPair> SUCCESSORS = Map.ofEntries(
            successor(
                    "README.md",
                    "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
                    "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59"),
            successor(
                    "docs/refactor/05-progress.md",
                    "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
                    "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b"),
            successor(
                    "docs/refactor/phase4c/README.md",
                    "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c",
                    "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c"),
            successor(
                    PREDECESSOR,
                    "be652b57cf9e024effbd62d5eb5f438931c4db3c8126e8318e2af077236e4073",
                    "be652b57cf9e024effbd62d5eb5f438931c4db3c8126e8318e2af077236e4073"),
            successor(
                    STAGE_A_JAVA_ACCEPTANCE,
                    "dbdb33fdcba228d45ee72a560dccc11baee489c3780864caa1e649e2e9aa489b",
                    "288e85ace1a4fc3e2a74e03d4390533044678604fef71fe6707c3e840c2b5d85"),
            successor(
                    STAGE_A_JAVA_PARITY,
                    "e17f062b1cd960289aa5a56cd3fc7b0aa65a649b16f48c7d802d51fab81a89ec",
                    "34d6b638cf40667a2c0b1ce1214cc04b8e149321f3137ea8d5d09ee44290d694"),
            successor(
                    "tools/build_phase6_web_foundation_source_successor_contract.py",
                    "f9fc6c70ad12e98ceb4d1bf27bb448085807c91fc390c56e451b905403b263c6",
                    "ed3a711cf9e0b15cb7facfcaa76a63ca2d6509eda84dc617afbfc8b033a1079a"),
            successor(
                    "tools/phase6_web_foundation_source_successor_acceptance.py",
                    "1904fae55218791fdc7c66490bcff0d9d9702a4d769ceb919542670bb6e32974",
                    "19190c0053c1313f5b481c5ce85db8d905e959f6ada10745848c7dcce4f57e59"),
            successor(
                    "tools/test_phase6_web_foundation_source_successor_contract.py",
                    "08058702a694a380e16a3a385293396f5f13f88b1cfb36209ffff16818c2a471",
                    "fb553e8d15c8b748dc62eb6517f775614132657a60b13716449ad1a72606685d"));

    @Test
    void matchesThePythonBuilderCanonicalContractAndPayload() throws Exception {
        JsonNode contract = contract();

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase6.web-foundation-source-successor-anchor-contract");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        "87d952b1ba4ca4336c067d8d68ffbe86101ea0263c854541674ac3dbd7feb4af");
        assertThat(contract.path("captured_at").asString())
                .isEqualTo("2026-07-19T03:00:00+08:00");
        assertThat(contract.properties()).hasSize(16);
        assertThat(contract.path("authorization")
                .path("predecessor_source_successor_checkpoint_"
                        + "external_git_anchor_complete")
                .asBoolean()).isTrue();
        assertThat(contract.path("authorization")
                .path("current_successor_bytes_external_git_anchor_complete")
                .asBoolean()).isFalse();
        assertThat(contract.path("authorization")
                .path("phase6_complete").asBoolean()).isFalse();
    }

    @Test
    void fixesTheExactElevenPathGitDeltaAndBothSourceAnchorGroups()
            throws Exception {
        JsonNode contract = contract();
        JsonNode checkpoint = contract.path("git_checkpoint");

        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo(
                "40a27ffdd83ecf240e17f4a5f69106906faaef35");
        assertThat(checkpoint.path("parent_oid").asString()).isEqualTo(
                "c563ac655077e69306c34d163f63a4da50569e01");
        assertThat(checkpoint.path("root_tree_oid").asString()).isEqualTo(
                "b83b6957736c594066cf18955b8e87b1c91f6b82");
        assertThat(checkpoint.path("ti_java_tree_oid").asString()).isEqualTo(
                "d7c83c3439509ea51e5fa06f3310df91bf0fd5a4");
        assertThat(checkpoint.path("server_tree_oid").asString()).isEqualTo(
                "275dbc7251889ca9fad02688fb4b418e52d2c68a");
        assertThat(checkpoint.path("server_src_main_tree_oid").asString())
                .isEqualTo("7130e1d1fde766030689658cdd508794ab9a12d6");
        assertThat(checkpoint.path("web_tree_oid").asString()).isEqualTo(
                "a75f69a8205a56843feb055656ddb015ec5b5215");
        assertThat(checkpoint.path("raw_delta_sha256").asString()).isEqualTo(
                "0e97aacf626cf528ab4303bc5c61cfc9e359edb66f1a9b227e866dc21c26d2cd");
        assertThat(checkpoint.path("changed_path_count").asInt()).isEqualTo(11);
        assertThat(checkpoint.path("added_count").asInt()).isEqualTo(6);
        assertThat(checkpoint.path("modified_count").asInt()).isEqualTo(5);
        assertThat(checkpoint.path("deleted_count").asInt()).isZero();
        assertThat(checkpoint.path("inserted_line_count").asInt())
                .isEqualTo(2_297);
        assertThat(checkpoint.path("deleted_line_count").asInt()).isEqualTo(28);
        assertThat(checkpoint.path("artifacts")).hasSize(11);
        assertThat(checkpoint.path("exact_eleven_path_delta").asBoolean())
                .isTrue();

        JsonNode controls = contract.path("predecessor_control_source_anchor");
        assertThat(controls.path("source_count").asInt()).isEqualTo(6);
        assertThat(controls.path("source_paths")).hasSize(6);
        assertThat(controls.path("artifacts")).hasSize(6);
        assertThat(controls.path(
                "predecessor_control_sources_external_git_anchor_complete")
                .asBoolean()).isTrue();

        JsonNode bridge = contract.path("typed_anchor_bridge_source_anchor");
        assertThat(bridge.path("source_count").asInt()).isEqualTo(5);
        assertThat(bridge.path("source_paths")).hasSize(5);
        assertThat(bridge.path("artifacts")).hasSize(5);
        assertThat(bridge.path(
                "typed_anchor_bridge_sources_external_git_anchor_complete")
                .asBoolean()).isTrue();
    }

    @Test
    void exposesExactlyNineFixedSourceSuccessorsAndRejectsSelfAuthority()
            throws Exception {
        assertThat(Phase6WebFoundationSourceSuccessorAnchorAcceptance
                .successorPaths()).containsExactlyInAnyOrderElementsOf(
                SUCCESSORS.keySet());
        for (Map.Entry<String, HashPair> entry : SUCCESSORS.entrySet()) {
            String relative = entry.getKey();
            assertThat(Phase6WebFoundationSourceSuccessorAnchorAcceptance
                    .acceptedSha256(relative)).as(relative)
                    .isEqualTo(entry.getValue().accepted());
            assertThat(Phase6WebFoundationSourceSuccessorAnchorAcceptance
                    .successorSha256(root(), relative)).as(relative)
                    .isEqualTo(entry.getValue().successor());
        }

        for (String forbidden : Set.of(
                Phase6WebFoundationSourceSuccessorAnchorAcceptance
                        .contractRelative(),
                STAGE_B_JAVA_ACCEPTANCE,
                STAGE_B_JAVA_PARITY,
                "tools/build_phase6_web_foundation_source_successor_"
                        + "anchor_contract.py",
                "tools/unknown-source.py")) {
            assertThat(Phase6WebFoundationSourceSuccessorAnchorAcceptance
                    .acceptedSha256(forbidden)).as(forbidden).isNull();
            assertThat(Phase6WebFoundationSourceSuccessorAnchorAcceptance
                    .successorSha256(root(), forbidden)).as(forbidden).isNull();
        }
    }

    @Test
    void keepsRouteWormJavaAndCurrentNodeAuthorityClosed() throws Exception {
        JsonNode contract = contract();

        JsonNode authority = contract.path("effective_authority");
        assertThat(authority.path("migrated_operation_count").asInt())
                .isEqualTo(13);
        assertThat(authority.path("pending_operation_count").asInt())
                .isEqualTo(598);
        assertThat(authority.path(
                "production_cutover_operation_count").asInt()).isZero();
        assertThat(authority.path(
                "legacy_flask_remains_production_owner").asBoolean()).isTrue();

        JsonNode boundary = contract.path("java_build_context_boundary");
        assertThat(boundary.path("java_build_context_sha256").asString())
                .isEqualTo(
                        "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3");
        assertThat(boundary.path("server_src_main_tree_unchanged_from_parent")
                .asBoolean()).isTrue();
        assertThat(boundary.path("web_tree_unchanged_from_parent")
                .asBoolean()).isTrue();
        assertThat(boundary.path("new_worm_node_required").asBoolean())
                .isFalse();

        JsonNode trust = contract.path("current_node_trust_boundary");
        assertThat(trust.path("control_source_count").asInt()).isEqualTo(6);
        assertThat(trust.path(
                "control_sources_excluded_from_self_authority").asBoolean())
                .isTrue();
        assertThat(trust.path(
                "control_sources_external_git_anchor_complete").asBoolean())
                .isFalse();
        assertThat(trust.path("independently_signed_provenance").asBoolean())
                .isFalse();
    }

    @Test
    void loadsFromTheExactGitlessFixtureWithoutCurrentControlSources(
            @TempDir Path temporary) throws Exception {
        copyMinimalFixture(temporary);

        assertThat(temporary.resolve(".git")).doesNotExist();
        assertThat(temporary.resolve(STAGE_B_JAVA_ACCEPTANCE)).doesNotExist();
        assertThat(temporary.resolve(STAGE_B_JAVA_PARITY)).doesNotExist();
        assertThat(temporary.resolve(
                "tools/phase6_web_foundation_source_successor_anchor_"
                        + "acceptance.py")).doesNotExist();

        JsonNode loaded =
                Phase6WebFoundationSourceSuccessorAnchorAcceptance
                        .load(temporary);
        assertThat(loaded.path("git_checkpoint").path("commit_oid").asString())
                .isEqualTo("40a27ffdd83ecf240e17f4a5f69106906faaef35");
    }

    @Test
    void rejectsContractAndEverySuccessorTamper(@TempDir Path temporary)
            throws Exception {
        Path contractFixture = temporary.resolve("contract");
        copyMinimalFixture(contractFixture);
        Files.writeString(
                contractFixture.resolve(
                        Phase6WebFoundationSourceSuccessorAnchorAcceptance
                                .contractRelative()),
                " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase6WebFoundationSourceSuccessorAnchorAcceptance
                        .load(contractFixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("contract physical bytes");

        int index = 0;
        for (String relative : SUCCESSORS.keySet()) {
            Path fixture = temporary.resolve("source-" + index++);
            copyMinimalFixture(fixture);
            Files.writeString(
                    fixture.resolve(relative), " ", StandardOpenOption.APPEND);
            assertThatThrownBy(() ->
                    Phase6WebFoundationSourceSuccessorAnchorAcceptance
                            .load(fixture))
                    .as(relative)
                    .isInstanceOf(AssertionError.class);
        }
    }

    @Test
    void rejectsSymlinkSubstitution(@TempDir Path temporary) throws Exception {
        copyMinimalFixture(temporary);
        Path route = temporary.resolve(
                "docs/refactor/phase4c/"
                        + "effective-route-parity-successor-status.json");
        Path outside = temporary.resolve("outside-route.json");
        Files.move(route, outside);
        Files.createSymbolicLink(route, outside);

        assertThatThrownBy(() ->
                Phase6WebFoundationSourceSuccessorAnchorAcceptance
                        .load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("symlink");
    }

    @Test
    void rejectsCheckpointRouteCutoverAndSelfAuthorityOverclaims()
            throws Exception {
        JsonNode fixed = contract();
        Set<Mutation> mutations = Set.of(
                new Mutation("commit", value -> ((ObjectNode) value
                        .path("git_checkpoint")).put(
                        "commit_oid", "0".repeat(40))),
                new Mutation("insertions", value -> ((ObjectNode) value
                        .path("git_checkpoint")).put(
                        "inserted_line_count", 1_897)),
                new Mutation("blob", value -> ((ObjectNode) value
                        .path("git_checkpoint").path("artifacts")
                        .path(PREDECESSOR)).put(
                        "git_blob_oid", "f".repeat(40))),
                new Mutation("control count", value -> ((ObjectNode) value
                        .path("predecessor_control_source_anchor")).put(
                        "source_count", 5)),
                new Mutation("bridge count", value -> ((ObjectNode) value
                        .path("typed_anchor_bridge_source_anchor")).put(
                        "source_count", 4)),
                new Mutation("successor", value -> ((ObjectNode) value
                        .path("source_successors").path("overrides")
                        .path(STAGE_A_JAVA_ACCEPTANCE)).put(
                        "successor_sha256", "f".repeat(64))),
                new Mutation("migrated", value -> ((ObjectNode) value
                        .path("effective_authority")).put(
                        "migrated_operation_count", 14)),
                new Mutation("WORM", value -> ((ObjectNode) value
                        .path("java_build_context_boundary")).put(
                        "new_worm_node_required", true)),
                new Mutation("Phase6", value -> ((ObjectNode) value
                        .path("authorization")).put("phase6_complete", true)),
                new Mutation("cutover", value -> ((ObjectNode) value
                        .path("authorization")).put("production_cutover", true)),
                new Mutation("self anchor", value -> ((ObjectNode) value
                        .path("current_node_trust_boundary")).put(
                        "control_sources_external_git_anchor_complete", true)));

        for (Mutation mutation : mutations) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase6WebFoundationSourceSuccessorAnchorAcceptance
                            .validate(changed, root()))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    private static JsonNode contract() throws Exception {
        return Phase6WebFoundationSourceSuccessorAnchorAcceptance.load(root());
    }

    private static void copyMinimalFixture(Path targetRoot) throws Exception {
        Set<String> paths = new LinkedHashSet<>(
                Phase6WebFoundationSourceSuccessorAnchorAcceptance
                        .minimalFixturePaths());
        for (String relative : paths) {
            Path target = targetRoot.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(relative), target);
        }
    }

    private static Path root() {
        Path basedir = Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
        return basedir.getParent();
    }

    private static Map.Entry<String, HashPair> successor(
            String relative,
            String accepted,
            String successor) {
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
