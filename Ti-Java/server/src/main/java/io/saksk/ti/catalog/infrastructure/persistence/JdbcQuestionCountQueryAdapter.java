package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.QuestionCatalogCountQuery;
import io.saksk.ti.catalog.api.QuestionSubjectAssignmentScope;
import io.saksk.ti.catalog.application.port.QuestionCountQueryPort;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.support.SqlArrayValue;
import org.springframework.stereotype.Repository;

@Repository
class JdbcQuestionCountQueryAdapter implements QuestionCountQueryPort {

    static final String BASE_COUNT_SQL = """
            SELECT COUNT(1)
            FROM questions q
            LEFT JOIN subjects s ON s.id = q.subject_id
            WHERE (s.is_locked = false OR s.is_locked IS NULL)""";
    static final String REQUIRE_EXISTING_SUBJECT_SQL = "\nAND s.id IS NOT NULL";
    static final String EXCLUDE_SUBJECTS_SQL =
            "\nAND s.id <> ALL(CAST(:excluded_subject_ids AS integer[]))";
    static final String SUBJECT_NAME_SQL = "\nAND s.name = :subject_name";
    static final String QUESTION_TYPE_SQL = "\nAND q.type = :question_type";
    static final String CANDIDATE_QUESTION_IDS_SQL =
            "\nAND q.id = ANY(CAST(:candidate_question_ids AS bigint[]))";

    private final JdbcClient jdbc;

    JdbcQuestionCountQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public long countQuestions(QuestionCatalogCountQuery query) {
        if (query.candidateQuestionIds().filter(List::isEmpty).isPresent()) {
            return 0;
        }

        JdbcClient.StatementSpec statement = jdbc.sql(sqlFor(query));
        if (!query.excludedSubjectIds().isEmpty()) {
            Object[] excluded = query.excludedSubjectIds().stream()
                    .sorted()
                    .toArray(Integer[]::new);
            statement = statement.param(
                    "excluded_subject_ids", new SqlArrayValue("integer", excluded));
        }
        if (query.subjectName().isPresent()) {
            statement = statement.param("subject_name", query.subjectName().orElseThrow());
        }
        if (query.questionType().isPresent()) {
            statement = statement.param("question_type", query.questionType().orElseThrow());
        }
        if (query.candidateQuestionIds().isPresent()) {
            Object[] candidates = query.candidateQuestionIds().orElseThrow().toArray(Long[]::new);
            statement = statement.param(
                    "candidate_question_ids", new SqlArrayValue("bigint", candidates));
        }
        return statement.query(Long.class).single();
    }

    static String sqlFor(QuestionCatalogCountQuery query) {
        StringBuilder sql = new StringBuilder(BASE_COUNT_SQL);
        if (query.subjectAssignmentScope()
                == QuestionSubjectAssignmentScope.REQUIRE_EXISTING_SUBJECT) {
            sql.append(REQUIRE_EXISTING_SUBJECT_SQL);
        }
        if (!query.excludedSubjectIds().isEmpty()) {
            sql.append(EXCLUDE_SUBJECTS_SQL);
        }
        query.subjectName().ifPresent(ignored -> sql.append(SUBJECT_NAME_SQL));
        query.questionType().ifPresent(ignored -> sql.append(QUESTION_TYPE_SQL));
        query.candidateQuestionIds()
                .filter(candidateIds -> !candidateIds.isEmpty())
                .ifPresent(ignored -> sql.append(CANDIDATE_QUESTION_IDS_SQL));
        return sql.toString();
    }
}
