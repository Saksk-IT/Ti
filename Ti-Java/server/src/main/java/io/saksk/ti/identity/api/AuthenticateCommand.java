package io.saksk.ti.identity.api;

import java.util.Arrays;
import java.util.Objects;

/** Password-bearing application command with defensive copies and a redacted string form. */
public final class AuthenticateCommand implements AutoCloseable {

    private final String identifier;
    private final char[] password;

    public AuthenticateCommand(String identifier, char[] password) {
        this.identifier = Objects.requireNonNull(identifier, "identifier");
        this.password = Arrays.copyOf(Objects.requireNonNull(password, "password"), password.length);
    }

    public String identifier() {
        return identifier;
    }

    public char[] passwordCopy() {
        return Arrays.copyOf(password, password.length);
    }

    @Override
    public void close() {
        Arrays.fill(password, '\0');
    }

    @Override
    public String toString() {
        return "AuthenticateCommand[identifier=<redacted>, password=<redacted>]";
    }
}
