package io.saksk.ti.personalbank.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class PersonalBankOwnedShareViewTest {

    @Test
    void preservesSignedNullableAndArbitraryLegacyFactsWithoutNormalization() {
        var raw = new PersonalBankOwnedShareView(
                -2,
                0,
                Long.MAX_VALUE,
                null,
                " token ",
                "unexpected-value",
                null,
                -1,
                -2,
                null,
                LocalDateTime.of(2026, 7, 17, 12, 0),
                " 题库 🧪 ");

        assertThat(raw.id()).isEqualTo(-2);
        assertThat(raw.bankId()).isZero();
        assertThat(raw.ownerId()).isEqualTo(Long.MAX_VALUE);
        assertThat(raw.shareCode()).isNull();
        assertThat(raw.shareToken()).isEqualTo(" token ");
        assertThat(raw.permission()).isEqualTo("unexpected-value");
        assertThat(raw.expiresAt()).isNull();
        assertThat(raw.maxUses()).isEqualTo(-1);
        assertThat(raw.currentUses()).isEqualTo(-2);
        assertThat(raw.isActive()).isNull();
        assertThat(raw.createdAt()).isEqualTo(LocalDateTime.of(2026, 7, 17, 12, 0));
        assertThat(raw.bankName()).isEqualTo(" 题库 🧪 ");
    }

    @Test
    void requiresOnlyTheJoinedBankNameAndPreservesAnEmptyName() {
        assertThat(new PersonalBankOwnedShareView(
                1, 2, 3, null, null, null, null, null, null, null, null, "")
                .bankName()).isEmpty();

        assertThatNullPointerException()
                .isThrownBy(() -> new PersonalBankOwnedShareView(
                        1, 2, 3, null, null, null, null, null, null, null, null, null))
                .withMessage("bankName");
    }
}
