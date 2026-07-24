package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.api.StudyScopeInput;
import io.saksk.ti.learning.application.port.StudyStatePort;
import java.sql.Types;
import java.time.LocalDateTime;
import java.util.Objects;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Repository
class JdbcStudyStateAdapter implements StudyStatePort {

    private static final long STUDY_LOCK_SEED = 0x5374_7564_7953_636fL;

    private final JdbcClient jdbc;

    JdbcStudyStateAdapter(JdbcClient jdbc) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
    }

    @Override
    public void lockScope(StudyKey key) {
        requireWritableTransaction();
        jdbc.sql("""
                        SELECT pg_advisory_xact_lock(
                            hashtextextended(CAST(:scopeKey AS text), :seed)
                        )
                        """)
                .param("scopeKey", canonicalLockKey(key))
                .param("seed", STUDY_LOCK_SEED)
                .query((row, rowNumber) -> Boolean.TRUE)
                .single();
    }

    @Override
    public Optional<LearningState> findLearning(StudyKey key) {
        requireWritableTransaction();
        return jdbc.sql("""
                        SELECT COALESCE(streak, 0) AS streak,
                               COALESCE(is_learned, false) AS is_learned,
                               COALESCE(correct_count, 0) AS correct_count,
                               COALESCE(wrong_count, 0) AS wrong_count,
                               COALESCE(last_result, 'wrong') AS last_result,
                               COALESCE(
                                   last_answered_at,
                                   TIMESTAMP '1970-01-01 00:00:00'
                               ) AS last_answered_at
                          FROM study_learning
                         WHERE user_id = :actorId
                           AND source = :source
                           AND scope_id = :scopeId
                           AND question_id = :questionId
                        """)
                .param("actorId", key.actorId())
                .param("source", key.source())
                .param("scopeId", key.scopeId())
                .param("questionId", key.questionId())
                .query((row, rowNumber) -> new LearningState(
                        row.getInt("streak"),
                        row.getBoolean("is_learned"),
                        row.getInt("correct_count"),
                        row.getInt("wrong_count"),
                        row.getString("last_result"),
                        row.getObject("last_answered_at", LocalDateTime.class)))
                .optional();
    }

    @Override
    public void saveLearning(
            StudyKey key,
            LearningState state,
            LocalDateTime now
    ) {
        requireWritableTransaction();
        int changed = jdbc.sql("""
                        INSERT INTO study_learning (
                            user_id,
                            source,
                            scope_id,
                            question_id,
                            streak,
                            is_learned,
                            correct_count,
                            wrong_count,
                            last_result,
                            last_answered_at,
                            created_at,
                            updated_at
                        ) VALUES (
                            :actorId,
                            :source,
                            :scopeId,
                            :questionId,
                            :streak,
                            :learned,
                            :correctCount,
                            :wrongCount,
                            :lastResult,
                            :lastAnsweredAt,
                            :now,
                            :now
                        )
                        ON CONFLICT (user_id, source, scope_id, question_id)
                        DO UPDATE
                              SET streak = EXCLUDED.streak,
                                  is_learned = EXCLUDED.is_learned,
                                  correct_count = EXCLUDED.correct_count,
                                  wrong_count = EXCLUDED.wrong_count,
                                  last_result = EXCLUDED.last_result,
                                  last_answered_at = EXCLUDED.last_answered_at,
                                  updated_at = EXCLUDED.updated_at
                        """)
                .param("actorId", key.actorId())
                .param("source", key.source())
                .param("scopeId", key.scopeId())
                .param("questionId", key.questionId())
                .param("streak", state.streak())
                .param("learned", state.learned())
                .param("correctCount", state.correctCount())
                .param("wrongCount", state.wrongCount())
                .param("lastResult", state.lastResult())
                .param("lastAnsweredAt", state.lastAnsweredAt())
                .param("now", now)
                .update();
        requireSingleChange("study learning upsert", changed);
    }

    @Override
    public void addMistake(StudyKey key, LocalDateTime now) {
        requireWritableTransaction();
        if (StudyScopeInput.USER_BANK_SOURCE.equals(key.source())) {
            addPersonalBankMistake(key, now);
        } else {
            addPublicMistake(key, now);
        }
    }

    @Override
    public void activateReview(
            StudyKey key,
            LocalDateTime dueAt,
            LocalDateTime now
    ) {
        requireWritableTransaction();
        int changed = jdbc.sql("""
                        INSERT INTO study_review (
                            user_id,
                            source,
                            scope_id,
                            question_id,
                            review_level,
                            next_due_at,
                            last_review_at,
                            last_rating,
                            lapse_count,
                            is_mastered,
                            created_at,
                            updated_at
                        ) VALUES (
                            :actorId,
                            :source,
                            :scopeId,
                            :questionId,
                            0,
                            :dueAt,
                            NULL,
                            NULL,
                            0,
                            false,
                            :now,
                            :now
                        )
                        ON CONFLICT (user_id, source, scope_id, question_id)
                        DO UPDATE
                              SET is_mastered = false,
                                  next_due_at = COALESCE(
                                      study_review.next_due_at,
                                      EXCLUDED.next_due_at
                                  ),
                                  updated_at = EXCLUDED.updated_at
                        """)
                .param("actorId", key.actorId())
                .param("source", key.source())
                .param("scopeId", key.scopeId())
                .param("questionId", key.questionId())
                .param("dueAt", dueAt)
                .param("now", now)
                .update();
        requireSingleChange("study review activation", changed);
    }

    @Override
    public Optional<ReviewState> findReview(StudyKey key) {
        requireWritableTransaction();
        return jdbc.sql("""
                        SELECT COALESCE(review_level, 0) AS review_level,
                               next_due_at,
                               last_review_at,
                               last_rating,
                               COALESCE(lapse_count, 0) AS lapse_count,
                               COALESCE(is_mastered, false) AS is_mastered
                          FROM study_review
                         WHERE user_id = :actorId
                           AND source = :source
                           AND scope_id = :scopeId
                           AND question_id = :questionId
                        """)
                .param("actorId", key.actorId())
                .param("source", key.source())
                .param("scopeId", key.scopeId())
                .param("questionId", key.questionId())
                .query((row, rowNumber) -> new ReviewState(
                        row.getInt("review_level"),
                        Optional.ofNullable(
                                row.getObject("next_due_at", LocalDateTime.class)),
                        Optional.ofNullable(
                                row.getObject("last_review_at", LocalDateTime.class)),
                        Optional.ofNullable(row.getString("last_rating")),
                        row.getInt("lapse_count"),
                        row.getBoolean("is_mastered")))
                .optional();
    }

    @Override
    public void saveReview(
            StudyKey key,
            ReviewState state,
            LocalDateTime now
    ) {
        requireWritableTransaction();
        int changed = jdbc.sql("""
                        INSERT INTO study_review (
                            user_id,
                            source,
                            scope_id,
                            question_id,
                            review_level,
                            next_due_at,
                            last_review_at,
                            last_rating,
                            lapse_count,
                            is_mastered,
                            created_at,
                            updated_at
                        ) VALUES (
                            :actorId,
                            :source,
                            :scopeId,
                            :questionId,
                            :reviewLevel,
                            :nextDueAt,
                            :lastReviewAt,
                            :lastRating,
                            :lapseCount,
                            :mastered,
                            :now,
                            :now
                        )
                        ON CONFLICT (user_id, source, scope_id, question_id)
                        DO UPDATE
                              SET review_level = EXCLUDED.review_level,
                                  next_due_at = EXCLUDED.next_due_at,
                                  last_review_at = EXCLUDED.last_review_at,
                                  last_rating = EXCLUDED.last_rating,
                                  lapse_count = EXCLUDED.lapse_count,
                                  is_mastered = EXCLUDED.is_mastered,
                                  updated_at = EXCLUDED.updated_at
                        """)
                .param("actorId", key.actorId())
                .param("source", key.source())
                .param("scopeId", key.scopeId())
                .param("questionId", key.questionId())
                .param("reviewLevel", state.reviewLevel())
                .param(
                        "nextDueAt",
                        state.nextDueAt().orElse(null),
                        Types.TIMESTAMP)
                .param(
                        "lastReviewAt",
                        state.lastReviewAt().orElse(null),
                        Types.TIMESTAMP)
                .param(
                        "lastRating",
                        state.lastRating().orElse(null),
                        Types.VARCHAR)
                .param("lapseCount", state.lapseCount())
                .param("mastered", state.mastered())
                .param("now", now)
                .update();
        requireSingleChange("study review upsert", changed);
    }

    private void addPublicMistake(StudyKey key, LocalDateTime now) {
        int changed = jdbc.sql("""
                        INSERT INTO mistakes (
                            user_id,
                            question_id,
                            wrong_count,
                            created_at,
                            updated_at,
                            last_updated
                        ) VALUES (
                            :actorId,
                            :questionId,
                            1,
                            :now,
                            :now,
                            :now
                        )
                        ON CONFLICT (user_id, question_id)
                        DO UPDATE
                              SET wrong_count = COALESCE(mistakes.wrong_count, 0) + 1,
                                  updated_at = EXCLUDED.updated_at,
                                  last_updated = EXCLUDED.last_updated
                        """)
                .param("actorId", key.actorId())
                .param("questionId", key.questionId())
                .param("now", now)
                .update();
        requireSingleChange("public study mistake upsert", changed);
    }

    private void addPersonalBankMistake(StudyKey key, LocalDateTime now) {
        int changed = jdbc.sql("""
                        INSERT INTO user_bank_mistakes (
                            user_id,
                            bank_id,
                            question_id,
                            wrong_count,
                            created_at,
                            updated_at
                        ) VALUES (
                            :actorId,
                            :scopeId,
                            :questionId,
                            1,
                            :now,
                            :now
                        )
                        ON CONFLICT (user_id, question_id)
                        DO UPDATE
                              SET wrong_count =
                                      COALESCE(user_bank_mistakes.wrong_count, 0) + 1,
                                  updated_at = EXCLUDED.updated_at
                        """)
                .param("actorId", key.actorId())
                .param("scopeId", key.scopeId())
                .param("questionId", key.questionId())
                .param("now", now)
                .update();
        requireSingleChange("personal-bank study mistake upsert", changed);
    }

    private static String canonicalLockKey(StudyKey key) {
        return key.actorId()
                + "|" + key.source().length() + ":" + key.source()
                + "|" + key.scopeId()
                + "|" + key.questionId();
    }

    private static void requireSingleChange(String operation, int changed) {
        if (changed != 1) {
            throw new IllegalStateException(
                    operation + " changed an unexpected row count: " + changed);
        }
    }

    private static void requireWritableTransaction() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()
                || TransactionSynchronizationManager.isCurrentTransactionReadOnly()) {
            throw new IllegalStateException(
                    "Study mutations require an active writable transaction");
        }
    }
}
