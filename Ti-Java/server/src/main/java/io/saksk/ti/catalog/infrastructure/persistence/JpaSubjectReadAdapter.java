package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.application.port.SubjectReadPort;
import io.saksk.ti.catalog.domain.SubjectSnapshot;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/** JPA adapter for the Phase 2 legacy-schema compatibility probe. */
@Component
@Transactional(readOnly = true)
class JpaSubjectReadAdapter implements SubjectReadPort {

    private final SubjectReadRepository subjects;

    JpaSubjectReadAdapter(SubjectReadRepository subjects) {
        this.subjects = subjects;
    }

    @Override
    public Optional<SubjectSnapshot> findById(int subjectId) {
        if (subjectId <= 0) {
            return Optional.empty();
        }
        return subjects.findById(subjectId).map(SubjectReadEntity::toSnapshot);
    }

    @Override
    public List<SubjectSnapshot> findAllByName() {
        return subjects.findAllByOrderByNameAsc().stream()
                .map(SubjectReadEntity::toSnapshot)
                .toList();
    }
}
