package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity gate for the typed-normalization external anchor. */
class Phase4cPersonalBankUserCountsHttpTypedNormalizationAnchorContractParityTest {

    @Test
    void loadsTheCanonicalFixedAnchorAndKeepsRoutesPending() throws Exception {
        JsonNode contract =
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.load(root());

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-user-counts-http-typed-normalization-"
                        + "anchor-contract");
        assertThat(contract.path("git_checkpoint").path("commit_oid").asString())
                .isEqualTo("b0861d61438f649ed48d5d5e6806e02c804fa2e4");
        assertThat(contract.path("document_payload_sha256").asString()).isEqualTo(
                "430ef24103006265001ecd1f2f6aa5e4b24a886e82fcc1391cc516eba5dbde7c");

        JsonNode acceptance = contract.path("acceptance");
        assertThat(acceptance.path("checkpoint_changed_path_count").asInt())
                .isEqualTo(26);
        assertThat(acceptance.path("checkpoint_added_count").asInt()).isEqualTo(12);
        assertThat(acceptance.path("checkpoint_modified_count").asInt()).isEqualTo(14);
        assertThat(acceptance.path("typed_source_anchor_count").asInt()).isEqualTo(6);
        assertThat(acceptance.path("typed_source_anchor_total_bytes").asLong())
                .isEqualTo(280_664L);
        assertThat(acceptance.path("migrated_operation_count").asInt()).isEqualTo(11);
        assertThat(acceptance.path("pending_operation_count").asInt()).isEqualTo(600);
        assertThat(acceptance.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(acceptance.path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(acceptance.path("full_target_parity_closed").asBoolean()).isFalse();
        assertThat(acceptance.path("production_cutover").asBoolean()).isFalse();
    }

    @Test
    void fixesEveryCheckpointDescriptorAndTheSixTypedSources() throws Exception {
        JsonNode contract =
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.load(root());
        JsonNode artifacts = contract.path("git_checkpoint").path("artifacts");
        assertThat(artifacts).hasSize(26);

        int added = 0;
        int modified = 0;
        for (Map.Entry<String, JsonNode> entry : artifacts.properties()) {
            JsonNode descriptor = entry.getValue();
            if ("A".equals(descriptor.path("change_type").asString())) {
                added++;
                assertThat(descriptor.path("previous_mode").asString())
                        .isEqualTo("000000");
                assertThat(descriptor.path("previous_git_blob_oid").asString())
                        .isEqualTo("0000000000000000000000000000000000000000");
            } else {
                modified++;
            }
            assertThat(descriptor.path("object_type").asString()).isEqualTo("blob");
            assertThat(descriptor.path("git_blob_oid").asString()).hasSize(40);
            assertThat(descriptor.path("sha256").asString()).hasSize(64);
            assertThat(descriptor.path("byte_count").asLong()).isPositive();
        }
        assertThat(added).isEqualTo(12);
        assertThat(modified).isEqualTo(14);

        JsonNode anchor = contract.path("typed_normalization_source_anchor");
        assertThat(anchor.path("artifacts")).hasSize(6);
        assertThat(anchor.path(
                "predecessor_current_sources_external_git_anchor_complete")
                .asBoolean()).isTrue();
        assertThat(anchor.path(
                "current_anchor_sources_excluded_from_self_authority")
                .asBoolean()).isTrue();
        assertThat(anchor.path(
                "current_anchor_source_bytes_external_git_anchor_complete")
                .asBoolean()).isFalse();
        assertThat(anchor.path("independently_signed_provenance").asBoolean())
                .isFalse();
    }

    @Test
    void exposesOnlyTheThirteenCodeFixedSuccessorTransitions() throws Exception {
        Set<String> paths =
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .successorPaths();
        assertThat(paths).hasSize(13);
        for (String relative : paths) {
            String accepted =
                    Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                            .acceptedHash(relative);
            String successor =
                    Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                            .successorHash(root(), relative);
            assertThat(accepted).as(relative).hasSize(64).isNotEqualTo(successor);
            assertThat(successor).as(relative).hasSize(64);
            if (Phase4cHttpTypedNormalizationSuccessorAcceptance
                    .successorPaths().contains(relative)) {
                assertThat(Phase4cHttpTypedNormalizationSuccessorAcceptance
                        .successorHash(root(), relative)).as(relative)
                        .isEqualTo(successor);
            }
        }
        for (String relative : Set.of(
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .contractRelative(),
                "tools/build_phase4c_personal_bank_user_counts_http_"
                        + "typed_normalization_anchor_contract.py",
                "tools/phase4c_http_typed_normalization_anchor_"
                        + "successor_acceptance.py",
                "tools/unknown-source.py")) {
            assertThat(Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                    .acceptedHash(relative)).as(relative).isNull();
            assertThat(Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                    .successorHash(root(), relative)).as(relative).isNull();
        }
    }

    @Test
    void loadsFromTheExactMinimalGitlessFixture(@TempDir Path temporary)
            throws Exception {
        copyMinimalFixture(temporary);
        assertThat(temporary.resolve(".git")).doesNotExist();
        JsonNode loaded =
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .load(temporary);
        assertThat(loaded.path("git_checkpoint").path("commit_oid").asString())
                .isEqualTo("b0861d61438f649ed48d5d5e6806e02c804fa2e4");
    }

    @Test
    void rehashesTheContractAndRequestedSuccessor(@TempDir Path temporary)
            throws Exception {
        String relative = "README.md";
        for (String source : Set.of(
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .contractRelative(),
                relative)) {
            Path target = temporary.resolve(source);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(source), target);
        }
        assertThat(Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                .successorHash(temporary, relative))
                .isNotEqualTo(
                        Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                                .acceptedHash(relative));

        Files.writeString(
                temporary.resolve(relative), " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .successorHash(temporary, relative))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("successor bytes");

        Files.copy(
                root().resolve(relative),
                temporary.resolve(relative),
                StandardCopyOption.REPLACE_EXISTING);
        Files.writeString(
                temporary.resolve(
                        Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                                .contractRelative()),
                " ",
                StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .successorHash(temporary, relative))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("contract physical bytes");
    }

    @Test
    void rejectsSymlinkSubstitution(@TempDir Path temporary) throws Exception {
        copyMinimalFixture(temporary);
        Path manifest = temporary.resolve(
                "docs/refactor/phase4c/"
                        + "personal-bank-user-counts-typed-normalization-"
                        + "junit-manifest.json");
        Path outside = temporary.resolve("outside-manifest.json");
        Files.move(manifest, outside);
        Files.createSymbolicLink(manifest, outside);
        assertThatThrownBy(() ->
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                        .load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("symlink");
    }

    @Test
    void rejectsTrustRouteAndEvidenceOverclaims() throws Exception {
        JsonNode fixed =
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance.load(root());
        Set<Mutation> mutations = Set.of(
                new Mutation("self anchor", value -> ((ObjectNode) value
                        .path("typed_normalization_source_anchor")).put(
                        "current_anchor_source_bytes_external_git_anchor_complete",
                        true)),
                new Mutation("route", value -> ((ObjectNode) value
                        .path("authorization")).put(
                        "route_migration_eligible", true)),
                new Mutation("typed parity", value -> ((ObjectNode) value
                        .path("authorization")).put(
                        "typed_parity_review_complete", true)),
                new Mutation("migrated 13", value -> ((ObjectNode) value
                        .path("acceptance")).put(
                        "migrated_operation_count", 13)),
                new Mutation("WORM 6", value -> ((ObjectNode) value
                        .path("worm_evidence")).put(
                        "fixed_chain_node_count", 6)));
        for (Mutation mutation : mutations) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
                            .validate(changed, root()))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    @Test
    void PythonBuilderAndAcceptanceFixTheSameContractIdentity() throws Exception {
        String builder = Files.readString(root().resolve(
                "tools/build_phase4c_personal_bank_user_counts_http_"
                        + "typed_normalization_anchor_contract.py"));
        String acceptance = Files.readString(root().resolve(
                "tools/phase4c_http_typed_normalization_anchor_"
                        + "successor_acceptance.py"));
        for (String literal : Set.of(
                "b0861d61438f649ed48d5d5e6806e02c804fa2e4",
                "9d295380b565307dc5ebe0a5b9bf3d8589452dbf",
                "ff845fbf8b7e3b7a4823ebb00bf8dcb164fde019",
                "175dd8deb2cddb69e4bb6d6d985d312e041055699177d1054a8bb5ebef4f27c0")) {
            assertThat(builder).contains(literal);
            assertThat(acceptance).contains(literal);
        }
        assertThat(acceptance).contains(
                "430ef24103006265001ecd1f2f6aa5e4b24a886e82fcc1391cc516eba5dbde7c");
        assertThat(builder).doesNotContain(".glob(", ".rglob(");
        assertThat(acceptance).doesNotContain(".glob(", ".rglob(");
    }

    private static void copyMinimalFixture(Path targetRoot) throws Exception {
        Set<String> paths = new LinkedHashSet<>(
                Phase4cHttpTypedNormalizationAnchorSuccessorAcceptance
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

    private record Mutation(String label, MutationAction action) {
    }

    @FunctionalInterface
    private interface MutationAction {
        void apply(JsonNode value);
    }
}
