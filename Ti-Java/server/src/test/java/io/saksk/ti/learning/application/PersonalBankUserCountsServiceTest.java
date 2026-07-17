package io.saksk.ti.learning.application;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.PersonalBankUserCountsQuery;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.learning.application.port.PersonalBankUserCountsQueryPort;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionMembershipView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.personalbank.api.PersonalBankQuestionTypeCount;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

class PersonalBankUserCountsServiceTest {

    private static final AuthenticatedLearningViewer VIEWER =
            new AuthenticatedLearningViewer(7_001L);
    private static final int BANK_ID = 7_101;

    @Test
    void rechecksAccessBeforeReturningZeroView() {
        List<String> deniedEvents = new ArrayList<>();
        var deniedFacts = new RecordingFacts(deniedEvents);
        deniedFacts.accessResults.add(PersonalBankQuestionAccessResult.available());
        deniedFacts.accessResults.add(PersonalBankQuestionAccessResult.denied());
        var deniedMemberships = new RecordingMemberships(deniedEvents);
        deniedMemberships.tagIds = List.of();

        PersonalBankUserCountsResult denied = service(deniedFacts, deniedMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", "重点"));

        assertThat(denied).isEqualTo(PersonalBankUserCountsResult.denied());
        assertThat(deniedEvents).containsExactly("access", "tag:重点", "access");
        assertThat(deniedFacts.selections).isEmpty();

        List<String> availableEvents = new ArrayList<>();
        var availableFacts = new RecordingFacts(availableEvents);
        var availableMemberships = new RecordingMemberships(availableEvents);
        availableMemberships.tagIds = List.of();

        PersonalBankUserCountsResult available = service(availableFacts, availableMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", "重点"));

        assertThat(available.data()).contains(new PersonalBankUserCountsView(
                0, 0, 0, List.of(), false));
        assertThat(availableEvents).containsExactly("access", "tag:重点", "access");
        assertThat(availableFacts.selections).isEmpty();
    }

    @Test
    void deniedFromAnyPersonalbankCallIsTerminal() {
        List<String> accessEvents = new ArrayList<>();
        var accessDenied = new RecordingFacts(accessEvents);
        accessDenied.accessResults.add(PersonalBankQuestionAccessResult.denied());
        var accessMemberships = new RecordingMemberships(accessEvents);

        assertThat(service(accessDenied, accessMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", "")))
                .isEqualTo(PersonalBankUserCountsResult.denied());
        assertThat(accessEvents).containsExactly("access");

        for (int deniedSummary = 1; deniedSummary <= 4; deniedSummary++) {
            List<String> events = new ArrayList<>();
            var facts = new RecordingFacts(events);
            for (int index = 1; index < deniedSummary; index++) {
                facts.summaryResults.add(facts(100L + index, "single_choice"));
            }
            facts.summaryResults.add(PersonalBankQuestionFactsResult.denied());
            var memberships = new RecordingMemberships(events);

            PersonalBankUserCountsResult result = service(facts, memberships)
                    .findPersonalBankUserCounts(VIEWER, query("", "all", ""));

            assertThat(result.outcome())
                    .as("summary call %s", deniedSummary)
                    .isEqualTo(PersonalBankUserCountsResult.Outcome.DENIED);
            assertThat(result.data()).isEmpty();
            assertThat(facts.selections).hasSize(deniedSummary);
            assertThat(events.getLast()).startsWith("summary:");
        }
    }

    @Test
    void optionalFailuresRemainFieldLocal() {
        List<String> localFailureEvents = new ArrayList<>();
        var localFailureFacts = new RecordingFacts(localFailureEvents);
        localFailureFacts.summaryResults.add(facts(9, "boolean"));
        localFailureFacts.summaryResults.add(facts(3, "multi_choice"));
        localFailureFacts.summaryResults.add(facts(
                9, "boolean", null, "", "unexpected_type", "single_choice"));
        var localFailureMemberships = new RecordingMemberships(localFailureEvents);
        localFailureMemberships.favoriteFailure =
                new DataAccessResourceFailureException("favorites unavailable");

        PersonalBankUserCountsResult localFailureResult = service(
                localFailureFacts, localFailureMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", ""));

        assertThat(localFailureResult.data()).contains(new PersonalBankUserCountsView(
                9,
                0,
                3,
                List.of("判断题", "简答题", "选择题"),
                false));
        assertThat(localFailureEvents).containsExactly(
                "access",
                "summary:all",
                "favorites:all",
                "mistakes:all",
                "summary:[8201, 8202]",
                "summary:all");

        List<String> providerFailureEvents = new ArrayList<>();
        var providerFailureFacts = new RecordingFacts(providerFailureEvents);
        providerFailureFacts.summaryResults.add(facts(9, "boolean"));
        providerFailureFacts.summaryResults.add(
                new DataAccessResourceFailureException("favorite facts unavailable"));
        providerFailureFacts.summaryResults.add(facts(3, "multi_choice"));
        providerFailureFacts.summaryResults.add(facts(9, "single_choice", "multi_choice"));
        var providerFailureMemberships = new RecordingMemberships(providerFailureEvents);

        PersonalBankUserCountsResult providerFailureResult = service(
                providerFailureFacts, providerFailureMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", ""));

        assertThat(providerFailureResult.data()).contains(new PersonalBankUserCountsView(
                9, 0, 3, List.of("选择题", "多选题"), true));
    }

    @Test
    void mistakeFailuresRemainFieldLocalAndTypesContinue() {
        List<String> localFailureEvents = new ArrayList<>();
        var localFailureFacts = new RecordingFacts(localFailureEvents);
        localFailureFacts.summaryResults.add(facts(9, "boolean"));
        localFailureFacts.summaryResults.add(facts(4, "single_choice"));
        localFailureFacts.summaryResults.add(facts(9, "single_choice", "multi_choice"));
        var localFailureMemberships = new RecordingMemberships(localFailureEvents);
        localFailureMemberships.mistakeFailure =
                new DataAccessResourceFailureException("mistakes unavailable");

        PersonalBankUserCountsResult localFailureResult = service(
                localFailureFacts, localFailureMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", ""));

        assertThat(localFailureResult.data()).contains(new PersonalBankUserCountsView(
                9, 4, 0, List.of("选择题", "多选题"), true));
        assertThat(localFailureEvents).containsExactly(
                "access",
                "summary:all",
                "favorites:all",
                "summary:[8101, 8102]",
                "mistakes:all",
                "summary:all");

        List<String> providerFailureEvents = new ArrayList<>();
        var providerFailureFacts = new RecordingFacts(providerFailureEvents);
        providerFailureFacts.summaryResults.add(facts(9, "boolean"));
        providerFailureFacts.summaryResults.add(facts(4, "single_choice"));
        providerFailureFacts.summaryResults.add(
                new DataAccessResourceFailureException("mistake facts unavailable"));
        providerFailureFacts.summaryResults.add(facts(9, "single_choice", "multi_choice"));

        PersonalBankUserCountsResult providerFailureResult = service(
                providerFailureFacts, new RecordingMemberships(providerFailureEvents))
                .findPersonalBankUserCounts(VIEWER, query("", "all", ""));

        assertThat(providerFailureResult.data()).contains(new PersonalBankUserCountsView(
                9, 4, 0, List.of("选择题", "多选题"), true));
        assertThat(providerFailureEvents).containsExactly(
                "access",
                "summary:all",
                "favorites:all",
                "summary:[8101, 8102]",
                "mistakes:all",
                "summary:[8201, 8202]",
                "summary:all");
    }

    @Test
    void typeFailuresRemainFieldLocal() {
        List<String> localFailureEvents = new ArrayList<>();
        var localFailureFacts = new RecordingFacts(localFailureEvents);
        localFailureFacts.summaryResults.add(facts(2, "single_choice"));
        localFailureFacts.summaryResults.add(facts(2, "single_choice"));
        localFailureFacts.summaryResults.add(facts(1, "multi_choice"));
        var localFailureMemberships = new RecordingMemberships(localFailureEvents);
        localFailureMemberships.favoriteFailure =
                new DataAccessResourceFailureException("type memberships unavailable");
        localFailureMemberships.favoriteFailureCall = 3;

        PersonalBankUserCountsResult localFailureResult = service(
                localFailureFacts, localFailureMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "favorites", ""));

        assertThat(localFailureResult.data()).contains(new PersonalBankUserCountsView(
                2, 2, 1, List.of(), false));
        assertThat(localFailureEvents).containsExactly(
                "access",
                "favorites:all",
                "summary:[8101, 8102]",
                "favorites:all",
                "summary:[8101, 8102]",
                "mistakes:all",
                "summary:[8201, 8202]",
                "favorites:all");

        List<String> providerFailureEvents = new ArrayList<>();
        var providerFailureFacts = new RecordingFacts(providerFailureEvents);
        providerFailureFacts.summaryResults.add(facts(9, "boolean"));
        providerFailureFacts.summaryResults.add(facts(4, "single_choice"));
        providerFailureFacts.summaryResults.add(facts(3, "multi_choice"));
        providerFailureFacts.summaryResults.add(
                new DataAccessResourceFailureException("types unavailable"));

        PersonalBankUserCountsResult providerFailureResult = service(
                providerFailureFacts, new RecordingMemberships(providerFailureEvents))
                .findPersonalBankUserCounts(VIEWER, query("", "all", ""));

        assertThat(providerFailureResult.data()).contains(new PersonalBankUserCountsView(
                9, 4, 3, List.of(), false));
    }

    @Test
    void onlyInfrastructureFailuresAreFailSoft() {

        IllegalStateException programmingFailure =
                new IllegalStateException("not an infrastructure failure");
        var strictMemberships = new RecordingMemberships(new ArrayList<>());
        strictMemberships.favoriteFailure = programmingFailure;
        assertThatThrownBy(() -> service(
                        new RecordingFacts(new ArrayList<>()), strictMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", "")))
                .isSameAs(programmingFailure);

        List<String> tagFailureEvents = new ArrayList<>();
        var tagFailureFacts = new RecordingFacts(tagFailureEvents);
        var tagFailureMemberships = new RecordingMemberships(tagFailureEvents);
        tagFailureMemberships.tagFailure =
                new DataAccessResourceFailureException("tag membership unavailable");
        assertThat(service(tagFailureFacts, tagFailureMemberships)
                .findPersonalBankUserCounts(VIEWER, query("", "all", "重点"))
                .data())
                .contains(new PersonalBankUserCountsView(0, 0, 0, List.of(), false));
        assertThat(tagFailureEvents).containsExactly("access", "tag:重点", "access");
    }

    @Test
    void preservesOrderedLegacyQuerySequence() {
        assertSequence("all", List.of(
                "access",
                "summary:all",
                "favorites:all",
                "summary:[8101, 8102]",
                "mistakes:all",
                "summary:[8201, 8202]",
                "summary:all"));
        assertSequence("favorites", List.of(
                "access",
                "favorites:all",
                "summary:[8101, 8102]",
                "favorites:all",
                "summary:[8101, 8102]",
                "mistakes:all",
                "summary:[8201, 8202]",
                "favorites:all",
                "summary:[8101, 8102]"));
        assertSequence("mistakes", List.of(
                "access",
                "mistakes:all",
                "summary:[8201, 8202]",
                "favorites:all",
                "summary:[8101, 8102]",
                "mistakes:all",
                "summary:[8201, 8202]",
                "mistakes:all",
                "summary:[8201, 8202]"));
    }

    @Test
    void normalizesFrozenFiltersAndPreservesRawTypeOrderAndDuplicates() {
        List<String> events = new ArrayList<>();
        var facts = new RecordingFacts(events);
        PersonalBankQuestionFactsResult response = facts(
                4, "boolean", null, "", "unexpected_type", "single_choice", "single");
        facts.defaultSummaryResult = response;
        var memberships = new RecordingMemberships(events);
        memberships.tagIds = Arrays.asList(8_103, null, -1, 8_101, 8_103);

        PersonalBankUserCountsResult result = service(facts, memberships)
                .findPersonalBankUserCounts(
                        VIEWER,
                        query("  单选题  ", " Favorites ", " All "));

        assertThat(facts.selections).hasSize(4).allSatisfy(selection ->
                assertThat(selection.portableType()).contains("single_choice"));
        assertThat(facts.selections.get(0).candidateQuestionIds())
                .contains(List.of(8_101, 8_103));
        assertThat(facts.selections.get(1).candidateQuestionIds())
                .contains(List.of(8_101));
        assertThat(facts.selections.get(2).candidateQuestionIds())
                .contains(List.of());
        assertThat(facts.selections.get(3).candidateQuestionIds())
                .contains(List.of(8_101, 8_103));
        assertThat(result.data()).contains(new PersonalBankUserCountsView(
                4,
                4,
                4,
                List.of("判断题", "简答题", "选择题", "选择题"),
                false));
        assertThat(events.getFirst()).isEqualTo("access");
        assertThat(events.get(1)).isEqualTo("tag:All");
    }

    @Test
    void suspendsAnyOuterTransactionAtTheLearningBoundary() throws Exception {
        Transactional transaction = PersonalBankUserCountsService.class
                .getDeclaredMethod(
                        "findPersonalBankUserCounts",
                        AuthenticatedLearningViewer.class,
                        PersonalBankUserCountsQuery.class)
                .getAnnotation(Transactional.class);

        assertThat(transaction).isNotNull();
        assertThat(transaction.propagation()).isEqualTo(Propagation.NOT_SUPPORTED);
    }

    private static void assertSequence(String source, List<String> expectedEvents) {
        List<String> events = new ArrayList<>();
        var facts = new RecordingFacts(events);
        var memberships = new RecordingMemberships(events);

        PersonalBankUserCountsResult result = service(facts, memberships)
                .findPersonalBankUserCounts(VIEWER, query("", source, ""));

        assertThat(result.outcome()).isEqualTo(PersonalBankUserCountsResult.Outcome.AVAILABLE);
        assertThat(events).containsExactlyElementsOf(expectedEvents);
    }

    private static PersonalBankUserCountsService service(
            PersonalBankQuestionFactsApi facts,
            PersonalBankUserCountsQueryPort memberships
    ) {
        return new PersonalBankUserCountsService(facts, memberships);
    }

    private static PersonalBankUserCountsQuery query(
            String rawQuestionType,
            String rawSource,
            String rawTag
    ) {
        return new PersonalBankUserCountsQuery(
                BANK_ID, rawQuestionType, rawSource, rawTag);
    }

    private static PersonalBankQuestionFactsResult facts(long total, String... rawTypes) {
        return PersonalBankQuestionFactsResult.available(new PersonalBankQuestionFactsView(
                total,
                Arrays.stream(rawTypes)
                        .map(rawType -> new PersonalBankQuestionTypeCount(
                                Optional.ofNullable(rawType), 1L))
                        .toList()));
    }

    private static String candidates(PersonalBankQuestionSelection selection) {
        return selection.candidateQuestionIds()
                .map(Object::toString)
                .orElse("all");
    }

    private static String candidates(Optional<List<Integer>> candidateQuestionIds) {
        return candidateQuestionIds.map(Object::toString).orElse("all");
    }

    private static final class RecordingFacts implements PersonalBankQuestionFactsApi {

        private final List<String> events;
        private final Deque<PersonalBankQuestionAccessResult> accessResults =
                new ArrayDeque<>();
        private final Deque<Object> summaryResults = new ArrayDeque<>();
        private final List<PersonalBankQuestionSelection> selections = new ArrayList<>();
        private PersonalBankQuestionFactsResult defaultSummaryResult =
                facts(1, "single_choice");

        private RecordingFacts(List<String> events) {
            this.events = events;
        }

        @Override
        public PersonalBankQuestionAccessResult checkQuestionAccess(
                AuthenticatedPersonalBankViewer viewer,
                int bankId
        ) {
            assertThat(viewer.identityId()).isEqualTo(VIEWER.identityId());
            assertThat(bankId).isEqualTo(BANK_ID);
            events.add("access");
            return accessResults.isEmpty()
                    ? PersonalBankQuestionAccessResult.available()
                    : accessResults.removeFirst();
        }

        @Override
        public PersonalBankQuestionFactsResult summarizeQuestions(
                AuthenticatedPersonalBankViewer viewer,
                PersonalBankQuestionSelection selection
        ) {
            assertThat(viewer.identityId()).isEqualTo(VIEWER.identityId());
            selections.add(selection);
            events.add("summary:" + candidates(selection));
            if (summaryResults.isEmpty()) {
                return defaultSummaryResult;
            }
            Object next = summaryResults.removeFirst();
            if (next instanceof RuntimeException failure) {
                throw failure;
            }
            return (PersonalBankQuestionFactsResult) next;
        }

        @Override
        public PersonalBankQuestionMembershipView inspectQuestionMembership(
                int bankId,
                List<Integer> questionIds
        ) {
            throw new AssertionError("membership inspection is not part of this read sequence");
        }
    }

    private static final class RecordingMemberships implements PersonalBankUserCountsQueryPort {

        private final List<String> events;
        private List<Integer> tagIds = List.of(8_101, 8_103);
        private List<Integer> favoriteIds = Arrays.asList(8_102, 8_101, 8_102, 0, null);
        private List<Integer> mistakeIds = Arrays.asList(8_202, 8_201, 8_202, -1, null);
        private RuntimeException tagFailure;
        private RuntimeException favoriteFailure;
        private RuntimeException mistakeFailure;
        private int favoriteFailureCall = 1;
        private int favoriteCalls;
        private int mistakeFailureCall = 1;
        private int mistakeCalls;

        private RecordingMemberships(List<String> events) {
            this.events = events;
        }

        @Override
        public List<Integer> findQuestionIdsByTag(long viewerId, int bankId, String tag) {
            assertThat(viewerId).isEqualTo(VIEWER.identityId());
            assertThat(bankId).isEqualTo(BANK_ID);
            events.add("tag:" + tag);
            if (tagFailure != null) {
                throw tagFailure;
            }
            return tagIds;
        }

        @Override
        public List<Integer> findFavoriteQuestionIds(
                long viewerId,
                Optional<List<Integer>> candidateQuestionIds
        ) {
            assertThat(viewerId).isEqualTo(VIEWER.identityId());
            events.add("favorites:" + candidates(candidateQuestionIds));
            favoriteCalls++;
            if (favoriteFailure != null && favoriteCalls == favoriteFailureCall) {
                throw favoriteFailure;
            }
            return filterByCandidates(favoriteIds, candidateQuestionIds);
        }

        @Override
        public List<Integer> findMistakeQuestionIds(
                long viewerId,
                Optional<List<Integer>> candidateQuestionIds
        ) {
            assertThat(viewerId).isEqualTo(VIEWER.identityId());
            events.add("mistakes:" + candidates(candidateQuestionIds));
            mistakeCalls++;
            if (mistakeFailure != null && mistakeCalls == mistakeFailureCall) {
                throw mistakeFailure;
            }
            return filterByCandidates(mistakeIds, candidateQuestionIds);
        }

        private static List<Integer> filterByCandidates(
                List<Integer> ids,
                Optional<List<Integer>> candidateQuestionIds
        ) {
            if (candidateQuestionIds.isEmpty()) {
                return ids;
            }
            List<Integer> candidates = candidateQuestionIds.orElseThrow();
            return ids.stream()
                    .filter(id -> id != null)
                    .filter(candidates::contains)
                    .toList();
        }
    }
}
