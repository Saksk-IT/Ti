package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRating;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.StudyStatePort;
import java.time.Clock;

public final class StudyWriteTransactionTestAccess {

    private StudyWriteTransactionTestAccess() {
    }

    public static StudyWriteResult<StudyLearnView> recordLearning(
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            Clock clock,
            long actorId,
            long questionId,
            boolean correct,
            String source,
            int scopeId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        return new StudyWriteTransaction(state, receipts, clock).recordLearning(
                actorId,
                questionId,
                correct,
                new StudyApplicationService.ResolvedScope(source, scopeId),
                idempotencyKey,
                requestSha256);
    }

    public static StudyWriteResult<StudyReviewRecordView> recordReview(
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            Clock clock,
            long actorId,
            long questionId,
            StudyReviewRating rating,
            String source,
            int scopeId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        return new StudyWriteTransaction(state, receipts, clock).recordReview(
                actorId,
                questionId,
                rating,
                new StudyApplicationService.ResolvedScope(source, scopeId),
                idempotencyKey,
                requestSha256);
    }

    public static StudyWriteResult<StudyReviewMasterView> setReviewMastered(
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            Clock clock,
            long actorId,
            long questionId,
            boolean mastered,
            String source,
            int scopeId,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        return new StudyWriteTransaction(state, receipts, clock).setReviewMastered(
                actorId,
                questionId,
                mastered,
                new StudyApplicationService.ResolvedScope(source, scopeId),
                idempotencyKey,
                requestSha256);
    }
}
