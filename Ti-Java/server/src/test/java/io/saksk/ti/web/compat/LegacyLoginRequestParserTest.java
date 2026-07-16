package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

class LegacyLoginRequestParserTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    private final LegacyLoginRequestParser parser = new LegacyLoginRequestParser();

    @ParameterizedTest
    @MethodSource("acceptedRememberValues")
    void acceptsOnlyTheLegacyBooleanCoercions(String rememberJson, boolean expected) throws Exception {
        JsonNode body = JSON.readTree("""
                {"username":"  user@example.com  ","password":" password ","remember":%s,
                 "redirect":"/practice?from=login","unknown":"ignored"}
                """.formatted(rememberJson));

        try (LegacyLoginInput parsed = parser.parse(body)) {
            assertThat(parsed.identifier()).isEqualTo("user@example.com");
            assertThat(parsed.passwordCopy()).containsExactly(" password ".toCharArray());
            assertThat(parsed.remember()).isEqualTo(expected);
            assertThat(parsed.redirect()).isEqualTo("/practice?from=login");
            assertThat(parsed.toString()).doesNotContain("user@example.com", " password ");
        }
    }

    @Test
    void omittedRememberAndRedirectUseLegacyDefaultsAndClosingErasesTheCredential() throws Exception {
        LegacyLoginInput parsed = parser.parse(JSON.readTree(
                "{\"username\":\"13800138000\",\"password\":\"secret\"}"));

        assertThat(parsed.remember()).isFalse();
        assertThat(parsed.redirect()).isEqualTo("/");
        parsed.close();

        assertThat(parsed.passwordCopy()).containsOnly('\0');
    }

    @ParameterizedTest
    @MethodSource("invalidBodies")
    void rejectsMalformedOrAmbiguousInput(String bodyJson) throws Exception {
        JsonNode body = bodyJson == null ? null : JSON.readTree(bodyJson);

        assertThatThrownBy(() -> parser.parse(body))
                .isInstanceOf(LegacyLoginRequestParser.InvalidLegacyLoginRequest.class);
    }

    @ParameterizedTest
    @MethodSource("redirectCandidates")
    void acceptsOnlySameOriginRelativeRedirects(String candidate, String expected) {
        assertThat(SafeLegacyRedirect.sanitize(candidate)).isEqualTo(expected);
    }

    private static Stream<Arguments> acceptedRememberValues() {
        return Stream.of(
                Arguments.of("true", true),
                Arguments.of("false", false),
                Arguments.of("1", true),
                Arguments.of("0", false),
                Arguments.of("\" true \"", true),
                Arguments.of("\"FALSE\"", false),
                Arguments.of("\"yes\"", true),
                Arguments.of("\"no\"", false),
                Arguments.of("\"on\"", true),
                Arguments.of("\"off\"", false),
                Arguments.of("\"y\"", true),
                Arguments.of("\"n\"", false));
    }

    private static Stream<String> invalidBodies() {
        String tooLongIdentifier = "x".repeat(1025);
        String tooLongPassword = "x".repeat(1025);
        return Stream.of(
                null,
                "null",
                "[]",
                "{}",
                "{\"username\":null,\"password\":\"x\"}",
                "{\"username\":1,\"password\":\"x\"}",
                "{\"username\":\"user@example.com\",\"password\":null}",
                "{\"username\":\"user@example.com\",\"password\":1}",
                "{\"username\":\"user@example.com\",\"password\":\"\"}",
                "{\"username\":\"user@example.com\",\"password\":\"x\",\"remember\":null}",
                "{\"username\":\"user@example.com\",\"password\":\"x\",\"remember\":2}",
                "{\"username\":\"user@example.com\",\"password\":\"x\",\"remember\":18446744073709551616}",
                "{\"username\":\"user@example.com\",\"password\":\"x\",\"remember\":\"maybe\"}",
                "{\"username\":\"user@example.com\",\"password\":\"x\",\"redirect\":1}",
                "{\"username\":\"" + tooLongIdentifier + "\",\"password\":\"x\"}",
                "{\"username\":\"user@example.com\",\"password\":\"" + tooLongPassword + "\"}");
    }

    private static Stream<Arguments> redirectCandidates() {
        return Stream.of(
                Arguments.of(null, "/"),
                Arguments.of("", "/"),
                Arguments.of("/", "/"),
                Arguments.of("/practice?next=%2Fanswer#question", "/practice?next=%2Fanswer#question"),
                Arguments.of("https://evil.example/", "/"),
                Arguments.of("//evil.example/path", "/"),
                Arguments.of("///evil.example/path", "/"),
                Arguments.of("/\\\\evil.example", "/"),
                Arguments.of("/%5cevil.example", "/"),
                Arguments.of("/%2f%2fevil.example", "/"),
                Arguments.of("/safe%0d%0aLocation:evil", "/"),
                Arguments.of("/safe\nunsafe", "/"),
                Arguments.of("/" + "x".repeat(2048), "/"));
    }
}
