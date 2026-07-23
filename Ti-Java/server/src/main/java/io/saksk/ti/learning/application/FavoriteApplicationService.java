package io.saksk.ti.learning.application;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionMetadataApplicationApi;
import io.saksk.ti.identity.api.SubjectAccessDecision;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import io.saksk.ti.learning.api.LearningWriteApplicationApi;
import io.saksk.ti.learning.api.ToggleFavoriteCommand;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import java.util.Objects;
import java.util.Optional;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

@Service
class FavoriteApplicationService implements LearningWriteApplicationApi {

    private final QuestionMetadataApplicationApi questions;
    private final SubjectAccessPolicyApi subjectAccess;
    private final FavoriteWriteTransaction transaction;

    FavoriteApplicationService(
            QuestionMetadataApplicationApi questions,
            SubjectAccessPolicyApi subjectAccess,
            FavoriteWriteTransaction transaction
    ) {
        this.questions = Objects.requireNonNull(questions, "questions");
        this.subjectAccess = Objects.requireNonNull(subjectAccess, "subjectAccess");
        this.transaction = Objects.requireNonNull(transaction, "transaction");
    }

    @Override
    public ToggleFavoriteResult toggleFavorite(ToggleFavoriteCommand command) {
        command = Objects.requireNonNull(command, "command");
        if (command.questionId() <= 0) {
            return ToggleFavoriteResult.questionNotFound();
        }

        Optional<QuestionCatalogRecordView> question =
                questions.findQuestionById(command.questionId());
        if (question.isEmpty()) {
            return ToggleFavoriteResult.questionNotFound();
        }

        SubjectAccessDecision access =
                subjectAccess.subjectAccess(command.viewer().identityId());
        if (!access.identityExists()) {
            return ToggleFavoriteResult.identityRejected();
        }
        Long subjectId = question.orElseThrow().subjectId();
        if (!access.administrator()
                && subjectId != null
                && (!isIntegerId(subjectId)
                        || access.restrictedSubjectIds().contains(subjectId.intValue()))) {
            return ToggleFavoriteResult.subjectAccessDenied();
        }

        try {
            return transaction.execute(
                    command.viewer().identityId(),
                    command.questionId(),
                    command.idempotencyKey(),
                    LearningWriteRequestFingerprints.favorite(
                            command.viewer().identityId(),
                            command.questionId()));
        } catch (DataIntegrityViolationException exception) {
            return ToggleFavoriteResult.mutationRejected();
        }
    }

    private static boolean isIntegerId(long value) {
        return value > 0 && value <= Integer.MAX_VALUE;
    }
}
