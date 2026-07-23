package io.saksk.ti.learning.application;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

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
