package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionEditApplicationApi;
import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditResult;
import java.util.Objects;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;

@Service
class QuestionEditApplicationService implements QuestionEditApplicationApi {

    private final QuestionEditWriteTransaction transaction;

    QuestionEditApplicationService(QuestionEditWriteTransaction transaction) {
        this.transaction = Objects.requireNonNull(transaction, "transaction");
    }

    @Override
    public QuestionEditResult editQuestion(QuestionEditCommand command) {
        command = Objects.requireNonNull(command, "command");
        if (!command.editor().mayEditQuestions()) {
            return QuestionEditResult.forbidden();
        }
        try {
            return transaction.execute(
                    command,
                    QuestionEditRequestFingerprint.of(command));
        } catch (DataIntegrityViolationException exception) {
            return QuestionEditResult.mutationRejected();
        }
    }
}
