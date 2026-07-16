package io.saksk.ti.catalog.api;

import java.util.List;

/** Internal catalog boundary for raw subject metadata owned by the catalog module. */
public interface SubjectMetadataApplicationApi {

    List<SubjectInventorySummaryView> listSubjectInventorySummaries();
}
