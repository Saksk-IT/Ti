package io.saksk.ti.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.saksk.ti.identity.application.LegacyAuthenticationAuthority;
import io.saksk.ti.identity.domain.AuthoritativeIdentityState;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

class LegacyAuthenticationConfigurationTest {

    private static final String PUBLIC_TEST_SECRET =
            new String(LegacyAuthVectors.publicTestSecret(), StandardCharsets.UTF_8);
    private static final Instant VECTOR_TIME =
            Instant.ofEpochSecond(LegacyAuthVectors.fixedTime() + 3_600);

    @Test
    void compatibilityBeanIsAbsentUnlessTheKillSwitchIsExplicitlyEnabled() {
        new ApplicationContextRunner()
                .withUserConfiguration(
                        LegacyAuthenticationConfiguration.class,
                        SupportConfiguration.class)
                .run(context -> assertThat(context)
                        .doesNotHaveBean(LegacyAuthenticationCompatibilityService.class));
    }

    @Test
    void enabledCompatibilityWindowBindsPropertiesAndBuildsTheLocalVerifiers() {
        new ApplicationContextRunner()
                .withUserConfiguration(
                        LegacyAuthenticationConfiguration.class,
                        SupportConfiguration.class)
                .withPropertyValues(
                        "ti.security.legacy-auth.enabled=true",
                        "ti.security.legacy-auth.accept-until=2030-01-02T00:00:00Z",
                        "ti.security.legacy-auth.secret=" + PUBLIC_TEST_SECRET)
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    assertThat(context)
                            .hasSingleBean(LegacyAuthenticationCompatibilityService.class);
                    assertThat(context.getBean(LegacyAuthenticationProperties.class).toString())
                            .contains("2030-01-02T00:00:00Z", "<redacted>")
                            .doesNotContain(PUBLIC_TEST_SECRET);
                });
    }

    @Test
    void invalidSecretAndExpiredOrOverlongWindowsFailClosed() {
        assertThatThrownBy(() -> new LegacyAuthenticationProperties(
                        VECTOR_TIME.plus(Duration.ofDays(1)), "too-short"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("invalid length")
                .hasMessageNotContaining("too-short");

        Clock clock = Clock.fixed(VECTOR_TIME, ZoneOffset.UTC);
        LegacyAuthenticationConfiguration configuration =
                new LegacyAuthenticationConfiguration();
        LegacyAuthenticationAuthority authority = authority();
        MeterRegistry meters = new SimpleMeterRegistry();

        assertThatThrownBy(() -> configuration.legacyAuthenticationCompatibilityService(
                        propertiesAt(VECTOR_TIME), authority, clock, meters))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("next 366 days");
        assertThatThrownBy(() -> configuration.legacyAuthenticationCompatibilityService(
                        propertiesAt(VECTOR_TIME.plus(Duration.ofDays(367))),
                        authority,
                        clock,
                        meters))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("next 366 days");
    }

    @Test
    void cutoffIsRecheckedForEveryCredentialAndOutcomesAreCounted() {
        MutableClock clock = new MutableClock(VECTOR_TIME);
        SimpleMeterRegistry meters = new SimpleMeterRegistry();
        Instant cutoff = VECTOR_TIME.plus(Duration.ofHours(1));
        var service = new LegacyAuthenticationConfiguration()
                .legacyAuthenticationCompatibilityService(
                        propertiesAt(cutoff), authority(), clock, meters);
        String token = LegacyAuthVectors.root().path("jwt").path("token").asString();

        assertThat(service.authenticateJwt(token)).isPresent();
        clock.set(cutoff);
        assertThat(service.authenticateJwt(token)).isEmpty();

        assertThat(meters.get("ti.security.legacy.authentication")
                        .tags("format", "jwt", "outcome", "accepted")
                        .counter()
                        .count())
                .isEqualTo(1.0);
        assertThat(meters.get("ti.security.legacy.authentication")
                        .tags("format", "jwt", "outcome", "rejected")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    private static LegacyAuthenticationProperties propertiesAt(Instant acceptUntil) {
        return new LegacyAuthenticationProperties(acceptUntil, PUBLIC_TEST_SECRET);
    }

    private static LegacyAuthenticationAuthority authority() {
        return new LegacyAuthenticationAuthority(identityId -> Optional.of(
                new AuthoritativeIdentityState(
                        identityId,
                        "current-database-user",
                        "o-public-test-only-openid-0001",
                        false,
                        false,
                        7,
                        true,
                        false)));
    }

    @Configuration(proxyBeanMethods = false)
    static class SupportConfiguration {

        @Bean
        Clock legacyAuthenticationClock() {
            return Clock.fixed(Instant.parse("2030-01-01T00:00:00Z"), ZoneOffset.UTC);
        }

        @Bean
        MeterRegistry meterRegistry() {
            return new SimpleMeterRegistry();
        }

        @Bean
        LegacyAuthenticationAuthority legacyAuthenticationAuthority() {
            return authority();
        }
    }

    private static final class MutableClock extends Clock {
        private Instant instant;

        private MutableClock(Instant instant) {
            this.instant = instant;
        }

        private void set(Instant instant) {
            this.instant = instant;
        }

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            if (!ZoneOffset.UTC.equals(zone)) {
                throw new IllegalArgumentException("Only UTC is supported by this test clock");
            }
            return this;
        }

        @Override
        public Instant instant() {
            return instant;
        }
    }
}
