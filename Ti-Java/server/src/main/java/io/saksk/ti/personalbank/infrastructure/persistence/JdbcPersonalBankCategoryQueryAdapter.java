package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcPersonalBankCategoryQueryAdapter implements PersonalBankCategoryQueryPort {

    static final String SELECT_PERSONAL_BANK_CATEGORIES = """
            SELECT c.id AS category_id,
                   c.user_id AS category_user_id,
                   c.name AS category_name,
                   c.description AS category_description,
                   c.sort_order AS category_sort_order,
                   c.created_at AS category_created_at,
                   c.updated_at AS category_updated_at,
                   COUNT(b.id) AS bank_count
            FROM user_bank_categories c
            LEFT JOIN user_question_banks b
                   ON b.category_id = c.id
                  AND b.status = 1
            WHERE c.user_id = :user_id
            GROUP BY c.id,
                     c.user_id,
                     c.name,
                     c.description,
                     c.sort_order,
                     c.created_at,
                     c.updated_at
            ORDER BY c.sort_order ASC NULLS LAST, c.id ASC""";

    private final JdbcClient jdbc;

    JdbcPersonalBankCategoryQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<PersonalBankCategoryView> listCategories(long userId) {
        return jdbc.sql(SELECT_PERSONAL_BANK_CATEGORIES)
                .param("user_id", userId)
                .query((row, rowNumber) -> new PersonalBankCategoryView(
                        row.getInt("category_id"),
                        row.getLong("category_user_id"),
                        row.getString("category_name"),
                        row.getString("category_description"),
                        row.getObject("category_sort_order", Integer.class),
                        row.getObject("category_created_at", LocalDateTime.class),
                        row.getObject("category_updated_at", LocalDateTime.class),
                        row.getLong("bank_count")))
                .list();
    }
}
