package io.saksk.ti.identity.infrastructure.security;

import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

final class PasswordInputLimits {
    static final int MAXIMUM_CHARACTERS = 1024;
    static final int MAXIMUM_UTF8_BYTES = 4096;

    private PasswordInputLimits() {
    }

    static byte[] encodeUtf8(char[] password) {
        if (password == null || password.length > MAXIMUM_CHARACTERS) {
            return null;
        }
        try {
            ByteBuffer encoded = StandardCharsets.UTF_8
                    .newEncoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .encode(CharBuffer.wrap(password));
            if (encoded.remaining() > MAXIMUM_UTF8_BYTES) {
                clearBackingArray(encoded);
                return null;
            }
            byte[] result = new byte[encoded.remaining()];
            encoded.get(result);
            clearBackingArray(encoded);
            return result;
        } catch (CharacterCodingException exception) {
            return null;
        }
    }

    private static void clearBackingArray(ByteBuffer buffer) {
        if (buffer.hasArray()) {
            Arrays.fill(buffer.array(), (byte) 0);
        }
    }
}
