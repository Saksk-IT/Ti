package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.catalog.application.port.QuestionTypeQueryPort;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

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
        var service = new QuestionMetadataQueryService(port);

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
        var service = new QuestionMetadataQueryService(port);

        assertThatThrownBy(service::questionTypes).isSameAs(failure);
        assertThat(calls).hasValue(1);
    }

    @Test
    void returnsAnImmutableEmptyCatalogWhenThePortHasNoRows() {
        var service = new QuestionMetadataQueryService(List::of);

        assertThat(service.questionTypes().questionTypes()).isEmpty();
    }
}
