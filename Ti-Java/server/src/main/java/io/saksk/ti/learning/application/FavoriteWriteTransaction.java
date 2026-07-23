package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import io.saksk.ti.learning.application.port.FavoriteTogglePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class FavoriteWriteTransaction {

    private final FavoriteTogglePort favorites;
    private final LearningWriteReceiptPort receipts;

    FavoriteWriteTransaction(
            FavoriteTogglePort favorites,
            LearningWriteReceiptPort receipts
    ) {
        this.favorites = Objects.requireNonNull(favorites, "favorites");
        this.receipts = Objects.requireNonNull(receipts, "receipts");
    }

    @Transactional
    public ToggleFavoriteResult execute(
            long actorId,
            long questionId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        Objects.requireNonNull(idempotencyKey, "idempotencyKey");
        Objects.requireNonNull(requestSha256, "requestSha256");
        if (!idempotencyKey.isPresent()) {
            return ToggleFavoriteResult.success(
                    favorites.toggle(actorId, questionId),
                    false);
        }

        String rawKey = idempotencyKey.value().orElseThrow();
        LearningWriteReceiptPort.BeginResult begin =
                receipts.begin(new LearningWriteReceiptPort.BeginCommand(
                        actorId,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        rawKey,
                        requestSha256));
        return switch (begin.outcome()) {
            case CONFLICT -> ToggleFavoriteResult.idempotencyConflict();
            case IN_PROGRESS -> ToggleFavoriteResult.idempotencyInProgress();
            case REPLAY -> replay(begin.replay().orElseThrow());
            case ACQUIRED -> {
                boolean favorite = favorites.toggle(actorId, questionId);
                LearningWriteReceiptPort.StoredResponse stored =
                        receipts.complete(new LearningWriteReceiptPort.CompleteCommand(
                                actorId,
                                LearningWriteReceiptPort.Operation.FAVORITE,
                                rawKey,
                                requestSha256,
                                200,
                                "{\"is_favorite\":" + favorite + "}"));
                yield ToggleFavoriteResult.success(decodeFavorite(stored), false);
            }
        };
    }

    private static ToggleFavoriteResult replay(
            LearningWriteReceiptPort.StoredResponse response
    ) {
        return ToggleFavoriteResult.success(decodeFavorite(response), true);
    }

    private static boolean decodeFavorite(LearningWriteReceiptPort.StoredResponse response) {
        if (response.status() != 200) {
            throw new IllegalStateException("Favorite receipt contains an invalid status");
        }
        String compact = response.bodyJson().replaceAll("\\s+", "");
        return switch (compact) {
            case "{\"is_favorite\":true}" -> true;
            case "{\"is_favorite\":false}" -> false;
            default -> throw new IllegalStateException(
                    "Favorite receipt contains an invalid response body");
        };
    }
}
