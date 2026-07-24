package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditOptionView;
import io.saksk.ti.catalog.api.QuestionEditResult;
import io.saksk.ti.catalog.api.QuestionEditView;
import io.saksk.ti.catalog.application.LegacyQuestionEditNormalizer.NormalizationResult;
import io.saksk.ti.catalog.application.port.CatalogQuestionEditReceiptPort;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort.QuestionEditSnapshot;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;
import tools.jackson.databind.json.JsonMapper;

@Service
class QuestionEditWriteTransaction {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Set<String> SUCCESS_FIELDS = Set.of(
            "id",
            "content",
            "q_type",
            "options",
            "answer",
            "explanation",
            "image_path",
            "subject");

    private final QuestionEditStatePort state;
    private final CatalogQuestionEditReceiptPort receipts;

    QuestionEditWriteTransaction(
            QuestionEditStatePort state,
            CatalogQuestionEditReceiptPort receipts
    ) {
        this.state = Objects.requireNonNull(state, "state");
        this.receipts = Objects.requireNonNull(receipts, "receipts");
    }

    @Transactional
    public QuestionEditResult execute(
            QuestionEditCommand command,
            byte[] requestSha256
    ) {
        command = Objects.requireNonNull(command, "command");
        requestSha256 = Objects.requireNonNull(requestSha256, "requestSha256");
        String rawKey = command.idempotencyKey().value().orElse(null);

        // The historical integer route admits zero, while the durable receipt schema intentionally
        // binds only real positive question identities. A missing zero row therefore remains a
        // compatible 404 without manufacturing an invalid receipt.
        boolean durable = rawKey != null && command.questionId() > 0;
        if (durable) {
            CatalogQuestionEditReceiptPort.BeginResult begin =
                    receipts.begin(new CatalogQuestionEditReceiptPort.BeginCommand(
                            command.editor().identityId(),
                            command.questionId(),
                            rawKey,
                            requestSha256));
            switch (begin.outcome()) {
                case CONFLICT:
                    return QuestionEditResult.idempotencyConflict();
                case IN_PROGRESS:
                    return QuestionEditResult.idempotencyInProgress();
                case REPLAY:
                    return decode(begin.replay().orElseThrow(), true);
                case ACQUIRED:
                    break;
            }
        }

        QuestionEditResult result = mutate(command);
        if (!durable) {
            return result;
        }
        CatalogQuestionEditReceiptPort.StoredResponse stored =
                receipts.complete(new CatalogQuestionEditReceiptPort.CompleteCommand(
                        command.editor().identityId(),
                        command.questionId(),
                        rawKey,
                        requestSha256,
                        status(result),
                        encode(result)));
        return decode(stored, false);
    }

    private QuestionEditResult mutate(QuestionEditCommand command) {
        Optional<QuestionEditSnapshot> snapshot =
                state.findForUpdate(command.questionId());
        if (snapshot.isEmpty()) {
            return QuestionEditResult.questionNotFound(false);
        }
        NormalizationResult normalized =
                LegacyQuestionEditNormalizer.normalize(snapshot.orElseThrow(), command);
        if (normalized.validationError().isPresent()) {
            return QuestionEditResult.invalidMultiChoice(
                    normalized.validationError().orElseThrow(),
                    false);
        }
        state.update(normalized.mutation().orElseThrow());
        return QuestionEditResult.success(normalized.view().orElseThrow(), false);
    }

    private static int status(QuestionEditResult result) {
        return switch (result.outcome()) {
            case SUCCESS -> 200;
            case INVALID_MULTI_CHOICE_ANSWER -> 400;
            case QUESTION_NOT_FOUND -> 404;
            default -> throw new IllegalStateException(
                    "Question edit receipt cannot store " + result.outcome());
        };
    }

    private static String encode(QuestionEditResult result) {
        ObjectNode root = JSON.createObjectNode();
        root.put("outcome", result.outcome().name());
        switch (result.outcome()) {
            case SUCCESS -> root.set("data", encodeView(result.data().orElseThrow()));
            case INVALID_MULTI_CHOICE_ANSWER ->
                    root.put("detail", result.detail().orElseThrow());
            case QUESTION_NOT_FOUND -> {
                // The outcome is the complete durable representation.
            }
            default -> throw new IllegalStateException(
                    "Question edit receipt cannot encode " + result.outcome());
        }
        return root.toString();
    }

    private static ObjectNode encodeView(QuestionEditView view) {
        ObjectNode data = JSON.createObjectNode();
        data.put("id", view.id());
        data.put("content", view.content());
        data.put("q_type", view.questionType());
        ArrayNode options = data.putArray("options");
        view.options().forEach(option -> {
            ObjectNode value = options.addObject();
            value.put("key", option.key());
            value.put("value", option.value());
        });
        data.put("answer", view.answer());
        data.put("explanation", view.explanation());
        view.imagePath().ifPresentOrElse(
                value -> data.put("image_path", value),
                () -> data.putNull("image_path"));
        data.put("subject", view.subject());
        return data;
    }

    private static QuestionEditResult decode(
            CatalogQuestionEditReceiptPort.StoredResponse response,
            boolean replayed
    ) {
        try {
            JsonNode root = JSON.readTree(response.bodyJson());
            if (root == null || !root.isObject() || !root.path("outcome").isString()) {
                throw new IllegalStateException(
                        "Question edit receipt body must contain an outcome");
            }
            QuestionEditResult.Outcome outcome = QuestionEditResult.Outcome.valueOf(
                    root.path("outcome").stringValue());
            return switch (outcome) {
                case SUCCESS -> {
                    requireReceiptStatus(response, 200);
                    requireRootFields(root, Set.of("outcome", "data"));
                    yield QuestionEditResult.success(decodeView(root.path("data")), replayed);
                }
                case QUESTION_NOT_FOUND -> {
                    requireReceiptStatus(response, 404);
                    requireRootFields(root, Set.of("outcome"));
                    yield QuestionEditResult.questionNotFound(replayed);
                }
                case INVALID_MULTI_CHOICE_ANSWER -> {
                    requireReceiptStatus(response, 400);
                    requireRootFields(root, Set.of("outcome", "detail"));
                    if (!root.path("detail").isString()) {
                        throw new IllegalStateException(
                                "Question edit receipt contains invalid validation detail");
                    }
                    yield QuestionEditResult.invalidMultiChoice(
                            root.path("detail").stringValue(),
                            replayed);
                }
                default -> throw new IllegalStateException(
                        "Question edit receipt contains a non-durable outcome");
            };
        } catch (IllegalStateException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new IllegalStateException(
                    "Question edit receipt contains invalid values",
                    exception);
        }
    }

    private static QuestionEditView decodeView(JsonNode data) {
        if (!data.isObject()) {
            throw new IllegalStateException("Question edit receipt data must be an object");
        }
        requireRootFields(data, SUCCESS_FIELDS);
        JsonNode id = data.path("id");
        if (!id.isIntegralNumber() || !id.canConvertToLong() || id.longValue() < 0) {
            throw new IllegalStateException("Question edit receipt contains an invalid id");
        }
        JsonNode optionsNode = data.path("options");
        if (!optionsNode.isArray()) {
            throw new IllegalStateException(
                    "Question edit receipt contains invalid options");
        }
        List<QuestionEditOptionView> options = new ArrayList<>();
        for (JsonNode option : optionsNode) {
            requireRootFields(option, Set.of("key", "value"));
            options.add(new QuestionEditOptionView(
                    requireText(option, "key"),
                    requireText(option, "value")));
        }
        JsonNode image = data.path("image_path");
        Optional<String> imagePath;
        if (image.isNull()) {
            imagePath = Optional.empty();
        } else if (image.isString()) {
            imagePath = Optional.of(image.stringValue());
        } else {
            throw new IllegalStateException(
                    "Question edit receipt contains an invalid image path");
        }
        return new QuestionEditView(
                id.longValue(),
                requireText(data, "content"),
                requireText(data, "q_type"),
                options,
                requireText(data, "answer"),
                requireText(data, "explanation"),
                imagePath,
                requireText(data, "subject"));
    }

    private static void requireReceiptStatus(
            CatalogQuestionEditReceiptPort.StoredResponse response,
            int expected
    ) {
        if (response.status() != expected) {
            throw new IllegalStateException(
                    "Question edit receipt contains an invalid status");
        }
    }

    private static void requireRootFields(JsonNode node, Set<String> expected) {
        if (!node.isObject()) {
            throw new IllegalStateException("Question edit receipt value must be an object");
        }
        Set<String> actual = new HashSet<>();
        actual.addAll(node.propertyNames());
        if (!actual.equals(expected)) {
            throw new IllegalStateException(
                    "Question edit receipt contains an invalid field set");
        }
    }

    private static String requireText(JsonNode node, String field) {
        JsonNode value = node.path(field);
        if (!value.isString()) {
            throw new IllegalStateException(
                    "Question edit receipt contains an invalid " + field);
        }
        return value.stringValue();
    }
}
