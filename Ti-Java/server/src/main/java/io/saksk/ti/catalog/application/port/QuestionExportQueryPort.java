package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.QuestionExportQuery;
import io.saksk.ti.catalog.api.QuestionExportRecordView;
import java.util.List;

/** Raw question export snapshot query owned by the catalog module. */
public interface QuestionExportQueryPort {

    List<QuestionExportRecordView> listQuestionExportRecords(QuestionExportQuery query);
}
