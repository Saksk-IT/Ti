package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.RecordResultStatePort;
import java.util.Objects;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Repository
class JdbcRecordResultStateAdapter implements RecordResultStatePort {

    private static final long RECORD_RESULT_LOCK_DOMAIN = 0x7252_6573_756C_7400L;

    private final JdbcClient jdbc;

    JdbcRecordResultStateAdapter(JdbcClient jdbc) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
    }

    @Override
    public void lockActor(long actorId) {
        requireWritableTransaction();
        long lockKey = RECORD_RESULT_LOCK_DOMAIN ^ actorId;
        jdbc.sql("SELECT pg_advisory_xact_lock(:lockKey)")
                .param("lockKey", lockKey)
                .query((row, rowNumber) -> Boolean.TRUE)
                .single();
    }

    @Override
    public long currentQuizCount(long actorId) {
        requireWritableTransaction();
        return jdbc.sql("""
                        SELECT COALESCE(total_answered, 0)::bigint
                          FROM user_quiz_stats
                         WHERE user_id = :actorId
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .optional()
                .orElse(0L);
    }

    @Override
    public void addOrIncrementMistake(long actorId, long questionId) {
        requireWritableTransaction();
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
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP,
                            CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (user_id, question_id)
                        DO UPDATE
                              SET wrong_count = COALESCE(mistakes.wrong_count, 0) + 1,
                                  updated_at = CURRENT_TIMESTAMP,
                                  last_updated = CURRENT_TIMESTAMP
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .update();
        requireSingleChange("mistake upsert", changed);
    }

    @Override
    public void removeMistake(long actorId, long questionId) {
        requireWritableTransaction();
        int changed = jdbc.sql("""
                        DELETE FROM mistakes
                         WHERE user_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .update();
        if (changed < 0 || changed > 1) {
            throw new IllegalStateException(
                    "Mistake removal changed an unexpected row count: " + changed);
        }
    }

    @Override
    public void replaceLatestAnswer(
            long actorId,
            long questionId,
            boolean correct
    ) {
        requireWritableTransaction();
        jdbc.sql("""
                        DELETE FROM user_answers
                         WHERE user_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .update();
        int inserted = jdbc.sql("""
                        INSERT INTO user_answers (
                            user_id,
                            question_id,
                            user_answer,
                            is_correct,
                            created_at
                        ) VALUES (
                            :actorId,
                            :questionId,
                            NULL,
                            :correct,
                            CURRENT_TIMESTAMP
                        )
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .param("correct", correct)
                .update();
        requireSingleChange("latest answer insert", inserted);
    }

    @Override
    public void incrementQuizCount(long actorId) {
        requireWritableTransaction();
        int changed = jdbc.sql("""
                        INSERT INTO user_quiz_stats (
                            user_id,
                            total_answered,
                            updated_at
                        ) VALUES (
                            :actorId,
                            1,
                            CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (user_id)
                        DO UPDATE
                              SET total_answered =
                                      COALESCE(user_quiz_stats.total_answered, 0) + 1,
                                  updated_at = CURRENT_TIMESTAMP
                        """)
                .param("actorId", actorId)
                .update();
        requireSingleChange("quiz count upsert", changed);
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
                    "Record-result mutations require an active writable transaction");
        }
    }
}
