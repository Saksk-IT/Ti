package io.saksk.ti.catalog.api;

/** Catalog application boundary for the legacy in-quiz question editor. */
public interface QuestionEditApplicationApi {

    QuestionEditResult editQuestion(QuestionEditCommand command);
}
