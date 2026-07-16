package io.saksk.ti.personalbank.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class PersonalBankCategoryViewTest {

    @Test
    void preservesSignedIdsExactNamesNullableMetadataAndLongCounts() {
        var nullable = new PersonalBankCategoryView(
                Integer.MIN_VALUE, Long.MIN_VALUE, "", null, null, null, null, 0);
        LocalDateTime createdAt = LocalDateTime.of(2026, 7, 17, 1, 2, 3, 4);
        LocalDateTime updatedAt = LocalDateTime.of(2026, 7, 18, 4, 5, 6, 7);
        var full = new PersonalBankCategoryView(
                Integer.MAX_VALUE,
                Long.MAX_VALUE,
                "  分类 🧪  ",
                "  描述 🌏  ",
                Integer.MIN_VALUE,
                createdAt,
                updatedAt,
                Long.MAX_VALUE);

        assertThat(nullable.id()).isEqualTo(Integer.MIN_VALUE);
        assertThat(nullable.userId()).isEqualTo(Long.MIN_VALUE);
        assertThat(nullable.name()).isEmpty();
        assertThat(nullable.description()).isNull();
        assertThat(nullable.sortOrder()).isNull();
        assertThat(nullable.createdAt()).isNull();
        assertThat(nullable.updatedAt()).isNull();
        assertThat(nullable.bankCount()).isZero();
        assertThat(full.id()).isEqualTo(Integer.MAX_VALUE);
        assertThat(full.userId()).isEqualTo(Long.MAX_VALUE);
        assertThat(full.name()).isEqualTo("  分类 🧪  ");
        assertThat(full.description()).isEqualTo("  描述 🌏  ");
        assertThat(full.sortOrder()).isEqualTo(Integer.MIN_VALUE);
        assertThat(full.createdAt()).isEqualTo(createdAt);
        assertThat(full.updatedAt()).isEqualTo(updatedAt);
        assertThat(full.bankCount()).isEqualTo(Long.MAX_VALUE);
    }

    @Test
    void acceptsZeroIdAndWhitespaceButRejectsMissingNameAndNegativeCounts() {
        assertThat(new PersonalBankCategoryView(0, 1, "  ", "", 0, null, null, 1).id())
                .isZero();
        assertThatNullPointerException()
                .isThrownBy(() -> new PersonalBankCategoryView(
                        1, 1, null, null, null, null, null, 0))
                .withMessage("name");
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new PersonalBankCategoryView(
                        1, 1, "name", null, null, null, null, -1))
                .withMessage("bankCount must not be negative");
    }
}
