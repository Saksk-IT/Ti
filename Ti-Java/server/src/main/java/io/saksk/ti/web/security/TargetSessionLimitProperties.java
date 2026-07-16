package io.saksk.ti.web.security;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.security.target-session-limit")
public record TargetSessionLimitProperties(
        String namespace,
        int maxSessionsPerIdentity,
        int maxTotalSessions,
        Duration registryTtl
) {

    public TargetSessionLimitProperties {
        if (namespace == null
                || !namespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || namespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe target Session registry namespace");
        }
        if (maxSessionsPerIdentity < 1 || maxSessionsPerIdentity > 10) {
            throw new IllegalArgumentException(
                    "Target Sessions per identity must be between 1 and 10");
        }
        if (maxTotalSessions < maxSessionsPerIdentity || maxTotalSessions > 100_000) {
            throw new IllegalArgumentException(
                    "Global target Session limit must cover the per-identity limit and be at most 100000");
        }
        if (registryTtl == null
                || registryTtl.compareTo(Duration.ofDays(7)) < 0
                || registryTtl.compareTo(Duration.ofDays(30)) > 0) {
            throw new IllegalArgumentException(
                    "Target Session registry TTL must be between seven and thirty days");
        }
    }
}
