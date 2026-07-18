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

/** Cross-language parity gate for the Phase 6 source-successor bootstrap. */
class Phase6WebFoundationSourceSuccessorContractParityTest {

    private static final Map<String, String> ACCEPTED = Map.of(
            "README.md",
            "524f03e89122b4d8a9af4ed805596a3b315a4859dac2777b0ab989ac25e82b47",
            "docs/refactor/05-progress.md",
            "62ff84e2cc3b525855f0a0eb07a1820c231ad50864956329d0da08a3d86b697c",
            "docs/refactor/phase4c/README.md",
            "dd0f41f78466636d09d3afa7669e507814aa78a04cb94d62bf7e96596c18e85a");

    private static final Map<String, String> CURRENT = Map.of(
            "README.md",
            "5e3f2b7da26c3edf0f791e99110dcc4e53e1cb64dfdd78b46fe4e276406a1e59",
            "docs/refactor/05-progress.md",
            "657ca0e5fec6d0a70fbcfd8b81da6815a46be395a2cd3230520fe036b584144b",
            "docs/refactor/phase4c/README.md",
            "dbf542c042b3ee96663cb39c049bc44deb1790cf4c6e0345f208ea6c27cc2d0c");

    @Test
    void loadsTheCanonicalFixedBootstrapWithoutPromotingPhase6() throws Exception {
        JsonNode contract =
                Phase6WebFoundationSourceSuccessorAcceptance.load(root());

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase6.web-foundation-source-successor-contract");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        "93e2eccb5bd3cdcc95addac0d09bef26d25ae3676c1ffd1b9c10c337c1b1b693");
        assertThat(contract.path("git_checkpoint").path("commit_oid").asString())
                .isEqualTo("c563ac655077e69306c34d163f63a4da50569e01");
        assertThat(contract.path("phase6_foundation")
                .path("foundation_complete").asBoolean()).isTrue();
        assertThat(contract.path("phase6_foundation")
                .path("phase6_complete").asBoolean()).isFalse();
    }

    @Test
    void exposesExactlyTheThreeFixedDocumentTransitions() throws Exception {
        assertThat(Phase6WebFoundationSourceSuccessorAcceptance.successorPaths())
                .containsExactlyInAnyOrderElementsOf(CURRENT.keySet());
        for (String relative : CURRENT.keySet()) {
            assertThat(Phase6WebFoundationSourceSuccessorAcceptance
                    .acceptedHash(relative)).as(relative)
                    .isEqualTo(ACCEPTED.get(relative));
            assertThat(Phase6WebFoundationSourceSuccessorAcceptance
                    .successorHash(root(), relative)).as(relative)
                    .isEqualTo(CURRENT.get(relative))
                    .isNotEqualTo(ACCEPTED.get(relative));
        }
        for (String relative : Set.of(
                Phase6WebFoundationSourceSuccessorAcceptance.contractRelative(),
                "tools/build_phase6_web_foundation_source_successor_contract.py",
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase6WebFoundationSourceSuccessorAcceptance.java",
                "tools/unknown-source.py")) {
            assertThat(Phase6WebFoundationSourceSuccessorAcceptance
                    .acceptedHash(relative)).as(relative).isNull();
            assertThat(Phase6WebFoundationSourceSuccessorAcceptance
                    .successorHash(root(), relative)).as(relative).isNull();
        }
    }

    @Test
    void keepsRouteJavaAndSelfAuthorityBoundariesClosed() throws Exception {
        JsonNode contract =
                Phase6WebFoundationSourceSuccessorAcceptance.load(root());

        JsonNode authority = contract.path("effective_authority");
        assertThat(authority.path("migrated_operation_count").asInt())
                .isEqualTo(13);
        assertThat(authority.path("pending_operation_count").asInt())
                .isEqualTo(598);
        assertThat(authority.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(authority.path(
                "legacy_flask_remains_production_owner").asBoolean()).isTrue();

        JsonNode boundary = contract.path("java_build_context_boundary");
        assertThat(boundary.path("java_build_context_sha256").asString())
                .isEqualTo(
                        "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3");
        assertThat(boundary.path("web_in_java_build_context").asBoolean())
                .isFalse();
        assertThat(boundary.path("new_worm_node_required").asBoolean()).isFalse();

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
        assertThat(contract.path("authorization").properties())
                .allMatch(entry -> entry.getValue().isBoolean()
                        && !entry.getValue().asBoolean());
    }

    @Test
    void loadsFromExactGitlessFixtureWithOnlyAnchoredPredecessorSources(
            @TempDir Path temporary) throws Exception {
        copyMinimalFixture(temporary);
        assertThat(temporary.resolve(".git")).doesNotExist();
        assertThat(temporary.resolve(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase6WebFoundationSourceSuccessorAcceptance.java"))
                .exists();
        assertThat(temporary.resolve(
                "tools/phase6_web_foundation_source_successor_acceptance.py"))
                .exists();
        assertThat(temporary.resolve(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase6WebFoundationSourceSuccessorAnchorAcceptance.java"))
                .doesNotExist();
        assertThat(temporary.resolve(
                "tools/phase6_web_foundation_source_successor_anchor_"
                        + "acceptance.py"))
                .doesNotExist();

        JsonNode loaded =
                Phase6WebFoundationSourceSuccessorAcceptance.load(temporary);
        assertThat(loaded.path("git_checkpoint").path("commit_oid").asString())
                .isEqualTo("c563ac655077e69306c34d163f63a4da50569e01");
    }

    @Test
    void rejectsContractAndEveryDelegatedDocumentTamper(@TempDir Path temporary)
            throws Exception {
        Path contractFixture = temporary.resolve("contract");
        copyMinimalFixture(contractFixture);
        Files.writeString(
                contractFixture.resolve(
                        Phase6WebFoundationSourceSuccessorAcceptance
                                .contractRelative()),
                " ",
                StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase6WebFoundationSourceSuccessorAcceptance
                        .load(contractFixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("contract physical bytes");

        int index = 0;
        for (String relative : CURRENT.keySet()) {
            Path fixture = temporary.resolve("source-" + index++);
            copyMinimalFixture(fixture);
            Files.writeString(
                    fixture.resolve(relative), " ", StandardOpenOption.APPEND);
            assertThatThrownBy(() ->
                    Phase6WebFoundationSourceSuccessorAcceptance
                            .load(fixture))
                    .as(relative)
                    .isInstanceOf(AssertionError.class)
                    .hasMessageContaining("bytes drifted");
        }
    }

    @Test
    void rejectsSymlinkSubstitution(@TempDir Path temporary) throws Exception {
        copyMinimalFixture(temporary);
        Path route = temporary.resolve(
                "docs/refactor/phase4c/effective-route-parity-successor-status.json");
        Path outside = temporary.resolve("outside-route.json");
        Files.move(route, outside);
        Files.createSymbolicLink(route, outside);

        assertThatThrownBy(() ->
                Phase6WebFoundationSourceSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("symlink");
    }

    @Test
    void rejectsFoundationRouteMigrationAndTrustOverclaims() throws Exception {
        JsonNode fixed =
                Phase6WebFoundationSourceSuccessorAcceptance.load(root());
        Set<Mutation> mutations = Set.of(
                new Mutation("Phase6 complete", value -> ((ObjectNode) value
                        .path("phase6_foundation")).put(
                        "phase6_complete", true)),
                new Mutation("migrated 14", value -> ((ObjectNode) value
                        .path("effective_authority")).put(
                        "migrated_operation_count", 14)),
                new Mutation("Web enters Java context", value ->
                        ((ObjectNode) value.path("java_build_context_boundary"))
                                .put("web_in_java_build_context", true)),
                new Mutation("operator", value -> ((ObjectNode) value
                        .path("authorization")).put(
                        "operator_authorized", true)),
                new Mutation("external anchor", value -> ((ObjectNode) value
                        .path("current_node_trust_boundary")).put(
                        "control_sources_external_git_anchor_complete", true)),
                new Mutation("delegation count", value -> ((ObjectNode) value
                        .path("typed_anchor_delegation")).put(
                        "delegated_path_count", 4)));
        for (Mutation mutation : mutations) {
            JsonNode changed = fixed.deepCopy();
            mutation.action().apply(changed);
            assertThatThrownBy(() ->
                    Phase6WebFoundationSourceSuccessorAcceptance
                            .validate(changed, root()))
                    .as(mutation.label())
                    .isInstanceOf(AssertionError.class);
        }
    }

    private static void copyMinimalFixture(Path targetRoot) throws Exception {
        Set<String> paths = new LinkedHashSet<>(
                Phase6WebFoundationSourceSuccessorAcceptance
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
