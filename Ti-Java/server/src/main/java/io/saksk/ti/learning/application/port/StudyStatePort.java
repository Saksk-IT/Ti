package io.saksk.ti.learning.application.port;

import java.time.LocalDateTime;
import java.util.Objects;
import java.util.Optional;

/**
 * Learning-owned persistence boundary for study learning and spaced-review transitions.
 *
 * <p>Every method participates in the caller's writable learning transaction. Scope access and
 * question membership are immutable provider snapshots resolved before entering this boundary.
 */
public interface StudyStatePort {

    void lockScope(StudyKey key);

    Optional<LearningState> findLearning(StudyKey key);

    void saveLearning(StudyKey key, LearningState state, LocalDateTime now);

    void addMistake(StudyKey key, LocalDateTime now);

    void activateReview(StudyKey key, LocalDateTime dueAt, LocalDateTime now);

    Optional<ReviewState> findReview(StudyKey key);

    void saveReview(StudyKey key, ReviewState state, LocalDateTime now);

    record StudyKey(long actorId, String source, int scopeId, long questionId) {
        public StudyKey {
            if (actorId <= 0L) {
                throw new IllegalArgumentException("actorId must be positive");
            }
            source = Objects.requireNonNull(source, "source");
            if (source.isBlank()) {
                throw new IllegalArgumentException("source must not be blank");
            }
            if (scopeId <= 0) {
                throw new IllegalArgumentException("scopeId must be positive");
            }
            if (questionId <= 0L) {
                throw new IllegalArgumentException("questionId must be positive");
            }
        }
    }

    record LearningState(
            int streak,
            boolean learned,
            int correctCount,
            int wrongCount,
            String lastResult,
            LocalDateTime lastAnsweredAt
    ) {
        public LearningState {
            lastResult = Objects.requireNonNull(lastResult, "lastResult");
            if (!lastResult.equals("correct") && !lastResult.equals("wrong")) {
                throw new IllegalArgumentException("lastResult must be correct or wrong");
            }
            lastAnsweredAt = Objects.requireNonNull(lastAnsweredAt, "lastAnsweredAt");
        }
    }

    record ReviewState(
            int reviewLevel,
            Optional<LocalDateTime> nextDueAt,
            Optional<LocalDateTime> lastReviewAt,
            Optional<String> lastRating,
            int lapseCount,
            boolean mastered
    ) {
        public ReviewState {
            nextDueAt = Objects.requireNonNull(nextDueAt, "nextDueAt");
            lastReviewAt = Objects.requireNonNull(lastReviewAt, "lastReviewAt");
            lastRating = Objects.requireNonNull(lastRating, "lastRating");
        }

        public static ReviewState empty() {
            return new ReviewState(
                    0,
                    Optional.empty(),
                    Optional.empty(),
                    Optional.empty(),
                    0,
                    false);
        }
    }
}
