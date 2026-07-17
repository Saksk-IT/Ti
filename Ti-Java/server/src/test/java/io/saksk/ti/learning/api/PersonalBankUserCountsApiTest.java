package io.saksk.ti.learning.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class PersonalBankUserCountsApiTest {

    @Test
    void keepsTheRawRequestAndServerDerivedIdentityValid() {
        var viewer = new AuthenticatedLearningViewer(Long.MAX_VALUE);
        var query = new PersonalBankUserCountsQuery(7_101, " ALL ", "Favorites", " 重点 ");

        assertThat(viewer.identityId()).isEqualTo(Long.MAX_VALUE);
        assertThat(query).isEqualTo(new PersonalBankUserCountsQuery(
                7_101, " ALL ", "Favorites", " 重点 "));
        assertThatThrownBy(() -> new AuthenticatedLearningViewer(0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new PersonalBankUserCountsQuery(0, "", "", ""))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new PersonalBankUserCountsQuery(1, null, "", ""))
                .isInstanceOf(NullPointerException.class);
    }

    @Test
    void enforcesResultPresenceAndDefensivelyCopiesDisplayTypes() {
        List<String> mutableTypes = new ArrayList<>(List.of("选择题", "选择题"));
        var view = new PersonalBankUserCountsView(2, 7, 3, mutableTypes, true);
        var available = PersonalBankUserCountsResult.available(view);

        mutableTypes.clear();
        assertThat(available.outcome())
                .isEqualTo(PersonalBankUserCountsResult.Outcome.AVAILABLE);
        assertThat(available.data()).contains(view);
        assertThat(available.data().orElseThrow().types())
                .containsExactly("选择题", "选择题");
        assertThatThrownBy(() -> available.data().orElseThrow().types().add("多选题"))
                .isInstanceOf(UnsupportedOperationException.class);

        assertThat(PersonalBankUserCountsResult.denied().data()).isEmpty();
        assertThatThrownBy(() -> new PersonalBankUserCountsResult(
                PersonalBankUserCountsResult.Outcome.DENIED,
                Optional.of(view)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new PersonalBankUserCountsView(
                -1, 0, 0, List.of(), false))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
