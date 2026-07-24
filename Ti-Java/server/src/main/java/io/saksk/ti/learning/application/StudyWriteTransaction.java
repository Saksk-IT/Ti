package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRating;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyWriteOutcome;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.learning.application.StudyApplicationService.ResolvedScope;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.StudyStatePort;
import io.saksk.ti.learning.application.port.StudyStatePort.LearningState;
import io.saksk.ti.learning.application.port.StudyStatePort.ReviewState;
import io.saksk.ti.learning.application.port.StudyStatePort.StudyKey;
import java.time.Clock;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.util.Objects;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class StudyWriteTransaction {

    private static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");
    private static final int[] REVIEW_INTERVAL_DAYS = {1, 2, 4, 7, 15, 30, 60, 120};
    private static final Pattern LEARN_RECEIPT = Pattern.compile(
            "\\{\"streak\":(-?[0-9]+),\"is_learned\":([01]),"
                    + "\"next_due_at\":(null|\"([^\"]+)\")}");
    private static final Pattern REVIEW_RECEIPT = Pattern.compile(
            "\\{\"review_level\":([0-7]),\"next_due_at\":\"([^\"]+)\"}");
    private static final Pattern REVIEW_RECEIPT_JSONB_ORDER = Pattern.compile(
            "\\{\"next_due_at\":\"([^\"]+)\",\"review_level\":([0-7])}");
    private static final Pattern MASTER_RECEIPT =
            Pattern.compile("\\{\"is_mastered\":([01])}");

    private final StudyStatePort state;
    private final LearningWriteReceiptPort receipts;
    private final Clock clock;

    @Autowired
    StudyWriteTransaction(
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            ObjectProvider<Clock> clocks
    ) {
        this(
                state,
                receipts,
                Objects.requireNonNull(clocks, "clocks")
                        .getIfAvailable(Clock::systemUTC));
    }

    StudyWriteTransaction(
            StudyStatePort state,
            LearningWriteReceiptPort receipts,
            Clock clock
    ) {
        this.state = Objects.requireNonNull(state, "state");
        this.receipts = Objects.requireNonNull(receipts, "receipts");
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    @Transactional
    public StudyWriteResult<StudyLearnView> recordLearning(
            long actorId,
            long questionId,
            boolean correct,
            ResolvedScope scope,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        PreparedReceipt prepared = begin(
                actorId,
                LearningWriteReceiptPort.Operation.STUDY_LEARN,
                idempotencyKey,
                requestSha256);
        if (prepared.terminal().isPresent()) {
            return terminalLearn(prepared.terminal().orElseThrow());
        }

        StudyKey key = key(actorId, questionId, scope);
        state.lockScope(key);
        LocalDateTime now = now();
        LearningState previous = state.findLearning(key)
                .orElse(new LearningState(0, false, 0, 0, "wrong", now));
        int streak = correct ? Math.addExact(previous.streak(), 1) : 0;
        boolean learned = streak >= 3;
        int correctCount = correct
                ? Math.addExact(previous.correctCount(), 1)
                : previous.correctCount();
        int wrongCount = correct
                ? previous.wrongCount()
                : Math.addExact(previous.wrongCount(), 1);
        state.saveLearning(
                key,
                new LearningState(
                        streak,
                        learned,
                        correctCount,
                        wrongCount,
                        correct ? "correct" : "wrong",
                        now),
                now);
        if (!correct) {
            state.addMistake(key, now);
        }

        Optional<LocalDateTime> nextDueAt = Optional.empty();
        if (learned && !previous.learned()) {
            LocalDateTime dueAt = nextFourAm(now);
            state.activateReview(key, dueAt, now);
            nextDueAt = Optional.of(dueAt);
        }
        StudyLearnView view = new StudyLearnView(streak, learned, nextDueAt);
        if (prepared.rawKey().isEmpty()) {
            return StudyWriteResult.success(view, false);
        }
        LearningWriteReceiptPort.StoredResponse stored = complete(
                actorId,
                LearningWriteReceiptPort.Operation.STUDY_LEARN,
                prepared.rawKey().orElseThrow(),
                requestSha256,
                learnReceipt(view));
        return StudyWriteResult.success(decodeLearn(stored), false);
    }

    @Transactional
    public StudyWriteResult<StudyReviewRecordView> recordReview(
            long actorId,
            long questionId,
            StudyReviewRating rating,
            ResolvedScope scope,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        PreparedReceipt prepared = begin(
                actorId,
                LearningWriteReceiptPort.Operation.STUDY_REVIEW_RECORD,
                idempotencyKey,
                requestSha256);
        if (prepared.terminal().isPresent()) {
            return terminalReview(prepared.terminal().orElseThrow());
        }

        StudyKey key = key(actorId, questionId, scope);
        state.lockScope(key);
        ReviewState previous = state.findReview(key).orElseGet(ReviewState::empty);
        int level;
        int lapseCount = previous.lapseCount();
        switch (rating) {
            case KNOWN -> level = clampLevel(previous.reviewLevel() + 1);
            case FUZZY -> level = clampLevel(previous.reviewLevel() - 1);
            case UNKNOWN -> {
                level = 0;
                lapseCount = Math.addExact(lapseCount, 1);
            }
            default -> throw new IllegalStateException("Unsupported review rating: " + rating);
        }
        LocalDateTime now = now();
        LocalDateTime nextDueAt = nextFourAm(now).plusDays(REVIEW_INTERVAL_DAYS[level]);
        state.saveReview(
                key,
                new ReviewState(
                        level,
                        Optional.of(nextDueAt),
                        Optional.of(now),
                        Optional.of(rating.wireValue()),
                        lapseCount,
                        false),
                now);
        StudyReviewRecordView view = new StudyReviewRecordView(level, nextDueAt);
        if (prepared.rawKey().isEmpty()) {
            return StudyWriteResult.success(view, false);
        }
        LearningWriteReceiptPort.StoredResponse stored = complete(
                actorId,
                LearningWriteReceiptPort.Operation.STUDY_REVIEW_RECORD,
                prepared.rawKey().orElseThrow(),
                requestSha256,
                reviewReceipt(view));
        return StudyWriteResult.success(decodeReview(stored), false);
    }

    @Transactional
    public StudyWriteResult<StudyReviewMasterView> setReviewMastered(
            long actorId,
            long questionId,
            boolean mastered,
            ResolvedScope scope,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        PreparedReceipt prepared = begin(
                actorId,
                LearningWriteReceiptPort.Operation.STUDY_REVIEW_MASTER,
                idempotencyKey,
                requestSha256);
        if (prepared.terminal().isPresent()) {
            return terminalMaster(prepared.terminal().orElseThrow());
        }

        StudyKey key = key(actorId, questionId, scope);
        state.lockScope(key);
        ReviewState previous = state.findReview(key).orElseGet(ReviewState::empty);
        LocalDateTime now = now();
        state.saveReview(
                key,
                new ReviewState(
                        previous.reviewLevel(),
                        mastered ? Optional.empty() : Optional.of(nextFourAm(now)),
                        previous.lastReviewAt(),
                        previous.lastRating(),
                        previous.lapseCount(),
                        mastered),
                now);
        StudyReviewMasterView view = new StudyReviewMasterView(mastered);
        if (prepared.rawKey().isEmpty()) {
            return StudyWriteResult.success(view, false);
        }
        LearningWriteReceiptPort.StoredResponse stored = complete(
                actorId,
                LearningWriteReceiptPort.Operation.STUDY_REVIEW_MASTER,
                prepared.rawKey().orElseThrow(),
                requestSha256,
                masterReceipt(view));
        return StudyWriteResult.success(decodeMaster(stored), false);
    }

    private PreparedReceipt begin(
            long actorId,
            LearningWriteReceiptPort.Operation operation,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        Objects.requireNonNull(idempotencyKey, "idempotencyKey");
        Objects.requireNonNull(requestSha256, "requestSha256");
        String rawKey = idempotencyKey.value().orElse(null);
        if (rawKey == null) {
            return PreparedReceipt.executeWithoutReceipt();
        }
        LearningWriteReceiptPort.BeginResult begin =
                receipts.begin(new LearningWriteReceiptPort.BeginCommand(
                        actorId,
                        operation,
                        rawKey,
                        requestSha256));
        return switch (begin.outcome()) {
            case ACQUIRED -> PreparedReceipt.acquired(rawKey);
            case CONFLICT -> PreparedReceipt.terminal(TerminalReceipt.forConflict());
            case IN_PROGRESS -> PreparedReceipt.terminal(TerminalReceipt.forInProgress());
            case REPLAY -> PreparedReceipt.terminal(
                    TerminalReceipt.replay(begin.replay().orElseThrow()));
        };
    }

    private LearningWriteReceiptPort.StoredResponse complete(
            long actorId,
            LearningWriteReceiptPort.Operation operation,
            String rawKey,
            byte[] requestSha256,
            String body
    ) {
        return receipts.complete(new LearningWriteReceiptPort.CompleteCommand(
                actorId,
                operation,
                rawKey,
                requestSha256,
                200,
                body));
    }

    private static StudyKey key(
            long actorId,
            long questionId,
            ResolvedScope scope
    ) {
        return new StudyKey(actorId, scope.source(), scope.scopeId(), questionId);
    }

    private LocalDateTime now() {
        return LocalDateTime.ofInstant(clock.instant(), BEIJING);
    }

    static LocalDateTime nextFourAm(LocalDateTime now) {
        LocalDate date = now.toLocalDate();
        LocalDateTime target = LocalDateTime.of(date, LocalTime.of(4, 0));
        return now.isBefore(target) ? target : target.plusDays(1);
    }

    private static int clampLevel(int level) {
        return Math.max(0, Math.min(level, REVIEW_INTERVAL_DAYS.length - 1));
    }

    private static <T> StudyWriteResult<T> terminalRejection(TerminalReceipt terminal) {
        return StudyWriteResult.rejected(
                terminal.conflict()
                        ? StudyWriteOutcome.IDEMPOTENCY_CONFLICT
                        : StudyWriteOutcome.IDEMPOTENCY_IN_PROGRESS);
    }

    private static StudyWriteResult<StudyLearnView> terminalLearn(
            TerminalReceipt terminal
    ) {
        if (terminal.replay().isEmpty()) {
            return terminalRejection(terminal);
        }
        return StudyWriteResult.success(
                decodeLearn(terminal.replay().orElseThrow()),
                true);
    }

    private static StudyWriteResult<StudyReviewRecordView> terminalReview(
            TerminalReceipt terminal
    ) {
        if (terminal.replay().isEmpty()) {
            return terminalRejection(terminal);
        }
        return StudyWriteResult.success(
                decodeReview(terminal.replay().orElseThrow()),
                true);
    }

    private static StudyWriteResult<StudyReviewMasterView> terminalMaster(
            TerminalReceipt terminal
    ) {
        if (terminal.replay().isEmpty()) {
            return terminalRejection(terminal);
        }
        return StudyWriteResult.success(
                decodeMaster(terminal.replay().orElseThrow()),
                true);
    }

    private static String learnReceipt(StudyLearnView view) {
        String due = view.nextDueAt()
                .map(value -> "\"" + value + "\"")
                .orElse("null");
        return "{\"streak\":" + view.streak()
                + ",\"is_learned\":" + (view.learned() ? 1 : 0)
                + ",\"next_due_at\":" + due + "}";
    }

    private static StudyLearnView decodeLearn(
            LearningWriteReceiptPort.StoredResponse response
    ) {
        requireSuccess(response, "study-learn");
        Matcher matcher = LEARN_RECEIPT.matcher(compact(response.bodyJson()));
        if (!matcher.matches()) {
            throw new IllegalStateException("Study-learn receipt has an invalid body");
        }
        try {
            Optional<LocalDateTime> due = "null".equals(matcher.group(3))
                    ? Optional.empty()
                    : Optional.of(LocalDateTime.parse(matcher.group(4)));
            return new StudyLearnView(
                    Integer.parseInt(matcher.group(1)),
                    "1".equals(matcher.group(2)),
                    due);
        } catch (NumberFormatException | DateTimeParseException exception) {
            throw new IllegalStateException("Study-learn receipt has invalid values", exception);
        }
    }

    private static String reviewReceipt(StudyReviewRecordView view) {
        return "{\"review_level\":" + view.reviewLevel()
                + ",\"next_due_at\":\"" + view.nextDueAt() + "\"}";
    }

    private static StudyReviewRecordView decodeReview(
            LearningWriteReceiptPort.StoredResponse response
    ) {
        requireSuccess(response, "study-review-record");
        String compact = compact(response.bodyJson());
        Matcher matcher = REVIEW_RECEIPT.matcher(compact);
        Matcher jsonbMatcher = REVIEW_RECEIPT_JSONB_ORDER.matcher(compact);
        boolean emittedOrder = matcher.matches();
        boolean jsonbOrder = jsonbMatcher.matches();
        if (!emittedOrder && !jsonbOrder) {
            throw new IllegalStateException("Study-review receipt has an invalid body");
        }
        try {
            return new StudyReviewRecordView(
                    Integer.parseInt(
                            emittedOrder
                                    ? matcher.group(1)
                                    : jsonbMatcher.group(2)),
                    LocalDateTime.parse(
                            emittedOrder
                                    ? matcher.group(2)
                                    : jsonbMatcher.group(1)));
        } catch (NumberFormatException | DateTimeParseException exception) {
            throw new IllegalStateException("Study-review receipt has invalid values", exception);
        }
    }

    private static String masterReceipt(StudyReviewMasterView view) {
        return "{\"is_mastered\":" + (view.mastered() ? 1 : 0) + "}";
    }

    private static StudyReviewMasterView decodeMaster(
            LearningWriteReceiptPort.StoredResponse response
    ) {
        requireSuccess(response, "study-review-master");
        Matcher matcher = MASTER_RECEIPT.matcher(compact(response.bodyJson()));
        if (!matcher.matches()) {
            throw new IllegalStateException("Study-master receipt has an invalid body");
        }
        return new StudyReviewMasterView("1".equals(matcher.group(1)));
    }

    private static void requireSuccess(
            LearningWriteReceiptPort.StoredResponse response,
            String operation
    ) {
        if (response.status() != 200) {
            throw new IllegalStateException(operation + " receipt has an invalid status");
        }
    }

    private static String compact(String body) {
        return body.replaceAll("\\s+", "");
    }

    private record PreparedReceipt(
            Optional<String> rawKey,
            Optional<TerminalReceipt> terminal
    ) {
        private PreparedReceipt {
            rawKey = Objects.requireNonNull(rawKey, "rawKey");
            terminal = Objects.requireNonNull(terminal, "terminal");
            if (rawKey.isPresent() && terminal.isPresent()) {
                throw new IllegalArgumentException(
                        "A prepared receipt cannot both execute and terminate");
            }
        }

        static PreparedReceipt executeWithoutReceipt() {
            return new PreparedReceipt(Optional.empty(), Optional.empty());
        }

        static PreparedReceipt acquired(String rawKey) {
            return new PreparedReceipt(Optional.of(rawKey), Optional.empty());
        }

        static PreparedReceipt terminal(TerminalReceipt terminal) {
            return new PreparedReceipt(Optional.empty(), Optional.of(terminal));
        }

        @Override
        public String toString() {
            return "PreparedReceipt[rawKey=<redacted>, terminal=" + terminal.isPresent() + "]";
        }
    }

    private record TerminalReceipt(
            boolean conflict,
            Optional<LearningWriteReceiptPort.StoredResponse> replay
    ) {
        private TerminalReceipt {
            replay = Objects.requireNonNull(replay, "replay");
            if (conflict && replay.isPresent()) {
                throw new IllegalArgumentException("A conflict cannot carry a replay");
            }
        }

        static TerminalReceipt forConflict() {
            return new TerminalReceipt(true, Optional.empty());
        }

        static TerminalReceipt forInProgress() {
            return new TerminalReceipt(false, Optional.empty());
        }

        static TerminalReceipt replay(LearningWriteReceiptPort.StoredResponse response) {
            return new TerminalReceipt(false, Optional.of(response));
        }
    }
}
