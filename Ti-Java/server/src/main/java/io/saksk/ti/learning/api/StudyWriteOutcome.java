package io.saksk.ti.learning.api;

/** HTTP-neutral outcomes shared by the three legacy study write operations. */
public enum StudyWriteOutcome {
    SUCCESS,
    QUESTION_ID_INVALID,
    BANK_ID_INVALID,
    BANK_ACCESS_DENIED,
    SUBJECT_INVALID,
    SUBJECT_NOT_FOUND,
    QUESTION_OUT_OF_SCOPE,
    MUTATION_REJECTED,
    IDEMPOTENCY_CONFLICT,
    IDEMPOTENCY_IN_PROGRESS
}
