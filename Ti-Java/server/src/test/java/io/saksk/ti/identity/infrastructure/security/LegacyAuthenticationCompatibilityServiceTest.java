package io.saksk.ti.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.identity.application.LegacyAuthenticationAuthority;
import io.saksk.ti.identity.application.port.AuthoritativeIdentityStateStore;
import io.saksk.ti.identity.domain.AuthoritativeIdentityState;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.Optional;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

class LegacyAuthenticationCompatibilityServiceTest {

    private static final byte[] SECRET = LegacyAuthVectors.publicTestSecret();
    private static final long ISSUED_AT = LegacyAuthVectors.fixedTime();
    private static final long JWT_EXPIRES_AT = ISSUED_AT + 15 * 24 * 60 * 60;

    @Test
    void validJwtMustAlsoMatchCurrentPostgresqlState() {
        FakeStore store = new FakeStore(state(
                "current-database-name",
                "o-public-test-only-openid-0001",
                false,
                false,
                7,
                true,
                false));
        var service = serviceAt(ISSUED_AT + 3600, store);

        var identity = service.authenticateJwt(LegacyAuthVectors.root()
                        .path("jwt")
                        .path("token")
                        .asString())
                .orElseThrow()
                .identity();

        assertThat(identity.username()).isEqualTo("current-database-name");
        assertThat(identity.administrator()).isFalse();
        assertThat(identity.subjectAdministrator()).isTrue();
        assertThat(identity.notificationAdministrator()).isFalse();
        assertThat(store.calls).isOne();
    }

    @Test
    void expiredJwtIsRejectedByTheVerifierBeforeAnyDatabaseLookup() {
        FakeStore store = new FakeStore(state(
                "current", "o-public-test-only-openid-0001", true, false, 7, true, true));
        var expired = serviceAt(JWT_EXPIRES_AT + 60, store);

        assertThat(expired.authenticateJwt(LegacyAuthVectors.root()
                        .path("jwt")
                        .path("token")
                        .asString()))
                .isEmpty();
        assertThat(store.calls).isZero();
    }

    @Test
    void sessionUsernameAndRolesAreAlwaysReloadedFromTheDatabase() {
        JsonNode roleBearingVector = LegacyAuthVectors.root().path("flask_sessions").get(1);
        assertThat(roleBearingVector.path("name").asString())
                .isEqualTo("compressed_roles_ignored");
        String cookie = roleBearingVector.path("cookie").asString();
        String cookieUsername = roleBearingVector.path("identity").path("username").asString();
        FakeStore store = new FakeStore(state(
                "renamed-in-database", null, false, false, 7, false, true));

        var authentication = serviceAt(ISSUED_AT + 3600, store)
                .authenticateFlaskSession(cookie)
                .orElseThrow();
        var identity = authentication.identity();

        assertThat(identity.username()).isEqualTo("renamed-in-database").isNotEqualTo(cookieUsername);
        assertThat(identity.administrator()).isFalse();
        assertThat(identity.subjectAdministrator()).isFalse();
        assertThat(identity.notificationAdministrator()).isTrue();
        assertThat(authentication.remember()).isTrue();
        assertThat(identity.toString())
                .doesNotContain(cookie, cookieUsername, "renamed-in-database", "4242");
    }

    @Test
    void versionLockMissingUserAndDatabaseFailureAllFailClosed() {
        String token = LegacyAuthVectors.root().path("jwt").path("token").asString();

        assertThat(serviceAt(ISSUED_AT + 1, new FakeStore(state(
                        "version-changed",
                        "o-public-test-only-openid-0001",
                        true,
                        false,
                        8,
                        true,
                        true)))
                        .authenticateJwt(token))
                .isEmpty();
        assertThat(serviceAt(ISSUED_AT + 1, new FakeStore(state(
                        "locked",
                        "o-public-test-only-openid-0001",
                        true,
                        true,
                        7,
                        true,
                        true)))
                        .authenticateJwt(token))
                .isEmpty();
        assertThat(serviceAt(ISSUED_AT + 1, new FakeStore(null)).authenticateJwt(token))
                .isEmpty();

        FakeStore failing = new FakeStore(null);
        failing.failure = new IllegalStateException("database unavailable");
        assertThat(serviceAt(ISSUED_AT + 1, failing).authenticateJwt(token)).isEmpty();
    }

    @Test
    void unbindAndRebindInvalidateNonEmptyOpenidTokens() {
        String token = LegacyAuthVectors.root().path("jwt").path("token").asString();
        assertThat(serviceAt(ISSUED_AT + 1, new FakeStore(state(
                        "unbound", null, false, false, 7, false, false)))
                        .authenticateJwt(token))
                .isEmpty();
        assertThat(serviceAt(ISSUED_AT + 1, new FakeStore(state(
                        "rebound", "different-openid", false, false, 7, false, false)))
                        .authenticateJwt(token))
                .isEmpty();
    }

    @Test
    void emptyOpenidJwtPreservesObservedNonWechatBearerSemantics() {
        FakeStore bound = new FakeStore(state(
                "database-user", "later-database-binding", false, false, 7, false, false));

        assertThat(serviceAt(ISSUED_AT + 1, bound).authenticateJwt(signedJwt("")))
                .isPresent();
    }

    @Test
    void malformedInputsAndFacadeStringRepresentationDoNotLeakCredentials() {
        FakeStore store = new FakeStore(state(
                "current", "o-public-test-only-openid-0001", false, false, 7, false, false));
        var service = serviceAt(ISSUED_AT + 1, store);

        assertThat(service.authenticateJwt(null)).isEmpty();
        assertThat(service.authenticateJwt("not-a-jwt")).isEmpty();
        assertThat(service.authenticateFlaskSession(null)).isEmpty();
        assertThat(service.authenticateFlaskSession("not-a-cookie")).isEmpty();
        assertThat(store.calls).isZero();
        assertThat(service.toString())
                .isEqualTo("LegacyAuthenticationCompatibilityService[redacted]")
                .doesNotContain("openid", "token", "cookie");
    }

    private static LegacyAuthenticationCompatibilityService serviceAt(
            long epochSecond,
            FakeStore store
    ) {
        Clock clock = Clock.fixed(Instant.ofEpochSecond(epochSecond), ZoneOffset.UTC);
        return new LegacyAuthenticationCompatibilityService(
                new LegacyJwtVerifier(SECRET, clock),
                new LegacyFlaskSessionVerifier(SECRET, clock),
                new LegacyAuthenticationAuthority(store),
                clock,
                clock.instant().plusSeconds(24 * 60 * 60),
                null);
    }

    private static AuthoritativeIdentityState state(
            String username,
            String openid,
            boolean administrator,
            boolean locked,
            int sessionVersion,
            boolean subjectAdministrator,
            boolean notificationAdministrator
    ) {
        return new AuthoritativeIdentityState(
                4242,
                username,
                openid,
                administrator,
                locked,
                sessionVersion,
                subjectAdministrator,
                notificationAdministrator);
    }

    private static String signedJwt(String openid) {
        String header = encode("{\"alg\":\"HS256\",\"typ\":\"JWT\"}");
        String payload = encode("{\"user_id\":4242,\"openid\":\""
                + openid
                + "\",\"session_version\":7,\"exp\":"
                + JWT_EXPIRES_AT
                + ",\"iat\":"
                + ISSUED_AT
                + ",\"jti\":\"0123456789abcdef0123456789abcdef\"}");
        String signingInput = header + "." + payload;
        return signingInput + "." + Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(hmacSha256(signingInput));
    }

    private static String encode(String value) {
        return Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static byte[] hmacSha256(String value) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(SECRET, "HmacSHA256"));
            return mac.doFinal(value.getBytes(StandardCharsets.US_ASCII));
        } catch (Exception exception) {
            throw new AssertionError(exception);
        }
    }

    private static final class FakeStore implements AuthoritativeIdentityStateStore {
        private final AuthoritativeIdentityState state;
        private RuntimeException failure;
        private int calls;

        private FakeStore(AuthoritativeIdentityState state) {
            this.state = state;
        }

        @Override
        public Optional<AuthoritativeIdentityState> findById(long identityId) {
            calls++;
            if (failure != null) {
                throw failure;
            }
            return Optional.ofNullable(state);
        }
    }
}
