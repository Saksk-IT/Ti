package io.saksk.ti.learning.infrastructure.persistence;

import java.math.BigInteger;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.sql.DataSource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * Test-only row-transaction primitive for a future explicit migration of legacy
 * {@code bank_<bank_id>_tags} rows. This deliberately does not implement the
 * required global dry-run/preflight or a production operator. It lives outside
 * {@code src/main} and is evidence, not a runtime migration or public API.
 */
public final class LegacyPersonalBankTagMigrationEvidence {

    static final String USER_BANK_SCOPE = "user_bank";
    static final int TAG_DEFINITION_QUESTION_ID = 0;
    static final int MAX_TAG_LENGTH = 20;

    private static final Pattern STRICT_KEY =
            Pattern.compile("bank_([1-9][0-9]*)_tags");
    private static final Pattern LEGACY_QUESTION_ID =
            Pattern.compile("\\+?\\p{Nd}(?:_?\\p{Nd})*");
    private static final BigInteger MAX_QUESTION_ID =
            BigInteger.valueOf(Integer.MAX_VALUE);
    private static final ObjectMapper JSON = new ObjectMapper();

    static final String DISCOVER_SOURCE_IDS_SQL = """
            SELECT id
            FROM user_progress
            WHERE p_key ~ '^bank_[1-9][0-9]*_tags$'
            ORDER BY id
            """;

    static final String LOCK_SOURCE_ROW_SQL = """
            SELECT id, user_id, p_key, data
            FROM user_progress
            WHERE id = ?
            FOR UPDATE
            """;

    static final String TRANSACTION_ID_SQL = "SELECT txid_current()";

    static final String TARGET_ANY_ROW_SQL = """
            SELECT 1
            FROM user_question_tag_items
            WHERE user_id = ?
              AND scope = 'user_bank'
              AND scope_id = ?
            LIMIT 1
            """;

    /** Test-fixture projection only; this is not a production cross-module query/API. */
    static final String BANK_EXISTS_PROJECTION_SQL = """
            SELECT 1
            FROM phase4c_personal_bank_membership_projection
            WHERE bank_id = ?
            LIMIT 1
            """;

    /** Test-fixture projection only; it prevents cross-bank question bindings. */
    static final String QUESTION_MEMBERSHIP_PROJECTION_SQL = """
            SELECT 1
            FROM phase4c_personal_bank_membership_projection
            WHERE bank_id = ?
              AND question_id = ?
            LIMIT 1
            """;

    static final String INSERT_TARGET_SQL = """
            INSERT INTO user_question_tag_items (
                user_id, scope, scope_id, question_id, tag
            ) VALUES (?, 'user_bank', ?, ?, ?)
            ON CONFLICT (user_id, scope, scope_id, question_id, tag) DO NOTHING
            """;

    private final DataSource dataSource;

    public LegacyPersonalBankTagMigrationEvidence(DataSource dataSource) {
        this.dataSource = Objects.requireNonNull(dataSource, "dataSource");
    }

    /** Sweeps the test fixture to exercise one fresh transaction per source row. */
    public RunResult runFixturePrimitiveSweep() throws SQLException {
        return runFixturePrimitiveSweep(FaultInjector.NONE);
    }

    /** Fixture-only sweep with deterministic fault injection; not a production apply. */
    public RunResult runFixturePrimitiveSweep(FaultInjector faultInjector)
            throws SQLException {
        Objects.requireNonNull(faultInjector, "faultInjector");
        List<RowResult> rows = new ArrayList<>();
        for (long sourceRowId : discoverSourceRowIds()) {
            rows.add(runSourceRow(sourceRowId, faultInjector));
        }
        return new RunResult(rows);
    }

    /** Operator-style targeted retry/evidence hook; still opens one independent transaction. */
    public RowResult runSourceRow(long sourceRowId, FaultInjector faultInjector)
            throws SQLException {
        Objects.requireNonNull(faultInjector, "faultInjector");

        int attemptedInserts = 0;
        long transactionId = -1L;
        SourceRow source = null;
        Integer bankId = null;

        try (Connection connection = dataSource.getConnection()) {
            connection.setTransactionIsolation(Connection.TRANSACTION_SERIALIZABLE);
            connection.setAutoCommit(false);
            try {
                transactionId = transactionId(connection);
                Optional<SourceRow> locked = lockSourceRow(connection, sourceRowId);
                if (locked.isEmpty()) {
                    connection.commit();
                    return RowResult.skipped(
                            sourceRowId,
                            transactionId,
                            null,
                            null,
                            RowOutcome.SOURCE_DISAPPEARED);
                }
                source = locked.orElseThrow();

                OptionalInt parsedBankId = strictBankId(source.key());
                if (parsedBankId.isEmpty()) {
                    connection.commit();
                    return RowResult.skipped(
                            source.id(),
                            transactionId,
                            source.userId(),
                            null,
                            RowOutcome.INVALID_KEY);
                }
                bankId = parsedBankId.getAsInt();

                // Existing normalized state has absolute precedence over every
                // source-side validation or fill attempt for the tuple.
                if (targetHasAnyRow(connection, source.userId(), bankId)) {
                    connection.commit();
                    return RowResult.skipped(
                            source.id(),
                            transactionId,
                            source.userId(),
                            bankId,
                            RowOutcome.TARGET_ALREADY_PRESENT);
                }

                if (!bankExists(connection, bankId)) {
                    connection.commit();
                    return RowResult.skipped(
                            source.id(),
                            transactionId,
                            source.userId(),
                            bankId,
                            RowOutcome.BANK_MISSING);
                }

                int resolvedBankId = bankId;
                MigrationPlan plan;
                try {
                    plan = plan(
                            source.data(),
                            questionId -> questionBelongsToBank(
                                    connection, resolvedBankId, questionId));
                } catch (InvalidDataException invalid) {
                    connection.commit();
                    return RowResult.invalidData(
                            source.id(),
                            transactionId,
                            source.userId(),
                            bankId,
                            invalid.getMessage());
                } catch (OrphanQuestionException orphan) {
                    connection.commit();
                    return RowResult.skipped(
                            source.id(),
                            transactionId,
                            source.userId(),
                            bankId,
                            RowOutcome.ORPHAN_QUESTION);
                }

                int changedRows = 0;
                try (PreparedStatement insert = connection.prepareStatement(INSERT_TARGET_SQL)) {
                    for (TagInsert item : plan.inserts()) {
                        insert.setLong(1, source.userId());
                        insert.setInt(2, bankId);
                        insert.setInt(3, item.questionId());
                        insert.setString(4, item.tag());
                        changedRows += insert.executeUpdate();
                        attemptedInserts++;
                        faultInjector.afterInsert(
                                new SourceIdentity(source.id(), source.userId(), bankId),
                                attemptedInserts);
                    }
                }

                connection.commit();
                return new RowResult(
                        source.id(),
                        transactionId,
                        source.userId(),
                        bankId,
                        RowOutcome.MIGRATED,
                        attemptedInserts,
                        changedRows,
                        null);
            } catch (Exception failure) {
                try {
                    connection.rollback();
                } catch (SQLException rollbackFailure) {
                    failure.addSuppressed(rollbackFailure);
                }
                return new RowResult(
                        sourceRowId,
                        transactionId,
                        source == null ? null : source.userId(),
                        bankId,
                        RowOutcome.FAILED_ROLLED_BACK,
                        attemptedInserts,
                        0,
                        failure.getClass().getName() + ": " + String.valueOf(failure.getMessage()));
            }
        }
    }

    /** The only mutation statement in this evidence harness. */
    static List<String> mutationStatements() {
        return List.of(INSERT_TARGET_SQL);
    }

    /** Exact legacy namespace: canonical positive decimal bank id, no extra text. */
    public static OptionalInt strictBankId(String key) {
        if (key == null) {
            return OptionalInt.empty();
        }
        Matcher matcher = STRICT_KEY.matcher(key);
        if (!matcher.matches()) {
            return OptionalInt.empty();
        }
        try {
            return OptionalInt.of(Integer.parseInt(matcher.group(1)));
        } catch (NumberFormatException ignored) {
            return OptionalInt.empty();
        }
    }

    static MigrationPlan plan(String rawData, QuestionMembership membership)
            throws Exception {
        Objects.requireNonNull(membership, "membership");
        JsonNode root = parseRoot(rawData);
        if (root == null || !root.isObject()) {
            throw invalid("legacy tag payload must be a JSON object");
        }

        TagNormalizer tags = new TagNormalizer();
        LinkedHashSet<String> definitions = new LinkedHashSet<>();
        JsonNode rawDefinitions = root.get("tags");
        if (rawDefinitions != null) {
            if (!rawDefinitions.isArray()) {
                throw invalid("tags must be an array when present");
            }
            definitions.addAll(tags.cleanStringArray(rawDefinitions, "tags"));
        }

        JsonNode questionTags = root.get("question_tags");
        List<QuestionBinding> parsedBindings = new ArrayList<>();
        Map<Integer, String> normalizedQuestionIds = new LinkedHashMap<>();
        if (questionTags != null) {
            if (!questionTags.isObject()) {
                throw invalid("question_tags must be an object when present");
            }
            for (String rawQuestionId : questionTags.propertyNames()) {
                int questionId = normalizeQuestionId(rawQuestionId);
                String priorRawId = normalizedQuestionIds.putIfAbsent(
                        questionId, rawQuestionId);
                if (priorRawId != null) {
                    throw invalid("question_tags keys normalize to the same positive ID: "
                            + priorRawId + " and " + rawQuestionId);
                }
                List<String> questionBindingTags = tags.cleanQuestionValue(
                        questionTags.get(rawQuestionId),
                        "question_tags[" + rawQuestionId + "]");
                definitions.addAll(questionBindingTags);
                parsedBindings.add(new QuestionBinding(questionId, questionBindingTags));
            }
        }

        LinkedHashSet<TagInsert> bindings = new LinkedHashSet<>();
        for (QuestionBinding binding : parsedBindings) {
            if (!membership.contains(binding.questionId())) {
                throw new OrphanQuestionException(binding.questionId());
            }
            for (String tag : binding.tags()) {
                bindings.add(new TagInsert(binding.questionId(), tag));
            }
        }

        List<TagInsert> inserts = new ArrayList<>();
        for (String tag : definitions) {
            inserts.add(new TagInsert(TAG_DEFINITION_QUESTION_ID, tag));
        }
        inserts.addAll(bindings);
        return new MigrationPlan(inserts);
    }

    private List<Long> discoverSourceRowIds() throws SQLException {
        List<Long> ids = new ArrayList<>();
        try (Connection connection = dataSource.getConnection();
             PreparedStatement statement = connection.prepareStatement(DISCOVER_SOURCE_IDS_SQL);
             ResultSet rows = statement.executeQuery()) {
            while (rows.next()) {
                ids.add(rows.getLong("id"));
            }
        }
        return List.copyOf(ids);
    }

    private static long transactionId(Connection connection) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(TRANSACTION_ID_SQL);
             ResultSet row = statement.executeQuery()) {
            if (!row.next()) {
                throw new SQLException("txid_current() returned no row");
            }
            return row.getLong(1);
        }
    }

    private static Optional<SourceRow> lockSourceRow(
            Connection connection,
            long sourceRowId
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(LOCK_SOURCE_ROW_SQL)) {
            statement.setLong(1, sourceRowId);
            try (ResultSet row = statement.executeQuery()) {
                if (!row.next()) {
                    return Optional.empty();
                }
                return Optional.of(new SourceRow(
                        row.getLong("id"),
                        row.getLong("user_id"),
                        row.getString("p_key"),
                        row.getString("data")));
            }
        }
    }

    private static boolean targetHasAnyRow(
            Connection connection,
            long userId,
            int bankId
    ) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(TARGET_ANY_ROW_SQL)) {
            statement.setLong(1, userId);
            statement.setInt(2, bankId);
            try (ResultSet row = statement.executeQuery()) {
                return row.next();
            }
        }
    }

    private static boolean bankExists(Connection connection, int bankId) throws SQLException {
        try (PreparedStatement statement =
                     connection.prepareStatement(BANK_EXISTS_PROJECTION_SQL)) {
            statement.setInt(1, bankId);
            try (ResultSet row = statement.executeQuery()) {
                return row.next();
            }
        }
    }

    private static boolean questionBelongsToBank(
            Connection connection,
            int bankId,
            int questionId
    ) throws SQLException {
        try (PreparedStatement statement =
                     connection.prepareStatement(QUESTION_MEMBERSHIP_PROJECTION_SQL)) {
            statement.setInt(1, bankId);
            statement.setInt(2, questionId);
            try (ResultSet row = statement.executeQuery()) {
                return row.next();
            }
        }
    }

    private static JsonNode parseRoot(String rawData) throws InvalidDataException {
        if (rawData == null) {
            throw invalid("legacy tag payload must not be null");
        }
        try {
            return JSON.readTree(rawData);
        } catch (Exception failure) {
            throw new InvalidDataException("legacy tag payload is not valid JSON", failure);
        }
    }

    private static int normalizeQuestionId(String rawQuestionId)
            throws InvalidDataException {
        if (rawQuestionId == null) {
            throw invalid("question_tags key must not be null");
        }
        String candidate = rawQuestionId.strip();
        if (!LEGACY_QUESTION_ID.matcher(candidate).matches()) {
            throw invalid("question_tags key is not an int-compatible positive ID: "
                    + rawQuestionId);
        }
        StringBuilder decimal = new StringBuilder(candidate.length());
        for (int offset = candidate.startsWith("+") ? 1 : 0;
                offset < candidate.length();) {
            int codePoint = candidate.codePointAt(offset);
            offset += Character.charCount(codePoint);
            if (codePoint == '_') {
                continue;
            }
            int digit = Character.digit(codePoint, 10);
            if (digit < 0) {
                throw invalid("question_tags key contains a non-decimal digit: "
                        + rawQuestionId);
            }
            decimal.append((char) ('0' + digit));
        }
        BigInteger parsed = new BigInteger(decimal.toString());
        if (parsed.signum() <= 0 || parsed.compareTo(MAX_QUESTION_ID) > 0) {
            throw invalid("question_tags key is outside the positive integer range: "
                    + rawQuestionId);
        }
        return parsed.intValueExact();
    }

    private static InvalidDataException invalid(String message) {
        return new InvalidDataException(message);
    }

    private static final class TagNormalizer {
        private final Map<String, String> sourceByNormalizedTag = new LinkedHashMap<>();

        private List<String> cleanStringArray(JsonNode array, String path)
                throws InvalidDataException {
            List<String> raw = new ArrayList<>();
            int index = 0;
            for (JsonNode item : array) {
                if (!item.isString()) {
                    throw invalid(path + "[" + index + "] must be a string");
                }
                raw.add(item.asString());
                index++;
            }
            return clean(raw);
        }

        private List<String> cleanQuestionValue(JsonNode value, String path)
                throws InvalidDataException {
            if (value == null) {
                throw invalid(path + " is missing");
            }
            if (value.isArray()) {
                return cleanStringArray(value, path);
            }
            if (!value.isString()) {
                throw invalid(path + " must be a string array, encoded array, or CSV string");
            }

            String scalar = value.asString().strip();
            if (!scalar.startsWith("[")) {
                return clean(List.of(scalar.replace('，', ',').split(",", -1)));
            }

            try {
                JsonNode parsed = JSON.readTree(scalar);
                if (parsed == null || !parsed.isArray()) {
                    throw invalid(path + " encoded value must be a JSON array");
                }
                return cleanStringArray(parsed, path);
            } catch (InvalidDataException failure) {
                throw failure;
            } catch (Exception failure) {
                throw new InvalidDataException(
                        path + " encoded value is not a valid JSON array", failure);
            }
        }

        private List<String> clean(List<String> raw) throws InvalidDataException {
            LinkedHashSet<String> cleaned = new LinkedHashSet<>();
            for (String candidate : raw) {
                String source = candidate.strip();
                String tag = source;
                if (tag.codePointCount(0, tag.length()) > MAX_TAG_LENGTH) {
                    tag = tag.substring(0, tag.offsetByCodePoints(0, MAX_TAG_LENGTH)).strip();
                }
                if (tag.isEmpty() || tag.equalsIgnoreCase("all")) {
                    continue;
                }
                String priorSource = sourceByNormalizedTag.putIfAbsent(tag, source);
                if (priorSource != null && !priorSource.equals(source)) {
                    throw invalid("distinct tags truncate to the same 20-code-point value: "
                            + priorSource + " and " + source);
                }
                cleaned.add(tag);
            }
            return List.copyOf(cleaned);
        }
    }

    @FunctionalInterface
    interface QuestionMembership {
        boolean contains(int questionId) throws Exception;
    }

    @FunctionalInterface
    public interface FaultInjector {
        FaultInjector NONE = (source, insertOrdinal) -> { };

        void afterInsert(SourceIdentity source, int insertOrdinal) throws Exception;
    }

    public enum RowOutcome {
        MIGRATED,
        TARGET_ALREADY_PRESENT,
        INVALID_KEY,
        INVALID_DATA,
        BANK_MISSING,
        ORPHAN_QUESTION,
        SOURCE_DISAPPEARED,
        FAILED_ROLLED_BACK;

        public boolean blocksApply() {
            return switch (this) {
                case SOURCE_DISAPPEARED,
                        INVALID_KEY,
                        INVALID_DATA,
                        BANK_MISSING,
                        ORPHAN_QUESTION,
                        FAILED_ROLLED_BACK -> true;
                case MIGRATED, TARGET_ALREADY_PRESENT -> false;
            };
        }
    }

    public record SourceIdentity(long sourceRowId, long userId, int bankId) {
    }

    public record TagInsert(int questionId, String tag) {
        public TagInsert {
            if (questionId < 0) {
                throw new IllegalArgumentException("questionId must be non-negative");
            }
            tag = Objects.requireNonNull(tag, "tag");
            if (tag.isBlank() || tag.codePointCount(0, tag.length()) > MAX_TAG_LENGTH) {
                throw new IllegalArgumentException("tag must be 1..20 Unicode code points");
            }
        }
    }

    static final class OrphanQuestionException extends Exception {
        private OrphanQuestionException(int questionId) {
            super("question does not belong to bank: " + questionId);
        }
    }

    static final class InvalidDataException extends Exception {
        private InvalidDataException(String message) {
            super(message);
        }

        private InvalidDataException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    public record MigrationPlan(List<TagInsert> inserts) {
        public MigrationPlan {
            inserts = List.copyOf(inserts);
        }
    }

    public record RowResult(
            long sourceRowId,
            long transactionId,
            Long userId,
            Integer bankId,
            RowOutcome outcome,
            int insertStatementsAttempted,
            int insertedRowsCommitted,
            String failure
    ) {
        private static RowResult skipped(
                long sourceRowId,
                long transactionId,
                Long userId,
                Integer bankId,
                RowOutcome outcome
        ) {
            return new RowResult(
                    sourceRowId,
                    transactionId,
                    userId,
                    bankId,
                    outcome,
                    0,
                    0,
                    null);
        }

        private static RowResult invalidData(
                long sourceRowId,
                long transactionId,
                long userId,
                int bankId,
                String detail
        ) {
            return new RowResult(
                    sourceRowId,
                    transactionId,
                    userId,
                    bankId,
                    RowOutcome.INVALID_DATA,
                    0,
                    0,
                    detail);
        }
    }

    public record RunResult(List<RowResult> rows) {
        public RunResult {
            rows = List.copyOf(rows);
        }

        public int insertStatementsAttempted() {
            return rows.stream().mapToInt(RowResult::insertStatementsAttempted).sum();
        }

        public int insertedRowsCommitted() {
            return rows.stream().mapToInt(RowResult::insertedRowsCommitted).sum();
        }

        public long rollbackFailureCount() {
            return rows.stream()
                    .filter(row -> row.outcome() == RowOutcome.FAILED_ROLLED_BACK)
                    .count();
        }

        public long blockingRowCount() {
            return rows.stream().filter(row -> row.outcome().blocksApply()).count();
        }

        public boolean isApplyEligible() {
            return blockingRowCount() == 0;
        }

        public RowResult row(long sourceRowId) {
            return rows.stream()
                    .filter(candidate -> candidate.sourceRowId() == sourceRowId)
                    .findFirst()
                    .orElseThrow(() -> new IllegalArgumentException(
                            "No result for source row " + sourceRowId));
        }
    }

    private record SourceRow(long id, long userId, String key, String data) {
    }

    private record QuestionBinding(int questionId, List<String> tags) {
        private QuestionBinding {
            tags = List.copyOf(tags);
        }
    }
}
