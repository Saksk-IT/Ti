package io.saksk.ti.learning.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Optional;
import org.junit.jupiter.api.Test;

class ToggleFavoriteContractTest {

    @Test
    void commandRedactsTheServerDerivedActorAndRawKey() {
        ToggleFavoriteCommand command = new ToggleFavoriteCommand(
                new AuthenticatedLearningViewer(91L),
                101L,
                LearningWriteIdempotencyKey.of("favorite-private-key"));

        assertThat(command.toString())
                .contains("questionId=101", "<redacted>")
                .doesNotContain("favorite-private-key")
                .doesNotContain("91");
    }

    @Test
    void resultRequiresFavoriteStateOnlyForSuccess() {
        assertThat(ToggleFavoriteResult.success(true, false).favorite()).contains(true);
        assertThat(ToggleFavoriteResult.success(false, true).replayed()).isTrue();
        assertThatThrownBy(() -> new ToggleFavoriteResult(
                        ToggleFavoriteResult.Outcome.SUCCESS,
                        Optional.empty(),
                        false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ToggleFavoriteResult(
                        ToggleFavoriteResult.Outcome.QUESTION_NOT_FOUND,
                        Optional.of(true),
                        false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new ToggleFavoriteResult(
                        ToggleFavoriteResult.Outcome.IDEMPOTENCY_CONFLICT,
                        Optional.empty(),
                        true))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
