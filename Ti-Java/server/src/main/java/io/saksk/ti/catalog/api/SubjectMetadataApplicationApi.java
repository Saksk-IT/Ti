package io.saksk.ti.catalog.api;

import java.util.List;
import java.util.Optional;

/** Internal catalog boundary for raw subject metadata owned by the catalog module. */
public interface SubjectMetadataApplicationApi {

    List<SubjectInventorySummaryView> listSubjectInventorySummaries();

    Optional<SubjectContextView> findSubjectById(long subjectId);

    Optional<SubjectContextView> findSubjectByExactName(String subjectName);
}
