package io.saksk.ti.web;

import java.util.Optional;

/** Normalizes the Unicode decimal-digit semantics used by Werkzeug's int converter. */
public final class LegacyDecimalPathInteger {

    private LegacyDecimalPathInteger() {}

    /**
     * Returns an ASCII representation when every code point is a Unicode decimal digit.
     * Numeric characters outside the Unicode Nd category are intentionally rejected.
     */
    public static Optional<String> normalize(String value) {
        if (value == null || value.isEmpty()) {
            return Optional.empty();
        }
        StringBuilder normalized = new StringBuilder(value.length());
        for (int offset = 0; offset < value.length(); ) {
            int codePoint = value.codePointAt(offset);
            if (Character.getType(codePoint) != Character.DECIMAL_DIGIT_NUMBER) {
                return Optional.empty();
            }
            int digit = Character.digit(codePoint, 10);
            if (digit < 0) {
                return Optional.empty();
            }
            normalized.append((char) ('0' + digit));
            offset += Character.charCount(codePoint);
        }
        return Optional.of(normalized.toString());
    }
}
