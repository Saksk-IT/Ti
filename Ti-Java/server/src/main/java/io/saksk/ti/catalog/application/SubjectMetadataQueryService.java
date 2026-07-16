package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.SubjectCatalogRecordView;
import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import io.saksk.ti.catalog.api.SubjectMetadataApplicationApi;
import io.saksk.ti.catalog.application.port.SubjectDetailQueryPort;
import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class SubjectMetadataQueryService implements SubjectMetadataApplicationApi {

    private final SubjectInventoryQueryPort subjectInventory;
    private final SubjectDetailQueryPort subjectDetail;

    SubjectMetadataQueryService(
            SubjectInventoryQueryPort subjectInventory,
            SubjectDetailQueryPort subjectDetail
    ) {
        this.subjectInventory = subjectInventory;
        this.subjectDetail = subjectDetail;
    }

    @Override
    @Transactional(readOnly = true)
    public List<SubjectInventorySummaryView> listSubjectInventorySummaries() {
        return List.copyOf(subjectInventory.listSubjectInventorySummaries());
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<SubjectCatalogRecordView> findSubjectById(long subjectId) {
        if (subjectId < 0) {
            throw new IllegalArgumentException("subjectId must not be negative");
        }
        return subjectDetail.findSubjectById(subjectId);
    }
}
