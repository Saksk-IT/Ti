package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import org.junit.jupiter.api.Test;

class SubjectContextViewTest {

    @Test
    void preservesSignedIdsAndExactNamesWithoutTrimmingOrBlankRejection() {
        var minimum = new SubjectContextView(Integer.MIN_VALUE, "");
        var zero = new SubjectContextView(0, "  ");
        var maximum = new SubjectContextView(Integer.MAX_VALUE, "科目 🧪");

        assertThat(minimum.id()).isEqualTo(Integer.MIN_VALUE);
        assertThat(minimum.name()).isEmpty();
        assertThat(zero.id()).isZero();
        assertThat(zero.name()).isEqualTo("  ");
        assertThat(maximum.id()).isEqualTo(Integer.MAX_VALUE);
        assertThat(maximum.name()).isEqualTo("科目 🧪");
    }

    @Test
    void rejectsOnlyAMissingRequiredName() {
        assertThatNullPointerException()
                .isThrownBy(() -> new SubjectContextView(1, null))
                .withMessage("name");
    }
}

