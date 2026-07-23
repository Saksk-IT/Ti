package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class FavoriteWriteArchitectureTest {

    @Test
    void crossModuleReadsStayOutsideTheLearningWriteTransaction() throws Exception {
        assertThat(FavoriteApplicationService.class.getAnnotation(Transactional.class))
                .isNull();
        assertThat(FavoriteApplicationService.class
                        .getDeclaredMethod(
                                "toggleFavorite",
                                io.saksk.ti.learning.api.ToggleFavoriteCommand.class)
                        .getAnnotation(Transactional.class))
                .isNull();
        assertThat(FavoriteWriteTransaction.class
                        .getDeclaredMethod(
                                "execute",
                                long.class,
                                long.class,
                                io.saksk.ti.learning.api.LearningWriteIdempotencyKey.class,
                                byte[].class)
                        .getAnnotation(Transactional.class))
                .isNotNull();
    }

    @Test
    void favoriteAdapterMutatesOnlyTheLearningOwnedFavoriteTable() throws Exception {
        String source = Files.readString(serverRoot().resolve(
                "src/main/java/io/saksk/ti/learning/infrastructure/persistence/"
                        + "JdbcFavoriteToggleAdapter.java"));

        assertThat(source).contains(
                "FROM favorites",
                "DELETE FROM favorites",
                "INSERT INTO favorites");
        assertThat(source).doesNotContain(
                "FROM questions",
                "JOIN questions",
                "FROM subjects",
                "JOIN subjects",
                "FROM users",
                "JOIN users",
                "catalog_question_edit_commands");
    }

    private static Path serverRoot() {
        return Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
    }
}
