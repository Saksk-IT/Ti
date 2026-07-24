package io.saksk.ti.learning.api;

import java.time.LocalDateTime;
import java.util.Objects;

/** Result data for one spaced-review rating transition. */
public record StudyReviewRecordView(
        int reviewLevel,
        LocalDateTime nextDueAt
) {

    public StudyReviewRecordView {
        if (reviewLevel < 0 || reviewLevel > 7) {
            throw new IllegalArgumentException("reviewLevel must be between 0 and 7");
        }
        nextDueAt = Objects.requireNonNull(nextDueAt, "nextDueAt");
    }
}
