package io.saksk.ti.catalog.infrastructure.coordination;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import java.time.Duration;
import org.junit.jupiter.api.Test;

class PublicBankSnapshotPropertiesTest {

    @Test
    void usesSafeShadowDefaultsWhenOptionalConfigurationIsAbsent() {
        PublicBankSnapshotProperties properties =
                new PublicBankSnapshotProperties(false, null, null);

        assertThat(properties.readinessEnabled()).isFalse();
        assertThat(properties.refreshLockKey())
                .isEqualTo("ti-java:catalog:public-bank-snapshot:refresh-lock");
        assertThat(properties.refreshLockTtl()).isEqualTo(Duration.ofMinutes(15));
    }

    @Test
    void derivesOneBoundedRefreshLockKey() {
        PublicBankSnapshotProperties properties = new PublicBankSnapshotProperties(
                false,
                "ti-java:catalog:public-bank-snapshot",
                Duration.ofMinutes(15));

        assertThat(properties.readinessEnabled()).isFalse();
        assertThat(properties.refreshLockKey())
                .isEqualTo("ti-java:catalog:public-bank-snapshot:refresh-lock");
        assertThat(properties.refreshLockTtl()).isEqualTo(Duration.ofMinutes(15));
    }

    @Test
    void rejectsUnsafeNamespacesAndUnboundedLeaseTtls() {
        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankSnapshotProperties(false, "unsafe namespace", Duration.ofMinutes(1)));
        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankSnapshotProperties(false, "safe:namespace:", Duration.ofMinutes(1)));
        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankSnapshotProperties(false, "safe:namespace", Duration.ofSeconds(29)));
        assertThatIllegalArgumentException().isThrownBy(() ->
                new PublicBankSnapshotProperties(false, "safe:namespace", Duration.ofHours(25)));
    }
}
