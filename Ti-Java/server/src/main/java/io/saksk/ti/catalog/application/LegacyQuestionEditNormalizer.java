package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditOptionView;
import io.saksk.ti.catalog.api.QuestionEditView;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort.QuestionEditMutation;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort.QuestionEditSnapshot;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.web.util.HtmlUtils;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Exact Java counterpart of the reviewed legacy PQF edit conversion.
 *
 * <p>This deliberately retains the old merge, trimming, option parsing, answer conversion and
 * malformed-option fallbacks. The approved behavior difference is confined to actually executing
 * the catalog update instead of swallowing the legacy SQLAlchemy 2 positional UPDATE failure.
 */
final class LegacyQuestionEditNormalizer {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Pattern PLACEHOLDER = Pattern.compile("\\{(\\d+)}");
    private static final Pattern ASCII_LETTER = Pattern.compile("[A-Za-z]");
    private static final Pattern EXPLICIT_OPTION_PREFIX = Pattern.compile(
            "^([A-Za-z]|\\d{1,2})\\s*([、.．:：])\\s*(.+)$");
    private static final String ALPHA_SEED = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    private LegacyQuestionEditNormalizer() {
    }

    static NormalizationResult normalize(
            QuestionEditSnapshot snapshot,
            QuestionEditCommand command
    ) {
        Objects.requireNonNull(snapshot, "snapshot");
        Objects.requireNonNull(command, "command");
        LegacyProjection old = projectExisting(snapshot.question());

        String nextType = command.questionType().orElse(old.questionType()).strip();
        String nextContent = command.content().orElse(old.content()).strip();
        String nextAnswer = command.answer().orElse(old.answer()).strip();
        String nextExplanation =
                command.explanation().orElse(old.explanation()).strip();

        ParsedOptions options = command.optionsJsonOrText()
                .map(LegacyQuestionEditNormalizer::parseRequestOptions)
                .orElseGet(() -> ParsedOptions.success(old.options()));

        Optional<String> validationError =
                validateMultiChoice(nextType, nextAnswer, options);
        if (validationError.isPresent()) {
            return NormalizationResult.invalid(validationError.orElseThrow());
        }

        PortableColumns portable = toPortable(
                command.questionId(),
                nextType,
                nextContent,
                options.valueForConversion(),
                nextAnswer,
                nextExplanation,
                old.difficulty(),
                old.tags());
        QuestionEditMutation mutation = portable.toMutation(command.questionId());
        QuestionEditView view = toLegacyView(snapshot, portable);
        return NormalizationResult.success(mutation, view);
    }

    private static Optional<String> validateMultiChoice(
            String questionType,
            String answer,
            ParsedOptions options
    ) {
        if (!"多选题".equals(questionType)) {
            return Optional.empty();
        }
        if (answer.codePointCount(0, answer.length()) < 2) {
            return Optional.of("多选题答案至少需要两个选项，例如：AB 或 ABC");
        }
        if (!options.parsed()) {
            return Optional.empty();
        }
        List<ParsedOption> parsedOptions = parseOptions(options.value());
        Set<String> validKeys = new LinkedHashSet<>();
        parsedOptions.stream()
                .map(ParsedOption::key)
                .filter(key -> !key.isEmpty())
                .forEach(validKeys::add);
        Set<String> answerKeys = new LinkedHashSet<>();
        answer.toUpperCase(Locale.ROOT).codePoints()
                .mapToObj(codePoint -> new String(Character.toChars(codePoint)))
                .forEach(answerKeys::add);
        List<String> invalid = answerKeys.stream()
                .filter(key -> !validKeys.contains(key))
                .sorted()
                .toList();
        if (invalid.isEmpty()) {
            return Optional.empty();
        }
        String valid = validKeys.stream().sorted().reduce(
                (left, right) -> left + ", " + right).orElse("");
        return Optional.of(
                "多选题答案中包含无效选项：" + String.join(", ", invalid)
                        + "。有效选项为：" + valid);
    }

    private static LegacyProjection projectExisting(QuestionCatalogRecordView question) {
        String portableType = normalizePortableType(question.type());
        String questionType = portableToQuestionType(portableType);
        String content = normalizeText(question.content()).strip();
        if ("fill".equals(portableType)) {
            content = PLACEHOLDER.matcher(content).replaceAll("__");
        }

        ArrayNode rawOptions = parseArrayOrEmpty(question.optionsRaw());
        ArrayNode internalOptions = JSON.createArrayNode();
        for (int index = 0; index < rawOptions.size(); index++) {
            String value = normalizeText(pythonString(rawOptions.get(index)));
            if (("single_choice".equals(portableType)
                    || "multi_choice".equals(portableType))
                    && !rawOptions.isEmpty()) {
                String key = index < ALPHA_SEED.length()
                        ? String.valueOf(ALPHA_SEED.charAt(index))
                        : Integer.toString(index + 1);
                value = key + ". " + value;
            }
            internalOptions.add(value);
        }

        JsonNode rawAnswer = parseJsonOrDefaultArray(question.answerRaw());
        String answer = portableAnswerToInternal(
                portableType,
                rawAnswer,
                placeholderOrder(question.content()));
        String analysis = normalizeText(question.analysis()).strip();
        int difficulty = clampDifficulty(question.difficulty());
        ArrayNode tags = normalizeTags(question.tagsRaw());
        return new LegacyProjection(
                questionType,
                content,
                internalOptions,
                answer,
                analysis,
                difficulty,
                tags);
    }

    private static PortableColumns toPortable(
            long questionId,
            String questionType,
            String content,
            JsonNode rawOptions,
            String answer,
            String explanation,
            int difficulty,
            ArrayNode tags
    ) {
        String portableType = questionTypeToPortable(questionType);
        String portableContent = normalizeText(content).strip();
        if ("fill".equals(portableType)) {
            portableContent = internalFillContentToPortable(portableContent);
        }

        ArrayNode options = JSON.createArrayNode();
        if (rawOptions != null && rawOptions.isArray()) {
            parseOptions(rawOptions).stream()
                    .map(ParsedOption::value)
                    .map(LegacyQuestionEditNormalizer::normalizeText)
                    .forEach(options::add);
        }

        String normalizedAnswer = normalizeText(answer).strip();
        ArrayNode portableAnswer = JSON.createArrayNode();
        switch (portableType) {
            case "single_choice" -> {
                List<Integer> indices = answerLettersToIndices(normalizedAnswer);
                if (!indices.isEmpty()) {
                    portableAnswer.add(indices.getFirst());
                }
            }
            case "multi_choice" ->
                    answerLettersToIndices(normalizedAnswer).forEach(portableAnswer::add);
            case "boolean" -> {
                normalizeBoolean(normalizedAnswer).ifPresent(portableAnswer::add);
                if (options.isEmpty()) {
                    options.add("正确");
                    options.add("错误");
                }
            }
            case "fill" -> appendFillAnswer(
                    portableAnswer,
                    normalizedAnswer,
                    countOpeningBraces(portableContent));
            default -> {
                if (!normalizedAnswer.isEmpty()) {
                    portableAnswer.add(normalizedAnswer);
                }
            }
        }

        return new PortableColumns(
                questionId,
                portableType,
                portableContent,
                options,
                portableAnswer,
                normalizeText(explanation).strip(),
                tags.deepCopy(),
                clampDifficulty(difficulty));
    }

    private static QuestionEditView toLegacyView(
            QuestionEditSnapshot snapshot,
            PortableColumns portable
    ) {
        String questionType = portableToQuestionType(portable.type());
        String content = portable.content();
        List<Integer> order = List.of();
        if ("fill".equals(portable.type())) {
            FillInternalContent fill = portableFillContentToInternal(content);
            content = fill.content();
            order = fill.placeholderOrder();
        }

        ArrayNode internalOptions = JSON.createArrayNode();
        for (int index = 0; index < portable.options().size(); index++) {
            String value = normalizeText(pythonString(portable.options().get(index)));
            if (("single_choice".equals(portable.type())
                    || "multi_choice".equals(portable.type()))
                    && !portable.options().isEmpty()) {
                String key = index < ALPHA_SEED.length()
                        ? String.valueOf(ALPHA_SEED.charAt(index))
                        : Integer.toString(index + 1);
                value = key + ". " + value;
            }
            internalOptions.add(value);
        }
        List<QuestionEditOptionView> options = parseOptions(internalOptions).stream()
                .map(option -> new QuestionEditOptionView(option.key(), option.value()))
                .toList();
        if ("boolean".equals(portable.type()) && options.isEmpty()) {
            options = List.of(
                    new QuestionEditOptionView("正确", "正确"),
                    new QuestionEditOptionView("错误", "错误"));
        }

        String answer = portableAnswerToInternal(
                portable.type(),
                portable.answer(),
                order);
        return new QuestionEditView(
                portable.id(),
                content,
                questionType,
                options,
                answer,
                portable.analysis(),
                Optional.ofNullable(snapshot.question().imagePathRaw()),
                snapshot.subjectName());
    }

    private static ParsedOptions parseRequestOptions(String raw) {
        if (raw.strip().isEmpty()) {
            return ParsedOptions.success(JSON.createArrayNode());
        }
        try {
            return ParsedOptions.success(JSON.readTree(raw));
        } catch (Exception exception) {
            return ParsedOptions.failed();
        }
    }

    private static List<ParsedOption> parseOptions(JsonNode rawOptions) {
        if (rawOptions == null || !rawOptions.isArray()) {
            return List.of();
        }
        List<JsonNode> items = new ArrayList<>();
        rawOptions.forEach(items::add);
        List<String> texts = new ArrayList<>();
        for (JsonNode item : items) {
            texts.add(item.isObject() ? null : pythonString(item).strip());
        }
        java.util.Map<Integer, String> compactKeys = compactPrefixKeys(texts);

        List<ParsedOption> parsed = new ArrayList<>();
        for (int index = 0; index < items.size(); index++) {
            JsonNode item = items.get(index);
            if (item.isObject()) {
                String key = pythonTruthyString(item.get("key")).strip();
                String value = stripSpacesAndTabs(pythonTruthyString(item.get("value")));
                parsed.add(new ParsedOption(key, value));
                continue;
            }
            String text = texts.get(index);
            if (text.isEmpty()) {
                parsed.add(new ParsedOption("", ""));
                continue;
            }
            Matcher explicit = EXPLICIT_OPTION_PREFIX.matcher(text);
            if (explicit.matches()
                    && !isNumericDecimalPrefix(
                            explicit.group(1),
                            explicit.group(2),
                            explicit.group(3))) {
                parsed.add(new ParsedOption(
                        explicit.group(1).substring(0, 1).toUpperCase(Locale.ROOT),
                        explicit.group(3).strip()));
                continue;
            }
            String compactKey = compactKeys.get(index);
            if (compactKey != null) {
                parsed.add(new ParsedOption(
                        compactKey,
                        text.substring(1)
                                .replaceFirst("^[ :：.,、\\t\\r\\n]+", "")
                                .strip()));
            } else {
                parsed.add(new ParsedOption("", text));
            }
        }

        if (!parsed.isEmpty() && parsed.stream().allMatch(
                option -> option.key().strip().isEmpty())) {
            List<ParsedOption> keyed = new ArrayList<>();
            for (int index = 0; index < parsed.size(); index++) {
                String key = index < ALPHA_SEED.length()
                        ? String.valueOf(ALPHA_SEED.charAt(index))
                        : Integer.toString(index + 1);
                keyed.add(new ParsedOption(key, parsed.get(index).value()));
            }
            return List.copyOf(keyed);
        }
        return List.copyOf(parsed);
    }

    private static java.util.Map<Integer, String> compactPrefixKeys(List<String> texts) {
        List<Integer> indexes = new ArrayList<>();
        List<String> alpha = new ArrayList<>();
        List<String> digits = new ArrayList<>();
        for (int index = 0; index < texts.size(); index++) {
            String text = texts.get(index);
            if (text == null || text.isEmpty()) {
                continue;
            }
            indexes.add(index);
            alpha.add(compactAlphaKey(text));
            digits.add(compactDigitKey(text));
        }
        if (indexes.isEmpty()) {
            return java.util.Map.of();
        }
        if (allSequential(alpha, ALPHA_SEED)) {
            java.util.Map<Integer, String> result = new java.util.HashMap<>();
            for (int index = 0; index < indexes.size(); index++) {
                result.put(indexes.get(index), alpha.get(index));
            }
            return result;
        }
        if (allSequential(digits, "123456789")) {
            java.util.Map<Integer, String> result = new java.util.HashMap<>();
            for (int index = 0; index < indexes.size(); index++) {
                result.put(indexes.get(index), digits.get(index));
            }
            return result;
        }
        return java.util.Map.of();
    }

    private static String compactAlphaKey(String text) {
        if (text.length() < 2) {
            return null;
        }
        String first = text.substring(0, 1).toUpperCase(Locale.ROOT);
        char second = text.charAt(1);
        if (!ALPHA_SEED.contains(first)
                || (second < 128 && Character.isLetterOrDigit(second))) {
            return null;
        }
        return first;
    }

    private static String compactDigitKey(String text) {
        if (text.length() < 2 || !Character.isDigit(text.charAt(0))) {
            return null;
        }
        char second = text.charAt(1);
        if (second < '\u3400' || second > '\u9fff') {
            return null;
        }
        return text.substring(0, 1);
    }

    private static boolean allSequential(List<String> keys, String seed) {
        if (keys.isEmpty() || keys.stream().anyMatch(Objects::isNull)
                || keys.size() > seed.length()) {
            return false;
        }
        for (int index = 0; index < keys.size(); index++) {
            if (!keys.get(index).equals(String.valueOf(seed.charAt(index)))) {
                return false;
            }
        }
        return true;
    }

    private static boolean isNumericDecimalPrefix(
            String key,
            String delimiter,
            String value
    ) {
        return key.chars().allMatch(Character::isDigit)
                && (".".equals(delimiter) || "．".equals(delimiter))
                && !value.isEmpty()
                && Character.isDigit(value.charAt(0));
    }

    private static String questionTypeToPortable(String questionType) {
        String value = questionType.strip();
        if (value.contains("多选")) {
            return "multi_choice";
        }
        if (value.contains("选择") || value.contains("单选")) {
            return "single_choice";
        }
        if (value.contains("判断")) {
            return "boolean";
        }
        if (value.contains("填空")) {
            return "fill";
        }
        return "essay";
    }

    private static String normalizePortableType(String value) {
        String normalized = Objects.requireNonNullElse(value, "")
                .strip()
                .toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "single", "single_choice", "singlechoice" -> "single_choice";
            case "multi", "multiple", "multi_choice", "multichoice" -> "multi_choice";
            case "boolean", "bool", "judge", "true_false", "truefalse" -> "boolean";
            case "fill", "fill_in_the_blank", "fill-in-the-blank", "fillblank",
                    "fill_in_the_blank_question" -> "fill";
            case "essay", "short_answer", "shortanswer" -> "essay";
            default -> normalized;
        };
    }

    private static String portableToQuestionType(String portableType) {
        return switch (normalizePortableType(portableType)) {
            case "single_choice" -> "选择题";
            case "multi_choice" -> "多选题";
            case "boolean" -> "判断题";
            case "fill" -> "填空题";
            default -> "简答题";
        };
    }

    private static List<Integer> answerLettersToIndices(String answer) {
        Set<Integer> indices = new LinkedHashSet<>();
        Matcher matcher = ASCII_LETTER.matcher(answer);
        while (matcher.find()) {
            char letter = Character.toUpperCase(matcher.group().charAt(0));
            indices.add(letter - 'A');
        }
        return indices.stream().sorted().toList();
    }

    private static String portableAnswerToInternal(
            String portableType,
            JsonNode answer,
            List<Integer> placeholderOrder
    ) {
        return switch (normalizePortableType(portableType)) {
            case "single_choice" -> indicesFromPortableAnswer(answer).stream()
                    .findFirst()
                    .filter(index -> index < 26)
                    .map(index -> String.valueOf((char) ('A' + index)))
                    .orElse("");
            case "multi_choice" -> indicesFromPortableAnswer(answer).stream()
                    .filter(index -> index < 26)
                    .map(index -> String.valueOf((char) ('A' + index)))
                    .reduce("", String::concat);
            case "boolean" -> booleanPortableToInternal(answer);
            case "fill" -> fillPortableToInternal(answer, placeholderOrder);
            default -> essayPortableToInternal(answer);
        };
    }

    private static List<Integer> indicesFromPortableAnswer(JsonNode answer) {
        List<JsonNode> values = new ArrayList<>();
        if (answer != null && answer.isArray()) {
            answer.forEach(values::add);
        } else if (answer != null && !answer.isNull()) {
            values.add(answer);
        }
        Set<Integer> indices = new LinkedHashSet<>();
        for (JsonNode value : values) {
            if (value.isBoolean()) {
                continue;
            }
            try {
                int index = value.isNumber()
                        ? (int) value.doubleValue()
                        : Integer.parseInt(value.asString());
                if (index >= 0) {
                    indices.add(index);
                }
            } catch (RuntimeException ignored) {
                // Legacy int conversion drops malformed choice entries.
            }
        }
        return indices.stream().sorted().toList();
    }

    private static Optional<Boolean> normalizeBoolean(String raw) {
        String value = raw.strip().toLowerCase(Locale.ROOT);
        return switch (value) {
            case "true", "t", "1", "yes", "y", "对", "正确", "是", "√" ->
                    Optional.of(true);
            case "false", "f", "0", "no", "n", "错", "错误", "否", "×" ->
                    Optional.of(false);
            default -> Optional.empty();
        };
    }

    private static String booleanPortableToInternal(JsonNode answer) {
        JsonNode value = answer;
        if (answer != null && answer.isArray()) {
            value = answer.isEmpty() ? null : answer.get(0);
        }
        if (value == null || value.isNull()) {
            return "";
        }
        if (value.isBoolean()) {
            return value.booleanValue() ? "正确" : "错误";
        }
        if (value.isNumber()) {
            return value.intValue() == 0 ? "正确" : "错误";
        }
        return normalizeBoolean(value.asString())
                .map(result -> result ? "正确" : "错误")
                .orElse("");
    }

    private static void appendFillAnswer(
            ArrayNode destination,
            String answer,
            int blankCount
    ) {
        if (answer.isEmpty()) {
            return;
        }
        List<ArrayNode> groups = new ArrayList<>();
        for (String group : answer.split(";;", -1)) {
            ArrayNode alternatives = JSON.createArrayNode();
            for (String candidate : group.split(";", -1)) {
                String value = normalizeText(candidate).strip();
                if (!value.isEmpty()) {
                    alternatives.add(value);
                }
            }
            groups.add(alternatives);
        }
        if (blankCount > 0) {
            while (groups.size() < blankCount) {
                groups.add(JSON.createArrayNode());
            }
            if (groups.size() > blankCount) {
                groups = new ArrayList<>(groups.subList(0, blankCount));
            }
        }
        groups.forEach(destination::add);
    }

    private static String fillPortableToInternal(
            JsonNode answer,
            List<Integer> placeholderOrder
    ) {
        if (answer == null || !answer.isArray()) {
            return "";
        }
        List<List<String>> groups = new ArrayList<>();
        for (JsonNode group : answer) {
            List<String> alternatives = new ArrayList<>();
            if (group.isArray()) {
                for (JsonNode candidate : group) {
                    String value = normalizeText(pythonString(candidate)).strip();
                    if (!value.isEmpty()) {
                        alternatives.add(value);
                    }
                }
            } else {
                String value = normalizeText(pythonString(group)).strip();
                if (!value.isEmpty()) {
                    alternatives.add(value);
                }
            }
            groups.add(List.copyOf(alternatives));
        }
        List<Integer> order = placeholderOrder.isEmpty()
                ? java.util.stream.IntStream.range(0, groups.size()).boxed().toList()
                : placeholderOrder;
        List<String> ordered = new ArrayList<>();
        for (int index : order) {
            ordered.add(index >= 0 && index < groups.size()
                    ? String.join(";", groups.get(index))
                    : "");
        }
        return String.join(";;", ordered).replaceAll("^;+|;+$", "");
    }

    private static String essayPortableToInternal(JsonNode answer) {
        if (answer == null || answer.isNull()) {
            return "";
        }
        if (!answer.isArray()) {
            return normalizeText(pythonString(answer)).strip();
        }
        List<String> values = new ArrayList<>();
        for (JsonNode value : answer) {
            String normalized = normalizeText(pythonString(value)).stripTrailing();
            if (!normalized.strip().isEmpty()) {
                values.add(normalized);
            }
        }
        return String.join("\n", values).strip();
    }

    private static String internalFillContentToPortable(String content) {
        String[] parts = normalizeNewlines(content).split("__", -1);
        if (parts.length == 1) {
            return content;
        }
        StringBuilder result = new StringBuilder();
        for (int index = 0; index < parts.length; index++) {
            result.append(parts[index]);
            if (index < parts.length - 1) {
                result.append('{').append(index).append('}');
            }
        }
        return result.toString();
    }

    private static FillInternalContent portableFillContentToInternal(String content) {
        Matcher matcher = PLACEHOLDER.matcher(normalizeNewlines(content));
        StringBuilder result = new StringBuilder();
        List<Integer> order = new ArrayList<>();
        while (matcher.find()) {
            order.add(Integer.parseInt(matcher.group(1)));
            matcher.appendReplacement(result, "__");
        }
        matcher.appendTail(result);
        if (order.isEmpty()) {
            int count = countOccurrences(result.toString(), "__");
            order = java.util.stream.IntStream.range(0, count).boxed().toList();
        }
        return new FillInternalContent(result.toString(), List.copyOf(order));
    }

    private static List<Integer> placeholderOrder(String content) {
        Matcher matcher = PLACEHOLDER.matcher(normalizeNewlines(content));
        List<Integer> order = new ArrayList<>();
        while (matcher.find()) {
            order.add(Integer.parseInt(matcher.group(1)));
        }
        return List.copyOf(order);
    }

    private static int countOpeningBraces(String value) {
        return (int) value.chars().filter(character -> character == '{').count();
    }

    private static int countOccurrences(String value, String token) {
        int count = 0;
        int offset = 0;
        while ((offset = value.indexOf(token, offset)) >= 0) {
            count++;
            offset += token.length();
        }
        return count;
    }

    private static ArrayNode normalizeTags(String rawTags) {
        ArrayNode tags = JSON.createArrayNode();
        if (rawTags == null) {
            return tags;
        }
        String value = rawTags.strip();
        if (value.isEmpty()) {
            return tags;
        }
        if (value.startsWith("[")) {
            try {
                JsonNode parsed = JSON.readTree(value);
                if (parsed.isArray()) {
                    for (JsonNode tag : parsed) {
                        String normalized = pythonString(tag).strip();
                        if (!normalized.isEmpty()) {
                            tags.add(normalized);
                        }
                    }
                    return tags;
                }
            } catch (Exception ignored) {
                // Fall through to comma-separated legacy parsing.
            }
        }
        for (String tag : value.replace('，', ',').split(",")) {
            String normalized = tag.strip();
            if (!normalized.isEmpty()
                    && !"[]".equals(normalized)
                    && !"[ ]".equals(normalized)) {
                tags.add(normalized);
            }
        }
        return tags;
    }

    private static ArrayNode parseArrayOrEmpty(String raw) {
        JsonNode parsed = parseJsonOrDefaultArray(raw);
        return parsed.isArray() ? (ArrayNode) parsed : JSON.createArrayNode();
    }

    private static JsonNode parseJsonOrDefaultArray(String raw) {
        if (raw == null) {
            return JSON.createArrayNode();
        }
        try {
            return JSON.readTree(raw);
        } catch (Exception exception) {
            return JSON.createArrayNode();
        }
    }

    private static String normalizeText(Object raw) {
        String value = normalizeNewlines(Objects.requireNonNullElse(raw, "").toString());
        for (int iteration = 0; iteration < 3; iteration++) {
            String decoded = HtmlUtils.htmlUnescape(value)
                    .replace('\u00a0', ' ')
                    .replace("\u2003", "  ");
            if (decoded.equals(value)) {
                break;
            }
            value = decoded;
        }
        return value;
    }

    private static String normalizeNewlines(String value) {
        return value.replace("\r\n", "\n").replace('\r', '\n');
    }

    private static String stripSpacesAndTabs(String value) {
        int start = 0;
        int end = value.length();
        while (start < end && (value.charAt(start) == ' ' || value.charAt(start) == '\t')) {
            start++;
        }
        while (end > start
                && (value.charAt(end - 1) == ' ' || value.charAt(end - 1) == '\t')) {
            end--;
        }
        return value.substring(start, end);
    }

    private static String pythonTruthyString(JsonNode value) {
        if (value == null || value.isNull()
                || (value.isBoolean() && !value.booleanValue())
                || (value.isNumber() && value.doubleValue() == 0.0d)
                || (value.isString() && value.stringValue().isEmpty())) {
            return "";
        }
        return pythonString(value);
    }

    private static String pythonString(JsonNode value) {
        if (value == null || value.isNull()) {
            return "None";
        }
        if (value.isString()) {
            return value.stringValue();
        }
        if (value.isBoolean()) {
            return value.booleanValue() ? "True" : "False";
        }
        if (value.isNumber()) {
            return value.asString();
        }
        if (value.isArray()) {
            List<String> values = new ArrayList<>();
            value.forEach(item -> values.add(pythonRepr(item)));
            return "[" + String.join(", ", values) + "]";
        }
        if (value.isObject()) {
            List<String> fields = new ArrayList<>();
            value.properties().forEach(entry -> fields.add(
                    quotePython(entry.getKey()) + ": " + pythonRepr(entry.getValue())));
            return "{" + String.join(", ", fields) + "}";
        }
        return value.toString();
    }

    private static String pythonRepr(JsonNode value) {
        return value != null && value.isString()
                ? quotePython(value.stringValue())
                : pythonString(value);
    }

    private static String quotePython(String value) {
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'";
    }

    private static int clampDifficulty(Integer difficulty) {
        int value = difficulty == null || difficulty == 0 ? 1 : difficulty;
        return Math.max(1, Math.min(5, value));
    }

    record NormalizationResult(
            Optional<QuestionEditMutation> mutation,
            Optional<QuestionEditView> view,
            Optional<String> validationError
    ) {
        NormalizationResult {
            mutation = Objects.requireNonNull(mutation, "mutation");
            view = Objects.requireNonNull(view, "view");
            validationError = Objects.requireNonNull(validationError, "validationError");
            boolean successful = mutation.isPresent() && view.isPresent();
            if (successful == validationError.isPresent()
                    || mutation.isPresent() != view.isPresent()) {
                throw new IllegalArgumentException("Invalid normalization result");
            }
        }

        static NormalizationResult success(
                QuestionEditMutation mutation,
                QuestionEditView view
        ) {
            return new NormalizationResult(
                    Optional.of(mutation),
                    Optional.of(view),
                    Optional.empty());
        }

        static NormalizationResult invalid(String message) {
            return new NormalizationResult(
                    Optional.empty(),
                    Optional.empty(),
                    Optional.of(message));
        }
    }

    private record LegacyProjection(
            String questionType,
            String content,
            ArrayNode options,
            String answer,
            String explanation,
            int difficulty,
            ArrayNode tags
    ) {
    }

    private record PortableColumns(
            long id,
            String type,
            String content,
            ArrayNode options,
            ArrayNode answer,
            String analysis,
            ArrayNode tags,
            int difficulty
    ) {
        QuestionEditMutation toMutation(long questionId) {
            return new QuestionEditMutation(
                    questionId,
                    type,
                    content,
                    options.toString(),
                    answer.toString(),
                    analysis,
                    tags.toString(),
                    difficulty);
        }
    }

    private record ParsedOption(String key, String value) {
    }

    private record ParsedOptions(boolean parsed, JsonNode value) {
        private ParsedOptions {
            value = Objects.requireNonNull(value, "value");
        }

        static ParsedOptions success(JsonNode value) {
            return new ParsedOptions(true, value);
        }

        static ParsedOptions failed() {
            return new ParsedOptions(false, JSON.createArrayNode());
        }

        JsonNode valueForConversion() {
            return parsed ? value : JSON.createArrayNode();
        }
    }

    private record FillInternalContent(String content, List<Integer> placeholderOrder) {
    }
}
