package io.saksk.ti.learning.api;

/** User-specific favorite and mistake flags for one catalog question. */
public record QuestionLearningStatusView(boolean favorite, boolean mistake) {
}
