package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Map;
import java.util.Objects;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity gate for the Phase 4C full-parity external anchor. */
class Phase4cPersonalBankUserCountsHttpFullParityAnchorContractParityTest {

    @Test
    void fixesTheExactBootstrapCommitAndCompleteDelta() throws Exception {
        JsonNode contract = Phase4cHttpFullParityAnchorSuccessorAcceptance.load(root());
        JsonNode checkpoint = contract.path("git_checkpoint");
        assertThat(checkpoint.path("commit_oid").asString())
                .isEqualTo("848af89cb99ae0330ec1f0955cf23749a044d40e");
        assertThat(checkpoint.path("parent_oid").asString())
                .isEqualTo("765e4470f1ddb60f0ce6f23227d6303961f47fcf");
        assertThat(checkpoint.path("root_tree_oid").asString())
                .isEqualTo("9cbb82ee611128bba95a3b726021dab9adde1011");
        assertThat(checkpoint.path("ti_java_tree_oid").asString())
                .isEqualTo("88107eea64154eccba9c48e853ba08a52371c27c");
        assertThat(checkpoint.path("changed_path_count").asInt()).isEqualTo(15);
        assertThat(checkpoint.path("added_path_count").asInt()).isEqualTo(12);
        assertThat(checkpoint.path("modified_path_count").asInt()).isEqualTo(3);
        assertThat(checkpoint.path("artifacts")).hasSize(15);
    }

    @Test
    void externallyAnchorsAllSixBootstrapControlSources() throws Exception {
        JsonNode contract = Phase4cHttpFullParityAnchorSuccessorAcceptance.load(root());
        JsonNode anchor = contract.path("full_parity_source_anchor");
        assertThat(anchor.path("source_count").asInt()).isEqualTo(6);
        assertThat(anchor.path("source_paths")).hasSize(6);
        assertThat(anchor.path("artifacts")).hasSize(6);
        assertThat(anchor.path("predecessor_bootstrap_sources_external_git_anchor_complete")
                .asBoolean()).isTrue();
        assertThat(anchor.path("current_anchor_sources_excluded_from_self_authority")
                .asBoolean()).isTrue();
        assertThat(anchor.path("current_anchor_source_bytes_external_git_anchor_complete")
                .asBoolean()).isFalse();
        for (Map.Entry<String, Phase4cHttpFullParityAnchorSuccessorAcceptance.Artifact> entry
                : Phase4cHttpFullParityAnchorSuccessorAcceptance.bootstrapSources().entrySet()) {
            JsonNode descriptor = anchor.path("artifacts").path(entry.getKey());
            assertThat(descriptor.path("sha256").asString())
                    .isEqualTo(entry.getValue().sha256());
            assertThat(descriptor.path("byte_count").asLong())
                    .isEqualTo(entry.getValue().bytes());
        }
    }

    @Test
    void makesRoutesEligibleWithoutPromotingOrCuttingOver() throws Exception {
        JsonNode contract = Phase4cHttpFullParityAnchorSuccessorAcceptance.load(root());
        JsonNode parity = contract.path("parity");
        assertThat(parity.path("pg16_pg18_termination_fingerprints_complete").asBoolean())
                .isTrue();
        assertThat(parity.path("real_tomcat_complete_response_header_matrix_complete")
                .asBoolean()).isTrue();
        assertThat(parity.path("same_service_redis_outage_and_recovery_complete")
                .asBoolean()).isTrue();
        assertThat(parity.path("full_target_parity_closed").asBoolean()).isTrue();
        JsonNode authorization = contract.path("authorization");
        assertThat(authorization.path("route_migration_eligible").asBoolean()).isTrue();
        assertThat(authorization.path("two_legacy_get_routes_migrated").asBoolean()).isFalse();
        assertThat(authorization.path("production_cutover").asBoolean()).isFalse();
        assertThat(contract.path("route_state").path("migrated_operation_count").asInt())
                .isEqualTo(11);
        assertThat(contract.path("route_state").path("pending_operation_count").asInt())
                .isEqualTo(600);
    }

    @Test
    void loadsFromAGitlessMinimalFixture(@TempDir Path temporary) throws Exception {
        copyFixture(temporary);
        assertThat(temporary.resolve(".git")).doesNotExist();
        assertThat(Phase4cHttpFullParityAnchorSuccessorAcceptance.load(temporary)
                .path("authorization").path("route_migration_eligible").asBoolean())
                .isTrue();
    }

    @Test
    void rejectsContractAndBootstrapSourceTampering(@TempDir Path temporary) throws Exception {
        copyFixture(temporary);
        Path contract = temporary.resolve(
                Phase4cHttpFullParityAnchorSuccessorAcceptance.contractRelative());
        Files.writeString(contract, " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cHttpFullParityAnchorSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes drifted");

        copyFixture(temporary);
        String source = Phase4cHttpFullParityAnchorSuccessorAcceptance.bootstrapSources()
                .keySet().iterator().next();
        Files.writeString(temporary.resolve(source), " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cHttpFullParityAnchorSuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes drifted");
    }

    private static void copyFixture(Path targetRoot) throws Exception {
        copy(Phase4cHttpFullParityAnchorSuccessorAcceptance.contractRelative(), targetRoot);
        for (String relative : Phase4cHttpFullParityAnchorSuccessorAcceptance
                .bootstrapSources().keySet()) {
            copy(relative, targetRoot);
        }
    }

    private static void copy(String relative, Path targetRoot) throws Exception {
        Path target = targetRoot.resolve(relative);
        Files.createDirectories(target.getParent());
        Files.copy(root().resolve(relative), target, StandardCopyOption.REPLACE_EXISTING);
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
