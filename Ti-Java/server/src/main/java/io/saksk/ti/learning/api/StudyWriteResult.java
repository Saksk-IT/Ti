package io.saksk.ti.learning.api;

import java.util.Objects;
import java.util.Optional;

/** Typed outcome for a study write; only durable success can be replayed. */
public record StudyWriteResult<T>(
        StudyWriteOutcome outcome,
        Optional<T> data,
        boolean replayed
) {

    public StudyWriteResult {
        outcome = Objects.requireNonNull(outcome, "outcome");
        data = Objects.requireNonNull(data, "data");
        if ((outcome == StudyWriteOutcome.SUCCESS) != data.isPresent()) {
            throw new IllegalArgumentException(
                    "Study data must be present exactly for success");
        }
        if (replayed && outcome != StudyWriteOutcome.SUCCESS) {
            throw new IllegalArgumentException("Only successful study writes may be replayed");
        }
    }

    public static <T> StudyWriteResult<T> success(T data, boolean replayed) {
        return new StudyWriteResult<>(
                StudyWriteOutcome.SUCCESS,
                Optional.of(Objects.requireNonNull(data, "data")),
                replayed);
    }

    public static <T> StudyWriteResult<T> rejected(StudyWriteOutcome outcome) {
        if (Objects.requireNonNull(outcome, "outcome") == StudyWriteOutcome.SUCCESS) {
            throw new IllegalArgumentException("A rejection outcome must not be SUCCESS");
        }
        return new StudyWriteResult<>(outcome, Optional.empty(), false);
    }
}
