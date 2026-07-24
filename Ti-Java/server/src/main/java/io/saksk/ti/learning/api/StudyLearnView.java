package io.saksk.ti.learning.api;

import java.time.LocalDateTime;
import java.util.Objects;
import java.util.Optional;

/** Result data for one study learning transition. */
public record StudyLearnView(
        int streak,
        boolean learned,
        Optional<LocalDateTime> nextDueAt
) {

    public StudyLearnView {
        nextDueAt = Objects.requireNonNull(nextDueAt, "nextDueAt");
    }
}
