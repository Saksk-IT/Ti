package io.saksk.ti.support;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.sql.CallableStatement;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Pattern;
import org.postgresql.PGConnection;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.AbstractDataSource;

/**
 * Dedicated dual-version PostgreSQL probe for the Phase 4C user-counts termination gate.
 *
 * <p>Each version has a single physical connection. The PostgreSQL backend PID therefore gives a
 * stable, server-observed identity across request termination, rollback, return to Hikari and the
 * following request. SQL tracing is opt-in and thread confined; fingerprint queries bypass the
 * traced facade so the application boundary remains unambiguous.
 */
public final class Phase4cUserCountsTerminationFingerprintSupport
        extends AbstractDataSource implements AutoCloseable {

    private static final String MISSING_COLUMN_SQL =
            "SELECT missing_phase4c_termination_fingerprint_column";
    private static final String ABORTED_TRANSACTION_PROBE_SQL = "SELECT 1";
    private static final Pattern WRITE_OPERATION = Pattern.compile(
            "\\b(?:insert\\s+into|update|delete\\s+from|merge\\s+into)\\b");
    private static final Pattern USERS_REFERENCE = Pattern.compile(
            "\\b(?:from|join|update|into|delete\\s+from|merge\\s+into)\\s+"
                    + "(?:(?:\\\"?[a-z_][a-z0-9_$]*\\\"?)\\s*\\.\\s*)?"
                    + "\\\"?users\\\"?(?=\\s|$|[,;)])");
    private static final Pattern LAST_ACTIVE_REFERENCE = Pattern.compile(
            "\\blast_active\\b");
    private static final Pattern SCHEMA_MUTATION = Pattern.compile(
            "^(?:create|alter|drop|truncate|comment|grant|revoke)\\b");
    private static final List<String> FINGERPRINT_TABLES = List.of(
            "users",
            "user_progress",
            "user_question_banks",
            "bank_shares",
            "bank_share_records",
            "user_bank_questions",
            "user_bank_favorites",
            "user_bank_mistakes",
            "user_question_tag_items");
    private static final Set<Family> BUSINESS_FAMILIES = Set.of(
            Family.BANK_ACCESS,
            Family.SHARE_ACCESS,
            Family.TAG_MEMBERSHIP,
            Family.FAVORITE_MEMBERSHIP,
            Family.MISTAKE_MEMBERSHIP,
            Family.QUESTION_SUMMARY);

    private final Map<PgVersion, HikariDataSource> pools;
    private final AtomicReference<PgVersion> selected =
            new AtomicReference<>(PgVersion.PG18);
    private final ThreadLocal<ActiveTrace> activeTrace = new ThreadLocal<>();

    public Phase4cUserCountsTerminationFingerprintSupport(
            Endpoint pg16,
            Endpoint pg18
    ) {
        EnumMap<PgVersion, HikariDataSource> configured = new EnumMap<>(PgVersion.class);
        configured.put(PgVersion.PG16, pool(PgVersion.PG16, pg16));
        configured.put(PgVersion.PG18, pool(PgVersion.PG18, pg18));
        pools = Map.copyOf(configured);
    }

    public void select(PgVersion version) {
        Objects.requireNonNull(version, "version");
        if (activeTrace.get() != null) {
            throw new IllegalStateException("Cannot switch PostgreSQL while tracing");
        }
        selected.set(version);
    }

    public PgVersion selectedVersion() {
        return selected.get();
    }

    public String serverVersion(PgVersion version) {
        return jdbc(version).queryForObject("SHOW server_version", String.class);
    }

    public DatabaseFingerprint fingerprint(PgVersion version) {
        JdbcTemplate jdbc = jdbc(version);
        Map<String, String> values = new LinkedHashMap<>();
        for (String table : FINGERPRINT_TABLES) {
            String hash = jdbc.queryForObject(
                    "SELECT md5(COALESCE(jsonb_agg(to_jsonb(t) "
                            + "ORDER BY to_jsonb(t)::text), '[]'::jsonb)::text) FROM "
                            + table + " t",
                    String.class);
            values.put(table, Objects.requireNonNull(hash, "fingerprint for " + table));
        }
        return new DatabaseFingerprint(values);
    }

    public long usersWithLastActive(PgVersion version) {
        Long count = jdbc(version).queryForObject(
                "SELECT COUNT(*) FROM users WHERE last_active IS NOT NULL", Long.class);
        return Objects.requireNonNull(count, "last_active count");
    }

    public void start(FaultPlan faultPlan) {
        if (activeTrace.get() != null) {
            throw new IllegalStateException("Termination fingerprint trace is already active");
        }
        activeTrace.set(new ActiveTrace(selected.get(), faultPlan));
    }

    public TraceSnapshot snapshot() {
        return requireActiveTrace().snapshot();
    }

    public TraceSnapshot stop() {
        ActiveTrace trace = requireActiveTrace();
        try {
            return trace.snapshot();
        } finally {
            activeTrace.remove();
        }
    }

    @Override
    public Connection getConnection() throws SQLException {
        PgVersion version = selected.get();
        return tracingConnection(version, pool(version).getConnection());
    }

    @Override
    public Connection getConnection(String username, String password) throws SQLException {
        PgVersion version = selected.get();
        return tracingConnection(
                version, pool(version).getConnection(username, password));
    }

    @Override
    public void close() {
        pools.values().forEach(HikariDataSource::close);
    }

    public static Set<Family> businessFamilies() {
        return BUSINESS_FAMILIES;
    }

    private JdbcTemplate jdbc(PgVersion version) {
        return new JdbcTemplate(pool(Objects.requireNonNull(version, "version")));
    }

    private HikariDataSource pool(PgVersion version) {
        return Objects.requireNonNull(pools.get(version), "pool for " + version);
    }

    private ActiveTrace requireActiveTrace() {
        ActiveTrace trace = activeTrace.get();
        if (trace == null) {
            throw new IllegalStateException("Termination fingerprint trace is not active");
        }
        return trace;
    }

    private Connection tracingConnection(PgVersion version, Connection target)
            throws SQLException {
        ConnectionIdentity identity = new ConnectionIdentity(
                version, target.unwrap(PGConnection.class).getBackendPID());
        return (Connection) Proxy.newProxyInstance(
                getClass().getClassLoader(),
                new Class<?>[]{Connection.class},
                (proxy, method, arguments) -> {
                    Object result = invokeReflectively(target, method, arguments);
                    ActiveTrace trace = activeTrace.get();
                    if (method.getName().equals("rollback") && trace != null) {
                        trace.recordRollback(identity);
                    }
                    if (!(result instanceof Statement statement)) {
                        return result;
                    }
                    String preparedSql = firstSqlArgument(arguments);
                    return tracingStatement(statement, target, preparedSql, identity);
                });
    }

    private Object tracingStatement(
            Statement target,
            Connection connection,
            String preparedSql,
            ConnectionIdentity identity
    ) {
        Class<?> statementType = target instanceof CallableStatement
                ? CallableStatement.class
                : target instanceof PreparedStatement
                        ? PreparedStatement.class
                        : Statement.class;
        InvocationHandler handler = new TracingStatementHandler(
                target, connection, preparedSql, identity);
        return Proxy.newProxyInstance(
                getClass().getClassLoader(), new Class<?>[]{statementType}, handler);
    }

    private Execution recordAndInjectIfPlanned(
            Connection connection,
            ConnectionIdentity identity,
            String rawSql
    ) throws SQLException {
        ActiveTrace trace = activeTrace.get();
        if (trace == null) {
            return null;
        }
        if (trace.version != identity.version()) {
            throw new IllegalStateException(
                    "Trace version " + trace.version + " observed " + identity.version());
        }

        String normalizedSql = normalize(rawSql);
        Family family = family(normalizedSql);
        int occurrence = trace.nextOccurrence(family);
        boolean writeDml = isWriteDml(normalizedSql);
        boolean usersWriteDml = writeDml && USERS_REFERENCE.matcher(normalizedSql).find();
        Execution execution = new Execution(
                family,
                occurrence,
                normalizedSql,
                connection.isReadOnly(),
                transactionReadOnly(connection),
                connection.getAutoCommit(),
                writeDml,
                usersWriteDml,
                writeDml && LAST_ACTIVE_REFERENCE.matcher(normalizedSql).find(),
                isSchemaMutation(normalizedSql),
                identity,
                trace.nextSequence());
        trace.executions.add(execution);

        if (trace.faultPlan != null && trace.faultPlan.matches(family, occurrence)) {
            injectPostgresAbort(connection, execution, trace);
        }
        return execution;
    }

    private static boolean transactionReadOnly(Connection connection) throws SQLException {
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery("SHOW transaction_read_only")) {
            if (!result.next()) {
                throw new SQLException("SHOW transaction_read_only returned no row");
            }
            return "on".equals(result.getString(1));
        }
    }

    private static void injectPostgresAbort(
            Connection connection,
            Execution trigger,
            ActiveTrace trace
    ) throws SQLException {
        SQLException initialFailure;
        try (Statement statement = connection.createStatement();
             ResultSet ignored = statement.executeQuery(MISSING_COLUMN_SQL)) {
            throw new IllegalStateException(
                    "PostgreSQL unexpectedly accepted the missing-column fault query");
        } catch (SQLException failure) {
            initialFailure = failure;
        }

        SQLException poisonedFailure = null;
        try (Statement statement = connection.createStatement();
             ResultSet ignored = statement.executeQuery(ABORTED_TRANSACTION_PROBE_SQL)) {
            // A successful probe is preserved as a null SQLSTATE in the evidence below.
        } catch (SQLException failure) {
            poisonedFailure = failure;
        }

        trace.faults.add(new FaultObservation(
                trigger.family(),
                trigger.occurrence(),
                trigger.normalizedSql(),
                trigger.connectionReadOnly(),
                trigger.serverTransactionReadOnly(),
                trigger.connectionIdentity(),
                trace.nextSequence(),
                initialFailure.getSQLState(),
                poisonedFailure == null ? null : poisonedFailure.getSQLState()));
        throw initialFailure;
    }

    private static HikariDataSource pool(PgVersion version, Endpoint endpoint) {
        Objects.requireNonNull(version, "version");
        Objects.requireNonNull(endpoint, "endpoint");
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl(endpoint.jdbcUrl());
        config.setUsername(endpoint.username());
        config.setPassword(endpoint.password());
        config.setPoolName("phase4c-termination-" + version.label());
        config.setMaximumPoolSize(1);
        config.setMinimumIdle(1);
        config.setConnectionTimeout(30_000L);
        config.setValidationTimeout(5_000L);
        config.addDataSourceProperty("autosave", "never");
        config.addDataSourceProperty("readOnlyMode", "transaction");
        return new HikariDataSource(config);
    }

    private static String firstSqlArgument(Object[] arguments) {
        return arguments != null
                && arguments.length > 0
                && arguments[0] instanceof String sql
                ? sql
                : null;
    }

    private static String normalize(String sql) {
        return Objects.requireNonNull(sql, "sql")
                .replaceAll("\\s+", " ")
                .strip()
                .toLowerCase(Locale.ROOT);
    }

    private static Family family(String sql) {
        if (USERS_REFERENCE.matcher(sql).find()) {
            return Family.AUTHORITY_USERS;
        }
        if (sql.contains("bank_share_records") || sql.contains("bank_shares")) {
            return Family.SHARE_ACCESS;
        }
        if (sql.contains("user_question_tag_items")) {
            return Family.TAG_MEMBERSHIP;
        }
        if (sql.contains("user_bank_favorites")) {
            return Family.FAVORITE_MEMBERSHIP;
        }
        if (sql.contains("user_bank_mistakes")) {
            return Family.MISTAKE_MEMBERSHIP;
        }
        if (sql.contains("from user_bank_questions q")
                && sql.contains("group by q.type")) {
            return Family.QUESTION_SUMMARY;
        }
        if (sql.contains("user_question_banks")) {
            return Family.BANK_ACCESS;
        }
        return Family.OTHER;
    }

    private static boolean isWriteDml(String sql) {
        return sql.startsWith("insert ")
                || sql.startsWith("update ")
                || sql.startsWith("delete ")
                || sql.startsWith("merge ")
                || sql.startsWith("with ") && WRITE_OPERATION.matcher(sql).find();
    }

    private static boolean isSchemaMutation(String sql) {
        return SCHEMA_MUTATION.matcher(sql).find();
    }

    private static boolean isExecution(Method method) {
        return method.getName().startsWith("execute");
    }

    private static Object invokeReflectively(Object target, Method method, Object[] arguments)
            throws Throwable {
        try {
            return method.invoke(target, arguments);
        } catch (InvocationTargetException exception) {
            Throwable cause = exception.getCause();
            throw cause == null ? exception : cause;
        }
    }

    public enum PgVersion {
        PG16("pg16", "16.14"),
        PG18("pg18", "18.4");

        private final String label;
        private final String serverVersion;

        PgVersion(String label, String serverVersion) {
            this.label = label;
            this.serverVersion = serverVersion;
        }

        public String label() {
            return label;
        }

        public String serverVersion() {
            return serverVersion;
        }
    }

    public enum Family {
        AUTHORITY_USERS,
        BANK_ACCESS,
        SHARE_ACCESS,
        TAG_MEMBERSHIP,
        FAVORITE_MEMBERSHIP,
        MISTAKE_MEMBERSHIP,
        QUESTION_SUMMARY,
        OTHER
    }

    public record Endpoint(String jdbcUrl, String username, String password) {

        public Endpoint {
            Objects.requireNonNull(jdbcUrl, "jdbcUrl");
            Objects.requireNonNull(username, "username");
            Objects.requireNonNull(password, "password");
        }
    }

    public record ConnectionIdentity(PgVersion version, int postgresBackendPid) {

        public ConnectionIdentity {
            Objects.requireNonNull(version, "version");
            if (postgresBackendPid <= 0) {
                throw new IllegalArgumentException("postgresBackendPid must be positive");
            }
        }
    }

    public record FaultPlan(Family family, int occurrence) {

        public FaultPlan {
            Objects.requireNonNull(family, "family");
            if (occurrence < 1) {
                throw new IllegalArgumentException("occurrence must be positive");
            }
        }

        private boolean matches(Family actualFamily, int actualOccurrence) {
            return family == actualFamily && occurrence == actualOccurrence;
        }
    }

    public record Execution(
            Family family,
            int occurrence,
            String normalizedSql,
            boolean connectionReadOnly,
            boolean serverTransactionReadOnly,
            boolean autoCommit,
            boolean writeDml,
            boolean usersWriteDml,
            boolean lastActiveWriteDml,
            boolean schemaMutation,
            ConnectionIdentity connectionIdentity,
            long sequence
    ) {

        public Execution {
            Objects.requireNonNull(family, "family");
            Objects.requireNonNull(normalizedSql, "normalizedSql");
            Objects.requireNonNull(connectionIdentity, "connectionIdentity");
            if (occurrence < 1 || sequence < 1) {
                throw new IllegalArgumentException(
                        "occurrence and sequence must be positive");
            }
        }
    }

    public record ExecutionSuccess(
            Family family,
            int occurrence,
            ConnectionIdentity connectionIdentity,
            long sequence
    ) {

        public ExecutionSuccess {
            Objects.requireNonNull(family, "family");
            Objects.requireNonNull(connectionIdentity, "connectionIdentity");
            if (occurrence < 1 || sequence < 1) {
                throw new IllegalArgumentException(
                        "occurrence and sequence must be positive");
            }
        }
    }

    public record RollbackObservation(ConnectionIdentity connectionIdentity, long sequence) {

        public RollbackObservation {
            Objects.requireNonNull(connectionIdentity, "connectionIdentity");
            if (sequence < 1) {
                throw new IllegalArgumentException("sequence must be positive");
            }
        }
    }

    public record FaultObservation(
            Family family,
            int occurrence,
            String normalizedSql,
            boolean connectionReadOnly,
            boolean serverTransactionReadOnly,
            ConnectionIdentity connectionIdentity,
            long sequence,
            String initialSqlState,
            String poisonedSqlState
    ) {

        public FaultObservation {
            Objects.requireNonNull(family, "family");
            Objects.requireNonNull(normalizedSql, "normalizedSql");
            Objects.requireNonNull(connectionIdentity, "connectionIdentity");
            if (occurrence < 1 || sequence < 1) {
                throw new IllegalArgumentException(
                        "occurrence and sequence must be positive");
            }
        }
    }

    public record DatabaseFingerprint(Map<String, String> byTable) {

        public DatabaseFingerprint {
            byTable = Map.copyOf(byTable);
            if (!byTable.keySet().equals(Set.copyOf(FINGERPRINT_TABLES))) {
                throw new IllegalArgumentException("Fingerprint must cover all nine tables");
            }
        }
    }

    public record TraceSnapshot(
            PgVersion version,
            List<Execution> executions,
            List<ExecutionSuccess> successes,
            List<FaultObservation> faults,
            List<RollbackObservation> rollbacks,
            Map<Family, Integer> occurrenceCounts
    ) {

        public TraceSnapshot {
            Objects.requireNonNull(version, "version");
            executions = List.copyOf(executions);
            successes = List.copyOf(successes);
            faults = List.copyOf(faults);
            rollbacks = List.copyOf(rollbacks);
            occurrenceCounts = Map.copyOf(occurrenceCounts);
        }

        public int occurrenceCount(Family family) {
            return occurrenceCounts.getOrDefault(
                    Objects.requireNonNull(family, "family"), 0);
        }

        public long writeDmlCount() {
            return executions.stream().filter(Execution::writeDml).count();
        }

        public long usersLastActiveWriteDmlCount() {
            return executions.stream()
                    .filter(execution -> execution.usersWriteDml()
                            && execution.lastActiveWriteDml())
                    .count();
        }

        public long schemaMutationCount() {
            return executions.stream().filter(Execution::schemaMutation).count();
        }
    }

    private final class TracingStatementHandler implements InvocationHandler {

        private final Statement target;
        private final Connection connection;
        private final String preparedSql;
        private final ConnectionIdentity identity;
        private final List<String> batchSql = new ArrayList<>();

        private TracingStatementHandler(
                Statement target,
                Connection connection,
                String preparedSql,
                ConnectionIdentity identity
        ) {
            this.target = target;
            this.connection = connection;
            this.preparedSql = preparedSql;
            this.identity = identity;
        }

        @Override
        public Object invoke(Object proxy, Method method, Object[] arguments) throws Throwable {
            if (method.getName().equals("addBatch")) {
                Object result = invokeReflectively(target, method, arguments);
                String sql = firstSqlArgument(arguments);
                batchSql.add(sql == null
                        ? Objects.requireNonNull(preparedSql, "prepared batch SQL")
                        : sql);
                return result;
            }
            if (method.getName().equals("clearBatch")) {
                Object result = invokeReflectively(target, method, arguments);
                batchSql.clear();
                return result;
            }
            if (!isExecution(method)) {
                return invokeReflectively(target, method, arguments);
            }

            boolean batchExecution = method.getName().equals("executeBatch")
                    || method.getName().equals("executeLargeBatch");
            List<String> executionSql = batchExecution && !batchSql.isEmpty()
                    ? List.copyOf(batchSql)
                    : List.of(Objects.requireNonNullElse(
                            firstSqlArgument(arguments),
                            Objects.requireNonNullElse(preparedSql, method.getName())));
            try {
                List<Execution> recorded = new ArrayList<>();
                for (String sql : executionSql) {
                    Execution execution = recordAndInjectIfPlanned(
                            connection, identity, sql);
                    if (execution != null) {
                        recorded.add(execution);
                    }
                }
                Object result = invokeReflectively(target, method, arguments);
                ActiveTrace trace = activeTrace.get();
                if (trace != null) {
                    recorded.forEach(trace::recordSuccess);
                }
                return result;
            } finally {
                if (batchExecution) {
                    batchSql.clear();
                }
            }
        }
    }

    private static final class ActiveTrace {

        private final PgVersion version;
        private final FaultPlan faultPlan;
        private final List<Execution> executions = new ArrayList<>();
        private final List<ExecutionSuccess> successes = new ArrayList<>();
        private final List<FaultObservation> faults = new ArrayList<>();
        private final List<RollbackObservation> rollbacks = new ArrayList<>();
        private final EnumMap<Family, Integer> occurrenceCounts =
                new EnumMap<>(Family.class);
        private long sequence;

        private ActiveTrace(PgVersion version, FaultPlan faultPlan) {
            this.version = Objects.requireNonNull(version, "version");
            this.faultPlan = faultPlan;
            for (Family family : Family.values()) {
                occurrenceCounts.put(family, 0);
            }
        }

        private int nextOccurrence(Family family) {
            int next = occurrenceCounts.get(family) + 1;
            occurrenceCounts.put(family, next);
            return next;
        }

        private long nextSequence() {
            return ++sequence;
        }

        private void recordSuccess(Execution execution) {
            successes.add(new ExecutionSuccess(
                    execution.family(),
                    execution.occurrence(),
                    execution.connectionIdentity(),
                    nextSequence()));
        }

        private void recordRollback(ConnectionIdentity identity) {
            rollbacks.add(new RollbackObservation(identity, nextSequence()));
        }

        private TraceSnapshot snapshot() {
            return new TraceSnapshot(
                    version,
                    executions,
                    successes,
                    faults,
                    rollbacks,
                    occurrenceCounts);
        }
    }
}
