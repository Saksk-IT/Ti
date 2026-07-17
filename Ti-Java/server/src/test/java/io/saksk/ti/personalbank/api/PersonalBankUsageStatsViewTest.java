package io.saksk.ti.personalbank.api;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class PersonalBankUsageStatsViewTest {

    @Test
    void preservesTheExactEightFieldHttpNeutralSnapshot() {
        var view = new PersonalBankUsageStatsView(
                -7, true, Long.MAX_VALUE, 1, 2, 3, 4, 3);

        assertThat(view.bankId()).isEqualTo(-7);
        assertThat(view.publicBank()).isTrue();
        assertThat(view.ownerId()).isEqualTo(Long.MAX_VALUE);
        assertThat(view.ownerCount()).isEqualTo(1);
        assertThat(view.sharedUsers()).isEqualTo(2);
        assertThat(view.publicUsers()).isEqualTo(3);
        assertThat(view.totalUsers()).isEqualTo(4);
        assertThat(view.totalUsersExcludingOwner()).isEqualTo(3);
    }
}
