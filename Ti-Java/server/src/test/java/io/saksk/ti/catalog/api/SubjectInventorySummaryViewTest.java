package io.saksk.ti.catalog.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import org.junit.jupiter.api.Test;

class SubjectInventorySummaryViewTest {

    @Test
    void preservesSignedIdsExactNamesNullableLockStateAndLongCounts() {
        var minimum = new SubjectInventorySummaryView(Integer.MIN_VALUE, "", null, 0);
        var maximum = new SubjectInventorySummaryView(
                Integer.MAX_VALUE, "科目 🧪", true, Long.MAX_VALUE);

        assertThat(minimum.id()).isEqualTo(Integer.MIN_VALUE);
        assertThat(minimum.name()).isEmpty();
        assertThat(minimum.isLocked()).isNull();
        assertThat(minimum.questionCount()).isZero();
        assertThat(maximum.id()).isEqualTo(Integer.MAX_VALUE);
        assertThat(maximum.name()).isEqualTo("科目 🧪");
        assertThat(maximum.isLocked()).isTrue();
        assertThat(maximum.questionCount()).isEqualTo(Long.MAX_VALUE);
    }

    @Test
    void acceptsZeroIdButRejectsMissingNameAndNegativeCounts() {
        assertThat(new SubjectInventorySummaryView(0, "  ", false, 1).id()).isZero();
        assertThatNullPointerException()
                .isThrownBy(() -> new SubjectInventorySummaryView(1, null, false, 0))
                .withMessage("name");
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new SubjectInventorySummaryView(1, "name", false, -1))
                .withMessage("questionCount must not be negative");
    }
}
