package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.catalog.api.QuestionEditApplicationApi;
import io.saksk.ti.catalog.api.QuestionEditCommand;
import io.saksk.ti.catalog.api.QuestionEditOptionView;
import io.saksk.ti.catalog.api.QuestionEditResult;
import io.saksk.ti.catalog.api.QuestionEditView;
import io.saksk.ti.learning.api.CheckinApplicationApi;
import io.saksk.ti.learning.api.CheckinResult;
import io.saksk.ti.learning.api.CheckinView;
import io.saksk.ti.learning.api.LearningWriteApplicationApi;
import io.saksk.ti.learning.api.QuestionLearningStatusApplicationApi;
import io.saksk.ti.learning.api.QuestionLearningStatusView;
import io.saksk.ti.learning.api.RecordResultAction;
import io.saksk.ti.learning.api.RecordResultApplicationApi;
import io.saksk.ti.learning.api.RecordResultResult;
import io.saksk.ti.learning.api.StudyLearnView;
import io.saksk.ti.learning.api.StudyReviewMasterView;
import io.saksk.ti.learning.api.StudyReviewRecordView;
import io.saksk.ti.learning.api.StudyWriteApplicationApi;
import io.saksk.ti.learning.api.StudyWriteResult;
import io.saksk.ti.learning.api.ToggleFavoriteResult;
import io.saksk.ti.operations.api.QuizLimitPolicyApplicationApi;
import io.saksk.ti.operations.api.QuizLimitPolicyView;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

class LegacyTransactionWriteControllerTest {

    private final JsonMapper json = JsonMapper.builder().build();
    private final LearningWriteApplicationApi favorites =
            mock(LearningWriteApplicationApi.class);
    private final RecordResultApplicationApi recordResults =
            mock(RecordResultApplicationApi.class);
    private final StudyWriteApplicationApi study = mock(StudyWriteApplicationApi.class);
    private final CheckinApplicationApi checkins = mock(CheckinApplicationApi.class);
    private final QuestionEditApplicationApi questionEdits =
            mock(QuestionEditApplicationApi.class);
    private final QuestionLearningStatusApplicationApi statuses =
            mock(QuestionLearningStatusApplicationApi.class);
    private final QuizLimitPolicyApplicationApi quizLimits =
            mock(QuizLimitPolicyApplicationApi.class);
    private final LegacyTransactionWriteController controller =
            new LegacyTransactionWriteController(
                    json,
                    favorites,
                    recordResults,
                    study,
                    checkins,
                    questionEdits,
                    statuses,
                    quizLimits);

    @Test
    void favoriteAliasesUseTheServerPrincipalAndFrozenSuccessEnvelope() {
        when(favorites.toggleFavorite(any()))
                .thenReturn(ToggleFavoriteResult.success(true, false));

        ResponseEntity<ObjectNode> response = controller.favorite(
                json.readTree("{\"question_id\":\"93001\"}"),
                "favorite-key",
                authentication("ROLE_USER"),
                request("/api/favorite", "favorite-success"));

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody().path("status").asText()).isEqualTo("success");
        assertThat(response.getBody().path("message").asText()).isEmpty();
        assertThat(response.getBody().path("request_id").asText())
                .isEqualTo("favorite-success");
        assertThat(response.getBody().path("data").path("is_favorite").asBoolean())
                .isTrue();
    }

    @Test
    void recordResultPreservesTheTopLevelAndDataActionAliases() {
        when(quizLimits.getQuizLimitPolicy())
                .thenReturn(new QuizLimitPolicyView(false, 100));
        when(recordResults.recordResult(any()))
                .thenReturn(RecordResultResult.success(
                        RecordResultAction.REMOVED_MISTAKE,
                        false));

        ResponseEntity<ObjectNode> response = controller.recordResult(
                json.readTree("""
                        {"question_id":93001,"is_correct":true,
                         "clear_mistake_on_correct":"false"}
                        """),
                null,
                authentication("ROLE_USER"),
                request("/api/quiz/record_result", "record-success"));

        assertThat(response.getBody().path("action").asText())
                .isEqualTo("removed_mistake");
        assertThat(response.getBody().path("data").path("action").asText())
                .isEqualTo("removed_mistake");
    }

    @Test
    void studyResponsesRetainLegacyIntegerFlagsAndDateTimeText() {
        when(study.recordLearning(any()))
                .thenReturn(StudyWriteResult.success(
                        new StudyLearnView(
                                3,
                                true,
                                Optional.of(LocalDateTime.of(2026, 7, 25, 4, 0))),
                        false));
        when(study.recordReview(any()))
                .thenReturn(StudyWriteResult.success(
                        new StudyReviewRecordView(
                                2,
                                LocalDateTime.of(2026, 7, 27, 15, 20, 1)),
                        false));
        when(study.setReviewMastered(any()))
                .thenReturn(StudyWriteResult.success(
                        new StudyReviewMasterView(true),
                        false));
        Authentication authentication = authentication("ROLE_USER");

        ResponseEntity<ObjectNode> learn = controller.studyLearn(
                json.readTree("""
                        {"question_id":93001,"is_correct":1,
                         "source":"public","subject":"高等数学"}
                        """),
                null,
                authentication,
                request("/api/quiz/study/learn/record", "learn"));
        ResponseEntity<ObjectNode> review = controller.studyReview(
                json.readTree("""
                        {"question_id":93001,"rating":"KNOWN",
                         "source":"public","subject":"高等数学"}
                        """),
                null,
                authentication,
                request("/api/quiz/study/review/record", "review"));
        ResponseEntity<ObjectNode> master = controller.studyMaster(
                json.readTree("""
                        {"question_id":93001,"source":"public",
                         "subject":"高等数学"}
                        """),
                null,
                authentication,
                request("/api/quiz/study/review/master", "master"));

        assertThat(learn.getBody().at("/data/is_learned").asInt()).isOne();
        assertThat(learn.getBody().at("/data/next_due_at").asText())
                .isEqualTo("2026-07-25 04:00:00");
        assertThat(review.getBody().at("/data/review_level").asInt()).isEqualTo(2);
        assertThat(review.getBody().at("/data/next_due_at").asText())
                .isEqualTo("2026-07-27 15:20:01");
        assertThat(master.getBody().at("/data/is_mastered").asInt()).isOne();
    }

    @Test
    void checkinUsesTheRestoredDurableProjection() {
        when(checkins.checkIn(any())).thenReturn(CheckinResult.success(
                new CheckinView(
                        LocalDate.of(2026, 7, 24),
                        true,
                        Optional.of(LocalDateTime.of(2026, 7, 24, 8, 2, 3)),
                        4,
                        8,
                        true,
                        List.of("2026-07-21", "2026-07-24")),
                false));

        ResponseEntity<ObjectNode> response = controller.checkin(
                null,
                authentication("ROLE_USER"),
                request("/api/user/checkin", "checkin"));

        assertThat(response.getBody().at("/data/today").asText())
                .isEqualTo("2026-07-24");
        assertThat(response.getBody().at("/data/checked_in_at").asText())
                .isEqualTo("2026-07-24 08:02:03");
        assertThat(response.getBody().at("/data/checked_dates").size()).isEqualTo(2);
    }

    @Test
    void questionEditUsesAuthoritiesAndLearningOwnedUserFlags() {
        QuestionEditView edited = new QuestionEditView(
                93_001,
                "更新后的题干",
                "选择题",
                List.of(
                        new QuestionEditOptionView("A", "甲"),
                        new QuestionEditOptionView("B", "乙")),
                "A",
                "解析",
                Optional.empty(),
                "高等数学");
        when(questionEdits.editQuestion(any()))
                .thenReturn(QuestionEditResult.success(edited, false));
        when(statuses.findStatus(any(), any(Long.class)))
                .thenReturn(new QuestionLearningStatusView(true, false));

        ResponseEntity<ObjectNode> response = controller.editQuestion(
                "93001",
                json.readTree("""
                        {"content":"更新后的题干","q_type":"选择题",
                         "options":[{"key":"A","value":"甲"},{"key":"B","value":"乙"}],
                         "answer":"A","explanation":"解析"}
                        """),
                "question-key",
                authentication("ROLE_USER", "ROLE_SUBJECT_ADMIN"),
                request("/api/quiz/questions/93001", "question-edit"));

        ArgumentCaptor<QuestionEditCommand> command =
                ArgumentCaptor.forClass(QuestionEditCommand.class);
        verify(questionEdits).editQuestion(command.capture());
        assertThat(command.getValue().editor().subjectAdministrator()).isTrue();
        assertThat(response.getBody().at("/data/is_fav").asInt()).isOne();
        assertThat(response.getBody().at("/data/is_mistake").asInt()).isZero();
        assertThat(response.getBody().at("/data/options/1/value").asText())
                .isEqualTo("乙");
    }

    @Test
    void frozenFirstLayerValidationRunsBeforeApplicationCalls() {
        ResponseEntity<ObjectNode> favorite = controller.favorite(
                json.readTree("{\"question_id\":\"not-an-integer\"}"),
                null,
                authentication("ROLE_USER"),
                request("/api/favorite", "bad-favorite"));
        ResponseEntity<ObjectNode> record = controller.recordResult(
                json.readTree("{}"),
                null,
                authentication("ROLE_USER"),
                request("/api/record_result", "bad-record"));
        ResponseEntity<ObjectNode> review = controller.studyReview(
                json.readTree("{}"),
                null,
                authentication("ROLE_USER"),
                request("/api/quiz/study/review/record", "bad-review"));
        ResponseEntity<ObjectNode> edit = controller.editQuestion(
                "93001",
                json.readTree("{\"content\":42}"),
                null,
                authentication("ROLE_ADMIN"),
                request("/api/quiz/questions/93001", "bad-edit"));

        assertThat(favorite.getBody().path("message").asText())
                .isEqualTo("question_id 参数错误");
        assertThat(record.getBody().path("message").asText()).isEqualTo("参数不完整");
        assertThat(review.getBody().path("message").asText())
                .isEqualTo("rating 参数错误");
        assertThat(edit.getBody().path("message").asText())
                .isEqualTo("content 必须为字符串");
    }

    private static Authentication authentication(String... roles) {
        return new UsernamePasswordAuthenticationToken(
                new TargetAuthenticatedPrincipal(91_001L, "actor"),
                "redacted",
                java.util.Arrays.stream(roles)
                        .map(SimpleGrantedAuthority::new)
                        .toList());
    }

    private static MockHttpServletRequest request(String path, String requestId) {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", path);
        request.setAttribute(RequestId.ATTRIBUTE_NAME, requestId);
        return request;
    }
}
