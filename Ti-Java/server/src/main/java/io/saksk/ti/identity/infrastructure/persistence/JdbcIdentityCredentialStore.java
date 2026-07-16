package io.saksk.ti.identity.infrastructure.persistence;

import io.saksk.ti.identity.application.port.IdentityCredentialStore;
import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.identity.domain.IdentityCredential;
import io.saksk.ti.identity.domain.LoginIdentifier;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcIdentityCredentialStore implements IdentityCredentialStore {

    private final JdbcClient jdbc;

    JdbcIdentityCredentialStore(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<IdentityCredential> findForAuthentication(LoginIdentifier identifier) {
        String column = switch (identifier.kind()) {
            case EMAIL -> "email";
            case PHONE -> "phone";
        };
        return jdbc.sql("""
                        SELECT id,
                               username,
                               password_hash,
                               is_admin,
                               is_locked,
                               session_version,
                               is_subject_admin,
                               is_notification_admin,
                               has_password_set
                        FROM users
                        WHERE %s = :identifier
                        ORDER BY id
                        LIMIT 2
                        """.formatted(column))
                .param("identifier", identifier.value())
                .query(this::mapCredential)
                .list();
    }

    @Override
    public Optional<IdentityCredential> findByIdForAuthentication(long identityId) {
        if (identityId <= 0) {
            return Optional.empty();
        }
        return jdbc.sql("""
                        SELECT id,
                               username,
                               password_hash,
                               is_admin,
                               is_locked,
                               session_version,
                               is_subject_admin,
                               is_notification_admin,
                               has_password_set
                        FROM users
                        WHERE id = :identityId
                        """)
                .param("identityId", identityId)
                .query(this::mapCredential)
                .optional();
    }

    @Override
    public boolean replacePasswordHashAndMarkSet(
            long identityId,
            String observedHash,
            int observedSessionVersion,
            String targetHash
    ) {
        return jdbc.sql("""
                        UPDATE users
                        SET password_hash = :targetHash,
                            has_password_set = true
                        WHERE id = :identityId
                          AND password_hash = :observedHash
                          AND COALESCE(session_version, 0) = :observedSessionVersion
                          AND COALESCE(is_locked, false) = false
                        """)
                .param("targetHash", targetHash)
                .param("identityId", identityId)
                .param("observedHash", observedHash)
                .param("observedSessionVersion", observedSessionVersion)
                .update() == 1;
    }

    @Override
    public Optional<IdentitySummary> confirmSuccessfulAuthentication(
            long identityId,
            String observedHash,
            int observedSessionVersion
    ) {
        if (identityId <= 0 || observedSessionVersion < 0) {
            return Optional.empty();
        }
        return jdbc.sql("""
                        SELECT id,
                               username,
                               is_admin,
                               session_version,
                               is_subject_admin,
                               is_notification_admin
                        FROM users
                        WHERE id = :identityId
                          AND password_hash = :observedHash
                          AND COALESCE(session_version, 0) = :observedSessionVersion
                          AND COALESCE(is_locked, false) = false
                        """)
                .param("identityId", identityId)
                .param("observedHash", observedHash)
                .param("observedSessionVersion", observedSessionVersion)
                .query((row, rowNumber) -> new IdentitySummary(
                        row.getLong("id"),
                        row.getString("username"),
                        Boolean.TRUE.equals(row.getObject("is_admin", Boolean.class)),
                        Boolean.TRUE.equals(row.getObject("is_subject_admin", Boolean.class)),
                        Boolean.TRUE.equals(row.getObject("is_notification_admin", Boolean.class)),
                        java.util.Objects.requireNonNullElse(
                                row.getObject("session_version", Integer.class), 0)))
                .optional();
    }

    private IdentityCredential mapCredential(ResultSet resultSet, int rowNumber) throws SQLException {
        return new IdentityCredential(
                resultSet.getLong("id"),
                resultSet.getString("username"),
                resultSet.getString("password_hash"),
                resultSet.getBoolean("is_admin"),
                resultSet.getBoolean("is_locked"),
                resultSet.getInt("session_version"),
                resultSet.getBoolean("is_subject_admin"),
                resultSet.getBoolean("is_notification_admin"),
                resultSet.getBoolean("has_password_set"));
    }
}
