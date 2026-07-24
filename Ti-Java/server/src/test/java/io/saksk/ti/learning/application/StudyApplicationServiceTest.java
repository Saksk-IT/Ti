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
import io.saksk.ti.catalog.api.SubjectContextView;
import io.saksk.ti.catalog.api.SubjectMetadataApplicationApi;
import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.StudyLearnCommand;
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterCommand;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRating;
import io.saksk.ti.learning.api.StudyReviewRecordCommand;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyScopeInput;
import io.saksk.ti.learning.api.StudyWriteOutcome;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;

class StudyApplicationServiceTest {

    private final SubjectMetadataApplicationApi subjects =
            mock(SubjectMetadataApplicationApi.class);
    private final QuestionMetadataApplicationApi questions =
            mock(QuestionMetadataApplicationApi.class);
    private final PersonalBankQuestionFactsApi personalBank =
            mock(PersonalBankQuestionFactsApi.class);
    private final StudyWriteTransaction transaction =
            mock(StudyWriteTransaction.class);
    private final StudyApplicationService service =
            new StudyApplicationService(subjects, questions, personalBank, transaction);

    @Test
    void rejectsQuestionAndPublicScopeErrorsBeforeMutation() {
        assertThat(service.recordLearning(learn(0, publicScope("数学"))).outcome())
                .isEqualTo(StudyWriteOutcome.QUESTION_ID_INVALID);
        verifyNoInteractions(subjects, questions, personalBank, transaction);

        assertThat(service.recordLearning(learn(101, publicScope("  "))).outcome())
                .isEqualTo(StudyWriteOutcome.SUBJECT_INVALID);
        verifyNoInteractions(subjects, questions, personalBank, transaction);

        when(subjects.findSubjectByExactName("数学")).thenReturn(Optional.empty());
        assertThat(service.recordLearning(learn(101, publicScope("数学"))).outcome())
                .isEqualTo(StudyWriteOutcome.SUBJECT_NOT_FOUND);
        verifyNoInteractions(questions, personalBank, transaction);
    }

    @Test
    void publicResolutionUsesExactSubjectAndQuestionMembershipBeforeTransaction() {
        StudyLearnCommand command = learn(
                101,
                StudyScopeInput.legacy(" custom ", " 数学 ", null));
        when(subjects.findSubjectByExactName("数学"))
                .thenReturn(Optional.of(new SubjectContextView(201, "数学")));
        when(questions.findQuestionById(101))
                .thenReturn(Optional.of(question(101, 201L)));
        StudyWriteResult<StudyLearnView> expected =
                StudyWriteResult.success(
                        new StudyLearnView(1, false, Optional.empty()),
                        false);
        when(transaction.recordLearning(
                        org.mockito.ArgumentMatchers.eq(91L),
                        org.mockito.ArgumentMatchers.eq(101L),
                        org.mockito.ArgumentMatchers.eq(true),
                        org.mockito.ArgumentMatchers.argThat(
                                scope -> scope.source().equals("custom")
                                        && scope.scopeId() == 201),
                        org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(expected);

        assertThat(service.recordLearning(command)).isEqualTo(expected);
        var ordered = inOrder(subjects, questions, transaction);
        ordered.verify(subjects).findSubjectByExactName("数学");
        ordered.verify(questions).findQuestionById(101);
        ordered.verify(transaction).recordLearning(
                org.mockito.ArgumentMatchers.eq(91L),
                org.mockito.ArgumentMatchers.eq(101L),
                org.mockito.ArgumentMatchers.eq(true),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.same(command.idempotencyKey()),
                org.mockito.ArgumentMatchers.any(byte[].class));
        verifyNoInteractions(personalBank);
    }

    @Test
    void publicQuestionMustBelongToTheResolvedSubject() {
        when(subjects.findSubjectByExactName("数学"))
                .thenReturn(Optional.of(new SubjectContextView(201, "数学")));
        when(questions.findQuestionById(101))
                .thenReturn(Optional.of(question(101, 202L)));

        assertThat(service.recordLearning(learn(101, publicScope("数学"))).outcome())
                .isEqualTo(StudyWriteOutcome.QUESTION_OUT_OF_SCOPE);
        verifyNoInteractions(transaction);
    }

    @Test
    void personalBankResolutionSeparatesAccessFromQuestionMembership() {
        StudyScopeInput missingBank = StudyScopeInput.legacy("user_bank", null, null);
        assertThat(service.recordLearning(learn(101, missingBank)).outcome())
                .isEqualTo(StudyWriteOutcome.BANK_ID_INVALID);
        verifyNoInteractions(personalBank, transaction);

        StudyScopeInput bank = StudyScopeInput.legacy("user_bank", null, 301);
        when(personalBank.checkQuestionAccess(
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.eq(301)))
                .thenReturn(PersonalBankQuestionAccessResult.denied());
        assertThat(service.recordLearning(learn(101, bank)).outcome())
                .isEqualTo(StudyWriteOutcome.BANK_ACCESS_DENIED);
        verify(personalBank, never()).inspectQuestionMembership(
                org.mockito.ArgumentMatchers.anyInt(),
                org.mockito.ArgumentMatchers.anyList());

        when(personalBank.checkQuestionAccess(
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.eq(301)))
                .thenReturn(PersonalBankQuestionAccessResult.available());
        when(personalBank.inspectQuestionMembership(301, List.of(101)))
                .thenReturn(PersonalBankQuestionMembershipView.create(
                        301,
                        true,
                        List.of()));
        assertThat(service.recordLearning(learn(101, bank)).outcome())
                .isEqualTo(StudyWriteOutcome.QUESTION_OUT_OF_SCOPE);
        verifyNoInteractions(transaction);
    }

    @Test
    void allThreeOperationsDelegateAfterPersonalBankScopeProof() {
        StudyScopeInput bank = StudyScopeInput.legacy("user_bank", null, 301);
        allowBankQuestion();
        when(transaction.recordLearning(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyBoolean(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(StudyWriteResult.success(
                        new StudyLearnView(1, false, Optional.empty()),
                        false));
        when(transaction.recordReview(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(StudyWriteResult.success(
                        new StudyReviewRecordView(
                                1,
                                LocalDateTime.parse("2026-07-25T04:00:00")),
                        false));
        when(transaction.setReviewMastered(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyBoolean(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenReturn(StudyWriteResult.success(
                        new StudyReviewMasterView(true),
                        false));

        assertThat(service.recordLearning(learn(101, bank)).outcome())
                .isEqualTo(StudyWriteOutcome.SUCCESS);
        assertThat(service.recordReview(new StudyReviewRecordCommand(
                        viewer(),
                        101,
                        StudyReviewRating.KNOWN,
                        bank,
                        LearningWriteIdempotencyKey.absent())).outcome())
                .isEqualTo(StudyWriteOutcome.SUCCESS);
        assertThat(service.setReviewMastered(new StudyReviewMasterCommand(
                        viewer(),
                        101,
                        true,
                        bank,
                        LearningWriteIdempotencyKey.absent())).outcome())
                .isEqualTo(StudyWriteOutcome.SUCCESS);
    }

    @Test
    void constraintFailureMapsToSafeMutationOutcome() {
        when(subjects.findSubjectByExactName("数学"))
                .thenReturn(Optional.of(new SubjectContextView(201, "数学")));
        when(questions.findQuestionById(101))
                .thenReturn(Optional.of(question(101, 201L)));
        when(transaction.recordLearning(
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyLong(),
                        org.mockito.ArgumentMatchers.anyBoolean(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.any(byte[].class)))
                .thenThrow(new DataIntegrityViolationException("synthetic"));

        assertThat(service.recordLearning(learn(101, publicScope("数学"))).outcome())
                .isEqualTo(StudyWriteOutcome.MUTATION_REJECTED);
    }

    @Test
    void fingerprintsSeparateEveryNormalizedSemanticField() {
        StudyScopeInput publicMath = publicScope(" 数学 ");
        byte[] baseline = LearningWriteRequestFingerprints.studyLearn(
                91,
                101,
                true,
                publicMath);
        assertThat(baseline)
                .containsExactly(LearningWriteRequestFingerprints.studyLearn(
                        91, 101, true, publicScope("数学")))
                .isNotEqualTo(LearningWriteRequestFingerprints.studyLearn(
                        92, 101, true, publicMath))
                .isNotEqualTo(LearningWriteRequestFingerprints.studyLearn(
                        91, 102, true, publicMath))
                .isNotEqualTo(LearningWriteRequestFingerprints.studyLearn(
                        91, 101, false, publicMath))
                .isNotEqualTo(LearningWriteRequestFingerprints.studyLearn(
                        91,
                        101,
                        true,
                        StudyScopeInput.legacy("other", "数学", null)));
        assertThat(LearningWriteRequestFingerprints.studyReview(
                        91, 101, StudyReviewRating.KNOWN, publicMath))
                .isNotEqualTo(LearningWriteRequestFingerprints.studyReview(
                        91, 101, StudyReviewRating.UNKNOWN, publicMath));
    }

    private void allowBankQuestion() {
        when(personalBank.checkQuestionAccess(
                        org.mockito.ArgumentMatchers.any(),
                        org.mockito.ArgumentMatchers.eq(301)))
                .thenReturn(PersonalBankQuestionAccessResult.available());
        when(personalBank.inspectQuestionMembership(301, List.of(101)))
                .thenReturn(PersonalBankQuestionMembershipView.create(
                        301,
                        true,
                        List.of(101)));
    }

    private static StudyLearnCommand learn(long questionId, StudyScopeInput scope) {
        return new StudyLearnCommand(
                viewer(),
                questionId,
                true,
                scope,
                LearningWriteIdempotencyKey.absent());
    }

    private static StudyScopeInput publicScope(String subject) {
        return StudyScopeInput.legacy("public", subject, null);
    }

    private static AuthenticatedLearningViewer viewer() {
        return new AuthenticatedLearningViewer(91);
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
