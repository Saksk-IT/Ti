package io.saksk.ti.operations.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class QuizLimitPolicyArchitectureTest {

    @Test
    void operationsOwnsTheConfigurationReadAndExposesOnlyAnImmutableView()
            throws Exception {
        assertThat(QuizLimitPolicyQueryService.class
                        .getDeclaredMethod("getQuizLimitPolicy")
                        .getAnnotation(Transactional.class))
                .satisfies(transaction ->
                        assertThat(transaction.readOnly()).isTrue());

        String adapter = Files.readString(serverRoot().resolve(
                "src/main/java/io/saksk/ti/operations/infrastructure/persistence/"
                        + "JdbcQuizLimitPolicyReadAdapter.java"));
        assertThat(adapter).contains(
                "FROM system_config",
                "quiz_limit_enabled",
                "quiz_limit_count");
        assertThat(adapter).doesNotContain(
                "user_quiz_stats",
                "mistakes",
                "user_answers",
                "questions",
                "users");
    }

    private static Path serverRoot() {
        return Path.of(Objects.requireNonNull(
                        System.getProperty("basedir"),
                        "Maven must provide server basedir"))
                .toAbsolutePath()
                .normalize();
    }
}
