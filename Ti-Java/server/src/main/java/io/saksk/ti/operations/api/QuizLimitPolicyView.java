package io.saksk.ti.operations.api;

/** Operations-owned, normalized quiz-limit configuration for trusted adapters. */
public record QuizLimitPolicyView(boolean enabled, int limitCount) {
}
