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
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRating;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyWriteOutcome;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.learning.application.StudyApplicationService.ResolvedScope;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.StudyStatePort;
import io.saksk.ti.learning.application.port.StudyStatePort.LearningState;
import io.saksk.ti.learning.application.port.StudyStatePort.ReviewState;
import io.saksk.ti.learning.application.port.StudyStatePort.StudyKey;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class StudyWriteTransactionTest {

    private static final Clock CLOCK = Clock.fixed(
            Instant.parse("2026-07-23T13:00:00Z"),
            ZoneOffset.UTC);
    private static final LocalDateTime NOW =
            LocalDateTime.parse("2026-07-23T21:00:00");
    private static final ResolvedScope PUBLIC =
            new ResolvedScope("public", 201);

    private final StudyStatePort state = mock(StudyStatePort.class);
    private final LearningWriteReceiptPort receipts =
            mock(LearningWriteReceiptPort.class);
    private final StudyWriteTransaction transaction =
            new StudyWriteTransaction(state, receipts, CLOCK);

    @Test
    void thirdCorrectAnswerAtomicallyLearnsAndActivatesTheNextFourAmReview() {
        StudyKey key = new StudyKey(91, "public", 201, 101);
        when(state.findLearning(key)).thenReturn(Optional.of(new LearningState(
                2,
                false,
                2,
                4,
                "correct",
                LocalDateTime.parse("2026-07-22T20:00:00"))));

        StudyWriteResult<StudyLearnView> result = transaction.recordLearning(
                91,
                101,
                true,
                PUBLIC,
                LearningWriteIdempotencyKey.absent(),
                digest(1));

        assertThat(result).isEqualTo(StudyWriteResult.success(
                new StudyLearnView(
                        3,
                        true,
                        Optional.of(LocalDateTime.parse("2026-07-24T04:00:00"))),
                false));
        var ordered = inOrder(state);
        ordered.verify(state).lockScope(key);
        ordered.verify(state).findLearning(key);
        ordered.verify(state).saveLearning(
                key,
                new LearningState(3, true, 3, 4, "correct", NOW),
                NOW);
        ordered.verify(state).activateReview(
                key,
                LocalDateTime.parse("2026-07-24T04:00:00"),
                NOW);
        verify(state, never()).addMistake(
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
        verifyNoInteractions(receipts);
    }

    @Test
    void wrongAnswerResetsLearnedStateAndAddsTheScopeSpecificMistake() {
        StudyKey key = new StudyKey(91, "user_bank", 301, 101);
        when(state.findLearning(key)).thenReturn(Optional.of(new LearningState(
                5,
                true,
                5,
                1,
                "correct",
                NOW.minusDays(1))));

        StudyWriteResult<StudyLearnView> result = transaction.recordLearning(
                91,
                101,
                false,
                new ResolvedScope("user_bank", 301),
                LearningWriteIdempotencyKey.absent(),
                digest(2));

        assertThat(result.data()).contains(new StudyLearnView(
                0,
                false,
                Optional.empty()));
        verify(state).saveLearning(
                key,
                new LearningState(0, false, 5, 2, "wrong", NOW),
                NOW);
        verify(state).addMistake(key, NOW);
        verify(state, never()).activateReview(
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
    }

    @Test
    void reviewRatingsClampLevelAndUnknownAddsOneLapse() {
        StudyKey key = new StudyKey(91, "public", 201, 101);
        when(state.findReview(key)).thenReturn(Optional.of(new ReviewState(
                7,
                Optional.empty(),
                Optional.empty(),
                Optional.empty(),
                2,
                true)));

        StudyWriteResult<StudyReviewRecordView> known = transaction.recordReview(
                91,
                101,
                StudyReviewRating.KNOWN,
                PUBLIC,
                LearningWriteIdempotencyKey.absent(),
                digest(3));
        assertThat(known.data()).contains(new StudyReviewRecordView(
                7,
                LocalDateTime.parse("2026-11-21T04:00:00")));
        verify(state).saveReview(
                key,
                new ReviewState(
                        7,
                        Optional.of(LocalDateTime.parse("2026-11-21T04:00:00")),
                        Optional.of(NOW),
                        Optional.of("known"),
                        2,
                        false),
                NOW);

        StudyStatePort unknownState = mock(StudyStatePort.class);
        when(unknownState.findReview(key)).thenReturn(Optional.of(new ReviewState(
                5,
                Optional.empty(),
                Optional.empty(),
                Optional.of("legacy-raw"),
                2,
                false)));
        StudyWriteTransaction unknownTransaction =
                new StudyWriteTransaction(unknownState, receipts, CLOCK);
        assertThat(unknownTransaction.recordReview(
                        91,
                        101,
                        StudyReviewRating.UNKNOWN,
                        PUBLIC,
                        LearningWriteIdempotencyKey.absent(),
                        digest(4)).data())
                .contains(new StudyReviewRecordView(
                        0,
                        LocalDateTime.parse("2026-07-25T04:00:00")));
        verify(unknownState).saveReview(
                key,
                new ReviewState(
                        0,
                        Optional.of(LocalDateTime.parse("2026-07-25T04:00:00")),
                        Optional.of(NOW),
                        Optional.of("unknown"),
                        3,
                        false),
                NOW);
    }

    @Test
    void masteredStatePreservesExistingReviewFieldsAndControlsNextDue() {
        StudyKey key = new StudyKey(91, "public", 201, 101);
        ReviewState previous = new ReviewState(
                4,
                Optional.of(NOW.plusDays(1)),
                Optional.of(NOW.minusDays(1)),
                Optional.of("legacy-raw"),
                6,
                false);
        when(state.findReview(key)).thenReturn(Optional.of(previous));

        assertThat(transaction.setReviewMastered(
                        91,
                        101,
                        true,
                        PUBLIC,
                        LearningWriteIdempotencyKey.absent(),
                        digest(5)).data())
                .contains(new StudyReviewMasterView(true));
        verify(state).saveReview(
                key,
                new ReviewState(
                        4,
                        Optional.empty(),
                        previous.lastReviewAt(),
                        previous.lastRating(),
                        6,
                        true),
                NOW);

        StudyStatePort unmasterState = mock(StudyStatePort.class);
        when(unmasterState.findReview(key)).thenReturn(Optional.of(previous));
        StudyWriteTransaction unmaster =
                new StudyWriteTransaction(unmasterState, receipts, CLOCK);
        assertThat(unmaster.setReviewMastered(
                        91,
                        101,
                        false,
                        PUBLIC,
                        LearningWriteIdempotencyKey.absent(),
                        digest(6)).data())
                .contains(new StudyReviewMasterView(false));
        verify(unmasterState).saveReview(
                key,
                new ReviewState(
                        4,
                        Optional.of(LocalDateTime.parse("2026-07-24T04:00:00")),
                        previous.lastReviewAt(),
                        previous.lastRating(),
                        6,
                        false),
                NOW);
    }

    @Test
    void acquiredReceiptCompletesAfterMutationAndCommittedReceiptReplays() {
        StudyKey key = new StudyKey(91, "public", 201, 101);
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.acquired());
        when(receipts.complete(org.mockito.ArgumentMatchers.any()))
                .thenReturn(new LearningWriteReceiptPort.StoredResponse(
                        200,
                        "{\"review_level\": 1,"
                                + "\"next_due_at\": \"2026-07-26T04:00:00\"}"));

        StudyWriteResult<StudyReviewRecordView> result = transaction.recordReview(
                91,
                101,
                StudyReviewRating.KNOWN,
                PUBLIC,
                LearningWriteIdempotencyKey.of("review-key"),
                digest(7));
        assertThat(result.data()).contains(new StudyReviewRecordView(
                1,
                LocalDateTime.parse("2026-07-26T04:00:00")));
        ArgumentCaptor<LearningWriteReceiptPort.CompleteCommand> complete =
                ArgumentCaptor.forClass(LearningWriteReceiptPort.CompleteCommand.class);
        verify(receipts).complete(complete.capture());
        assertThat(complete.getValue().operation())
                .isEqualTo(LearningWriteReceiptPort.Operation.STUDY_REVIEW_RECORD);
        assertThat(complete.getValue().responseBodyJson())
                .isEqualTo("{\"review_level\":1,"
                        + "\"next_due_at\":\"2026-07-26T04:00\"}");
        verify(state).lockScope(key);

        StudyStatePort replayState = mock(StudyStatePort.class);
        LearningWriteReceiptPort replayReceipts =
                mock(LearningWriteReceiptPort.class);
        when(replayReceipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.replay(
                        new LearningWriteReceiptPort.StoredResponse(
                                200,
                                "{\"is_mastered\":1}")));
        StudyWriteTransaction replay =
                new StudyWriteTransaction(replayState, replayReceipts, CLOCK);
        assertThat(replay.setReviewMastered(
                        91,
                        101,
                        false,
                        PUBLIC,
                        LearningWriteIdempotencyKey.of("master-key"),
                        digest(8)))
                .isEqualTo(StudyWriteResult.success(
                        new StudyReviewMasterView(true),
                        true));
        verifyNoInteractions(replayState);
    }

    @Test
    void conflictAndPendingFailBeforeScopeLockAndMalformedReplayFailsClosed() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.conflict());
        assertThat(transaction.recordLearning(
                        91,
                        101,
                        true,
                        PUBLIC,
                        LearningWriteIdempotencyKey.of("conflict"),
                        digest(9)).outcome())
                .isEqualTo(StudyWriteOutcome.IDEMPOTENCY_CONFLICT);

        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.inProgress());
        assertThat(transaction.recordLearning(
                        91,
                        101,
                        true,
                        PUBLIC,
                        LearningWriteIdempotencyKey.of("pending"),
                        digest(10)).outcome())
                .isEqualTo(StudyWriteOutcome.IDEMPOTENCY_IN_PROGRESS);
        verifyNoInteractions(state);

        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.replay(
                        new LearningWriteReceiptPort.StoredResponse(
                                200,
                                "{\"streak\":1,\"is_learned\":2,"
                                        + "\"next_due_at\":null}")));
        assertThatThrownBy(() -> transaction.recordLearning(
                        91,
                        101,
                        true,
                        PUBLIC,
                        LearningWriteIdempotencyKey.of("malformed"),
                        digest(11)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid body");
    }

    @Test
    void nextFourAmMovesExactBoundaryToTheNextDay() {
        assertThat(StudyWriteTransaction.nextFourAm(
                        LocalDateTime.parse("2026-07-23T03:59:59")))
                .isEqualTo(LocalDateTime.parse("2026-07-23T04:00:00"));
        assertThat(StudyWriteTransaction.nextFourAm(
                        LocalDateTime.parse("2026-07-23T04:00:00")))
                .isEqualTo(LocalDateTime.parse("2026-07-24T04:00:00"));
    }

    private static byte[] digest(int firstByte) {
        byte[] value = new byte[32];
        value[0] = (byte) firstByte;
        return value;
    }
}
