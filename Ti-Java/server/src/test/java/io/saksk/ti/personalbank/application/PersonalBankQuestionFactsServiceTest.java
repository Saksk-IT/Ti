package io.saksk.ti.personalbank.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.QuestionFacts;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.QuestionMembership;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.RawTypeCount;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.ShareGrant;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

class PersonalBankQuestionFactsServiceTest {

    private static final int BANK_ID = 7_101;
    private static final long VIEWER_ID = 7_001L;
    private static final LocalDateTime BEIJING_NOON =
            LocalDateTime.of(2026, 7, 17, 12, 0);
    private static final Clock FIXED_CLOCK = Clock.fixed(
            Instant.parse("2026-07-17T04:00:00Z"), ZoneOffset.UTC);

    @Test
    void rejectsCrossBankShareGrant() {
        var port = new RecordingPort();
        port.access.add(Optional.of(privateBank(List.of(grant(
                91,
                BANK_ID,
                1,
                81,
                BANK_ID + 1,
                "read",
                true,
                BEIJING_NOON.plusMinutes(1))))));

        PersonalBankQuestionAccessResult result = service(port).checkQuestionAccess(
                new AuthenticatedPersonalBankViewer(VIEWER_ID), BANK_ID);

        assertThat(result).isEqualTo(PersonalBankQuestionAccessResult.denied());
        assertThat(port.calls).containsExactly("access:" + BANK_ID);
    }

    @Test
    void selectsDeterministicValidSameBankGrant() {
        var port = new RecordingPort();
        port.access.add(Optional.of(privateBank(List.of(
                grant(31, BANK_ID, 1, 21, BANK_ID, "read", true,
                        BEIJING_NOON.minusSeconds(1)),
                grant(32, BANK_ID, 1, 22, BANK_ID, "unknown", true,
                        BEIJING_NOON.plusDays(1)),
                grant(33, BANK_ID, 1, 23, BANK_ID, "copy", true,
                        BEIJING_NOON.plusNanos(1)),
                grant(34, BANK_ID, 1, 24, BANK_ID, "read", false, null)))));

        assertThat(service(port).checkQuestionAccess(
                new AuthenticatedPersonalBankViewer(VIEWER_ID), BANK_ID))
                .isEqualTo(PersonalBankQuestionAccessResult.available());

        var equalOnly = new RecordingPort();
        equalOnly.access.add(Optional.of(privateBank(List.of(grant(
                41, BANK_ID, 1, 31, BANK_ID, "read", true, BEIJING_NOON)))));
        assertThat(service(equalOnly).checkQuestionAccess(
                new AuthenticatedPersonalBankViewer(VIEWER_ID), BANK_ID))
                .isEqualTo(PersonalBankQuestionAccessResult.denied());
    }

    @Test
    void rejectsUnknownAndNullSharePermissions() {
        var unknown = new RecordingPort();
        unknown.access.add(Optional.of(privateBank(List.of(grant(
                42,
                BANK_ID,
                1,
                32,
                BANK_ID,
                "unknown",
                true,
                BEIJING_NOON.plusDays(1))))));
        assertThat(service(unknown).checkQuestionAccess(
                new AuthenticatedPersonalBankViewer(VIEWER_ID), BANK_ID))
                .isEqualTo(PersonalBankQuestionAccessResult.denied());

        var nullPermission = new RecordingPort();
        nullPermission.access.add(Optional.of(privateBank(List.of(grant(
                43,
                BANK_ID,
                1,
                33,
                BANK_ID,
                null,
                true,
                BEIJING_NOON.plusDays(1))))));
        assertThat(service(nullPermission).checkQuestionAccess(
                new AuthenticatedPersonalBankViewer(VIEWER_ID), BANK_ID))
                .isEqualTo(PersonalBankQuestionAccessResult.denied());
    }

    @Test
    void rechecksAccessForEveryFactsCall() {
        var port = new RecordingPort();
        port.access.add(Optional.of(privateBank(List.of(grant(
                51, BANK_ID, 1, 41, BANK_ID, "read", true, null)))));
        port.access.add(Optional.empty());
        port.facts = new QuestionFacts(3L, List.of(
                new RawTypeCount(Optional.of("single_choice"), 2L),
                new RawTypeCount(Optional.empty(), 1L)));
        var selection = new PersonalBankQuestionSelection(
                BANK_ID,
                Optional.empty(),
                Optional.of(List.of(8_102, 8_101, 8_102)));

        PersonalBankQuestionFactsResult first = service(port).summarizeQuestions(
                new AuthenticatedPersonalBankViewer(VIEWER_ID), selection);
        PersonalBankQuestionFactsResult second = service(port).summarizeQuestions(
                new AuthenticatedPersonalBankViewer(VIEWER_ID), selection);

        assertThat(first.outcome()).isEqualTo(PersonalBankQuestionFactsResult.Outcome.AVAILABLE);
        assertThat(first.data().orElseThrow().total()).isEqualTo(3L);
        assertThat(first.data().orElseThrow().rawTypes())
                .extracting(type -> type.rawType().orElse(null), type -> type.count())
                .containsExactly(
                        org.assertj.core.groups.Tuple.tuple("single_choice", 2L),
                        org.assertj.core.groups.Tuple.tuple(null, 1L));
        assertThat(second).isEqualTo(PersonalBankQuestionFactsResult.denied());
        assertThat(port.calls).containsExactly(
                "access:" + BANK_ID,
                "summary:" + BANK_ID,
                "access:" + BANK_ID);
        assertThat(port.selections).singleElement().satisfies(received ->
                assertThat(received.candidateQuestionIds().orElseThrow())
                        .containsExactly(8_101, 8_102));
    }

    @Test
    void presentEmptyCandidatesStillRecheckAccessAndSkipTheSummaryQuery() {
        var port = new RecordingPort();
        port.access.add(Optional.of(new BankAccess(
                BANK_ID, VIEWER_ID, false, 1, List.of())));

        PersonalBankQuestionFactsResult result = service(port).summarizeQuestions(
                new AuthenticatedPersonalBankViewer(VIEWER_ID),
                new PersonalBankQuestionSelection(
                        BANK_ID, Optional.empty(), Optional.of(List.of())));

        assertThat(result.data().orElseThrow().total()).isZero();
        assertThat(result.data().orElseThrow().rawTypes()).isEmpty();
        assertThat(port.calls).containsExactly("access:" + BANK_ID);
    }

    @Test
    void membershipNormalizesIdsAndBindsTheDigestToTheReturnedSubset() {
        var port = new RecordingPort();
        port.membership = new QuestionMembership(true, List.of(8_102, 8_101, 8_102));

        var membership = service(port).inspectQuestionMembership(
                BANK_ID, List.of(8_103, 8_102, 8_101, 8_103));

        assertThat(port.receivedMembershipIds).containsExactly(8_101, 8_102, 8_103);
        assertThat(membership.existingQuestionIds()).containsExactly(8_101, 8_102);
        assertThat(membership.membershipDigest()).matches("[0-9a-f]{64}");
        assertThatThrownBy(() -> service(port).inspectQuestionMembership(
                BANK_ID, List.of(8_101, 0)))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void allPublicFactsMethodsOpenIndependentReadOnlyTransactions() throws Exception {
        assertRequiresNew("checkQuestionAccess", AuthenticatedPersonalBankViewer.class, int.class);
        assertRequiresNew(
                "summarizeQuestions",
                AuthenticatedPersonalBankViewer.class,
                PersonalBankQuestionSelection.class);
        assertRequiresNew("inspectQuestionMembership", int.class, List.class);
    }

    private static PersonalBankQuestionFactsService service(RecordingPort port) {
        return new PersonalBankQuestionFactsService(port, FIXED_CLOCK);
    }

    private static BankAccess privateBank(List<ShareGrant> grants) {
        return new BankAccess(BANK_ID, VIEWER_ID + 100, false, 1, grants);
    }

    private static ShareGrant grant(
            int recordId,
            int recordBankId,
            Integer recordStatus,
            int shareId,
            int shareBankId,
            String permission,
            Boolean active,
            LocalDateTime expiresAt
    ) {
        return new ShareGrant(
                recordId,
                recordBankId,
                recordStatus,
                shareId,
                shareBankId,
                permission,
                active,
                expiresAt);
    }

    private static void assertRequiresNew(String method, Class<?>... parameterTypes)
            throws Exception {
        Transactional transaction = PersonalBankQuestionFactsService.class
                .getDeclaredMethod(method, parameterTypes)
                .getAnnotation(Transactional.class);
        assertThat(transaction).isNotNull();
        assertThat(transaction.propagation()).isEqualTo(Propagation.REQUIRES_NEW);
        assertThat(transaction.readOnly()).isTrue();
    }

    private static final class RecordingPort implements PersonalBankQuestionFactsQueryPort {

        private final Deque<Optional<BankAccess>> access = new ArrayDeque<>();
        private final List<String> calls = new ArrayList<>();
        private final List<PersonalBankQuestionSelection> selections = new ArrayList<>();
        private QuestionFacts facts = new QuestionFacts(0L, List.of());
        private QuestionMembership membership = new QuestionMembership(false, List.of());
        private List<Integer> receivedMembershipIds = List.of();

        @Override
        public Optional<BankAccess> findAccess(long viewerId, int bankId) {
            assertThat(viewerId).isEqualTo(VIEWER_ID);
            calls.add("access:" + bankId);
            return access.removeFirst();
        }

        @Override
        public QuestionFacts summarizeQuestions(PersonalBankQuestionSelection selection) {
            calls.add("summary:" + selection.bankId());
            selections.add(selection);
            return facts;
        }

        @Override
        public QuestionMembership inspectQuestionMembership(
                int bankId,
                List<Integer> questionIds
        ) {
            receivedMembershipIds = List.copyOf(questionIds);
            return membership;
        }
    }
}
