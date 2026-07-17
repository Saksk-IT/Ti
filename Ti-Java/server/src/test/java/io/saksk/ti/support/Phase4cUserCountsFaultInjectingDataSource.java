package io.saksk.ti.support;

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
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Pattern;
import javax.sql.DataSource;
import org.springframework.jdbc.datasource.DelegatingDataSource;

/**
 * Test-only SQL trace and PostgreSQL transaction-abort fault injector for the Phase 4C
 * personal-bank user-counts target execution suite.
 *
 * <p>Tracing is opt-in and isolated by thread. The injected statements deliberately use the
 * unwrapped physical connection so both failures occur inside the transaction under test and do
 * not recursively enter this tracer.
 */
public final class Phase4cUserCountsFaultInjectingDataSource
        extends DelegatingDataSource implements AutoCloseable {

    private static final String MISSING_COLUMN_SQL =
            "SELECT missing_phase4c_target_execution_column";
    private static final String ABORTED_TRANSACTION_PROBE_SQL = "SELECT 1";
    private static final Pattern WRITE_OPERATION = Pattern.compile(
            "\\b(?:insert\\s+into|update|delete\\s+from|merge\\s+into)\\b");
    private static final Pattern USERS_REFERENCE = Pattern.compile(
            "\\b(?:from|join|update|into|delete\\s+from|merge\\s+into)\\s+"
                    + "(?:(?:\\\"?[a-z_][a-z0-9_$]*\\\"?)\\s*\\.\\s*)?"
                    + "\\\"?users\\\"?(?=\\s|$|[,;)])");
    private static final Pattern LAST_ACTIVE_REFERENCE =
            Pattern.compile("\\blast_active\\b");
    private static final Pattern SCHEMA_MUTATION = Pattern.compile(
            "^(?:create|alter|drop|truncate|comment|grant|revoke)\\b");

    private final ThreadLocal<ActiveTrace> activeTrace = new ThreadLocal<>();

    public Phase4cUserCountsFaultInjectingDataSource(DataSource targetDataSource) {
        super(Objects.requireNonNull(targetDataSource, "targetDataSource"));
    }

    /** Starts a trace on the current thread. A {@code null} plan records without injecting. */
    public void start(FaultPlan faultPlan) {
        if (activeTrace.get() != null) {
            throw new IllegalStateException("Phase 4C user-counts SQL tracing is already active");
        }
        activeTrace.set(new ActiveTrace(faultPlan));
    }

    /** Returns an immutable point-in-time view without ending the current thread's trace. */
    public TraceSnapshot snapshot() {
        return requireActiveTrace().snapshot();
    }

    /** Ends the current thread's trace and returns its immutable final view. */
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
        return tracingConnection(super.getConnection());
    }

    @Override
    public Connection getConnection(String username, String password) throws SQLException {
        return tracingConnection(super.getConnection(username, password));
    }

    @Override
    public void close() {
        DataSource target = getTargetDataSource();
        while (target instanceof DelegatingDataSource delegating
                && delegating.getTargetDataSource() != null
                && delegating.getTargetDataSource() != target) {
            target = delegating.getTargetDataSource();
        }
        if (target instanceof HikariDataSource hikari) {
            hikari.close();
        }
    }

    private ActiveTrace requireActiveTrace() {
        ActiveTrace trace = activeTrace.get();
        if (trace == null) {
            throw new IllegalStateException("Phase 4C user-counts SQL tracing is not active");
        }
        return trace;
    }

    private Connection tracingConnection(Connection target) {
        int connectionIdentity = System.identityHashCode(target);
        return (Connection) Proxy.newProxyInstance(
                getClass().getClassLoader(),
                new Class<?>[]{Connection.class},
                (proxy, method, arguments) -> {
                    Object result = invokeReflectively(target, method, arguments);
                    ActiveTrace trace = activeTrace.get();
                    if (method.getName().equals("rollback") && trace != null) {
                        trace.recordRollback(connectionIdentity);
                    }
                    if (!(result instanceof Statement statement)) {
                        return result;
                    }
                    String preparedSql = firstSqlArgument(arguments);
                    return tracingStatement(
                            statement, target, preparedSql, connectionIdentity);
                });
    }

    private Object tracingStatement(
            Statement target,
            Connection connection,
            String preparedSql,
            int connectionIdentity
    ) {
        Class<?> statementType = target instanceof CallableStatement
                ? CallableStatement.class
                : target instanceof PreparedStatement
                        ? PreparedStatement.class
                        : Statement.class;
        InvocationHandler handler = new TracingStatementHandler(
                target, connection, preparedSql, connectionIdentity);
        return Proxy.newProxyInstance(
                getClass().getClassLoader(),
                new Class<?>[]{statementType},
                handler);
    }

    private Execution recordAndInjectIfPlanned(
            Connection connection,
            int connectionIdentity,
            String rawSql
    )
            throws SQLException {
        ActiveTrace trace = activeTrace.get();
        if (trace == null) {
            return null;
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
                writeDml,
                usersWriteDml,
                writeDml && LAST_ACTIVE_REFERENCE.matcher(normalizedSql).find(),
                isSchemaMutation(normalizedSql),
                connectionIdentity,
                trace.nextSequence());
        trace.executions.add(execution);

        if (trace.faultPlan != null && trace.faultPlan.matches(family, occurrence)) {
            injectPostgresAbort(connection, execution, trace);
        }
        return execution;
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
            // A successful probe is recorded as a missing SQLSTATE and fails the caller's
            // evidence assertion, while the original database exception remains the one thrown.
        } catch (SQLException failure) {
            poisonedFailure = failure;
        }

        trace.faults.add(new FaultObservation(
                trigger.family(),
                trigger.occurrence(),
                trigger.normalizedSql(),
                trigger.connectionReadOnly(),
                trigger.connectionIdentity(),
                trace.nextSequence(),
                initialFailure.getSQLState(),
                poisonedFailure == null ? null : poisonedFailure.getSQLState()));

        if (!"42703".equals(initialFailure.getSQLState())) {
            initialFailure.addSuppressed(new IllegalStateException(
                    "Expected missing-column SQLSTATE 42703 but observed "
                            + initialFailure.getSQLState()));
        }
        if (poisonedFailure == null || !"25P02".equals(poisonedFailure.getSQLState())) {
            initialFailure.addSuppressed(new IllegalStateException(
                    "Expected aborted-transaction SQLSTATE 25P02 but observed "
                            + (poisonedFailure == null
                                    ? "a successful SELECT 1"
                                    : poisonedFailure.getSQLState())));
        }
        throw initialFailure;
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
            boolean writeDml,
            boolean usersWriteDml,
            boolean lastActiveWriteDml,
            boolean schemaMutation,
            int connectionIdentity,
            long sequence
    ) {

        public Execution {
            Objects.requireNonNull(family, "family");
            Objects.requireNonNull(normalizedSql, "normalizedSql");
            if (occurrence < 1) {
                throw new IllegalArgumentException("occurrence must be positive");
            }
            if (sequence < 1) {
                throw new IllegalArgumentException("sequence must be positive");
            }
        }
    }

    public record ExecutionSuccess(
            Family family,
            int occurrence,
            int connectionIdentity,
            long sequence
    ) {

        public ExecutionSuccess {
            Objects.requireNonNull(family, "family");
            if (occurrence < 1 || sequence < 1) {
                throw new IllegalArgumentException(
                        "occurrence and sequence must be positive");
            }
        }
    }

    public record RollbackObservation(int connectionIdentity, long sequence) {

        public RollbackObservation {
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
            int connectionIdentity,
            long sequence,
            String initialSqlState,
            String poisonedSqlState
    ) {

        public FaultObservation {
            Objects.requireNonNull(family, "family");
            Objects.requireNonNull(normalizedSql, "normalizedSql");
            if (occurrence < 1) {
                throw new IllegalArgumentException("occurrence must be positive");
            }
            if (sequence < 1) {
                throw new IllegalArgumentException("sequence must be positive");
            }
        }

        public boolean observedExpectedAbortSequence() {
            return "42703".equals(initialSqlState) && "25P02".equals(poisonedSqlState);
        }
    }

    public record TraceSnapshot(
            List<Execution> executions,
            List<ExecutionSuccess> successes,
            List<FaultObservation> faults,
            List<RollbackObservation> rollbacks,
            Map<Family, Integer> occurrenceCounts
    ) {

        public TraceSnapshot {
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

        public long usersWriteDmlCount() {
            return executions.stream().filter(Execution::usersWriteDml).count();
        }

        public long lastActiveWriteDmlCount() {
            return executions.stream().filter(Execution::lastActiveWriteDml).count();
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
        private final int connectionIdentity;
        private final List<String> batchSql = new ArrayList<>();

        private TracingStatementHandler(
                Statement target,
                Connection connection,
                String preparedSql,
                int connectionIdentity
        ) {
            this.target = target;
            this.connection = connection;
            this.preparedSql = preparedSql;
            this.connectionIdentity = connectionIdentity;
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
                            connection, connectionIdentity, sql);
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

        private final FaultPlan faultPlan;
        private final List<Execution> executions = new ArrayList<>();
        private final List<ExecutionSuccess> successes = new ArrayList<>();
        private final List<FaultObservation> faults = new ArrayList<>();
        private final List<RollbackObservation> rollbacks = new ArrayList<>();
        private final EnumMap<Family, Integer> occurrenceCounts =
                new EnumMap<>(Family.class);
        private long sequence;

        private ActiveTrace(FaultPlan faultPlan) {
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

        private void recordRollback(int connectionIdentity) {
            rollbacks.add(new RollbackObservation(connectionIdentity, nextSequence()));
        }

        private TraceSnapshot snapshot() {
            return new TraceSnapshot(
                    executions, successes, faults, rollbacks, occurrenceCounts);
        }
    }
}
