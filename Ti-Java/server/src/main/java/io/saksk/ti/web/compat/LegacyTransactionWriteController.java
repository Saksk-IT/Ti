package io.saksk.ti.web.compat;

import io.saksk.ti.catalog.api.QuestionEditApplicationApi;
import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditIdempotencyKey;
import io.saksk.ti.catalog.api.QuestionEditResult;
import io.saksk.ti.catalog.api.QuestionEditView;
import io.saksk.ti.catalog.api.QuestionEditorIdentity;
import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.CheckinApplicationApi;
import io.saksk.ti.learning.api.CheckinCommand;
import io.saksk.ti.learning.api.CheckinResult;
import io.saksk.ti.learning.api.CheckinView;
import io.saksk.ti.learning.api.LearningWriteApplicationApi;
import io.saksk.ti.learning.api.LearningWriteIdempotencyKey;
import io.saksk.ti.learning.api.QuestionLearningStatusApplicationApi;
import io.saksk.ti.learning.api.QuestionLearningStatusView;
import io.saksk.ti.learning.api.QuizLimitPolicy;
import io.saksk.ti.learning.api.RecordResultApplicationApi;
import io.saksk.ti.learning.api.RecordResultCommand;
import io.saksk.ti.learning.api.RecordResultResult;
import io.saksk.ti.learning.api.StudyLearnCommand;
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterCommand;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRating;
import io.saksk.ti.learning.api.StudyReviewRecordCommand;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyScopeInput;
import io.saksk.ti.learning.api.StudyWriteApplicationApi;
import io.saksk.ti.learning.api.StudyWriteOutcome;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.learning.api.ToggleFavoriteCommand;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import io.saksk.ti.operations.api.QuizLimitPolicyApplicationApi;
import io.saksk.ti.operations.api.QuizLimitPolicyView;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/** Compatibility HTTP adapter for the Phase 4C transaction-write group. */
@RestController
final class LegacyTransactionWriteController {

    private static final Logger LOGGER =
            LoggerFactory.getLogger(LegacyTransactionWriteController.class);
    private static final String CONTENT_TYPE = "application/json; charset=utf-8";
    private static final DateTimeFormatter LEGACY_DATE_TIME =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final ObjectMapper objectMapper;
    private final LearningWriteApplicationApi favorites;
    private final RecordResultApplicationApi recordResults;
    private final StudyWriteApplicationApi study;
    private final CheckinApplicationApi checkins;
    private final QuestionEditApplicationApi questionEdits;
    private final QuestionLearningStatusApplicationApi learningStatuses;
    private final QuizLimitPolicyApplicationApi quizLimits;

    LegacyTransactionWriteController(
            ObjectMapper objectMapper,
            LearningWriteApplicationApi favorites,
            RecordResultApplicationApi recordResults,
            StudyWriteApplicationApi study,
            CheckinApplicationApi checkins,
            QuestionEditApplicationApi questionEdits,
            QuestionLearningStatusApplicationApi learningStatuses,
            QuizLimitPolicyApplicationApi quizLimits
    ) {
        this.objectMapper = objectMapper;
        this.favorites = favorites;
        this.recordResults = recordResults;
        this.study = study;
        this.checkins = checkins;
        this.questionEdits = questionEdits;
        this.learningStatuses = learningStatuses;
        this.quizLimits = quizLimits;
    }

    @PostMapping({"/api/favorite", "/api/quiz/favorite"})
    ResponseEntity<ObjectNode> favorite(
            @RequestBody(required = false) JsonNode body,
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            Authentication authentication,
            HttpServletRequest request
    ) {
        Long questionId = pythonInteger(field(body, "question_id"));
        if (questionId == null) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "question_id 参数错误");
        }
        ToggleFavoriteResult result = favorites.toggleFavorite(new ToggleFavoriteCommand(
                viewer(authentication),
                questionId,
                learningKey(idempotencyKey)));
        return switch (result.outcome()) {
            case SUCCESS -> {
                ObjectNode data = objectMapper.createObjectNode()
                        .put("is_favorite", result.favorite().orElseThrow());
                yield success(request, data);
            }
            case QUESTION_NOT_FOUND ->
                    error(request, HttpStatus.NOT_FOUND, "error", "题目不存在");
            case SUBJECT_ACCESS_DENIED ->
                    error(request, HttpStatus.FORBIDDEN, "error", "无权访问该题目");
            case IDENTITY_REJECTED ->
                    error(request, HttpStatus.NOT_FOUND, "error", "用户不存在");
            case MUTATION_REJECTED ->
                    error(
                            request,
                            HttpStatus.BAD_REQUEST,
                            "error",
                            "收藏失败：题目不存在或不可收藏");
            case IDEMPOTENCY_CONFLICT ->
                    idempotencyConflict(request);
            case IDEMPOTENCY_IN_PROGRESS ->
                    idempotencyInProgress(request);
        };
    }

    @PostMapping({"/api/record_result", "/api/quiz/record_result"})
    ResponseEntity<ObjectNode> recordResult(
            @RequestBody(required = false) JsonNode body,
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            Authentication authentication,
            HttpServletRequest request
    ) {
        JsonNode questionValue = field(body, "question_id");
        JsonNode correctValue = field(body, "is_correct");
        if (isPythonFalse(questionValue) || correctValue == null || correctValue.isNull()) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "参数不完整");
        }
        Long questionId = pythonInteger(questionValue);
        if (questionId == null) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "question_id 参数错误");
        }
        boolean correct = pythonBoolean(correctValue);
        boolean clear = parseLegacyBoolean(field(body, "clear_mistake_on_correct"), true);
        QuizLimitPolicyView policy = quizLimits.getQuizLimitPolicy();
        RecordResultResult result = recordResults.recordResult(new RecordResultCommand(
                viewer(authentication),
                questionId,
                correct,
                clear,
                new QuizLimitPolicy(policy.enabled(), policy.limitCount()),
                learningKey(idempotencyKey)));
        return switch (result.outcome()) {
            case SUCCESS -> {
                String action = result.action().orElseThrow().wireValue();
                ObjectNode response = successBody(request, objectMapper.createObjectNode()
                        .put("action", action));
                response.put("action", action);
                yield ok(response);
            }
            case QUIZ_LIMIT_REACHED -> {
                var limit = result.quizLimit().orElseThrow();
                ObjectNode data = objectMapper.createObjectNode()
                        .put("current_count", limit.currentCount())
                        .put("limit_count", limit.limitCount());
                ObjectNode response = base(
                        request,
                        "error",
                        limit.message(),
                        HttpStatus.FORBIDDEN);
                response.put("code", "QUIZ_LIMIT_REACHED");
                response.set("data", data);
                yield response(HttpStatus.FORBIDDEN, response);
            }
            case QUESTION_NOT_FOUND ->
                    error(request, HttpStatus.NOT_FOUND, "error", "题目不存在");
            case SUBJECT_ACCESS_DENIED ->
                    error(request, HttpStatus.FORBIDDEN, "error", "无权访问该题目");
            case IDENTITY_REJECTED ->
                    error(request, HttpStatus.NOT_FOUND, "error", "用户不存在");
            case MUTATION_REJECTED ->
                    error(
                            request,
                            HttpStatus.INTERNAL_SERVER_ERROR,
                            "error",
                            "记录答题结果失败");
            case IDEMPOTENCY_CONFLICT -> idempotencyConflict(request);
            case IDEMPOTENCY_IN_PROGRESS -> idempotencyInProgress(request);
        };
    }

    @PostMapping("/api/quiz/study/learn/record")
    ResponseEntity<ObjectNode> studyLearn(
            @RequestBody(required = false) JsonNode body,
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            Authentication authentication,
            HttpServletRequest request
    ) {
        Long questionId = pythonInteger(field(body, "question_id"));
        if (questionId == null) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "question_id 参数错误");
        }
        JsonNode correct = field(body, "is_correct");
        if (correct == null || correct.isNull()) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "is_correct 参数错误");
        }
        StudyWriteResult<StudyLearnView> result = study.recordLearning(new StudyLearnCommand(
                viewer(authentication),
                questionId,
                pythonBoolean(correct),
                studyScope(body),
                learningKey(idempotencyKey)));
        if (result.outcome() != StudyWriteOutcome.SUCCESS) {
            return studyError(request, result.outcome());
        }
        StudyLearnView data = result.data().orElseThrow();
        ObjectNode wire = objectMapper.createObjectNode()
                .put("streak", data.streak())
                .put("is_learned", data.learned() ? 1 : 0);
        data.nextDueAt().ifPresentOrElse(
                value -> wire.put("next_due_at", legacyDateTime(value)),
                () -> wire.putNull("next_due_at"));
        return success(request, wire);
    }

    @PostMapping("/api/quiz/study/review/record")
    ResponseEntity<ObjectNode> studyReview(
            @RequestBody(required = false) JsonNode body,
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            Authentication authentication,
            HttpServletRequest request
    ) {
        String ratingValue = textOrEmpty(field(body, "rating"))
                .strip()
                .toLowerCase(Locale.ROOT);
        Optional<StudyReviewRating> rating =
                StudyReviewRating.fromWireValue(ratingValue);
        if (rating.isEmpty()) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "rating 参数错误");
        }
        Long questionId = pythonInteger(field(body, "question_id"));
        if (questionId == null) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "question_id 参数错误");
        }
        StudyWriteResult<StudyReviewRecordView> result = study.recordReview(
                new StudyReviewRecordCommand(
                        viewer(authentication),
                        questionId,
                        rating.orElseThrow(),
                        studyScope(body),
                        learningKey(idempotencyKey)));
        if (result.outcome() != StudyWriteOutcome.SUCCESS) {
            return studyError(request, result.outcome());
        }
        StudyReviewRecordView data = result.data().orElseThrow();
        return success(request, objectMapper.createObjectNode()
                .put("review_level", data.reviewLevel())
                .put("next_due_at", legacyDateTime(data.nextDueAt())));
    }

    @PostMapping("/api/quiz/study/review/master")
    ResponseEntity<ObjectNode> studyMaster(
            @RequestBody(required = false) JsonNode body,
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            Authentication authentication,
            HttpServletRequest request
    ) {
        Long questionId = pythonInteger(field(body, "question_id"));
        if (questionId == null) {
            return error(request, HttpStatus.BAD_REQUEST, "error", "question_id 参数错误");
        }
        StudyWriteResult<StudyReviewMasterView> result = study.setReviewMastered(
                new StudyReviewMasterCommand(
                        viewer(authentication),
                        questionId,
                        parseLegacyBoolean(field(body, "is_mastered"), true),
                        studyScope(body),
                        learningKey(idempotencyKey)));
        if (result.outcome() != StudyWriteOutcome.SUCCESS) {
            return studyError(request, result.outcome());
        }
        return success(request, objectMapper.createObjectNode()
                .put("is_mastered", result.data().orElseThrow().mastered() ? 1 : 0));
    }

    @PostMapping("/api/user/checkin")
    ResponseEntity<ObjectNode> checkin(
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            Authentication authentication,
            HttpServletRequest request
    ) {
        CheckinResult result = checkins.checkIn(new CheckinCommand(
                viewer(authentication),
                learningKey(idempotencyKey)));
        if (result.outcome() == CheckinResult.Outcome.SUCCESS) {
            CheckinView data = result.data().orElseThrow();
            ObjectNode wire = objectMapper.createObjectNode()
                    .put("today", data.today().toString())
                    .put("checked_in_today", data.checkedInToday())
                    .put("streak_days", data.streakDays())
                    .put("total_days", data.totalDays())
                    .put("just_checked_in", data.justCheckedIn());
            data.checkedInAt().ifPresentOrElse(
                    value -> wire.put("checked_in_at", legacyDateTime(value)),
                    () -> wire.putNull("checked_in_at"));
            ArrayNode dates = wire.putArray("checked_dates");
            data.checkedDates().forEach(dates::add);
            return success(request, wire);
        }
        return switch (result.outcome()) {
            case MUTATION_REJECTED ->
                    error(
                            request,
                            HttpStatus.INTERNAL_SERVER_ERROR,
                            "error",
                            "签到失败，请稍后重试");
            case IDEMPOTENCY_CONFLICT -> idempotencyConflict(request);
            case IDEMPOTENCY_IN_PROGRESS -> idempotencyInProgress(request);
            case SUCCESS -> throw new IllegalStateException("Handled above");
        };
    }

    @PutMapping("/api/quiz/questions/{questionId}")
    ResponseEntity<ObjectNode> editQuestion(
            @PathVariable String questionId,
            @RequestBody(required = false) JsonNode body,
            @RequestHeader(name = "Idempotency-Key", required = false) String idempotencyKey,
            Authentication authentication,
            HttpServletRequest request
    ) {
        for (String field : new String[]{"content", "q_type", "answer", "explanation"}) {
            JsonNode value = field(body, field);
            if (value != null && !value.isNull() && !value.isTextual()) {
                return error(
                        request,
                        HttpStatus.BAD_REQUEST,
                        "error",
                        field + " 必须为字符串");
            }
        }
        Long parsedQuestionId = pythonIntegerText(questionId);
        if (parsedQuestionId == null || parsedQuestionId < 0) {
            return error(request, HttpStatus.NOT_FOUND, "error", "题目不存在");
        }
        TargetAuthenticatedPrincipal principal = principal(authentication);
        QuestionEditResult result = questionEdits.editQuestion(new QuestionEditCommand(
                new QuestionEditorIdentity(
                        principal.identityId(),
                        hasRole(authentication, "ROLE_ADMIN"),
                        hasRole(authentication, "ROLE_SUBJECT_ADMIN")),
                parsedQuestionId,
                optionalText(body, "content"),
                optionalText(body, "q_type"),
                optionalText(body, "answer"),
                optionalText(body, "explanation"),
                optionalOptions(body),
                questionKey(idempotencyKey)));
        return switch (result.outcome()) {
            case SUCCESS -> questionEditSuccess(
                    request,
                    principal.identityId(),
                    result.data().orElseThrow());
            case FORBIDDEN ->
                    error(
                            request,
                            HttpStatus.FORBIDDEN,
                            "forbidden",
                            "需要管理员或科目管理员权限");
            case QUESTION_NOT_FOUND ->
                    error(request, HttpStatus.NOT_FOUND, "error", "题目不存在");
            case INVALID_MULTI_CHOICE_ANSWER ->
                    error(
                            request,
                            HttpStatus.BAD_REQUEST,
                            "error",
                            result.detail().orElseThrow());
            case MUTATION_REJECTED ->
                    error(
                            request,
                            HttpStatus.INTERNAL_SERVER_ERROR,
                            "error",
                            "题目更新失败");
            case IDEMPOTENCY_CONFLICT -> idempotencyConflict(request);
            case IDEMPOTENCY_IN_PROGRESS -> idempotencyInProgress(request);
        };
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ObjectNode> safeFailure(
            Exception exception,
            HttpServletRequest request
    ) {
        LOGGER.error("Transaction-write request failed type={}",
                exception.getClass().getName());
        String path = request.getRequestURI();
        if (path != null && path.endsWith("/user/checkin")) {
            return error(
                    request,
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "error",
                    "签到失败，请稍后重试");
        }
        ObjectNode body = base(
                request,
                "error",
                "An unexpected server error occurred.",
                HttpStatus.INTERNAL_SERVER_ERROR);
        body.putNull("payload");
        return response(HttpStatus.INTERNAL_SERVER_ERROR, body);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<ObjectNode> malformedJson(
            HttpMessageNotReadableException exception,
            HttpServletRequest request
    ) {
        String path = request.getRequestURI();
        String message;
        if (path != null && (path.equals("/api/favorite")
                || path.equals("/api/quiz/favorite")
                || path.equals("/api/quiz/study/learn/record")
                || path.equals("/api/quiz/study/review/master"))) {
            message = "question_id 参数错误";
        } else if (path != null && (path.equals("/api/record_result")
                || path.equals("/api/quiz/record_result"))) {
            message = "参数不完整";
        } else if (path != null
                && path.equals("/api/quiz/study/review/record")) {
            message = "rating 参数错误";
        } else {
            message = "请求数据格式错误";
        }
        return error(request, HttpStatus.BAD_REQUEST, "error", message);
    }

    @ExceptionHandler(InvalidIdempotencyKeyException.class)
    ResponseEntity<ObjectNode> invalidIdempotencyKey(
            InvalidIdempotencyKeyException exception,
            HttpServletRequest request
    ) {
        return error(
                request,
                HttpStatus.BAD_REQUEST,
                "error",
                "Idempotency-Key 参数错误");
    }

    private ResponseEntity<ObjectNode> questionEditSuccess(
            HttpServletRequest request,
            long identityId,
            QuestionEditView data
    ) {
        QuestionLearningStatusView status = learningStatuses.findStatus(
                new AuthenticatedLearningViewer(identityId),
                data.id());
        ObjectNode wire = objectMapper.createObjectNode()
                .put("id", data.id())
                .put("content", data.content())
                .put("q_type", data.questionType());
        ArrayNode options = wire.putArray("options");
        data.options().forEach(option -> options.add(objectMapper.createObjectNode()
                .put("key", option.key())
                .put("value", option.value())));
        wire.put("answer", data.answer())
                .put("explanation", data.explanation());
        data.imagePath().ifPresentOrElse(
                value -> wire.put("image_path", value),
                () -> wire.putNull("image_path"));
        wire.put("subject", data.subject())
                .put("is_fav", status.favorite() ? 1 : 0)
                .put("is_mistake", status.mistake() ? 1 : 0);
        return success(request, wire);
    }

    private ResponseEntity<ObjectNode> studyError(
            HttpServletRequest request,
            StudyWriteOutcome outcome
    ) {
        return switch (outcome) {
            case QUESTION_ID_INVALID ->
                    error(request, HttpStatus.BAD_REQUEST, "error", "question_id 参数错误");
            case BANK_ID_INVALID ->
                    error(request, HttpStatus.FORBIDDEN, "error", "bank_id 参数错误");
            case BANK_ACCESS_DENIED ->
                    error(request, HttpStatus.FORBIDDEN, "error", "无权访问该题库");
            case SUBJECT_INVALID ->
                    error(request, HttpStatus.FORBIDDEN, "error", "subject 参数错误");
            case SUBJECT_NOT_FOUND ->
                    error(request, HttpStatus.FORBIDDEN, "error", "subject 不存在");
            case QUESTION_OUT_OF_SCOPE ->
                    error(
                            request,
                            HttpStatus.BAD_REQUEST,
                            "error",
                            "题目不存在或不属于当前范围");
            case MUTATION_REJECTED ->
                    error(
                            request,
                            HttpStatus.INTERNAL_SERVER_ERROR,
                            "error",
                            "An unexpected server error occurred.");
            case IDEMPOTENCY_CONFLICT -> idempotencyConflict(request);
            case IDEMPOTENCY_IN_PROGRESS -> idempotencyInProgress(request);
            case SUCCESS -> throw new IllegalArgumentException("Success is not an error");
        };
    }

    private StudyScopeInput studyScope(JsonNode body) {
        String source = textOrDefault(field(body, "source"), "public");
        String subject = textOrNull(field(body, "subject"));
        Long bank = pythonInteger(field(body, "bank_id"));
        Integer bankId = bank != null
                        && bank >= Integer.MIN_VALUE
                        && bank <= Integer.MAX_VALUE
                ? bank.intValue()
                : null;
        return StudyScopeInput.legacy(source, subject, bankId);
    }

    private LearningWriteIdempotencyKey learningKey(String raw) {
        try {
            return LearningWriteIdempotencyKey.fromNullable(raw);
        } catch (IllegalArgumentException exception) {
            throw new InvalidIdempotencyKeyException();
        }
    }

    private QuestionEditIdempotencyKey questionKey(String raw) {
        try {
            return QuestionEditIdempotencyKey.fromNullable(raw);
        } catch (IllegalArgumentException exception) {
            throw new InvalidIdempotencyKeyException();
        }
    }

    private AuthenticatedLearningViewer viewer(Authentication authentication) {
        return new AuthenticatedLearningViewer(principal(authentication).identityId());
    }

    private static TargetAuthenticatedPrincipal principal(Authentication authentication) {
        if (authentication == null
                || !(authentication.getPrincipal()
                        instanceof TargetAuthenticatedPrincipal principal)) {
            throw new IllegalStateException("Target authentication is required");
        }
        return principal;
    }

    private static boolean hasRole(Authentication authentication, String role) {
        return authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(role::equals);
    }

    private Optional<String> optionalOptions(JsonNode body) {
        JsonNode value = field(body, "options");
        if (value == null || value.isNull()) {
            return Optional.empty();
        }
        return Optional.of(value.isTextual()
                ? value.asText()
                : objectMapper.writeValueAsString(value));
    }

    private static Optional<String> optionalText(JsonNode body, String name) {
        JsonNode value = field(body, name);
        return value == null || value.isNull()
                ? Optional.empty()
                : Optional.of(value.asText());
    }

    private ResponseEntity<ObjectNode> success(
            HttpServletRequest request,
            ObjectNode data
    ) {
        return ok(successBody(request, data));
    }

    private ObjectNode successBody(HttpServletRequest request, ObjectNode data) {
        ObjectNode body = objectMapper.createObjectNode()
                .put("status", "success");
        body.set("data", data);
        body.put("message", "")
                .put("request_id", RequestId.from(request));
        return body;
    }

    private ResponseEntity<ObjectNode> error(
            HttpServletRequest request,
            HttpStatus httpStatus,
            String legacyStatus,
            String message
    ) {
        return response(
                httpStatus,
                base(request, legacyStatus, message, httpStatus));
    }

    private ObjectNode base(
            HttpServletRequest request,
            String legacyStatus,
            String message,
            HttpStatus status
    ) {
        return objectMapper.createObjectNode()
                .put("status", legacyStatus)
                .put("message", message)
                .put("status_code", status.value())
                .put("request_id", RequestId.from(request));
    }

    private ResponseEntity<ObjectNode> idempotencyConflict(HttpServletRequest request) {
        return error(
                request,
                HttpStatus.CONFLICT,
                "error",
                "Idempotency-Key 与原请求不一致");
    }

    private ResponseEntity<ObjectNode> idempotencyInProgress(HttpServletRequest request) {
        return error(
                request,
                HttpStatus.CONFLICT,
                "error",
                "相同请求正在处理中");
    }

    private ResponseEntity<ObjectNode> ok(ObjectNode body) {
        return response(HttpStatus.OK, body);
    }

    private ResponseEntity<ObjectNode> response(HttpStatus status, ObjectNode body) {
        return ResponseEntity.status(status)
                .header(HttpHeaders.CONTENT_TYPE, CONTENT_TYPE)
                .body(body);
    }

    private static JsonNode field(JsonNode body, String name) {
        return body != null && body.isObject() ? body.get(name) : null;
    }

    private static Long pythonInteger(JsonNode value) {
        if (value == null || value.isNull()) {
            return null;
        }
        if (value.isBoolean()) {
            return value.asBoolean() ? 1L : 0L;
        }
        if (value.isIntegralNumber()) {
            try {
                return value.bigIntegerValue().longValueExact();
            } catch (ArithmeticException exception) {
                return null;
            }
        }
        if (value.isFloatingPointNumber()) {
            try {
                return value.decimalValue().toBigInteger().longValueExact();
            } catch (ArithmeticException exception) {
                return null;
            }
        }
        return value.isTextual() ? pythonIntegerText(value.asText()) : null;
    }

    private static Long pythonIntegerText(String value) {
        try {
            return new BigInteger(value.strip()).longValueExact();
        } catch (ArithmeticException | NumberFormatException exception) {
            return null;
        }
    }

    private static boolean pythonBoolean(JsonNode value) {
        if (value == null || value.isNull()) {
            return false;
        }
        if (value.isBoolean()) {
            return value.asBoolean();
        }
        if (value.isNumber()) {
            return value.decimalValue().compareTo(BigDecimal.ZERO) != 0;
        }
        if (value.isTextual() || value.isArray() || value.isObject()) {
            return value.size() > 0;
        }
        return true;
    }

    private static boolean isPythonFalse(JsonNode value) {
        return !pythonBoolean(value);
    }

    private static boolean parseLegacyBoolean(JsonNode value, boolean fallback) {
        if (value == null || value.isNull()) {
            return fallback;
        }
        if (value.isTextual()) {
            return switch (value.asText().strip().toLowerCase(Locale.ROOT)) {
                case "0", "false", "no", "off" -> false;
                case "1", "true", "yes", "on" -> true;
                default -> fallback;
            };
        }
        return pythonBoolean(value);
    }

    private static String textOrDefault(JsonNode value, String fallback) {
        if (value == null || value.isNull() || isPythonFalse(value)) {
            return fallback;
        }
        return value.isTextual() ? value.asText() : value.toString();
    }

    private static String textOrNull(JsonNode value) {
        return value == null || value.isNull()
                ? null
                : value.isTextual() ? value.asText() : value.toString();
    }

    private static String textOrEmpty(JsonNode value) {
        return textOrNull(value) == null ? "" : textOrNull(value);
    }

    private static String legacyDateTime(LocalDateTime value) {
        return LEGACY_DATE_TIME.format(value);
    }

    private static final class InvalidIdempotencyKeyException
            extends RuntimeException {

        private InvalidIdempotencyKeyException() {
            super("Invalid Idempotency-Key");
        }
    }
}
