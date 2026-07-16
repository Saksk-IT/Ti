package io.saksk.ti.identity.infrastructure.security;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.Optional;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

final class LegacyCryptoSupport {
    private LegacyCryptoSupport() {
    }

    static byte[] hmac(String algorithm, byte[] key, byte[] value) {
        try {
            Mac mac = Mac.getInstance(algorithm);
            mac.init(new SecretKeySpec(key, algorithm));
            return mac.doFinal(value);
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("required JCA algorithm is unavailable", exception);
        }
    }

    static Optional<byte[]> decodeBase64Url(String encoded, int maximumDecodedBytes) {
        if (encoded == null || encoded.isEmpty() || encoded.indexOf('=') >= 0 || encoded.length() % 4 == 1) {
            return Optional.empty();
        }
        for (int index = 0; index < encoded.length(); index++) {
            char value = encoded.charAt(index);
            if (!(value >= 'A' && value <= 'Z')
                    && !(value >= 'a' && value <= 'z')
                    && !(value >= '0' && value <= '9')
                    && value != '-'
                    && value != '_') {
                return Optional.empty();
            }
        }

        try {
            byte[] decoded = Base64.getUrlDecoder().decode(padBase64(encoded));
            if (decoded.length > maximumDecodedBytes
                    || !Base64.getUrlEncoder().withoutPadding().encodeToString(decoded).equals(encoded)) {
                return Optional.empty();
            }
            return Optional.of(decoded);
        } catch (IllegalArgumentException exception) {
            return Optional.empty();
        }
    }

    static boolean constantTimeEquals(byte[] left, byte[] right) {
        return MessageDigest.isEqual(left, right);
    }

    static boolean hasControlCharacter(String value) {
        return value.codePoints().anyMatch(Character::isISOControl);
    }

    static byte[] ascii(String value) {
        return value.getBytes(StandardCharsets.US_ASCII);
    }

    private static String padBase64(String value) {
        return switch (value.length() % 4) {
            case 0 -> value;
            case 2 -> value + "==";
            case 3 -> value + "=";
            default -> throw new IllegalArgumentException("invalid base64url length");
        };
    }
}
