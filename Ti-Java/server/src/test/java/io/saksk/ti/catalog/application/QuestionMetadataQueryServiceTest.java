package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionSubjectAssignmentScope;
import io.saksk.ti.catalog.application.port.QuestionCountQueryPort;
import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
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
        var service = new QuestionMetadataQueryService(port, unusedQuestionCountPort());

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
        var service = new QuestionMetadataQueryService(port, unusedQuestionCountPort());

        assertThatThrownBy(service::questionTypes).isSameAs(failure);
        assertThat(calls).hasValue(1);
    }

    @Test
    void returnsAnImmutableEmptyCatalogWhenThePortHasNoRows() {
        var service = new QuestionMetadataQueryService(List::of, unusedQuestionCountPort());

        assertThat(service.questionTypes().questionTypes()).isEmpty();
    }

    @Test
    void returnsZeroWithoutCallingThePortForAnExplicitlyEmptyCandidateScope() {
        AtomicInteger calls = new AtomicInteger();
        QuestionCountQueryPort port = query -> {
            calls.incrementAndGet();
            return 99;
        };
        var service = new QuestionMetadataQueryService(List::of, port);

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
        var service = new QuestionMetadataQueryService(List::of, port);
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
        var service = new QuestionMetadataQueryService(List::of, port);

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

    private static QuestionCountQueryPort unusedQuestionCountPort() {
        return query -> {
            throw new AssertionError("question-count port must not be called");
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
