package io.saksk.ti.identity.infrastructure.security;

import io.saksk.ti.identity.application.port.PasswordHashPort;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.Objects;
import org.bouncycastle.crypto.generators.SCrypt;
import org.springframework.stereotype.Component;

/**
 * Transition-safe password adapter.
 *
 * <p>The target remains Werkzeug's exact scrypt format while Flask rollback is supported. A
 * Spring-only encoding may be introduced only after the old runtime has permanently exited.</p>
 */
@Component
class TransitionalPasswordHashAdapter implements PasswordHashPort {

    static final String TARGET_METHOD = "scrypt:32768:8:1";
    static final String TARGET_PREFIX = TARGET_METHOD + "$";
    static final String PUBLIC_TEST_ONLY_DUMMY_HASH = TARGET_PREFIX
            + "PublicSalt123456$"
            + "1cfde846b842e31ba36d7c9a7f55beb23395332274230dae40c8d89d7660651d"
            + "a42fff3d8b5918d898465e477379787c9523da58e804edb352688c0af428bb9c";

    private static final char[] SALT_ALPHABET =
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789".toCharArray();
    private static final int TARGET_SALT_CHARACTERS = 16;
    private static final int TARGET_HASH_BYTES = 64;

    private final PasswordKdfBudget kdfBudget;
    private final WerkzeugPasswordVerifier werkzeug;
    private final SecureRandom secureRandom;

    TransitionalPasswordHashAdapter() {
        this(PasswordKdfBudget.processWide(), new SecureRandom());
    }

    TransitionalPasswordHashAdapter(PasswordKdfBudget kdfBudget, SecureRandom secureRandom) {
        this.kdfBudget = Objects.requireNonNull(kdfBudget, "kdfBudget");
        this.werkzeug = new WerkzeugPasswordVerifier(kdfBudget);
        this.secureRandom = Objects.requireNonNull(secureRandom, "secureRandom");
    }

    @Override
    public boolean matches(char[] password, String storedHash) {
        if (looksLikeSupportedWerkzeugHash(storedHash)) {
            return werkzeug.verifyOrThrowOnCapacity(password, storedHash);
        }
        performDummyVerification(password);
        return false;
    }

    @Override
    public boolean isTargetHash(String storedHash) {
        return WerkzeugPasswordVerifier.isExactScryptHash(storedHash);
    }

    @Override
    public String encodeTarget(char[] password) {
        byte[] passwordBytes = requirePasswordBytes(password);
        char[] saltCharacters = new char[TARGET_SALT_CHARACTERS];
        for (int index = 0; index < saltCharacters.length; index++) {
            saltCharacters[index] = SALT_ALPHABET[secureRandom.nextInt(SALT_ALPHABET.length)];
        }
        byte[] saltBytes = new String(saltCharacters).getBytes(StandardCharsets.US_ASCII);
        try {
            return kdfBudget.callOrThrow(() -> encodeWithinBudget(passwordBytes, saltCharacters, saltBytes));
        } finally {
            Arrays.fill(passwordBytes, (byte) 0);
            Arrays.fill(saltCharacters, '\0');
            Arrays.fill(saltBytes, (byte) 0);
        }
    }

    @Override
    public void performDummyVerification(char[] password) {
        werkzeug.verifyOrThrowOnCapacity(password, PUBLIC_TEST_ONLY_DUMMY_HASH);
    }

    private static String encodeWithinBudget(
            byte[] passwordBytes,
            char[] saltCharacters,
            byte[] saltBytes
    ) {
        byte[] derived = null;
        try {
            derived = SCrypt.generate(passwordBytes, saltBytes, 32_768, 8, 1, TARGET_HASH_BYTES);
            return TARGET_PREFIX + new String(saltCharacters) + "$"
                    + HexFormat.of().formatHex(derived);
        } finally {
            if (derived != null) {
                Arrays.fill(derived, (byte) 0);
            }
        }
    }

    private static byte[] requirePasswordBytes(char[] password) {
        byte[] encoded = PasswordInputLimits.encodeUtf8(password);
        if (encoded == null) {
            throw new IllegalArgumentException("password input is invalid");
        }
        return encoded;
    }

    private static boolean looksLikeSupportedWerkzeugHash(String storedHash) {
        return storedHash != null
                && (storedHash.startsWith("scrypt:") || storedHash.startsWith("pbkdf2:sha256:"));
    }
}
