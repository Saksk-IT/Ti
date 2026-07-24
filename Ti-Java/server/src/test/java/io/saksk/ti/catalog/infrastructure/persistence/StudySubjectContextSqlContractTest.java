package io.saksk.ti.catalog.infrastructure.persistence;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Locale;
import org.junit.jupiter.api.Test;

class StudySubjectContextSqlContractTest {

    @Test
    void exactNameLookupUsesOneCatalogStatementAndRejectsImplicitNormalization() {
        String sql = JdbcSubjectContextQueryAdapter
                .SELECT_SUBJECT_CONTEXT_BY_EXACT_NAME
                .toLowerCase(Locale.ROOT)
                .replaceAll("\\s+", " ");

        assertThat(sql)
                .contains("from subjects s")
                .contains("where s.name = :subject_name")
                .contains("order by s.id asc")
                .contains("limit 2")
                .doesNotContain("lower(")
                .doesNotContain("trim(")
                .doesNotContain("study_")
                .doesNotContain("user_bank");
    }
}
