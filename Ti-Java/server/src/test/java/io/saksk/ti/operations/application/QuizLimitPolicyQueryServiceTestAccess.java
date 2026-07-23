package io.saksk.ti.operations.application;

import io.saksk.ti.operations.api.QuizLimitPolicyView;
import io.saksk.ti.operations.application.port.QuizLimitPolicyReadPort;

public final class QuizLimitPolicyQueryServiceTestAccess {

    private QuizLimitPolicyQueryServiceTestAccess() {
    }

    public static QuizLimitPolicyView read(QuizLimitPolicyReadPort policies) {
        return new QuizLimitPolicyQueryService(policies).getQuizLimitPolicy();
    }
}
