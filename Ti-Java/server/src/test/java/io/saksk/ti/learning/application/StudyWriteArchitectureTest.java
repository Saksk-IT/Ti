package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class StudyWriteArchitectureTest {

    @Test
    void catalogAndPersonalBankScopeProofsStayOutsideLearningTransactions()
            throws Exception {
        assertThat(StudyApplicationService.class.getAnnotation(Transactional.class))
                .isNull();
        assertThat(StudyApplicationService.class
                        .getDeclaredMethod(
                                "recordLearning",
                                io.saksk.ti.learning.api.StudyLearnCommand.class)
                        .getAnnotation(Transactional.class))
                .isNull();
        assertThat(StudyWriteTransaction.class
                        .getDeclaredMethod(
                                "recordLearning",
                                long.class,
                                long.class,
                                boolean.class,
                                StudyApplicationService.ResolvedScope.class,
                                io.saksk.ti.learning.api.LearningWriteIdempotencyKey.class,
                                byte[].class)
                        .getAnnotation(Transactional.class))
                .isNotNull();
        assertThat(StudyWriteTransaction.class
                        .getDeclaredMethod(
                                "recordReview",
                                long.class,
                                long.class,
                                io.saksk.ti.learning.api.StudyReviewRating.class,
                                StudyApplicationService.ResolvedScope.class,
                                io.saksk.ti.learning.api.LearningWriteIdempotencyKey.class,
                                byte[].class)
                        .getAnnotation(Transactional.class))
                .isNotNull();
        assertThat(StudyWriteTransaction.class
                        .getDeclaredMethod(
                                "setReviewMastered",
                                long.class,
                                long.class,
                                boolean.class,
                                StudyApplicationService.ResolvedScope.class,
                                io.saksk.ti.learning.api.LearningWriteIdempotencyKey.class,
                                byte[].class)
                        .getAnnotation(Transactional.class))
                .isNotNull();
    }

    @Test
    void jdbcAdapterTouchesOnlyLearningOwnedStudyState() throws Exception {
        String source = Files.readString(serverRoot().resolve(
                "src/main/java/io/saksk/ti/learning/infrastructure/persistence/"
                        + "JdbcStudyStateAdapter.java"));

        assertThat(source).contains(
                "FROM study_learning",
                "INSERT INTO study_learning",
                "FROM study_review",
                "INSERT INTO study_review",
                "INSERT INTO mistakes",
                "INSERT INTO user_bank_mistakes",
                "pg_advisory_xact_lock");
        assertThat(source).doesNotContain(
                "FROM questions",
                "JOIN questions",
                "FROM subjects",
                "JOIN subjects",
                "FROM user_bank_questions",
                "JOIN user_bank_questions",
                "FROM user_question_banks",
                "JOIN user_question_banks",
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
