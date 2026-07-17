package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.api.PersonalBankShareView;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import java.sql.Types;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcPersonalBankShareQueryAdapter implements PersonalBankShareQueryPort {

    static final String SELECT_OWNER_ACTIVE_BANK = """
            SELECT id
            FROM user_question_banks
            WHERE id = :bank_id
              AND user_id = :viewer_id
              AND status = 1
            """;

    static final String SELECT_PERSONAL_BANK_SHARES = """
            SELECT id,
                   bank_id,
                   owner_id,
                   share_code,
                   share_token,
                   permission,
                   expires_at,
                   max_uses,
                   current_uses,
                   is_active,
                   created_at
            FROM bank_shares
            WHERE bank_id = :bank_id
            ORDER BY created_at DESC NULLS FIRST
            """;

    private final JdbcClient jdbc;

    JdbcPersonalBankShareQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<List<PersonalBankShareView>> findShares(long viewerId, int bankId) {
        Optional<Integer> availableBank = jdbc.sql(SELECT_OWNER_ACTIVE_BANK)
                .param("bank_id", bankId, Types.INTEGER)
                .param("viewer_id", viewerId, Types.BIGINT)
                .query(Integer.class)
                .optional();
        if (availableBank.isEmpty()) {
            return Optional.empty();
        }

        List<PersonalBankShareView> rows = jdbc.sql(SELECT_PERSONAL_BANK_SHARES)
                .param("bank_id", bankId, Types.INTEGER)
                .query((row, rowNumber) -> new PersonalBankShareView(
                        row.getInt("id"),
                        row.getInt("bank_id"),
                        row.getLong("owner_id"),
                        row.getString("share_code"),
                        row.getString("share_token"),
                        row.getString("permission"),
                        row.getObject("expires_at", LocalDateTime.class),
                        row.getObject("max_uses", Integer.class),
                        row.getObject("current_uses", Integer.class),
                        row.getObject("is_active", Boolean.class),
                        row.getObject("created_at", LocalDateTime.class)))
                .list();
        return Optional.of(List.copyOf(rows));
    }
}
