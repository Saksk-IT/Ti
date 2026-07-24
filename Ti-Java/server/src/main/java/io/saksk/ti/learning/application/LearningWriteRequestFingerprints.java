package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.StudyReviewRating;
import io.saksk.ti.learning.api.StudyScopeInput;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;

final class LearningWriteRequestFingerprints {

    private LearningWriteRequestFingerprints() {
    }

    static byte[] favorite(long actorId, long questionId) {
        MessageDigest digest = sha256();
        frame(digest, "ti-java:learning-write-request:v1");
        frame(digest, "POST");
        frame(digest, "favorite");
        frame(digest, Long.toString(actorId));
        frame(digest, "[]");
        frame(digest, "{\"question_id\":" + questionId + "}");
        return digest.digest();
    }

    static byte[] recordResult(
            long actorId,
            long questionId,
            boolean correct,
            boolean clearMistakeOnCorrect
    ) {
        MessageDigest digest = sha256();
        frame(digest, "ti-java:learning-write-request:v1");
        frame(digest, "POST");
        frame(digest, "record-result");
        frame(digest, Long.toString(actorId));
        frame(digest, "[]");
        frame(
                digest,
                "{\"clear_mistake_on_correct\":" + clearMistakeOnCorrect
                        + ",\"is_correct\":" + correct
                        + ",\"question_id\":" + questionId + "}");
        return digest.digest();
    }

    static byte[] studyLearn(
            long actorId,
            long questionId,
            boolean correct,
            StudyScopeInput scope
    ) {
        return study(
                "study-learn",
                actorId,
                questionId,
                scope,
                "\"is_correct\":" + correct);
    }

    static byte[] studyReview(
            long actorId,
            long questionId,
            StudyReviewRating rating,
            StudyScopeInput scope
    ) {
        return study(
                "study-review-record",
                actorId,
                questionId,
                scope,
                "\"rating\":" + jsonString(rating.wireValue()));
    }

    static byte[] studyReviewMaster(
            long actorId,
            long questionId,
            boolean mastered,
            StudyScopeInput scope
    ) {
        return study(
                "study-review-master",
                actorId,
                questionId,
                scope,
                "\"is_mastered\":" + mastered);
    }

    static byte[] checkin(long actorId, LocalDate beijingDate) {
        MessageDigest digest = sha256();
        frame(digest, "ti-java:learning-write-request:v1");
        frame(digest, "POST");
        frame(digest, "checkin");
        frame(digest, Long.toString(actorId));
        frame(digest, "[]");
        frame(
                digest,
                "{\"beijing_date\":" + jsonString(beijingDate.toString()) + "}");
        return digest.digest();
    }

    private static byte[] study(
            String operation,
            long actorId,
            long questionId,
            StudyScopeInput scope,
            String operationField
    ) {
        MessageDigest digest = sha256();
        frame(digest, "ti-java:learning-write-request:v1");
        frame(digest, "POST");
        frame(digest, operation);
        frame(digest, Long.toString(actorId));
        frame(digest, "[]");
        String body = "{\"bank_id\":"
                + scope.bankId().map(String::valueOf).orElse("null")
                + "," + operationField
                + ",\"question_id\":" + questionId
                + ",\"source\":" + jsonString(scope.source())
                + ",\"subject\":"
                + scope.subject().map(LearningWriteRequestFingerprints::jsonString)
                        .orElse("null")
                + "}";
        frame(digest, body);
        return digest.digest();
    }

    private static String jsonString(String value) {
        StringBuilder escaped = new StringBuilder(value.length() + 2).append('"');
        value.codePoints().forEach(codePoint -> {
            switch (codePoint) {
                case '"' -> escaped.append("\\\"");
                case '\\' -> escaped.append("\\\\");
                case '\b' -> escaped.append("\\b");
                case '\f' -> escaped.append("\\f");
                case '\n' -> escaped.append("\\n");
                case '\r' -> escaped.append("\\r");
                case '\t' -> escaped.append("\\t");
                default -> {
                    if (codePoint < 0x20) {
                        escaped.append(String.format("\\u%04x", codePoint));
                    } else {
                        escaped.appendCodePoint(codePoint);
                    }
                }
            }
        });
        return escaped.append('"').toString();
    }

    private static MessageDigest sha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable", exception);
        }
    }

    private static void frame(MessageDigest digest, String value) {
        byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
        digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(bytes.length).array());
        digest.update(bytes);
    }
}
