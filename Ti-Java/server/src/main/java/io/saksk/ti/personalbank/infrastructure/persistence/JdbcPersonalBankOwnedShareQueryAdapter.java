package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.api.PersonalBankOwnedShareView;
import io.saksk.ti.personalbank.application.port.PersonalBankOwnedShareQueryPort;
import java.sql.Types;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcPersonalBankOwnedShareQueryAdapter implements PersonalBankOwnedShareQueryPort {

    static final String SELECT_OWNED_SHARES = """
            SELECT bs.id,
                   bs.bank_id,
                   bs.owner_id,
                   bs.share_code,
                   bs.share_token,
                   bs.permission,
                   bs.expires_at,
                   bs.max_uses,
                   bs.current_uses,
                   bs.is_active,
                   bs.created_at,
                   b.name AS bank_name
            FROM bank_shares bs
            JOIN user_question_banks b ON bs.bank_id = b.id
            WHERE bs.owner_id = :viewer_id
              AND b.status = 1
            ORDER BY bs.created_at DESC NULLS FIRST
            """;

    private final JdbcClient jdbc;

    JdbcPersonalBankOwnedShareQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<PersonalBankOwnedShareView> listOwnedShares(long viewerId) {
        List<PersonalBankOwnedShareView> rows = jdbc.sql(SELECT_OWNED_SHARES)
                .param("viewer_id", viewerId, Types.BIGINT)
                .query((row, rowNumber) -> new PersonalBankOwnedShareView(
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
                        row.getObject("created_at", LocalDateTime.class),
                        row.getString("bank_name")))
                .list();
        return List.copyOf(rows);
    }
}
