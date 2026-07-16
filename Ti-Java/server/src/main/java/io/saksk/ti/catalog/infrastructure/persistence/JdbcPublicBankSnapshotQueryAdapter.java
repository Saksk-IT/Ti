package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.api.PublicBankBoardRef;
import io.saksk.ti.catalog.api.PublicBankBoardView;
import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankDetailView;
import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankRelationView;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.api.PublicBankSourceBreakdownView;
import io.saksk.ti.catalog.api.PublicBankSummaryView;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotInspectionPort;
import io.saksk.ti.catalog.application.port.PublicBankSnapshotQueryPort;
import io.saksk.ti.catalog.domain.PublicBankPageSlice;
import io.saksk.ti.catalog.domain.PublicBankSnapshot;
import io.saksk.ti.catalog.domain.PublicBankSnapshotResult;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.OptionalLong;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
class JdbcPublicBankSnapshotQueryAdapter
        implements PublicBankSnapshotQueryPort, PublicBankSnapshotInspectionPort {

    private static final ZoneId PUBLIC_BANK_TIME_ZONE = ZoneId.of("Asia/Shanghai");

    static final String SNAPSHOT_CTE = """
            WITH snapshot AS (
                SELECT state.generation AS state_generation,
                       state.status AS state_status,
                       state.last_success_at,
                       state.metrics_count AS expected_metrics_count,
                       state.viewer_state_count AS expected_viewer_state_count,
                       state.system_count AS expected_system_count,
                       state.user_public_count AS expected_user_public_count,
                       state.projection_digest,
                       state.projector_schema_version,
                       state.source_high_watermark,
                       metric_first.snapshot_generation AS metric_first_generation,
                       metric_first.projection_digest AS metric_first_digest,
                       metric_last.snapshot_generation AS metric_last_generation,
                       metric_last.projection_digest AS metric_last_digest,
                       viewer_first.snapshot_generation AS viewer_first_generation,
                       viewer_first.projection_digest AS viewer_first_digest,
                       viewer_last.snapshot_generation AS viewer_last_generation,
                       viewer_last.projection_digest AS viewer_last_digest
                FROM public_bank_plaza_snapshot_state state
                LEFT JOIN LATERAL (
                    SELECT snapshot_generation, projection_digest
                      FROM public_bank_plaza_metrics
                     ORDER BY snapshot_generation, projection_digest,
                              source_type, source_id
                     LIMIT 1
                ) metric_first ON true
                LEFT JOIN LATERAL (
                    SELECT snapshot_generation, projection_digest
                      FROM public_bank_plaza_metrics
                     ORDER BY snapshot_generation DESC, projection_digest DESC,
                              source_type DESC, source_id DESC
                     LIMIT 1
                ) metric_last ON true
                LEFT JOIN LATERAL (
                    SELECT snapshot_generation, projection_digest
                      FROM public_bank_plaza_viewer_state
                     ORDER BY snapshot_generation, projection_digest,
                              identity_id, source_type, source_id
                     LIMIT 1
                ) viewer_first ON true
                LEFT JOIN LATERAL (
                    SELECT snapshot_generation, projection_digest
                      FROM public_bank_plaza_viewer_state
                     ORDER BY snapshot_generation DESC, projection_digest DESC,
                              identity_id DESC, source_type DESC, source_id DESC
                     LIMIT 1
                ) viewer_last ON true
                WHERE state.snapshot_name = 'public-bank-plaza'
            )
            """;

    private static final String SNAPSHOT_COLUMNS = """
            s.state_generation,
            s.state_status,
            s.last_success_at,
            s.expected_metrics_count,
            s.expected_viewer_state_count,
            s.expected_system_count,
            s.expected_user_public_count,
            s.projection_digest,
            s.projector_schema_version,
            s.source_high_watermark,
            s.metric_first_generation,
            s.metric_first_digest,
            s.metric_last_generation,
            s.metric_last_digest,
            s.viewer_first_generation,
            s.viewer_first_digest,
            s.viewer_last_generation,
            s.viewer_last_digest
            """;

    private static final String CARD_COLUMNS = """
            m.source_type,
            m.source_id,
            m.name,
            m.description,
            m.cover_image,
            m.owner_id,
            m.owner_label,
            m.owner_avatar,
            m.question_count_total,
            m.plaza_board_id,
            m.is_featured,
            m.featured_weight,
            m.published_at,
            m.last_activity_at,
            m.join_count_total,
            m.join_users_7d,
            m.answer_count_7d,
            m.answer_users_7d,
            m.hot_score,
            m.active_score,
            m.recommended_score,
            m.join_mode,
            m.join_note,
            m.allow_copy,
            m.share_count,
            board.slug AS board_slug,
            board.name AS board_name
            """;

    private final JdbcClient jdbc;

    JdbcPublicBankSnapshotQueryAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public PublicBankSnapshot inspect() {
        return jdbc.sql(snapshotInspectionSql())
                .query((row, rowNumber) -> mapSnapshot(row))
                .optional()
                .orElseGet(PublicBankSnapshot::cold);
    }

    static String snapshotInspectionSql() {
        return SNAPSHOT_CTE + "\nSELECT " + SNAPSHOT_COLUMNS + "\nFROM snapshot s";
    }

    @Override
    public PublicBankSnapshotResult<PublicBankPageSlice> search(
        PublicBankSearchQuery query,
        OptionalLong viewerIdentityId
    ) {
        SearchStatements statements = searchStatements(query, viewerIdentityId);
        Optional<SearchCountRow> count = jdbc.sql(statements.total().sql())
                .params(statements.total().parameters())
                .query((row, rowNumber) -> new SearchCountRow(
                        mapSnapshot(row), row.getLong("result_total")))
                .optional();
        if (count.isEmpty()) {
            return new PublicBankSnapshotResult<>(
                    PublicBankSnapshot.cold(), new PublicBankPageSlice(List.of(), 0));
        }

        List<CardRow> rows = jdbc.sql(statements.page().sql())
                .params(statements.page().parameters())
                .query(JdbcPublicBankSnapshotQueryAdapter::mapCardRow)
                .list();
        assertSameSnapshot(count.orElseThrow().snapshot(), rows.stream()
                .map(CardRow::snapshot)
                .toList());
        return new PublicBankSnapshotResult<>(
                count.orElseThrow().snapshot(),
                new PublicBankPageSlice(rows.stream().map(CardRow::card).toList(),
                        count.orElseThrow().total()));
    }

    static SearchStatements searchStatements(
            PublicBankSearchQuery query,
            OptionalLong viewerIdentityId
    ) {
        String predicate = metricPredicate(query.filter(), query.sort() == PublicBankSort.FEATURED);
        Map<String, Object> filterParameters = filterParameters(query.filter());

        String totalSql = SNAPSHOT_CTE + "\nSELECT " + SNAPSHOT_COLUMNS + ",\n"
                + "       (SELECT COUNT(*) FROM public_bank_plaza_metrics m "
                + "WHERE " + predicate + ") AS result_total\n"
                + "FROM snapshot s";

        Map<String, Object> pageParameters = new LinkedHashMap<>(filterParameters);
        pageParameters.put("viewerPresent", viewerIdentityId.isPresent());
        pageParameters.put("viewerId", viewerIdentityId.orElse(0));
        pageParameters.put("limit", query.pageSize());
        pageParameters.put("offset", query.offset());
        if (!query.filter().keyword().isEmpty()) {
            pageParameters.put("keywordExact", query.filter().keyword());
            pageParameters.put("keywordPrefix", query.filter().keyword() + "%");
        }
        String rank = keywordRank(query.filter());
        String pageSql = SNAPSHOT_CTE + "\nSELECT " + SNAPSHOT_COLUMNS + ",\n"
                + CARD_COLUMNS + ",\n"
                + rank + " AS search_rank,\n"
                + "       COALESCE(viewer.has_public, false) AS relation_public,\n"
                + "       COALESCE(viewer.has_shared, false) AS relation_shared\n"
                + "FROM snapshot s\n"
                + "JOIN public_bank_plaza_metrics m ON m.snapshot_generation = s.state_generation\n"
                + "LEFT JOIN plaza_boards board ON board.id = m.plaza_board_id\n"
                + "LEFT JOIN public_bank_plaza_viewer_state viewer\n"
                + "  ON :viewerPresent AND viewer.identity_id = :viewerId\n"
                + " AND viewer.source_type = m.source_type AND viewer.source_id = m.source_id\n"
                + " AND viewer.snapshot_generation = s.state_generation\n"
                + "WHERE " + predicate + "\n"
                + "ORDER BY " + orderBy(query.sort(), !query.filter().keyword().isEmpty()) + "\n"
                + "LIMIT :limit OFFSET :offset";
        return new SearchStatements(
                new SqlStatement(totalSql, filterParameters),
                new SqlStatement(pageSql, pageParameters));
    }

    @Override
    public PublicBankSnapshotResult<List<PublicBankBoardView>> boards(PublicBankFilter filter) {
        SqlStatement statement = boardsStatement(filter);
        List<BoardRow> rows = jdbc.sql(statement.sql())
                .params(statement.parameters())
                .query(JdbcPublicBankSnapshotQueryAdapter::mapBoardRow)
                .list();
        if (rows.isEmpty()) {
            return new PublicBankSnapshotResult<>(PublicBankSnapshot.cold(), List.of());
        }
        PublicBankSnapshot snapshot = rows.getFirst().snapshot();
        assertSameSnapshot(snapshot, rows.stream().map(BoardRow::snapshot).toList());
        return new PublicBankSnapshotResult<>(snapshot, rows.stream()
                .map(BoardRow::board)
                .flatMap(Optional::stream)
                .toList());
    }

    static String boardsSql(PublicBankFilter filter) {
        String having = hasBoardMetricFilter(filter)
                ? "    HAVING COUNT(m.source_id) > 0\n"
                : "";
        return SNAPSHOT_CTE + "\nSELECT " + SNAPSHOT_COLUMNS + ",\n"
                + "       result.*\n"
                + "FROM snapshot s\n"
                + "LEFT JOIN LATERAL (\n"
                + "    SELECT board.id AS result_board_id,\n"
                + "           board.slug AS result_board_slug,\n"
                + "           board.name AS result_board_name,\n"
                + "           COALESCE(board.description, '') AS result_board_description,\n"
                + "           board.sort_order AS result_board_sort_order,\n"
                + "           COUNT(m.source_id) AS result_bank_count\n"
                + "    FROM plaza_boards board\n"
                + "    LEFT JOIN public_bank_plaza_metrics m\n"
                + "      ON m.plaza_board_id = board.id\n"
                + "     AND m.snapshot_generation = s.state_generation\n"
                + "    WHERE " + boardPredicate(filter) + "\n"
                + "    GROUP BY board.id, board.slug, board.name,\n"
                + "             board.description, board.sort_order\n"
                + having
                + "    ORDER BY board.sort_order ASC, result_bank_count DESC, board.id ASC\n"
                + ") result ON true\n"
                + "ORDER BY result.result_board_sort_order ASC,\n"
                + "         result.result_bank_count DESC, result.result_board_id ASC";
    }

    static SqlStatement boardsStatement(PublicBankFilter filter) {
        return new SqlStatement(boardsSql(filter), filterParameters(filter));
    }

    @Override
    public PublicBankSnapshotResult<List<PublicBankCardView>> hot(PublicBankHotQuery query) {
        SqlStatement statement = hotStatement(query);
        List<CardRow> rows = jdbc.sql(statement.sql())
                .params(statement.parameters())
                .query(JdbcPublicBankSnapshotQueryAdapter::mapCardRow)
                .list();
        if (rows.isEmpty()) {
            return new PublicBankSnapshotResult<>(PublicBankSnapshot.cold(), List.of());
        }
        PublicBankSnapshot snapshot = rows.getFirst().snapshot();
        assertSameSnapshot(snapshot, rows.stream().map(CardRow::snapshot).toList());
        return new PublicBankSnapshotResult<>(snapshot, rows.stream()
                .map(CardRow::optionalCard)
                .filter(Optional::isPresent)
                .map(Optional::orElseThrow)
                .toList());
    }

    static SqlStatement hotStatement(PublicBankHotQuery query) {
        Map<String, Object> parameters = filterParameters(query.filter());
        parameters.put("limit", query.limit());
        String predicate = metricPredicate(query.filter(), false);
        String sql = SNAPSHOT_CTE + "\nSELECT " + SNAPSHOT_COLUMNS + ", hot.*\n"
                + "FROM snapshot s\n"
                + "LEFT JOIN LATERAL (\n"
                + "    SELECT " + indent(CARD_COLUMNS, 11) + ",\n"
                + "           false AS relation_public, false AS relation_shared\n"
                + "    FROM public_bank_plaza_metrics m\n"
                + "    LEFT JOIN plaza_boards board ON board.id = m.plaza_board_id\n"
                + "    WHERE " + predicate + "\n"
                + "    ORDER BY m.hot_score DESC, m.published_at DESC, "
                + "m.source_id DESC, m.source_type ASC\n"
                + "    LIMIT :limit\n"
                + ") hot ON true\n"
                + "ORDER BY hot.hot_score DESC, hot.published_at DESC, "
                + "hot.source_id DESC, hot.source_type ASC";
        return new SqlStatement(sql, parameters);
    }

    @Override
    public PublicBankSnapshotResult<PublicBankSummaryView> summary(
            PublicBankFilter filter,
            Instant rollingSevenDayCutoff
    ) {
        SqlStatement statement = summaryStatement(filter, rollingSevenDayCutoff);
        Optional<SummaryRow> row = jdbc.sql(statement.sql())
                .params(statement.parameters())
                .query(JdbcPublicBankSnapshotQueryAdapter::mapSummaryRow)
                .optional();
        return row.<PublicBankSnapshotResult<PublicBankSummaryView>>map(value ->
                        new PublicBankSnapshotResult<>(value.snapshot(), value.summary()))
                .orElseGet(() -> new PublicBankSnapshotResult<>(
                        PublicBankSnapshot.cold(), emptySummary()));
    }

    static SqlStatement summaryStatement(
            PublicBankFilter filter,
            Instant rollingSevenDayCutoff
    ) {
        Map<String, Object> parameters = filterParameters(filter);
        parameters.put("publishedCutoff7d", LocalDateTime.ofInstant(
                rollingSevenDayCutoff, PUBLIC_BANK_TIME_ZONE));
        parameters.put("activityCutoff7d", rollingSevenDayCutoff.atOffset(ZoneOffset.UTC));
        String predicate = metricPredicate(filter, false);
        String activePredicate = metricPredicate("active_bank", filter, false);
        String sql = SNAPSHOT_CTE + "\nSELECT " + SNAPSHOT_COLUMNS + ",\n"
                + "       COUNT(m.source_id) AS total_banks,\n"
                + "       COALESCE(SUM(m.question_count_total), 0) AS total_questions,\n"
                + "       COUNT(DISTINCT m.plaza_board_id) AS total_boards,\n"
                + "       COUNT(m.source_id) FILTER ("
                + "WHERE m.published_at >= :publishedCutoff7d)\n"
                + "           AS new_banks_7d,\n"
                + "       COUNT(m.source_id) FILTER (WHERE m.source_type = 'system')\n"
                + "           AS system_count,\n"
                + "       COUNT(m.source_id) FILTER (WHERE m.source_type = 'user_public')\n"
                + "           AS user_public_count,\n"
                + "       (SELECT COUNT(DISTINCT active.identity_id)\n"
                + "          FROM public_bank_plaza_viewer_state active\n"
                + "          JOIN public_bank_plaza_metrics active_bank\n"
                + "            ON active_bank.source_type = active.source_type\n"
                + "           AND active_bank.source_id = active.source_id\n"
                + "           AND active_bank.snapshot_generation = s.state_generation\n"
                + "         WHERE active.snapshot_generation = s.state_generation\n"
                + "           AND active.last_activity_at >= :activityCutoff7d\n"
                + "           AND " + activePredicate + ") AS active_users_7d\n"
                + "FROM snapshot s\n"
                + "LEFT JOIN public_bank_plaza_metrics m\n"
                + "  ON " + predicate + "\n"
                + "GROUP BY " + snapshotGroupBy();
        return new SqlStatement(sql, parameters);
    }

    @Override
    public PublicBankSnapshotResult<Optional<PublicBankDetailView>> detail(
            PublicBankRef ref,
            OptionalLong viewerIdentityId
    ) {
        SqlStatement statement = detailStatement(ref, viewerIdentityId);
        Optional<DetailRow> row = jdbc.sql(statement.sql())
                .params(statement.parameters())
                .query((resultSet, rowNumber) -> mapDetailRow(
                        resultSet, viewerIdentityId))
                .optional();
        return row.<PublicBankSnapshotResult<Optional<PublicBankDetailView>>>map(value ->
                        new PublicBankSnapshotResult<>(value.snapshot(), value.detail()))
                .orElseGet(() -> new PublicBankSnapshotResult<>(
                        PublicBankSnapshot.cold(), Optional.empty()));
    }

    static SqlStatement detailStatement(
            PublicBankRef ref,
        OptionalLong viewerIdentityId
    ) {
        Map<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("detailSource", databaseSourceType(ref.source()));
        parameters.put("detailId", ref.id());
        parameters.put("viewerPresent", viewerIdentityId.isPresent());
        parameters.put("viewerId", viewerIdentityId.orElse(0));
        String sql = SNAPSHOT_CTE + "\nSELECT " + SNAPSHOT_COLUMNS + ", detail.*\n"
                + "FROM snapshot s\n"
                + "LEFT JOIN LATERAL (\n"
                + "    SELECT " + indent(CARD_COLUMNS, 11) + ",\n"
                + "           COALESCE(viewer.has_public, false) AS relation_public,\n"
                + "           COALESCE(viewer.has_shared, false) AS relation_shared\n"
                + "    FROM public_bank_plaza_metrics m\n"
                + "    LEFT JOIN plaza_boards board ON board.id = m.plaza_board_id\n"
                + "    LEFT JOIN public_bank_plaza_viewer_state viewer\n"
                + "      ON :viewerPresent AND viewer.identity_id = :viewerId\n"
                + "     AND viewer.source_type = m.source_type\n"
                + "     AND viewer.source_id = m.source_id\n"
                + "     AND viewer.snapshot_generation = s.state_generation\n"
                + "    WHERE m.snapshot_generation = s.state_generation\n"
                + "      AND m.source_type = :detailSource AND m.source_id = :detailId\n"
                + "    LIMIT 1\n"
                + ") detail ON true";
        return new SqlStatement(sql, parameters);
    }

    static String orderBy(PublicBankSort sort, boolean keywordPresent) {
        String selected = switch (sort) {
            case LATEST -> "m.published_at DESC, m.source_id DESC, m.source_type ASC";
            case HOT -> "m.hot_score DESC, m.published_at DESC, m.source_id DESC, "
                    + "m.source_type ASC";
            case ACTIVE -> "m.active_score DESC, m.last_activity_at DESC, "
                    + "m.source_id DESC, m.source_type ASC";
            case FEATURED -> "m.featured_weight DESC, m.recommended_score DESC, "
                    + "m.published_at DESC, m.source_id DESC, m.source_type ASC";
            case QUESTIONS -> "m.question_count_total DESC, m.published_at DESC, "
                    + "m.source_id DESC, m.source_type ASC";
        };
        return keywordPresent ? "search_rank DESC, " + selected : selected;
    }

    private static String metricPredicate(PublicBankFilter filter, boolean featuredOnly) {
        return metricPredicate("m", filter, featuredOnly);
    }

    private static String boardPredicate(PublicBankFilter filter) {
        List<String> predicates = new ArrayList<>();
        predicates.add("board.is_active = true");
        filter.boardId().ifPresent(ignored -> predicates.add("board.id = :boardId"));
        filter.source().ifPresent(ignored -> predicates.add("m.source_type = :sourceType"));
        if (!filter.keyword().isEmpty()) {
            predicates.add("(LOWER(m.name) LIKE :keyword OR LOWER(COALESCE("
                    + "m.description, '')) LIKE :keyword OR LOWER(COALESCE("
                    + "m.owner_label, '')) LIKE :keyword)");
        }
        return String.join(" AND ", predicates);
    }

    private static boolean hasBoardMetricFilter(PublicBankFilter filter) {
        return filter.boardId().isPresent()
                || filter.source().isPresent()
                || !filter.keyword().isEmpty();
    }

    private static String metricPredicate(
            String alias,
            PublicBankFilter filter,
            boolean featuredOnly
    ) {
        List<String> predicates = new ArrayList<>();
        predicates.add(alias + ".snapshot_generation = s.state_generation");
        filter.boardId().ifPresent(ignored ->
                predicates.add(alias + ".plaza_board_id = :boardId"));
        filter.source().ifPresent(ignored ->
                predicates.add(alias + ".source_type = :sourceType"));
        if (!filter.keyword().isEmpty()) {
            predicates.add("(LOWER(" + alias + ".name) LIKE :keyword OR LOWER(COALESCE("
                    + alias + ".description, '')) LIKE :keyword OR LOWER(COALESCE("
                    + alias + ".owner_label, '')) LIKE :keyword)");
        }
        if (featuredOnly) {
            predicates.add("COALESCE(" + alias + ".is_featured, false) = true");
        }
        return String.join(" AND ", predicates);
    }

    private static Map<String, Object> filterParameters(PublicBankFilter filter) {
        Map<String, Object> parameters = new LinkedHashMap<>();
        filter.boardId().ifPresent(value -> parameters.put("boardId", value));
        filter.source().ifPresent(value ->
                parameters.put("sourceType", databaseSourceType(value)));
        if (!filter.keyword().isEmpty()) {
            parameters.put("keyword", "%" + filter.keyword() + "%");
        }
        return parameters;
    }

    private static String keywordRank(PublicBankFilter filter) {
        if (filter.keyword().isEmpty()) {
            return "0";
        }
        return """
                (CASE
                   WHEN LOWER(m.name) = :keywordExact THEN 120
                   WHEN LOWER(m.name) LIKE :keywordPrefix THEN 90
                   WHEN LOWER(m.name) LIKE :keyword THEN 70
                   ELSE 0
                 END
                 + CASE
                   WHEN LOWER(COALESCE(m.description, '')) LIKE :keywordPrefix THEN 35
                   WHEN LOWER(COALESCE(m.description, '')) LIKE :keyword THEN 20
                   ELSE 0
                 END
                 + CASE WHEN LOWER(COALESCE(m.owner_label, '')) LIKE :keyword
                        THEN 10 ELSE 0 END)
                """.strip();
    }

    private static CardRow mapCardRow(ResultSet row, int rowNumber) throws SQLException {
        return new CardRow(mapSnapshot(row), mapCard(row));
    }

    private static Optional<PublicBankCardView> mapCard(ResultSet row) throws SQLException {
        Long id = row.getObject("source_id", Long.class);
        if (id == null) {
            return Optional.empty();
        }
        PublicBankSource source = sourceFromDatabaseType(row.getString("source_type"));
        LocalDateTime lastActivity = row.getObject("last_activity_at", LocalDateTime.class);
        LocalDateTime published = row.getObject("published_at", LocalDateTime.class);
        if (published == null) {
            published = lastActivity;
        }
        Integer boardId = row.getObject("plaza_board_id", Integer.class);
        Boolean allowCopyValue = row.getObject("allow_copy", Boolean.class);
        boolean allowCopy = source == PublicBankSource.SYSTEM
                ? false
                : allowCopyValue == null || allowCopyValue;
        String joinMode = source == PublicBankSource.SYSTEM
                ? "free"
                : defaultIfBlank(row.getString("join_mode"), "free");
        PublicBankRelationView relation = PublicBankRelationView.fromFlags(
                row.getBoolean("relation_public"), row.getBoolean("relation_shared"));
        return Optional.of(new PublicBankCardView(
                id,
                source,
                stripped(row.getString("name")),
                stripped(row.getString("description")),
                nullableEmpty(row.getString("cover_image")),
                stripped(row.getString("owner_label")),
                nullableEmpty(row.getString("owner_avatar")),
                row.getLong("question_count_total"),
                row.getLong("join_count_total"),
                row.getLong("join_users_7d"),
                row.getLong("answer_users_7d"),
                row.getLong("answer_count_7d"),
                row.getDouble("hot_score"),
                row.getDouble("active_score"),
                row.getDouble("recommended_score"),
                published,
                lastActivity,
                row.getBoolean("is_featured"),
                row.getInt("featured_weight"),
                new PublicBankBoardRef(
                        boardId,
                        nullableEmpty(row.getString("board_slug")),
                        defaultIfBlank(row.getString("board_name"), "未分板块")),
                joinMode,
                stripped(row.getString("join_note")),
                allowCopy,
                relation));
    }

    private static BoardRow mapBoardRow(ResultSet row, int rowNumber) throws SQLException {
        Integer id = row.getObject("result_board_id", Integer.class);
        Optional<PublicBankBoardView> board = id == null
                ? Optional.empty()
                : Optional.of(new PublicBankBoardView(
                        id,
                        row.getString("result_board_slug"),
                        row.getString("result_board_name"),
                        row.getString("result_board_description"),
                        row.getLong("result_bank_count")));
        return new BoardRow(mapSnapshot(row), board);
    }

    private static SummaryRow mapSummaryRow(ResultSet row, int rowNumber) throws SQLException {
        return new SummaryRow(
                mapSnapshot(row),
                new PublicBankSummaryView(
                        row.getLong("total_banks"),
                        row.getLong("total_questions"),
                        row.getLong("total_boards"),
                        row.getLong("new_banks_7d"),
                        row.getLong("active_users_7d"),
                        new PublicBankSourceBreakdownView(
                                row.getLong("system_count"),
                                row.getLong("user_public_count"))));
    }

    private static DetailRow mapDetailRow(ResultSet row, OptionalLong viewerIdentityId)
            throws SQLException {
        PublicBankSnapshot snapshot = mapSnapshot(row);
        Optional<PublicBankCardView> card = mapCard(row);
        if (card.isEmpty()) {
            return new DetailRow(snapshot, Optional.empty());
        }
        Long authorId = card.orElseThrow().source() == PublicBankSource.USER_PUBLIC
                ? row.getObject("owner_id", Long.class)
                : null;
        long shareCount = card.orElseThrow().source() == PublicBankSource.USER_PUBLIC
                ? row.getLong("share_count")
                : 0;
        boolean owner = authorId != null
                && viewerIdentityId.isPresent()
                && authorId == viewerIdentityId.orElseThrow();
        return new DetailRow(snapshot, Optional.of(new PublicBankDetailView(
                card.orElseThrow(), shareCount, authorId, owner)));
    }

    private static PublicBankSnapshot mapSnapshot(ResultSet row) throws SQLException {
        return new PublicBankSnapshot(
                true,
                row.getLong("state_generation"),
                row.getString("state_status"),
                instant(row.getObject("last_success_at")),
                row.getLong("expected_metrics_count"),
                row.getLong("expected_viewer_state_count"),
                row.getLong("expected_system_count"),
                row.getLong("expected_user_public_count"),
                row.getString("projection_digest"),
                row.getString("projector_schema_version"),
                row.getString("source_high_watermark"),
                new PublicBankSnapshot.ProjectionBoundary(
                        row.getObject("metric_first_generation", Long.class),
                        row.getString("metric_first_digest"),
                        row.getObject("metric_last_generation", Long.class),
                        row.getString("metric_last_digest")),
                new PublicBankSnapshot.ProjectionBoundary(
                        row.getObject("viewer_first_generation", Long.class),
                        row.getString("viewer_first_digest"),
                        row.getObject("viewer_last_generation", Long.class),
                        row.getString("viewer_last_digest")));
    }

    private static Instant instant(Object value) {
        return switch (value) {
            case null -> null;
            case Instant instant -> instant;
            case OffsetDateTime offset -> offset.toInstant();
            case Timestamp timestamp -> timestamp.toInstant();
            case LocalDateTime local -> local.toInstant(ZoneOffset.UTC);
            default -> throw new IllegalStateException("Unsupported snapshot timestamp type");
        };
    }

    private static PublicBankSummaryView emptySummary() {
        return new PublicBankSummaryView(
                0, 0, 0, 0, 0, new PublicBankSourceBreakdownView(0, 0));
    }

    private static String snapshotGroupBy() {
        return SNAPSHOT_COLUMNS.lines()
                .map(String::strip)
                .filter(value -> !value.isEmpty())
                .map(value -> value.endsWith(",")
                        ? value.substring(0, value.length() - 1)
                        : value)
                .reduce((left, right) -> left + ", " + right)
                .orElseThrow();
    }

    private static String indent(String value, int spaces) {
        return value.lines()
                .map(line -> " ".repeat(spaces) + line.strip())
                .reduce((left, right) -> left + "\n" + right)
                .orElse("");
    }

    private static String stripped(String value) {
        return value == null ? "" : value.strip();
    }

    private static String nullableEmpty(String value) {
        return value == null || value.isEmpty() ? null : value;
    }

    private static String defaultIfBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private static String databaseSourceType(PublicBankSource source) {
        return switch (Objects.requireNonNull(source, "source")) {
            case SYSTEM -> "system";
            case USER_PUBLIC -> "user_public";
        };
    }

    private static PublicBankSource sourceFromDatabaseType(String value) {
        return switch (Objects.requireNonNull(value, "source_type")) {
            case "system" -> PublicBankSource.SYSTEM;
            case "user_public" -> PublicBankSource.USER_PUBLIC;
            default -> throw new IllegalArgumentException("Unknown public-bank source_type");
        };
    }

    private static void assertSameSnapshot(
            PublicBankSnapshot expected,
            List<PublicBankSnapshot> observed
    ) {
        if (observed.stream().anyMatch(snapshot -> !snapshot.equals(expected))) {
            throw new IllegalStateException("Public-bank query observed mixed snapshot state");
        }
    }

    record SqlStatement(String sql, Map<String, Object> parameters) {

        SqlStatement {
            if (sql == null || sql.isBlank()) {
                throw new IllegalArgumentException("Public-bank SQL must not be blank");
            }
            parameters = Map.copyOf(Objects.requireNonNull(parameters, "parameters"));
        }
    }

    record SearchStatements(SqlStatement total, SqlStatement page) {

        SearchStatements {
            Objects.requireNonNull(total, "total");
            Objects.requireNonNull(page, "page");
        }
    }

    private record SearchCountRow(PublicBankSnapshot snapshot, long total) {}

    private record CardRow(
            PublicBankSnapshot snapshot,
            Optional<PublicBankCardView> optionalCard
    ) {
        PublicBankCardView card() {
            return optionalCard.orElseThrow(() ->
                    new IllegalStateException("Paged query returned a snapshot-only row"));
        }
    }

    private record BoardRow(
            PublicBankSnapshot snapshot,
            Optional<PublicBankBoardView> board
    ) {}

    private record SummaryRow(
            PublicBankSnapshot snapshot,
            PublicBankSummaryView summary
    ) {}

    private record DetailRow(
            PublicBankSnapshot snapshot,
            Optional<PublicBankDetailView> detail
    ) {}
}
