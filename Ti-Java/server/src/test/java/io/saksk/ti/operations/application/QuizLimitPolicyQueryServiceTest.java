package io.saksk.ti.operations.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.saksk.ti.operations.api.QuizLimitPolicyView;
import io.saksk.ti.operations.application.port.QuizLimitPolicyReadPort;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class QuizLimitPolicyQueryServiceTest {

    private final QuizLimitPolicyReadPort policies =
            mock(QuizLimitPolicyReadPort.class);
    private final QuizLimitPolicyQueryService service =
            new QuizLimitPolicyQueryService(policies);

    @Test
    void missingConfigurationPreservesLegacyDisabledHundredDefault() {
        when(policies.read()).thenReturn(raw(null, null));

        assertThat(service.getQuizLimitPolicy())
                .isEqualTo(new QuizLimitPolicyView(false, 100));
    }

    @Test
    void onlyTheExactLegacyOneValueEnablesTheLimit() {
        when(policies.read()).thenReturn(raw("1", "60"));
        assertThat(service.getQuizLimitPolicy())
                .isEqualTo(new QuizLimitPolicyView(true, 60));

        when(policies.read()).thenReturn(raw("true", "60"));
        assertThat(service.getQuizLimitPolicy())
                .isEqualTo(new QuizLimitPolicyView(false, 60));
    }

    @Test
    void integerParsingMatchesLegacyWhitespaceAndFallbackBehavior() {
        when(policies.read()).thenReturn(raw("1", " -1 "));
        assertThat(service.getQuizLimitPolicy().limitCount()).isEqualTo(-1);

        when(policies.read()).thenReturn(raw("1", "not-an-integer"));
        assertThat(service.getQuizLimitPolicy().limitCount()).isEqualTo(100);

        when(policies.read()).thenReturn(raw("1", "999999999999999999999"));
        assertThat(service.getQuizLimitPolicy().limitCount()).isEqualTo(100);
    }

    private static QuizLimitPolicyReadPort.RawQuizLimitConfiguration raw(
            String enabled,
            String limit
    ) {
        return new QuizLimitPolicyReadPort.RawQuizLimitConfiguration(
                Optional.ofNullable(enabled),
                Optional.ofNullable(limit));
    }
}
