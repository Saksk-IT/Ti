package io.saksk.ti.learning.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class StudyWriteContractTest {

    @Test
    void normalizesLegacyScopeWithoutCollapsingUnknownPublicSources() {
        assertThat(StudyScopeInput.legacy(null, null, null))
                .isEqualTo(new StudyScopeInput(
                        "public",
                        Optional.empty(),
                        Optional.empty()));
        assertThat(StudyScopeInput.legacy("  USER_BANK ", "  subject  ", 12))
                .isEqualTo(new StudyScopeInput(
                        "user_bank",
                        Optional.of("subject"),
                        Optional.of(12)));
        assertThat(StudyScopeInput.legacy(" Custom ", "  数学  ", null).source())
                .isEqualTo("custom");
        assertThat(StudyScopeInput.legacy(" Custom ", "  数学  ", null).personalBank())
                .isFalse();
    }

    @Test
    void typedResultsCarryDataExactlyForSuccessAndReplayOnlyDurableSuccess() {
        StudyLearnView view = new StudyLearnView(
                3,
                true,
                Optional.of(LocalDateTime.parse("2026-07-24T04:00:00")));
        assertThat(StudyWriteResult.success(view, true))
                .isEqualTo(new StudyWriteResult<>(
                        StudyWriteOutcome.SUCCESS,
                        Optional.of(view),
                        true));
        assertThat(StudyWriteResult.<StudyLearnView>rejected(
                        StudyWriteOutcome.SUBJECT_NOT_FOUND).data())
                .isEmpty();

        assertThatThrownBy(() -> new StudyWriteResult<>(
                        StudyWriteOutcome.SUCCESS,
                        Optional.empty(),
                        false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new StudyWriteResult<>(
                        StudyWriteOutcome.BANK_ACCESS_DENIED,
                        Optional.of(view),
                        false))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new StudyWriteResult<>(
                        StudyWriteOutcome.SUBJECT_INVALID,
                        Optional.empty(),
                        true))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void ratingParsingIsTrimmedCaseInsensitiveAndClosedToUnknownValues() {
        assertThat(StudyReviewRating.fromWireValue(" KNOWN "))
                .contains(StudyReviewRating.KNOWN);
        assertThat(StudyReviewRating.fromWireValue("fUzZy"))
                .contains(StudyReviewRating.FUZZY);
        assertThat(StudyReviewRating.fromWireValue("unknown"))
                .contains(StudyReviewRating.UNKNOWN);
        assertThat(StudyReviewRating.fromWireValue("almost")).isEmpty();
        assertThat(StudyReviewRating.fromWireValue(null)).isEmpty();
    }

    @Test
    void commandsAndIdempotencyKeysNeverExposeCredentialMaterial() {
        LearningWriteIdempotencyKey key = LearningWriteIdempotencyKey.of(
                "密钥-" + "x".repeat(20));
        StudyLearnCommand command = new StudyLearnCommand(
                new AuthenticatedLearningViewer(91),
                101,
                true,
                StudyScopeInput.legacy("public", "数学", null),
                key);

        assertThat(command.toString())
                .doesNotContain("密钥")
                .doesNotContain("数学")
                .contains("<redacted>");
        assertThat(key.value().orElseThrow().getBytes(StandardCharsets.UTF_8))
                .isNotEmpty();
    }
}
