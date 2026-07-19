package io.saksk.ti.learning.infrastructure.migration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.KeyFailure;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.KeyKind;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseFailure;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.ParseFailureCode;
import io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagPreflightParser.TagRow;
import java.util.List;
import org.junit.jupiter.api.Test;

class LegacyPersonalBankTagPreflightParserTest {

    @Test
    void distinguishesCanonicalKeysWhileReproducingLegacySplitIndexNormalization() {
        var canonical = LegacyPersonalBankTagPreflightParser.analyzeReservedKey(
                "bank_9411_tags");
        assertThat(canonical.kind()).isEqualTo(KeyKind.CANONICAL);
        assertThat(canonical.normalizedBankId()).hasValue(9_411);
        assertThat(canonical.failure()).isEqualTo(KeyFailure.NONE);

        for (String nearMiss : List.of(
                "bank_09411_tags",
                "bank_9411_extra_tags",
                "bank_٩٤١١_tags",
                "bank_+9411_tags")) {
            var analysis = LegacyPersonalBankTagPreflightParser.analyzeReservedKey(nearMiss);
            assertThat(analysis.kind()).as(nearMiss).isEqualTo(KeyKind.NEAR_MISS);
            assertThat(analysis.normalizedBankId()).as(nearMiss).hasValue(9_411);
            assertThat(analysis.failure()).as(nearMiss)
                    .isEqualTo(KeyFailure.NON_CANONICAL_RESERVED_KEY);
        }

        var overflow = LegacyPersonalBankTagPreflightParser.analyzeReservedKey(
                "bank_2147483648_tags");
        assertThat(overflow.kind()).isEqualTo(KeyKind.CANONICAL_INVALID);
        assertThat(overflow.normalizedBankId()).isEmpty();
        assertThat(overflow.failure()).isEqualTo(KeyFailure.BANK_ID_OUT_OF_RANGE);

        var unparseable = LegacyPersonalBankTagPreflightParser.analyzeReservedKey(
                "bank_not-a-number_tags");
        assertThat(unparseable.kind()).isEqualTo(KeyKind.NEAR_MISS);
        assertThat(unparseable.normalizedBankId()).isEmpty();
        assertThat(unparseable.failure()).isEqualTo(KeyFailure.UNPARSEABLE_RESERVED_KEY);
    }

    @Test
    void producesCanonicalRowsFromAllApprovedLegacyValueShapes() throws Exception {
        String pythonWhitespace = "\u00a0\u0085\u2007\u202f\u3000";
        String oversizedEmoji = "😀".repeat(21);
        var result = LegacyPersonalBankTagPreflightParser.parse("""
                {
                  "tags": ["%1$salpha%1$s", "ALL", "%2$s"],
                  "question_tags": {
                    "%1$s+１２%1$s": ["alpha", "beta"],
                    "13": "[\\\"gamma\\\", \\\"beta\\\"]",
                    "14": "delta,epsilon，zeta"
                  }
                }
                """.formatted(pythonWhitespace, oversizedEmoji));

        assertThat(result.definitionCount()).isEqualTo(7);
        assertThat(result.questionBindingCount()).isEqualTo(7);
        assertThat(result.distinctTagCount()).isEqualTo(7);
        assertThat(result.rows()).contains(
                new TagRow(0, "alpha"),
                new TagRow(0, "😀".repeat(20)),
                new TagRow(12, "alpha"),
                new TagRow(12, "beta"),
                new TagRow(13, "gamma"),
                new TagRow(14, "zeta"));
        assertThat(result.rows()).isSortedAccordingTo(
                java.util.Comparator.comparingInt(TagRow::questionId)
                        .thenComparing(TagRow::tag));
        assertThat(result.planDigest())
                .matches("[0-9a-f]{64}")
                .isEqualTo(LegacyPersonalBankTagPreflightParser.digestRows(result.rows()));
    }

    @Test
    void rejectsAmbiguousNormalizationWithStableRedactedFailureCodes() {
        assertFailure(
                "{\"tags\":[\"alpha\"],\"tags\":[\"secret-value\"]}",
                ParseFailureCode.INVALID_JSON,
                "secret-value");
        assertFailure("""
                {"tags":[],"question_tags":{"11":["alpha"],"０１１":["beta"]}}
                """, ParseFailureCode.QUESTION_ID_COLLISION, "alpha");
        assertFailure("""
                {
                  "tags": ["12345678901234567890-one"],
                  "question_tags": {"11": ["12345678901234567890-two"]}
                }
                """, ParseFailureCode.TAG_NORMALIZATION_COLLISION, "-two");
    }

    @Test
    void rejectsTrailingTokensAndEveryMalformedLegacyContainerShape() {
        assertFailure("{} {\"trailing\":true}", ParseFailureCode.INVALID_JSON, "trailing");

        MapCase[] malformed = {
                new MapCase("{\"tags\":\"alpha\"}", ParseFailureCode.TAGS_NOT_ARRAY),
                new MapCase("{\"tags\":null}", ParseFailureCode.TAGS_NOT_ARRAY),
                new MapCase("{\"tags\":[7]}", ParseFailureCode.TAG_ITEM_NOT_STRING),
                new MapCase("{\"question_tags\":[]}",
                        ParseFailureCode.QUESTION_TAGS_NOT_OBJECT),
                new MapCase("{\"question_tags\":null}",
                        ParseFailureCode.QUESTION_TAGS_NOT_OBJECT),
                new MapCase("{\"question_tags\":{\"11\":7}}",
                        ParseFailureCode.QUESTION_VALUE_INVALID),
                new MapCase("{\"question_tags\":{\"11\":true}}",
                        ParseFailureCode.QUESTION_VALUE_INVALID),
                new MapCase("{\"question_tags\":{\"11\":null}}",
                        ParseFailureCode.QUESTION_VALUE_INVALID),
                new MapCase("{\"question_tags\":{\"11\":{}}}",
                        ParseFailureCode.QUESTION_VALUE_INVALID),
                new MapCase("{\"question_tags\":{\"11\":[\"alpha\",7]}}",
                        ParseFailureCode.TAG_ITEM_NOT_STRING),
                new MapCase("{\"question_tags\":{\"11\":\"['alpha']\"}}",
                        ParseFailureCode.ENCODED_TAG_ARRAY_INVALID)
        };
        for (MapCase invalid : malformed) {
            assertFailure(invalid.payload(), invalid.code(), "must-not-appear");
        }
    }

    @Test
    void rejectsQuestionIdsOutsideTheExactPythonIntegerCompatibilitySubset() {
        for (String invalidQuestionId : List.of(
                "0",
                "-1",
                "1__0",
                "1.0",
                "\u200b11\u200b",
                "2147483648")) {
            String payload = "{\"question_tags\":{\""
                    + invalidQuestionId
                    + "\":[\"alpha\"]}}";
            assertFailure(payload, ParseFailureCode.QUESTION_ID_INVALID, "alpha");
        }
    }

    @Test
    void preservesCaseAndUnicodeNormalizationFormsAsDistinctLegacyTags()
            throws Exception {
        var result = LegacyPersonalBankTagPreflightParser.parse("""
                {"tags":["é","é","A","a"],"question_tags":{}}
                """);

        assertThat(result.rows()).containsExactly(
                new TagRow(0, "A"),
                new TagRow(0, "a"),
                new TagRow(0, "é"),
                new TagRow(0, "é"));
        assertThat(result.distinctTagCount()).isEqualTo(4);
    }

    @Test
    void rejectsTextPostgresCannotRepresentWithoutUtf8Replacement() throws Exception {
        String escapedHighSurrogate = "{\"tags\":[\"\\u" + "d800\"]}";
        String escapedLowSurrogate = "{\"tags\":[\"\\u" + "dc00\"]}";
        String escapedNull = "{\"tags\":[\"\\u" + "0000\"]}";
        for (String payload : List.of(
                escapedHighSurrogate, escapedLowSurrogate, escapedNull)) {
            assertFailure(payload, ParseFailureCode.TAG_NOT_LOSSLESS, "must-not-leak");
        }

        String escapedEmojiPair = "{\"tags\":[\"\\u" + "d83d\\u" + "de00\"]}";
        var valid = LegacyPersonalBankTagPreflightParser.parse(escapedEmojiPair);
        assertThat(valid.rows()).containsExactly(new TagRow(0, "😀"));
    }

    @Test
    void rejectsPayloadsLargerThanOneMebibyteBeforeJsonParsing() {
        String oversized = "{\"tags\":[\""
                + "x".repeat(LegacyPersonalBankTagPreflightParser.MAX_PAYLOAD_UTF8_BYTES)
                + "\"]}";

        assertFailure(
                oversized,
                ParseFailureCode.PAYLOAD_LIMIT_EXCEEDED,
                "x".repeat(32));
    }

    @Test
    void acceptsOnlyAlreadyCanonicalTargetTags() {
        assertThat(LegacyPersonalBankTagPreflightParser.isCanonicalTargetTag("alpha"))
                .isTrue();
        assertThat(LegacyPersonalBankTagPreflightParser.isCanonicalTargetTag(
                "😀".repeat(20))).isTrue();
        String unpairedHighSurrogate = String.valueOf(
                Character.highSurrogate(0x1F600));
        String unpairedLowSurrogate = String.valueOf(
                Character.lowSurrogate(0x1F600));
        for (String invalid : List.of(
                "",
                "ALL",
                " padded ",
                "😀".repeat(21),
                "\u0000",
                unpairedHighSurrogate,
                unpairedLowSurrogate)) {
            assertThat(LegacyPersonalBankTagPreflightParser.isCanonicalTargetTag(invalid))
                    .as(invalid)
                    .isFalse();
        }
        assertThat(LegacyPersonalBankTagPreflightParser.isCanonicalTargetTag(null))
                .isFalse();
    }

    private static void assertFailure(
            String payload,
            ParseFailureCode expectedCode,
            String forbiddenRawValue
    ) {
        assertThatThrownBy(() -> LegacyPersonalBankTagPreflightParser.parse(payload))
                .isInstanceOfSatisfying(ParseFailure.class, failure -> {
                    assertThat(failure.code()).isEqualTo(expectedCode);
                    assertThat(failure.getMessage())
                            .contains(expectedCode.name())
                            .doesNotContain(forbiddenRawValue);
                });
    }

    private record MapCase(String payload, ParseFailureCode code) {
    }
}
