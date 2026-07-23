package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import io.saksk.ti.learning.application.port.FavoriteTogglePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class FavoriteWriteTransactionTest {

    private final FavoriteTogglePort favorites = mock(FavoriteTogglePort.class);
    private final LearningWriteReceiptPort receipts = mock(LearningWriteReceiptPort.class);
    private final FavoriteWriteTransaction transaction =
            new FavoriteWriteTransaction(favorites, receipts);

    @Test
    void noHeaderPreservesOneTogglePerAcceptedAttempt() {
        when(favorites.toggle(91L, 101L)).thenReturn(true);

        ToggleFavoriteResult result = transaction.execute(
                91L,
                101L,
                LearningWriteIdempotencyKey.absent(),
                digest(1));

        assertThat(result.favorite()).contains(true);
        assertThat(result.replayed()).isFalse();
        verify(favorites).toggle(91L, 101L);
        verifyNoInteractions(receipts);
    }

    @Test
    void acquisitionMutationAndCompletionShareOneTypedReceipt() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.acquired());
        when(favorites.toggle(91L, 101L)).thenReturn(true);
        when(receipts.complete(org.mockito.ArgumentMatchers.any()))
                .thenReturn(new LearningWriteReceiptPort.StoredResponse(
                        200,
                        "{\"is_favorite\": true}"));

        ToggleFavoriteResult result = transaction.execute(
                91L,
                101L,
                LearningWriteIdempotencyKey.of("favorite-idempotency-key"),
                digest(2));

        assertThat(result).isEqualTo(ToggleFavoriteResult.success(true, false));
        ArgumentCaptor<LearningWriteReceiptPort.BeginCommand> begin =
                ArgumentCaptor.forClass(LearningWriteReceiptPort.BeginCommand.class);
        ArgumentCaptor<LearningWriteReceiptPort.CompleteCommand> complete =
                ArgumentCaptor.forClass(LearningWriteReceiptPort.CompleteCommand.class);
        verify(receipts).begin(begin.capture());
        verify(receipts).complete(complete.capture());
        assertThat(begin.getValue().operation())
                .isEqualTo(LearningWriteReceiptPort.Operation.FAVORITE);
        assertThat(begin.getValue().idempotencyKey()).isEqualTo("favorite-idempotency-key");
        assertThat(begin.getValue().requestSha256()).containsExactly(digest(2));
        assertThat(complete.getValue().responseBodyJson())
                .isEqualTo("{\"is_favorite\":true}");
    }

    @Test
    void committedReceiptReplaysWithoutAnotherBusinessMutation() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.replay(
                        new LearningWriteReceiptPort.StoredResponse(
                                200,
                                "{\"is_favorite\": false}")));

        ToggleFavoriteResult result = transaction.execute(
                91L,
                101L,
                LearningWriteIdempotencyKey.of("favorite-idempotency-key"),
                digest(3));

        assertThat(result).isEqualTo(ToggleFavoriteResult.success(false, true));
        verify(favorites, never()).toggle(
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyLong());
        verify(receipts, never()).complete(org.mockito.ArgumentMatchers.any());
    }

    @Test
    void conflictsAndCommittedPendingRowsFailClosedBeforeMutation() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.conflict());
        assertThat(transaction.execute(
                        91L,
                        101L,
                        LearningWriteIdempotencyKey.of("favorite-idempotency-key"),
                        digest(4)).outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.IDEMPOTENCY_CONFLICT);

        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(LearningWriteReceiptPort.BeginResult.inProgress());
        assertThat(transaction.execute(
                        91L,
                        101L,
                        LearningWriteIdempotencyKey.of("favorite-idempotency-key"),
                        digest(4)).outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.IDEMPOTENCY_IN_PROGRESS);
        verifyNoInteractions(favorites);
    }

    @Test
    void malformedPersistedResponsesNeverBecomeSuccessfulReplays() {
        when(receipts.begin(org.mockito.ArgumentMatchers.any()))
                .thenReturn(new LearningWriteReceiptPort.BeginResult(
                        LearningWriteReceiptPort.BeginOutcome.REPLAY,
                        Optional.of(new LearningWriteReceiptPort.StoredResponse(
                                201,
                                "{\"is_favorite\":true}"))));

        assertThatThrownBy(() -> transaction.execute(
                        91L,
                        101L,
                        LearningWriteIdempotencyKey.of("favorite-idempotency-key"),
                        digest(5)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("invalid status");
    }

    @Test
    void requestFingerprintIsStableAndSeparatesActorsAndBodies() {
        assertThat(LearningWriteRequestFingerprints.favorite(91L, 101L))
                .containsExactly(LearningWriteRequestFingerprints.favorite(91L, 101L))
                .isNotEqualTo(LearningWriteRequestFingerprints.favorite(92L, 101L))
                .isNotEqualTo(LearningWriteRequestFingerprints.favorite(91L, 102L));
    }

    private static byte[] digest(int firstByte) {
        byte[] digest = new byte[32];
        digest[0] = (byte) firstByte;
        return digest;
    }
}
