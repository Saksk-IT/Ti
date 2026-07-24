package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.QuestionCatalogRecordView;
import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditIdempotencyKey;
import io.saksk.ti.catalog.api.QuestionEditorIdentity;
import io.saksk.ti.catalog.application.LegacyQuestionEditNormalizer.NormalizationResult;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort.QuestionEditMutation;
import io.saksk.ti.catalog.application.port.QuestionEditStatePort.QuestionEditSnapshot;
import java.time.LocalDateTime;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class LegacyQuestionEditNormalizerTest {

    private static final QuestionEditorIdentity EDITOR =
            new QuestionEditorIdentity(91, true, false);

    @Test
    void normalizesStructuredChoiceEditAndPreservesCatalogMetadata() {
        NormalizationResult result = normalize(
                snapshot(
                        "single_choice",
                        "旧题干",
                        "[{\"key\":\"A\",\"value\":\"旧甲\"},{\"key\":\"B\",\"value\":\"旧乙\"}]",
                        "[0]",
                        "旧解析",
                        "[\"标签一\",\"标签二\"]",
                        3),
                command(
                        Optional.of("  更新&amp;题干  "),
                        Optional.of(" 选择题 "),
                        Optional.of(" a "),
                        Optional.of(" 更新解析 "),
                        Optional.of(
                                "[{\"key\":\"A\",\"value\":\" 甲 \"},"
                                        + "{\"key\":\"B\",\"value\":\"乙\"}]")));

        assertThat(result.validationError()).isEmpty();
        QuestionEditMutation mutation = result.mutation().orElseThrow();
        assertThat(mutation.type()).isEqualTo("single_choice");
        assertThat(mutation.content()).isEqualTo("更新&题干");
        assertThat(mutation.optionsJson()).isEqualTo("[\"甲\",\"乙\"]");
        assertThat(mutation.answerJson()).isEqualTo("[0]");
        assertThat(mutation.analysis()).isEqualTo("更新解析");
        assertThat(mutation.tagsJson()).isEqualTo("[\"标签一\",\"标签二\"]");
        assertThat(mutation.difficulty()).isEqualTo(3);
        assertThat(result.view().orElseThrow().options())
                .extracting("key", "value")
                .containsExactly(
                        org.assertj.core.groups.Tuple.tuple("A", "甲"),
                        org.assertj.core.groups.Tuple.tuple("B", "乙"));
        assertThat(result.view().orElseThrow().answer()).isEqualTo("A");
        assertThat(result.view().orElseThrow().subject()).isEqualTo("高等数学");
        assertThat(result.view().orElseThrow().imagePath()).contains("/q.png");
    }

    @Test
    void rejectsInvalidMultiChoiceButRetainsLegacyMalformedOptionBypass() {
        NormalizationResult tooShort = normalize(
                snapshot("multi_choice", "题干", "[\"甲\",\"乙\"]", "[0,1]", "", "[]", 1),
                command(
                        Optional.empty(),
                        Optional.of("多选题"),
                        Optional.of("A"),
                        Optional.empty(),
                        Optional.of("[\"A. 甲\",\"B. 乙\"]")));
        assertThat(tooShort.validationError())
                .contains("多选题答案至少需要两个选项，例如：AB 或 ABC");

        NormalizationResult invalidKey = normalize(
                snapshot("multi_choice", "题干", "[\"甲\",\"乙\"]", "[0,1]", "", "[]", 1),
                command(
                        Optional.empty(),
                        Optional.of("多选题"),
                        Optional.of("AC"),
                        Optional.empty(),
                        Optional.of("[\"A. 甲\",\"B. 乙\"]")));
        assertThat(invalidKey.validationError()).contains(
                "多选题答案中包含无效选项：C。有效选项为：A, B");

        NormalizationResult malformedOptions = normalize(
                snapshot("multi_choice", "题干", "[\"甲\",\"乙\"]", "[0,1]", "", "[]", 1),
                command(
                        Optional.empty(),
                        Optional.of("多选题"),
                        Optional.of("AZ"),
                        Optional.empty(),
                        Optional.of("legacy-not-json")));
        assertThat(malformedOptions.validationError()).isEmpty();
        assertThat(malformedOptions.mutation().orElseThrow().optionsJson())
                .isEqualTo("[]");
        assertThat(malformedOptions.mutation().orElseThrow().answerJson())
                .isEqualTo("[0,25]");
    }

    @Test
    void mapsBooleanFillAndEssayAnswersExactlyIntoPortableColumns() {
        NormalizationResult booleanResult = normalize(
                snapshot("essay", "题干", "[]", "[]", "", "[]", null),
                command(
                        Optional.empty(),
                        Optional.of("判断题"),
                        Optional.of("正确"),
                        Optional.empty(),
                        Optional.of("[]")));
        assertThat(booleanResult.mutation().orElseThrow().type()).isEqualTo("boolean");
        assertThat(booleanResult.mutation().orElseThrow().optionsJson())
                .isEqualTo("[\"正确\",\"错误\"]");
        assertThat(booleanResult.mutation().orElseThrow().answerJson()).isEqualTo("[true]");
        assertThat(booleanResult.view().orElseThrow().answer()).isEqualTo("正确");

        NormalizationResult fillResult = normalize(
                snapshot("essay", "题干", "[]", "[]", "", "[]", 1),
                command(
                        Optional.of("第一空__第二空__"),
                        Optional.of("填空题"),
                        Optional.of("甲;A;;乙"),
                        Optional.empty(),
                        Optional.of("[]")));
        assertThat(fillResult.mutation().orElseThrow().content())
                .isEqualTo("第一空{0}第二空{1}");
        assertThat(fillResult.mutation().orElseThrow().answerJson())
                .isEqualTo("[[\"甲\",\"A\"],[\"乙\"]]");
        assertThat(fillResult.view().orElseThrow().content())
                .isEqualTo("第一空__第二空__");
        assertThat(fillResult.view().orElseThrow().answer()).isEqualTo("甲;A;;乙");

        NormalizationResult essayResult = normalize(
                snapshot("essay", "题干", "[]", "[]", "", "[]", 9),
                command(
                        Optional.empty(),
                        Optional.of("无法识别题型"),
                        Optional.of("  第一行\r\n第二行  "),
                        Optional.empty(),
                        Optional.empty()));
        assertThat(essayResult.mutation().orElseThrow().type()).isEqualTo("essay");
        assertThat(essayResult.mutation().orElseThrow().answerJson())
                .isEqualTo("[\"第一行\\n第二行\"]");
        assertThat(essayResult.mutation().orElseThrow().difficulty()).isEqualTo(5);
    }

    @Test
    void omittedFieldsUseTheSameLegacyProjectionBeforeWritingPqf() {
        NormalizationResult result = normalize(
                snapshot(
                        "fill",
                        "旧{1}题{0}",
                        "[]",
                        "[[\"乙\"],[\"甲\"]]",
                        "  旧解析  ",
                        "标签一，标签二",
                        0),
                command(
                        Optional.empty(),
                        Optional.empty(),
                        Optional.empty(),
                        Optional.empty(),
                        Optional.empty()));

        QuestionEditMutation mutation = result.mutation().orElseThrow();
        assertThat(mutation.type()).isEqualTo("fill");
        assertThat(mutation.content()).isEqualTo("旧{0}题{1}");
        assertThat(mutation.answerJson()).isEqualTo("[[\"甲\"],[\"乙\"]]");
        assertThat(mutation.analysis()).isEqualTo("旧解析");
        assertThat(mutation.tagsJson()).isEqualTo("[\"标签一\",\"标签二\"]");
        assertThat(mutation.difficulty()).isEqualTo(1);
    }

    private static NormalizationResult normalize(
            QuestionEditSnapshot snapshot,
            QuestionEditCommand command
    ) {
        return LegacyQuestionEditNormalizer.normalize(snapshot, command);
    }

    private static QuestionEditCommand command(
            Optional<String> content,
            Optional<String> type,
            Optional<String> answer,
            Optional<String> explanation,
            Optional<String> options
    ) {
        return new QuestionEditCommand(
                EDITOR,
                93001,
                content,
                type,
                answer,
                explanation,
                options,
                QuestionEditIdempotencyKey.absent());
    }

    private static QuestionEditSnapshot snapshot(
            String type,
            String content,
            String options,
            String answer,
            String analysis,
            String tags,
            Integer difficulty
    ) {
        return new QuestionEditSnapshot(
                new QuestionCatalogRecordView(
                        93001,
                        92001L,
                        type,
                        content,
                        options,
                        answer,
                        analysis,
                        tags,
                        difficulty,
                        "/q.png",
                        "test",
                        91L,
                        91L,
                        LocalDateTime.parse("2026-07-24T01:00:00"),
                        LocalDateTime.parse("2026-07-24T01:00:00")),
                "高等数学");
    }
}
