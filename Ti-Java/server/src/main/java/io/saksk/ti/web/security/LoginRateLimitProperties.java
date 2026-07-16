package io.saksk.ti.web.security;

import java.nio.charset.StandardCharsets;
import java.util.Objects;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.login-rate-limit")
public final class LoginRateLimitProperties {

    private static final int MINIMUM_SECRET_BYTES = 32;

    private final String namespace;
    private final int requestsPerMinute;
    private final String keySecret;

    public LoginRateLimitProperties(String namespace, int requestsPerMinute, String keySecret) {
        this.namespace = requireNamespace(namespace);
        if (requestsPerMinute < 1 || requestsPerMinute > 100_000) {
            throw new IllegalArgumentException("Login rate limit must be between 1 and 100000");
        }
        this.requestsPerMinute = requestsPerMinute;
        this.keySecret = Objects.requireNonNull(keySecret, "keySecret");
        if (keySecret.getBytes(StandardCharsets.UTF_8).length < MINIMUM_SECRET_BYTES) {
            throw new IllegalArgumentException("Login rate-limit key secret must contain at least 32 bytes");
        }
    }

    public String namespace() {
        return namespace;
    }

    public int requestsPerMinute() {
        return requestsPerMinute;
    }

    byte[] keySecretBytes() {
        return keySecret.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public String toString() {
        return "LoginRateLimitProperties[namespace=" + namespace
                + ", requestsPerMinute=" + requestsPerMinute
                + ", keySecret=<redacted>]";
    }

    private static String requireNamespace(String namespace) {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe login rate-limit namespace");
        }
        return namespace;
    }
}
