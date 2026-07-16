package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.QuestionCatalogListQuery;
import io.saksk.ti.catalog.api.QuestionCatalogSummaryView;
import java.util.List;

/** Raw filtered question summaries owned by the catalog module. */
public interface QuestionSummaryQueryPort {

    List<QuestionCatalogSummaryView> listQuestionSummaries(QuestionCatalogListQuery query);
}
