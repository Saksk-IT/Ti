package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.SubjectCatalogRecordView;
import io.saksk.ti.catalog.api.SubjectInventorySummaryView;
import io.saksk.ti.catalog.application.port.SubjectDetailQueryPort;
import io.saksk.ti.catalog.application.port.SubjectInventoryQueryPort;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
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
        var service = new SubjectMetadataQueryService(port, unusedSubjectContextPort());

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
        assertThat(new SubjectMetadataQueryService(List::of, unusedSubjectContextPort())
                .listSubjectInventorySummaries()).isEmpty();

        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("inventory unavailable");
        var failing = new SubjectMetadataQueryService(
                () -> {
                    calls.incrementAndGet();
                    throw failure;
                },
                unusedSubjectContextPort());

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

    @Test
    void delegatesSubjectContextExactlyOnceAndPreservesTheRawProjection() {
        AtomicInteger calls = new AtomicInteger();
        AtomicLong received = new AtomicLong(Long.MIN_VALUE);
        var expected = new SubjectCatalogRecordView(0, "  ");
        SubjectDetailQueryPort port = subjectId -> {
            calls.incrementAndGet();
            received.set(subjectId);
            return Optional.of(expected);
        };
        var service = new SubjectMetadataQueryService(unusedSubjectInventoryPort(), port);

        assertThat(service.findSubjectById(0)).containsSame(expected);
        assertThat(received).hasValue(0L);
        assertThat(calls).hasValue(1);
    }

    @Test
    void preservesMissingAndFullLongRangeLookupsAndPropagatesPortFailures() {
        AtomicInteger calls = new AtomicInteger();
        AtomicLong received = new AtomicLong();
        var missing = new SubjectMetadataQueryService(
                unusedSubjectInventoryPort(),
                subjectId -> {
                    calls.incrementAndGet();
                    received.set(subjectId);
                    return Optional.empty();
                });

        assertThat(missing.findSubjectById(Long.MAX_VALUE)).isEmpty();
        assertThat(received).hasValue(Long.MAX_VALUE);
        assertThat(calls).hasValue(1);

        IllegalStateException failure = new IllegalStateException("subject context unavailable");
        var failing = new SubjectMetadataQueryService(
                unusedSubjectInventoryPort(),
                subjectId -> {
                    calls.incrementAndGet();
                    throw failure;
                });
        assertThatThrownBy(() -> failing.findSubjectById(1)).isSameAs(failure);
        assertThat(calls).hasValue(2);
    }

    @Test
    void rejectsNegativeSubjectIdsBeforeThePortAndDeclaresAReadOnlyTransaction()
            throws Exception {
        AtomicInteger calls = new AtomicInteger();
        var service = new SubjectMetadataQueryService(
                unusedSubjectInventoryPort(),
                subjectId -> {
                    calls.incrementAndGet();
                    return Optional.empty();
                });

        assertThatThrownBy(() -> service.findSubjectById(-1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("subjectId must not be negative");
        assertThatThrownBy(() -> service.findSubjectById(Long.MIN_VALUE))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("subjectId must not be negative");
        assertThat(calls).hasValue(0);

        Transactional transactional = SubjectMetadataQueryService.class
                .getDeclaredMethod("findSubjectById", long.class)
                .getAnnotation(Transactional.class);
        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }

    private static SubjectInventoryQueryPort unusedSubjectInventoryPort() {
        return () -> {
            throw new AssertionError("subject-inventory port must not be called");
        };
    }

    private static SubjectDetailQueryPort unusedSubjectContextPort() {
        return subjectId -> {
            throw new AssertionError("subject-context port must not be called");
        };
    }
}
