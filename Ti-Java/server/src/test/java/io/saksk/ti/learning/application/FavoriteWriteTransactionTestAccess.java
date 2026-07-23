package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import io.saksk.ti.learning.application.port.FavoriteTogglePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;

public final class FavoriteWriteTransactionTestAccess {

    private FavoriteWriteTransactionTestAccess() {
    }

    public static ToggleFavoriteResult execute(
            FavoriteTogglePort favorites,
            LearningWriteReceiptPort receipts,
            long actorId,
            long questionId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        return new FavoriteWriteTransaction(favorites, receipts).execute(
                actorId,
                questionId,
                idempotencyKey,
                requestSha256);
    }
}
