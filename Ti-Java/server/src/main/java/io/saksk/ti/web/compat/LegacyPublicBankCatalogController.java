package io.saksk.ti.web.compat;

import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.api.PublicBankBoardView;
import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankCatalogApi;
import io.saksk.ti.catalog.api.PublicBankDetailView;
import io.saksk.ti.catalog.api.PublicBankFilter;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankPageView;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSnapshotUnavailableException;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.catalog.api.PublicBankSummaryView;
import io.saksk.ti.web.LegacyDecimalPathInteger;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import java.math.BigInteger;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.node.NullNode;

/** Compatibility HTTP adapter for the seven Phase 4A public-bank catalog reads. */
@RestController
@RequestMapping("/api/public/banks")
class LegacyPublicBankCatalogController {

    private static final Logger LOGGER =
            LoggerFactory.getLogger(LegacyPublicBankCatalogController.class);
    private static final String LEGACY_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
    private static final String LEGACY_CONVERTER_JSON_CONTENT_TYPE = "application/json";
    private static final BigInteger INTEGER_MAX = BigInteger.valueOf(Integer.MAX_VALUE);
    private static final String LONG_MAX_VALUE = Long.toString(Long.MAX_VALUE);
    private static final String LEGACY_CONVERTER_NOT_FOUND =
            "The requested URL was not found on the server. "
                    + "If you entered the URL manually please check your spelling and try again.";
    private static final DateTimeFormatter LEGACY_DATE_TIME =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss", Locale.ROOT);

    private final PublicBankCatalogApi catalog;

    LegacyPublicBankCatalogController(PublicBankCatalogApi catalog) {
        this.catalog = catalog;
    }

    @GetMapping(produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacySuccess> legacyList(
            @AuthenticationPrincipal TargetAuthenticatedPrincipal principal,
            HttpServletRequest request
    ) {
        PublicBankSort sort = legacySort(request.getParameter("sort"));
        PublicBankFilter filter = new PublicBankFilter(
                Optional.empty(),
                valueOrEmpty(request.getParameter("keyword")),
                legacySourceFilter(request.getParameter("type")));
        int page = positivePage(request.getParameter("page"), 1);
        int pageSize = legacyPageSize(request.getParameter("per_page"));
        PublicBankPageView result = catalog.search(
                new PublicBankSearchQuery(filter, sort, page, pageSize),
                viewer(principal));
        List<Map<String, Object>> banks = result.items().stream()
                .map(LegacyPublicBankCatalogController::legacyBank)
                .toList();
        Map<String, Object> data = linkedMap();
        data.put("banks", banks);
        data.put("total", result.total());
        data.put("page", result.page());
        return success(data, request);
    }

    @GetMapping(path = "/boards", produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacySuccess> boards(HttpServletRequest request) {
        PublicBankFilter filter = new PublicBankFilter(
                Optional.empty(),
                valueOrEmpty(request.getParameter("keyword")),
                Optional.empty());
        List<Map<String, Object>> items = catalog.boards(filter).stream()
                .map(LegacyPublicBankCatalogController::board)
                .toList();
        return success(Map.of("items", items), request);
    }

    @GetMapping(path = "/hot", produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacySuccess> hot(HttpServletRequest request) {
        PublicBankFilter filter = new PublicBankFilter(
                positiveLong(request.getParameter("board_id")),
                valueOrEmpty(request.getParameter("keyword")),
                Optional.empty());
        int limit = boundedSize(request.getParameter("limit"), 5, 10);
        List<Map<String, Object>> items = catalog.hot(
                        new PublicBankHotQuery(filter, limit),
                        Optional.empty())
                .stream()
                .map(LegacyPublicBankCatalogController::card)
                .toList();
        return success(Map.of("items", items), request);
    }

    @GetMapping(path = "/list", produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacySuccess> plazaList(
            @AuthenticationPrincipal TargetAuthenticatedPrincipal principal,
            HttpServletRequest request
    ) {
        PublicBankSort sort = plazaSort(request.getParameter("tab"));
        PublicBankFilter filter = new PublicBankFilter(
                positiveLong(request.getParameter("board_id")),
                valueOrEmpty(request.getParameter("keyword")),
                Optional.empty());
        int page = positivePage(request.getParameter("page"), 1);
        int pageSize = boundedSize(request.getParameter("per_page"), 12, 50);
        PublicBankPageView result = catalog.search(
                new PublicBankSearchQuery(filter, sort, page, pageSize),
                viewer(principal));
        Map<String, Object> data = linkedMap();
        data.put("items", result.items().stream()
                .map(LegacyPublicBankCatalogController::card)
                .toList());
        data.put("total", result.total());
        data.put("page", result.page());
        data.put("per_page", result.pageSize());
        data.put("tab", sortName(result.sort()));
        data.put("keyword", result.filter().keyword());
        data.put("board_id", nullable(result.filter().boardId().orElse(null)));
        data.put("available_tabs", result.availableSorts().stream()
                .map(LegacyPublicBankCatalogController::sortName)
                .toList());
        return success(data, request);
    }

    @GetMapping(path = "/summary", produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacySuccess> summary(HttpServletRequest request) {
        PublicBankFilter filter = new PublicBankFilter(
                positiveLong(request.getParameter("board_id")),
                valueOrEmpty(request.getParameter("keyword")),
                Optional.empty());
        PublicBankSummaryView result = catalog.summary(filter);
        Map<String, Object> breakdown = linkedMap();
        breakdown.put("system", result.sourceBreakdown().system());
        breakdown.put("user_public", result.sourceBreakdown().userPublic());
        Map<String, Object> data = linkedMap();
        data.put("total_banks", result.totalBanks());
        data.put("total_questions", result.totalQuestions());
        data.put("total_boards", result.totalBoards());
        data.put("new_banks_7d", result.newBanks7d());
        data.put("active_users_7d", result.activeUsers7d());
        data.put("source_breakdown", breakdown);
        return success(data, request);
    }

    @GetMapping(path = "/card/{sourceType}/{bankId}", produces = "application/json;charset=UTF-8")
    ResponseEntity<?> cardDetail(
            @PathVariable String sourceType,
            @PathVariable String bankId,
            @AuthenticationPrincipal TargetAuthenticatedPrincipal principal,
            HttpServletRequest request
    ) {
        ParsedBankId parsedId = parseBankId(bankId);
        if (parsedId.state() == BankIdParseState.INVALID) {
            return converterNotFound(request);
        }
        if (parsedId.state() == BankIdParseState.OUT_OF_RANGE) {
            return safeInternalFailure(request);
        }
        PublicBankSource source = sourceType.strip().equals("system")
                ? PublicBankSource.SYSTEM
                : PublicBankSource.USER_PUBLIC;
        return detail(new PublicBankRef(source, parsedId.value()), principal, request);
    }

    @GetMapping(path = "/{bankId}", produces = "application/json;charset=UTF-8")
    ResponseEntity<?> detailAlias(
            @PathVariable String bankId,
            @AuthenticationPrincipal TargetAuthenticatedPrincipal principal,
            HttpServletRequest request
    ) {
        ParsedBankId parsedId = parseBankId(bankId);
        if (parsedId.state() == BankIdParseState.INVALID) {
            return converterNotFound(request);
        }
        if (parsedId.state() == BankIdParseState.OUT_OF_RANGE) {
            return safeInternalFailure(request);
        }
        String requestedType = valueOrEmpty(request.getParameter("type")).strip();
        PublicBankSource source = requestedType.equals("system")
                ? PublicBankSource.SYSTEM
                : PublicBankSource.USER_PUBLIC;
        return detail(new PublicBankRef(source, parsedId.value()), principal, request);
    }

    private ResponseEntity<?> detail(
            PublicBankRef reference,
            TargetAuthenticatedPrincipal principal,
            HttpServletRequest request
    ) {
        Optional<PublicBankDetailView> found = catalog.detail(reference, viewer(principal));
        if (found.isEmpty()) {
            return legacyError(
                    HttpStatus.NOT_FOUND,
                    "题库不存在或未公开",
                    request);
        }
        return success(detail(found.orElseThrow()), request);
    }

    @ExceptionHandler(PublicBankSnapshotUnavailableException.class)
    ResponseEntity<LegacyError> snapshotUnavailable(
            PublicBankSnapshotUnavailableException exception,
            HttpServletRequest request
    ) {
        return legacyError(HttpStatus.SERVICE_UNAVAILABLE, "服务暂时不可用", request);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<LegacyError> safeFailure(Exception exception, HttpServletRequest request) {
        LOGGER.error("Public-bank catalog read failed type={}", exception.getClass().getName());
        return safeInternalFailure(request);
    }

    private static ResponseEntity<LegacySuccess> success(
            Object data,
            HttpServletRequest request
    ) {
        return compatibilityResponse(HttpStatus.OK, new LegacySuccess(
                "success", 0, data, "", RequestId.from(request)));
    }

    private static ResponseEntity<LegacyError> legacyError(
            HttpStatus status,
            String message,
            HttpServletRequest request
    ) {
        return compatibilityResponse(status, new LegacyError(
                "error", 1, message, status.value(), RequestId.from(request)));
    }

    private static ResponseEntity<LegacyError> safeInternalFailure(
            HttpServletRequest request
    ) {
        return legacyError(HttpStatus.INTERNAL_SERVER_ERROR, "服务暂时不可用", request);
    }

    private static ResponseEntity<LegacyConverterError> converterNotFound(
            HttpServletRequest request
    ) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .header(HttpHeaders.CONTENT_TYPE, LEGACY_CONVERTER_JSON_CONTENT_TYPE)
                .header(HttpHeaders.VARY, "Origin, Cookie")
                .body(new LegacyConverterError(
                        "error",
                        LEGACY_CONVERTER_NOT_FOUND,
                        HttpStatus.NOT_FOUND.value(),
                        NullNode.getInstance(),
                        RequestId.from(request)));
    }

    private static <T> ResponseEntity<T> compatibilityResponse(HttpStatus status, T body) {
        return ResponseEntity.status(status)
                .header(HttpHeaders.CONTENT_TYPE, LEGACY_JSON_CONTENT_TYPE)
                .header(HttpHeaders.VARY, "Origin, Cookie")
                .body(body);
    }

    private static Optional<AuthenticatedCatalogViewer> viewer(
            TargetAuthenticatedPrincipal principal
    ) {
        return principal == null
                ? Optional.empty()
                : Optional.of(new AuthenticatedCatalogViewer(principal.identityId()));
    }

    private static Map<String, Object> board(PublicBankBoardView board) {
        Map<String, Object> item = linkedMap();
        item.put("id", board.id());
        item.put("slug", board.slug());
        item.put("name", board.name());
        item.put("description", board.description());
        item.put("bank_count", board.bankCount());
        return item;
    }

    private static Map<String, Object> card(PublicBankCardView card) {
        Map<String, Object> board = linkedMap();
        board.put("id", nullable(card.board().id()));
        board.put("slug", nullable(card.board().slug()));
        board.put("name", card.board().name());
        Map<String, Object> relation = linkedMap();
        relation.put("joined_via", card.relation().joinedVia().name()
                .toLowerCase(Locale.ROOT));
        relation.put("is_joined", card.relation().joined());

        Map<String, Object> item = linkedMap();
        item.put("id", card.id());
        item.put("source_type", legacySourceType(card.source()));
        item.put("name", card.name());
        item.put("description", card.description());
        item.put("cover_image", nullable(card.coverImage()));
        item.put("owner_label", card.ownerLabel());
        item.put("owner_avatar", nullable(card.ownerAvatar()));
        item.put("question_count", card.questionCount());
        item.put("participants_total", card.participantsTotal());
        item.put("join_users_7d", card.joinUsers7d());
        item.put("answer_users_7d", card.answerUsers7d());
        item.put("answer_count_7d", card.answerCount7d());
        item.put("hot_score", card.hotScore());
        item.put("active_score", card.activeScore());
        item.put("recommended_score", card.recommendedScore());
        item.put("published_at", nullable(legacyDateTime(card.publishedAt())));
        item.put("last_activity_at", nullable(legacyDateTime(card.lastActivityAt())));
        item.put("is_featured", card.featured());
        item.put("featured_weight", card.featuredWeight());
        item.put("board", board);
        item.put("detail_url", legacyDetailUrl(card));
        item.put("practice_url", legacyPracticeUrl(card));
        item.put("source_label", legacySourceLabel(card.source()));
        item.put("join_mode", card.joinMode());
        item.put("join_note", card.joinNote());
        item.put("allow_copy", card.allowCopy());
        item.put("relation", relation);
        return item;
    }

    private static Map<String, Object> legacyBank(PublicBankCardView card) {
        Map<String, Object> common = card(card);
        Map<String, Object> item = linkedMap();
        item.put("id", card.id());
        item.put("name", card.name());
        item.put("description", card.description());
        item.put("cover_image", common.get("cover_image"));
        item.put("question_count", card.questionCount());
        item.put("use_count", card.participantsTotal());
        item.put("allow_copy", card.allowCopy());
        item.put("public_at", common.get("published_at"));
        item.put("created_at", common.get("published_at"));
        item.put("owner_nickname", card.ownerLabel());
        item.put("owner_avatar", common.get("owner_avatar"));
        item.put("join_mode", card.joinMode());
        item.put("join_note", card.joinNote());
        item.put("relation", common.get("relation"));
        item.put("source_type", legacySourceType(card.source()));
        item.put("source_label", legacySourceLabel(card.source()));
        item.put("participants_total", card.participantsTotal());
        item.put("answer_users_7d", card.answerUsers7d());
        item.put("bank_type", card.source() == PublicBankSource.SYSTEM ? "system" : "user");
        item.put("is_shared", 0);
        return item;
    }

    private static Map<String, Object> detail(PublicBankDetailView detail) {
        PublicBankCardView card = detail.card();
        Map<String, Object> item = card(card);
        if (card.source() == PublicBankSource.SYSTEM) {
            item.put("bank_type", "system");
            item.put("join_mode", "free");
            item.put("join_note", "系统题库当前支持免费加入。");
            item.put("allow_copy", false);
            return item;
        }
        item.put("bank_type", "user");
        item.put("share_count", detail.shareCount());
        item.put("author_id", detail.authorId());
        item.put("is_owner", detail.owner());
        return item;
    }

    private static PublicBankSort legacySort(String value) {
        return switch (valueOrEmpty(value).strip()) {
            case "popular" -> PublicBankSort.HOT;
            case "questions" -> PublicBankSort.QUESTIONS;
            case "newest" -> PublicBankSort.LATEST;
            default -> PublicBankSort.LATEST;
        };
    }

    private static PublicBankSort plazaSort(String value) {
        String normalized = valueOrDefault(value, "latest").strip().toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "hot" -> PublicBankSort.HOT;
            case "active" -> PublicBankSort.ACTIVE;
            case "featured" -> PublicBankSort.FEATURED;
            case "questions" -> PublicBankSort.QUESTIONS;
            default -> PublicBankSort.LATEST;
        };
    }

    private static Optional<PublicBankSource> legacySourceFilter(String value) {
        if ("system".equals(value)) {
            return Optional.of(PublicBankSource.SYSTEM);
        }
        if ("user".equals(value)) {
            return Optional.of(PublicBankSource.USER_PUBLIC);
        }
        return Optional.empty();
    }

    private static String legacySourceType(PublicBankSource source) {
        return switch (source) {
            case SYSTEM -> "system";
            case USER_PUBLIC -> "user_public";
        };
    }

    private static String legacySourceLabel(PublicBankSource source) {
        return switch (source) {
            case SYSTEM -> "系统题库";
            case USER_PUBLIC -> "用户公开";
        };
    }

    private static String legacyDetailUrl(PublicBankCardView card) {
        String legacySource = card.source() == PublicBankSource.SYSTEM ? "system" : "user";
        return "/public/banks/card/" + legacySource + "/" + card.id();
    }

    private static String legacyPracticeUrl(PublicBankCardView card) {
        return card.source() == PublicBankSource.SYSTEM
                ? "/subjects/" + card.id()
                : "/user/banks/" + card.id() + "/practice";
    }

    private static int positivePage(String value, int fallback) {
        BigInteger parsed = integer(value).orElse(BigInteger.valueOf(fallback));
        return parsed.max(BigInteger.ONE).min(INTEGER_MAX).intValueExact();
    }

    private static int legacyPageSize(String value) {
        Optional<BigInteger> parsed = integer(value);
        if (parsed.isEmpty()) {
            return 20;
        }
        BigInteger legacyLowerLayerValue = parsed.orElseThrow().signum() == 0
                ? BigInteger.valueOf(12)
                : parsed.orElseThrow();
        return boundedInt(legacyLowerLayerValue, 50);
    }

    private static int boundedSize(String value, int fallback, int maximum) {
        BigInteger candidate = integer(value).orElse(BigInteger.valueOf(fallback));
        if (candidate.signum() == 0) {
            candidate = BigInteger.valueOf(fallback);
        }
        return boundedInt(candidate, maximum);
    }

    private static int boundedInt(BigInteger value, int maximum) {
        return value.max(BigInteger.ONE)
                .min(BigInteger.valueOf(maximum))
                .intValueExact();
    }

    private static Optional<BigInteger> integer(String value) {
        if (value == null) {
            return Optional.empty();
        }
        try {
            return Optional.of(new BigInteger(value.strip()));
        } catch (NumberFormatException exception) {
            return Optional.empty();
        }
    }

    private static Optional<Long> positiveLong(String value) {
        if (value == null || value.isBlank()) {
            return Optional.empty();
        }
        try {
            BigInteger parsed = new BigInteger(value.strip());
            if (parsed.signum() <= 0) {
                return Optional.empty();
            }
            return Optional.of(parsed.min(BigInteger.valueOf(Long.MAX_VALUE)).longValueExact());
        } catch (NumberFormatException exception) {
            return Optional.empty();
        }
    }

    private static ParsedBankId parseBankId(String value) {
        Optional<String> normalized = LegacyDecimalPathInteger.normalize(value);
        if (normalized.isEmpty()) {
            return ParsedBankId.invalid();
        }
        String asciiDigits = normalized.orElseThrow();
        int firstSignificantDigit = asciiDigits.length();
        for (int index = 0; index < asciiDigits.length(); index++) {
            char digit = asciiDigits.charAt(index);
            if (firstSignificantDigit == asciiDigits.length() && digit != '0') {
                firstSignificantDigit = index;
            }
        }
        if (firstSignificantDigit == asciiDigits.length()) {
            return ParsedBankId.inRange(0);
        }
        int significantLength = asciiDigits.length() - firstSignificantDigit;
        if (significantLength > LONG_MAX_VALUE.length()) {
            return ParsedBankId.outOfRange();
        }
        String significantValue = asciiDigits.substring(firstSignificantDigit);
        if (significantLength == LONG_MAX_VALUE.length()
                && significantValue.compareTo(LONG_MAX_VALUE) > 0) {
            return ParsedBankId.outOfRange();
        }
        return ParsedBankId.inRange(Long.parseLong(significantValue));
    }

    private static String sortName(PublicBankSort sort) {
        return sort.name().toLowerCase(Locale.ROOT);
    }

    private static String valueOrEmpty(String value) {
        return value == null ? "" : value;
    }

    private static String valueOrDefault(String value, String fallback) {
        return value == null ? fallback : value;
    }

    private static String legacyDateTime(LocalDateTime value) {
        return value == null ? null : LEGACY_DATE_TIME.format(value);
    }

    private static Object nullable(Object value) {
        return value == null ? NullNode.getInstance() : value;
    }

    private static Map<String, Object> linkedMap() {
        return new LinkedHashMap<>();
    }

    record LegacySuccess(String status, int code, Object data, String message, String requestId) {
    }

    record LegacyError(
            String status,
            int code,
            String message,
            int statusCode,
            String requestId
    ) {
    }

    record LegacyConverterError(
            String status,
            String message,
            int statusCode,
            Object payload,
            String requestId
    ) {
    }

    private enum BankIdParseState {
        INVALID,
        IN_RANGE,
        OUT_OF_RANGE
    }

    private record ParsedBankId(BankIdParseState state, long value) {

        private static ParsedBankId invalid() {
            return new ParsedBankId(BankIdParseState.INVALID, 0);
        }

        private static ParsedBankId inRange(long value) {
            return new ParsedBankId(BankIdParseState.IN_RANGE, value);
        }

        private static ParsedBankId outOfRange() {
            return new ParsedBankId(BankIdParseState.OUT_OF_RANGE, 0);
        }
    }
}
