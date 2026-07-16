package io.saksk.ti.web.security;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Optional;
import org.springframework.http.HttpMethod;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.stereotype.Component;

/**
 * Resolves the two exact subject-directory reads from the raw Servlet request URI.
 *
 * <p>Servlet containers and Spring MVC can decode unreserved percent-encoded characters before
 * controller mapping. Security and rate-limit decisions therefore use this single resolver and
 * decode only RFC 3986 unreserved ASCII bytes. Encoded reserved/non-ASCII bytes and malformed
 * escapes remain non-matches, so ambiguous paths are denied by the security chain.
 */
@Component
public final class SubjectReadRequestResolver implements RequestMatcher {

    private static final String SUBJECTS_PATH = "/api/quiz/subjects";
    private static final String SUBJECTS_META_PATH = "/api/quiz/subjects/meta";

    @Override
    public boolean matches(HttpServletRequest request) {
        return resolve(request).isPresent();
    }

    public Optional<SubjectReadRateLimiter.Route> resolve(HttpServletRequest request) {
        if (!HttpMethod.GET.matches(request.getMethod())) {
            return Optional.empty();
        }
        String path = applicationPath(request);
        if (path == null) {
            return Optional.empty();
        }
        return switch (path) {
            case SUBJECTS_PATH -> Optional.of(SubjectReadRateLimiter.Route.SUBJECTS);
            case SUBJECTS_META_PATH -> Optional.of(SubjectReadRateLimiter.Route.SUBJECTS_META);
            default -> Optional.empty();
        };
    }

    private static String applicationPath(HttpServletRequest request) {
        String rawPath = request.getRequestURI();
        if (rawPath == null) {
            return null;
        }
        String contextPath = request.getContextPath();
        if (contextPath != null && !contextPath.isEmpty()) {
            if (!rawPath.startsWith(contextPath)) {
                return null;
            }
            rawPath = rawPath.substring(contextPath.length());
        }
        return decodeUnreserved(rawPath);
    }

    private static String decodeUnreserved(String rawPath) {
        StringBuilder canonical = new StringBuilder(rawPath.length());
        for (int index = 0; index < rawPath.length(); index++) {
            char current = rawPath.charAt(index);
            if (current != '%') {
                canonical.append(current);
                continue;
            }
            if (index + 2 >= rawPath.length()) {
                return null;
            }
            int high = Character.digit(rawPath.charAt(index + 1), 16);
            int low = Character.digit(rawPath.charAt(index + 2), 16);
            if (high < 0 || low < 0) {
                return null;
            }
            char decoded = (char) ((high << 4) | low);
            if (!isUnreservedAscii(decoded)) {
                return null;
            }
            canonical.append(decoded);
            index += 2;
        }
        return canonical.toString();
    }

    private static boolean isUnreservedAscii(char value) {
        return value >= 'a' && value <= 'z'
                || value >= 'A' && value <= 'Z'
                || value >= '0' && value <= '9'
                || value == '-'
                || value == '.'
                || value == '_'
                || value == '~';
    }
}
