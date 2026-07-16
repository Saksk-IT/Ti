package io.saksk.ti.catalog.api;

/** Controls whether a catalog count may retain questions without an existing subject row. */
public enum QuestionSubjectAssignmentScope {
    INCLUDE_UNASSIGNED,
    REQUIRE_EXISTING_SUBJECT
}
