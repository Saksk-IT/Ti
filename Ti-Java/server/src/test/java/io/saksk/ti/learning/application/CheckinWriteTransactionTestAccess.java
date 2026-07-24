package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.CheckinResult;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.application.port.CheckinStatePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import java.time.LocalDate;
import java.time.LocalDateTime;

public final class CheckinWriteTransactionTestAccess {

    private CheckinWriteTransactionTestAccess() {
    }

    public static CheckinResult execute(
            CheckinStatePort state,
            LearningWriteReceiptPort receipts,
            long actorId,
            LocalDate today,
            LocalDateTime now,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        return new CheckinWriteTransaction(state, receipts).execute(
                actorId,
                today,
                now,
                idempotencyKey,
                requestSha256);
    }
}
