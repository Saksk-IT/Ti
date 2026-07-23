package io.saksk.ti.catalog.application.port;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Objects;
import java.util.Optional;

/**
 * Transaction-local idempotency receipt boundary for catalog-owned question edits.
 *
 * <p>The raw key is transient input only. Implementations must persist only a keyed digest and
 * must participate in the catalog question update transaction.
 */
public interface CatalogQuestionEditReceiptPort {

    BeginResult begin(BeginCommand command);

    StoredResponse complete(CompleteCommand command);

    enum BeginOutcome {
        ACQUIRED,
        REPLAY,
        CONFLICT,
        IN_PROGRESS
    }

    record BeginCommand(
            long actorId,
            long questionId,
            String idempotencyKey,
            byte[] requestSha256
    ) {
        public BeginCommand {
            requireIdentity(actorId, questionId);
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
                    + ", questionId=" + questionId
                    + ", idempotencyKey=<redacted>, requestSha256=<redacted>]";
        }
    }

    record CompleteCommand(
            long actorId,
            long questionId,
            String idempotencyKey,
            byte[] requestSha256,
            int responseStatus,
            String responseBodyJson
    ) {
        public CompleteCommand {
            requireIdentity(actorId, questionId);
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
                    + ", questionId=" + questionId
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

    private static void requireIdentity(long actorId, long questionId) {
        if (actorId <= 0) {
            throw new IllegalArgumentException("actorId must be positive");
        }
        if (questionId <= 0) {
            throw new IllegalArgumentException("questionId must be positive");
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
