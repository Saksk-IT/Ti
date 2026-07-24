package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.SubjectContextView;
import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import io.saksk.ti.catalog.api.SubjectMetadataApplicationApi;
import io.saksk.ti.catalog.application.port.SubjectContextQueryPort;
import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class SubjectMetadataQueryService implements SubjectMetadataApplicationApi {

    private final SubjectInventoryQueryPort subjectInventory;
    private final SubjectContextQueryPort subjectContext;

    SubjectMetadataQueryService(
            SubjectInventoryQueryPort subjectInventory,
            SubjectContextQueryPort subjectContext
    ) {
        this.subjectInventory = subjectInventory;
        this.subjectContext = subjectContext;
    }

    @Override
    @Transactional(readOnly = true)
    public List<SubjectInventorySummaryView> listSubjectInventorySummaries() {
        return List.copyOf(subjectInventory.listSubjectInventorySummaries());
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<SubjectContextView> findSubjectById(long subjectId) {
        if (subjectId < 0) {
            throw new IllegalArgumentException("subjectId must not be negative");
        }
        return subjectContext.findSubjectById(subjectId);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<SubjectContextView> findSubjectByExactName(String subjectName) {
        subjectName = Objects.requireNonNull(subjectName, "subjectName").strip();
        if (subjectName.isEmpty()) {
            throw new IllegalArgumentException("subjectName must not be blank");
        }
        return subjectContext.findSubjectByExactName(subjectName);
    }
}
