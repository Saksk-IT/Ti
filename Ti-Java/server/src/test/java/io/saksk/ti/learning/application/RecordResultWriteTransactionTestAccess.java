package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.QuizLimitPolicy;
import io.saksk.ti.learning.api.RecordResultResult;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.RecordResultStatePort;

public final class RecordResultWriteTransactionTestAccess {

    private RecordResultWriteTransactionTestAccess() {
    }

    public static RecordResultResult execute(
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts,
            long actorId,
            boolean administrator,
            long questionId,
            boolean correct,
            boolean clearMistakeOnCorrect,
            QuizLimitPolicy quizLimitPolicy,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        return new RecordResultWriteTransaction(state, receipts).execute(
                actorId,
                administrator,
                questionId,
                correct,
                clearMistakeOnCorrect,
                quizLimitPolicy,
                idempotencyKey,
                requestSha256);
    }
}
