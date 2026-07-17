package io.saksk.ti.personalbank.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.api.PersonalBankOwnedShareView;
import io.saksk.ti.personalbank.api.PersonalBankShareView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
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
        var service = new PersonalBankQueryService(
                port, unusedSharePort(), unusedOwnedSharePort());

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
        }, unusedSharePort(), unusedOwnedSharePort());

        assertThatNullPointerException()
                .isThrownBy(() -> service.listCategories(null))
                .withMessage("viewer");
        assertThat(calls).hasValue(0);
    }

    @Test
    void preservesEmptyResultsAndPropagatesPortFailuresWithoutRetryOrTranslation() {
        assertThat(new PersonalBankQueryService(
                userId -> List.of(), unusedSharePort(), unusedOwnedSharePort())
                .listCategories(new AuthenticatedPersonalBankViewer(1)))
                .isEmpty();

        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("category inventory unavailable");
        var failing = new PersonalBankQueryService(userId -> {
            calls.incrementAndGet();
            throw failure;
        }, unusedSharePort(), unusedOwnedSharePort());

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

    @Test
    void preservesShareAvailabilityRawOrderAndImmutableSnapshot() {
        AtomicInteger calls = new AtomicInteger();
        AtomicLong receivedViewerId = new AtomicLong(Long.MIN_VALUE);
        AtomicInteger receivedBankId = new AtomicInteger(Integer.MIN_VALUE);
        var first = new PersonalBankShareView(
                -2, 0, 42L, null, null, null, null, null, -1, null, null);
        var second = new PersonalBankShareView(
                7, 0, 43L, "", " token ", "unexpected-value",
                LocalDateTime.of(2026, 7, 17, 12, 0), 0, -2, false,
                LocalDateTime.of(2026, 7, 17, 11, 0));
        var portRows = new ArrayList<>(List.of(first, second));
        PersonalBankShareQueryPort port = (viewerId, bankId) -> {
            calls.incrementAndGet();
            receivedViewerId.set(viewerId);
            receivedBankId.set(bankId);
            return Optional.of(portRows);
        };
        var service = new PersonalBankQueryService(
                userId -> List.of(), port, unusedOwnedSharePort());

        var result = service.findShares(new AuthenticatedPersonalBankViewer(41), 0);

        assertThat(result).isPresent();
        assertThat(result.orElseThrow().shares()).containsExactly(first, second);
        assertThat(receivedViewerId).hasValue(41L);
        assertThat(receivedBankId).hasValue(0);
        assertThat(calls).hasValue(1);
        portRows.clear();
        assertThat(result.orElseThrow().shares()).containsExactly(first, second);
        assertThatThrownBy(() -> result.orElseThrow().shares().add(first))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void distinguishesUnavailableFromPresentEmptyAndAllowsSignedBankIds() {
        AtomicInteger calls = new AtomicInteger();
        var unavailable = new PersonalBankQueryService(
                userId -> List.of(),
                (viewerId, bankId) -> {
                    calls.incrementAndGet();
                    assertThat(viewerId).isEqualTo(9L);
                    assertThat(bankId).isEqualTo(-7);
                    return Optional.empty();
                }, unusedOwnedSharePort());

        assertThat(unavailable.findShares(new AuthenticatedPersonalBankViewer(9), -7))
                .isEmpty();
        assertThat(calls).hasValue(1);

        var presentEmpty = new PersonalBankQueryService(
                userId -> List.of(),
                (viewerId, bankId) -> Optional.of(List.of()),
                unusedOwnedSharePort());
        assertThat(presentEmpty.findShares(new AuthenticatedPersonalBankViewer(9), 0))
                .isPresent()
                .get()
                .extracting(view -> view.shares())
                .isEqualTo(List.of());
    }

    @Test
    void rejectsANullShareViewerAndPropagatesPortFailuresExactlyOnce() {
        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("share inventory unavailable");
        var service = new PersonalBankQueryService(
                userId -> List.of(),
                (viewerId, bankId) -> {
                    calls.incrementAndGet();
                    throw failure;
                }, unusedOwnedSharePort());

        assertThatNullPointerException()
                .isThrownBy(() -> service.findShares(null, 1))
                .withMessage("viewer");
        assertThat(calls).hasValue(0);
        assertThatThrownBy(() -> service.findShares(
                        new AuthenticatedPersonalBankViewer(1), Integer.MAX_VALUE))
                .isSameAs(failure);
        assertThat(calls).hasValue(1);
    }

    @Test
    void declaresTheShareBoundaryAsAReadOnlyTransaction() throws Exception {
        Transactional transactional = PersonalBankQueryService.class
                .getDeclaredMethod(
                        "findShares", AuthenticatedPersonalBankViewer.class, int.class)
                .getAnnotation(Transactional.class);

        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }

    @Test
    void delegatesOwnedSharesWithTheFullViewerIdentityAndDefensivelyCopiesRows() {
        AtomicInteger calls = new AtomicInteger();
        AtomicLong receivedViewerId = new AtomicLong(Long.MIN_VALUE);
        var first = new PersonalBankOwnedShareView(
                -2, 0, (long) Integer.MAX_VALUE + 1L,
                null, " token ", "unexpected-value", null, -1, -2, null, null,
                " 题库 🧪 ");
        var second = new PersonalBankOwnedShareView(
                7, 8, (long) Integer.MAX_VALUE + 1L,
                "", "", "", LocalDateTime.of(2020, 1, 1, 0, 0),
                0, 0, false, LocalDateTime.of(2026, 7, 17, 12, 0), "");
        var portRows = new ArrayList<>(List.of(first, second));
        PersonalBankOwnedShareQueryPort port = viewerId -> {
            calls.incrementAndGet();
            receivedViewerId.set(viewerId);
            return portRows;
        };
        var service = new PersonalBankQueryService(
                userId -> List.of(), unusedSharePort(), port);

        List<PersonalBankOwnedShareView> result = service.listOwnedShares(
                new AuthenticatedPersonalBankViewer((long) Integer.MAX_VALUE + 1L));

        assertThat(result).containsExactly(first, second);
        assertThat(receivedViewerId).hasValue((long) Integer.MAX_VALUE + 1L);
        assertThat(calls).hasValue(1);
        portRows.clear();
        assertThat(result).containsExactly(first, second);
        assertThatThrownBy(() -> result.add(first))
                .isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void ownedSharesRejectsNullPreservesEmptyAndPropagatesFailuresExactlyOnce() {
        AtomicInteger nullCalls = new AtomicInteger();
        var nullService = new PersonalBankQueryService(
                userId -> List.of(),
                unusedSharePort(),
                viewerId -> {
                    nullCalls.incrementAndGet();
                    return List.of();
                });
        assertThatNullPointerException()
                .isThrownBy(() -> nullService.listOwnedShares(null))
                .withMessage("viewer");
        assertThat(nullCalls).hasValue(0);

        assertThat(new PersonalBankQueryService(
                userId -> List.of(), unusedSharePort(), viewerId -> List.of())
                .listOwnedShares(new AuthenticatedPersonalBankViewer(1)))
                .isEmpty();

        AtomicInteger failureCalls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException(
                "owned share inventory unavailable");
        var failing = new PersonalBankQueryService(
                userId -> List.of(),
                unusedSharePort(),
                viewerId -> {
                    failureCalls.incrementAndGet();
                    throw failure;
                });
        assertThatThrownBy(() -> failing.listOwnedShares(
                new AuthenticatedPersonalBankViewer(2)))
                .isSameAs(failure);
        assertThat(failureCalls).hasValue(1);
    }

    @Test
    void declaresTheOwnedShareBoundaryAsAReadOnlyTransaction() throws Exception {
        Transactional transactional = PersonalBankQueryService.class
                .getDeclaredMethod(
                        "listOwnedShares", AuthenticatedPersonalBankViewer.class)
                .getAnnotation(Transactional.class);

        assertThat(transactional).isNotNull();
        assertThat(transactional.readOnly()).isTrue();
    }

    private static PersonalBankShareQueryPort unusedSharePort() {
        return (viewerId, bankId) -> {
            throw new AssertionError("share port must not be called");
        };
    }

    private static PersonalBankOwnedShareQueryPort unusedOwnedSharePort() {
        return viewerId -> {
            throw new AssertionError("owned-share port must not be called");
        };
    }
}
