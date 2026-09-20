package io.saksk.ti.architecture;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class Phase4cLearningTransactionWriteHttpIntegrationSuccessorTest {
    private static final String PROGRESS = "docs/refactor/05-progress.md";

    @Test
    void everyFixedPredecessorComposesWithoutPromotingRoutes() throws Exception {
        var contract = Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.load(root());
        assertThat(contract.path("transitions").size()).isEqualTo(28);
        assertThat(contract.path("authorization").path("route_migration_eligible").asBoolean()).isFalse();
        for (var entry : contract.path("transitions").properties()) {
            for (var accepted : entry.getValue().path("accepted")) {
                assertThat(Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.accepts(
                        root(), entry.getKey(), accepted.path("sha256").asString(),
                        accepted.path("byte_count").asLong())).as(entry.getKey()).isTrue();
            }
        }
    }

    @Test
    void rejectsUnknownPredecessorsAndPaths() throws Exception {
        assertThat(Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.accepts(
                root(), PROGRESS, "0".repeat(64), 0)).isFalse();
        assertThat(Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.accepts(
                root(), "unknown", "0".repeat(64), 0)).isFalse();
    }

    @Test
    void gitlessFixtureRejectsChangedCurrentBytes(@TempDir Path fixture) throws Exception {
        copyFixture(fixture);
        var previous = Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.load(fixture)
                .path("transitions").path(PROGRESS).path("accepted").get(0);
        assertThat(Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.accepts(
                fixture, PROGRESS, previous.path("sha256").asString(), previous.path("byte_count").asLong())).isTrue();
        Files.writeString(fixture.resolve(PROGRESS), "\n", StandardOpenOption.APPEND);
        assertThat(Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.accepts(
                fixture, PROGRESS, previous.path("sha256").asString(), previous.path("byte_count").asLong())).isFalse();
    }

    @Test
    void rejectsModifiedContract(@TempDir Path fixture) throws Exception {
        copyFixture(fixture);
        Files.writeString(fixture.resolve(Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.CONTRACT),
                "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.load(fixture))
                .isInstanceOf(AssertionError.class);
    }

    @Test
    void rejectsSymlinksAndEscapingPaths(@TempDir Path fixture) throws Exception {
        copyFixture(fixture);
        Path target = fixture.resolve("outside.md");
        Files.move(fixture.resolve(PROGRESS), target);
        Files.createSymbolicLink(fixture.resolve(PROGRESS), target);
        assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.fixedFile(fixture, PROGRESS))
                .isInstanceOf(AssertionError.class);
        assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.fixedFile(fixture, "../outside"))
                .isInstanceOf(AssertionError.class);
    }

    private static void copyFixture(Path fixture) throws Exception {
        for (String relative : new String[]{PROGRESS, Phase4cLearningTransactionWriteHttpIntegrationSuccessorAcceptance.CONTRACT}) {
            Files.createDirectories(fixture.resolve(relative).getParent());
            Files.copy(root().resolve(relative), fixture.resolve(relative));
        }
    }

    private static Path root() {
        return Path.of(System.getProperty("basedir")).toAbsolutePath().getParent();
    }
}
