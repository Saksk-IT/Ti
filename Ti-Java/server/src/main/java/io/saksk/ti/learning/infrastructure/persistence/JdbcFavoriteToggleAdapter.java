package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.FavoriteTogglePort;
import java.util.Objects;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Repository
class JdbcFavoriteToggleAdapter implements FavoriteTogglePort {

    private final JdbcClient jdbc;

    JdbcFavoriteToggleAdapter(JdbcClient jdbc) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
    }

    @Override
    public boolean toggle(long actorId, long questionId) {
        requireWritableTransaction();
        Optional<Long> existing = jdbc.sql("""
                        SELECT id
                          FROM favorites
                         WHERE user_id = :actorId
                           AND question_id = :questionId
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .query(Long.class)
                .optional();
        if (existing.isPresent()) {
            int removed = jdbc.sql("""
                            DELETE FROM favorites
                             WHERE id = :favoriteId
                               AND user_id = :actorId
                               AND question_id = :questionId
                            """)
                    .param("favoriteId", existing.orElseThrow())
                    .param("actorId", actorId)
                    .param("questionId", questionId)
                    .update();
            if (removed != 1) {
                throw new IllegalStateException(
                        "Concurrent favorite removal changed no row");
            }
            return false;
        }

        int inserted = jdbc.sql("""
                        INSERT INTO favorites (user_id, question_id, created_at)
                        VALUES (:actorId, :questionId, CURRENT_TIMESTAMP)
                        """)
                .param("actorId", actorId)
                .param("questionId", questionId)
                .update();
        if (inserted != 1) {
            throw new IllegalStateException("Favorite insertion changed no row");
        }
        return true;
    }

    private static void requireWritableTransaction() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()
                || TransactionSynchronizationManager.isCurrentTransactionReadOnly()) {
            throw new IllegalStateException(
                    "Favorite mutations require an active writable transaction");
        }
    }
}
