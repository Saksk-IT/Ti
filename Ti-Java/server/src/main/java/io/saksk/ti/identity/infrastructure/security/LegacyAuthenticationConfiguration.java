package io.saksk.ti.identity.infrastructure.security;

import io.micrometer.core.instrument.MeterRegistry;
import io.saksk.ti.identity.application.LegacyAuthenticationAuthority;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Arrays;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(
        prefix = "ti.security.legacy-auth",
        name = "enabled",
        havingValue = "true")
@EnableConfigurationProperties(LegacyAuthenticationProperties.class)
class LegacyAuthenticationConfiguration {

    private static final Duration MAXIMUM_TRANSITION_WINDOW = Duration.ofDays(366);

    @Bean
    LegacyAuthenticationCompatibilityService legacyAuthenticationCompatibilityService(
            LegacyAuthenticationProperties properties,
            LegacyAuthenticationAuthority authority,
            Clock clock,
            MeterRegistry meters
    ) {
        Instant now = clock.instant();
        if (!properties.acceptUntil().isAfter(now)
                || properties.acceptUntil().isAfter(now.plus(MAXIMUM_TRANSITION_WINDOW))) {
            throw new IllegalStateException(
                    "Legacy authentication accept-until must be in the next 366 days");
        }

        byte[] secret = properties.secretCopy();
        try {
            return new LegacyAuthenticationCompatibilityService(
                    new LegacyJwtVerifier(secret, clock),
                    new LegacyFlaskSessionVerifier(secret, clock),
                    authority,
                    clock,
                    properties.acceptUntil(),
                    new LegacyAuthenticationMetrics(meters));
        } finally {
            Arrays.fill(secret, (byte) 0);
        }
    }
}
