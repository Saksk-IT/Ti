package io.saksk.ti.identity.infrastructure.security;

import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.zip.DataFormatException;
import java.util.zip.Inflater;

/**
 * Restricted verifier for Flask 3.1 / itsdangerous 2.2 URL-safe timed cookie sessions.
 *
 * <p>SHA-1 is accepted only inside this legacy HMAC compatibility boundary. It is not exposed as
 * a general signing option and must not be used for any newly issued credential.</p>
 */
public final class LegacyFlaskSessionVerifier {
    static final int MAXIMUM_COOKIE_BYTES = 4096;
    static final int MAXIMUM_PAYLOAD_BYTES = 8192;
    static final Duration MAXIMUM_AGE = Duration.ofDays(7);

    private static final byte[] COOKIE_SESSION_SALT =
            "cookie-session".getBytes(StandardCharsets.UTF_8);
    private static final Set<String> ALLOWED_KEYS = Set.of(
            "_permanent",
            "user_id",
            "username",
            "is_admin",
            "is_subject_admin",
            "is_notification_admin",
            "session_version",
            "remember",
            "csrf_token");

    private final byte[] secret;
    private final Clock clock;
    private final Duration maximumAge;

    public LegacyFlaskSessionVerifier(byte[] secret, Clock clock) {
        this(secret, clock, MAXIMUM_AGE);
    }

    LegacyFlaskSessionVerifier(byte[] secret, Clock clock, Duration maximumAge) {
        if (secret == null || secret.length < 16 || secret.length > 4096) {
            throw new IllegalArgumentException("legacy Flask secret has an invalid length");
        }
        if (clock == null
                || maximumAge == null
                || maximumAge.isNegative()
                || maximumAge.isZero()
                || maximumAge.compareTo(Duration.ofDays(7)) > 0) {
            throw new IllegalArgumentException("legacy Flask session verification policy is invalid");
        }
        this.secret = Arrays.copyOf(secret, secret.length);
        this.clock = clock;
        this.maximumAge = maximumAge;
    }

    /** Verifies a legacy cookie without logging or returning role-shaped values. */
    public Optional<LegacySessionIdentity> verify(String cookie) {
        try {
            return verifyStrict(cookie);
        } catch (RuntimeException exception) {
            return Optional.empty();
        }
    }

    private Optional<LegacySessionIdentity> verifyStrict(String cookie) {
        if (cookie == null
                || cookie.isEmpty()
                || cookie.length() > MAXIMUM_COOKIE_BYTES
                || cookie.getBytes(StandardCharsets.UTF_8).length > MAXIMUM_COOKIE_BYTES) {
            return Optional.empty();
        }

        int signatureSeparator = cookie.lastIndexOf('.');
        int timestampSeparator = signatureSeparator < 0
                ? -1
                : cookie.lastIndexOf('.', signatureSeparator - 1);
        if (timestampSeparator < 0
                || signatureSeparator <= timestampSeparator + 1
                || signatureSeparator >= cookie.length() - 1) {
            return Optional.empty();
        }

        String payload = cookie.substring(0, timestampSeparator);
        String encodedTimestamp = cookie.substring(timestampSeparator + 1, signatureSeparator);
        String encodedSignature = cookie.substring(signatureSeparator + 1);
        if (payload.isEmpty() || payload.equals(".") || payload.substring(1).indexOf('.') >= 0) {
            return Optional.empty();
        }

        Optional<byte[]> suppliedSignature = LegacyCryptoSupport.decodeBase64Url(encodedSignature, 20);
        if (suppliedSignature.isEmpty() || suppliedSignature.orElseThrow().length != 20) {
            return Optional.empty();
        }

        byte[] derivedKey = LegacyCryptoSupport.hmac("HmacSHA1", secret, COOKIE_SESSION_SALT);
        byte[] expectedSignature = LegacyCryptoSupport.hmac(
                "HmacSHA1",
                derivedKey,
                LegacyCryptoSupport.ascii(cookie.substring(0, signatureSeparator)));
        Arrays.fill(derivedKey, (byte) 0);
        if (!LegacyCryptoSupport.constantTimeEquals(expectedSignature, suppliedSignature.orElseThrow())) {
            return Optional.empty();
        }

        Optional<byte[]> timestampBytes = LegacyCryptoSupport.decodeBase64Url(encodedTimestamp, 8);
        if (timestampBytes.isEmpty()) {
            return Optional.empty();
        }
        Optional<Long> signedAtValue = parseMinimalUnsignedLong(timestampBytes.orElseThrow());
        if (signedAtValue.isEmpty()) {
            return Optional.empty();
        }

        long signedAtSeconds = signedAtValue.orElseThrow();
        long nowSeconds = clock.instant().getEpochSecond();
        if (signedAtSeconds > nowSeconds
                || nowSeconds < 0
                || nowSeconds - signedAtSeconds > maximumAge.toSeconds()) {
            return Optional.empty();
        }

        boolean compressed = payload.startsWith(".");
        String encodedPayload = compressed ? payload.substring(1) : payload;
        Optional<byte[]> decodedPayload =
                LegacyCryptoSupport.decodeBase64Url(encodedPayload, MAXIMUM_PAYLOAD_BYTES);
        if (decodedPayload.isEmpty()) {
            return Optional.empty();
        }
        byte[] json = compressed
                ? decompressBounded(decodedPayload.orElseThrow(), MAXIMUM_PAYLOAD_BYTES)
                : decodedPayload.orElseThrow();

        Map<String, Object> values =
                StrictLegacyJson.parseFlatObject(json, MAXIMUM_PAYLOAD_BYTES, ALLOWED_KEYS.size(), 512);
        if (!ALLOWED_KEYS.containsAll(values.keySet())
                || !values.containsKey("user_id")
                || !values.containsKey("username")
                || !values.containsKey("session_version")
                || !optionalBooleansAreValid(values)
                || !optionalCsrfTokenIsValid(values)) {
            return Optional.empty();
        }

        Optional<Long> userId = boundedInteger(values.get("user_id"), 1, Long.MAX_VALUE);
        Optional<Long> sessionVersion =
                boundedInteger(values.get("session_version"), 0, Integer.MAX_VALUE);
        if (userId.isEmpty() || sessionVersion.isEmpty()) {
            return Optional.empty();
        }
        if (!(values.get("username") instanceof String username)
                || username.isBlank()
                || username.length() > 128
                || username.getBytes(StandardCharsets.UTF_8).length > 256
                || LegacyCryptoSupport.hasControlCharacter(username)) {
            return Optional.empty();
        }

        Instant signedAt = Instant.ofEpochSecond(signedAtSeconds);
        boolean remember = Boolean.TRUE.equals(values.get("_permanent"))
                || Boolean.TRUE.equals(values.get("remember"));
        return Optional.of(new LegacySessionIdentity(
                userId.orElseThrow(),
                username,
                sessionVersion.orElseThrow().intValue(),
                remember,
                signedAt,
                signedAt.plus(maximumAge)));
    }

    private static Optional<Long> parseMinimalUnsignedLong(byte[] value) {
        if (value.length == 0
                || value.length > 8
                || value.length > 1 && value[0] == 0
                || value.length == 8 && value[0] < 0) {
            return Optional.empty();
        }
        long parsed = 0;
        for (byte current : value) {
            parsed = (parsed << 8) | (current & 0xffL);
        }
        return parsed > 0 ? Optional.of(parsed) : Optional.empty();
    }

    private static byte[] decompressBounded(byte[] compressed, int maximumOutputBytes) {
        Inflater inflater = new Inflater();
        inflater.setInput(compressed);
        byte[] result = new byte[maximumOutputBytes + 1];
        int total = 0;
        try {
            while (!inflater.finished()) {
                int count = inflater.inflate(result, total, result.length - total);
                total += count;
                if (total > maximumOutputBytes) {
                    throw new IllegalArgumentException("legacy session payload exceeds its limit");
                }
                if (count == 0) {
                    if (inflater.needsDictionary() || inflater.needsInput()) {
                        throw new IllegalArgumentException("invalid legacy session compression");
                    }
                    throw new IllegalArgumentException("stalled legacy session decompression");
                }
            }
            if (inflater.getRemaining() != 0) {
                throw new IllegalArgumentException("trailing legacy session compression data");
            }
            return Arrays.copyOf(result, total);
        } catch (DataFormatException exception) {
            throw new IllegalArgumentException("invalid legacy session compression", exception);
        } finally {
            inflater.end();
        }
    }

    private static boolean optionalBooleansAreValid(Map<String, Object> values) {
        for (String key : Set.of(
                "_permanent", "remember", "is_admin", "is_subject_admin", "is_notification_admin")) {
            if (values.containsKey(key) && !(values.get(key) instanceof Boolean)) {
                return false;
            }
        }
        return true;
    }

    private static boolean optionalCsrfTokenIsValid(Map<String, Object> values) {
        if (!values.containsKey("csrf_token")) {
            return true;
        }
        return values.get("csrf_token") instanceof String csrfToken
                && !csrfToken.isEmpty()
                && csrfToken.length() <= 256
                && !LegacyCryptoSupport.hasControlCharacter(csrfToken);
    }

    private static Optional<Long> boundedInteger(Object value, long minimum, long maximum) {
        if (!(value instanceof Long parsed) || parsed < minimum || parsed > maximum) {
            return Optional.empty();
        }
        return Optional.of(parsed);
    }
}
