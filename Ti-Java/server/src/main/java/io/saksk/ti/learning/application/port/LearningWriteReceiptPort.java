package io.saksk.ti.learning.application.port;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Objects;
import java.util.Optional;

/**
 * Transaction-local idempotency receipt boundary for learning-owned write operations.
 *
 * <p>The raw key is transient input only. Implementations must persist only a keyed digest and
 * must participate in the caller's business transaction.
 */
public interface LearningWriteReceiptPort {

    BeginResult begin(BeginCommand command);

    StoredResponse complete(CompleteCommand command);

    enum Operation {
        FAVORITE("favorite"),
        RECORD_RESULT("record-result"),
        STUDY_LEARN("study-learn"),
        STUDY_REVIEW_RECORD("study-review-record"),
        STUDY_REVIEW_MASTER("study-review-master"),
        CHECKIN("checkin");

        private final String databaseValue;

        Operation(String databaseValue) {
            this.databaseValue = databaseValue;
        }

        public String databaseValue() {
            return databaseValue;
        }
    }

    enum BeginOutcome {
        ACQUIRED,
        REPLAY,
        CONFLICT,
        IN_PROGRESS
    }

    record BeginCommand(
            long actorId,
            Operation operation,
            String idempotencyKey,
            byte[] requestSha256
    ) {
        public BeginCommand {
            requireActor(actorId);
            operation = Objects.requireNonNull(operation, "operation");
            idempotencyKey = requireKey(idempotencyKey);
            requestSha256 = requireDigest(requestSha256);
        }

        @Override
        public byte[] requestSha256() {
            return Arrays.copyOf(requestSha256, requestSha256.length);
        }

        @Override
        public String toString() {
            return "BeginCommand[actorId=" + actorId
                    + ", operation=" + operation
                    + ", idempotencyKey=<redacted>, requestSha256=<redacted>]";
        }
    }

    record CompleteCommand(
            long actorId,
            Operation operation,
            String idempotencyKey,
            byte[] requestSha256,
            int responseStatus,
            String responseBodyJson
    ) {
        public CompleteCommand {
            requireActor(actorId);
            operation = Objects.requireNonNull(operation, "operation");
            idempotencyKey = requireKey(idempotencyKey);
            requestSha256 = requireDigest(requestSha256);
            if (responseStatus < 200 || responseStatus > 599) {
                throw new IllegalArgumentException("responseStatus must be between 200 and 599");
            }
            responseBodyJson = Objects.requireNonNull(responseBodyJson, "responseBodyJson");
            if (responseBodyJson.isBlank()) {
                throw new IllegalArgumentException("responseBodyJson must not be blank");
            }
        }

        @Override
        public byte[] requestSha256() {
            return Arrays.copyOf(requestSha256, requestSha256.length);
        }

        @Override
        public String toString() {
            return "CompleteCommand[actorId=" + actorId
                    + ", operation=" + operation
                    + ", idempotencyKey=<redacted>, requestSha256=<redacted>"
                    + ", responseStatus=" + responseStatus
                    + ", responseBodyJson=<redacted>]";
        }
    }

    record StoredResponse(int status, String bodyJson) {
        public StoredResponse {
            if (status < 200 || status > 599) {
                throw new IllegalArgumentException("status must be between 200 and 599");
            }
            bodyJson = Objects.requireNonNull(bodyJson, "bodyJson");
            if (bodyJson.isBlank()) {
                throw new IllegalArgumentException("bodyJson must not be blank");
            }
        }
    }

    record BeginResult(BeginOutcome outcome, Optional<StoredResponse> replay) {
        public BeginResult {
            outcome = Objects.requireNonNull(outcome, "outcome");
            replay = Objects.requireNonNull(replay, "replay");
            if ((outcome == BeginOutcome.REPLAY) != replay.isPresent()) {
                throw new IllegalArgumentException(
                        "Only a replay outcome may carry a stored response");
            }
        }

        public static BeginResult acquired() {
            return new BeginResult(BeginOutcome.ACQUIRED, Optional.empty());
        }

        public static BeginResult replay(StoredResponse response) {
            return new BeginResult(BeginOutcome.REPLAY, Optional.of(response));
        }

        public static BeginResult conflict() {
            return new BeginResult(BeginOutcome.CONFLICT, Optional.empty());
        }

        public static BeginResult inProgress() {
            return new BeginResult(BeginOutcome.IN_PROGRESS, Optional.empty());
        }
    }

    private static void requireActor(long actorId) {
        if (actorId <= 0) {
            throw new IllegalArgumentException("actorId must be positive");
        }
    }

    private static String requireKey(String key) {
        Objects.requireNonNull(key, "idempotencyKey");
        int length = key.getBytes(StandardCharsets.UTF_8).length;
        if (key.isBlank() || length > 255) {
            throw new IllegalArgumentException(
                    "idempotencyKey must contain between 1 and 255 UTF-8 bytes");
        }
        return key;
    }

    private static byte[] requireDigest(byte[] digest) {
        Objects.requireNonNull(digest, "requestSha256");
        if (digest.length != 32) {
            throw new IllegalArgumentException("requestSha256 must contain exactly 32 bytes");
        }
        return Arrays.copyOf(digest, digest.length);
    }
}
