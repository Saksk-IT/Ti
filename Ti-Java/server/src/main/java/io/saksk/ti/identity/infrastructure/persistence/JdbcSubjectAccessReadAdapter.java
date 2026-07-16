package io.saksk.ti.identity.infrastructure.persistence;

import io.saksk.ti.identity.application.port.SubjectAccessReadPort;
import io.saksk.ti.identity.domain.SubjectAccessState;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcSubjectAccessReadAdapter implements SubjectAccessReadPort {

    static final String SELECT_SUBJECT_ACCESS = """
            SELECT u.is_admin AS administrator,
                   us.subject_id AS restricted_subject_id
            FROM users u
            LEFT JOIN user_subjects us ON us.user_id = u.id
            WHERE u.id = :identityId
            ORDER BY us.subject_id ASC NULLS FIRST
            """;

    private final JdbcClient jdbc;

    JdbcSubjectAccessReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<SubjectAccessState> findByIdentityId(long identityId) {
        if (identityId <= 0) {
            return Optional.empty();
        }
        List<SubjectAccessRow> rows = jdbc.sql(SELECT_SUBJECT_ACCESS)
                .param("identityId", identityId)
                .query((resultSet, rowNumber) -> {
                    int restrictedId = resultSet.getInt("restricted_subject_id");
                    Integer nullableRestrictedId = resultSet.wasNull() ? null : restrictedId;
                    return new SubjectAccessRow(
                            resultSet.getBoolean("administrator"),
                            nullableRestrictedId);
                })
                .list();
        if (rows.isEmpty()) {
            return Optional.empty();
        }

        boolean administrator = rows.getFirst().administrator();
        Set<Integer> restricted = new LinkedHashSet<>();
        for (SubjectAccessRow row : rows) {
            if (row.administrator() != administrator) {
                throw new IllegalStateException("inconsistent identity access projection");
            }
            if (row.restrictedSubjectId() != null) {
                restricted.add(row.restrictedSubjectId());
            }
        }
        return Optional.of(new SubjectAccessState(administrator, restricted));
    }

    private record SubjectAccessRow(boolean administrator, Integer restrictedSubjectId) {
    }
}
