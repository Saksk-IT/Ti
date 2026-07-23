package io.saksk.ti.operations.application.port;

import java.util.Objects;
import java.util.Optional;

/** Raw owner-local read of the two legacy quiz-limit settings. */
public interface QuizLimitPolicyReadPort {

    RawQuizLimitConfiguration read();

    record RawQuizLimitConfiguration(
            Optional<String> enabledValue,
            Optional<String> limitValue
    ) {
        public RawQuizLimitConfiguration {
            enabledValue = Objects.requireNonNull(enabledValue, "enabledValue");
            limitValue = Objects.requireNonNull(limitValue, "limitValue");
        }
    }
}
