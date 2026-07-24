package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionEditCommand;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Optional;

final class QuestionEditRequestFingerprint {

    private QuestionEditRequestFingerprint() {
    }

    static byte[] of(QuestionEditCommand command) {
        MessageDigest digest = sha256();
        frame(digest, "ti-java:catalog-question-edit-request:v1");
        frame(digest, "PUT");
        frame(digest, "question-edit");
        frame(digest, Long.toString(command.editor().identityId()));
        frame(digest, Long.toString(command.questionId()));
        frameOptional(digest, "content", command.content());
        frameOptional(digest, "questionType", command.questionType());
        frameOptional(digest, "answer", command.answer());
        frameOptional(digest, "explanation", command.explanation());
        frameOptional(digest, "optionsJsonOrText", command.optionsJsonOrText());
        return digest.digest();
    }

    private static void frameOptional(
            MessageDigest digest,
            String name,
            Optional<String> value
    ) {
        frame(digest, name);
        frame(digest, value.isPresent() ? "present" : "absent");
        value.ifPresent(item -> frame(digest, item));
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
