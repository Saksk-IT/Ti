package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import org.junit.jupiter.api.Test;

class SubjectInventorySqlContractTest {

    @Test
    void runtimeQueryIsTheSingleFixedZeroBindLegacyInventoryProjection() {
        String sql = JdbcSubjectInventoryQueryAdapter.SELECT_SUBJECT_INVENTORY_SUMMARIES;

        assertThat(sql).isEqualTo("""
                SELECT s.id AS subject_id,
                       s.name AS subject_name,
                       s.is_locked AS subject_locked,
                       COUNT(q.id) AS question_count
                FROM subjects s
                LEFT JOIN questions q ON s.id = q.subject_id
                GROUP BY s.id, s.name, s.is_locked
                ORDER BY s.id ASC""");
        assertThat(sql)
                .containsOnlyOnce("FROM subjects s")
                .containsOnlyOnce("LEFT JOIN questions q ON s.id = q.subject_id")
                .containsOnlyOnce("COUNT(q.id)")
                .doesNotContain(
                        "SELECT *",
                        "WHERE",
                        "HAVING",
                        "LIMIT",
                        "OFFSET",
                        ":",
                        "users",
                        "user_subjects",
                        "favorites",
                        "mistakes");
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
