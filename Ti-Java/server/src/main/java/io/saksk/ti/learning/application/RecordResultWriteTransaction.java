package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.QuizLimitPolicy;
import io.saksk.ti.learning.api.RecordResultAction;
import io.saksk.ti.learning.api.RecordResultResult;
import io.saksk.ti.learning.application.port.LearningWriteReceiptPort;
import io.saksk.ti.learning.application.port.RecordResultStatePort;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class RecordResultWriteTransaction {

    private static final Pattern QUOTA_RECEIPT =
            Pattern.compile("\\{\"quota\":\"(-?[0-9]+):(-?[0-9]+)\"}");

    private final RecordResultStatePort state;
    private final LearningWriteReceiptPort receipts;

    RecordResultWriteTransaction(
            RecordResultStatePort state,
            LearningWriteReceiptPort receipts
    ) {
        this.state = Objects.requireNonNull(state, "state");
        this.receipts = Objects.requireNonNull(receipts, "receipts");
    }

    @Transactional
    public RecordResultResult execute(
            long actorId,
            boolean administrator,
            long questionId,
            boolean correct,
            boolean clearMistakeOnCorrect,
            QuizLimitPolicy quizLimitPolicy,
            LearningWriteIdempotencyKey idempotencyKey,
            byte[] requestSha256
    ) {
        quizLimitPolicy = Objects.requireNonNull(quizLimitPolicy, "quizLimitPolicy");
        idempotencyKey = Objects.requireNonNull(idempotencyKey, "idempotencyKey");
        requestSha256 = Objects.requireNonNull(requestSha256, "requestSha256");

        String rawKey = idempotencyKey.value().orElse(null);
        if (rawKey != null) {
            LearningWriteReceiptPort.BeginResult begin =
                    receipts.begin(new LearningWriteReceiptPort.BeginCommand(
                            actorId,
                            LearningWriteReceiptPort.Operation.RECORD_RESULT,
                            rawKey,
                            requestSha256));
            switch (begin.outcome()) {
                case CONFLICT:
                    return RecordResultResult.idempotencyConflict();
                case IN_PROGRESS:
                    return RecordResultResult.idempotencyInProgress();
                case REPLAY:
                    return replay(begin.replay().orElseThrow());
                case ACQUIRED:
                    break;
            }
        }

        state.lockActor(actorId);
        if (quizLimitPolicy.enabled() && !administrator) {
            long currentCount = state.currentQuizCount(actorId);
            if (currentCount >= quizLimitPolicy.limitCount()) {
                RecordResultResult rejected = RecordResultResult.quizLimitReached(
                        currentCount,
                        quizLimitPolicy.limitCount(),
                        false);
                if (rawKey == null) {
                    return rejected;
                }
                LearningWriteReceiptPort.StoredResponse stored =
                        receipts.complete(new LearningWriteReceiptPort.CompleteCommand(
                                actorId,
                                LearningWriteReceiptPort.Operation.RECORD_RESULT,
                                rawKey,
                                requestSha256,
                                403,
                                quotaReceipt(currentCount, quizLimitPolicy.limitCount())));
                return decode(stored, false);
            }
        }

        RecordResultAction action;
        if (!correct) {
            state.addOrIncrementMistake(actorId, questionId);
            action = RecordResultAction.ADDED_MISTAKE;
        } else if (clearMistakeOnCorrect) {
            state.removeMistake(actorId, questionId);
            action = RecordResultAction.REMOVED_MISTAKE;
        } else {
            action = RecordResultAction.KEPT_MISTAKE;
        }
        state.replaceLatestAnswer(actorId, questionId, correct);
        if (quizLimitPolicy.enabled() && !administrator) {
            state.incrementQuizCount(actorId);
        }

        if (rawKey == null) {
            return RecordResultResult.success(action, false);
        }
        LearningWriteReceiptPort.StoredResponse stored =
                receipts.complete(new LearningWriteReceiptPort.CompleteCommand(
                        actorId,
                        LearningWriteReceiptPort.Operation.RECORD_RESULT,
                        rawKey,
                        requestSha256,
                        200,
                        "{\"action\":\"" + action.wireValue() + "\"}"));
        return decode(stored, false);
    }

    private static RecordResultResult replay(
            LearningWriteReceiptPort.StoredResponse response
    ) {
        return decode(response, true);
    }

    private static RecordResultResult decode(
            LearningWriteReceiptPort.StoredResponse response,
            boolean replayed
    ) {
        String compact = response.bodyJson().replaceAll("\\s+", "");
        if (response.status() == 200
                && compact.startsWith("{\"action\":\"")
                && compact.endsWith("\"}")) {
            String value = compact.substring(
                    "{\"action\":\"".length(),
                    compact.length() - 2);
            return RecordResultResult.success(
                    RecordResultAction.fromWireValue(value),
                    replayed);
        }
        if (response.status() == 403) {
            Matcher matcher = QUOTA_RECEIPT.matcher(compact);
            if (matcher.matches()) {
                try {
                    return RecordResultResult.quizLimitReached(
                            Long.parseLong(matcher.group(1)),
                            Integer.parseInt(matcher.group(2)),
                            replayed);
                } catch (NumberFormatException exception) {
                    throw new IllegalStateException(
                            "Record-result receipt contains invalid quota numbers",
                            exception);
                }
            }
        }
        throw new IllegalStateException(
                "Record-result receipt contains an invalid persisted response");
    }

    private static String quotaReceipt(long currentCount, int limitCount) {
        return "{\"quota\":\"" + currentCount + ":" + limitCount + "\"}";
    }
}
