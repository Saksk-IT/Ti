package io.saksk.ti.personalbank.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class PersonalBankShareViewTest {

    @Test
    void preservesSignedZeroNullableAndArbitraryLegacyFactsWithoutNormalization() {
        var raw = new PersonalBankShareView(
                -2,
                0,
                Long.MAX_VALUE,
                null,
                " token ",
                "unexpected-value",
                null,
                -1,
                0,
                null,
                LocalDateTime.of(2026, 7, 17, 12, 0));

        assertThat(raw.id()).isEqualTo(-2);
        assertThat(raw.bankId()).isZero();
        assertThat(raw.ownerId()).isEqualTo(Long.MAX_VALUE);
        assertThat(raw.shareCode()).isNull();
        assertThat(raw.shareToken()).isEqualTo(" token ");
        assertThat(raw.permission()).isEqualTo("unexpected-value");
        assertThat(raw.expiresAt()).isNull();
        assertThat(raw.maxUses()).isEqualTo(-1);
        assertThat(raw.currentUses()).isZero();
        assertThat(raw.isActive()).isNull();
        assertThat(raw.createdAt()).isEqualTo(LocalDateTime.of(2026, 7, 17, 12, 0));
    }

    @Test
    void listViewDefensivelyCopiesRowsAndRejectsNullCollectionsOrElements() {
        var row = new PersonalBankShareView(
                1, 2, 3L, "", "", "", null, null, null, false, null);
        var mutable = new ArrayList<>(List.of(row));

        var view = new PersonalBankShareListView(mutable);

        mutable.clear();
        assertThat(view.shares()).containsExactly(row);
        assertThatThrownBy(() -> view.shares().add(row))
                .isInstanceOf(UnsupportedOperationException.class);
        assertThatNullPointerException()
                .isThrownBy(() -> new PersonalBankShareListView(null));
        assertThatNullPointerException()
                .isThrownBy(() -> new PersonalBankShareListView(
                        java.util.Arrays.asList(row, null)));
    }
}
