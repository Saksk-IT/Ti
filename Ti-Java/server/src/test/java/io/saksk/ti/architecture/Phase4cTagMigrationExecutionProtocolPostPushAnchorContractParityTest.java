package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermission;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity for the Phase 4C execution-protocol D0+D1 Git anchor. */
class Phase4cTagMigrationExecutionProtocolPostPushAnchorContractParityTest {

    @Test
    void fixesCanonicalPhysicalAndPayloadIdentity() throws Exception {
        JsonNode contract = contract();

        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.personal-bank-tag-migration-execution-protocol-"
                        + "post-push-anchor-contract");
        assertThat(contract.path("captured_at").asString())
                .isEqualTo("2026-07-23T17:47:54+08:00");
        assertThat(contract.path("document_payload_sha256").asString())
                .isEqualTo(
                        Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                                .payloadSha256());
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .physicalSha256()).isEqualTo(
                        "a6dff0717d0da91091f50cb7a51d35ffc66db364e966c568fec40bdb3ca936cd");
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .byteCount()).isEqualTo(80_324L);
        assertThat(contract.properties()).hasSize(18);
    }

    @Test
    void fixesMixedD0CheckpointAndExactSevenPlusFortyEightPartition()
            throws Exception {
        JsonNode contract = contract();
        JsonNode checkpoint = contract.path("implementation_checkpoint");
        JsonNode artifacts = checkpoint.path("artifacts");
        JsonNode anchor = contract.path("execution_protocol_authority_anchor");
        Set<String> controls = new LinkedHashSet<>(strings(
                anchor.path("implementation_control_sources")));
        Set<String> fixed = new LinkedHashSet<>(strings(
                anchor.path("implementation_fixed_non_control_sources")));
        Set<String> transitions = new LinkedHashSet<>(strings(
                anchor.path("implementation_transition_sources")));
        Set<String> partition = new LinkedHashSet<>(controls);
        partition.addAll(fixed);

        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo(
                "19db389aacad439f63cb93b930bea20ddd31f5e8");
        assertThat(checkpoint.path("parent_oid").asString()).isEqualTo(
                "4c47d1ea220ae9e310338bbf23b74d87d477e20f");
        assertThat(checkpoint.path("root_tree_oid").asString()).isEqualTo(
                "76ddb6bfd9a864c350dcdf86303518404227afae");
        assertThat(checkpoint.path("changed_path_count").asInt()).isEqualTo(55);
        assertThat(checkpoint.path("added_count").asInt()).isEqualTo(18);
        assertThat(checkpoint.path("modified_count").asInt()).isEqualTo(37);
        assertThat(checkpoint.path("deleted_count").asInt()).isZero();
        assertThat(artifacts).hasSize(55);
        assertThat(controls).hasSize(7).doesNotContainAnyElementsOf(fixed);
        assertThat(fixed).hasSize(48).containsAll(transitions);
        assertThat(transitions).hasSize(37);
        assertThat(partition).isEqualTo(properties(artifacts));
        assertThat(anchor.path("implementation_control_path_manifest_sha256")
                .asString()).isEqualTo(
                "b0d38af07b440adc413433c8307350fd135921117b42b0749d520ca26367e089");
        assertThat(anchor.path("implementation_fixed_manifest_sha256")
                .asString()).isEqualTo(
                "f701ca15dc594369a43234f5b0615d6ad7d7e27a80e30c013002650084faefd7");
        assertThat(anchor.path("implementation_transition_manifest_sha256")
                .asString()).isEqualTo(
                "3a360d9e4c636b8c3e731bacd7d0598c75d73c1e77d18c013c7131569e16e6e3");
        assertThat(transitions).allSatisfy(relative ->
                assertThat(artifacts.path(relative).path("change_type")
                        .asString()).as(relative).isEqualTo("M"));
        for (String relative : partition) {
            String accepted = artifacts.path(relative)
                    .path("sha256").asString();
            assertThat(
                    Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                            .acceptedSha256(root(), relative))
                    .as(relative)
                    .isEqualTo(accepted);
        }
    }

    @Test
    void fixesIndependentAcceptanceAsExactTwoAddedModes() throws Exception {
        JsonNode contract = contract();
        JsonNode checkpoint = contract.path(
                "independent_acceptance_checkpoint");
        JsonNode artifacts = checkpoint.path("artifacts");
        String evidence = "docs/refactor/phase4c/"
                + "personal-bank-tag-migration-execution-protocol-"
                + "independent-acceptance-evidence.json";
        String runner = "tools/run_phase4c_tag_migration_execution_protocol_"
                + "independent_acceptance.sh";

        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo(
                "aff3c9e8d6b1ed33dc0a050c0e435572cddd51db");
        assertThat(checkpoint.path("parent_oid").asString()).isEqualTo(
                "19db389aacad439f63cb93b930bea20ddd31f5e8");
        assertThat(checkpoint.path("changed_path_count").asInt()).isEqualTo(2);
        assertThat(checkpoint.path("added_count").asInt()).isEqualTo(2);
        assertThat(checkpoint.path("modified_count").asInt()).isZero();
        assertThat(checkpoint.path("deleted_count").asInt()).isZero();
        assertThat(properties(artifacts)).containsExactlyInAnyOrder(
                evidence, runner);
        assertAddedArtifact(
                artifacts.path(evidence), "100644",
                "eb874216f39a008d2da6df51d31471dd1dc11773781f840cd06afa87ebddf993",
                9_561L);
        assertAddedArtifact(
                artifacts.path(runner), "100755",
                "127a99443a670362e81349742477f5ba596df5694fe50fec6b64f485ece3d994",
                66_124L);
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .acceptedSha256(root(), evidence))
                .isEqualTo(artifacts.path(evidence).path("sha256").asString());
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .acceptedSha256(root(), runner))
                .isEqualTo(artifacts.path(runner).path("sha256").asString());
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .acceptedSha256(root(), "tools/unknown.py"))
                .isNull();
    }

    @Test
    void retainsIndependentMavenComposeCleanupAndSourceDiscoveryTruth()
            throws Exception {
        JsonNode verification = contract().path("independent_copy_verification")
                .path("verification");
        JsonNode full = verification.path("maven_full");
        JsonNode focused = verification.path("focused_node_d");
        JsonNode compose = verification.path("compose");
        JsonNode cleanup = verification.path("cleanup");
        JsonNode discovery = verification.path("source_discovery");

        assertThat(full.path("surefire").path("tests").asInt()).isEqualTo(898);
        assertThat(full.path("failsafe").path("tests").asInt()).isEqualTo(178);
        assertThat(focused.path("unit").path("tests").asInt()).isEqualTo(31);
        assertThat(focused.path("execution_protocol_integration")
                .path("tests").asInt())
                .isEqualTo(2);
        assertThat(compose.path("service_count").asInt()).isEqualTo(3);
        assertThat(compose.path("healthy_service_count").asInt()).isEqualTo(3);
        assertThat(compose.path("all_services_healthy_after_restart")
                .asBoolean()).isTrue();
        assertThat(compose.path("source_worktree_bind_count").asInt()).isZero();
        assertThat(cleanup.path("container_residue").asInt()).isZero();
        assertThat(cleanup.path("network_residue").asInt()).isZero();
        assertThat(cleanup.path("volume_residue").asInt()).isZero();
        assertThat(cleanup.path("image_residue").asInt()).isZero();
        assertThat(discovery.path("executed_inside_independent_copy")
                .asBoolean()).isFalse();
        assertThat(discovery.path("claimed_independent_copy_test_count")
                .asInt()).isZero();
    }

    @Test
    void retainsWormRouteAndConservativeProductionAuthorization()
            throws Exception {
        JsonNode contract = contract();
        JsonNode boundary = contract.path("production_and_worm_boundary");
        JsonNode worm = boundary.path("worm");
        JsonNode route = contract.path("route_state");
        JsonNode authorization = contract.path("authorization");

        assertThat(worm.path("current_report").path("sha256").asString())
                .isEqualTo(
                        "5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c");
        assertThat(worm.path("current_build_context_sha256").asString())
                .isEqualTo(
                        "36978a808a327abfb3c7b3dfe138f5622000213a25bad762b59128c78894d7c7");
        assertThat(worm.path("dockerfile_sha256").asString()).isEqualTo(
                "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499");
        assertThat(route.path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(route.path("pending_operation_count").asInt()).isEqualTo(598);
        assertThat(route.path("production_cutover_operation_count").asInt())
                .isZero();
        assertThat(route.path("legacy_flask_remains_production_owner")
                .asBoolean()).isTrue();
        for (String field : List.of(
                "migration_design_closed", "production_schema_or_index",
                "flyway_baseline_or_migration",
                "backup_and_rollback_evidence_closed",
                "real_data_migration_execution",
                "legacy_runtime_permanently_disabled",
                "route_or_openapi_delta", "client_gateway_or_proxy_change",
                "production_cutover")) {
            assertThat(authorization.path(field).asBoolean())
                    .as(field).isFalse();
        }
        assertThat(contract.path("acceptance")
                .path("anchor_closes_no_functional_gate").asBoolean()).isTrue();
    }

    @Test
    void sixCurrentControlsRemainGitlessAndCannotAuthorizeThemselves()
            throws Exception {
        JsonNode contract = contract();
        JsonNode current = contract.path("current_node_trust_boundary");
        Set<String> anchored = properties(contract
                .path("implementation_checkpoint").path("artifacts"));
        anchored.addAll(properties(contract.path(
                "independent_acceptance_checkpoint").path("artifacts")));

        assertThat(strings(current.path("control_sources")))
                .containsExactlyElementsOf(
                        Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                                .currentControlSources());
        assertThat(strings(current.path("control_sources")))
                .doesNotContainAnyElementsOf(anchored);
        assertThat(current.path("control_source_count").asInt()).isEqualTo(6);
        assertThat(current.path("control_sources_excluded_from_self_authority")
                .asBoolean()).isTrue();
        assertThat(current.path("control_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();
        assertThat(current.path("d2_commit_or_tree_identity_embedded")
                .asBoolean()).isFalse();
        for (String relative : strings(current.path("control_sources"))) {
            assertThat(
                    Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                            .acceptedSha256(root(), relative))
                    .as(relative).isNull();
        }

        String acceptanceSource = Files.readString(root().resolve(
                "server/src/test/java/io/saksk/ti/architecture/"
                        + "Phase4cTagMigrationExecutionProtocolPostPushAnchor"
                        + "SuccessorAcceptance.java"));
        assertThat(acceptanceSource).doesNotContain(
                "ProcessBuilder", "Runtime.getRuntime().exec",
                "org.eclipse.jgit");
    }

    @Test
    void minimalGitlessFixturePassesAndEveryRequiredPhysicalInputIsFixed(
            @TempDir Path temporary
    ) throws Exception {
        Path fixture = temporary.resolve("Ti-Java");
        Files.createDirectories(fixture);
        List<String> inputs = List.of(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .contractRelative(),
                "docs/refactor/phase4c/"
                        + "personal-bank-tag-migration-execution-protocol-contract.json",
                "docs/refactor/phase4c/"
                        + "personal-bank-tag-migration-execution-protocol-"
                        + "independent-acceptance-evidence.json",
                "tools/run_phase4c_tag_migration_execution_protocol_"
                        + "independent_acceptance.sh",
                "docs/refactor/05-progress.md");
        for (String relative : inputs) {
            Path target = fixture.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(relative), target);
        }
        Path runnerPath = fixture.resolve(inputs.get(3));
        Files.setPosixFilePermissions(runnerPath, Set.of(
                PosixFilePermission.OWNER_READ,
                PosixFilePermission.OWNER_WRITE,
                PosixFilePermission.OWNER_EXECUTE,
                PosixFilePermission.GROUP_READ,
                PosixFilePermission.GROUP_EXECUTE,
                PosixFilePermission.OTHERS_READ,
                PosixFilePermission.OTHERS_EXECUTE));
        assertThat(temporary.resolve(".git")).doesNotExist();
        Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                .load(fixture);
        String anchoredSample = inputs.get(1);
        String anchoredSampleSha256 = contract()
                .path("implementation_checkpoint").path("artifacts")
                .path(anchoredSample).path("sha256").asString();
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .acceptedSha256(fixture, anchoredSample))
                .isEqualTo(anchoredSampleSha256);
        Path anchoredSamplePath = fixture.resolve(anchoredSample);
        Files.writeString(
                anchoredSamplePath, "\n", StandardOpenOption.APPEND);
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .acceptedSha256(fixture, anchoredSample))
                .isNull();
        Files.copy(root().resolve(anchoredSample), anchoredSamplePath,
                StandardCopyOption.REPLACE_EXISTING);

        Path contractPath = fixture.resolve(inputs.get(0));
        Files.writeString(contractPath, "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes");
        Files.copy(root().resolve(inputs.get(0)), contractPath,
                StandardCopyOption.REPLACE_EXISTING);

        Path evidencePath = fixture.resolve(inputs.get(2));
        Files.writeString(evidencePath, "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes");
        Files.copy(root().resolve(inputs.get(2)), evidencePath,
                StandardCopyOption.REPLACE_EXISTING);

        Files.writeString(runnerPath, "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("runner fixed bytes");
        Files.copy(root().resolve(inputs.get(3)), runnerPath,
                StandardCopyOption.REPLACE_EXISTING);
        Files.setPosixFilePermissions(runnerPath, Set.of(
                PosixFilePermission.OWNER_READ,
                PosixFilePermission.OWNER_WRITE,
                PosixFilePermission.GROUP_READ,
                PosixFilePermission.OTHERS_READ));
        assertThatThrownBy(() ->
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("runner mode");
        assertThat(
                Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                        .acceptedSha256(fixture, inputs.get(3)))
                .isNull();
    }

    private static void assertAddedArtifact(
            JsonNode artifact,
            String mode,
            String sha256,
            long byteCount
    ) {
        assertThat(artifact.path("change_type").asString()).isEqualTo("A");
        assertThat(artifact.path("previous_mode").asString())
                .isEqualTo("000000");
        assertThat(artifact.path("mode").asString()).isEqualTo(mode);
        assertThat(artifact.path("previous_git_blob_oid").asString())
                .isEqualTo("0".repeat(40));
        assertThat(artifact.path("sha256").asString()).isEqualTo(sha256);
        assertThat(artifact.path("byte_count").asLong()).isEqualTo(byteCount);
    }

    private static JsonNode contract() throws Exception {
        return Phase4cTagMigrationExecutionProtocolPostPushAnchorSuccessorAcceptance
                .load(root());
    }

    private static List<String> strings(JsonNode array) {
        List<String> result = new ArrayList<>();
        array.forEach(value -> result.add(value.asString()));
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
