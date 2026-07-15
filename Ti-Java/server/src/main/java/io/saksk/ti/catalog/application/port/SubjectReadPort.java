package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.domain.SubjectSnapshot;
import java.util.List;
import java.util.Optional;

/** Catalog-owned, read-only access to the legacy {@code subjects} table. */
public interface SubjectReadPort {

    Optional<SubjectSnapshot> findById(int subjectId);

    List<SubjectSnapshot> findAllByName();
}
