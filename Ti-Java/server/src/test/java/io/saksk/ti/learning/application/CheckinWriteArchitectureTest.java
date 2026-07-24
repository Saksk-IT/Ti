package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class CheckinWriteArchitectureTest {

    @Test
    void applicationDerivesBeijingTimeOutsideOneLearningTransaction()
            throws Exception {
        assertThat(CheckinApplicationService.class.getAnnotation(Transactional.class))
                .isNull();
        assertThat(CheckinApplicationService.class
                        .getDeclaredMethod(
                                "checkIn",
                                io.saksk.ti.learning.api.CheckinCommand.class)
                        .getAnnotation(Transactional.class))
                .isNull();
        assertThat(CheckinWriteTransaction.class
                        .getDeclaredMethod(
                                "execute",
                                long.class,
                                java.time.LocalDate.class,
                                java.time.LocalDateTime.class,
                                io.saksk.ti.learning.api.LearningWriteIdempotencyKey.class,
                                byte[].class)
                        .getAnnotation(Transactional.class))
                .isNotNull();
    }

    @Test
    void adapterTouchesOnlyTheLearningOwnedCheckinTable() throws Exception {
        String source = Files.readString(serverRoot().resolve(
                "src/main/java/io/saksk/ti/learning/infrastructure/persistence/"
                        + "JdbcCheckinStateAdapter.java"));

        assertThat(source).contains(
                "INSERT INTO user_checkins",
                "FROM user_checkins",
                "COUNT(*)",
                "ORDER BY checkin_date");
        assertThat(source).doesNotContain(
                "FROM users",
                "JOIN users",
                "FROM user_answers",
                "JOIN user_answers",
                "FROM questions",
                "JOIN questions",
                "FROM subjects",
                "JOIN subjects");
    }

    private static Path serverRoot() {
        return Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
    }
}
