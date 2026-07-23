package io.saksk.ti.catalog.application.port;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class CatalogQuestionEditReceiptPortTest {

    @Test
    void commandOwnsItsDigestAndRedactsKeyAndResponse() {
        byte[] digest = digest(3);
        CatalogQuestionEditReceiptPort.BeginCommand begin =
                new CatalogQuestionEditReceiptPort.BeginCommand(
                        51L, 61L, "catalog-raw-key", digest);
        digest[0] = 100;
        byte[] returned = begin.requestSha256();
        returned[0] = 99;

        assertThat(begin.requestSha256()).containsExactly(digest(3));
        assertThat(begin.toString()).doesNotContain("catalog-raw-key");

        CatalogQuestionEditReceiptPort.CompleteCommand complete =
                new CatalogQuestionEditReceiptPort.CompleteCommand(
                        51L,
                        61L,
                        "catalog-raw-key",
                        digest(4),
                        200,
                        "{\"answer\":\"sensitive\"}");
        assertThat(complete.toString())
                .doesNotContain("catalog-raw-key")
                .doesNotContain("sensitive");
    }

    @Test
    void rejectsInvalidIdentityKeyDigestAndResponse() {
        assertThatThrownBy(() -> new CatalogQuestionEditReceiptPort.BeginCommand(
                        0, 1, "key", digest(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CatalogQuestionEditReceiptPort.BeginCommand(
                        1, 0, "key", digest(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CatalogQuestionEditReceiptPort.BeginCommand(
                        1, 1, "", digest(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CatalogQuestionEditReceiptPort.BeginCommand(
                        1, 1, "key", new byte[33]))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CatalogQuestionEditReceiptPort.CompleteCommand(
                        1, 1, "key", digest(1), 600, "{}"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private static byte[] digest(int firstByte) {
        byte[] digest = new byte[32];
        digest[0] = (byte) firstByte;
        return digest;
    }
}
