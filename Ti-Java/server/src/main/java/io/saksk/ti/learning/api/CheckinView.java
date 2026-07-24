package io.saksk.ti.learning.api;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/** Immutable legacy-compatible daily check-in response data. */
public record CheckinView(
        LocalDate today,
        boolean checkedInToday,
        Optional<LocalDateTime> checkedInAt,
        int streakDays,
        long totalDays,
        boolean justCheckedIn,
        List<String> checkedDates
) {

    public CheckinView {
        today = Objects.requireNonNull(today, "today");
        checkedInAt = Objects.requireNonNull(checkedInAt, "checkedInAt");
        if (!checkedInToday) {
            throw new IllegalArgumentException(
                    "A successful check-in result must be checked in today");
        }
        if (streakDays < 0 || totalDays < 0L) {
            throw new IllegalArgumentException(
                    "Check-in streak and total must not be negative");
        }
        checkedDates = List.copyOf(Objects.requireNonNull(checkedDates, "checkedDates"));
        if (checkedDates.stream().anyMatch(Objects::isNull)) {
            throw new NullPointerException("checkedDates must not contain null");
        }
    }
}
