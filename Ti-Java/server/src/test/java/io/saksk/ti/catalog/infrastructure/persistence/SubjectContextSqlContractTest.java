package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import org.junit.jupiter.api.Test;

class SubjectContextSqlContractTest {

    @Test
    void runtimeQueryIsTheSingleExplicitBigintBoundSubjectProjection() {
        String sql = JdbcSubjectDetailQueryAdapter.SELECT_SUBJECT_BY_ID;

        assertThat(sql).isEqualTo("""
                SELECT s.id,
                       s.name
                FROM subjects s
                WHERE s.id = :subject_id""");
        assertThat(sql)
                .containsOnlyOnce("FROM subjects s")
                .containsOnlyOnce("WHERE s.id = :subject_id")
                .doesNotContain(
                        "SELECT *",
                        "JOIN ",
                        "questions",
                        "users",
                        "user_subjects",
                        "is_locked",
                        "description",
                        "CAST",
                        "::",
                        "LIMIT",
                        "OFFSET");
        assertThat(sql.split(":subject_id", -1)).hasSize(2);
        assertThat(sql.toUpperCase(Locale.ROOT)).doesNotContain(
                "INSERT ",
                "UPDATE ",
                "DELETE ",
                "CREATE ",
                "ALTER ",
                "DROP ",
                "TEMP ");
    }
}
