package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import java.util.Optional;
import org.junit.jupiter.api.Test;

class QuestionCatalogListQueryTest {

    @Test
    void preservesTheCompleteIntegerDomainAndExactQuestionTypeText() {
        var minimum = new QuestionCatalogListQuery(
                Optional.of(Integer.MIN_VALUE), Optional.of(""));
        var maximum = new QuestionCatalogListQuery(
                Optional.of(Integer.MAX_VALUE), Optional.of("  "));
        var zero = new QuestionCatalogListQuery(Optional.of(0), Optional.empty());

        assertThat(minimum.subjectId()).contains(Integer.MIN_VALUE);
        assertThat(minimum.questionType()).contains("");
        assertThat(maximum.subjectId()).contains(Integer.MAX_VALUE);
        assertThat(maximum.questionType()).contains("  ");
        assertThat(zero.subjectId()).contains(0);
        assertThat(zero.questionType()).isEmpty();
    }

    @Test
    void requiresBothOptionalContainers() {
        assertThatNullPointerException()
                .isThrownBy(() -> new QuestionCatalogListQuery(null, Optional.empty()))
                .withMessage("subjectId");
        assertThatNullPointerException()
                .isThrownBy(() -> new QuestionCatalogListQuery(Optional.empty(), null))
                .withMessage("questionType");
    }
}
