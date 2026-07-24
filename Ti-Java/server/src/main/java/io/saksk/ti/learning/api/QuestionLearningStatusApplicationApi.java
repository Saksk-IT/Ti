package io.saksk.ti.learning.api;

/** Narrow learning-owned read used to enrich the legacy question-edit response. */
public interface QuestionLearningStatusApplicationApi {

    QuestionLearningStatusView findStatus(
            AuthenticatedLearningViewer viewer,
            long questionId);
}
