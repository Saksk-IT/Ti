package io.saksk.ti.identity.infrastructure.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.concurrent.Semaphore;
import org.junit.jupiter.api.Test;

class PasswordKdfBudgetTest {

    @Test
    void releasesPermitAfterSuccessAndException() {
        PasswordKdfBudget budget = new PasswordKdfBudget(new Semaphore(1));

        assertThat(budget.callOrThrow(() -> "ok")).isEqualTo("ok");
        assertThat(budget.availablePermits()).isEqualTo(1);
        assertThatThrownBy(() -> budget.callOrThrow(() -> {
                    throw new IllegalArgumentException("public-test-only failure");
                }))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("public-test-only failure");
        assertThat(budget.availablePermits()).isEqualTo(1);
    }

    @Test
    void forbidsNestedAcquisitionAndStillReleasesTheOuterPermit() {
        PasswordKdfBudget budget = new PasswordKdfBudget(new Semaphore(1));

        assertThatThrownBy(() -> budget.callOrThrow(() -> budget.callOrThrow(() -> "nested")))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("nested password KDF execution is forbidden");
        assertThat(budget.availablePermits()).isEqualTo(1);
    }

    @Test
    void saturatedBudgetHasOneStableFailureMode() {
        PasswordKdfBudget budget = new PasswordKdfBudget(new Semaphore(0));

        assertThat(budget.tryRun(() -> true)).isFalse();
        assertThatThrownBy(() -> budget.callOrThrow(() -> "never"))
                .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class)
                .hasMessage("password KDF capacity is exhausted");
    }

    @Test
    void capacityRecoversImmediatelyAfterTheSaturatingWorkReleasesItsPermit()
            throws Exception {
        Semaphore semaphore = new Semaphore(1, true);
        PasswordKdfBudget budget = new PasswordKdfBudget(semaphore);
        semaphore.acquire();

        assertThatThrownBy(() -> budget.callOrThrow(() -> "blocked"))
                .isInstanceOf(PasswordKdfBudget.PasswordKdfCapacityException.class);
        semaphore.release();

        assertThat(budget.callOrThrow(() -> "recovered")).isEqualTo("recovered");
        assertThat(budget.availablePermits()).isEqualTo(1);
    }
}
