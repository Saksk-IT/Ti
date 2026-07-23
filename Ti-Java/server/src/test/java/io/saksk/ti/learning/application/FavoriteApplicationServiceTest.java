package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.identity.api.SubjectAccessDecision;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.ToggleFavoriteCommand;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

class FavoriteApplicationServiceTest {

    private final QuestionMetadataApplicationApi questions =
            mock(QuestionMetadataApplicationApi.class);
    private final SubjectAccessPolicyApi access = mock(SubjectAccessPolicyApi.class);
    private final FavoriteWriteTransaction transaction = mock(FavoriteWriteTransaction.class);
    private final FavoriteApplicationService service =
            new FavoriteApplicationService(questions, access, transaction);

    @Test
    void rejectsInvalidOrMissingQuestionsBeforeIdentityAndMutation() {
        assertThat(service.toggleFavorite(command(0)).outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.QUESTION_NOT_FOUND);
        verifyNoInteractions(questions, access, transaction);

        when(questions.findQuestionById(101L)).thenReturn(Optional.empty());
        assertThat(service.toggleFavorite(command(101)).outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.QUESTION_NOT_FOUND);
        verifyNoInteractions(access, transaction);
    }

    @Test
    void rejectsMissingIdentityAndRestrictedSubjectsBeforeTheLearningTransaction() {
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, 201L)));
        when(access.subjectAccess(91L)).thenReturn(SubjectAccessDecision.missingIdentity());
        assertThat(service.toggleFavorite(command(101)).outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.IDENTITY_REJECTED);
        verifyNoInteractions(transaction);

        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, false, Set.of(201)));
        assertThat(service.toggleFavorite(command(101)).outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.SUBJECT_ACCESS_DENIED);
        verifyNoInteractions(transaction);
    }

    @Test
    void completesCrossModuleReadsBeforeEnteringTheLearningTransaction() {
        ToggleFavoriteCommand command = command(101);
        ToggleFavoriteResult expected = ToggleFavoriteResult.success(true, false);
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, 201L)));
        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, false, Set.of()));
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.eq(91L),
                        org.mockito.ArgumentMatchers.eq(101L),
                        org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(expected);

        assertThat(service.toggleFavorite(command)).isEqualTo(expected);
        var ordered = inOrder(questions, access, transaction);
        ordered.verify(questions).findQuestionById(101L);
        ordered.verify(access).subjectAccess(91L);
        ordered.verify(transaction).execute(
                org.mockito.ArgumentMatchers.eq(91L),
                org.mockito.ArgumentMatchers.eq(101L),
                org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                org.mockito.ArgumentMatchers.any(byte[].class));
    }

    @Test
    void administratorsIgnoreRestrictionsAndMutationConstraintFailuresRemainCompatible() {
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, 201L)));
        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, true, Set.of(201)));
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.eq(91L),
                        org.mockito.ArgumentMatchers.eq(101L),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenThrow(new DataIntegrityViolationException("synthetic favorite conflict"));

        assertThat(service.toggleFavorite(command(101)).outcome())
                .isEqualTo(ToggleFavoriteResult.Outcome.MUTATION_REJECTED);
    }

    @Test
    void subjectlessQuestionDoesNotInventARestriction() {
        when(questions.findQuestionById(101L))
                .thenReturn(Optional.of(question(101L, null)));
        when(access.subjectAccess(91L))
                .thenReturn(new SubjectAccessDecision(true, false, Set.of(201)));
        when(transaction.execute(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(ToggleFavoriteResult.success(false, false));

        assertThat(service.toggleFavorite(command(101)).favorite()).contains(false);
        verify(transaction).execute(
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.anyLong(),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any(byte[].class));
        verify(access).subjectAccess(91L);
        verify(questions, never()).findQuestionById(-1L);
    }

    private static ToggleFavoriteCommand command(long questionId) {
        return new ToggleFavoriteCommand(
                new AuthenticatedLearningViewer(91L),
                questionId,
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
