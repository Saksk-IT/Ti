package io.saksk.ti.catalog.infrastructure.persistence;

import java.util.List;
import java.util.Optional;
import org.springframework.data.repository.Repository;
import org.springframework.transaction.annotation.Transactional;

/**
 * Deliberately extends the marker repository only and declares no save/delete operation.
 * Writes remain owned by the legacy runtime until the Phase 4 catalog cutover.
 */
@Transactional(readOnly = true)
public interface SubjectReadRepository extends Repository<SubjectReadEntity, Integer> {

    Optional<SubjectReadEntity> findById(Integer id);

    List<SubjectReadEntity> findAllByOrderByNameAsc();
}
