package io.saksk.ti.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import java.util.zip.DeflaterOutputStream;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

class LegacyFlaskSessionVerifierTest {
    private static final byte[] PUBLIC_TEST_SECRET = LegacyAuthVectors.publicTestSecret();
    private static final long SIGNED_AT = LegacyAuthVectors.fixedTime();

    @Test
    void verifiesCompressedAndUncompressedFlaskCrossLanguageVectors() {
        JsonNode vectors = LegacyAuthVectors.root().path("flask_sessions");
        LegacyFlaskSessionVerifier verifier = verifierAt(SIGNED_AT + 3600);

        for (JsonNode vector : vectors) {
            LegacySessionIdentity identity =
                    verifier.verify(vector.path("cookie").asString()).orElseThrow();
            JsonNode expected = vector.path("identity");
            assertThat(identity.userId()).isEqualTo(expected.path("user_id").asLong());
            assertThat(identity.username()).isEqualTo(expected.path("username").asString());
            assertThat(identity.sessionVersion())
                    .isEqualTo(expected.path("session_version").asInt());
            assertThat(identity.signedAt()).isEqualTo(Instant.ofEpochSecond(SIGNED_AT));
            assertThat(vector.path("cookie").asString().startsWith("."))
                    .isEqualTo(vector.path("compressed").asBoolean());
        }
    }

    @Test
    void signedLegacyRoleValuesAreDiscardedAndCannotBecomeAuthorities() {
        JsonNode vector = LegacyAuthVectors.root().path("flask_sessions").get(1);
        LegacySessionIdentity identity =
                verifierAt(SIGNED_AT + 1).verify(vector.path("cookie").asString()).orElseThrow();

        assertThat(identity.userId()).isEqualTo(4242);
        assertThat(identity.toString())
                .doesNotContain(identity.username(), Long.toString(identity.userId()));
        assertThat(List.of(LegacySessionIdentity.class.getRecordComponents()).stream()
                        .map(component -> component.getName()))
                .containsExactly(
                        "userId", "username", "sessionVersion", "remember", "signedAt", "expiresAt")
                .doesNotContain("role", "roles", "isAdmin", "isSubjectAdmin", "isNotificationAdmin");
    }

    @Test
    void rejectsTamperingFutureTimeExpiryAndHonorsExactAgeBoundary() {
        String cookie = LegacyAuthVectors.root()
                .path("flask_sessions")
                .get(0)
                .path("cookie")
                .asString();

        assertThat(verifierAt(SIGNED_AT + 1).verify(cookie.substring(0, cookie.length() - 1) + "A"))
                .isEmpty();
        assertThat(verifierAt(SIGNED_AT - 1).verify(cookie)).isEmpty();
        assertThat(verifierAt(SIGNED_AT + 7 * 24 * 60 * 60).verify(cookie)).isPresent();
        assertThat(verifierAt(SIGNED_AT + 7 * 24 * 60 * 60 + 1).verify(cookie)).isEmpty();
    }

    @Test
    void rejectsDuplicateUnknownNestedTaggedAndWrongTypedValues() {
        LegacyFlaskSessionVerifier verifier = verifierAt(SIGNED_AT + 1);
        for (String invalidJson : List.of(
                "{\"user_id\":4242,\"user_id\":4243,\"username\":\"u\",\"session_version\":7}",
                "{\"user_id\":4242,\"username\":\"u\",\"session_version\":7,\"unknown\":true}",
                "{\"user_id\":{\" t\":[1,2]},\"username\":\"u\",\"session_version\":7}",
                "{\"user_id\":4242,\"username\":[\"u\"],\"session_version\":7}",
                "{\"user_id\":true,\"username\":\"u\",\"session_version\":7}",
                "{\"user_id\":4242,\"username\":\"u\",\"session_version\":-1}",
                "{\"user_id\":4242,\"username\":\"u\",\"session_version\":-0}",
                "{\"user_id\":4242,\"username\":\"\\u００４１\",\"session_version\":7}",
                "{\"user_id\":4242,\"username\":\"u\",\"session_version\":7,\"is_admin\":\"true\"}",
                "{\"user_id\":4242,\"username\":\"u\",\"session_version\":7,\"csrf_token\":null}")) {
            assertThat(verifier.verify(signedCookie(invalidJson, SIGNED_AT, false)))
                    .as("restricted JSON must fail closed")
                    .isEmpty();
        }
    }

    @Test
    void boundsCookieAndDecompressionAndRejectsTrailingCompressedData() {
        LegacyFlaskSessionVerifier verifier = verifierAt(SIGNED_AT + 1);
        String bombJson = "{\"user_id\":4242,\"username\":\""
                + "a".repeat(LegacyFlaskSessionVerifier.MAXIMUM_PAYLOAD_BYTES + 1000)
                + "\",\"session_version\":7}";
        String bomb = signedCookie(bombJson, SIGNED_AT, true);
        assertThat(bomb.length()).isLessThan(LegacyFlaskSessionVerifier.MAXIMUM_COOKIE_BYTES);
        assertThat(verifier.verify(bomb)).isEmpty();

        byte[] compressed = compress(
                "{\"user_id\":4242,\"username\":\"u\",\"session_version\":7}"
                        .getBytes(StandardCharsets.UTF_8));
        byte[] withTrailingData = Arrays.copyOf(compressed, compressed.length + 1);
        withTrailingData[withTrailingData.length - 1] = 1;
        assertThat(verifier.verify(signedCompressedBytes(withTrailingData, SIGNED_AT))).isEmpty();

        assertThat(verifier.verify("x".repeat(LegacyFlaskSessionVerifier.MAXIMUM_COOKIE_BYTES + 1)))
                .isEmpty();
        assertThat(verifier.verify(null)).isEmpty();
    }

    @Test
    void rejectsNonCanonicalTimestampAndBase64Forms() {
        LegacyFlaskSessionVerifier verifier = verifierAt(SIGNED_AT + 1);
        String payload = encode(
                "{\"user_id\":4242,\"username\":\"u\",\"session_version\":7}"
                        .getBytes(StandardCharsets.UTF_8));
        byte[] nineByteTimestamp = new byte[9];
        nineByteTimestamp[0] = 1;

        assertThat(verifier.verify(signEncoded(payload, "AA"))).isEmpty();
        assertThat(verifier.verify(signEncoded(payload, "AAE"))).isEmpty();
        assertThat(verifier.verify(signEncoded(payload, encode(nineByteTimestamp)))).isEmpty();
        assertThat(verifier.verify(signEncoded(
                        payload + "=", encode(minimalBigEndian(SIGNED_AT)))))
                .isEmpty();
    }

    private static LegacyFlaskSessionVerifier verifierAt(long epochSecond) {
        return new LegacyFlaskSessionVerifier(
                PUBLIC_TEST_SECRET,
                Clock.fixed(Instant.ofEpochSecond(epochSecond), ZoneOffset.UTC));
    }

    private static String signedCookie(String json, long timestamp, boolean compressed) {
        byte[] jsonBytes = json.getBytes(StandardCharsets.UTF_8);
        byte[] payloadBytes = compressed ? compress(jsonBytes) : jsonBytes;
        String payload = (compressed ? "." : "") + encode(payloadBytes);
        return signPayload(payload, timestamp);
    }

    private static String signedCompressedBytes(byte[] compressed, long timestamp) {
        return signPayload("." + encode(compressed), timestamp);
    }

    private static String signPayload(String payload, long timestamp) {
        String encodedTimestamp = encode(minimalBigEndian(timestamp));
        return signEncoded(payload, encodedTimestamp);
    }

    private static String signEncoded(String payload, String encodedTimestamp) {
        String unsigned = payload + "." + encodedTimestamp;
        byte[] derivedKey = hmac("HmacSHA1", PUBLIC_TEST_SECRET, "cookie-session".getBytes(StandardCharsets.UTF_8));
        byte[] signature = hmac("HmacSHA1", derivedKey, unsigned.getBytes(StandardCharsets.US_ASCII));
        Arrays.fill(derivedKey, (byte) 0);
        return unsigned + "." + encode(signature);
    }

    private static byte[] minimalBigEndian(long value) {
        byte[] full = ByteBuffer.allocate(Long.BYTES).putLong(value).array();
        int first = 0;
        while (first < full.length - 1 && full[first] == 0) {
            first++;
        }
        return Arrays.copyOfRange(full, first, full.length);
    }

    private static byte[] compress(byte[] value) {
        try {
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            try (DeflaterOutputStream deflater = new DeflaterOutputStream(output)) {
                deflater.write(value);
            }
            return output.toByteArray();
        } catch (IOException exception) {
            throw new AssertionError(exception);
        }
    }

    private static byte[] hmac(String algorithm, byte[] key, byte[] value) {
        try {
            Mac mac = Mac.getInstance(algorithm);
            mac.init(new SecretKeySpec(key, algorithm));
            return mac.doFinal(value);
        } catch (Exception exception) {
            throw new AssertionError(exception);
        }
    }

    private static String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }
}
