package io.saksk.ti.identity.infrastructure.security;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Arrays;
import java.util.Objects;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.legacy-auth")
final class LegacyAuthenticationProperties {

    private final Instant acceptUntil;
    private final byte[] secret;

    LegacyAuthenticationProperties(Instant acceptUntil, String secret) {
        this.acceptUntil = Objects.requireNonNull(acceptUntil, "acceptUntil");
        byte[] encoded = Objects.requireNonNull(secret, "secret").getBytes(StandardCharsets.UTF_8);
        if (encoded.length < 16 || encoded.length > 4096) {
            Arrays.fill(encoded, (byte) 0);
            throw new IllegalArgumentException("Legacy authentication secret has an invalid length");
        }
        this.secret = encoded;
    }

    Instant acceptUntil() {
        return acceptUntil;
    }

    byte[] secretCopy() {
        return Arrays.copyOf(secret, secret.length);
    }

    @Override
    public String toString() {
        return "LegacyAuthenticationProperties[acceptUntil=" + acceptUntil + ", secret=<redacted>]";
    }
}
