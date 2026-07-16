package io.saksk.ti.identity.infrastructure.security;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import org.bouncycastle.crypto.digests.SHA256Digest;
import org.bouncycastle.crypto.generators.PKCS5S2ParametersGenerator;
import org.bouncycastle.crypto.generators.SCrypt;
import org.bouncycastle.crypto.params.KeyParameter;

/**
 * Fail-closed verifier for observed Werkzeug password-hash strings.
 *
 * <p>It accepts the current exact scrypt parameters and bounded historical PBKDF2-SHA256
 * parameters only. Successful callers still need to upgrade the stored hash transactionally.</p>
 */
public final class WerkzeugPasswordVerifier {
    static final int MINIMUM_PBKDF2_ITERATIONS = 50_000;
    static final int MAXIMUM_PBKDF2_ITERATIONS = 1_000_000;
    static final int MAXIMUM_PASSWORD_CHARACTERS = PasswordInputLimits.MAXIMUM_CHARACTERS;
    static final int MAXIMUM_PASSWORD_BYTES = PasswordInputLimits.MAXIMUM_UTF8_BYTES;
    static final int MAXIMUM_STORED_HASH_CHARACTERS = 256;

    private static final String SCRYPT_METHOD = "scrypt:32768:8:1";
    private static final String PBKDF2_PREFIX = "pbkdf2:sha256:";
    private final PasswordKdfBudget kdfBudget;

    public WerkzeugPasswordVerifier() {
        this(PasswordKdfBudget.processWide());
    }

    WerkzeugPasswordVerifier(PasswordKdfBudget kdfBudget) {
        this.kdfBudget = java.util.Objects.requireNonNull(kdfBudget, "kdfBudget");
    }

    /** Verifies without ever including the password or encoded hash in an exception or log. */
    public boolean verify(char[] password, String storedHash) {
        return verify(password, storedHash, false);
    }

    boolean verifyOrThrowOnCapacity(char[] password, String storedHash) {
        return verify(password, storedHash, true);
    }

    static boolean isExactScryptHash(String storedHash) {
        if (storedHash == null || storedHash.length() > MAXIMUM_STORED_HASH_CHARACTERS) {
            return false;
        }
        ParsedHash parsed = parse(storedHash);
        if (parsed == null) {
            return false;
        }
        try {
            return parsed.kind() == HashKind.SCRYPT;
        } finally {
            Arrays.fill(parsed.expected(), (byte) 0);
        }
    }

    private boolean verify(char[] password, String storedHash, boolean throwOnCapacity) {
        if (password == null
                || password.length > MAXIMUM_PASSWORD_CHARACTERS
                || storedHash == null
                || storedHash.isEmpty()
                || storedHash.length() > MAXIMUM_STORED_HASH_CHARACTERS) {
            return false;
        }

        try {
            ParsedHash parsed = parse(storedHash);
            if (parsed == null) {
                return false;
            }

            byte[] passwordBytes = PasswordInputLimits.encodeUtf8(password);
            if (passwordBytes == null) {
                Arrays.fill(parsed.expected(), (byte) 0);
                return false;
            }
            byte[] saltBytes = parsed.salt().getBytes(StandardCharsets.US_ASCII);
            try {
                java.util.function.BooleanSupplier operation = () -> {
                    byte[] calculated = null;
                    try {
                        calculated = switch (parsed.kind()) {
                            case SCRYPT ->
                                SCrypt.generate(passwordBytes, saltBytes, 32_768, 8, 1, 64);
                            case PBKDF2 ->
                                pbkdf2HmacSha256(passwordBytes, saltBytes, parsed.iterations());
                        };
                        return LegacyCryptoSupport.constantTimeEquals(
                                calculated, parsed.expected());
                    } finally {
                        if (calculated != null) {
                            Arrays.fill(calculated, (byte) 0);
                        }
                    }
                };
                return throwOnCapacity
                        ? kdfBudget.callOrThrow(operation::getAsBoolean)
                        : kdfBudget.tryRun(operation);
            } finally {
                Arrays.fill(passwordBytes, (byte) 0);
                Arrays.fill(saltBytes, (byte) 0);
                Arrays.fill(parsed.expected(), (byte) 0);
            }
        } catch (PasswordKdfBudget.PasswordKdfCapacityException exception) {
            if (throwOnCapacity) {
                throw exception;
            }
            return false;
        } catch (RuntimeException exception) {
            return false;
        }
    }

    private static ParsedHash parse(String storedHash) {
        int firstSeparator = storedHash.indexOf('$');
        int secondSeparator = firstSeparator < 0 ? -1 : storedHash.indexOf('$', firstSeparator + 1);
        if (firstSeparator <= 0
                || secondSeparator <= firstSeparator + 1
                || secondSeparator >= storedHash.length() - 1
                || storedHash.indexOf('$', secondSeparator + 1) >= 0) {
            return null;
        }

        String method = storedHash.substring(0, firstSeparator);
        String salt = storedHash.substring(firstSeparator + 1, secondSeparator);
        if (!validWerkzeugSalt(salt)) {
            return null;
        }

        HashKind kind;
        int iterations;
        int expectedBytes;
        if (SCRYPT_METHOD.equals(method)) {
            kind = HashKind.SCRYPT;
            iterations = 0;
            expectedBytes = 64;
        } else if (method.startsWith(PBKDF2_PREFIX)) {
            String encodedIterations = method.substring(PBKDF2_PREFIX.length());
            if (!canonicalPositiveInteger(encodedIterations)) {
                return null;
            }
            try {
                iterations = Integer.parseInt(encodedIterations);
            } catch (NumberFormatException exception) {
                return null;
            }
            if (iterations < MINIMUM_PBKDF2_ITERATIONS
                    || iterations > MAXIMUM_PBKDF2_ITERATIONS) {
                return null;
            }
            kind = HashKind.PBKDF2;
            expectedBytes = 32;
        } else {
            return null;
        }

        byte[] expected = decodeLowercaseHex(storedHash.substring(secondSeparator + 1), expectedBytes);
        return expected == null ? null : new ParsedHash(kind, salt, iterations, expected);
    }

    private static byte[] pbkdf2HmacSha256(byte[] password, byte[] salt, int iterations) {
        PKCS5S2ParametersGenerator generator =
                new PKCS5S2ParametersGenerator(new SHA256Digest());
        generator.init(password, salt, iterations);
        return ((KeyParameter) generator.generateDerivedParameters(256)).getKey();
    }

    private static boolean validWerkzeugSalt(String salt) {
        if (salt.isEmpty() || salt.length() > 64) {
            return false;
        }
        for (int index = 0; index < salt.length(); index++) {
            char value = salt.charAt(index);
            if (!(value >= 'A' && value <= 'Z')
                    && !(value >= 'a' && value <= 'z')
                    && !(value >= '0' && value <= '9')) {
                return false;
            }
        }
        return true;
    }

    private static boolean canonicalPositiveInteger(String value) {
        if (value.isEmpty() || value.length() > 10 || value.length() > 1 && value.charAt(0) == '0') {
            return false;
        }
        for (int index = 0; index < value.length(); index++) {
            if (value.charAt(index) < '0' || value.charAt(index) > '9') {
                return false;
            }
        }
        return !value.equals("0");
    }

    private static byte[] decodeLowercaseHex(String value, int expectedBytes) {
        if (value.length() != expectedBytes * 2) {
            return null;
        }
        byte[] decoded = new byte[expectedBytes];
        for (int index = 0; index < decoded.length; index++) {
            int high = lowercaseHexDigit(value.charAt(index * 2));
            int low = lowercaseHexDigit(value.charAt(index * 2 + 1));
            if (high < 0 || low < 0) {
                Arrays.fill(decoded, (byte) 0);
                return null;
            }
            decoded[index] = (byte) ((high << 4) | low);
        }
        return decoded;
    }

    private static int lowercaseHexDigit(char value) {
        if (value >= '0' && value <= '9') {
            return value - '0';
        }
        if (value >= 'a' && value <= 'f') {
            return value - 'a' + 10;
        }
        return -1;
    }

    private enum HashKind {
        SCRYPT,
        PBKDF2
    }

    private record ParsedHash(HashKind kind, String salt, int iterations, byte[] expected) {
    }
}
