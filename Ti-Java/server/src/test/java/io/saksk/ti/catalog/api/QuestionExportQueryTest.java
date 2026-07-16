package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import java.util.Optional;
import org.junit.jupiter.api.Test;

class QuestionExportQueryTest {

    @Test
    void preservesAbsentAndTheCompleteSignedIntegerSubjectDomain() {
        assertThat(new QuestionExportQuery(Optional.empty()).subjectId()).isEmpty();
        assertThat(new QuestionExportQuery(Optional.of(Integer.MIN_VALUE)).subjectId())
                .contains(Integer.MIN_VALUE);
        assertThat(new QuestionExportQuery(Optional.of(0)).subjectId()).contains(0);
        assertThat(new QuestionExportQuery(Optional.of(Integer.MAX_VALUE)).subjectId())
                .contains(Integer.MAX_VALUE);
    }

    @Test
    void rejectsOnlyANullOptionalContainer() {
        assertThatNullPointerException()
                .isThrownBy(() -> new QuestionExportQuery(null))
                .withMessage("subjectId");
    }
}
