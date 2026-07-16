package io.saksk.ti.identity.infrastructure.security;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Minimal JSON reader for signed legacy authentication payloads.
 *
 * <p>The compatibility formats only need a flat object of scalar values. Keeping that grammar
 * explicit rejects duplicate keys, tagged/nested objects, arrays and ambiguous numeric forms
 * before any legacy value reaches an authentication boundary.</p>
 */
final class StrictLegacyJson {
    private StrictLegacyJson() {
    }

    static Map<String, Object> parseFlatObject(
            byte[] utf8, int maximumBytes, int maximumMembers, int maximumStringCharacters) {
        if (utf8 == null || utf8.length == 0 || utf8.length > maximumBytes) {
            throw invalid();
        }

        String source;
        try {
            source = StandardCharsets.UTF_8
                    .newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(utf8))
                    .toString();
        } catch (CharacterCodingException exception) {
            throw invalid();
        }

        Parser parser = new Parser(source, maximumMembers, maximumStringCharacters);
        return parser.parse();
    }

    private static IllegalArgumentException invalid() {
        return new IllegalArgumentException("invalid legacy JSON");
    }

    private static final class Parser {
        private final String source;
        private final int maximumMembers;
        private final int maximumStringCharacters;
        private int index;

        private Parser(String source, int maximumMembers, int maximumStringCharacters) {
            this.source = source;
            this.maximumMembers = maximumMembers;
            this.maximumStringCharacters = maximumStringCharacters;
        }

        private Map<String, Object> parse() {
            skipWhitespace();
            expect('{');
            skipWhitespace();

            Map<String, Object> values = new LinkedHashMap<>();
            if (consume('}')) {
                requireEnd();
                return Collections.unmodifiableMap(values);
            }

            while (true) {
                if (values.size() >= maximumMembers) {
                    throw invalid();
                }

                String key = parseString();
                if (key.isEmpty() || key.length() > 64) {
                    throw invalid();
                }
                skipWhitespace();
                expect(':');
                skipWhitespace();
                Object value = parseScalar();
                if (values.containsKey(key)) {
                    throw invalid();
                }
                values.put(key, value);

                skipWhitespace();
                if (consume('}')) {
                    requireEnd();
                    return Collections.unmodifiableMap(values);
                }
                expect(',');
                skipWhitespace();
            }
        }

        private Object parseScalar() {
            if (atEnd()) {
                throw invalid();
            }
            return switch (source.charAt(index)) {
                case '"' -> parseString();
                case 't' -> parseLiteral("true", Boolean.TRUE);
                case 'f' -> parseLiteral("false", Boolean.FALSE);
                case 'n' -> parseLiteral("null", null);
                case '-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' -> parseInteger();
                default -> throw invalid();
            };
        }

        private Object parseLiteral(String literal, Object value) {
            if (!source.startsWith(literal, index)) {
                throw invalid();
            }
            index += literal.length();
            return value;
        }

        private Long parseInteger() {
            int start = index;
            if (consume('-') && atEnd()) {
                throw invalid();
            }
            if (consume('0')) {
                if (!atEnd() && Character.isDigit(source.charAt(index))) {
                    throw invalid();
                }
            } else {
                if (atEnd() || source.charAt(index) < '1' || source.charAt(index) > '9') {
                    throw invalid();
                }
                while (!atEnd() && source.charAt(index) >= '0' && source.charAt(index) <= '9') {
                    index++;
                }
            }

            if (!atEnd()) {
                char next = source.charAt(index);
                if (next == '.' || next == 'e' || next == 'E' || next == '+') {
                    throw invalid();
                }
            }
            try {
                String encoded = source.substring(start, index);
                if (encoded.equals("-0")) {
                    throw invalid();
                }
                return Long.parseLong(encoded);
            } catch (NumberFormatException exception) {
                throw invalid();
            }
        }

        private String parseString() {
            expect('"');
            StringBuilder value = new StringBuilder();
            while (!atEnd()) {
                char current = source.charAt(index++);
                if (current == '"') {
                    if (value.length() > maximumStringCharacters) {
                        throw invalid();
                    }
                    return value.toString();
                }
                if (current == '\\') {
                    appendEscape(value);
                } else {
                    appendRawCharacter(value, current);
                }
                if (value.length() > maximumStringCharacters) {
                    throw invalid();
                }
            }
            throw invalid();
        }

        private void appendEscape(StringBuilder value) {
            if (atEnd()) {
                throw invalid();
            }
            char escaped = source.charAt(index++);
            switch (escaped) {
                case '"', '\\', '/' -> value.append(escaped);
                case 'b' -> value.append('\b');
                case 'f' -> value.append('\f');
                case 'n' -> value.append('\n');
                case 'r' -> value.append('\r');
                case 't' -> value.append('\t');
                case 'u' -> appendUnicodeEscape(value);
                default -> throw invalid();
            }
        }

        private void appendUnicodeEscape(StringBuilder value) {
            char first = parseHexCodeUnit();
            if (Character.isHighSurrogate(first)) {
                if (index + 6 > source.length()
                        || source.charAt(index) != '\\'
                        || source.charAt(index + 1) != 'u') {
                    throw invalid();
                }
                index += 2;
                char second = parseHexCodeUnit();
                if (!Character.isLowSurrogate(second)) {
                    throw invalid();
                }
                value.append(first).append(second);
            } else if (Character.isLowSurrogate(first)) {
                throw invalid();
            } else {
                value.append(first);
            }
        }

        private char parseHexCodeUnit() {
            if (index + 4 > source.length()) {
                throw invalid();
            }
            int codeUnit = 0;
            for (int offset = 0; offset < 4; offset++) {
                int digit = asciiHexDigit(source.charAt(index++));
                if (digit < 0) {
                    throw invalid();
                }
                codeUnit = (codeUnit << 4) | digit;
            }
            return (char) codeUnit;
        }

        private static int asciiHexDigit(char value) {
            if (value >= '0' && value <= '9') {
                return value - '0';
            }
            if (value >= 'a' && value <= 'f') {
                return value - 'a' + 10;
            }
            if (value >= 'A' && value <= 'F') {
                return value - 'A' + 10;
            }
            return -1;
        }

        private void appendRawCharacter(StringBuilder value, char current) {
            if (current < 0x20) {
                throw invalid();
            }
            if (Character.isHighSurrogate(current)) {
                if (atEnd() || !Character.isLowSurrogate(source.charAt(index))) {
                    throw invalid();
                }
                value.append(current).append(source.charAt(index++));
            } else if (Character.isLowSurrogate(current)) {
                throw invalid();
            } else {
                value.append(current);
            }
        }

        private void requireEnd() {
            skipWhitespace();
            if (!atEnd()) {
                throw invalid();
            }
        }

        private void skipWhitespace() {
            while (!atEnd()) {
                char value = source.charAt(index);
                if (value != ' ' && value != '\t' && value != '\n' && value != '\r') {
                    return;
                }
                index++;
            }
        }

        private void expect(char expected) {
            if (!consume(expected)) {
                throw invalid();
            }
        }

        private boolean consume(char expected) {
            if (!atEnd() && source.charAt(index) == expected) {
                index++;
                return true;
            }
            return false;
        }

        private boolean atEnd() {
            return index >= source.length();
        }
    }
}
