package io.saksk.ti.web.compat;

import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.api.CatalogApplicationApi;
import io.saksk.ti.catalog.api.SubjectCatalogView;
import io.saksk.ti.catalog.api.SubjectSummaryView;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import io.saksk.ti.web.security.SubjectReadRateLimiter;
import io.saksk.ti.web.security.SubjectReadRequestResolver;
import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Exact compatibility adapter for the two protected legacy subject-directory reads. */
@RestController
@RequestMapping("/api/quiz/subjects")
class LegacySubjectCatalogController {

    private static final String LEGACY_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
    private static final Logger LOGGER = LoggerFactory.getLogger(LegacySubjectCatalogController.class);

    private final CatalogApplicationApi catalog;
    private final SubjectReadRequestResolver subjectReadRoutes;

    LegacySubjectCatalogController(
            CatalogApplicationApi catalog,
            SubjectReadRequestResolver subjectReadRoutes
    ) {
        this.catalog = catalog;
        this.subjectReadRoutes = subjectReadRoutes;
    }

    @GetMapping(produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacySubjectListResponse> subjects(
            @AuthenticationPrincipal TargetAuthenticatedPrincipal principal,
            HttpServletRequest request
    ) {
        SubjectCatalogView current = catalog.subjectCatalog(
                new AuthenticatedCatalogViewer(principal.identityId()));
        List<String> names = current.subjects().stream()
                .map(SubjectSummaryView::name)
                .toList();
        return compatibilityResponse(new LegacySubjectListResponse(
                "success",
                names,
                "",
                new LegacySubjectListData(names),
                RequestId.from(request)));
    }

    @GetMapping(path = "/meta", produces = "application/json;charset=UTF-8")
    ResponseEntity<LegacySubjectMetaResponse> metadata(
            @AuthenticationPrincipal TargetAuthenticatedPrincipal principal,
            HttpServletRequest request
    ) {
        SubjectCatalogView current = catalog.subjectCatalog(
                new AuthenticatedCatalogViewer(principal.identityId()));
        List<LegacySubjectMetaItem> subjects = current.subjects().stream()
                .map(subject -> new LegacySubjectMetaItem(
                        subject.id(),
                        subject.name(),
                        subject.questionCount()))
                .toList();
        return compatibilityResponse(new LegacySubjectMetaResponse(
                "success",
                new LegacySubjectMetaData(subjects, current.quizCount()),
                "",
                RequestId.from(request)));
    }

    private static <T> ResponseEntity<T> compatibilityResponse(T body) {
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, LEGACY_JSON_CONTENT_TYPE)
                .header(HttpHeaders.VARY, "Origin, Cookie")
                .body(body);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<?> safeReadFailure(Exception exception, HttpServletRequest request) {
        LOGGER.error("Subject catalog read failed type={}", exception.getClass().getName());
        Object body = subjectReadRoutes.resolve(request)
                .filter(route -> route == SubjectReadRateLimiter.Route.SUBJECTS_META)
                .isPresent()
                ? new LegacySubjectMetaFailure(
                        "error",
                        "服务暂时不可用",
                        new LegacySubjectMetaData(List.of(), 0),
                        HttpStatus.INTERNAL_SERVER_ERROR.value(),
                        RequestId.from(request))
                : new LegacySubjectListFailure(
                        "error",
                        "服务暂时不可用",
                        List.of(),
                        HttpStatus.INTERNAL_SERVER_ERROR.value(),
                        RequestId.from(request));
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .header(HttpHeaders.CONTENT_TYPE, LEGACY_JSON_CONTENT_TYPE)
                .header(HttpHeaders.VARY, "Origin, Cookie")
                .body(body);
    }

    record LegacySubjectListResponse(
            String status,
            List<String> subjects,
            String message,
            LegacySubjectListData data,
            String requestId
    ) {
    }

    record LegacySubjectListData(List<String> subjects) {
    }

    record LegacySubjectMetaResponse(
            String status,
            LegacySubjectMetaData data,
            String message,
            String requestId
    ) {
    }

    record LegacySubjectMetaData(List<LegacySubjectMetaItem> subjects, long quizCount) {
    }

    record LegacySubjectMetaItem(int id, String name, long questionCount) {
    }

    record LegacySubjectListFailure(
            String status,
            String message,
            List<String> subjects,
            int statusCode,
            String requestId
    ) {
    }

    record LegacySubjectMetaFailure(
            String status,
            String message,
            LegacySubjectMetaData data,
            int statusCode,
            String requestId
    ) {
    }
}
