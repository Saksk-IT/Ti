package io.saksk.ti.learning.application.port;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Optional;
import org.junit.jupiter.api.Test;

class LearningWriteReceiptPortTest {

    @Test
    void commandsDefensivelyCopyDigestsAndRedactSensitiveValues() {
        byte[] digest = digest(7);
        LearningWriteReceiptPort.BeginCommand begin =
                new LearningWriteReceiptPort.BeginCommand(
                        41L,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        "raw-secret-idempotency-key",
                        digest);
        digest[0] = 99;
        byte[] returned = begin.requestSha256();
        returned[1] = 98;

        assertThat(begin.requestSha256()).containsExactly(digest(7));
        assertThat(begin.toString())
                .doesNotContain("raw-secret-idempotency-key")
                .doesNotContain("[7");

        LearningWriteReceiptPort.CompleteCommand complete =
                new LearningWriteReceiptPort.CompleteCommand(
                        41L,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        "raw-secret-idempotency-key",
                        digest(8),
                        200,
                        "{\"private\":\"response\"}");
        assertThat(complete.toString())
                .doesNotContain("raw-secret-idempotency-key")
                .doesNotContain("private");
    }

    @Test
    void rejectsInvalidActorsKeysDigestsResponsesAndReplayShapes() {
        assertThatThrownBy(() -> new LearningWriteReceiptPort.BeginCommand(
                        0,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        "key",
                        digest(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteReceiptPort.BeginCommand(
                        1,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        " ",
                        digest(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteReceiptPort.BeginCommand(
                        1,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        "界".repeat(86),
                        digest(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteReceiptPort.BeginCommand(
                        1,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        "key",
                        new byte[31]))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteReceiptPort.CompleteCommand(
                        1,
                        LearningWriteReceiptPort.Operation.FAVORITE,
                        "key",
                        digest(1),
                        199,
                        "{}"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new LearningWriteReceiptPort.BeginResult(
                        LearningWriteReceiptPort.BeginOutcome.ACQUIRED,
                        Optional.of(new LearningWriteReceiptPort.StoredResponse(200, "{}"))))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static byte[] digest(int firstByte) {
        byte[] digest = new byte[32];
        digest[0] = (byte) firstByte;
        return digest;
    }
}
