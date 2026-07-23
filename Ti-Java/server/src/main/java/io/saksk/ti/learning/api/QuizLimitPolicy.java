package io.saksk.ti.learning.api;

/**
 * Trusted snapshot of the operations-owned quiz-limit configuration.
 *
 * <p>The web adapter obtains this value from the operations public API before invoking learning,
 * so the learning transaction never reads the operations-owned {@code system_config} table.
 */
public record QuizLimitPolicy(boolean enabled, int limitCount) {

    public static QuizLimitPolicy disabled() {
        return new QuizLimitPolicy(false, 100);
    }
}
