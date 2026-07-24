package io.saksk.ti.learning.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class CheckinContractTest {

    @Test
    void successCarriesTheCompleteLegacyResponseShape() {
        CheckinView view = new CheckinView(
                LocalDate.parse("2026-07-24"),
                true,
                Optional.of(LocalDateTime.parse("2026-07-24T09:15:00")),
                3,
                7,
                true,
                List.of("2026-07-22", "2026-07-23", "2026-07-24"));

        assertThat(CheckinResult.success(view, true))
                .isEqualTo(new CheckinResult(
                        CheckinResult.Outcome.SUCCESS,
                        Optional.of(view),
                        true));
        assertThat(view.checkedDates()).isUnmodifiable();
    }

    @Test
    void rejectedOutcomesNeverCarryOrReplayData() {
        assertThat(CheckinResult.idempotencyConflict().data()).isEmpty();
        assertThat(CheckinResult.idempotencyInProgress().data()).isEmpty();
        assertThat(CheckinResult.mutationRejected().data()).isEmpty();

        assertThatThrownBy(() -> new CheckinResult(
                        CheckinResult.Outcome.SUCCESS,
                        Optional.empty(),
                        false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CheckinResult(
                        CheckinResult.Outcome.MUTATION_REJECTED,
                        Optional.empty(),
                        true))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void responseInvariantsRejectImpossibleOrMutableValues() {
        assertThatThrownBy(() -> new CheckinView(
                        LocalDate.parse("2026-07-24"),
                        false,
                        Optional.empty(),
                        0,
                        0,
                        false,
                        List.of()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CheckinView(
                        LocalDate.parse("2026-07-24"),
                        true,
                        Optional.empty(),
                        -1,
                        0,
                        false,
                        List.of()))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void commandNeverExposesViewerOrRawIdempotencyKey() {
        CheckinCommand command = new CheckinCommand(
                new AuthenticatedLearningViewer(91),
                LearningWriteIdempotencyKey.of("daily-secret-key"));

        assertThat(command.toString())
                .doesNotContain("91")
                .doesNotContain("daily-secret-key")
                .contains("<redacted>");
    }
}
