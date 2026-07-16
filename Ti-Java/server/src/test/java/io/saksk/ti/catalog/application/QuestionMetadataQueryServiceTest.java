package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionCatalogListQuery;
import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionCatalogSummaryView;
import io.saksk.ti.catalog.api.QuestionExportQuery;
import io.saksk.ti.catalog.api.QuestionExportRecordView;
import io.saksk.ti.catalog.api.QuestionSubjectAssignmentScope;
import io.saksk.ti.catalog.application.port.QuestionCountQueryPort;
import io.saksk.ti.catalog.application.port.QuestionDetailQueryPort;
import io.saksk.ti.catalog.application.port.QuestionExportQueryPort;
import io.saksk.ti.catalog.application.port.QuestionSummaryQueryPort;
import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class QuestionMetadataQueryServiceTest {

    @Test
    void filtersOnlyNullAndPreservesExactBlankValuesWhileDeduplicatingAndSorting() {
        AtomicInteger calls = new AtomicInteger();
        QuestionTypeQueryPort port = () -> {
            calls.incrementAndGet();
            return new ArrayList<>(Arrays.asList(
                    "简答题",
                    "",
                    "  ",
                    "判断题",
                    "single_choice",
                    null,
                    "判断题",
                    "boolean"));
        };
        var service = new QuestionMetadataQueryService(
                port,
                unusedQuestionCountPort(),
                unusedQuestionDetailPort(),
                unusedQuestionSummaryPort(),
                unusedQuestionExportPort());

        var result = service.questionTypes();

        assertThat(result.questionTypes()).containsExactly(
                "", "  ", "boolean", "single_choice", "判断题", "简答题");
        assertThat(calls).hasValue(1);
        assertThatThrownBy(() -> result.questionTypes().add("essay"))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void propagatesPortFailureWithoutRetryOrTranslation() {
        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("database unavailable");
        QuestionTypeQueryPort port = () -> {
            calls.incrementAndGet();
            throw failure;
        };
        var service = new QuestionMetadataQueryService(
                port,
                unusedQuestionCountPort(),
                unusedQuestionDetailPort(),
                unusedQuestionSummaryPort(),
                unusedQuestionExportPort());

        assertThatThrownBy(service::questionTypes).isSameAs(failure);
        assertThat(calls).hasValue(1);
    }

    @Test
    void returnsAnImmutableEmptyCatalogWhenThePortHasNoRows() {
        var service = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                unusedQuestionDetailPort(),
                unusedQuestionSummaryPort(),
                unusedQuestionExportPort());

        assertThat(service.questionTypes().questionTypes()).isEmpty();
    }

    @Test
    void returnsZeroWithoutCallingThePortForAnExplicitlyEmptyCandidateScope() {
        AtomicInteger calls = new AtomicInteger();
        QuestionCountQueryPort port = query -> {
            calls.incrementAndGet();
            return 99;
        };
        var service = new QuestionMetadataQueryService(
                List::of, port, unusedQuestionDetailPort(), unusedQuestionSummaryPort(),
                unusedQuestionExportPort());

        long result = service.countQuestions(countQuery(Optional.of(List.of())));

        assertThat(result).isZero();
        assertThat(calls).hasValue(0);
    }

    @Test
    void delegatesAbsentAndNonemptyCandidateScopesExactlyOnce() {
        AtomicInteger calls = new AtomicInteger();
        AtomicReference<QuestionCatalogCountQuery> received = new AtomicReference<>();
        QuestionCountQueryPort port = query -> {
            calls.incrementAndGet();
            received.set(query);
            return 17;
        };
        var service = new QuestionMetadataQueryService(
                List::of, port, unusedQuestionDetailPort(), unusedQuestionSummaryPort(),
                unusedQuestionExportPort());
        var query = new QuestionCatalogCountQuery(
                Optional.of("数学"),
                Optional.of("single_choice"),
                QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT,
                Set.of(4, 2),
                Optional.of(List.of(9L, 3L)));

        assertThat(service.countQuestions(query)).isEqualTo(17);
        assertThat(received).hasValue(query);
        assertThat(calls).hasValue(1);

        var unrestricted = countQuery(Optional.empty());
        assertThat(service.countQuestions(unrestricted)).isEqualTo(17);
        assertThat(received).hasValue(unrestricted);
        assertThat(calls).hasValue(2);
    }

    @Test
    void propagatesCountPortFailureWithoutRetryOrTranslation() {
        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("count unavailable");
        QuestionCountQueryPort port = query -> {
            calls.incrementAndGet();
            throw failure;
        };
        var service = new QuestionMetadataQueryService(
                List::of, port, unusedQuestionDetailPort(), unusedQuestionSummaryPort(),
                unusedQuestionExportPort());

        assertThatThrownBy(() -> service.countQuestions(countQuery(Optional.empty())))
                .isSameAs(failure);
        assertThat(calls).hasValue(1);
    }

    @Test
    void declaresTheCountBoundaryAsAReadOnlyTransaction() throws Exception {
        Transactional transactional = QuestionMetadataQueryService.class
                .getDeclaredMethod("countQuestions", QuestionCatalogCountQuery.class)
                .getAnnotation(Transactional.class);

        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }

    @Test
    void delegatesAQuestionDetailLookupExactlyOnceWithoutProjectingRawFields() {
        AtomicInteger calls = new AtomicInteger();
        AtomicReference<Long> received = new AtomicReference<>();
        var expected = new QuestionCatalogRecordView(
                42,
                null,
                "unknown",
                "raw content",
                "{malformed",
                "answer]",
                null,
                "legacy,tags",
                null,
                "legacy.png",
                null,
                null,
                null,
                null,
                null);
        QuestionDetailQueryPort port = questionId -> {
            calls.incrementAndGet();
            received.set(questionId);
            return Optional.of(expected);
        };
        var service = new QuestionMetadataQueryService(
                List::of, unusedQuestionCountPort(), port, unusedQuestionSummaryPort(),
                unusedQuestionExportPort());

        assertThat(service.findQuestionById(42)).containsSame(expected);
        assertThat(received).hasValue(42L);
        assertThat(calls).hasValue(1);
    }

    @Test
    void preservesAnEmptyQuestionDetailAndPropagatesPortFailure() {
        var missing = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                questionId -> Optional.empty(),
                unusedQuestionSummaryPort(),
                unusedQuestionExportPort());
        assertThat(missing.findQuestionById(0)).isEmpty();

        IllegalStateException failure = new IllegalStateException("detail unavailable");
        var failing = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                questionId -> {
                    throw failure;
                },
                unusedQuestionSummaryPort(),
                unusedQuestionExportPort());
        assertThatThrownBy(() -> failing.findQuestionById(1)).isSameAs(failure);
    }

    @Test
    void rejectsNegativeQuestionIdsBeforeThePortAndDeclaresAReadOnlyTransaction()
            throws Exception {
        AtomicInteger calls = new AtomicInteger();
        var service = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                questionId -> {
                    calls.incrementAndGet();
                    return Optional.empty();
                },
                unusedQuestionSummaryPort(),
                unusedQuestionExportPort());

        assertThatThrownBy(() -> service.findQuestionById(-1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(calls).hasValue(0);

        Transactional transactional = QuestionMetadataQueryService.class
                .getDeclaredMethod("findQuestionById", long.class)
                .getAnnotation(Transactional.class);
        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }

    @Test
    void delegatesQuestionSummaryQueryExactlyOnceAndReturnsAnImmutableRawList() {
        AtomicInteger calls = new AtomicInteger();
        AtomicReference<QuestionCatalogListQuery> received = new AtomicReference<>();
        var raw = new QuestionCatalogSummaryView(
                0,
                -7L,
                "",
                "raw content",
                null,
                "{not-json-tags",
                "[not-json-image",
                null,
                LocalDateTime.of(2026, 7, 16, 12, 13, 14));
        var portRows = new ArrayList<>(List.of(raw));
        QuestionSummaryQueryPort port = query -> {
            calls.incrementAndGet();
            received.set(query);
            return portRows;
        };
        var service = new QuestionMetadataQueryService(
                List::of, unusedQuestionCountPort(), unusedQuestionDetailPort(), port,
                unusedQuestionExportPort());
        var query = new QuestionCatalogListQuery(Optional.of(-7), Optional.of(""));

        List<QuestionCatalogSummaryView> result = service.listQuestionSummaries(query);

        assertThat(result).containsExactly(raw);
        assertThat(result.getFirst()).isSameAs(raw);
        assertThat(received).hasValue(query);
        assertThat(calls).hasValue(1);
        portRows.clear();
        assertThat(result).containsExactly(raw);
        assertThatThrownBy(() -> result.add(raw))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void rejectsNullSummaryQueryBeforeThePortAndPropagatesPortFailures() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        QuestionSummaryQueryPort counting = query -> {
            calls.incrementAndGet();
            return List.of();
        };
        var guarded = new QuestionMetadataQueryService(
                List::of, unusedQuestionCountPort(), unusedQuestionDetailPort(), counting,
                unusedQuestionExportPort());

        assertThatThrownBy(() -> guarded.listQuestionSummaries(null))
                .isInstanceOf(NullPointerException.class)
                .hasMessage("query");
        assertThat(calls).hasValue(0);

        IllegalStateException failure = new IllegalStateException("summary unavailable");
        var failing = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                unusedQuestionDetailPort(),
                query -> {
                    throw failure;
                },
                unusedQuestionExportPort());
        var query = new QuestionCatalogListQuery(Optional.empty(), Optional.empty());
        assertThatThrownBy(() -> failing.listQuestionSummaries(query)).isSameAs(failure);

        Transactional transactional = QuestionMetadataQueryService.class
                .getDeclaredMethod("listQuestionSummaries", QuestionCatalogListQuery.class)
                .getAnnotation(Transactional.class);
        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }

    @Test
    void delegatesQuestionExportExactlyOnceAndReturnsAnImmutableRawSnapshot() {
        AtomicInteger calls = new AtomicInteger();
        AtomicReference<QuestionExportQuery> received = new AtomicReference<>();
        var raw = new QuestionExportRecordView(
                -1,
                -7L,
                null,
                null,
                "",
                "{not-json",
                "true",
                null,
                0,
                "42");
        var portRows = new ArrayList<>(List.of(raw));
        QuestionExportQueryPort port = query -> {
            calls.incrementAndGet();
            received.set(query);
            return portRows;
        };
        var service = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                unusedQuestionDetailPort(),
                unusedQuestionSummaryPort(),
                port);
        var query = new QuestionExportQuery(Optional.of(-7));

        List<QuestionExportRecordView> result = service.listQuestionExportRecords(query);

        assertThat(result).containsExactly(raw);
        assertThat(result.getFirst()).isSameAs(raw);
        assertThat(received).hasValue(query);
        assertThat(calls).hasValue(1);
        portRows.clear();
        assertThat(result).containsExactly(raw);
        assertThatThrownBy(() -> result.add(raw))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void rejectsNullExportQueryBeforeThePortAndPropagatesPortFailures() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        QuestionExportQueryPort counting = query -> {
            calls.incrementAndGet();
            return List.of();
        };
        var guarded = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                unusedQuestionDetailPort(),
                unusedQuestionSummaryPort(),
                counting);

        assertThatThrownBy(() -> guarded.listQuestionExportRecords(null))
                .isInstanceOf(NullPointerException.class)
                .hasMessage("query");
        assertThat(calls).hasValue(0);

        IllegalStateException failure = new IllegalStateException("export unavailable");
        var failing = new QuestionMetadataQueryService(
                List::of,
                unusedQuestionCountPort(),
                unusedQuestionDetailPort(),
                unusedQuestionSummaryPort(),
                query -> {
                    throw failure;
                });
        var query = new QuestionExportQuery(Optional.empty());
        assertThatThrownBy(() -> failing.listQuestionExportRecords(query)).isSameAs(failure);

        Transactional transactional = QuestionMetadataQueryService.class
                .getDeclaredMethod("listQuestionExportRecords", QuestionExportQuery.class)
                .getAnnotation(Transactional.class);
        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }

    private static QuestionCountQueryPort unusedQuestionCountPort() {
        return query -> {
            throw new AssertionError("question-count port must not be called");
        };
    }

    private static QuestionDetailQueryPort unusedQuestionDetailPort() {
        return questionId -> {
            throw new AssertionError("question-detail port must not be called");
        };
    }

    private static QuestionSummaryQueryPort unusedQuestionSummaryPort() {
        return query -> {
            throw new AssertionError("question-summary port must not be called");
        };
    }

    private static QuestionExportQueryPort unusedQuestionExportPort() {
        return query -> {
            throw new AssertionError("question-export port must not be called");
        };
    }

    private static QuestionCatalogCountQuery countQuery(Optional<List<Long>> candidates) {
        return new QuestionCatalogCountQuery(
                Optional.empty(),
                Optional.empty(),
                QuestionSubjectAssignmentScope.INCLUDE_UNASSIGNED,
                Set.of(),
                candidates);
    }
}
