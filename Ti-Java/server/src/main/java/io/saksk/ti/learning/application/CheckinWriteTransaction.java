package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.CheckinResult;
import io.saksk.ti.learning.api.CheckinView;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.application.port.CheckinStatePort;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;
import tools.jackson.databind.json.JsonMapper;

@Service
class CheckinWriteTransaction {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Set<String> RECEIPT_FIELDS = Set.of(
            "today",
            "checked_in_today",
            "checked_in_at",
            "streak_days",
            "total_days",
            "just_checked_in",
            "checked_dates");

    private final CheckinStatePort state;
    private final LearningWriteReceiptPort receipts;

    CheckinWriteTransaction(
            CheckinStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        this.state = Objects.requireNonNull(state, "state");
        this.receipts = Objects.requireNonNull(receipts, "receipts");
    }

    @Transactional
    public CheckinResult execute(
            long actorId,
            LocalDate today,
            LocalDateTime now,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        today = Objects.requireNonNull(today, "today");
        now = Objects.requireNonNull(now, "now");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
        requestSha256 = Objects.requireNonNull(requestSha256, "requestSha256");
        if (!now.toLocalDate().equals(today)) {
            throw new IllegalArgumentException(
                    "Check-in timestamp must belong to the supplied Beijing date");
        }

        String rawKey = idempotencyKey.value().orElse(null);
        if (rawKey != null) {
            LearningWriteReceiptPort.BeginResult begin =
                    receipts.begin(new LearningWriteReceiptPort.BeginCommand(
                            actorId,
                            LearningWriteReceiptPort.Operation.CHECKIN,
                            rawKey,
                            requestSha256));
            switch (begin.outcome()) {
                case CONFLICT:
                    return CheckinResult.idempotencyConflict();
                case IN_PROGRESS:
                    return CheckinResult.idempotencyInProgress();
                case REPLAY:
                    return CheckinResult.success(
                            decode(begin.replay().orElseThrow()),
                            true);
                case ACQUIRED:
                    break;
            }
        }

        boolean inserted = state.insertIfAbsent(actorId, today, now);
        Optional<LocalDateTime> checkedInAt = state.findCreatedAt(actorId, today);
        long totalDays = state.countAll(actorId);
        int streakDays = calculateStreak(
                state.listRecentDateValues(actorId, 100),
                today);
        LocalDate monthStart = today.withDayOfMonth(1);
        LocalDate nextMonthStart = monthStart.plusMonths(1);
        List<String> checkedDates =
                state.listDateValues(actorId, monthStart, nextMonthStart);
        CheckinView view = new CheckinView(
                today,
                true,
                checkedInAt,
                streakDays,
                totalDays,
                inserted,
                checkedDates);

        if (rawKey == null) {
            return CheckinResult.success(view, false);
        }
        LearningWriteReceiptPort.StoredResponse stored =
                receipts.complete(new LearningWriteReceiptPort.CompleteCommand(
                        actorId,
                        LearningWriteReceiptPort.Operation.CHECKIN,
                        rawKey,
                        requestSha256,
                        200,
                        encode(view)));
        return CheckinResult.success(decode(stored), false);
    }

    static int calculateStreak(List<String> rawDates, LocalDate today) {
        Objects.requireNonNull(rawDates, "rawDates");
        Objects.requireNonNull(today, "today");
        try {
            List<LocalDate> dates = new ArrayList<>();
            Set<LocalDate> distinct = new HashSet<>();
            for (String rawDate : rawDates) {
                LocalDate date = LocalDate.parse(
                        Objects.requireNonNull(rawDate, "raw check-in date"));
                if (distinct.add(date)) {
                    dates.add(date);
                }
            }
            dates.sort(java.util.Comparator.reverseOrder());
            if (dates.isEmpty() || dates.getFirst().isBefore(today.minusDays(1))) {
                return 0;
            }
            int streak = 1;
            for (int index = 1; index < dates.size(); index++) {
                if (dates.get(index - 1).minusDays(1).equals(dates.get(index))) {
                    streak++;
                } else {
                    break;
                }
            }
            return streak;
        } catch (DateTimeParseException | NullPointerException exception) {
            return 0;
        }
    }

    private static String encode(CheckinView view) {
        ObjectNode root = JSON.createObjectNode();
        root.put("today", view.today().toString());
        root.put("checked_in_today", view.checkedInToday());
        view.checkedInAt().ifPresentOrElse(
                value -> root.put("checked_in_at", value.toString()),
                () -> root.putNull("checked_in_at"));
        root.put("streak_days", view.streakDays());
        root.put("total_days", view.totalDays());
        root.put("just_checked_in", view.justCheckedIn());
        ArrayNode dates = root.putArray("checked_dates");
        view.checkedDates().forEach(dates::add);
        return root.toString();
    }

    private static CheckinView decode(
            LearningWriteReceiptPort.StoredResponse response
    ) {
        if (response.status() != 200) {
            throw new IllegalStateException("Check-in receipt has an invalid status");
        }
        try {
            JsonNode root = JSON.readTree(response.bodyJson());
            requireReceiptObject(root);
            LocalDate today = LocalDate.parse(requireText(root, "today"));
            if (!root.path("checked_in_today").isBoolean()
                    || !root.path("checked_in_today").booleanValue()) {
                throw new IllegalStateException(
                        "Check-in receipt must be checked in today");
            }
            JsonNode checkedAtNode = root.path("checked_in_at");
            Optional<LocalDateTime> checkedAt;
            if (checkedAtNode.isNull()) {
                checkedAt = Optional.empty();
            } else if (checkedAtNode.isTextual()) {
                checkedAt = Optional.of(LocalDateTime.parse(checkedAtNode.textValue()));
            } else {
                throw new IllegalStateException(
                        "Check-in receipt contains an invalid checked-in timestamp");
            }
            int streak = requireNonNegativeInt(root, "streak_days");
            long total = requireNonNegativeLong(root, "total_days");
            if (!root.path("just_checked_in").isBoolean()) {
                throw new IllegalStateException(
                        "Check-in receipt contains an invalid just-checked-in value");
            }
            JsonNode datesNode = root.path("checked_dates");
            if (!datesNode.isArray()) {
                throw new IllegalStateException(
                        "Check-in receipt contains an invalid checked-date list");
            }
            List<String> dates = new ArrayList<>();
            datesNode.forEach(node -> {
                if (!node.isTextual()) {
                    throw new IllegalStateException(
                            "Check-in receipt contains a non-text checked date");
                }
                dates.add(node.textValue());
            });
            return new CheckinView(
                    today,
                    true,
                    checkedAt,
                    streak,
                    total,
                    root.path("just_checked_in").booleanValue(),
                    dates);
        } catch (IllegalStateException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new IllegalStateException("Check-in receipt has invalid values", exception);
        }
    }

    private static void requireReceiptObject(JsonNode root) {
        if (root == null || !root.isObject()) {
            throw new IllegalStateException("Check-in receipt body must be an object");
        }
        Set<String> fields = new HashSet<>();
        fields.addAll(root.propertyNames());
        if (!fields.equals(RECEIPT_FIELDS)) {
            throw new IllegalStateException(
                    "Check-in receipt body contains an invalid field set");
        }
    }

    private static String requireText(JsonNode root, String field) {
        JsonNode node = root.path(field);
        if (!node.isTextual()) {
            throw new IllegalStateException(
                    "Check-in receipt contains an invalid " + field);
        }
        return node.textValue();
    }

    private static int requireNonNegativeInt(JsonNode root, String field) {
        JsonNode node = root.path(field);
        if (!node.isIntegralNumber() || !node.canConvertToInt() || node.intValue() < 0) {
            throw new IllegalStateException(
                    "Check-in receipt contains an invalid " + field);
        }
        return node.intValue();
    }

    private static long requireNonNegativeLong(JsonNode root, String field) {
        JsonNode node = root.path(field);
        if (!node.isIntegralNumber()
                || !node.canConvertToLong()
                || node.longValue() < 0L) {
            throw new IllegalStateException(
                    "Check-in receipt contains an invalid " + field);
        }
        return node.longValue();
    }
}
