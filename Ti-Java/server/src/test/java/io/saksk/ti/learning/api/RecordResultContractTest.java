package io.saksk.ti.learning.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Optional;
import org.junit.jupiter.api.Test;

class RecordResultContractTest {

    @Test
    void commandRedactsActorPolicyAndRawIdempotencyKey() {
        RecordResultCommand command = new RecordResultCommand(
                new AuthenticatedLearningViewer(91L),
                101L,
                false,
                true,
                new QuizLimitPolicy(true, 60),
                LearningWriteIdempotencyKey.of("record-result-private-key"));

        assertThat(command.toString())
                .contains(
                        "questionId=101",
                        "correct=false",
                        "clearMistakeOnCorrect=true",
                        "<redacted>")
                .doesNotContain("record-result-private-key")
                .doesNotContain("91")
                .doesNotContain("60");
    }

    @Test
    void actionsHaveTheExactLegacyWireValues() {
        assertThat(RecordResultAction.ADDED_MISTAKE.wireValue())
                .isEqualTo("added_mistake");
        assertThat(RecordResultAction.REMOVED_MISTAKE.wireValue())
                .isEqualTo("removed_mistake");
        assertThat(RecordResultAction.KEPT_MISTAKE.wireValue())
                .isEqualTo("kept_mistake");
        assertThat(RecordResultAction.fromWireValue("removed_mistake"))
                .isEqualTo(RecordResultAction.REMOVED_MISTAKE);
        assertThatThrownBy(() -> RecordResultAction.fromWireValue("unknown"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void resultRequiresExactlyThePayloadForItsOutcome() {
        assertThat(RecordResultResult.success(
                        RecordResultAction.ADDED_MISTAKE,
                        true).replayed())
                .isTrue();
        QuizLimitReached limit = RecordResultResult.quizLimitReached(
                        60L,
                        60,
                        false)
                .quizLimit()
                .orElseThrow();
        assertThat(limit.message())
                .isEqualTo("已达到刷题限制（60题），请付费或联系管理员");

        assertThatThrownBy(() -> new RecordResultResult(
                        RecordResultResult.Outcome.SUCCESS,
                        Optional.empty(),
                        Optional.empty(),
                        false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new RecordResultResult(
                        RecordResultResult.Outcome.QUIZ_LIMIT_REACHED,
                        Optional.of(RecordResultAction.KEPT_MISTAKE),
                        Optional.of(new QuizLimitReached(1L, 1)),
                        false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new RecordResultResult(
                        RecordResultResult.Outcome.IDEMPOTENCY_CONFLICT,
                        Optional.empty(),
                        Optional.empty(),
                        true))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void quotaPolicyPreservesDisabledDefaultAndLegacyIntegerRange() {
        assertThat(QuizLimitPolicy.disabled())
                .isEqualTo(new QuizLimitPolicy(false, 100));
        assertThat(new QuizLimitPolicy(true, -1).limitCount()).isEqualTo(-1);
        assertThat(new QuizLimitReached(-1L, -2).currentCount()).isEqualTo(-1L);
    }
}
