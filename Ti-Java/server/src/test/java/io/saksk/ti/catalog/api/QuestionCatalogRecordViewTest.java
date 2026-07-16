package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class QuestionCatalogRecordViewTest {

    @Test
    void preservesRawCompatibilityTextAndNullableLegacyColumns() {
        var view = new QuestionCatalogRecordView(
                7,
                null,
                "unknown",
                "raw content",
                "{not-json",
                "not-json]",
                null,
                "legacy,tag",
                null,
                "legacy/path.png",
                null,
                null,
                null,
                null,
                LocalDateTime.of(2026, 7, 16, 10, 30));

        assertThat(view.optionsRaw()).isEqualTo("{not-json");
        assertThat(view.answerRaw()).isEqualTo("not-json]");
        assertThat(view.tagsRaw()).isEqualTo("legacy,tag");
        assertThat(view.subjectId()).isNull();
        assertThat(view.createdAt()).isNull();
    }

    @Test
    void preservesLegacyZeroPrimaryKeyAndRejectsNegativeIdsAndRequiredColumnNulls() {
        assertThat(view(0, "essay", "content").id()).isZero();
        assertThatThrownBy(() -> view(-1, "essay", "content"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> view(1, null, "content"))
                .isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> view(1, "essay", null))
                .isInstanceOf(NullPointerException.class);
    }

    private static QuestionCatalogRecordView view(long id, String type, String content) {
        return new QuestionCatalogRecordView(
                id, null, type, content, null, null, null, null, null, null, null,
                null, null, null, null);
    }
}
