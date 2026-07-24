package io.saksk.ti.web.security;

import io.saksk.ti.web.LegacyDecimalPathInteger;
import jakarta.servlet.http.HttpServletRequest;
import java.util.Optional;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriUtils;

/** Single route authority for the nine Phase 4C transaction-write endpoints. */
@Component
public final class TransactionWriteRequestResolver {

    public enum Route {
        FAVORITE_WEB("favorite-web-alias", "POST", "/api/favorite", 30, "请先登录后使用此功能"),
        FAVORITE_API("favorite-quiz-api", "POST", "/api/quiz/favorite", 30, "请先登录"),
        RECORD_RESULT_WEB(
                "record-result-web-alias",
                "POST",
                "/api/record_result",
                60,
                "请先登录后使用此功能"),
        RECORD_RESULT_API(
                "record-result-quiz-api",
                "POST",
                "/api/quiz/record_result",
                60,
                "请先登录"),
        STUDY_LEARN(
                "study-learn-record",
                "POST",
                "/api/quiz/study/learn/record",
                60,
                "请先登录"),
        STUDY_REVIEW(
                "study-review-record",
                "POST",
                "/api/quiz/study/review/record",
                60,
                "请先登录"),
        STUDY_MASTER(
                "study-review-master",
                "POST",
                "/api/quiz/study/review/master",
                30,
                "请先登录"),
        CHECKIN("user-checkin", "POST", "/api/user/checkin", 10, "请先登录"),
        QUESTION_EDIT(
                "question-edit",
                "PUT",
                "/api/quiz/questions/{questionId}",
                10,
                "请先登录");

        private final String operationId;
        private final String method;
        private final String path;
        private final int requestsPerMinute;
        private final String authenticationMessage;

        Route(
                String operationId,
                String method,
                String path,
                int requestsPerMinute,
                String authenticationMessage
        ) {
            this.operationId = operationId;
            this.method = method;
            this.path = path;
            this.requestsPerMinute = requestsPerMinute;
            this.authenticationMessage = authenticationMessage;
        }

        public String operationId() {
            return operationId;
        }

        public String method() {
            return method;
        }

        public String path() {
            return path;
        }

        public int requestsPerMinute() {
            return requestsPerMinute;
        }

        public String authenticationMessage() {
            return authenticationMessage;
        }
    }

    public record Resolution(Route route, Optional<String> normalizedQuestionId) {
        public Resolution {
            if (route == null || normalizedQuestionId == null) {
                throw new IllegalArgumentException("Transaction-write resolution is incomplete");
            }
            if ((route == Route.QUESTION_EDIT) != normalizedQuestionId.isPresent()) {
                throw new IllegalArgumentException(
                        "Only question-edit may expose a path question id");
            }
        }
    }

    public Optional<Resolution> resolve(HttpServletRequest request) {
        return resolvePath(request)
                .filter(resolution -> resolution.route().method().equals(request.getMethod()));
    }

    /** Resolves an exact path independently of method for CORS and security boundaries. */
    public Optional<Resolution> resolvePath(HttpServletRequest request) {
        String path = applicationPath(request);
        if (path == null) {
            return Optional.empty();
        }
        for (Route route : Route.values()) {
            if (route != Route.QUESTION_EDIT && route.path().equals(path)) {
                return Optional.of(new Resolution(route, Optional.empty()));
            }
        }
        String prefix = "/api/quiz/questions/";
        if (!path.startsWith(prefix) || path.length() == prefix.length()) {
            return Optional.empty();
        }
        String segment = path.substring(prefix.length());
        if (segment.indexOf('/') >= 0) {
            return Optional.empty();
        }
        try {
            String decoded = UriUtils.decode(segment, java.nio.charset.StandardCharsets.UTF_8);
            return LegacyDecimalPathInteger.normalize(decoded)
                    .map(normalized -> new Resolution(
                            Route.QUESTION_EDIT,
                            Optional.of(stripLeadingZeros(normalized))));
        } catch (IllegalArgumentException exception) {
            return Optional.empty();
        }
    }

    public boolean matches(HttpServletRequest request) {
        return resolve(request).isPresent();
    }

    private static String stripLeadingZeros(String value) {
        int index = 0;
        while (index < value.length() && value.charAt(index) == '0') {
            index++;
        }
        return index == value.length() ? "0" : value.substring(index);
    }

    private static String applicationPath(HttpServletRequest request) {
        String path = request.getRequestURI();
        if (path == null || path.indexOf(';') >= 0) {
            return null;
        }
        String contextPath = request.getContextPath();
        if (contextPath != null && !contextPath.isEmpty()) {
            if (!path.startsWith(contextPath)) {
                return null;
            }
            path = path.substring(contextPath.length());
        }
        return path;
    }
}
