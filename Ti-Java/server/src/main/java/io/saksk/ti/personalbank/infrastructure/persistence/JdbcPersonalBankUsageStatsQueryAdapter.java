package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankUsageStatsQueryPort.SharedUserAccess;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Repository
class JdbcPersonalBankUsageStatsQueryAdapter implements PersonalBankUsageStatsQueryPort {

    static final String SELECT_BANK = """
            SELECT id,
                   user_id,
                   is_public,
                   status
            FROM user_question_banks
            WHERE id = :bank_id
            """;

    static final String SELECT_SHARED_USERS = """
            SELECT DISTINCT bsr.user_id AS user_id,
                            bs.expires_at AS expires_at
            FROM bank_share_records bsr
            JOIN bank_shares bs ON bsr.share_id = bs.id
            WHERE bsr.bank_id = :bank_id
              AND bsr.status = 1
              AND bs.is_active = TRUE
            """;

    static final String SELECT_PUBLIC_USER_IDS = """
            SELECT DISTINCT user_id
            FROM public_bank_users
            WHERE bank_id = :bank_id
            """;

    private final JdbcClient jdbc;

    JdbcPersonalBankUsageStatsQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<BankAccess> findBank(int bankId) {
        return jdbc.sql(SELECT_BANK)
                .param("bank_id", bankId, Types.INTEGER)
                .query(JdbcPersonalBankUsageStatsQueryAdapter::mapBank)
                .optional();
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public List<SharedUserAccess> listSharedUsers(int bankId) {
        List<SharedUserAccess> rows = jdbc.sql(SELECT_SHARED_USERS)
                .param("bank_id", bankId, Types.INTEGER)
                .query(JdbcPersonalBankUsageStatsQueryAdapter::mapSharedUser)
                .list();
        return List.copyOf(rows);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRES_NEW, readOnly = true)
    public List<Object> listPublicUserIds(int bankId) {
        List<Object> rows = jdbc.sql(SELECT_PUBLIC_USER_IDS)
                .param("bank_id", bankId, Types.INTEGER)
                .query(JdbcPersonalBankUsageStatsQueryAdapter::mapPublicUserId)
                .list();
        return List.copyOf(rows);
    }

    static BankAccess mapBank(ResultSet row, int rowNumber) throws SQLException {
        Number rawOwnerId = (Number) row.getObject("user_id");
        return new BankAccess(
                row.getInt("id"),
                rawOwnerId == null ? null : rawOwnerId.longValue(),
                row.getObject("is_public", Boolean.class),
                row.getObject("status", Integer.class));
    }

    static SharedUserAccess mapSharedUser(ResultSet row, int rowNumber) throws SQLException {
        return new SharedUserAccess(
                row.getObject("user_id"),
                row.getObject("expires_at"));
    }

    static Object mapPublicUserId(ResultSet row, int rowNumber) throws SQLException {
        return row.getObject("user_id");
    }
}
