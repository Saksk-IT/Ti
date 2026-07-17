package io.saksk.ti.learning.application;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.learning.api.PersonalBankUserCountsQuery;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.learning.application.port.PersonalBankUserCountsQueryPort;
import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankQuestionAccessResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsApi;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsResult;
import io.saksk.ti.personalbank.api.PersonalBankQuestionFactsView;
import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.personalbank.api.PersonalBankQuestionTypeCount;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;
import java.util.TreeSet;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.TransactionException;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Service
class PersonalBankUserCountsService implements LearningApplicationApi {

    private static final PersonalBankUserCountsView ZERO_VIEW =
            new PersonalBankUserCountsView(0L, 0L, 0L, List.of(), false);

    private final PersonalBankQuestionFactsApi questionFacts;
    private final PersonalBankUserCountsQueryPort memberships;

    PersonalBankUserCountsService(
            PersonalBankQuestionFactsApi questionFacts,
            PersonalBankUserCountsQueryPort memberships
    ) {
        this.questionFacts = Objects.requireNonNull(questionFacts, "questionFacts");
        this.memberships = Objects.requireNonNull(memberships, "memberships");
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public PersonalBankUserCountsResult findPersonalBankUserCounts(
            AuthenticatedLearningViewer viewer,
            PersonalBankUserCountsQuery query
    ) {
        Objects.requireNonNull(viewer, "viewer");
        Objects.requireNonNull(query, "query");

        AuthenticatedPersonalBankViewer bankViewer =
                new AuthenticatedPersonalBankViewer(viewer.identityId());
        if (isDenied(questionFacts.checkQuestionAccess(bankViewer, query.bankId()))) {
            return PersonalBankUserCountsResult.denied();
        }

        Optional<String> portableType = normalizeQuestionType(query.rawQuestionType());
        Source source = normalizeSource(query.rawSource());
        Optional<List<Integer>> tagCandidates = loadTagCandidates(viewer, query);
        if (tagCandidates.filter(List::isEmpty).isPresent()) {
            if (isDenied(questionFacts.checkQuestionAccess(bankViewer, query.bankId()))) {
                return PersonalBankUserCountsResult.denied();
            }
            return PersonalBankUserCountsResult.available(ZERO_VIEW);
        }

        PersonalBankQuestionFactsResult totalResult = summarize(
                bankViewer,
                query.bankId(),
                portableType,
                candidatesForSource(viewer.identityId(), source, tagCandidates));
        if (isDenied(totalResult)) {
            return PersonalBankUserCountsResult.denied();
        }
        long total = data(totalResult).total();

        FieldResult<Long> favorites = optionalCount(
                bankViewer,
                viewer.identityId(),
                query.bankId(),
                portableType,
                tagCandidates,
                Source.FAVORITES);
        if (favorites.denied()) {
            return PersonalBankUserCountsResult.denied();
        }

        FieldResult<Long> mistakes = optionalCount(
                bankViewer,
                viewer.identityId(),
                query.bankId(),
                portableType,
                tagCandidates,
                Source.MISTAKES);
        if (mistakes.denied()) {
            return PersonalBankUserCountsResult.denied();
        }

        FieldResult<List<String>> types = optionalTypes(
                bankViewer,
                viewer.identityId(),
                query.bankId(),
                portableType,
                tagCandidates,
                source);
        if (types.denied()) {
            return PersonalBankUserCountsResult.denied();
        }

        List<String> displayTypes = types.value();
        boolean shuffleOptionsAvailable = !displayTypes.isEmpty()
                && displayTypes.stream().allMatch(PersonalBankUserCountsService::isOptionType);
        return PersonalBankUserCountsResult.available(new PersonalBankUserCountsView(
                total,
                favorites.value(),
                mistakes.value(),
                displayTypes,
                shuffleOptionsAvailable));
    }

    private Optional<List<Integer>> loadTagCandidates(
            AuthenticatedLearningViewer viewer,
            PersonalBankUserCountsQuery query
    ) {
        String tag = query.rawTag().strip();
        if (tag.isEmpty() || tag.equals("all")) {
            return Optional.empty();
        }
        try {
            return Optional.of(normalizeIds(memberships.findQuestionIdsByTag(
                    viewer.identityId(), query.bankId(), tag)));
        } catch (RuntimeException exception) {
            if (isInfrastructureQueryFailure(exception)) {
                return Optional.of(List.of());
            }
            throw exception;
        }
    }

    private Optional<List<Integer>> candidatesForSource(
            long viewerId,
            Source source,
            Optional<List<Integer>> tagCandidates
    ) {
        return switch (source) {
            case ALL -> tagCandidates;
            case FAVORITES -> Optional.of(normalizeIds(
                    memberships.findFavoriteQuestionIds(viewerId, tagCandidates)));
            case MISTAKES -> Optional.of(normalizeIds(
                    memberships.findMistakeQuestionIds(viewerId, tagCandidates)));
        };
    }

    private FieldResult<Long> optionalCount(
            AuthenticatedPersonalBankViewer viewer,
            long viewerId,
            int bankId,
            Optional<String> portableType,
            Optional<List<Integer>> tagCandidates,
            Source source
    ) {
        try {
            PersonalBankQuestionFactsResult result = summarize(
                    viewer,
                    bankId,
                    portableType,
                    candidatesForSource(viewerId, source, tagCandidates));
            if (isDenied(result)) {
                return FieldResult.deniedResult();
            }
            return FieldResult.available(data(result).total());
        } catch (RuntimeException exception) {
            if (isInfrastructureQueryFailure(exception)) {
                return FieldResult.available(0L);
            }
            throw exception;
        }
    }

    private FieldResult<List<String>> optionalTypes(
            AuthenticatedPersonalBankViewer viewer,
            long viewerId,
            int bankId,
            Optional<String> portableType,
            Optional<List<Integer>> tagCandidates,
            Source source
    ) {
        try {
            PersonalBankQuestionFactsResult result = summarize(
                    viewer,
                    bankId,
                    portableType,
                    candidatesForSource(viewerId, source, tagCandidates));
            if (isDenied(result)) {
                return FieldResult.deniedResult();
            }
            return FieldResult.available(mapDisplayTypes(data(result).rawTypes()));
        } catch (RuntimeException exception) {
            if (isInfrastructureQueryFailure(exception)) {
                return FieldResult.available(List.of());
            }
            throw exception;
        }
    }

    private PersonalBankQuestionFactsResult summarize(
            AuthenticatedPersonalBankViewer viewer,
            int bankId,
            Optional<String> portableType,
            Optional<List<Integer>> candidateQuestionIds
    ) {
        return Objects.requireNonNull(questionFacts.summarizeQuestions(
                viewer,
                new PersonalBankQuestionSelection(
                        bankId,
                        portableType,
                        candidateQuestionIds)), "question facts result");
    }

    private static PersonalBankQuestionFactsView data(
            PersonalBankQuestionFactsResult result
    ) {
        return result.data().orElseThrow(
                () -> new IllegalStateException("available question facts require data"));
    }

    private static boolean isDenied(PersonalBankQuestionAccessResult result) {
        return Objects.requireNonNull(result, "question access result").outcome()
                == PersonalBankQuestionAccessResult.Outcome.DENIED;
    }

    private static boolean isDenied(PersonalBankQuestionFactsResult result) {
        return Objects.requireNonNull(result, "question facts result").outcome()
                == PersonalBankQuestionFactsResult.Outcome.DENIED;
    }

    private static List<Integer> normalizeIds(List<Integer> rawIds) {
        Objects.requireNonNull(rawIds, "questionIds");
        TreeSet<Integer> normalized = new TreeSet<>();
        for (Integer id : rawIds) {
            if (id != null && id > 0) {
                normalized.add(id);
            }
        }
        return List.copyOf(normalized);
    }

    private static Optional<String> normalizeQuestionType(String rawQuestionType) {
        String trimmed = rawQuestionType.strip();
        if (trimmed.isEmpty() || trimmed.equalsIgnoreCase("all")) {
            return Optional.empty();
        }
        String normalized = normalizePortableAlias(trimmed);
        if (isPortableType(normalized)) {
            return Optional.of(normalized);
        }
        if (trimmed.contains("多选")) {
            return Optional.of("multi_choice");
        }
        if (trimmed.contains("选择") || trimmed.contains("单选")) {
            return Optional.of("single_choice");
        }
        if (trimmed.contains("判断")) {
            return Optional.of("boolean");
        }
        if (trimmed.contains("填空")) {
            return Optional.of("fill");
        }
        return Optional.of("essay");
    }

    private static String normalizePortableAlias(String value) {
        String normalized = value.strip().toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "single", "single_choice", "singlechoice" -> "single_choice";
            case "multi", "multiple", "multi_choice", "multichoice" -> "multi_choice";
            case "boolean", "bool", "judge", "true_false", "truefalse" -> "boolean";
            case "fill", "fill_in_the_blank", "fill-in-the-blank", "fillblank",
                    "fill_in_the_blank_question" -> "fill";
            case "essay", "short_answer", "shortanswer" -> "essay";
            default -> normalized;
        };
    }

    private static boolean isPortableType(String value) {
        return value.equals("single_choice")
                || value.equals("multi_choice")
                || value.equals("boolean")
                || value.equals("fill")
                || value.equals("essay");
    }

    private static List<String> mapDisplayTypes(
            List<PersonalBankQuestionTypeCount> rawTypes
    ) {
        Objects.requireNonNull(rawTypes, "rawTypes");
        List<String> mapped = new ArrayList<>();
        for (PersonalBankQuestionTypeCount rawType : rawTypes) {
            Objects.requireNonNull(rawType, "rawType");
            if (rawType.rawType().isEmpty() || rawType.rawType().orElseThrow().isEmpty()) {
                continue;
            }
            mapped.add(toDisplayType(rawType.rawType().orElseThrow()));
        }
        return List.copyOf(mapped);
    }

    private static String toDisplayType(String rawType) {
        return switch (normalizePortableAlias(rawType)) {
            case "single_choice" -> "选择题";
            case "multi_choice" -> "多选题";
            case "boolean" -> "判断题";
            case "fill" -> "填空题";
            default -> "简答题";
        };
    }

    private static Source normalizeSource(String rawSource) {
        return switch (rawSource.strip()) {
            case "favorites" -> Source.FAVORITES;
            case "mistakes" -> Source.MISTAKES;
            default -> Source.ALL;
        };
    }

    private static boolean isInfrastructureQueryFailure(RuntimeException exception) {
        return exception instanceof DataAccessException
                || exception instanceof TransactionException;
    }

    private static boolean isOptionType(String type) {
        return type.equals("选择题") || type.equals("多选题");
    }

    private enum Source {
        ALL,
        FAVORITES,
        MISTAKES
    }

    private record FieldResult<T>(boolean denied, T value) {

        private static <T> FieldResult<T> available(T value) {
            return new FieldResult<>(false, Objects.requireNonNull(value, "value"));
        }

        private static <T> FieldResult<T> deniedResult() {
            return new FieldResult<>(true, null);
        }
    }
}
