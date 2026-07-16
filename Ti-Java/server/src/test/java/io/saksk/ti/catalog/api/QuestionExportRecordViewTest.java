package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class QuestionExportRecordViewTest {

    @Test
    void preservesEveryRawValueWithoutProjectionOrValidation() {
        var row = new QuestionExportRecordView(
                -1,
                -7L,
                "",
                null,
                null,
                "{malformed",
                "true",
                "  ",
                null,
                "42");

        assertThat(row.id()).isEqualTo(-1);
        assertThat(row.subjectId()).isEqualTo(-7L);
        assertThat(row.subjectName()).isEmpty();
        assertThat(row.type()).isNull();
        assertThat(row.content()).isNull();
        assertThat(row.optionsRaw()).isEqualTo("{malformed");
        assertThat(row.answerRaw()).isEqualTo("true");
        assertThat(row.analysis()).isEqualTo("  ");
        assertThat(row.difficulty()).isNull();
        assertThat(row.tagsRaw()).isEqualTo("42");
    }
}
