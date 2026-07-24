package io.saksk.ti.learning.application;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.catalog.api.SubjectContextView;
import io.saksk.ti.catalog.api.SubjectMetadataApplicationApi;
import io.saksk.ti.learning.api.StudyLearnCommand;
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterCommand;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRecordCommand;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyScopeInput;
import io.saksk.ti.learning.api.StudyWriteApplicationApi;
import io.saksk.ti.learning.api.StudyWriteOutcome;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

@Service
class StudyApplicationService implements StudyWriteApplicationApi {

    private final SubjectMetadataApplicationApi subjects;
    private final QuestionMetadataApplicationApi questions;
    private final PersonalBankQuestionFactsApi personalBankQuestions;
    private final StudyWriteTransaction transaction;

    StudyApplicationService(
            SubjectMetadataApplicationApi subjects,
            QuestionMetadataApplicationApi questions,
            PersonalBankQuestionFactsApi personalBankQuestions,
            StudyWriteTransaction transaction
    ) {
        this.subjects = Objects.requireNonNull(subjects, "subjects");
        this.questions = Objects.requireNonNull(questions, "questions");
        this.personalBankQuestions =
                Objects.requireNonNull(personalBankQuestions, "personalBankQuestions");
        this.transaction = Objects.requireNonNull(transaction, "transaction");
    }

    @Override
    public StudyWriteResult<StudyLearnView> recordLearning(StudyLearnCommand command) {
        command = Objects.requireNonNull(command, "command");
        Resolution resolution = resolve(
                command.viewer().identityId(),
                command.questionId(),
                command.scope());
        if (!resolution.successful()) {
            return StudyWriteResult.rejected(resolution.rejection());
        }
        ResolvedScope scope = resolution.scope().orElseThrow();
        try {
            return transaction.recordLearning(
                    command.viewer().identityId(),
                    command.questionId(),
                    command.correct(),
                    scope,
                    command.idempotencyKey(),
                    LearningWriteRequestFingerprints.studyLearn(
                            command.viewer().identityId(),
                            command.questionId(),
                            command.correct(),
                            command.scope()));
        } catch (DataIntegrityViolationException exception) {
            return StudyWriteResult.rejected(StudyWriteOutcome.MUTATION_REJECTED);
        }
    }

    @Override
    public StudyWriteResult<StudyReviewRecordView> recordReview(
            StudyReviewRecordCommand command
    ) {
        command = Objects.requireNonNull(command, "command");
        Resolution resolution = resolve(
                command.viewer().identityId(),
                command.questionId(),
                command.scope());
        if (!resolution.successful()) {
            return rejected(resolution);
        }
        ResolvedScope scope = resolution.scope().orElseThrow();
        try {
            return transaction.recordReview(
                    command.viewer().identityId(),
                    command.questionId(),
                    command.rating(),
                    scope,
                    command.idempotencyKey(),
                    LearningWriteRequestFingerprints.studyReview(
                            command.viewer().identityId(),
                            command.questionId(),
                            command.rating(),
                            command.scope()));
        } catch (DataIntegrityViolationException exception) {
            return StudyWriteResult.rejected(StudyWriteOutcome.MUTATION_REJECTED);
        }
    }

    @Override
    public StudyWriteResult<StudyReviewMasterView> setReviewMastered(
            StudyReviewMasterCommand command
    ) {
        command = Objects.requireNonNull(command, "command");
        Resolution resolution = resolve(
                command.viewer().identityId(),
                command.questionId(),
                command.scope());
        if (!resolution.successful()) {
            return rejected(resolution);
        }
        ResolvedScope scope = resolution.scope().orElseThrow();
        try {
            return transaction.setReviewMastered(
                    command.viewer().identityId(),
                    command.questionId(),
                    command.mastered(),
                    scope,
                    command.idempotencyKey(),
                    LearningWriteRequestFingerprints.studyReviewMaster(
                            command.viewer().identityId(),
                            command.questionId(),
                            command.mastered(),
                            command.scope()));
        } catch (DataIntegrityViolationException exception) {
            return StudyWriteResult.rejected(StudyWriteOutcome.MUTATION_REJECTED);
        }
    }

    private Resolution resolve(
            long actorId,
            long questionId,
            StudyScopeInput input
    ) {
        if (questionId <= 0L) {
            return Resolution.rejected(StudyWriteOutcome.QUESTION_ID_INVALID);
        }
        if (input.personalBank()) {
            return resolvePersonalBank(actorId, questionId, input);
        }
        return resolvePublic(questionId, input);
    }

    private Resolution resolvePersonalBank(
            long actorId,
            long questionId,
            StudyScopeInput input
    ) {
        Integer bankId = input.bankId().orElse(null);
        if (bankId == null || bankId == 0) {
            return Resolution.rejected(StudyWriteOutcome.BANK_ID_INVALID);
        }
        if (bankId < 0 || questionId > Integer.MAX_VALUE) {
            return Resolution.rejected(
                    bankId < 0
                            ? StudyWriteOutcome.BANK_ACCESS_DENIED
                            : StudyWriteOutcome.QUESTION_OUT_OF_SCOPE);
        }

        PersonalBankQuestionAccessResult access =
                personalBankQuestions.checkQuestionAccess(
                        new AuthenticatedPersonalBankViewer(actorId),
                        bankId);
        if (access.outcome() != PersonalBankQuestionAccessResult.Outcome.AVAILABLE) {
            return Resolution.rejected(StudyWriteOutcome.BANK_ACCESS_DENIED);
        }
        PersonalBankQuestionMembershipView membership =
                personalBankQuestions.inspectQuestionMembership(
                        bankId,
                        List.of(Math.toIntExact(questionId)));
        if (!membership.bankExists()
                || !membership.existingQuestionIds().contains(Math.toIntExact(questionId))) {
            return Resolution.rejected(StudyWriteOutcome.QUESTION_OUT_OF_SCOPE);
        }
        return Resolution.resolved(new ResolvedScope(input.source(), bankId));
    }

    private Resolution resolvePublic(long questionId, StudyScopeInput input) {
        String subjectName = input.subject().orElse("").strip();
        if (subjectName.isEmpty()) {
            return Resolution.rejected(StudyWriteOutcome.SUBJECT_INVALID);
        }
        Optional<SubjectContextView> subject = subjects.findSubjectByExactName(subjectName);
        if (subject.isEmpty()) {
            return Resolution.rejected(StudyWriteOutcome.SUBJECT_NOT_FOUND);
        }
        Optional<QuestionCatalogRecordView> question = questions.findQuestionById(questionId);
        Long actualSubjectId = question.map(QuestionCatalogRecordView::subjectId).orElse(null);
        if (actualSubjectId == null
                || actualSubjectId.longValue() != subject.orElseThrow().id()) {
            return Resolution.rejected(StudyWriteOutcome.QUESTION_OUT_OF_SCOPE);
        }
        return Resolution.resolved(
                new ResolvedScope(input.source(), subject.orElseThrow().id()));
    }

    private static <T> StudyWriteResult<T> rejected(Resolution resolution) {
        return StudyWriteResult.rejected(resolution.rejection());
    }

    record ResolvedScope(String source, int scopeId) {
        ResolvedScope {
            source = Objects.requireNonNull(source, "source");
            if (source.isBlank() || scopeId <= 0) {
                throw new IllegalArgumentException("Resolved study scope must be valid");
            }
        }
    }

    private record Resolution(
            Optional<ResolvedScope> scope,
            Optional<StudyWriteOutcome> rejectionOutcome
    ) {
        private Resolution {
            scope = Objects.requireNonNull(scope, "scope");
            rejectionOutcome = Objects.requireNonNull(rejectionOutcome, "rejectionOutcome");
            if (scope.isPresent() == rejectionOutcome.isPresent()) {
                throw new IllegalArgumentException(
                        "Resolution must carry exactly one scope or rejection");
            }
        }

        static Resolution resolved(ResolvedScope scope) {
            return new Resolution(Optional.of(scope), Optional.empty());
        }

        static Resolution rejected(StudyWriteOutcome outcome) {
            if (outcome == StudyWriteOutcome.SUCCESS) {
                throw new IllegalArgumentException("Resolution rejection must not be SUCCESS");
            }
            return new Resolution(Optional.empty(), Optional.of(outcome));
        }

        boolean successful() {
            return scope.isPresent();
        }

        StudyWriteOutcome rejection() {
            return rejectionOutcome.orElseThrow();
        }
    }
}
