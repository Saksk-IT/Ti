package io.saksk.ti.identity.domain;

import java.util.Optional;
import java.util.regex.Pattern;

public record LoginIdentifier(Kind kind, String value) {

    private static final Pattern PHONE = Pattern.compile("1[3-9]\\d{9}");

    public static Optional<LoginIdentifier> parse(String raw) {
        if (raw == null) {
            return Optional.empty();
        }
        String value = raw.strip();
        if (value.isEmpty()) {
            return Optional.empty();
        }
        if (value.indexOf('@') >= 0) {
            return Optional.of(new LoginIdentifier(Kind.EMAIL, value));
        }
        return PHONE.matcher(value).matches()
                ? Optional.of(new LoginIdentifier(Kind.PHONE, value))
                : Optional.empty();
    }

    public enum Kind {
        EMAIL,
        PHONE
    }
}
