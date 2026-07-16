package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class QuestionCatalogSummaryViewTest {

    @Test
    void preservesTheCompleteSignedIdDomainNullableColumnsAndMalformedRawText() {
        LocalDateTime updatedAt = LocalDateTime.of(2026, 7, 16, 12, 13, 14);
        var view = new QuestionCatalogSummaryView(
                Long.MIN_VALUE,
                null,
                "",
                "raw content",
                null,
                "{not-json-tags",
                "[not-json-image",
                null,
                updatedAt);

        assertThat(view.id()).isEqualTo(Long.MIN_VALUE);
        assertThat(view.subjectId()).isNull();
        assertThat(view.type()).isEmpty();
        assertThat(view.content()).isEqualTo("raw content");
        assertThat(view.difficulty()).isNull();
        assertThat(view.tagsRaw()).isEqualTo("{not-json-tags");
        assertThat(view.imagePathRaw()).isEqualTo("[not-json-image");
        assertThat(view.createdBy()).isNull();
        assertThat(view.updatedAt()).isEqualTo(updatedAt);
    }

    @Test
    void acceptsZeroAndMaximumIdsButRejectsRequiredTextGaps() {
        assertThat(view(0, "type", "content").id()).isZero();
        assertThat(view(Long.MAX_VALUE, "type", "content").id())
                .isEqualTo(Long.MAX_VALUE);
        assertThatNullPointerException()
                .isThrownBy(() -> view(1, null, "content"))
                .withMessage("type");
        assertThatNullPointerException()
                .isThrownBy(() -> view(1, "type", null))
                .withMessage("content");
    }

    private static QuestionCatalogSummaryView view(long id, String type, String content) {
        return new QuestionCatalogSummaryView(
                id, null, type, content, null, null, null, null, null);
    }
}
