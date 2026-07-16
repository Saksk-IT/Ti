package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.api.SubjectContextView;
import java.util.Optional;

/** Raw primary-key subject-context lookup owned by the catalog module. */
public interface SubjectContextQueryPort {

    Optional<SubjectContextView> findSubjectById(long subjectId);
}
