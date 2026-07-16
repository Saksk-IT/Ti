package io.saksk.ti.identity.application;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.identity.application.port.SubjectAccessReadPort;
import io.saksk.ti.identity.domain.SubjectAccessState;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SubjectAccessPolicyServiceTest {

    @Test
    void exposesCurrentIdentityOwnedAdministratorAndBlacklistFacts() {
        SubjectAccessReadPort port = identityId -> Optional.of(
                new SubjectAccessState(false, Set.of(8, 3)));
        var service = new SubjectAccessPolicyService(port);

        var decision = service.subjectAccess(41);

        assertThat(decision.identityExists()).isTrue();
        assertThat(decision.administrator()).isFalse();
        assertThat(decision.restrictedSubjectIds()).containsExactlyInAnyOrder(3, 8);
    }

    @Test
    void missingAndInvalidIdentitiesFailClosedWithoutInventingAccessFacts() {
        int[] calls = {0};
        SubjectAccessReadPort port = identityId -> {
            calls[0]++;
            return Optional.empty();
        };
        var service = new SubjectAccessPolicyService(port);

        assertThat(service.subjectAccess(41).identityExists()).isFalse();
        assertThat(service.subjectAccess(0).identityExists()).isFalse();
        assertThat(calls[0]).isOne();
    }
}
