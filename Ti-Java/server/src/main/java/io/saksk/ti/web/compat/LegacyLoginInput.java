package io.saksk.ti.web.compat;

import java.util.Arrays;

final class LegacyLoginInput implements AutoCloseable {

    private final String identifier;
    private final char[] password;
    private final boolean remember;
    private final String redirect;

    LegacyLoginInput(String identifier, char[] password, boolean remember, String redirect) {
        this.identifier = identifier;
        this.password = password;
        this.remember = remember;
        this.redirect = redirect;
    }

    String identifier() {
        return identifier;
    }

    char[] passwordCopy() {
        return Arrays.copyOf(password, password.length);
    }

    boolean remember() {
        return remember;
    }

    String redirect() {
        return redirect;
    }

    @Override
    public void close() {
        Arrays.fill(password, '\0');
    }

    @Override
    public String toString() {
        return "LegacyLoginInput[identifier=<redacted>, password=<redacted>]";
    }
}
