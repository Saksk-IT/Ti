package io.saksk.ti.personalbank.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

import org.junit.jupiter.api.Test;

class AuthenticatedPersonalBankViewerTest {

    @Test
    void preservesAValidServerDerivedIdentity() {
        assertThat(new AuthenticatedPersonalBankViewer(1).identityId()).isEqualTo(1);
        assertThat(new AuthenticatedPersonalBankViewer(Long.MAX_VALUE).identityId())
                .isEqualTo(Long.MAX_VALUE);
    }

    @Test
    void rejectsZeroAndNegativeIdentities() {
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new AuthenticatedPersonalBankViewer(0))
                .withMessage("identityId must be positive");
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new AuthenticatedPersonalBankViewer(Long.MIN_VALUE))
                .withMessage("identityId must be positive");
    }
}
