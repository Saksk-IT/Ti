package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.identity.api.SubjectAccessDecision;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.QuizLimitPolicy;
import io.saksk.ti.learning.api.RecordResultAction;
import io.saksk.ti.learning.api.RecordResultCommand;
import io.saksk.ti.learning.api.RecordResultResult;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

class RecordResultApplicationServiceTest {

    private final QuestionMetadataApplicationApi questions =
            mock(QuestionMetadataApplicationApi.class);
    private final SubjectAccessPolicyApi access =
            mock(SubjectAccessPolicyApi.class);
    private final RecordResultWriteTransaction transaction =
            mock(RecordResultWriteTransaction.class);
    private final RecordResultApplicationService service =
            new RecordResultApplicationService(questions, access, transaction);

    @Test
    void rejectsInvalidOrMissingQuestionsBeforeIdentityAndMutation() {
        assertThat(service.recordResult(command(0L)).outcome())
                .isEqualTo(RecordResultResult.Outcome.QUESTION_NOT_FOUND);
        verifyNoInteractions(questions, access, transaction);

        when(questions.findQuestionById(101L)).thenReturn(Optional.empty());
        assertThat(service.recordResult(command(101L)).outcome())
                .isEqualTo(RecordResultResult.Outcome.QUESTION_NOT_FOUND);
        verifyNoInteractions(access, transaction);
    }

    @Test
    void rejectsMissingIdentityAndRestrictedSubjectBeforeTransaction() {
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, 201L)));
        when(access.subjectAccess(91L))
                .thenReturn(SubjectAccessDecision.missingIdentity());
        assertThat(service.recordResult(command(101L)).outcome())
                .isEqualTo(RecordResultResult.Outcome.IDENTITY_REJECTED);
        verifyNoInteractions(transaction);

        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, false, Set.of(201)));
        assertThat(service.recordResult(command(101L)).outcome())
                .isEqualTo(RecordResultResult.Outcome.SUBJECT_ACCESS_DENIED);
        verifyNoInteractions(transaction);
    }

    @Test
    void completesCrossModuleReadsBeforeEnteringLearningTransaction() {
        RecordResultCommand command = command(101L);
        RecordResultResult expected = RecordResultResult.success(
                RecordResultAction.ADDED_MISTAKE,
                false);
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, 201L)));
        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, false, Set.of()));
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.eq(91L),
                        org.mockito.ArgumentMatchers.eq(false),
                        org.mockito.ArgumentMatchers.eq(101L),
                        org.mockito.ArgumentMatchers.eq(false),
                        org.mockito.ArgumentMatchers.eq(true),
                        org.mockito.ArgumentMatchers.same(command.quizLimitPolicy()),
                        org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(expected);

        assertThat(service.recordResult(command)).isEqualTo(expected);
        var ordered = inOrder(questions, access, transaction);
        ordered.verify(questions).findQuestionById(101L);
        ordered.verify(access).subjectAccess(91L);
        ordered.verify(transaction).execute(
                org.mockito.ArgumentMatchers.eq(91L),
                org.mockito.ArgumentMatchers.eq(false),
                org.mockito.ArgumentMatchers.eq(101L),
                org.mockito.ArgumentMatchers.eq(false),
                org.mockito.ArgumentMatchers.eq(true),
                org.mockito.ArgumentMatchers.same(command.quizLimitPolicy()),
                org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                org.mockito.ArgumentMatchers.any(byte[].class));
    }

    @Test
    void administratorBypassesRestrictionsButStillCarriesTrustedPolicy() {
        RecordResultCommand command = command(101L);
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, 201L)));
        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, true, Set.of(201)));
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.eq(91L),
                        org.mockito.ArgumentMatchers.eq(true),
                        org.mockito.ArgumentMatchers.eq(101L),
                        org.mockito.ArgumentMatchers.eq(false),
                        org.mockito.ArgumentMatchers.eq(true),
                        org.mockito.ArgumentMatchers.same(command.quizLimitPolicy()),
                        org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(RecordResultResult.success(
                        RecordResultAction.ADDED_MISTAKE,
                        false));

        assertThat(service.recordResult(command).outcome())
                .isEqualTo(RecordResultResult.Outcome.SUCCESS);
    }

    @Test
    void databaseConstraintFailureBecomesTheSafeLegacyServerErrorOutcome() {
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, null)));
        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, false, Set.of()));
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyBoolean(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyBoolean(),
                        org.mockito.ArgumentMatchers.anyBoolean(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenThrow(new DataIntegrityViolationException(
                        "synthetic record-result failure"));

        assertThat(service.recordResult(command(101L)).outcome())
                .isEqualTo(RecordResultResult.Outcome.MUTATION_REJECTED);
    }

    @Test
    void requestFingerprintSeparatesActorsAndEverySemanticBodyField() {
        assertThat(LearningWriteRequestFingerprints.recordResult(
                        91L, 101L, false, true))
                .containsExactly(LearningWriteRequestFingerprints.recordResult(
                        91L, 101L, false, true))
                .isNotEqualTo(LearningWriteRequestFingerprints.recordResult(
                        92L, 101L, false, true))
                .isNotEqualTo(LearningWriteRequestFingerprints.recordResult(
                        91L, 102L, false, true))
                .isNotEqualTo(LearningWriteRequestFingerprints.recordResult(
                        91L, 101L, true, true))
                .isNotEqualTo(LearningWriteRequestFingerprints.recordResult(
                        91L, 101L, false, false));
    }

    private static RecordResultCommand command(long questionId) {
        return new RecordResultCommand(
                new AuthenticatedLearningViewer(91L),
                questionId,
                false,
                true,
                new QuizLimitPolicy(true, 60),
                LearningWriteIdempotencyKey.absent());
    }

    private static QuestionCatalogRecordView question(long id, Long subjectId) {
        return new QuestionCatalogRecordView(
                id,
                subjectId,
                "single_choice",
                "content",
                "[]",
                "[]",
                null,
                "[]",
                1,
                null,
                null,
                null,
                null,
                null,
                null);
    }
}
