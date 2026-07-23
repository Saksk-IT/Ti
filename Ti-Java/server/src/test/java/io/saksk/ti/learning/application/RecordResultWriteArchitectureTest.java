package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class RecordResultWriteArchitectureTest {

    @Test
    void catalogIdentityAndQuotaConfigurationStayOutsideLearningTransaction()
            throws Exception {
        assertThat(RecordResultApplicationService.class
                        .getAnnotation(Transactional.class))
                .isNull();
        assertThat(RecordResultApplicationService.class
                        .getDeclaredMethod(
                                "recordResult",
                                io.saksk.ti.learning.api.RecordResultCommand.class)
                        .getAnnotation(Transactional.class))
                .isNull();
        assertThat(RecordResultWriteTransaction.class
                        .getDeclaredMethod(
                                "execute",
                                long.class,
                                boolean.class,
                                long.class,
                                boolean.class,
                                boolean.class,
                                io.saksk.ti.learning.api.QuizLimitPolicy.class,
                                io.saksk.ti.learning.api.LearningWriteIdempotencyKey.class,
                                byte[].class)
                        .getAnnotation(Transactional.class))
                .isNotNull();
    }

    @Test
    void jdbcAdapterTouchesOnlyLearningOwnedAnswerState() throws Exception {
        String source = Files.readString(serverRoot().resolve(
                "src/main/java/io/saksk/ti/learning/infrastructure/persistence/"
                        + "JdbcRecordResultStateAdapter.java"));

        assertThat(source).contains(
                "FROM user_quiz_stats",
                "INSERT INTO user_quiz_stats",
                "INSERT INTO mistakes",
                "DELETE FROM mistakes",
                "DELETE FROM user_answers",
                "INSERT INTO user_answers",
                "pg_advisory_xact_lock");
        assertThat(source).doesNotContain(
                "FROM questions",
                "JOIN questions",
                "FROM subjects",
                "JOIN subjects",
                "FROM system_config",
                "JOIN system_config",
                "FROM users",
                "JOIN users");
    }

    private static Path serverRoot() {
        return Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
    }
}
