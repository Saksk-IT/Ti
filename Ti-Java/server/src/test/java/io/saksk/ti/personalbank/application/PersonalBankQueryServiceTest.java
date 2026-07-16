package io.saksk.ti.personalbank.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class PersonalBankQueryServiceTest {

    @Test
    void delegatesTheViewerIdentityExactlyOnceAndReturnsAnImmutableRawSnapshot() {
        AtomicInteger calls = new AtomicInteger();
        AtomicLong receivedUserId = new AtomicLong(Long.MIN_VALUE);
        var first = new PersonalBankCategoryView(-7, 41, "", null, null, null, null, 0);
        var second = new PersonalBankCategoryView(0, 41, "分类 🧪", "", -2, null, null, 2);
        var portRows = new ArrayList<>(List.of(first, second));
        PersonalBankCategoryQueryPort port = userId -> {
            calls.incrementAndGet();
            receivedUserId.set(userId);
            return portRows;
        };
        var service = new PersonalBankQueryService(port);

        List<PersonalBankCategoryView> result =
                service.listCategories(new AuthenticatedPersonalBankViewer(41));

        assertThat(result).containsExactly(first, second);
        assertThat(result.getFirst()).isSameAs(first);
        assertThat(receivedUserId).hasValue(41);
        assertThat(calls).hasValue(1);
        portRows.clear();
        assertThat(result).containsExactly(first, second);
        assertThatThrownBy(() -> result.add(first))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void rejectsANullViewerBeforeCallingThePort() {
        AtomicInteger calls = new AtomicInteger();
        var service = new PersonalBankQueryService(userId -> {
            calls.incrementAndGet();
            return List.of();
        });

        assertThatNullPointerException()
                .isThrownBy(() -> service.listCategories(null))
                .withMessage("viewer");
        assertThat(calls).hasValue(0);
    }

    @Test
    void preservesEmptyResultsAndPropagatesPortFailuresWithoutRetryOrTranslation() {
        assertThat(new PersonalBankQueryService(userId -> List.of())
                .listCategories(new AuthenticatedPersonalBankViewer(1)))
                .isEmpty();

        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("category inventory unavailable");
        var failing = new PersonalBankQueryService(userId -> {
            calls.incrementAndGet();
            throw failure;
        });

        assertThatThrownBy(() -> failing.listCategories(new AuthenticatedPersonalBankViewer(2)))
                .isSameAs(failure);
        assertThat(calls).hasValue(1);
    }

    @Test
    void declaresTheCategoryBoundaryAsAReadOnlyTransaction() throws Exception {
        Transactional transactional = PersonalBankQueryService.class
                .getDeclaredMethod("listCategories", AuthenticatedPersonalBankViewer.class)
                .getAnnotation(Transactional.class);

        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }
}
