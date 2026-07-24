package io.saksk.ti.catalog.api;

/** Server-derived identity and role facts used by the catalog question-edit use case. */
public record QuestionEditorIdentity(
        long identityId,
        boolean administrator,
        boolean subjectAdministrator
) {

    public QuestionEditorIdentity {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
    }

    public boolean mayEditQuestions() {
        return administrator || subjectAdministrator;
    }
}
