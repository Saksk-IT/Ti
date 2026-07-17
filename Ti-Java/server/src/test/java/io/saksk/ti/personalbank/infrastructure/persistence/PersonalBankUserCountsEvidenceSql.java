package io.saksk.ti.personalbank.infrastructure.persistence;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/** Test-only SQL frozen before the personal-bank user-counts implementation starts. */
public final class PersonalBankUserCountsEvidenceSql {

    /** Safety bound for this test-only renderer; the legacy handler has no explicit cap. */
    public static final int EVIDENCE_MAX_TAG_PARAMETER_COUNT = 900;

    public static final String BANK_ACCESS_ID =
            "personal-bank-user-counts-bank-access";
    public static final String SHARE_ACCESS_ID =
            "personal-bank-user-counts-share-access";
    public static final String ALL_COUNT_ID =
            "personal-bank-user-counts-all-count";
    public static final String FAVORITES_COUNT_ID =
            "personal-bank-user-counts-favorites-count";
    public static final String MISTAKES_COUNT_ID =
            "personal-bank-user-counts-mistakes-count";
    public static final String ALL_TYPES_ID =
            "personal-bank-user-counts-all-types";
    public static final String FAVORITES_TYPES_ID =
            "personal-bank-user-counts-favorites-types";
    public static final String MISTAKES_TYPES_ID =
            "personal-bank-user-counts-mistakes-types";

    public static final String BANK_ACCESS = """
            SELECT *
            FROM user_question_banks
            WHERE id = :bank_id
            """;

    public static final String SHARE_ACCESS = """
            SELECT bsr.*,
                   bs.permission,
                   bs.is_active,
                   bs.expires_at
            FROM bank_share_records bsr
            JOIN bank_shares bs ON bsr.share_id = bs.id
            WHERE bsr.user_id = :user_id
              AND bsr.bank_id = :bank_id
              AND bsr.status = 1
            """;

    private static final String ALL_COUNT = """
            SELECT COUNT(*) AS cnt
            FROM user_bank_questions q
            WHERE q.bank_id = :bank_id
            """;

    private static final String FAVORITES_COUNT = """
            SELECT COUNT(*) AS cnt
            FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = :bank_id
              AND f.user_id = :uid
            """;

    private static final String MISTAKES_COUNT = """
            SELECT COUNT(*) AS cnt
            FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = :bank_id
              AND m.user_id = :uid
            """;

    private static final String ALL_TYPES = """
            SELECT DISTINCT q.type AS p_type
            FROM user_bank_questions q
            WHERE q.bank_id = :bank_id
            """;

    private static final String FAVORITES_TYPES = """
            SELECT DISTINCT q.type AS p_type
            FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = :bank_id
              AND f.user_id = :uid
            """;

    private static final String MISTAKES_TYPES = """
            SELECT DISTINCT q.type AS p_type
            FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = :bank_id
              AND m.user_id = :uid
            """;

    private PersonalBankUserCountsEvidenceSql() {
    }

    public static EvidenceQuery accessBank() {
        return query(
                BANK_ACCESS_ID,
                "bank-access",
                BANK_ACCESS,
                List.of("bank_id"),
                parameterTypes(false, false, 0));
    }

    public static EvidenceQuery accessShare() {
        return query(
                SHARE_ACCESS_ID,
                "share-access",
                SHARE_ACCESS,
                List.of("user_id", "bank_id"),
                linkedParameters("user_id", "bigint", "bank_id", "integer"));
    }

    public static List<EvidenceQuery> queryFamilies(
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        return List.of(
                accessBank(),
                accessShare(),
                allCount("all-count", qTypeFilter, tagParameterCount),
                favoritesCount("favorites-count", qTypeFilter, tagParameterCount),
                mistakesCount("mistakes-count", qTypeFilter, tagParameterCount),
                allTypes("all-types", qTypeFilter, tagParameterCount),
                favoritesTypes("favorites-types", qTypeFilter, tagParameterCount),
                mistakesTypes("mistakes-types", qTypeFilter, tagParameterCount));
    }

    public static List<EvidenceQuery> statisticsSequence(
            Source source,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        Objects.requireNonNull(source, "source");
        requireTagParameterCount(tagParameterCount);
        return switch (source) {
            case ALL -> List.of(
                    allCount("total", qTypeFilter, tagParameterCount),
                    favoritesCount("favorites", qTypeFilter, tagParameterCount),
                    mistakesCount("mistakes", qTypeFilter, tagParameterCount),
                    allTypes("types", qTypeFilter, tagParameterCount));
            case FAVORITES -> List.of(
                    favoritesCount("total", qTypeFilter, tagParameterCount),
                    favoritesCount("favorites", qTypeFilter, tagParameterCount),
                    mistakesCount("mistakes", qTypeFilter, tagParameterCount),
                    favoritesTypes("types", qTypeFilter, tagParameterCount));
            case MISTAKES -> List.of(
                    mistakesCount("total", qTypeFilter, tagParameterCount),
                    favoritesCount("favorites", qTypeFilter, tagParameterCount),
                    mistakesCount("mistakes", qTypeFilter, tagParameterCount),
                    mistakesTypes("types", qTypeFilter, tagParameterCount));
        };
    }

    public static String dynamicTagPredicate(int tagParameterCount) {
        requireTagParameterCount(tagParameterCount);
        if (tagParameterCount == 0) {
            return "q.id IN (NULL)";
        }
        String placeholders = IntStream.range(0, tagParameterCount)
                .mapToObj(index -> ":tq_" + index)
                .collect(Collectors.joining(", "));
        return "q.id IN (" + placeholders + ")";
    }

    private static EvidenceQuery allCount(
            String operation,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        return statisticsQuery(
                ALL_COUNT_ID,
                operation,
                ALL_COUNT,
                false,
                false,
                qTypeFilter,
                tagParameterCount);
    }

    private static EvidenceQuery favoritesCount(
            String operation,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        return statisticsQuery(
                FAVORITES_COUNT_ID,
                operation,
                FAVORITES_COUNT,
                true,
                false,
                qTypeFilter,
                tagParameterCount);
    }

    private static EvidenceQuery mistakesCount(
            String operation,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        return statisticsQuery(
                MISTAKES_COUNT_ID,
                operation,
                MISTAKES_COUNT,
                true,
                false,
                qTypeFilter,
                tagParameterCount);
    }

    private static EvidenceQuery allTypes(
            String operation,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        return statisticsQuery(
                ALL_TYPES_ID,
                operation,
                ALL_TYPES,
                false,
                true,
                qTypeFilter,
                tagParameterCount);
    }

    private static EvidenceQuery favoritesTypes(
            String operation,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        return statisticsQuery(
                FAVORITES_TYPES_ID,
                operation,
                FAVORITES_TYPES,
                true,
                true,
                qTypeFilter,
                tagParameterCount);
    }

    private static EvidenceQuery mistakesTypes(
            String operation,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        return statisticsQuery(
                MISTAKES_TYPES_ID,
                operation,
                MISTAKES_TYPES,
                true,
                true,
                qTypeFilter,
                tagParameterCount);
    }

    private static EvidenceQuery statisticsQuery(
            String queryId,
            String operation,
            String baseSql,
            boolean viewerParameter,
            boolean orderTypes,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        requireTagParameterCount(tagParameterCount);
        StringBuilder sql = new StringBuilder(baseSql.stripTrailing());
        if (qTypeFilter) {
            sql.append("\n  AND q.type = :q_type_f");
        }
        if (tagParameterCount > 0) {
            sql.append("\n  AND ").append(dynamicTagPredicate(tagParameterCount));
        }
        if (orderTypes) {
            sql.append("\nORDER BY q.type");
        }
        sql.append('\n');

        List<String> parameterOrder = new ArrayList<>();
        parameterOrder.add("bank_id");
        if (viewerParameter) {
            parameterOrder.add("uid");
        }
        if (qTypeFilter) {
            parameterOrder.add("q_type_f");
        }
        IntStream.range(0, tagParameterCount)
                .mapToObj(index -> "tq_" + index)
                .forEach(parameterOrder::add);
        return query(
                queryId,
                operation,
                sql.toString(),
                List.copyOf(parameterOrder),
                parameterTypes(viewerParameter, qTypeFilter, tagParameterCount));
    }

    private static Map<String, String> parameterTypes(
            boolean viewerParameter,
            boolean qTypeFilter,
            int tagParameterCount
    ) {
        LinkedHashMap<String, String> parameters = new LinkedHashMap<>();
        parameters.put("bank_id", "integer");
        if (viewerParameter) {
            parameters.put("uid", "bigint");
        }
        if (qTypeFilter) {
            parameters.put("q_type_f", "text");
        }
        IntStream.range(0, tagParameterCount)
                .forEach(index -> parameters.put("tq_" + index, "integer"));
        return Collections.unmodifiableMap(new LinkedHashMap<>(parameters));
    }

    private static Map<String, String> linkedParameters(String... pairs) {
        LinkedHashMap<String, String> parameters = new LinkedHashMap<>();
        for (int index = 0; index < pairs.length; index += 2) {
            parameters.put(pairs[index], pairs[index + 1]);
        }
        return Collections.unmodifiableMap(new LinkedHashMap<>(parameters));
    }

    private static EvidenceQuery query(
            String queryId,
            String operation,
            String sql,
            List<String> parameterOrder,
            Map<String, String> parameters
    ) {
        return new EvidenceQuery(
                queryId,
                operation,
                sql,
                List.copyOf(parameterOrder),
                Collections.unmodifiableMap(new LinkedHashMap<>(parameters)));
    }

    private static void requireTagParameterCount(int tagParameterCount) {
        if (tagParameterCount < 0) {
            throw new IllegalArgumentException("tagParameterCount must not be negative");
        }
        if (tagParameterCount > EVIDENCE_MAX_TAG_PARAMETER_COUNT) {
            throw new IllegalArgumentException(
                    "tagParameterCount exceeds the evidence render bound of "
                            + EVIDENCE_MAX_TAG_PARAMETER_COUNT);
        }
    }

    public enum Source {
        ALL,
        FAVORITES,
        MISTAKES
    }

    public record EvidenceQuery(
            String queryId,
            String operation,
            String sql,
            List<String> parameterOrder,
            Map<String, String> parameters
    ) {
    }
}
