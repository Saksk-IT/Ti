package io.saksk.ti.identity.domain;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class LoginIdentifierTest {

    @Test
    void preservesLegacyEmailAndMainlandPhoneClassification() {
        assertThat(LoginIdentifier.parse(" User@Example.test ").orElseThrow())
                .isEqualTo(new LoginIdentifier(LoginIdentifier.Kind.EMAIL, "User@Example.test"));
        assertThat(LoginIdentifier.parse("13800138000").orElseThrow().kind())
                .isEqualTo(LoginIdentifier.Kind.PHONE);
        assertThat(LoginIdentifier.parse("username")).isEmpty();
        assertThat(LoginIdentifier.parse("12800138000")).isEmpty();
        assertThat(LoginIdentifier.parse("   ")).isEmpty();
    }
}
