package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import java.util.List;

/** Raw subject inventory summaries owned by the catalog module. */
public interface SubjectInventoryQueryPort {

    List<SubjectInventorySummaryView> listSubjectInventorySummaries();
}
