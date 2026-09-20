package io.saksk.ti.architecture;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Objects;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class Phase4cLearningTransactionWriteHttpFullParityAnchorContractParityTest {
    private static Path root() {
        return Path.of(Objects.requireNonNull(System.getProperty("basedir"))).toAbsolutePath().getParent();
    }

    @Test
    void fixedBootstrapIsAnchoredWithoutPromotingRoutes() throws Exception {
        var document = Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.load(root());
        var checkpoint = document.path("git_checkpoint");
        assertThat(checkpoint.path("commit_oid").asString()).isEqualTo("6ed81347467a4155887300b7e4ae36589204af79");
        assertThat(checkpoint.path("changed_path_count").asInt()).isEqualTo(8);
        assertThat(checkpoint.path("added_path_count").asInt()).isEqualTo(6);
        assertThat(checkpoint.path("modified_path_count").asInt()).isEqualTo(2);
        assertThat(document.path("authorization").path("bootstrap_control_sources_external_git_anchor_complete").asBoolean()).isTrue();
        assertThat(document.path("authorization").path("current_anchor_sources_external_git_anchor_complete").asBoolean()).isFalse();
        assertThat(document.path("authorization").path("route_migration_eligible").asBoolean()).isFalse();
        assertThat(document.path("route_state").path("migrated_operation_count").asInt()).isEqualTo(13);
    }

    @Test
    void gitlessFixtureAndSnapshotTamper(@TempDir Path fixture) throws Exception {
        copyFixture(fixture);
        assertThat(Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.load(fixture))
                .isEqualTo(Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.load(root()));
        Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.load(fixture);
        Files.writeString(fixture.resolve(Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.SNAPSHOT),
                "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.load(fixture))
                .isInstanceOf(AssertionError.class).hasMessageContaining("fixed source drifted");
    }

    @Test
    void progressTamperAndWrongOriginFailClosed(@TempDir Path fixture) throws Exception {
        copyFixture(fixture);
        assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance
                .acceptsProgress(fixture, "docs/refactor/05-progress.md", "0".repeat(64), 0))
                .isInstanceOf(AssertionError.class).hasMessageContaining("predecessor drifted");
        Files.writeString(fixture.resolve("docs/refactor/05-progress.md"), "\n", StandardOpenOption.APPEND);
        assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpFullParitySuccessorAcceptance.load(fixture))
                .isInstanceOf(AssertionError.class).hasMessageContaining("fixed source drifted");
    }

    @Test
    void rejectsSymlinksAndNoncanonicalPaths(@TempDir Path fixture) throws Exception {
        copyFixture(fixture);
        Path original = fixture.resolve(Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.SNAPSHOT);
        Path outside = fixture.resolve("elsewhere");
        Files.move(original, outside);
        Files.createSymbolicLink(original, outside);
        assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.load(fixture))
                .isInstanceOf(AssertionError.class).hasMessageContaining("symlink");
        for (String path : new String[] {"../outside", "/tmp/outside", "C:/outside", "a/../b", "a\\b"}) {
            assertThatThrownBy(() -> Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.fixedRegularFile(fixture, path))
                    .isInstanceOf(AssertionError.class).hasMessageContaining("escapes root");
        }
    }

    private static void copyFixture(Path fixture) throws Exception {
        for (String relative : Phase4cLearningTransactionWriteHttpFullParityAnchorSuccessorAcceptance.minimalFixturePaths(root())) {
            Path target = fixture.resolve(relative);
            Files.createDirectories(target.getParent());
            Files.copy(root().resolve(relative), target);
        }
    }
}
