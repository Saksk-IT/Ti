package io.saksk.ti.web.compat;

import java.util.Locale;
import tools.jackson.databind.JsonNode;

final class LegacyLoginRequestParser {

    private static final int MAXIMUM_IDENTIFIER_CHARACTERS = 1024;
    private static final int MAXIMUM_PASSWORD_CHARACTERS = 1024;

    LegacyLoginInput parse(JsonNode body) {
        if (body == null || !body.isObject()) {
            throw new InvalidLegacyLoginRequest();
        }

        JsonNode username = body.get("username");
        JsonNode password = body.get("password");
        if (username == null
                || !username.isString()
                || username.stringValue().length() > MAXIMUM_IDENTIFIER_CHARACTERS
                || password == null
                || !password.isString()
                || password.stringValue().isEmpty()
                || password.stringValue().length() > MAXIMUM_PASSWORD_CHARACTERS) {
            throw new InvalidLegacyLoginRequest();
        }

        boolean remember = parseRemember(body.get("remember"));
        JsonNode redirectNode = body.get("redirect");
        if (redirectNode != null && !redirectNode.isNull() && !redirectNode.isString()) {
            throw new InvalidLegacyLoginRequest();
        }
        String redirect = redirectNode == null || redirectNode.isNull()
                ? null
                : redirectNode.stringValue();

        return new LegacyLoginInput(
                username.stringValue().strip(),
                password.stringValue().toCharArray(),
                remember,
                SafeLegacyRedirect.sanitize(redirect));
    }

    private boolean parseRemember(JsonNode value) {
        if (value == null) {
            return false;
        }
        if (value.isBoolean()) {
            return value.booleanValue();
        }
        if (value.isIntegralNumber() && value.canConvertToLong()) {
            long number = value.longValue();
            if (number == 0 || number == 1) {
                return number == 1;
            }
            throw new InvalidLegacyLoginRequest();
        }
        if (value.isString()) {
            return switch (value.stringValue().strip().toLowerCase(Locale.ROOT)) {
                case "true", "1", "yes", "on", "y" -> true;
                case "false", "0", "no", "off", "n" -> false;
                default -> throw new InvalidLegacyLoginRequest();
            };
        }
        throw new InvalidLegacyLoginRequest();
    }

    static final class InvalidLegacyLoginRequest extends RuntimeException {
        private static final long serialVersionUID = 1L;
    }
}
