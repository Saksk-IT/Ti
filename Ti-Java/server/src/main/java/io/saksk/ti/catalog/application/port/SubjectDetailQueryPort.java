package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.SubjectCatalogRecordView;
import java.util.Optional;

/** Raw primary-key subject lookup owned by the catalog module. */
public interface SubjectDetailQueryPort {

    Optional<SubjectCatalogRecordView> findSubjectById(long subjectId);
}
