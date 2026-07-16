package io.saksk.ti.identity.infrastructure.persistence;

import io.saksk.ti.identity.application.port.AuthoritativeIdentityStateStore;
import io.saksk.ti.identity.domain.AuthoritativeIdentityState;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Objects;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Primary-key-only PostgreSQL lookup for current authentication and authorization state. */
@Repository
class JdbcAuthoritativeIdentityStateStore implements AuthoritativeIdentityStateStore {

    private final JdbcClient jdbc;

    JdbcAuthoritativeIdentityStateStore(JdbcClient jdbc) {
        this.jdbc = Objects.requireNonNull(jdbc, "jdbc");
    }

    @Override
    public Optional<AuthoritativeIdentityState> findById(long identityId) {
        if (identityId <= 0) {
            return Optional.empty();
        }
        return jdbc.sql("""
                        SELECT id,
                               username,
                               openid,
                               is_admin,
                               is_locked,
                               session_version,
                               is_subject_admin,
                               is_notification_admin
                        FROM users
                        WHERE id = :identityId
                        """)
                .param("identityId", identityId)
                .query(JdbcAuthoritativeIdentityStateStore::mapState)
                .optional();
    }

    static AuthoritativeIdentityState mapState(ResultSet resultSet, int rowNumber)
            throws SQLException {
        return new AuthoritativeIdentityState(
                resultSet.getLong("id"),
                resultSet.getString("username"),
                resultSet.getString("openid"),
                isTrue(resultSet.getObject("is_admin", Boolean.class)),
                isTrue(resultSet.getObject("is_locked", Boolean.class)),
                integerOrZero(resultSet.getObject("session_version", Integer.class)),
                isTrue(resultSet.getObject("is_subject_admin", Boolean.class)),
                isTrue(resultSet.getObject("is_notification_admin", Boolean.class)));
    }

    private static boolean isTrue(Boolean value) {
        return Boolean.TRUE.equals(value);
    }

    private static int integerOrZero(Integer value) {
        return value == null ? 0 : value;
    }
}
