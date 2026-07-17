package io.saksk.ti.personalbank.application;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.personalbank.api.PersonalBankQuestionTypeCount;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.QuestionFacts;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.ShareGrant;
import java.time.Clock;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
class PersonalBankQuestionFactsService implements PersonalBankQuestionFactsApi {

    private static final ZoneId BEIJING = ZoneId.of("Asia/Shanghai");
    private static final Set<String> ALLOWED_SHARE_PERMISSIONS = Set.of("read", "copy");
    private static final Comparator<ShareGrant> DETERMINISTIC_GRANT_ORDER =
            Comparator.comparingInt(ShareGrant::shareId)
                    .thenComparingInt(ShareGrant::shareRecordId);

    private final PersonalBankQuestionFactsQueryPort queries;
    private final Clock clock;

    PersonalBankQuestionFactsService(
            PersonalBankQuestionFactsQueryPort queries,
            Clock clock
    ) {
        this.queries = Objects.requireNonNull(queries, "queries");
        this.clock = Objects.requireNonNull(clock, "clock");
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public PersonalBankQuestionAccessResult checkQuestionAccess(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    ) {
        requireViewerAndBank(viewer, bankId);
        return hasQuestionAccess(viewer, bankId)
                ? PersonalBankQuestionAccessResult.available()
                : PersonalBankQuestionAccessResult.denied();
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public PersonalBankQuestionFactsResult summarizeQuestions(
            AuthenticatedPersonalBankViewer viewer,
            PersonalBankQuestionSelection selection
    ) {
        Objects.requireNonNull(selection, "selection");
        requireViewerAndBank(viewer, selection.bankId());
        if (!hasQuestionAccess(viewer, selection.bankId())) {
            return PersonalBankQuestionFactsResult.denied();
        }

        if (selection.candidateQuestionIds().filter(List::isEmpty).isPresent()) {
            return PersonalBankQuestionFactsResult.available(
                    new PersonalBankQuestionFactsView(0L, List.of()));
        }

        QuestionFacts facts = Objects.requireNonNull(
                queries.summarizeQuestions(selection), "question facts");
        List<PersonalBankQuestionTypeCount> rawTypes = facts.rawTypes().stream()
                .map(rawType -> new PersonalBankQuestionTypeCount(
                        rawType.rawType(), rawType.count()))
                .toList();
        return PersonalBankQuestionFactsResult.available(
                new PersonalBankQuestionFactsView(facts.total(), rawTypes));
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public PersonalBankQuestionMembershipView inspectQuestionMembership(
            int bankId,
            List<Integer> questionIds
    ) {
        requirePositiveBankId(bankId);
        List<Integer> normalizedIds = normalizedPositiveIds(questionIds);
        PersonalBankQuestionFactsQueryPort.QuestionMembership membership =
                Objects.requireNonNull(
                        queries.inspectQuestionMembership(bankId, normalizedIds),
                        "question membership");
        validateMembershipResult(normalizedIds, membership);
        return PersonalBankQuestionMembershipView.create(
                bankId,
                membership.bankExists(),
                membership.existingQuestionIds());
    }

    private boolean hasQuestionAccess(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    ) {
        BankAccess bank = Objects.requireNonNull(
                        queries.findAccess(viewer.identityId(), bankId),
                        "bank access")
                .orElse(null);
        if (bank == null || bank.bankId() != bankId || Integer.valueOf(0).equals(bank.status())) {
            return false;
        }
        if (bank.ownerId() != null && bank.ownerId() == viewer.identityId()) {
            return true;
        }
        if (Boolean.TRUE.equals(bank.publicBank())) {
            return true;
        }

        LocalDateTime now = LocalDateTime.ofInstant(clock.instant(), BEIJING);
        return bank.shareGrants().stream()
                .sorted(DETERMINISTIC_GRANT_ORDER)
                .anyMatch(grant -> validGrant(grant, bankId, now));
    }

    private static boolean validGrant(
            ShareGrant grant,
            int requestedBankId,
            LocalDateTime now
    ) {
        return grant.shareRecordBankId() == requestedBankId
                && grant.shareBankId() == requestedBankId
                && Integer.valueOf(1).equals(grant.shareRecordStatus())
                && Boolean.TRUE.equals(grant.active())
                && grant.permission() != null
                && ALLOWED_SHARE_PERMISSIONS.contains(grant.permission())
                && (grant.expiresAt() == null || grant.expiresAt().isAfter(now));
    }

    private static void requireViewerAndBank(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    ) {
        Objects.requireNonNull(viewer, "viewer");
        requirePositiveBankId(bankId);
    }

    private static void requirePositiveBankId(int bankId) {
        if (bankId <= 0) {
            throw new IllegalArgumentException("bankId must be positive");
        }
    }

    private static List<Integer> normalizedPositiveIds(List<Integer> questionIds) {
        Objects.requireNonNull(questionIds, "questionIds");
        if (questionIds.stream().anyMatch(Objects::isNull)) {
            throw new NullPointerException("questionIds must not contain null");
        }
        if (questionIds.stream().anyMatch(questionId -> questionId <= 0)) {
            throw new IllegalArgumentException("questionIds must contain only positive IDs");
        }
        return List.copyOf(questionIds.stream().distinct().sorted().toList());
    }

    private static void validateMembershipResult(
            List<Integer> requestedIds,
            PersonalBankQuestionFactsQueryPort.QuestionMembership membership
    ) {
        Set<Integer> requested = new HashSet<>(requestedIds);
        if (membership.existingQuestionIds().stream().anyMatch(Objects::isNull)
                || membership.existingQuestionIds().stream()
                        .anyMatch(questionId -> questionId <= 0 || !requested.contains(questionId))) {
            throw new IllegalStateException(
                    "Question membership contains an invalid or unrequested ID");
        }
        if (!membership.bankExists() && !membership.existingQuestionIds().isEmpty()) {
            throw new IllegalStateException(
                    "A missing bank cannot contain existing questions");
        }
    }
}
