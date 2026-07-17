package io.saksk.ti.personalbank.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;

import io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult.Outcome;
import org.junit.jupiter.api.Test;

class PersonalBankUsageStatsResultTest {

    private static final PersonalBankUsageStatsView VIEW =
            new PersonalBankUsageStatsView(77, true, 41L, 1, 2, 3, 5, 4);

    @Test
    void factoriesExposeTheExactAvailableNotFoundAndForbiddenOutcomes() {
        PersonalBankUsageStatsResult available = PersonalBankUsageStatsResult.available(VIEW);
        PersonalBankUsageStatsResult notFound = PersonalBankUsageStatsResult.notFound();
        PersonalBankUsageStatsResult forbidden = PersonalBankUsageStatsResult.forbidden();

        assertThat(available.outcome()).isEqualTo(Outcome.AVAILABLE);
        assertThat(available.view()).isSameAs(VIEW);
        assertThat(notFound)
                .isEqualTo(new PersonalBankUsageStatsResult(Outcome.NOT_FOUND, null));
        assertThat(forbidden)
                .isEqualTo(new PersonalBankUsageStatsResult(Outcome.FORBIDDEN, null));
    }

    @Test
    void rejectsNullOutcomeAndNullAvailableView() {
        assertThatNullPointerException()
                .isThrownBy(() -> new PersonalBankUsageStatsResult(null, null))
                .withMessage("outcome");
        assertThatNullPointerException()
                .isThrownBy(() -> PersonalBankUsageStatsResult.available(null))
                .withMessage("view");
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new PersonalBankUsageStatsResult(Outcome.AVAILABLE, null));
    }

    @Test
    void rejectsPayloadsOnNonAvailableOutcomes() {
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new PersonalBankUsageStatsResult(Outcome.NOT_FOUND, VIEW));
        assertThatIllegalArgumentException()
                .isThrownBy(() -> new PersonalBankUsageStatsResult(Outcome.FORBIDDEN, VIEW));
    }
}
