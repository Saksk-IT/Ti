package io.saksk.ti.learning.application.port;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

/**
 * Learning-owned persistence boundary for daily check-in state and response aggregates.
 *
 * <p>All methods must participate in the caller's writable learning transaction.
 */
public interface CheckinStatePort {

    boolean insertIfAbsent(long actorId, LocalDate date, LocalDateTime createdAt);

    Optional<LocalDateTime> findCreatedAt(long actorId, LocalDate date);

    long countAll(long actorId);

    List<String> listRecentDateValues(long actorId, int limit);

    List<String> listDateValues(
            long actorId,
            LocalDate inclusiveStart,
            LocalDate exclusiveEnd);
}
