package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import java.util.Optional;

/** Raw primary-key question lookup owned by the catalog module. */
public interface QuestionDetailQueryPort {

    Optional<QuestionCatalogRecordView> findQuestionById(long questionId);
}
