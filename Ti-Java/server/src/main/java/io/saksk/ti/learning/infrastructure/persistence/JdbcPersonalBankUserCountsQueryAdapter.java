package io.saksk.ti.learning.infrastructure.persistence;

import io.saksk.ti.learning.application.port.PersonalBankUserCountsQueryPort;
import java.sql.Types;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.support.SqlArrayValue;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Repository
class JdbcPersonalBankUserCountsQueryAdapter implements PersonalBankUserCountsQueryPort {

    static final String SELECT_TAG_QUESTION_IDS = """
            SELECT DISTINCT question_id
            FROM user_question_tag_items
            WHERE user_id = :viewer_id
              AND scope = 'user_bank'
              AND scope_id = :bank_id
              AND tag = :tag
              AND question_id > 0
            ORDER BY question_id
            """;

    static final String SELECT_FAVORITE_QUESTION_IDS = """
            SELECT DISTINCT question_id
            FROM user_bank_favorites
            WHERE user_id = :viewer_id
              AND question_id > 0""";

    static final String SELECT_MISTAKE_QUESTION_IDS = """
            SELECT DISTINCT question_id
            FROM user_bank_mistakes
            WHERE user_id = :viewer_id
              AND question_id > 0""";

    static final String CANDIDATE_QUESTION_IDS_SQL = """

              AND question_id = ANY(CAST(:candidate_question_ids AS integer[]))""";

    static final String ORDER_BY_QUESTION_ID_SQL = """

            ORDER BY question_id
            """;

    private final JdbcClient jdbc;

    JdbcPersonalBankUserCountsQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public List<Integer> findQuestionIdsByTag(long viewerId, int bankId, String tag) {
        return List.copyOf(jdbc.sql(SELECT_TAG_QUESTION_IDS)
                .param("viewer_id", viewerId, Types.BIGINT)
                .param("bank_id", bankId, Types.INTEGER)
                .param("tag", tag, Types.VARCHAR)
                .query(Integer.class)
                .list());
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public List<Integer> findFavoriteQuestionIds(
            long viewerId,
            Optional<List<Integer>> candidateQuestionIds
    ) {
        return findRelationQuestionIds(
                SELECT_FAVORITE_QUESTION_IDS, viewerId, candidateQuestionIds);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public List<Integer> findMistakeQuestionIds(
            long viewerId,
            Optional<List<Integer>> candidateQuestionIds
    ) {
        return findRelationQuestionIds(
                SELECT_MISTAKE_QUESTION_IDS, viewerId, candidateQuestionIds);
    }

    private List<Integer> findRelationQuestionIds(
            String baseSql,
            long viewerId,
            Optional<List<Integer>> candidateQuestionIds
    ) {
        Objects.requireNonNull(candidateQuestionIds, "candidateQuestionIds");
        if (candidateQuestionIds.filter(List::isEmpty).isPresent()) {
            return List.of();
        }

        JdbcClient.StatementSpec statement = jdbc.sql(sqlFor(baseSql, candidateQuestionIds))
                .param("viewer_id", viewerId, Types.BIGINT);
        if (candidateQuestionIds.isPresent()) {
            Object[] candidates = candidateQuestionIds.orElseThrow().toArray(Integer[]::new);
            statement = statement.param(
                    "candidate_question_ids", new SqlArrayValue("integer", candidates));
        }
        return List.copyOf(statement.query(Integer.class).list());
    }

    static String sqlFor(
            String baseSql,
            Optional<List<Integer>> candidateQuestionIds
    ) {
        Objects.requireNonNull(baseSql, "baseSql");
        Objects.requireNonNull(candidateQuestionIds, "candidateQuestionIds");
        return baseSql
                + (candidateQuestionIds.filter(ids -> !ids.isEmpty()).isPresent()
                        ? CANDIDATE_QUESTION_IDS_SQL
                        : "")
                + ORDER_BY_QUESTION_ID_SQL;
    }
}
