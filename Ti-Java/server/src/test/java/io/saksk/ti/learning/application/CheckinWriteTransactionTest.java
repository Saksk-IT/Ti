package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.learning.api.CheckinResult;
import io.saksk.ti.learning.api.CheckinView;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.application.port.CheckinStatePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class CheckinWriteTransactionTest {

    private static final LocalDate TODAY = LocalDate.parse("2026-07-24");
    private static final LocalDateTime NOW =
            LocalDateTime.parse("2026-07-24T09:15:00");

    private final CheckinStatePort state = mock(CheckinStatePort.class);
    private final LearningWriteReceiptPort receipts =
            mock(LearningWriteReceiptPort.class);
    private final CheckinWriteTransaction transaction =
            new CheckinWriteTransaction(state, receipts);

    @Test
    void firstNaturalKeyInsertReturnsCompleteAggregatesInsideOneAttempt() {
        when(state.insertIfAbsent(91, TODAY, NOW)).thenReturn(true);
        when(state.findCreatedAt(91, TODAY)).thenReturn(Optional.of(NOW));
        when(state.countAll(91)).thenReturn(4L);
        when(state.listRecentDateValues(91, 100)).thenReturn(List.of(
                "2026-07-24",
                "2026-07-23",
                "2026-07-22",
                "2026-07-20"));
        when(state.listDateValues(
                        91,
                        LocalDate.parse("2026-07-01"),
                        LocalDate.parse("2026-08-01")))
                .thenReturn(List.of(
                        "2026-07-20",
                        "2026-07-22",
                        "2026-07-23",
                        "2026-07-24"));

        CheckinResult result = execute(
                LearningWriteIdempotencyKey.absent(),
                digest(1));

        assertThat(result).isEqualTo(CheckinResult.success(
                new CheckinView(
                        TODAY,
                        true,
                        Optional.of(NOW),
                        3,
                        4,
                        true,
                        List.of(
                                "2026-07-20",
                                "2026-07-22",
                                "2026-07-23",
                                "2026-07-24")),
                false));
        var ordered = inOrder(state);
        ordered.verify(state).insertIfAbsent(91, TODAY, NOW);
        ordered.verify(state).findCreatedAt(91, TODAY);
        ordered.verify(state).countAll(91);
        ordered.verify(state).listRecentDateValues(91, 100);
        ordered.verify(state).listDateValues(
                91,
                LocalDate.parse("2026-07-01"),
                LocalDate.parse("2026-08-01"));
        verifyNoInteractions(receipts);
    }

    @Test
    void naturalDuplicateReturnsOriginalTimestampAndJustCheckedInFalse() {
        LocalDateTime original = LocalDateTime.parse("2026-07-24T07:00:00");
        when(state.insertIfAbsent(91, TODAY, NOW)).thenReturn(false);
        when(state.findCreatedAt(91, TODAY)).thenReturn(Optional.of(original));
        when(state.countAll(91)).thenReturn(1L);
        when(state.listRecentDateValues(91, 100)).thenReturn(List.of("2026-07-24"));
        when(state.listDateValues(
                        91,
                        TODAY.withDayOfMonth(1),
                        TODAY.withDayOfMonth(1).plusMonths(1)))
                .thenReturn(List.of("2026-07-24"));

        assertThat(execute(
                        LearningWriteIdempotencyKey.absent(),
                        digest(2)).data())
                .contains(new CheckinView(
                        TODAY,
                        true,
                        Optional.of(original),
                        1,
                        1,
                        false,
                        List.of("2026-07-24")));
    }

    @Test
    void acquiredExplicitKeyPersistsAndDecodesTheExactResponse() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.acquired());
        when(state.insertIfAbsent(91, TODAY, NOW)).thenReturn(true);
        when(state.findCreatedAt(91, TODAY)).thenReturn(Optional.of(NOW));
        when(state.countAll(91)).thenReturn(1L);
        when(state.listRecentDateValues(91, 100)).thenReturn(List.of("2026-07-24"));
        when(state.listDateValues(
                        91,
                        TODAY.withDayOfMonth(1),
                        TODAY.withDayOfMonth(1).plusMonths(1)))
                .thenReturn(List.of("2026-07-24"));
        when(receipts.complete(org.mockito.ArgumentMatchers.any()))
                .thenAnswer(invocation -> {
                    LearningWriteReceiptPort.CompleteCommand command =
                            invocation.getArgument(0);
                    return new LearningWriteReceiptPort.StoredResponse(
                            command.responseStatus(),
                            command.responseBodyJson());
                });

        CheckinResult result = execute(
                LearningWriteIdempotencyKey.of("daily-key"),
                digest(3));

        assertThat(result.data().orElseThrow().justCheckedIn()).isTrue();
        ArgumentCaptor<LearningWriteReceiptPort.CompleteCommand> complete =
                ArgumentCaptor.forClass(LearningWriteReceiptPort.CompleteCommand.class);
        verify(receipts).complete(complete.capture());
        assertThat(complete.getValue().operation())
                .isEqualTo(LearningWriteReceiptPort.Operation.CHECKIN);
        assertThat(complete.getValue().responseBodyJson())
                .doesNotContain("daily-key")
                .contains("\"today\":\"2026-07-24\"")
                .contains("\"checked_in_at\":\"2026-07-24T09:15\"")
                .contains("\"just_checked_in\":true")
                .contains("\"checked_dates\":[\"2026-07-24\"]");
    }

    @Test
    void replayConflictAndPendingTerminateBeforeNaturalInsert() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.replay(
                        new LearningWriteReceiptPort.StoredResponse(
                                200,
                                """
                                {
                                  "today":"2026-07-24",
                                  "checked_in_today":true,
                                  "checked_in_at":"2026-07-24T09:15",
                                  "streak_days":1,
                                  "total_days":1,
                                  "just_checked_in":true,
                                  "checked_dates":["2026-07-24"]
                                }
                                """)));
        CheckinResult replay = execute(
                LearningWriteIdempotencyKey.of("replay"),
                digest(4));
        assertThat(replay.replayed()).isTrue();
        assertThat(replay.data().orElseThrow().justCheckedIn()).isTrue();

        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.conflict());
        assertThat(execute(
                        LearningWriteIdempotencyKey.of("conflict"),
                        digest(5)).outcome())
                .isEqualTo(CheckinResult.Outcome.IDEMPOTENCY_CONFLICT);

        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.inProgress());
        assertThat(execute(
                        LearningWriteIdempotencyKey.of("pending"),
                        digest(6)).outcome())
                .isEqualTo(CheckinResult.Outcome.IDEMPOTENCY_IN_PROGRESS);
        verifyNoInteractions(state);
    }

    @Test
    void malformedReceiptAndMismatchedTimestampFailClosed() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.replay(
                        new LearningWriteReceiptPort.StoredResponse(
                                200,
                                "{\"today\":\"2026-07-24\"}")));
        assertThatThrownBy(() -> execute(
                        LearningWriteIdempotencyKey.of("malformed"),
                        digest(7)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("field set");

        assertThatThrownBy(() -> transaction.execute(
                        91,
                        TODAY,
                        NOW.plusDays(1),
                        LearningWriteIdempotencyKey.absent(),
                        digest(8)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("Beijing date");
    }

    @Test
    void streakMatchesLegacyTodayYesterdayGapAndMalformedRules() {
        assertThat(CheckinWriteTransaction.calculateStreak(List.of(), TODAY)).isZero();
        assertThat(CheckinWriteTransaction.calculateStreak(
                        List.of("2026-07-24", "2026-07-23", "2026-07-22"),
                        TODAY))
                .isEqualTo(3);
        assertThat(CheckinWriteTransaction.calculateStreak(
                        List.of("2026-07-23", "2026-07-22"),
                        TODAY))
                .isEqualTo(2);
        assertThat(CheckinWriteTransaction.calculateStreak(
                        List.of("2026-07-22", "2026-07-21"),
                        TODAY))
                .isZero();
        assertThat(CheckinWriteTransaction.calculateStreak(
                        List.of("not-a-date", "2026-07-24"),
                        TODAY))
                .isZero();
        assertThat(CheckinWriteTransaction.calculateStreak(
                        List.of("2026-07-25", "2026-07-24"),
                        TODAY))
                .isEqualTo(2);
    }

    private CheckinResult execute(
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        return transaction.execute(
                91,
                TODAY,
                NOW,
                idempotencyKey,
                requestSha256);
    }

    private static byte[] digest(int firstByte) {
        byte[] value = new byte[32];
        value[0] = (byte) firstByte;
        return value;
    }
}
