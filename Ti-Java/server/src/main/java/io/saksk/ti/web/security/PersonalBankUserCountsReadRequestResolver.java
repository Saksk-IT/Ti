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

/**
 * Resolves the two Phase 4C personal-bank user-count compatibility aliases from the raw request
 * URI. Reserved percent escapes deliberately remain non-matches so {@code StrictHttpFirewall}
 * stays authoritative for ambiguous paths.
 */
@Component
public final class PersonalBankUserCountsReadRequestResolver implements RequestMatcher {

    private static final String API_ROOT = "/api/user/banks/api";
    private static final String WEB_ROOT = "/user/banks/api";
    private static final String USER_COUNTS_SEGMENT = "user-counts";
    private static final String INTEGER_MAX = Integer.toString(Integer.MAX_VALUE);

    public enum Alias {
        API,
        WEB
    }

    public enum BankIdKind {
        CONVERTER_MISS,
        ZERO,
        POSITIVE_INT,
        OVERFLOW
    }

    public enum CandidateKind {
        EXACT,
        NEAR_MISS
    }

    /**
     * A normalized exact-alias resolution. Converter misses use an empty normalized value and a
     * zero integer sentinel; zero and overflow resolutions likewise never expose a positive id.
     */
    public record Resolution(
            Alias alias,
            BankIdKind bankIdKind,
            String normalizedDigits,
            int bankId
    ) {
        public Resolution {
            if (alias == null || bankIdKind == null || normalizedDigits == null) {
                throw new IllegalArgumentException("User-count resolution fields are required");
            }
            switch (bankIdKind) {
                case CONVERTER_MISS -> {
                    if (!normalizedDigits.isEmpty() || bankId != 0) {
                        throw new IllegalArgumentException(
                                "Converter misses cannot expose normalized bank ids");
                    }
                }
                case ZERO -> {
                    if (!normalizedDigits.equals("0") || bankId != 0) {
                        throw new IllegalArgumentException("Zero bank ids must normalize to zero");
                    }
                }
                case POSITIVE_INT -> {
                    if (bankId <= 0 || !normalizedDigits.equals(Integer.toString(bankId))) {
                        throw new IllegalArgumentException(
                                "Positive bank ids must use their canonical decimal value");
                    }
                }
                case OVERFLOW -> {
                    if (bankId != 0 || !isAboveIntegerMaximum(normalizedDigits)) {
                        throw new IllegalArgumentException(
                                "Overflow bank ids must exceed the Java integer boundary");
                    }
                }
            }
        }
    }

    /** A path-family classification used by route-scoped boundary filters. */
    public record RouteCandidate(Alias alias, CandidateKind kind) {
        public RouteCandidate {
            if (alias == null || kind == null) {
                throw new IllegalArgumentException("Route candidate fields are required");
            }
        }
    }

    @Override
    public boolean matches(HttpServletRequest request) {
        return resolveRead(request).isPresent();
    }

    /**
     * Resolves structurally exact GET and HEAD aliases. A non-{@code Nd} bank-id segment is still
     * returned as {@link BankIdKind#CONVERTER_MISS} so the compatibility adapter can produce the
     * frozen 404 without consuming a route budget.
     */
    public Optional<Resolution> resolveRead(HttpServletRequest request) {
        if (!isReadMethod(request)) {
            return Optional.empty();
        }
        return resolveExact(request);
    }

    /** Resolves only GET and HEAD requests that consume one of the two independent route budgets. */
    public Optional<Resolution> resolveRateLimitedRoute(HttpServletRequest request) {
        return resolveRead(request)
                .filter(resolution -> resolution.bankIdKind() != BankIdKind.CONVERTER_MISS);
    }

    /** Resolves exact OPTIONS aliases, including converter misses, before authentication. */
    public Optional<Resolution> resolveOptions(HttpServletRequest request) {
        if (!HttpMethod.OPTIONS.matches(request.getMethod())) {
            return Optional.empty();
        }
        return resolveExact(request);
    }

    /** Resolves only converter-valid exact OPTIONS aliases before authentication or Session use. */
    public Optional<Resolution> resolveBareOptions(HttpServletRequest request) {
        return resolveOptions(request)
                .filter(resolution -> resolution.bankIdKind() != BankIdKind.CONVERTER_MISS);
    }

    /**
     * Classifies exact and narrowly related route candidates for HEAD suppression, Vary headers,
     * and converter near-miss handling. Unrelated descendants of the bank API are not candidates.
     */
    public Optional<RouteCandidate> resolveCandidate(HttpServletRequest request) {
        if (!isBoundaryMethod(request)) {
            return Optional.empty();
        }
        String path = applicationPath(request);
        if (path == null) {
            return Optional.empty();
        }
        Optional<AliasPath> aliasPath = aliasPath(path);
        if (aliasPath.isEmpty()) {
            return Optional.empty();
        }
        AliasPath candidate = aliasPath.orElseThrow();
        return exactBankSegment(candidate.remainder()).isPresent()
                ? Optional.of(new RouteCandidate(candidate.alias(), CandidateKind.EXACT))
                : isNearMissRemainder(candidate.remainder())
                        ? Optional.of(new RouteCandidate(
                                candidate.alias(), CandidateKind.NEAR_MISS))
                        : Optional.empty();
    }

    public boolean isNearMiss(HttpServletRequest request) {
        return resolveCandidate(request)
                .filter(candidate -> candidate.kind() == CandidateKind.NEAR_MISS)
                .isPresent();
    }

    private Optional<Resolution> resolveExact(HttpServletRequest request) {
        String path = applicationPath(request);
        if (path == null) {
            return Optional.empty();
        }
        return aliasPath(path).flatMap(aliasPath -> exactBankSegment(aliasPath.remainder())
                .map(bankSegment -> resolveBankId(aliasPath.alias(), bankSegment)));
    }

    private static Resolution resolveBankId(Alias alias, String bankSegment) {
        Optional<String> normalized = LegacyDecimalPathInteger.normalize(bankSegment);
        if (normalized.isEmpty()) {
            return new Resolution(alias, BankIdKind.CONVERTER_MISS, "", 0);
        }
        String canonical = stripLeadingZeros(normalized.orElseThrow());
        if (canonical.equals("0")) {
            return new Resolution(alias, BankIdKind.ZERO, canonical, 0);
        }
        if (isAboveIntegerMaximum(canonical)) {
            return new Resolution(alias, BankIdKind.OVERFLOW, canonical, 0);
        }
        return new Resolution(
                alias,
                BankIdKind.POSITIVE_INT,
                canonical,
                Integer.parseInt(canonical));
    }

    private static Optional<AliasPath> aliasPath(String path) {
        Optional<String> api = remainder(path, API_ROOT);
        if (api.isPresent()) {
            return Optional.of(new AliasPath(Alias.API, api.orElseThrow()));
        }
        return remainder(path, WEB_ROOT)
                .map(remainder -> new AliasPath(Alias.WEB, remainder));
    }

    private static Optional<String> remainder(String path, String root) {
        if (!path.startsWith(root)) {
            return Optional.empty();
        }
        if (path.length() == root.length()) {
            return Optional.of("");
        }
        if (path.charAt(root.length()) != '/') {
            return Optional.empty();
        }
        return Optional.of(path.substring(root.length() + 1));
    }

    private static Optional<String> exactBankSegment(String remainder) {
        String suffix = "/" + USER_COUNTS_SEGMENT;
        if (!remainder.endsWith(suffix)) {
            return Optional.empty();
        }
        String bankSegment = remainder.substring(0, remainder.length() - suffix.length());
        if (bankSegment.isEmpty() || bankSegment.indexOf('/') >= 0) {
            return Optional.empty();
        }
        return Optional.of(bankSegment);
    }

    private static boolean isNearMissRemainder(String remainder) {
        if (remainder.isEmpty()) {
            return false;
        }
        int start = 0;
        while (start <= remainder.length()) {
            int separator = remainder.indexOf('/', start);
            int end = separator < 0 ? remainder.length() : separator;
            if (remainder.substring(start, end).equals(USER_COUNTS_SEGMENT)) {
                return true;
            }
            if (separator < 0) {
                return false;
            }
            start = separator + 1;
        }
        return false;
    }

    private static boolean isReadMethod(HttpServletRequest request) {
        return HttpMethod.GET.matches(request.getMethod())
                || HttpMethod.HEAD.matches(request.getMethod());
    }

    private static boolean isBoundaryMethod(HttpServletRequest request) {
        return isReadMethod(request) || HttpMethod.OPTIONS.matches(request.getMethod());
    }

    private static String stripLeadingZeros(String normalized) {
        int firstNonZero = 0;
        while (firstNonZero < normalized.length() && normalized.charAt(firstNonZero) == '0') {
            firstNonZero++;
        }
        return firstNonZero == normalized.length() ? "0" : normalized.substring(firstNonZero);
    }

    private static boolean isAboveIntegerMaximum(String normalized) {
        return normalized.length() > INTEGER_MAX.length()
                || normalized.length() == INTEGER_MAX.length()
                        && normalized.compareTo(INTEGER_MAX) > 0;
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

    private record AliasPath(Alias alias, String remainder) {}
}
