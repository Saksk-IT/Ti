package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.CheckinStatePort;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Repository
class JdbcCheckinStateAdapter implements CheckinStatePort {

    private final JdbcClient jdbc;

    JdbcCheckinStateAdapter(JdbcClient jdbc) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
    }

    @Override
    public boolean insertIfAbsent(
            long actorId,
            LocalDate date,
            LocalDateTime createdAt
    ) {
        requireWritableTransaction();
        int inserted = jdbc.sql("""
                        INSERT INTO user_checkins (
                            user_id,
                            checkin_date,
                            created_at
                        ) VALUES (
                            :actorId,
                            :checkinDate,
                            :createdAt
                        )
                        ON CONFLICT (user_id, checkin_date) DO NOTHING
                        """)
                .param("actorId", actorId)
                .param("checkinDate", date.toString())
                .param("createdAt", createdAt)
                .update();
        if (inserted < 0 || inserted > 1) {
            throw new IllegalStateException(
                    "Check-in insert changed an unexpected row count: " + inserted);
        }
        return inserted == 1;
    }

    @Override
    public Optional<LocalDateTime> findCreatedAt(long actorId, LocalDate date) {
        requireWritableTransaction();
        return jdbc.sql("""
                        SELECT created_at
                          FROM user_checkins
                         WHERE user_id = :actorId
                           AND checkin_date = :checkinDate
                        """)
                .param("actorId", actorId)
                .param("checkinDate", date.toString())
                .query(LocalDateTime.class)
                .optional();
    }

    @Override
    public long countAll(long actorId) {
        requireWritableTransaction();
        return jdbc.sql("""
                        SELECT COUNT(*)
                          FROM user_checkins
                         WHERE user_id = :actorId
                        """)
                .param("actorId", actorId)
                .query(Long.class)
                .single();
    }

    @Override
    public List<String> listRecentDateValues(long actorId, int limit) {
        requireWritableTransaction();
        if (limit <= 0) {
            throw new IllegalArgumentException("limit must be positive");
        }
        return List.copyOf(jdbc.sql("""
                        SELECT DISTINCT checkin_date
                          FROM user_checkins
                         WHERE user_id = :actorId
                         ORDER BY checkin_date DESC
                         LIMIT :limit
                        """)
                .param("actorId", actorId)
                .param("limit", limit)
                .query(String.class)
                .list());
    }

    @Override
    public List<String> listDateValues(
            long actorId,
            LocalDate inclusiveStart,
            LocalDate exclusiveEnd
    ) {
        requireWritableTransaction();
        if (!exclusiveEnd.isAfter(inclusiveStart)) {
            throw new IllegalArgumentException(
                    "exclusiveEnd must be after inclusiveStart");
        }
        return List.copyOf(jdbc.sql("""
                        SELECT checkin_date
                          FROM user_checkins
                         WHERE user_id = :actorId
                           AND checkin_date >= :inclusiveStart
                           AND checkin_date < :exclusiveEnd
                         ORDER BY checkin_date ASC
                        """)
                .param("actorId", actorId)
                .param("inclusiveStart", inclusiveStart.toString())
                .param("exclusiveEnd", exclusiveEnd.toString())
                .query(String.class)
                .list());
    }

    private static void requireWritableTransaction() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()
                || TransactionSynchronizationManager.isCurrentTransactionReadOnly()) {
            throw new IllegalStateException(
                    "Check-in persistence requires an active writable transaction");
        }
    }
}
