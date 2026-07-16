package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class SubjectMetadataQueryServiceTest {

    @Test
    void delegatesExactlyOnceAndReturnsAnImmutableSnapshotWithoutFilteringRawRows() {
        AtomicInteger calls = new AtomicInteger();
        var unlocked = new SubjectInventorySummaryView(-7, "", null, 0);
        var locked = new SubjectInventorySummaryView(0, "锁定科目", true, 2);
        var portRows = new ArrayList<>(List.of(unlocked, locked));
        SubjectInventoryQueryPort port = () -> {
            calls.incrementAndGet();
            return portRows;
        };
        var service = new SubjectMetadataQueryService(port);

        List<SubjectInventorySummaryView> result = service.listSubjectInventorySummaries();

        assertThat(result).containsExactly(unlocked, locked);
        assertThat(result.getFirst()).isSameAs(unlocked);
        assertThat(calls).hasValue(1);
        portRows.clear();
        assertThat(result).containsExactly(unlocked, locked);
        assertThatThrownBy(() -> result.add(unlocked))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void preservesEmptyResultsAndPropagatesPortFailuresWithoutRetryOrTranslation() {
        assertThat(new SubjectMetadataQueryService(List::of)
                .listSubjectInventorySummaries()).isEmpty();

        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("inventory unavailable");
        var failing = new SubjectMetadataQueryService(() -> {
            calls.incrementAndGet();
            throw failure;
        });

        assertThatThrownBy(failing::listSubjectInventorySummaries).isSameAs(failure);
        assertThat(calls).hasValue(1);
    }

    @Test
    void declaresTheInventoryBoundaryAsAReadOnlyTransaction() throws Exception {
        Transactional transactional = SubjectMetadataQueryService.class
                .getDeclaredMethod("listSubjectInventorySummaries")
                .getAnnotation(Transactional.class);

        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }
}
