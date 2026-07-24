package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditResult;
import io.saksk.ti.catalog.application.port.CatalogQuestionEditReceiptPort;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort;

public final class QuestionEditWriteTransactionTestAccess {

    private QuestionEditWriteTransactionTestAccess() {
    }

    public static QuestionEditResult execute(
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts,
            QuestionEditCommand command,
            byte[] requestSha256
    ) {
        return new QuestionEditWriteTransaction(state, receipts)
                .execute(command, requestSha256);
    }
}
