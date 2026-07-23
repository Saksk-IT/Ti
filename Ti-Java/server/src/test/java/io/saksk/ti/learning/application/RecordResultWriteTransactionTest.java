package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.QuizLimitPolicy;
import io.saksk.ti.learning.api.RecordResultAction;
import io.saksk.ti.learning.api.RecordResultResult;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.RecordResultStatePort;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class RecordResultWriteTransactionTest {

    private final RecordResultStatePort state =
            mock(RecordResultStatePort.class);
    private final LearningWriteReceiptPort receipts =
            mock(LearningWriteReceiptPort.class);
    private final RecordResultWriteTransaction transaction =
            new RecordResultWriteTransaction(state, receipts);

    @Test
    void noHeaderWrongAnswerPreservesOneLogicalAttempt() {
        RecordResultResult result = execute(
                false,
                true,
                QuizLimitPolicy.disabled(),
                LearningWriteIdempotencyKey.absent(),
                digest(1));

        assertThat(result).isEqualTo(RecordResultResult.success(
                RecordResultAction.ADDED_MISTAKE,
                false));
        var ordered = inOrder(state);
        ordered.verify(state).lockActor(91L);
        ordered.verify(state).addOrIncrementMistake(91L, 101L);
        ordered.verify(state).replaceLatestAnswer(91L, 101L, false);
        verify(state, never()).incrementQuizCount(91L);
        verifyNoInteractions(receipts);
    }

    @Test
    void correctAnswerEitherRemovesOrKeepsTheMistake() {
        assertThat(execute(
                        true,
                        true,
                        QuizLimitPolicy.disabled(),
                        LearningWriteIdempotencyKey.absent(),
                        digest(2)).action())
                .contains(RecordResultAction.REMOVED_MISTAKE);
        verify(state).removeMistake(91L, 101L);
        verify(state).replaceLatestAnswer(91L, 101L, true);
    }

    @Test
    void correctAnswerWithClearDisabledKeepsMistakeWithoutTouchingItsRow() {
        RecordResultStatePort isolatedState = mock(RecordResultStatePort.class);
        RecordResultWriteTransaction isolated =
                new RecordResultWriteTransaction(isolatedState, receipts);

        RecordResultResult result = isolated.execute(
                91L,
                false,
                101L,
                true,
                false,
                QuizLimitPolicy.disabled(),
                LearningWriteIdempotencyKey.absent(),
                digest(3));

        assertThat(result.action()).contains(RecordResultAction.KEPT_MISTAKE);
        verify(isolatedState, never()).removeMistake(
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyLong());
        verify(isolatedState, never()).addOrIncrementMistake(
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyLong());
        verify(isolatedState).replaceLatestAnswer(91L, 101L, true);
    }

    @Test
    void quotaRejectsBeforeBusinessMutationAndCanBeDurablyReplayed() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.acquired());
        when(state.currentQuizCount(91L)).thenReturn(60L);
        when(receipts.complete(org.mockito.ArgumentMatchers.any()))
                .thenReturn(new LearningWriteReceiptPort.StoredResponse(
                        403,
                        "{\"quota\": \"60:60\"}"));

        RecordResultResult result = execute(
                false,
                true,
                new QuizLimitPolicy(true, 60),
                LearningWriteIdempotencyKey.of("record-quota-key"),
                digest(4));

        assertThat(result)
                .isEqualTo(RecordResultResult.quizLimitReached(60L, 60, false));
        verify(state).lockActor(91L);
        verify(state).currentQuizCount(91L);
        verify(state, never()).replaceLatestAnswer(
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyBoolean());
        ArgumentCaptor<LearningWriteReceiptPort.CompleteCommand> complete =
                ArgumentCaptor.forClass(LearningWriteReceiptPort.CompleteCommand.class);
        verify(receipts).complete(complete.capture());
        assertThat(complete.getValue().responseStatus()).isEqualTo(403);
        assertThat(complete.getValue().responseBodyJson())
                .isEqualTo("{\"quota\":\"60:60\"}");
    }

    @Test
    void enabledQuotaIncrementsInsideTheSameAttemptButAdministratorsBypassIt() {
        when(state.currentQuizCount(91L)).thenReturn(5L);
        RecordResultResult regular = execute(
                false,
                true,
                new QuizLimitPolicy(true, 60),
                LearningWriteIdempotencyKey.absent(),
                digest(5));
        assertThat(regular.outcome()).isEqualTo(RecordResultResult.Outcome.SUCCESS);
        verify(state).incrementQuizCount(91L);

        RecordResultStatePort adminState = mock(RecordResultStatePort.class);
        RecordResultWriteTransaction adminTransaction =
                new RecordResultWriteTransaction(adminState, receipts);
        RecordResultResult administrator = adminTransaction.execute(
                92L,
                true,
                101L,
                false,
                true,
                new QuizLimitPolicy(true, 0),
                LearningWriteIdempotencyKey.absent(),
                digest(6));
        assertThat(administrator.outcome())
                .isEqualTo(RecordResultResult.Outcome.SUCCESS);
        verify(adminState, never()).currentQuizCount(92L);
        verify(adminState, never()).incrementQuizCount(92L);
    }

    @Test
    void acquiredKeyCompletesARecordResultReceiptAfterEveryBusinessWrite() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.acquired());
        when(receipts.complete(org.mockito.ArgumentMatchers.any()))
                .thenReturn(new LearningWriteReceiptPort.StoredResponse(
                        200,
                        "{\"action\": \"added_mistake\"}"));

        RecordResultResult result = execute(
                false,
                true,
                QuizLimitPolicy.disabled(),
                LearningWriteIdempotencyKey.of("record-result-key"),
                digest(7));

        assertThat(result).isEqualTo(RecordResultResult.success(
                RecordResultAction.ADDED_MISTAKE,
                false));
        ArgumentCaptor<LearningWriteReceiptPort.BeginCommand> begin =
                ArgumentCaptor.forClass(LearningWriteReceiptPort.BeginCommand.class);
        ArgumentCaptor<LearningWriteReceiptPort.CompleteCommand> complete =
                ArgumentCaptor.forClass(LearningWriteReceiptPort.CompleteCommand.class);
        verify(receipts).begin(begin.capture());
        verify(receipts).complete(complete.capture());
        assertThat(begin.getValue().operation())
                .isEqualTo(LearningWriteReceiptPort.Operation.RECORD_RESULT);
        assertThat(begin.getValue().requestSha256()).containsExactly(digest(7));
        assertThat(complete.getValue().responseStatus()).isEqualTo(200);
        assertThat(complete.getValue().responseBodyJson())
                .isEqualTo("{\"action\":\"added_mistake\"}");
    }

    @Test
    void committedSuccessAndQuotaReceiptsReplayWithoutBusinessMutation() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.replay(
                        new LearningWriteReceiptPort.StoredResponse(
                                200,
                                "{\"action\": \"kept_mistake\"}")));
        assertThat(execute(
                        true,
                        false,
                        QuizLimitPolicy.disabled(),
                        LearningWriteIdempotencyKey.of("replay-key"),
                        digest(8)))
                .isEqualTo(RecordResultResult.success(
                        RecordResultAction.KEPT_MISTAKE,
                        true));
        verifyNoInteractions(state);

        RecordResultStatePort quotaState = mock(RecordResultStatePort.class);
        LearningWriteReceiptPort quotaReceipts = mock(LearningWriteReceiptPort.class);
        when(quotaReceipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.replay(
                        new LearningWriteReceiptPort.StoredResponse(
                                403,
                                "{\"quota\": \"100:60\"}")));
        RecordResultWriteTransaction quotaTransaction =
                new RecordResultWriteTransaction(quotaState, quotaReceipts);
        assertThat(quotaTransaction.execute(
                        91L,
                        false,
                        101L,
                        false,
                        true,
                        new QuizLimitPolicy(true, 60),
                        LearningWriteIdempotencyKey.of("quota-replay-key"),
                        digest(9)))
                .isEqualTo(RecordResultResult.quizLimitReached(
                        100L,
                        60,
                        true));
        verifyNoInteractions(quotaState);
    }

    @Test
    void conflictAndPendingReceiptFailClosedBeforeActorLock() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.conflict());
        assertThat(execute(
                        false,
                        true,
                        QuizLimitPolicy.disabled(),
                        LearningWriteIdempotencyKey.of("conflict-key"),
                        digest(10)).outcome())
                .isEqualTo(RecordResultResult.Outcome.IDEMPOTENCY_CONFLICT);

        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.inProgress());
        assertThat(execute(
                        false,
                        true,
                        QuizLimitPolicy.disabled(),
                        LearningWriteIdempotencyKey.of("pending-key"),
                        digest(11)).outcome())
                .isEqualTo(RecordResultResult.Outcome.IDEMPOTENCY_IN_PROGRESS);
        verifyNoInteractions(state);
    }

    @Test
    void malformedPersistedResponsesNeverBecomeApplicationSuccess() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(new LearningWriteReceiptPort.BeginResult(
                        LearningWriteReceiptPort.BeginOutcome.REPLAY,
                        Optional.of(new LearningWriteReceiptPort.StoredResponse(
                                201,
                                "{\"action\":\"added_mistake\"}"))));

        assertThatThrownBy(() -> execute(
                        false,
                        true,
                        QuizLimitPolicy.disabled(),
                        LearningWriteIdempotencyKey.of("malformed-key"),
                        digest(12)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid persisted response");
    }

    private RecordResultResult execute(
            boolean correct,
            boolean clearMistake,
            QuizLimitPolicy policy,
            LearningWriteIdempotencyKey key,
            byte[] digest
    ) {
        return transaction.execute(
                91L,
                false,
                101L,
                correct,
                clearMistake,
                policy,
                key,
                digest);
    }

    private static byte[] digest(int firstByte) {
        byte[] value = new byte[32];
        value[0] = (byte) firstByte;
        return value;
    }
}
