package io.saksk.ti.personalbank.infrastructure.persistence;

import io.saksk.ti.personalbank.api.PersonalBankQuestionSelection;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.BankAccess;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.QuestionFacts;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.QuestionMembership;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.RawTypeCount;
import io.saksk.ti.personalbank.application.port.PersonalBankQuestionFactsQueryPort.ShareGrant;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.jdbc.support.SqlArrayValue;
import org.springframework.stereotype.Repository;

@Repository
class JdbcPersonalBankQuestionFactsQueryAdapter
        implements PersonalBankQuestionFactsQueryPort {

    static final String SELECT_BANK_ACCESS = """
            SELECT requested_bank.id AS bank_id,
                   requested_bank.user_id AS owner_id,
                   requested_bank.is_public AS is_public,
                   requested_bank.status AS bank_status
            FROM user_question_banks requested_bank
            WHERE requested_bank.id = :bank_id
            """;

    static final String SELECT_SHARE_GRANTS = """
            SELECT bsr.id AS share_record_id,
                   bsr.bank_id AS share_record_bank_id,
                   bsr.status AS share_record_status,
                   bs.id AS share_id,
                   bs.bank_id AS share_bank_id,
                   bs.permission AS share_permission,
                   bs.is_active AS share_active,
                   bs.expires_at AS share_expires_at
            FROM user_question_banks requested_bank
            JOIN bank_share_records bsr
                   ON bsr.user_id = :viewer_id
                  AND bsr.bank_id = requested_bank.id
                  AND bsr.status = 1
            JOIN bank_shares bs
                   ON bs.id = bsr.share_id
                  AND bs.bank_id = requested_bank.id
            WHERE requested_bank.id = :bank_id
            ORDER BY bs.id ASC NULLS LAST,
                     bsr.id ASC NULLS LAST
            """;

    static final String BASE_SUMMARY = """
            SELECT q.type AS raw_type,
                   COUNT(*) AS question_count
            FROM user_bank_questions q
            WHERE q.bank_id = :bank_id""";
    static final String PORTABLE_TYPE_SQL = "\n  AND q.type = :portable_type";
    static final String CANDIDATE_QUESTION_IDS_SQL =
            "\n  AND q.id = ANY(CAST(:candidate_question_ids AS integer[]))";
    static final String GROUP_AND_ORDER_TYPES_SQL = """

            GROUP BY q.type
            ORDER BY q.type ASC
            """;

    static final String SELECT_MEMBERSHIP = """
            WITH requested_bank AS (
                SELECT EXISTS (
                    SELECT 1
                    FROM user_question_banks
                    WHERE id = :bank_id
                ) AS bank_exists
            )
            SELECT requested_bank.bank_exists,
                   q.id AS question_id
            FROM requested_bank
            LEFT JOIN user_bank_questions q
                   ON requested_bank.bank_exists
                  AND q.bank_id = :bank_id
                  AND q.id = ANY(CAST(:question_ids AS integer[]))
            ORDER BY q.id ASC
            """;

    private final JdbcClient jdbc;

    JdbcPersonalBankQuestionFactsQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<BankAccess> findAccess(long viewerId, int bankId) {
        Optional<BankRow> availableBank = jdbc.sql(SELECT_BANK_ACCESS)
                .param("bank_id", bankId, Types.INTEGER)
                .query(JdbcPersonalBankQuestionFactsQueryAdapter::mapBankRow)
                .optional();
        if (availableBank.isEmpty()) {
            return Optional.empty();
        }

        BankRow bank = availableBank.orElseThrow();
        List<ShareGrant> grants = shouldLoadShareGrants(bank, viewerId)
                ? List.copyOf(jdbc.sql(SELECT_SHARE_GRANTS)
                        .param("viewer_id", viewerId, Types.BIGINT)
                        .param("bank_id", bankId, Types.INTEGER)
                        .query(JdbcPersonalBankQuestionFactsQueryAdapter::mapShareGrant)
                        .list())
                : List.of();
        return Optional.of(new BankAccess(
                bank.bankId(),
                bank.ownerId(),
                bank.publicBank(),
                bank.bankStatus(),
                grants));
    }

    private static boolean shouldLoadShareGrants(BankRow bank, long viewerId) {
        return !Integer.valueOf(0).equals(bank.bankStatus())
                && (bank.ownerId() == null || bank.ownerId() != viewerId)
                && !Boolean.TRUE.equals(bank.publicBank());
    }

    @Override
    public QuestionFacts summarizeQuestions(PersonalBankQuestionSelection selection) {
        if (selection.candidateQuestionIds().filter(List::isEmpty).isPresent()) {
            return new QuestionFacts(0L, List.of());
        }

        JdbcClient.StatementSpec statement = jdbc.sql(sqlFor(selection))
                .param("bank_id", selection.bankId(), Types.INTEGER);
        if (selection.portableType().isPresent()) {
            statement = statement.param(
                    "portable_type", selection.portableType().orElseThrow(), Types.VARCHAR);
        }
        if (selection.candidateQuestionIds().isPresent()) {
            Object[] candidates = selection.candidateQuestionIds()
                    .orElseThrow()
                    .toArray(Integer[]::new);
            statement = statement.param(
                    "candidate_question_ids", new SqlArrayValue("integer", candidates));
        }

        List<RawTypeCount> rawTypes = List.copyOf(statement
                .query(JdbcPersonalBankQuestionFactsQueryAdapter::mapRawTypeCount)
                .list());
        long total = rawTypes.stream()
                .mapToLong(RawTypeCount::count)
                .reduce(0L, Math::addExact);
        return new QuestionFacts(total, rawTypes);
    }

    @Override
    public QuestionMembership inspectQuestionMembership(
            int bankId,
            List<Integer> questionIds
    ) {
        Object[] candidates = questionIds.toArray(Integer[]::new);
        List<MembershipRow> rows = jdbc.sql(SELECT_MEMBERSHIP)
                .param("bank_id", bankId, Types.INTEGER)
                .param("question_ids", new SqlArrayValue("integer", candidates))
                .query(JdbcPersonalBankQuestionFactsQueryAdapter::mapMembershipRow)
                .list();
        if (rows.isEmpty()) {
            throw new IllegalStateException("Membership query returned no snapshot row");
        }
        boolean bankExists = rows.getFirst().bankExists();
        List<Integer> existingIds = rows.stream()
                .map(MembershipRow::questionId)
                .flatMap(Optional::stream)
                .distinct()
                .sorted()
                .toList();
        return new QuestionMembership(bankExists, existingIds);
    }

    static String sqlFor(PersonalBankQuestionSelection selection) {
        StringBuilder sql = new StringBuilder(BASE_SUMMARY);
        selection.portableType().ifPresent(ignored -> sql.append(PORTABLE_TYPE_SQL));
        selection.candidateQuestionIds()
                .filter(candidateIds -> !candidateIds.isEmpty())
                .ifPresent(ignored -> sql.append(CANDIDATE_QUESTION_IDS_SQL));
        return sql.append(GROUP_AND_ORDER_TYPES_SQL).toString();
    }

    static BankRow mapBankRow(ResultSet row, int rowNumber) throws SQLException {
        Number rawOwnerId = (Number) row.getObject("owner_id");
        return new BankRow(
                row.getInt("bank_id"),
                rawOwnerId == null ? null : rawOwnerId.longValue(),
                row.getObject("is_public", Boolean.class),
                row.getObject("bank_status", Integer.class));
    }

    static ShareGrant mapShareGrant(ResultSet row, int rowNumber) throws SQLException {
        return new ShareGrant(
                row.getInt("share_record_id"),
                row.getInt("share_record_bank_id"),
                row.getObject("share_record_status", Integer.class),
                row.getInt("share_id"),
                row.getInt("share_bank_id"),
                row.getString("share_permission"),
                row.getObject("share_active", Boolean.class),
                row.getObject("share_expires_at", LocalDateTime.class));
    }

    static RawTypeCount mapRawTypeCount(ResultSet row, int rowNumber) throws SQLException {
        return new RawTypeCount(
                Optional.ofNullable(row.getString("raw_type")),
                row.getLong("question_count"));
    }

    static MembershipRow mapMembershipRow(ResultSet row, int rowNumber)
            throws SQLException {
        return new MembershipRow(
                row.getBoolean("bank_exists"),
                Optional.ofNullable(row.getObject("question_id", Integer.class)));
    }

    record BankRow(
            int bankId,
            Long ownerId,
            Boolean publicBank,
            Integer bankStatus
    ) {
    }

    record MembershipRow(boolean bankExists, Optional<Integer> questionId) {
    }
}
