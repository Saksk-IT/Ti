package io.saksk.ti.support;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Types;
import java.util.LinkedHashMap;
import java.util.Map;

/** JDBC-level assertions shared by the PostgreSQL 18 and 16 fixtures. */
public final class ReferenceSchemaAssertions {

    private ReferenceSchemaAssertions() {
    }

    public static void assertMinimalFixture(Connection connection) throws SQLException {
        assertThat(queryInt(connection,
                "SELECT count(*) FROM information_schema.tables "
                        + "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"))
                .isEqualTo(2);
        assertThat(queryInt(connection,
                "SELECT count(*) FROM information_schema.columns WHERE table_schema = 'public'"))
                .isEqualTo(10);

        Map<String, ColumnShape> actual = subjectColumns(connection.getMetaData());
        Map<String, ColumnShape> expected = new LinkedHashMap<>();
        expected.put("id", new ColumnShape("serial", Types.INTEGER, false, 1));
        expected.put("name", new ColumnShape("text", Types.VARCHAR, false, 2));
        expected.put("description", new ColumnShape("text", Types.VARCHAR, true, 3));
        expected.put("is_locked", new ColumnShape("bool", Types.BIT, true, 4));
        expected.put("created_at", new ColumnShape("timestamp", Types.TIMESTAMP, true, 5));
        expected.put("plaza_board_id", new ColumnShape("int4", Types.INTEGER, true, 6));
        expected.put("is_plaza_featured", new ColumnShape("bool", Types.BIT, false, 7));
        expected.put("plaza_featured_weight", new ColumnShape("int4", Types.INTEGER, false, 8));
        expected.put("plaza_featured_at", new ColumnShape("timestamp", Types.TIMESTAMP, true, 9));
        assertThat(actual).containsExactlyEntriesOf(expected);

        try (ResultSet imported = connection.getMetaData()
                .getImportedKeys(null, "public", "subjects")) {
            assertThat(imported.next()).isTrue();
            assertThat(imported.getString("FKCOLUMN_NAME")).isEqualTo("plaza_board_id");
            assertThat(imported.getString("FK_NAME")).isEqualTo("fk_subjects_plaza_board_id");
            assertThat(imported.getString("PKTABLE_NAME")).isEqualTo("plaza_boards");
            assertThat(imported.getString("PKCOLUMN_NAME")).isEqualTo("id");
            assertThat(imported.getInt("DELETE_RULE")).isEqualTo(DatabaseMetaData.importedKeySetNull);
            assertThat(imported.next()).isFalse();
        }

        try (Statement statement = connection.createStatement();
             ResultSet row = statement.executeQuery(
                     "SELECT name, plaza_board_id, is_plaza_featured "
                             + "FROM subjects ORDER BY id LIMIT 1")) {
            assertThat(row.next()).isTrue();
            assertThat(row.getString("name")).isEqualTo("Phase 2 reference subject");
            assertThat(row.getInt("plaza_board_id")).isEqualTo(1);
            assertThat(row.getBoolean("is_plaza_featured")).isTrue();
        }
    }

    public static void assertReadOnlyRole(Connection connection) throws SQLException {
        assertThat(queryText(connection, "SELECT current_user")).isEqualTo("ti_phase2_read");
        assertThat(queryText(connection, "SHOW default_transaction_read_only")).isEqualTo("on");
        assertThat(queryBoolean(connection,
                "SELECT has_database_privilege(current_user, current_database(), 'TEMPORARY')"))
                .isFalse();

        try (Statement statement = connection.createStatement();
             ResultSet role = statement.executeQuery(
                     "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication "
                             + "FROM pg_roles WHERE rolname = current_user")) {
            assertThat(role.next()).isTrue();
            assertThat(role.getBoolean("rolsuper")).isFalse();
            assertThat(role.getBoolean("rolcreatedb")).isFalse();
            assertThat(role.getBoolean("rolcreaterole")).isFalse();
            assertThat(role.getBoolean("rolreplication")).isFalse();
        }

        // default_transaction_read_only is a safety default, not an ACL: a normal role can
        // turn it off for its own session. Prove the grants still reject every write.
        try (Statement statement = connection.createStatement()) {
            statement.execute("SET default_transaction_read_only = off");
        }
        assertThat(queryText(connection, "SHOW default_transaction_read_only")).isEqualTo("off");

        try {
            assertPrivilegeRejected(connection, "INSERT INTO subjects (name) VALUES ('forbidden')");
            assertPrivilegeRejected(connection,
                    "UPDATE subjects SET description = 'forbidden' WHERE id = 1");
            assertPrivilegeRejected(connection, "DELETE FROM subjects WHERE id = 1");
            assertPrivilegeRejected(connection, "CREATE TABLE forbidden_phase2_ddl (id integer)");
            assertPrivilegeRejected(connection,
                    "CREATE TEMPORARY TABLE forbidden_phase2_temp_ddl (id integer)");
        } finally {
            try (Statement statement = connection.createStatement()) {
                statement.execute("SET default_transaction_read_only = on");
            }
        }

        assertThat(queryInt(connection, "SELECT count(*) FROM subjects")).isEqualTo(1);
    }

    public static String queryText(Connection connection, String sql) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(sql)) {
            assertThat(result.next()).isTrue();
            return result.getString(1);
        }
    }

    private static int queryInt(Connection connection, String sql) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(sql)) {
            assertThat(result.next()).isTrue();
            return result.getInt(1);
        }
    }

    private static boolean queryBoolean(Connection connection, String sql) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery(sql)) {
            assertThat(result.next()).isTrue();
            return result.getBoolean(1);
        }
    }

    private static Map<String, ColumnShape> subjectColumns(DatabaseMetaData metadata) throws SQLException {
        Map<String, ColumnShape> result = new LinkedHashMap<>();
        try (ResultSet columns = metadata.getColumns(null, "public", "subjects", null)) {
            while (columns.next()) {
                result.put(columns.getString("COLUMN_NAME"), new ColumnShape(
                        columns.getString("TYPE_NAME"),
                        columns.getInt("DATA_TYPE"),
                        columns.getInt("NULLABLE") == DatabaseMetaData.columnNullable,
                        columns.getInt("ORDINAL_POSITION")));
            }
        }
        return result;
    }

    private static void assertPrivilegeRejected(Connection connection, String sql) {
        assertThatThrownBy(() -> {
            try (Statement statement = connection.createStatement()) {
                statement.execute(sql);
            }
        }).isInstanceOf(SQLException.class)
                .satisfies(error -> assertThat(((SQLException) error).getSQLState())
                        .isEqualTo("42501"));
    }

    private record ColumnShape(String typeName, int jdbcType, boolean nullable, int ordinal) {
    }
}
