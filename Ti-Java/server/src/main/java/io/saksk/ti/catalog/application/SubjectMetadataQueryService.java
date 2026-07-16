package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import io.saksk.ti.catalog.api.SubjectMetadataApplicationApi;
import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class SubjectMetadataQueryService implements SubjectMetadataApplicationApi {

    private final SubjectInventoryQueryPort subjectInventory;

    SubjectMetadataQueryService(SubjectInventoryQueryPort subjectInventory) {
        this.subjectInventory = subjectInventory;
    }

    @Override
    @Transactional(readOnly = true)
    public List<SubjectInventorySummaryView> listSubjectInventorySummaries() {
        return List.copyOf(subjectInventory.listSubjectInventorySummaries());
    }
}
