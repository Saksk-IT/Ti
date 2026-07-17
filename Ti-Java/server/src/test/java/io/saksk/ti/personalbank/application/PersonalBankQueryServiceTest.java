package io.saksk.ti.personalbank.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNullPointerException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.api.PersonalBankOwnedShareView;
import io.saksk.ti.personalbank.api.PersonalBankShareView;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsResult.Outcome;
import io.saksk.ti.personalbank.api.PersonalBankUsageStatsView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.SharedUserAccess;
import java.math.BigInteger;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class PersonalBankQueryServiceTest {

    private static final Instant FIXED_INSTANT = Instant.parse("2026-07-17T04:00:00Z");
    private static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");
    private static final LocalDateTime BEIJING_NOON =
            LocalDateTime.of(2026, 7, 17, 12, 0);

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
                port, unusedSharePort(), unusedOwnedSharePort(),
                unusedUsagePort(), fixedClock());

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
        }, unusedSharePort(), unusedOwnedSharePort(),
                unusedUsagePort(), fixedClock());

        assertThatNullPointerException()
                .isThrownBy(() -> service.listCategories(null))
                .withMessage("viewer");
        assertThat(calls).hasValue(0);
    }

    @Test
    void preservesEmptyResultsAndPropagatesPortFailuresWithoutRetryOrTranslation() {
        assertThat(new PersonalBankQueryService(
                userId -> List.of(), unusedSharePort(), unusedOwnedSharePort(),
                unusedUsagePort(), fixedClock())
                .listCategories(new AuthenticatedPersonalBankViewer(1)))
                .isEmpty();

        AtomicInteger calls = new AtomicInteger();
        IllegalStateException failure = new IllegalStateException("category inventory unavailable");
        var failing = new PersonalBankQueryService(userId -> {
            calls.incrementAndGet();
            throw failure;
        }, unusedSharePort(), unusedOwnedSharePort(),
                unusedUsagePort(), fixedClock());

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
                userId -> List.of(), port, unusedOwnedSharePort(),
                unusedUsagePort(), fixedClock());

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
                }, unusedOwnedSharePort(), unusedUsagePort(), fixedClock());

        assertThat(unavailable.findShares(new AuthenticatedPersonalBankViewer(9), -7))
                .isEmpty();
        assertThat(calls).hasValue(1);

        var presentEmpty = new PersonalBankQueryService(
                userId -> List.of(),
                (viewerId, bankId) -> Optional.of(List.of()),
                unusedOwnedSharePort(), unusedUsagePort(), fixedClock());
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
                }, unusedOwnedSharePort(), unusedUsagePort(), fixedClock());

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
                userId -> List.of(), unusedSharePort(), port,
                unusedUsagePort(), fixedClock());

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
                }, unusedUsagePort(), fixedClock());
        assertThatNullPointerException()
                .isThrownBy(() -> nullService.listOwnedShares(null))
                .withMessage("viewer");
        assertThat(nullCalls).hasValue(0);

        assertThat(new PersonalBankQueryService(
                userId -> List.of(), unusedSharePort(), viewerId -> List.of(),
                unusedUsagePort(), fixedClock())
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
                }, unusedUsagePort(), fixedClock());
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

    @Test
    void usageStatsPropagatesTheBankProbeFailureAndNeverRunsLaterQueries() {
        var port = new RecordingUsagePort();
        IllegalStateException failure = new IllegalStateException("bank probe unavailable");
        port.bankFailure = failure;

        assertThatThrownBy(() -> usageService(port).findUsageStats(
                new AuthenticatedPersonalBankViewer(41), 77))
                .isSameAs(failure);
        assertThat(port.calls).containsExactly("bank:77");
    }

    @Test
    void usageStatsReturnsNotFoundForMissingOrInactiveBanksAndShortCircuits() {
        var missing = new RecordingUsagePort();
        missing.bank = Optional.empty();
        assertThat(usageService(missing).findUsageStats(
                new AuthenticatedPersonalBankViewer(41), -7))
                .isEqualTo(PersonalBankUsageStatsResult.notFound());
        assertThat(missing.calls).containsExactly("bank:-7");

        for (Integer status : Arrays.asList(null, -1, 0, 2)) {
            var inactive = new RecordingUsagePort();
            inactive.bank = Optional.of(new BankAccess(77, 41L, true, status));

            assertThat(usageService(inactive).findUsageStats(
                    new AuthenticatedPersonalBankViewer(41), 77))
                    .as("status %s", status)
                    .isEqualTo(PersonalBankUsageStatsResult.notFound());
            assertThat(inactive.calls).containsExactly("bank:77");
        }
    }

    @Test
    void usageStatsReturnsForbiddenForInvalidOwnerOrMismatchedViewerAndShortCircuits() {
        for (Long ownerId : Arrays.asList(null, -1L, 0L, 42L)) {
            var port = new RecordingUsagePort();
            port.bank = Optional.of(new BankAccess(77, ownerId, false, 1));

            assertThat(usageService(port).findUsageStats(
                    new AuthenticatedPersonalBankViewer(41), 77))
                    .as("owner %s", ownerId)
                    .isEqualTo(PersonalBankUsageStatsResult.forbidden());
            assertThat(port.calls).containsExactly("bank:77");
        }
    }

    @Test
    void usageStatsDefensivelyRejectsNonpositiveViewerIdentitiesAfterTheProbe() {
        for (long viewerId : new long[]{-1L, 0L}) {
            AuthenticatedPersonalBankViewer viewer = mock(AuthenticatedPersonalBankViewer.class);
            when(viewer.identityId()).thenReturn(viewerId);
            var port = new RecordingUsagePort();
            port.bank = Optional.of(new BankAccess(77, 41L, false, 1));

            assertThat(usageService(port).findUsageStats(viewer, 77))
                    .as("viewer %s", viewerId)
                    .isEqualTo(PersonalBankUsageStatsResult.forbidden());
            assertThat(port.calls).containsExactly("bank:77");
        }
    }

    @Test
    void usageStatsPreservesBeijingExpiryCoercionAndLegacySetCounting() {
        var port = new RecordingUsagePort();
        port.bank = Optional.of(new BankAccess(77, 41L, null, 1));
        port.shared = List.of(
                new SharedUserAccess(41L, null),
                new SharedUserAccess(1L, BEIJING_NOON.minusNanos(1)),
                new SharedUserAccess(2L, BEIJING_NOON),
                new SharedUserAccess(3L, null),
                new SharedUserAccess(4L, ""),
                new SharedUserAccess(5L, 0),
                new SharedUserAccess(6L, false),
                new SharedUserAccess(7L, "not-a-date"),
                new SharedUserAccess(8L, OffsetDateTime.parse("2026-07-17T12:00:00+08:00")),
                new SharedUserAccess("9", BEIJING_NOON.plusNanos(1)),
                new SharedUserAccess("not-an-id", null),
                new SharedUserAccess(null, null),
                new SharedUserAccess(0L, null),
                new SharedUserAccess(-10L, null),
                new SharedUserAccess(3L, BEIJING_NOON.plusHours(1)),
                new SharedUserAccess(Long.MAX_VALUE, null),
                new SharedUserAccess("1_000", null),
                new SharedUserAccess("１２３４", null),
                new SharedUserAccess("1__2", null),
                new SharedUserAccess(new BigInteger("9223372036854775808"), null),
                new SharedUserAccess(Double.POSITIVE_INFINITY, null),
                new SharedUserAccess(13L, "2099-01-01"),
                new SharedUserAccess(14L, "2020-01-01"));
        port.publicIds = Arrays.asList(
                41L, 3L, 9L, 11L, "12", 0L, null, "not-an-id",
                -10L, -13L, 11L, Long.MAX_VALUE, "1_000",
                "１２３４", new BigInteger("9223372036854775808"),
                Double.NEGATIVE_INFINITY);

        Clock utcClock = Clock.fixed(FIXED_INSTANT, ZoneId.of("UTC"));
        PersonalBankUsageStatsResult result = usageService(port, utcClock).findUsageStats(
                new AuthenticatedPersonalBankViewer(41), 77);

        assertThat(result.outcome()).isEqualTo(Outcome.AVAILABLE);
        assertThat(result.view()).isEqualTo(new PersonalBankUsageStatsView(
                77, false, 41L, 1, 12, 10, 16, 15));
        assertThat(port.calls).containsExactly("bank:77", "shared:77", "public:77");
    }

    @Test
    void usageStatsDegradesEachOptionalQueryIndependentlyAndStillRunsTheOther() {
        var sharedFails = new RecordingUsagePort();
        sharedFails.bank = Optional.of(new BankAccess(77, 41L, true, 1));
        sharedFails.sharedFailure = new IllegalStateException("shared unavailable");
        sharedFails.publicIds = List.of(2L, 3L, 41L);
        assertThat(usageService(sharedFails).findUsageStats(
                new AuthenticatedPersonalBankViewer(41), 77).view())
                .isEqualTo(new PersonalBankUsageStatsView(
                        77, true, 41L, 1, 0, 2, 3, 2));
        assertThat(sharedFails.calls)
                .containsExactly("bank:77", "shared:77", "public:77");

        var publicFails = new RecordingUsagePort();
        publicFails.bank = Optional.of(new BankAccess(77, 41L, false, 1));
        publicFails.shared = List.of(
                new SharedUserAccess(2L, null),
                new SharedUserAccess(41L, null));
        publicFails.publicFailure = new IllegalArgumentException("public unavailable");
        assertThat(usageService(publicFails).findUsageStats(
                new AuthenticatedPersonalBankViewer(41), 77).view())
                .isEqualTo(new PersonalBankUsageStatsView(
                        77, false, 41L, 1, 1, 0, 2, 1));
        assertThat(publicFails.calls)
                .containsExactly("bank:77", "shared:77", "public:77");

        var bothFail = new RecordingUsagePort();
        bothFail.bank = Optional.of(new BankAccess(77, 41L, false, 1));
        bothFail.sharedFailure = new IllegalStateException("shared unavailable");
        bothFail.publicFailure = new IllegalStateException("public unavailable");
        assertThat(usageService(bothFail).findUsageStats(
                new AuthenticatedPersonalBankViewer(41), 77).view())
                .isEqualTo(new PersonalBankUsageStatsView(
                        77, false, 41L, 1, 0, 0, 1, 0));
        assertThat(bothFail.calls)
                .containsExactly("bank:77", "shared:77", "public:77");
    }

    @Test
    void usageStatsRejectsNullBeforeTheProbeAndDeclaresAReadOnlyTransaction()
            throws Exception {
        var port = new RecordingUsagePort();

        assertThatNullPointerException()
                .isThrownBy(() -> usageService(port).findUsageStats(null, 77))
                .withMessage("viewer");
        assertThat(port.calls).isEmpty();

        Transactional transactional = PersonalBankQueryService.class
                .getDeclaredMethod(
                        "findUsageStats", AuthenticatedPersonalBankViewer.class, int.class)
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

    private static PersonalBankUsageStatsQueryPort unusedUsagePort() {
        return new PersonalBankUsageStatsQueryPort() {
            @Override
            public Optional<BankAccess> findBank(int bankId) {
                throw new AssertionError("usage-stats bank probe must not be called");
            }

            @Override
            public List<SharedUserAccess> listSharedUsers(int bankId) {
                throw new AssertionError("usage-stats shared-users query must not be called");
            }

            @Override
            public List<Object> listPublicUserIds(int bankId) {
                throw new AssertionError("usage-stats public-users query must not be called");
            }
        };
    }

    private static Clock fixedClock() {
        return Clock.fixed(FIXED_INSTANT, BEIJING);
    }

    private static PersonalBankQueryService usageService(RecordingUsagePort usage) {
        return usageService(usage, fixedClock());
    }

    private static PersonalBankQueryService usageService(
            RecordingUsagePort usage,
            Clock clock
    ) {
        return new PersonalBankQueryService(
                userId -> List.of(), unusedSharePort(), unusedOwnedSharePort(),
                usage, clock);
    }

    private static final class RecordingUsagePort implements PersonalBankUsageStatsQueryPort {

        private Optional<BankAccess> bank = Optional.empty();
        private List<SharedUserAccess> shared = List.of();
        private List<Object> publicIds = List.of();
        private RuntimeException bankFailure;
        private RuntimeException sharedFailure;
        private RuntimeException publicFailure;
        private final List<String> calls = new ArrayList<>();

        @Override
        public Optional<BankAccess> findBank(int bankId) {
            calls.add("bank:" + bankId);
            if (bankFailure != null) {
                throw bankFailure;
            }
            return bank;
        }

        @Override
        public List<SharedUserAccess> listSharedUsers(int bankId) {
            calls.add("shared:" + bankId);
            if (sharedFailure != null) {
                throw sharedFailure;
            }
            return shared;
        }

        @Override
        public List<Object> listPublicUserIds(int bankId) {
            calls.add("public:" + bankId);
            if (publicFailure != null) {
                throw publicFailure;
            }
            return publicIds;
        }
    }
}
