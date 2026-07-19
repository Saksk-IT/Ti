package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity for the Phase 4C tag-preflight Node A Git anchor. */
class Phase4cTagMigrationGlobalPreflightPostPushAnchorContractParityTest {

    @Test
    void matchesTheCanonicalPythonContractAndFixedPhysicalIdentity()
            throws Exception {
        JsonNode contract = contract();

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-tag-migration-global-preflight-"
                        + "post-push-anchor-contract");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        "85a3bf65e560e8240e0c38f5689401e93e5c716e8523125afa5b6589495bb01e");
        assertThat(contract.path("captured_at").asString())
                .isEqualTo("2026-07-19T11:15:25+08:00");
        assertThat(contract.properties()).hasSize(14);
        assertThat(Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance
                .acceptedSha256(root(), "tools/unknown.py")).isNull();
    }

    @Test
    void fixesTheUniqueParentTreesAndExactSixtyThreePathDelta()
            throws Exception {
        JsonNode checkpoint = contract().path("git_checkpoint");

        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo(
                "256d5b347e2e5266eef084221807337427ceb16f");
        assertThat(checkpoint.path("parent_oid").asString()).isEqualTo(
                "08328c3fe18e074f581bb9e782ee4ae86cf46c53");
        assertThat(checkpoint.path("root_tree_oid").asString()).isEqualTo(
                "efcd304e85f597ac22840110630d9fc0ae9a8fb0");
        assertThat(checkpoint.path("ti_java_tree_oid").asString()).isEqualTo(
                "e47d851f451fdf045d2c456065ae6913c69229d2");
        assertThat(checkpoint.path("server_tree_oid").asString()).isEqualTo(
                "0adfaa0bf6e0edeba2aceebce6c267421e3b8144");
        assertThat(checkpoint.path("server_src_main_tree_oid").asString())
                .isEqualTo("21fe4902d57a11998502e63041b5a56fb039a090");
        assertThat(checkpoint.path("web_tree_oid").asString()).isEqualTo(
                "a75f69a8205a56843feb055656ddb015ec5b5215");
        assertThat(checkpoint.path("parent_web_tree_oid").asString()).isEqualTo(
                checkpoint.path("web_tree_oid").asString());
        assertThat(checkpoint.path("raw_delta_sha256").asString()).isEqualTo(
                "035e51e17ce5b2596b604e479c244a1b2af711f14940730095a268257209ebcf");
        assertThat(checkpoint.path("numstat_sha256").asString()).isEqualTo(
                "8f06547f62f829b0b3c20f7596f0e5879377a76d08b5ee03ff5860f74792c7dd");
        assertThat(checkpoint.path("changed_path_count").asInt()).isEqualTo(63);
        assertThat(checkpoint.path("added_count").asInt()).isEqualTo(17);
        assertThat(checkpoint.path("modified_count").asInt()).isEqualTo(46);
        assertThat(checkpoint.path("deleted_count").asInt()).isZero();
        assertThat(checkpoint.path("artifacts")).hasSize(63);
        assertThat(checkpoint.path("exact_sixty_three_path_delta").asBoolean())
                .isTrue();
    }

    @Test
    void closesExactlyFortyTwoTransitionsTwentySixSemanticConsumersAndAllSources()
            throws Exception {
        JsonNode contract = contract();
        JsonNode node = contract.path("node_a_authority_anchor");
        Set<String> transitions = strings(node.path("source_successor_paths"));
        Set<String> semantic = strings(node.path("semantic_consumer_paths"));
        Set<String> fixed = strings(node.path("fixed_source_paths"));
        Set<String> controls = strings(node.path("control_sources"));
        Set<String> delta = properties(
                contract.path("git_checkpoint").path("artifacts"));
        Set<String> changedFixed = new LinkedHashSet<>(delta);
        changedFixed.retainAll(fixed);

        assertThat(transitions).hasSize(42);
        assertThat(semantic).hasSize(26).isSubsetOf(transitions);
        assertThat(fixed).hasSize(72);
        assertThat(controls).hasSize(11);
        assertThat(controls).doesNotContainAnyElementsOf(transitions);
        assertThat(controls).doesNotContainAnyElementsOf(fixed);
        assertThat(changedFixed).hasSize(52).containsAll(transitions);
        Set<String> partition = new LinkedHashSet<>(controls);
        partition.addAll(changedFixed);
        assertThat(partition).isEqualTo(delta);
        assertThat(node.path("source_successor_external_git_anchor_complete")
                .asBoolean()).isTrue();
        assertThat(node.path("semantic_successor_external_git_anchor_complete")
                .asBoolean()).isTrue();
        assertThat(node.path(
                "bootstrap_control_sources_external_git_anchor_complete")
                .asBoolean()).isTrue();
    }

    @Test
    void fixesAcceptedAndSuccessorSidesOfEveryTransition() throws Exception {
        JsonNode contract = contract();
        JsonNode predecessor = json(root().resolve(
                "docs/refactor/phase4c/"
                        + "personal-bank-tag-migration-global-preflight-contract.json"));
        JsonNode overrides = predecessor.path("source_successor_bridges")
                .path("overrides");
        JsonNode artifacts = contract.path("git_checkpoint").path("artifacts");

        for (String relative : strings(contract.path("node_a_authority_anchor")
                .path("source_successor_paths"))) {
            JsonNode artifact = artifacts.path(relative);
            JsonNode override = overrides.path(relative);
            assertThat(artifact.path("change_type").asString())
                    .as(relative).isEqualTo("M");
            assertThat(artifact.path("sha256").asString()).as(relative)
                    .isEqualTo(override.path("successor_sha256").asString());
            assertThat(artifact.path("byte_count").asLong()).as(relative)
                    .isEqualTo(override.path("successor_byte_count").asLong());
            assertThat(override.path("accepted_sha256").asString()).as(relative)
                    .hasSize(64);
            assertThat(override.path("accepted_byte_count").asLong()).as(relative)
                    .isPositive();
        }
    }

    @Test
    void retainsWormRuntimeRouteAndProductionAuthorizationBoundaries()
            throws Exception {
        JsonNode contract = contract();
        JsonNode production = contract.path("production_and_worm_boundary");
        assertThat(production.path("terminal_worm_sha256").asString())
                .isEqualTo(
                        "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344");
        assertThat(production.path("java_build_context_sha256").asString())
                .isEqualTo(
                        "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17");
        assertThat(production.path("main_additions")).hasSize(3);
        assertThat(production.path("existing_main_modified_count").asInt())
                .isZero();
        assertThat(production.path("existing_main_deleted_count").asInt())
                .isZero();
        assertThat(production.path("web_tree_unchanged_from_parent").asBoolean())
                .isTrue();

        JsonNode route = contract.path("route_state");
        assertThat(route.path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt())
                .isZero();
        JsonNode authorization = contract.path("authorization");
        for (String field : List.of(
                "migration_durable_ledger_freeze_design_evidence_closed",
                "migration_design_closed", "operator_migration_implementation",
                "production_schema_or_index", "real_data_migration_execution",
                "route_or_openapi_delta", "client_gateway_or_proxy_change",
                "production_cutover")) {
            assertThat(authorization.path(field).asBoolean()).as(field).isFalse();
        }
    }

    @Test
    void sixNewControlsAreGitlessAndCannotAuthorizeThemselves() throws Exception {
        JsonNode contract = contract();
        JsonNode trust = contract.path("current_node_trust_boundary");
        Set<String> current = strings(trust.path("control_sources"));
        Set<String> predecessorAuthority = new LinkedHashSet<>(strings(
                contract.path("node_a_authority_anchor")
                        .path("source_successor_paths")));
        predecessorAuthority.addAll(strings(contract.path("node_a_authority_anchor")
                .path("fixed_source_paths")));
        predecessorAuthority.addAll(strings(contract.path("node_a_authority_anchor")
                .path("control_sources")));

        assertThat(current).containsExactlyInAnyOrderElementsOf(
                Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance
                        .currentControlSources());
        assertThat(current).doesNotContainAnyElementsOf(predecessorAuthority);
        assertThat(trust.path("control_source_count").asInt()).isEqualTo(6);
        assertThat(trust.path("control_sources_excluded_from_self_authority")
                .asBoolean()).isTrue();
        assertThat(trust.path("control_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();

        String acceptanceSource = Files.readString(root().resolve(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cTagMigrationGlobalPreflightPostPushAnchor"
                        + "SuccessorAcceptance.java"));
        assertThat(acceptanceSource).doesNotContain(
                "ProcessBuilder", "Runtime.getRuntime().exec", "org.eclipse.jgit");
    }

    @Test
    void minimalGitlessFixturePassesAndPhysicalTamperFails(
            @TempDir Path temporary) throws Exception {
        Path fixture = temporary.resolve("Ti-Java");
        Files.createDirectories(fixture);
        for (String relative : List.of(
                Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance
                        .contractRelative(),
                "docs/refactor/phase4c/"
                        + "personal-bank-tag-migration-global-preflight-contract.json")) {
            Path target = fixture.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(relative), target);
        }
        assertThat(temporary.resolve(".git")).doesNotExist();
        Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance
                .load(fixture);
        Path contract = fixture.resolve(
                Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance
                        .contractRelative());
        Files.writeString(contract, "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes");
    }

    private static JsonNode contract() throws Exception {
        return Phase4cTagMigrationGlobalPreflightPostPushAnchorSuccessorAcceptance
                .load(root());
    }

    private static JsonNode json(Path path) throws Exception {
        return new tools.jackson.databind.ObjectMapper().readTree(
                Files.readAllBytes(path));
    }

    private static Set<String> strings(JsonNode values) {
        Set<String> result = new LinkedHashSet<>();
        values.forEach(value -> result.add(value.asString()));
        return result;
    }

    private static Set<String> properties(JsonNode object) {
        Set<String> result = new LinkedHashSet<>();
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
