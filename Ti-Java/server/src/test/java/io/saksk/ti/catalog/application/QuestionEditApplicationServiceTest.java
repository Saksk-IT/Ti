package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditIdempotencyKey;
import io.saksk.ti.catalog.api.QuestionEditResult;
import io.saksk.ti.catalog.api.QuestionEditorIdentity;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

class QuestionEditApplicationServiceTest {

    private final QuestionEditWriteTransaction transaction =
            mock(QuestionEditWriteTransaction.class);
    private final QuestionEditApplicationService service =
            new QuestionEditApplicationService(transaction);

    @Test
    void deniesRegularUserBeforeEnteringCatalogTransaction() {
        QuestionEditCommand command = command(
                new QuestionEditorIdentity(91, false, false));

        assertThat(service.editQuestion(command).outcome())
                .isEqualTo(QuestionEditResult.Outcome.FORBIDDEN);
        verify(transaction, never()).execute(any(), any());
    }

    @Test
    void acceptsEitherAdministratorRoleAndUsesStableFingerprint() {
        QuestionEditCommand administrator = command(
                new QuestionEditorIdentity(91, true, false));
        QuestionEditCommand subjectAdministrator = command(
                new QuestionEditorIdentity(92, false, true));
        when(transaction.execute(any(), any())).thenReturn(
                QuestionEditResult.questionNotFound(false));

        assertThat(service.editQuestion(administrator).outcome())
                .isEqualTo(QuestionEditResult.Outcome.QUESTION_NOT_FOUND);
        assertThat(service.editQuestion(subjectAdministrator).outcome())
                .isEqualTo(QuestionEditResult.Outcome.QUESTION_NOT_FOUND);
        verify(transaction).execute(
                org.mockito.ArgumentMatchers.same(administrator),
                org.mockito.ArgumentMatchers.argThat(value ->
                        java.util.Arrays.equals(
                                value,
                                QuestionEditRequestFingerprint.of(administrator))));
        verify(transaction).execute(
                org.mockito.ArgumentMatchers.same(subjectAdministrator),
                org.mockito.ArgumentMatchers.argThat(value ->
                        java.util.Arrays.equals(
                                value,
                                QuestionEditRequestFingerprint.of(subjectAdministrator))));
    }

    @Test
    void fingerprintSeparatesActorPathPresenceAndPayloadValues() {
        QuestionEditCommand baseline = command(
                new QuestionEditorIdentity(91, true, false));
        QuestionEditCommand otherActor = new QuestionEditCommand(
                new QuestionEditorIdentity(92, true, false),
                baseline.questionId(),
                baseline.content(),
                baseline.questionType(),
                baseline.answer(),
                baseline.explanation(),
                baseline.optionsJsonOrText(),
                baseline.idempotencyKey());
        QuestionEditCommand absentContent = new QuestionEditCommand(
                baseline.editor(),
                baseline.questionId(),
                Optional.empty(),
                baseline.questionType(),
                baseline.answer(),
                baseline.explanation(),
                baseline.optionsJsonOrText(),
                baseline.idempotencyKey());
        QuestionEditCommand emptyContent = new QuestionEditCommand(
                baseline.editor(),
                baseline.questionId(),
                Optional.of(""),
                baseline.questionType(),
                baseline.answer(),
                baseline.explanation(),
                baseline.optionsJsonOrText(),
                baseline.idempotencyKey());

        assertThat(QuestionEditRequestFingerprint.of(baseline))
                .containsExactly(QuestionEditRequestFingerprint.of(baseline))
                .isNotEqualTo(QuestionEditRequestFingerprint.of(otherActor))
                .isNotEqualTo(QuestionEditRequestFingerprint.of(absentContent));
        assertThat(QuestionEditRequestFingerprint.of(absentContent))
                .isNotEqualTo(QuestionEditRequestFingerprint.of(emptyContent));
    }

    @Test
    void databaseConstraintFailureBecomesSafeMutationRejection() {
        when(transaction.execute(any(), any()))
                .thenThrow(new DataIntegrityViolationException("synthetic"));

        assertThat(service.editQuestion(command(
                        new QuestionEditorIdentity(91, true, false))).outcome())
                .isEqualTo(QuestionEditResult.Outcome.MUTATION_REJECTED);
    }

    private static QuestionEditCommand command(QuestionEditorIdentity editor) {
        return new QuestionEditCommand(
                editor,
                93001,
                Optional.of("题干"),
                Optional.of("选择题"),
                Optional.of("A"),
                Optional.of("解析"),
                Optional.of("[\"甲\",\"乙\"]"),
                QuestionEditIdempotencyKey.of("question-edit-key"));
    }
}
