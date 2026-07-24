package io.saksk.ti.architecture;

import tools.jackson.databind.JsonNode;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Objects;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Cross-language parity for transaction-write full target execution. */
class Phase4cLearningTransactionWriteHttpFullParityContractParityTest {

    @Test
    void loadsFullParityWithoutPromotingRoutes() throws Exception {
        JsonNode contract =
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .load(root());
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.learning-transaction-write-http-"
                        + "full-parity-contract");
        assertThat(contract.path("parity")
                .path("full_target_parity_closed").asBoolean()).isTrue();
        assertThat(contract.path("parity")
                .path("operation_count").asInt()).isEqualTo(9);
        assertThat(contract.path("authorization")
                .path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(contract.path("route_state")
                .path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(contract.path("route_state")
                .path("pending_operation_count").asInt()).isEqualTo(598);
    }

    @Test
    void composesNodeDTransitionsToCurrentPhysicalBytes() throws Exception {
        for (String relative : new String[] {
                "docs/refactor/05-progress.md",
                "infra/phase2/README.md",
                "infra/phase2/verify-static.sh"
        }) {
            var current =
                    Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                            .sourceTransition(root(), relative);
            assertThat(current).isNotNull();
            assertThat(
                    Phase4cTagMigrationExecutionProtocolSuccessorAcceptance
                            .successorSha256(root(), relative))
                    .isEqualTo(current.successorSha256());
        }
        assertThat(
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .sourceTransition(root(), "unknown"))
                .isNull();
    }

    @Test
    void minimalGitlessFixtureLoadsAndTamperFailsClosed(
            @TempDir Path temporaryDirectory
    ) throws Exception {
        Path fixture = temporaryDirectory.resolve("fixture");
        for (String relative
                : Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                .minimalFixturePaths(root())) {
            Path target = fixture.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(
                    root().resolve(relative),
                    target,
                    StandardCopyOption.COPY_ATTRIBUTES);
        }
        assertThat(
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .load(fixture).path("contract_id").asString())
                .contains("transaction-write-http-full-parity");

        String relative = "docs/refactor/05-progress.md";
        Files.writeString(
                fixture.resolve(relative),
                "\n# tampered\n",
                StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("fixed source drifted");
    }

    @Test
    void evidencePinsTomcatRedisPostgresOpenapiAndWorm() throws Exception {
        JsonNode evidence =
                Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance
                        .load(root()).path("fixed_evidence");
        assertThat(evidence.path(
                "real_random_port_tomcat_full_filter_chain").asBoolean())
                .isTrue();
        assertThat(evidence.path(
                "target_session_flask_session_and_bearer_to_controller")
                .asBoolean()).isTrue();
        assertThat(evidence.path(
                "redis_7_4_atomicity_outage_and_recovery").asBoolean())
                .isTrue();
        assertThat(evidence.path("postgresql_versions").get(0).asString())
                .isEqualTo("16.14");
        assertThat(evidence.path("postgresql_versions").get(1).asString())
                .isEqualTo("18.4");
        assertThat(evidence.path(
                "openapi_3_1_2_exact_operation_count").asInt()).isEqualTo(9);
        assertThat(evidence.path("worm_chain_node_count").asInt())
                .isEqualTo(10);
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
