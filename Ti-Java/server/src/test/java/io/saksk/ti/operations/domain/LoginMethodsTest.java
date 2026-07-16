package io.saksk.ti.operations.domain;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class LoginMethodsTest {

    @Test
    void preservesTheObservedLegacyDefaultModePrecedence() {
        assertThat(new LoginMethods(true, true).defaultMode()).isEqualTo("phone");
        assertThat(new LoginMethods(false, true).defaultMode()).isEqualTo("qr");
        assertThat(new LoginMethods(false, false).defaultMode()).isEqualTo("password");
    }
}
