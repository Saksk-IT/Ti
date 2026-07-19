package io.saksk.ti.learning.infrastructure.migration;

import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.OptionalInt;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import tools.jackson.core.StreamReadFeature;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.json.JsonMapper;

/**
 * Strict, side-effect-free parser for the legacy {@code bank_<bank_id>_tags}
 * compatibility payload. This type intentionally has no database or Spring
 * dependency so the production preflight can classify untrusted legacy data
 * before it asks any provider for membership facts.
 */
final class LegacyPersonalBankTagPreflightParser {

    static final int TAG_DEFINITION_QUESTION_ID = 0;
    static final int MAX_TAG_CODE_POINTS = 20;
    static final int MAX_PAYLOAD_UTF8_BYTES = 1_048_576;
    static final int MAX_QUESTION_BINDINGS = 100_000;
    static final int MAX_PLANNED_ROWS = 200_000;

    private static final Pattern CANONICAL_KEY =
            Pattern.compile("bank_([1-9][0-9]*)_tags");
    private static final Pattern INT_COMPATIBLE =
            Pattern.compile("\\+?\\p{Nd}(?:_?\\p{Nd})*");
    private static final BigInteger MAX_INTEGER = BigInteger.valueOf(Integer.MAX_VALUE);
    private static final Comparator<TagRow> CANONICAL_ROW_ORDER =
            Comparator.comparingInt(TagRow::questionId).thenComparing(TagRow::tag);
    private static final ObjectMapper JSON = JsonMapper.builder()
            .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
            .build();

    private LegacyPersonalBankTagPreflightParser() {
    }

    static KeyAnalysis analyzeReservedKey(String key) {
        Objects.requireNonNull(key, "key");
        Matcher canonical = CANONICAL_KEY.matcher(key);
        if (canonical.matches()) {
            try {
                int bankId = Integer.parseInt(canonical.group(1));
                return new KeyAnalysis(KeyKind.CANONICAL, OptionalInt.of(bankId),
                        KeyFailure.NONE);
            } catch (NumberFormatException ignored) {
                return new KeyAnalysis(KeyKind.CANONICAL_INVALID, OptionalInt.empty(),
                        KeyFailure.BANK_ID_OUT_OF_RANGE);
            }
        }

        OptionalInt normalized = normalizedNearMissBankId(key);
        return new KeyAnalysis(
                KeyKind.NEAR_MISS,
                normalized,
                normalized.isPresent()
                        ? KeyFailure.NON_CANONICAL_RESERVED_KEY
                        : KeyFailure.UNPARSEABLE_RESERVED_KEY);
    }

    static ParseResult parse(String rawData) throws ParseFailure {
        if (rawData == null) {
            throw failure(ParseFailureCode.NULL_PAYLOAD, "root");
        }
        int payloadBytes = rawData.getBytes(StandardCharsets.UTF_8).length;
        if (payloadBytes > MAX_PAYLOAD_UTF8_BYTES) {
            throw failure(ParseFailureCode.PAYLOAD_LIMIT_EXCEEDED, "root");
        }

        JsonNode root;
        try {
            root = JSON.readTree(rawData);
        } catch (Exception invalidJson) {
            throw new ParseFailure(ParseFailureCode.INVALID_JSON, "root", invalidJson);
        }
        if (root == null || !root.isObject()) {
            throw failure(ParseFailureCode.ROOT_NOT_OBJECT, "root");
        }

        TagNormalizer normalizer = new TagNormalizer();
        LinkedHashSet<String> definitions = new LinkedHashSet<>();
        JsonNode rawDefinitions = root.get("tags");
        if (rawDefinitions != null) {
            if (!rawDefinitions.isArray()) {
                throw failure(ParseFailureCode.TAGS_NOT_ARRAY, "tags");
            }
            definitions.addAll(normalizer.cleanStringArray(rawDefinitions, "tags"));
        }

        List<QuestionBinding> bindings = new ArrayList<>();
        Map<Integer, String> rawQuestionIds = new LinkedHashMap<>();
        JsonNode rawQuestionTags = root.get("question_tags");
        if (rawQuestionTags != null) {
            if (!rawQuestionTags.isObject()) {
                throw failure(ParseFailureCode.QUESTION_TAGS_NOT_OBJECT, "question_tags");
            }
            int bindingCount = 0;
            for (String rawQuestionId : rawQuestionTags.propertyNames()) {
                bindingCount++;
                if (bindingCount > MAX_QUESTION_BINDINGS) {
                    throw failure(
                            ParseFailureCode.QUESTION_BINDING_LIMIT_EXCEEDED,
                            "question_tags");
                }
                int questionId = normalizePositiveInteger(
                        rawQuestionId,
                        ParseFailureCode.QUESTION_ID_INVALID,
                        "question_tags.key");
                String prior = rawQuestionIds.putIfAbsent(questionId, rawQuestionId);
                if (prior != null) {
                    throw failure(
                            ParseFailureCode.QUESTION_ID_COLLISION,
                            "question_tags.key");
                }
                List<String> tags = normalizer.cleanQuestionValue(
                        rawQuestionTags.get(rawQuestionId), "question_tags.value");
                definitions.addAll(tags);
                bindings.add(new QuestionBinding(questionId, tags));
            }
        }

        LinkedHashSet<TagRow> planned = new LinkedHashSet<>();
        for (String tag : definitions) {
            addPlannedRow(planned, new TagRow(TAG_DEFINITION_QUESTION_ID, tag));
        }
        for (QuestionBinding binding : bindings) {
            for (String tag : binding.tags()) {
                addPlannedRow(planned, new TagRow(binding.questionId(), tag));
            }
        }

        List<TagRow> rows = planned.stream().sorted(CANONICAL_ROW_ORDER).toList();
        long definitionCount = rows.stream()
                .filter(row -> row.questionId() == TAG_DEFINITION_QUESTION_ID)
                .count();
        long questionBindingCount = rows.size() - definitionCount;
        long distinctTagCount = rows.stream().map(TagRow::tag).distinct().count();
        return new ParseResult(
                rows,
                Math.toIntExact(definitionCount),
                Math.toIntExact(questionBindingCount),
                Math.toIntExact(distinctTagCount),
                digestRows(rows));
    }

    static boolean isCanonicalTargetTag(String tag) {
        if (tag == null || !isLosslessPostgresText(tag)) {
            return false;
        }
        String stripped = stripPythonWhitespace(tag);
        return !stripped.isEmpty()
                && stripped.equals(tag)
                && !stripped.toLowerCase(Locale.ROOT).equals("all")
                && stripped.codePointCount(0, stripped.length()) <= MAX_TAG_CODE_POINTS;
    }

    static String digestRows(List<TagRow> rows) {
        MessageDigest digest = sha256Digest();
        rows.stream().sorted(CANONICAL_ROW_ORDER).forEach(row -> {
            byte[] tag = row.tag().getBytes(StandardCharsets.UTF_8);
            digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(row.questionId()).array());
            digest.update(ByteBuffer.allocate(Integer.BYTES).putInt(tag.length).array());
            digest.update(tag);
        });
        return java.util.HexFormat.of().formatHex(digest.digest());
    }

    static String sha256(String value) {
        MessageDigest digest = sha256Digest();
        digest.update(Objects.requireNonNull(value, "value").getBytes(StandardCharsets.UTF_8));
        return java.util.HexFormat.of().formatHex(digest.digest());
    }

    static String stripPythonWhitespace(String value) {
        int start = 0;
        int end = value.length();
        while (start < end) {
            int codePoint = value.codePointAt(start);
            if (!isPythonWhitespace(codePoint)) {
                break;
            }
            start += Character.charCount(codePoint);
        }
        while (start < end) {
            int codePoint = value.codePointBefore(end);
            if (!isPythonWhitespace(codePoint)) {
                break;
            }
            end -= Character.charCount(codePoint);
        }
        return value.substring(start, end);
    }

    private static OptionalInt normalizedNearMissBankId(String key) {
        String[] parts = key.split("_", -1);
        if (parts.length < 3 || !parts[0].equals("bank")) {
            return OptionalInt.empty();
        }
        try {
            return OptionalInt.of(normalizePositiveInteger(
                    parts[1], ParseFailureCode.QUESTION_ID_INVALID, "key"));
        } catch (ParseFailure ignored) {
            return OptionalInt.empty();
        }
    }

    private static int normalizePositiveInteger(
            String raw,
            ParseFailureCode failureCode,
            String path
    ) throws ParseFailure {
        if (raw == null) {
            throw failure(failureCode, path);
        }
        String candidate = stripPythonWhitespace(raw);
        if (!INT_COMPATIBLE.matcher(candidate).matches()) {
            throw failure(failureCode, path);
        }
        StringBuilder decimal = new StringBuilder(candidate.length());
        for (int offset = candidate.startsWith("+") ? 1 : 0;
                offset < candidate.length();) {
            int codePoint = candidate.codePointAt(offset);
            offset += Character.charCount(codePoint);
            if (codePoint == '_') {
                continue;
            }
            int digit = Character.digit(codePoint, 10);
            if (digit < 0) {
                throw failure(failureCode, path);
            }
            decimal.append((char) ('0' + digit));
        }
        BigInteger parsed = new BigInteger(decimal.toString());
        if (parsed.signum() <= 0 || parsed.compareTo(MAX_INTEGER) > 0) {
            throw failure(failureCode, path);
        }
        return parsed.intValueExact();
    }

    private static void addPlannedRow(LinkedHashSet<TagRow> rows, TagRow row)
            throws ParseFailure {
        rows.add(row);
        if (rows.size() > MAX_PLANNED_ROWS) {
            throw failure(ParseFailureCode.PLAN_ROW_LIMIT_EXCEEDED, "root");
        }
    }

    private static ParseFailure failure(ParseFailureCode code, String path) {
        return new ParseFailure(code, path);
    }

    private static MessageDigest sha256Digest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("SHA-256 is unavailable", impossible);
        }
    }

    private static boolean isPythonWhitespace(int codePoint) {
        return codePoint >= 0x0009 && codePoint <= 0x000D
                || codePoint >= 0x001C && codePoint <= 0x0020
                || codePoint == 0x0085
                || codePoint == 0x00A0
                || codePoint == 0x1680
                || codePoint >= 0x2000 && codePoint <= 0x200A
                || codePoint == 0x2028
                || codePoint == 0x2029
                || codePoint == 0x202F
                || codePoint == 0x205F
                || codePoint == 0x3000;
    }

    private static boolean isLosslessPostgresText(String value) {
        for (int index = 0; index < value.length(); index++) {
            char current = value.charAt(index);
            if (current == '\u0000') {
                return false;
            }
            if (Character.isHighSurrogate(current)) {
                if (index + 1 >= value.length()
                        || !Character.isLowSurrogate(value.charAt(index + 1))) {
                    return false;
                }
                index++;
            } else if (Character.isLowSurrogate(current)) {
                return false;
            }
        }
        return true;
    }

    enum KeyKind {
        CANONICAL,
        CANONICAL_INVALID,
        NEAR_MISS
    }

    enum KeyFailure {
        NONE,
        BANK_ID_OUT_OF_RANGE,
        NON_CANONICAL_RESERVED_KEY,
        UNPARSEABLE_RESERVED_KEY
    }

    enum ParseFailureCode {
        NULL_PAYLOAD,
        PAYLOAD_LIMIT_EXCEEDED,
        INVALID_JSON,
        ROOT_NOT_OBJECT,
        TAGS_NOT_ARRAY,
        TAG_ITEM_NOT_STRING,
        QUESTION_TAGS_NOT_OBJECT,
        QUESTION_BINDING_LIMIT_EXCEEDED,
        QUESTION_ID_INVALID,
        QUESTION_ID_COLLISION,
        QUESTION_VALUE_INVALID,
        ENCODED_TAG_ARRAY_INVALID,
        TAG_NOT_LOSSLESS,
        TAG_NORMALIZATION_COLLISION,
        PLAN_ROW_LIMIT_EXCEEDED
    }

    record KeyAnalysis(KeyKind kind, OptionalInt normalizedBankId, KeyFailure failure) {
        KeyAnalysis {
            kind = Objects.requireNonNull(kind, "kind");
            normalizedBankId = Objects.requireNonNull(normalizedBankId, "normalizedBankId");
            failure = Objects.requireNonNull(failure, "failure");
        }

        boolean canonical() {
            return kind == KeyKind.CANONICAL;
        }
    }

    record ParseResult(
            List<TagRow> rows,
            int definitionCount,
            int questionBindingCount,
            int distinctTagCount,
            String planDigest
    ) {
        ParseResult {
            rows = List.copyOf(Objects.requireNonNull(rows, "rows"));
            planDigest = Objects.requireNonNull(planDigest, "planDigest");
        }
    }

    record TagRow(int questionId, String tag) {
        TagRow {
            if (questionId < 0) {
                throw new IllegalArgumentException("questionId must be non-negative");
            }
            tag = Objects.requireNonNull(tag, "tag");
            if (!isCanonicalTargetTag(tag)) {
                throw new IllegalArgumentException("tag must be canonical");
            }
        }
    }

    static final class ParseFailure extends Exception {
        private final ParseFailureCode code;
        private final String path;

        private ParseFailure(ParseFailureCode code, String path) {
            super(code.name() + " at " + path);
            this.code = Objects.requireNonNull(code, "code");
            this.path = Objects.requireNonNull(path, "path");
        }

        private ParseFailure(ParseFailureCode code, String path, Throwable cause) {
            super(code.name() + " at " + path, cause);
            this.code = Objects.requireNonNull(code, "code");
            this.path = Objects.requireNonNull(path, "path");
        }

        ParseFailureCode code() {
            return code;
        }

        String path() {
            return path;
        }
    }

    private record QuestionBinding(int questionId, List<String> tags) {
        private QuestionBinding {
            tags = List.copyOf(tags);
        }
    }

    private static final class TagNormalizer {
        private final Map<String, String> sourceByNormalizedTag = new LinkedHashMap<>();

        private List<String> cleanStringArray(JsonNode array, String path)
                throws ParseFailure {
            List<String> values = new ArrayList<>();
            int index = 0;
            for (JsonNode item : array) {
                if (!item.isString()) {
                    throw failure(ParseFailureCode.TAG_ITEM_NOT_STRING, path + ".item");
                }
                values.add(item.asString());
                index++;
                if (index > MAX_PLANNED_ROWS) {
                    throw failure(ParseFailureCode.PLAN_ROW_LIMIT_EXCEEDED, path);
                }
            }
            return clean(values, path);
        }

        private List<String> cleanQuestionValue(JsonNode value, String path)
                throws ParseFailure {
            if (value == null) {
                throw failure(ParseFailureCode.QUESTION_VALUE_INVALID, path);
            }
            if (value.isArray()) {
                return cleanStringArray(value, path);
            }
            if (!value.isString()) {
                throw failure(ParseFailureCode.QUESTION_VALUE_INVALID, path);
            }

            String scalar = stripPythonWhitespace(value.asString());
            if (!scalar.startsWith("[")) {
                return clean(List.of(scalar.replace('，', ',').split(",", -1)), path);
            }
            try {
                JsonNode parsed = JSON.readTree(scalar);
                if (parsed == null || !parsed.isArray()) {
                    throw failure(ParseFailureCode.ENCODED_TAG_ARRAY_INVALID, path);
                }
                return cleanStringArray(parsed, path);
            } catch (ParseFailure failure) {
                throw failure;
            } catch (Exception invalidEncodedArray) {
                throw new ParseFailure(
                        ParseFailureCode.ENCODED_TAG_ARRAY_INVALID,
                        path,
                        invalidEncodedArray);
            }
        }

        private List<String> clean(List<String> raw, String path) throws ParseFailure {
            LinkedHashSet<String> cleaned = new LinkedHashSet<>();
            for (String candidate : raw) {
                if (!isLosslessPostgresText(candidate)) {
                    throw failure(ParseFailureCode.TAG_NOT_LOSSLESS, path);
                }
                String source = stripPythonWhitespace(candidate);
                String tag = source;
                if (tag.codePointCount(0, tag.length()) > MAX_TAG_CODE_POINTS) {
                    tag = stripPythonWhitespace(tag.substring(
                            0, tag.offsetByCodePoints(0, MAX_TAG_CODE_POINTS)));
                }
                if (tag.isEmpty() || tag.toLowerCase(Locale.ROOT).equals("all")) {
                    continue;
                }
                String prior = sourceByNormalizedTag.putIfAbsent(tag, source);
                if (prior != null && !prior.equals(source)) {
                    throw failure(ParseFailureCode.TAG_NORMALIZATION_COLLISION, path);
                }
                cleaned.add(tag);
            }
            return List.copyOf(cleaned);
        }
    }
}
