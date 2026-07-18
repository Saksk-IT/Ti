package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Map;
import java.util.Objects;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity gate for the Phase 4C full-parity bootstrap. */
class Phase4cPersonalBankUserCountsHttpFullParityContractParityTest {

    @Test
    void closesAllFourEvidenceGatesButKeepsRoutesPending() throws Exception {
        JsonNode contract = Phase4cHttpFullParitySuccessorAcceptance.load(root());
        JsonNode parity = contract.path("parity");
        assertThat(parity.path("pg16_pg18_termination_fingerprints_complete").asBoolean())
                .isTrue();
        assertThat(parity.path("real_tomcat_complete_response_header_matrix_complete")
                .asBoolean()).isTrue();
        assertThat(parity.path("same_service_redis_outage_and_recovery_complete")
                .asBoolean()).isTrue();
        assertThat(parity.path("full_target_parity_closed").asBoolean()).isTrue();

        JsonNode authorization = contract.path("authorization");
        assertThat(authorization.path("current_bootstrap_sources_external_git_anchor_complete")
                .asBoolean()).isFalse();
        assertThat(authorization.path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(authorization.path("production_cutover").asBoolean()).isFalse();
        assertThat(contract.path("route_state").path("migrated_operation_count").asInt())
                .isEqualTo(11);
        assertThat(contract.path("route_state").path("pending_operation_count").asInt())
                .isEqualTo(600);
    }

    @Test
    void fixesThreeWorkerObjectsAndSixEvidenceFiles() throws Exception {
        JsonNode contract = Phase4cHttpFullParitySuccessorAcceptance.load(root());
        assertThat(contract.path("worker_integration").path("lane_count").asInt())
                .isEqualTo(3);
        assertThat(contract.path("worker_integration").path("lanes"))
                .hasSize(3);
        assertThat(contract.path("worker_integration").path("artifacts"))
                .hasSize(6);
        assertThat(Phase4cHttpFullParitySuccessorAcceptance.artifacts())
                .hasSize(6);
        for (Map.Entry<String, Phase4cHttpFullParitySuccessorAcceptance.Artifact> entry
                : Phase4cHttpFullParitySuccessorAcceptance.artifacts().entrySet()) {
            JsonNode descriptor = contract.path("worker_integration")
                    .path("artifacts").path(entry.getKey());
            assertThat(descriptor.path("sha256").asString())
                    .isEqualTo(entry.getValue().sha256());
            assertThat(descriptor.path("byte_count").asLong())
                    .isEqualTo(entry.getValue().bytes());
        }
    }

    @Test
    void fixesTheExactVerificationTotals() throws Exception {
        JsonNode verification = Phase4cHttpFullParitySuccessorAcceptance.load(root())
                .path("verification");
        assertThat(verification.path("targeted_failsafe_tests").asInt()).isEqualTo(13);
        assertThat(verification.path("targeted_failures_errors_skipped").asInt()).isZero();
        assertThat(verification.path("full_surefire_tests").asInt()).isEqualTo(709);
        assertThat(verification.path("full_failsafe_tests").asInt()).isEqualTo(167);
        assertThat(verification.path("full_failures_errors_skipped").asInt()).isZero();
        assertThat(verification.path("full_total_time").asString()).isEqualTo("07:02 min");
        assertThat(verification.path("testcontainers_remaining_after_verification").asInt())
                .isZero();
    }

    @Test
    void rejectsContractAndEvidenceTampering(@TempDir Path temporary) throws Exception {
        copyFixture(temporary);
        Path contract = temporary.resolve(
                Phase4cHttpFullParitySuccessorAcceptance.contractRelative());
        Files.writeString(contract, " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cHttpFullParitySuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes drifted");

        copyFixture(temporary);
        String evidence = Phase4cHttpFullParitySuccessorAcceptance.artifacts()
                .keySet().iterator().next();
        Files.writeString(temporary.resolve(evidence), " ", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cHttpFullParitySuccessorAcceptance.load(temporary))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed bytes drifted");
    }

    @Test
    void keepsSixBootstrapControlSourcesOutsideSelfAuthority() throws Exception {
        JsonNode authority = Phase4cHttpFullParitySuccessorAcceptance.load(root())
                .path("source_authority");
        assertThat(authority.path("control_source_count").asInt()).isEqualTo(6);
        assertThat(authority.path("control_sources")).hasSize(6);
        assertThat(authority.path("excluded_from_self_authority").asBoolean()).isTrue();
        assertThat(authority.path("historical_contracts_and_worm_overwritten").asBoolean())
                .isFalse();
    }

    private static void copyFixture(Path targetRoot) throws Exception {
        String predecessor = "docs/refactor/phase4c/"
                + "personal-bank-user-counts-http-typed-normalization-anchor-contract.json";
        copy(root(), targetRoot, Phase4cHttpFullParitySuccessorAcceptance.contractRelative());
        copy(root(), targetRoot, predecessor);
        for (String relative : Phase4cHttpFullParitySuccessorAcceptance.artifacts().keySet()) {
            copy(root(), targetRoot, relative);
        }
    }

    private static void copy(Path sourceRoot, Path targetRoot, String relative) throws Exception {
        Path target = targetRoot.resolve(relative);
        Files.createDirectories(target.getParent());
        Files.copy(sourceRoot.resolve(relative), target, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
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
