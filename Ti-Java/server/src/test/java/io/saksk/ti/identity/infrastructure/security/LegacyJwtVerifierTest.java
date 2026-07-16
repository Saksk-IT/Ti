package io.saksk.ti.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Set;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

class LegacyJwtVerifierTest {
    private static final String PUBLIC_TEST_HEADER = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
    private static final byte[] PUBLIC_TEST_SECRET = LegacyAuthVectors.publicTestSecret();
    private static final long ISSUED_AT = LegacyAuthVectors.fixedTime();
    private static final long EXPIRES_AT = ISSUED_AT + 15 * 24 * 60 * 60;

    @Test
    void verifiesPyJwtCrossLanguageVectorWithoutGrantingAnyRole() {
        JsonNode jwt = LegacyAuthVectors.root().path("jwt");
        LegacyJwtVerifier verifier = verifierAt(ISSUED_AT + 3600);

        LegacyJwtIdentity identity = verifier.verify(jwt.path("token").asString()).orElseThrow();

        assertThat(identity.userId()).isEqualTo(jwt.path("claims").path("user_id").asLong());
        assertThat(identity.openid()).isEqualTo(jwt.path("claims").path("openid").asString());
        assertThat(identity.sessionVersion())
                .isEqualTo(jwt.path("claims").path("session_version").asInt());
        assertThat(identity.issuedAt()).isEqualTo(Instant.ofEpochSecond(ISSUED_AT));
        assertThat(identity.expiresAt()).isEqualTo(Instant.ofEpochSecond(EXPIRES_AT));
        assertThat(identity.jti()).isEqualTo("0123456789abcdef0123456789abcdef");
        assertThat(identity.toString())
                .doesNotContain(identity.openid(), identity.jti(), Long.toString(identity.userId()));
        assertThat(List.of(LegacyJwtIdentity.class.getRecordComponents()).stream()
                        .map(component -> component.getName()))
                .containsExactly(
                        "userId", "openid", "sessionVersion", "expiresAt", "issuedAt", "jti")
                .doesNotContain("role", "roles", "isAdmin");
    }

    @Test
    void rejectsEveryMissingClaimAndEveryUnknownOrRoleClaim() {
        List<String> required =
                List.of("user_id", "openid", "session_version", "exp", "iat", "jti");
        for (String missing : required) {
            List<String> members = new ArrayList<>(validClaimMembers());
            members.removeIf(member -> member.startsWith("\"" + missing + "\":"));
            assertThat(verifierAt(ISSUED_AT + 1).verify(signed(PUBLIC_TEST_HEADER, object(members))))
                    .as("missing claim %s", missing)
                    .isEmpty();
        }

        for (String unknown : List.of(
                "\"role\":\"admin\"",
                "\"roles\":[\"admin\"]",
                "\"is_admin\":true",
                "\"unexpected\":null")) {
            List<String> members = new ArrayList<>(validClaimMembers());
            members.add(unknown);
            assertThat(verifierAt(ISSUED_AT + 1).verify(signed(PUBLIC_TEST_HEADER, object(members))))
                    .as("unknown claim %s", unknown)
                    .isEmpty();
        }
    }

    @Test
    void rejectsAlgorithmConfusionDuplicateKeysAndNonScalarJson() {
        LegacyJwtVerifier verifier = verifierAt(ISSUED_AT + 1);
        String validPayload = object(validClaimMembers());

        assertThat(verifier.verify(signed("{\"alg\":\"none\",\"typ\":\"JWT\"}", validPayload)))
                .isEmpty();
        assertThat(verifier.verify(signed("{\"alg\":\"HS512\",\"typ\":\"JWT\"}", validPayload)))
                .isEmpty();
        assertThat(verifier.verify(signed("{\"alg\":\"HS256\",\"alg\":\"HS256\"}", validPayload)))
                .isEmpty();
        assertThat(verifier.verify(signed("{\"alg\":\"HS256\",\"typ\":\"jwt\"}", validPayload)))
                .isEmpty();
        assertThat(verifier.verify(signed(PUBLIC_TEST_HEADER, validPayload.replace(
                        "\"user_id\":4242", "\"user_id\":4242,\"user_id\":4242"))))
                .isEmpty();
        assertThat(verifier.verify(signed(PUBLIC_TEST_HEADER, validPayload.replace(
                        "\"openid\":\"o-public-test-only-openid-0001\"",
                        "\"openid\":{\"value\":\"nested\"}"))))
                .isEmpty();
        assertThat(verifier.verify(signed(PUBLIC_TEST_HEADER, "[]"))).isEmpty();
    }

    @Test
    void enforcesClaimTypesAndBounds() {
        LegacyJwtVerifier verifier = verifierAt(ISSUED_AT + 1);
        String validPayload = object(validClaimMembers());

        for (String invalidPayload : List.of(
                validPayload.replace("\"user_id\":4242", "\"user_id\":0"),
                validPayload.replace("\"user_id\":4242", "\"user_id\":\"4242\""),
                validPayload.replace("\"session_version\":7", "\"session_version\":-1"),
                validPayload.replace("\"session_version\":7", "\"session_version\":-0"),
                validPayload.replace("\"session_version\":7", "\"session_version\":2147483648"),
                validPayload.replace("\"exp\":" + EXPIRES_AT, "\"exp\":1.0"),
                validPayload.replace("\"iat\":" + ISSUED_AT, "\"iat\":true"),
                validPayload.replace(
                        "o-public-test-only-openid-0001", "bad\\u0000openid"),
                validPayload.replace(
                        "o-public-test-only-openid-0001", "\\u００４１"),
                validPayload.replace(
                        "0123456789abcdef0123456789abcdef", "0123456789ABCDEF0123456789ABCDEF"),
                validPayload.replace(
                        "0123456789abcdef0123456789abcdef", "too-short"))) {
            assertThat(verifier.verify(signed(PUBLIC_TEST_HEADER, invalidPayload)))
                    .as("invalid payload %s", invalidPayload)
                    .isEmpty();
        }
    }

    @Test
    void enforcesExpiryFutureIssuedAtLifetimeAndClockSkewBoundaries() {
        String valid = signed(PUBLIC_TEST_HEADER, object(validClaimMembers()));
        assertThat(verifierAt(EXPIRES_AT + 59).verify(valid)).isPresent();
        assertThat(verifierAt(EXPIRES_AT + 60).verify(valid)).isEmpty();
        assertThat(verifierAt(ISSUED_AT - 60).verify(valid)).isPresent();
        assertThat(verifierAt(ISSUED_AT - 61).verify(valid)).isEmpty();

        String overlongLifetime = object(List.of(
                "\"user_id\":4242",
                "\"openid\":\"o-public-test-only-openid-0001\"",
                "\"session_version\":7",
                "\"exp\":" + (EXPIRES_AT + 1),
                "\"iat\":" + ISSUED_AT,
                "\"jti\":\"0123456789abcdef0123456789abcdef\""));
        assertThat(verifierAt(ISSUED_AT).verify(signed(PUBLIC_TEST_HEADER, overlongLifetime)))
                .isEmpty();
    }

    @Test
    void rejectsTamperingMalformedBase64AndOversizedTokens() {
        String token = LegacyAuthVectors.root().path("jwt").path("token").asString();
        LegacyJwtVerifier verifier = verifierAt(ISSUED_AT + 1);

        assertThat(verifier.verify(token.substring(0, token.length() - 1) + "A")).isEmpty();
        assertThat(verifier.verify("a.b.c")).isEmpty();
        assertThat(verifier.verify("a=.b.c")).isEmpty();
        assertThat(verifier.verify("x".repeat(LegacyJwtVerifier.MAXIMUM_TOKEN_BYTES + 1)))
                .isEmpty();
        assertThat(verifier.verify(null)).isEmpty();
    }

    private static LegacyJwtVerifier verifierAt(long epochSecond) {
        return new LegacyJwtVerifier(
                PUBLIC_TEST_SECRET,
                Clock.fixed(Instant.ofEpochSecond(epochSecond), ZoneOffset.UTC));
    }

    private static List<String> validClaimMembers() {
        return List.of(
                "\"user_id\":4242",
                "\"openid\":\"o-public-test-only-openid-0001\"",
                "\"session_version\":7",
                "\"exp\":" + EXPIRES_AT,
                "\"iat\":" + ISSUED_AT,
                "\"jti\":\"0123456789abcdef0123456789abcdef\"");
    }

    private static String object(List<String> members) {
        return "{" + String.join(",", members) + "}";
    }

    private static String signed(String header, String payload) {
        String encodedHeader = encode(header.getBytes(StandardCharsets.UTF_8));
        String encodedPayload = encode(payload.getBytes(StandardCharsets.UTF_8));
        String signingInput = encodedHeader + "." + encodedPayload;
        return signingInput + "." + encode(hmacSha256(PUBLIC_TEST_SECRET, signingInput));
    }

    private static byte[] hmacSha256(byte[] key, String input) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return mac.doFinal(input.getBytes(StandardCharsets.US_ASCII));
        } catch (Exception exception) {
            throw new AssertionError(exception);
        }
    }

    private static String encode(byte[] value) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }
}
