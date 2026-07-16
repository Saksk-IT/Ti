package io.saksk.ti.web.security;

import io.saksk.ti.web.LegacyDecimalPathInteger;
import jakarta.servlet.http.HttpServletRequest;
import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import org.springframework.http.HttpMethod;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.stereotype.Component;

/** Resolves only the seven Phase 4A public-bank GET compatibility operations. */
@Component
public final class PublicBankReadRequestResolver implements RequestMatcher {

    private static final String ROOT = "/api/public/banks";
    private static final String CARD_PREFIX = ROOT + "/card/";

    public enum Route {
        LEGACY_LIST,
        BOARDS,
        CARD_DETAIL,
        HOT,
        PLAZA_LIST,
        SUMMARY,
        DETAIL
    }

    @Override
    public boolean matches(HttpServletRequest request) {
        return resolve(request).isPresent();
    }

    public Optional<Route> resolve(HttpServletRequest request) {
        if (!HttpMethod.GET.matches(request.getMethod())) {
            return Optional.empty();
        }
        String path = applicationPath(request);
        if (path == null) {
            return Optional.empty();
        }
        Optional<Route> exact = switch (path) {
            case ROOT -> Optional.of(Route.LEGACY_LIST);
            case ROOT + "/boards" -> Optional.of(Route.BOARDS);
            case ROOT + "/hot" -> Optional.of(Route.HOT);
            case ROOT + "/list" -> Optional.of(Route.PLAZA_LIST);
            case ROOT + "/summary" -> Optional.of(Route.SUMMARY);
            default -> Optional.empty();
        };
        if (exact.isPresent()) {
            return exact;
        }
        if (path.startsWith(CARD_PREFIX)) {
            String remainder = path.substring(CARD_PREFIX.length());
            int separator = remainder.indexOf('/');
            if (separator > 0
                    && separator == remainder.lastIndexOf('/')
                    && separator < remainder.length() - 1) {
                return Optional.of(Route.CARD_DETAIL);
            }
            return Optional.empty();
        }
        String detailPrefix = ROOT + "/";
        if (!path.startsWith(detailPrefix)) {
            return Optional.empty();
        }
        String remainder = path.substring(detailPrefix.length());
        if (remainder.isEmpty() || remainder.indexOf('/') >= 0 || remainder.equals("joined")) {
            return Optional.empty();
        }
        return Optional.of(Route.DETAIL);
    }

    /**
     * Resolves reads that reached a legacy Flask handler and therefore consume its route budget.
     * Converter 404 paths stay publicly admitted by {@link #resolve(HttpServletRequest)} but do
     * not consume a budget.
     */
    public Optional<Route> resolveRateLimitedRoute(HttpServletRequest request) {
        Optional<Route> resolved = resolve(request);
        if (resolved.isEmpty()) {
            return resolved;
        }
        Route route = resolved.orElseThrow();
        if (route != Route.DETAIL && route != Route.CARD_DETAIL) {
            return resolved;
        }
        String path = applicationPath(request);
        if (path == null) {
            return Optional.empty();
        }
        String bankId = path.substring(path.lastIndexOf('/') + 1);
        return LegacyDecimalPathInteger.normalize(bankId).isPresent()
                ? resolved
                : Optional.empty();
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
        if (rawPath.indexOf(';') >= 0) {
            return null;
        }
        return decodeCanonicalPath(rawPath);
    }

    private static String decodeCanonicalPath(String rawPath) {
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
            int decoded = (high << 4) | low;
            if (decoded < 0x80) {
                if (!isUnreservedAscii((char) decoded)) {
                    return null;
                }
                canonical.append((char) decoded);
                index += 2;
                continue;
            }

            ByteArrayOutputStream encoded = new ByteArrayOutputStream(4);
            int cursor = index;
            while (cursor + 2 < rawPath.length() && rawPath.charAt(cursor) == '%') {
                int octetHigh = Character.digit(rawPath.charAt(cursor + 1), 16);
                int octetLow = Character.digit(rawPath.charAt(cursor + 2), 16);
                if (octetHigh < 0 || octetLow < 0) {
                    return null;
                }
                int octet = (octetHigh << 4) | octetLow;
                if (octet < 0x80) {
                    break;
                }
                encoded.write(octet);
                cursor += 3;
            }
            String unicode = decodeStrictUtf8(encoded.toByteArray());
            if (unicode == null) {
                return null;
            }
            canonical.append(unicode);
            index = cursor - 1;
        }
        return canonical.toString();
    }

    private static String decodeStrictUtf8(byte[] encoded) {
        try {
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(encoded))
                    .toString();
        } catch (CharacterCodingException exception) {
            return null;
        }
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
