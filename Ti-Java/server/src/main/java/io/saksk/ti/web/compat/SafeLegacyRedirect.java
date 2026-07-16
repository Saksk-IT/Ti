package io.saksk.ti.web.compat;

import java.net.URI;
import java.util.Locale;

final class SafeLegacyRedirect {

    private static final int MAXIMUM_LENGTH = 2048;

    private SafeLegacyRedirect() {
    }

    static String sanitize(String candidate) {
        if (candidate == null || candidate.isEmpty()) {
            return "/";
        }
        if (candidate.length() > MAXIMUM_LENGTH
                || candidate.charAt(0) != '/'
                || candidate.startsWith("//")
                || candidate.indexOf('\\') >= 0
                || hasControlCharacter(candidate)) {
            return "/";
        }

        String lower = candidate.toLowerCase(Locale.ROOT);
        if (lower.contains("%5c")
                || lower.contains("%2f%2f")
                || lower.contains("%0d")
                || lower.contains("%0a")
                || lower.contains("%00")) {
            return "/";
        }

        try {
            URI parsed = URI.create(candidate);
            return parsed.isAbsolute() || parsed.getRawAuthority() != null ? "/" : candidate;
        } catch (IllegalArgumentException exception) {
            return "/";
        }
    }

    private static boolean hasControlCharacter(String value) {
        for (int index = 0; index < value.length(); index++) {
            if (Character.isISOControl(value.charAt(index))) {
                return true;
            }
        }
        return false;
    }
}
