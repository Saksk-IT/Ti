package io.saksk.ti.learning.api;

import java.util.Locale;
import java.util.Objects;
import java.util.Optional;

/**
 * Normalized legacy study scope input.
 *
 * <p>Only the exact {@code user_bank} value selects personal-bank resolution. Every other
 * normalized source keeps its legacy stored value while using the public subject scope.
 */
public record StudyScopeInput(
        String source,
        Optional<String> subject,
        Optional<Integer> bankId
) {

    public static final String PUBLIC_SOURCE = "public";
    public static final String USER_BANK_SOURCE = "user_bank";

    public StudyScopeInput {
        source = normalizeSource(source);
        subject = Objects.requireNonNull(subject, "subject")
                .map(String::strip);
        bankId = Objects.requireNonNull(bankId, "bankId");
    }

    public static StudyScopeInput legacy(
            String source,
            String subject,
            Integer bankId
    ) {
        return new StudyScopeInput(
                source,
                Optional.ofNullable(subject),
                Optional.ofNullable(bankId));
    }

    public boolean personalBank() {
        return USER_BANK_SOURCE.equals(source);
    }

    private static String normalizeSource(String source) {
        if (source == null || source.isBlank()) {
            return PUBLIC_SOURCE;
        }
        return source.strip().toLowerCase(Locale.ROOT);
    }
}
