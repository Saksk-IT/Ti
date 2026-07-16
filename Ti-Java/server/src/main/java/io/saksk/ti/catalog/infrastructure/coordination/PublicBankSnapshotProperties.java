package io.saksk.ti.catalog.infrastructure.coordination;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("ti.catalog.public-bank.snapshot")
public final class PublicBankSnapshotProperties {

    private static final String DEFAULT_REFRESH_LOCK_NAMESPACE =
            "ti-java:catalog:public-bank-snapshot";
    private static final Duration DEFAULT_REFRESH_LOCK_TTL = Duration.ofMinutes(15);

    private final boolean readinessEnabled;
    private final String refreshLockNamespace;
    private final Duration refreshLockTtl;

    public PublicBankSnapshotProperties(
            boolean readinessEnabled,
            String refreshLockNamespace,
            Duration refreshLockTtl
    ) {
        refreshLockNamespace = refreshLockNamespace == null
                ? DEFAULT_REFRESH_LOCK_NAMESPACE
                : refreshLockNamespace;
        refreshLockTtl = refreshLockTtl == null ? DEFAULT_REFRESH_LOCK_TTL : refreshLockTtl;
        if (refreshLockNamespace == null
                || !refreshLockNamespace.matches("[a-z0-9][a-z0-9:_-]{0,127}")
                || refreshLockNamespace.endsWith(":")) {
            throw new IllegalArgumentException("Unsafe public-bank refresh-lock namespace");
        }
        if (refreshLockTtl == null
                || refreshLockTtl.compareTo(Duration.ofSeconds(30)) < 0
                || refreshLockTtl.compareTo(Duration.ofHours(24)) > 0) {
            throw new IllegalArgumentException(
                    "Public-bank refresh-lock TTL must be between 30 seconds and 24 hours");
        }
        this.readinessEnabled = readinessEnabled;
        this.refreshLockNamespace = refreshLockNamespace;
        this.refreshLockTtl = refreshLockTtl;
    }

    public boolean readinessEnabled() {
        return readinessEnabled;
    }

    public String refreshLockKey() {
        return refreshLockNamespace + ":refresh-lock";
    }

    public Duration refreshLockTtl() {
        return refreshLockTtl;
    }
}
