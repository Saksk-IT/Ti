package io.saksk.ti.operations.application;

import io.saksk.ti.operations.api.QuizLimitPolicyApplicationApi;
import io.saksk.ti.operations.api.QuizLimitPolicyView;
import io.saksk.ti.operations.application.port.QuizLimitPolicyReadPort;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class QuizLimitPolicyQueryService implements QuizLimitPolicyApplicationApi {

    private static final int DEFAULT_LIMIT = 100;

    private final QuizLimitPolicyReadPort policies;

    QuizLimitPolicyQueryService(QuizLimitPolicyReadPort policies) {
        this.policies = Objects.requireNonNull(policies, "policies");
    }

    @Override
    @Transactional(readOnly = true)
    public QuizLimitPolicyView getQuizLimitPolicy() {
        QuizLimitPolicyReadPort.RawQuizLimitConfiguration raw = policies.read();
        boolean enabled = raw.enabledValue().filter("1"::equals).isPresent();
        int limit = raw.limitValue()
                .map(QuizLimitPolicyQueryService::parseLimit)
                .orElse(DEFAULT_LIMIT);
        return new QuizLimitPolicyView(enabled, limit);
    }

    private static int parseLimit(String raw) {
        try {
            return Integer.parseInt(raw.trim());
        } catch (NumberFormatException exception) {
            return DEFAULT_LIMIT;
        }
    }
}
