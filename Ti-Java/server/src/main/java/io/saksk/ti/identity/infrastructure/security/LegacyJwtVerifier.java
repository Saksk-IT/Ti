package io.saksk.ti.identity.infrastructure.security;

import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

/** Strict, local-only verifier for the legacy PyJWT HS256 format. */
public final class LegacyJwtVerifier {
    static final int MAXIMUM_TOKEN_BYTES = 4096;
    static final Duration CLOCK_SKEW = Duration.ofSeconds(60);
    static final Duration MAXIMUM_LIFETIME = Duration.ofDays(15);

    private static final Set<String> HEADER_WITH_TYPE = Set.of("alg", "typ");
    private static final Set<String> HEADER_WITHOUT_TYPE = Set.of("alg");
    private static final Set<String> REQUIRED_CLAIMS =
            Set.of("user_id", "openid", "session_version", "exp", "iat", "jti");
    private static final long MAXIMUM_NUMERIC_DATE = 253_402_300_799L;

    private final byte[] secret;
    private final Clock clock;
    private final Duration clockSkew;
    private final Duration maximumLifetime;

    public LegacyJwtVerifier(byte[] secret, Clock clock) {
        this(secret, clock, CLOCK_SKEW, MAXIMUM_LIFETIME);
    }

    LegacyJwtVerifier(byte[] secret, Clock clock, Duration clockSkew, Duration maximumLifetime) {
        if (secret == null || secret.length < 16 || secret.length > 4096) {
            throw new IllegalArgumentException("legacy JWT secret has an invalid length");
        }
        if (clock == null
                || clockSkew == null
                || clockSkew.isNegative()
                || clockSkew.compareTo(Duration.ofMinutes(5)) > 0
                || maximumLifetime == null
                || maximumLifetime.isZero()
                || maximumLifetime.isNegative()
                || maximumLifetime.compareTo(Duration.ofDays(15)) > 0) {
            throw new IllegalArgumentException("legacy JWT verification policy is invalid");
        }
        this.secret = Arrays.copyOf(secret, secret.length);
        this.clock = clock;
        this.clockSkew = clockSkew;
        this.maximumLifetime = maximumLifetime;
    }

    /**
     * Returns only identity-shaped legacy data; every malformed, ambiguous or unauthorized shape
     * fails closed as an empty result.
     */
    public Optional<LegacyJwtIdentity> verify(String token) {
        try {
            return verifyStrict(token);
        } catch (RuntimeException exception) {
            return Optional.empty();
        }
    }

    private Optional<LegacyJwtIdentity> verifyStrict(String token) {
        if (token == null
                || token.isEmpty()
                || token.length() > MAXIMUM_TOKEN_BYTES
                || token.getBytes(StandardCharsets.UTF_8).length > MAXIMUM_TOKEN_BYTES) {
            return Optional.empty();
        }

        int firstSeparator = token.indexOf('.');
        int secondSeparator = firstSeparator < 0 ? -1 : token.indexOf('.', firstSeparator + 1);
        if (firstSeparator <= 0
                || secondSeparator <= firstSeparator + 1
                || secondSeparator >= token.length() - 1
                || token.indexOf('.', secondSeparator + 1) >= 0) {
            return Optional.empty();
        }

        String encodedHeader = token.substring(0, firstSeparator);
        String encodedPayload = token.substring(firstSeparator + 1, secondSeparator);
        String encodedSignature = token.substring(secondSeparator + 1);
        Optional<byte[]> headerBytes = LegacyCryptoSupport.decodeBase64Url(encodedHeader, 512);
        Optional<byte[]> payloadBytes = LegacyCryptoSupport.decodeBase64Url(encodedPayload, 2048);
        Optional<byte[]> suppliedSignature = LegacyCryptoSupport.decodeBase64Url(encodedSignature, 32);
        if (headerBytes.isEmpty()
                || payloadBytes.isEmpty()
                || suppliedSignature.isEmpty()
                || suppliedSignature.orElseThrow().length != 32) {
            return Optional.empty();
        }

        byte[] expectedSignature = LegacyCryptoSupport.hmac(
                "HmacSHA256",
                secret,
                LegacyCryptoSupport.ascii(token.substring(0, secondSeparator)));
        if (!LegacyCryptoSupport.constantTimeEquals(expectedSignature, suppliedSignature.orElseThrow())) {
            return Optional.empty();
        }

        Map<String, Object> header =
                StrictLegacyJson.parseFlatObject(headerBytes.orElseThrow(), 512, 2, 64);
        if ((!header.keySet().equals(HEADER_WITH_TYPE)
                        && !header.keySet().equals(HEADER_WITHOUT_TYPE))
                || !"HS256".equals(header.get("alg"))
                || header.containsKey("typ") && !"JWT".equals(header.get("typ"))) {
            return Optional.empty();
        }

        Map<String, Object> claims =
                StrictLegacyJson.parseFlatObject(payloadBytes.orElseThrow(), 2048, 6, 512);
        if (!claims.keySet().equals(REQUIRED_CLAIMS)) {
            // Unknown keys include every possible legacy role spelling and are never accepted.
            return Optional.empty();
        }

        Optional<Long> userId = boundedInteger(claims.get("user_id"), 1, Long.MAX_VALUE);
        Optional<Long> sessionVersion =
                boundedInteger(claims.get("session_version"), 0, Integer.MAX_VALUE);
        Optional<Long> expiration = boundedInteger(claims.get("exp"), 0, MAXIMUM_NUMERIC_DATE);
        Optional<Long> issuedAt = boundedInteger(claims.get("iat"), 0, MAXIMUM_NUMERIC_DATE);
        if (userId.isEmpty() || sessionVersion.isEmpty() || expiration.isEmpty() || issuedAt.isEmpty()) {
            return Optional.empty();
        }

        // Empty is an observed legacy value for non-WeChat bearer tokens. Presence and type are
        // still mandatory; the caller must resolve the authoritative binding from PostgreSQL.
        if (!(claims.get("openid") instanceof String openid)
                || openid.length() > 128
                || openid.getBytes(StandardCharsets.UTF_8).length > 256
                || LegacyCryptoSupport.hasControlCharacter(openid)) {
            return Optional.empty();
        }
        if (!(claims.get("jti") instanceof String jti) || !isLegacyJti(jti)) {
            return Optional.empty();
        }

        long exp = expiration.orElseThrow();
        long iat = issuedAt.orElseThrow();
        long now = clock.instant().getEpochSecond();
        long skew = clockSkew.toSeconds();
        if (exp <= subtractSaturated(now, skew)
                || iat > addSaturated(now, skew)
                || exp <= iat
                || exp - iat > maximumLifetime.toSeconds()) {
            return Optional.empty();
        }

        return Optional.of(new LegacyJwtIdentity(
                userId.orElseThrow(),
                openid,
                sessionVersion.orElseThrow().intValue(),
                Instant.ofEpochSecond(exp),
                Instant.ofEpochSecond(iat),
                jti));
    }

    private static Optional<Long> boundedInteger(Object value, long minimum, long maximum) {
        if (!(value instanceof Long parsed) || parsed < minimum || parsed > maximum) {
            return Optional.empty();
        }
        return Optional.of(parsed);
    }

    private static boolean isLegacyJti(String value) {
        if (value.length() != 32) {
            return false;
        }
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            if (!(character >= '0' && character <= '9')
                    && !(character >= 'a' && character <= 'f')) {
                return false;
            }
        }
        return true;
    }

    private static long addSaturated(long left, long right) {
        if (right > 0 && left > Long.MAX_VALUE - right) {
            return Long.MAX_VALUE;
        }
        return left + right;
    }

    private static long subtractSaturated(long left, long right) {
        if (right > 0 && left < Long.MIN_VALUE + right) {
            return Long.MIN_VALUE;
        }
        return left - right;
    }
}
