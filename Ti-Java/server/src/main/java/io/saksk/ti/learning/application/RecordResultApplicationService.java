package io.saksk.ti.learning.application;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.identity.api.SubjectAccessDecision;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import io.saksk.ti.learning.api.RecordResultApplicationApi;
import io.saksk.ti.learning.api.RecordResultCommand;
import io.saksk.ti.learning.api.RecordResultResult;
import java.util.Objects;
import java.util.Optional;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

@Service
class RecordResultApplicationService implements RecordResultApplicationApi {

    private final QuestionMetadataApplicationApi questions;
    private final SubjectAccessPolicyApi subjectAccess;
    private final RecordResultWriteTransaction transaction;

    RecordResultApplicationService(
            QuestionMetadataApplicationApi questions,
            SubjectAccessPolicyApi subjectAccess,
            RecordResultWriteTransaction transaction
    ) {
        this.questions = Objects.requireNonNull(questions, "questions");
        this.subjectAccess = Objects.requireNonNull(subjectAccess, "subjectAccess");
        this.transaction = Objects.requireNonNull(transaction, "transaction");
    }

    @Override
    public RecordResultResult recordResult(RecordResultCommand command) {
        command = Objects.requireNonNull(command, "command");
        if (command.questionId() <= 0L) {
            return RecordResultResult.questionNotFound();
        }

        Optional<QuestionCatalogRecordView> question =
                questions.findQuestionById(command.questionId());
        if (question.isEmpty()) {
            return RecordResultResult.questionNotFound();
        }

        SubjectAccessDecision access =
                subjectAccess.subjectAccess(command.viewer().identityId());
        if (!access.identityExists()) {
            return RecordResultResult.identityRejected();
        }
        Long subjectId = question.orElseThrow().subjectId();
        if (!access.administrator()
                && subjectId != null
                && (!isIntegerId(subjectId)
                        || access.restrictedSubjectIds().contains(subjectId.intValue()))) {
            return RecordResultResult.subjectAccessDenied();
        }

        try {
            return transaction.execute(
                    command.viewer().identityId(),
                    access.administrator(),
                    command.questionId(),
                    command.correct(),
                    command.clearMistakeOnCorrect(),
                    command.quizLimitPolicy(),
                    command.idempotencyKey(),
                    LearningWriteRequestFingerprints.recordResult(
                            command.viewer().identityId(),
                            command.questionId(),
                            command.correct(),
                            command.clearMistakeOnCorrect()));
        } catch (DataIntegrityViolationException exception) {
            return RecordResultResult.mutationRejected();
        }
    }

    private static boolean isIntegerId(long value) {
        return value > 0L && value <= Integer.MAX_VALUE;
    }
}
