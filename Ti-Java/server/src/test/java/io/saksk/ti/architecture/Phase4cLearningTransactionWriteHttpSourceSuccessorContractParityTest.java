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

/** Java parity for the transaction-write source/runtime successor. */
class Phase4cLearningTransactionWriteHttpSourceSuccessorContractParityTest {

    @Test
    void loadsRuntimeAndWormWithoutPromotingRoutes() throws Exception {
        JsonNode contract =
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .load(root());
        assertThat(contract.path("contract_id").asString()).isEqualTo(
                "ti.phase4c.learning-transaction-write-http-"
                        + "source-successor-contract");
        assertThat(contract.path("semantic_successors")
                .path("full_runtime").path("current_file_count").asInt())
                .isEqualTo(395);
        assertThat(contract.path("semantic_successors")
                .path("learning_personalbank_main")
                .path("current_file_count").asInt()).isEqualTo(105);
        assertThat(contract.path("semantic_successors")
                .path("java_build_context_and_worm")
                .path("current_chain_node_count").asInt()).isEqualTo(10);
        assertThat(contract.path("authorization")
                .path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(contract.path("route_state")
                .path("migrated_operation_count").asInt()).isEqualTo(13);
        assertThat(contract.path("route_state")
                .path("pending_operation_count").asInt()).isEqualTo(598);
    }

    @Test
    void composesNodeDRuntimeToCurrentPhysicalManifest() throws Exception {
        Map<String, String> accepted =
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .nodeDCurrentRuntimeManifest(root());
        Map<String, String> current =
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .productionRuntimeManifest(root());
        var successor =
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(), accepted, current, "full_runtime");
        assertThat(successor.acceptedFileCount()).isEqualTo(311);
        assertThat(successor.currentFileCount()).isEqualTo(395);
        assertThat(successor.addedFiles()).hasSize(84);
        assertThat(successor.changedFiles()).hasSize(10);
        assertThat(successor.deletedFiles()).isEmpty();

        Map<String, String> acceptedScoped = accepted.entrySet().stream()
                .filter(entry -> entry.getKey().startsWith(
                        "server/src/main/java/io/saksk/ti/learning/")
                        || entry.getKey().startsWith(
                        "server/src/main/java/io/saksk/ti/personalbank/"))
                .collect(java.util.stream.Collectors.toMap(
                        Map.Entry::getKey, Map.Entry::getValue));
        Map<String, String> currentScoped = current.entrySet().stream()
                .filter(entry -> entry.getKey().startsWith(
                        "server/src/main/java/io/saksk/ti/learning/")
                        || entry.getKey().startsWith(
                        "server/src/main/java/io/saksk/ti/personalbank/"))
                .collect(java.util.stream.Collectors.toMap(
                        Map.Entry::getKey, Map.Entry::getValue));
        var scoped =
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .validateProductionRuntimeSuccessor(
                                root(),
                                acceptedScoped,
                                currentScoped,
                                "learning_personalbank_main");
        assertThat(scoped.acceptedFileCount()).isEqualTo(54);
        assertThat(scoped.currentFileCount()).isEqualTo(105);
    }

    @Test
    void composesNodeNineToTenWithoutRouteAuthority() throws Exception {
        var successor =
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .validateWormSuccessor(
                                root(),
                                "5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c",
                                "36978a808a327abfb3c7b3dfe138f5622000213a25bad762b59128c78894d7c7",
                                "5e4247d0a43405661cef27b91b4169273e8ad096bfa750b4ba4488ca6c247224");
        assertThat(successor.acceptedChainNodeCount()).isEqualTo(9);
        assertThat(successor.currentChainNodeCount()).isEqualTo(10);
        assertThat(successor.currentReportSha256()).isEqualTo(
                "dd165106d7b3a73512acdbf89924b352e3f1ad027132b8a8519af957a47de599");
    }

    @Test
    void minimalGitlessFixtureLoadsAndTamperFailsClosed(
            @TempDir Path temporaryDirectory
    ) throws Exception {
        Path fixture = temporaryDirectory.resolve("fixture");
        for (String relative
                : Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                .minimalFixturePaths(root())) {
            Path target = fixture.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(
                    root().resolve(relative),
                    target,
                    StandardCopyOption.COPY_ATTRIBUTES);
        }
        assertThat(
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .load(fixture).path("contract_id").asString())
                .contains("source-successor");

        String relative = "server/src/main/resources/application.yml";
        Files.writeString(
                fixture.resolve(relative),
                "\n# tampered\n",
                StandardOpenOption.APPEND);
        assertThatThrownBy(() ->
                Phase4cLearningTransactionWriteHttpSourceSuccessorAcceptance
                        .load(fixture))
                .isInstanceOf(AssertionError.class)
                .hasMessageContaining("transition drifted");
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
