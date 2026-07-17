package io.saksk.ti.web.compat;

import io.saksk.ti.learning.api.AuthenticatedLearningViewer;
import io.saksk.ti.learning.api.LearningApplicationApi;
import io.saksk.ti.learning.api.PersonalBankUserCountsQuery;
import io.saksk.ti.learning.api.PersonalBankUserCountsResult;
import io.saksk.ti.learning.api.PersonalBankUserCountsView;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.BankIdKind;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Resolution;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** Compatibility HTTP adapter for the two protected personal-bank user-count reads. */
@RestController
class LegacyPersonalBankUserCountsController {

    static final String API_PATH = "/api/user/banks/api/{bankId}/user-counts";
    static final String WEB_PATH = "/user/banks/api/{bankId}/user-counts";

    private static final Logger LOGGER =
            LoggerFactory.getLogger(LegacyPersonalBankUserCountsController.class);
    private static final String LEGACY_JSON_CONTENT_TYPE = "application/json; charset=utf-8";

    private final LearningApplicationApi learning;
    private final PersonalBankUserCountsReadRequestResolver requests;
    private final LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter;

    LegacyPersonalBankUserCountsController(
            LearningApplicationApi learning,
            PersonalBankUserCountsReadRequestResolver requests,
            LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter
    ) {
        this.learning = learning;
        this.requests = requests;
        this.errorWriter = errorWriter;
    }

    @GetMapping(path = {API_PATH, WEB_PATH})
    ResponseEntity<?> userCounts(
            @PathVariable String bankId,
            @AuthenticationPrincipal TargetAuthenticatedPrincipal principal,
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        Resolution resolved = requests.resolveRead(request)
                .orElseThrow(() -> new IllegalStateException(
                        "Mapped user-counts request was not resolved"));
        if (resolved.bankIdKind() != BankIdKind.POSITIVE_INT) {
            writePathBoundary(request, response, resolved);
            return null;
        }
        if (principal == null || principal.identityId() <= 0L) {
            throw new IllegalStateException(
                    "Authenticated user-counts request requires a target principal");
        }

        PersonalBankUserCountsResult result = Objects.requireNonNull(
                learning.findPersonalBankUserCounts(
                        new AuthenticatedLearningViewer(principal.identityId()),
                        new PersonalBankUserCountsQuery(
                                resolved.bankId(),
                                firstParameter(request, "q_type", ""),
                                firstParameter(request, "source", "all"),
                                firstParameter(request, "tag", ""))),
                "learning user-counts result");
        if (result.outcome() == PersonalBankUserCountsResult.Outcome.DENIED) {
            errorWriter.writeDenied(request, response, resolved.alias());
            return null;
        }

        PersonalBankUserCountsView data = result.data().orElseThrow(
                () -> new IllegalStateException("Available user-counts result requires data"));
        LegacyPersonalBankUserCountsSecurityErrorWriter.mergeVary(
                response,
                resolved.alias());
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_TYPE, LEGACY_JSON_CONTENT_TYPE)
                .body(new LegacySuccess(
                        "success",
                        0,
                        data,
                        "",
                        RequestId.from(request)));
    }

    @ExceptionHandler(Exception.class)
    void safeFailure(
            Exception exception,
            HttpServletRequest request,
            HttpServletResponse response
    ) throws IOException {
        LOGGER.error("Personal-bank user-counts read failed type={}",
                exception.getClass().getName());
        errorWriter.writeInternalFailure(request, response, resolveAlias(request));
    }

    private void writePathBoundary(
            HttpServletRequest request,
            HttpServletResponse response,
            Resolution resolved
    ) throws IOException {
        switch (resolved.bankIdKind()) {
            case CONVERTER_MISS ->
                    errorWriter.writeNotFound(request, response, resolved.alias());
            case ZERO -> errorWriter.writeDenied(request, response, resolved.alias());
            case OVERFLOW ->
                    errorWriter.writeInternalFailure(request, response, resolved.alias());
            case POSITIVE_INT -> throw new IllegalStateException(
                    "Positive bank id cannot terminate at the path boundary");
        }
    }

    private Alias resolveAlias(HttpServletRequest request) {
        return requests.resolveRead(request)
                .map(Resolution::alias)
                .orElseGet(() -> applicationPath(request).startsWith("/api/")
                        ? Alias.API
                        : Alias.WEB);
    }

    private static String firstParameter(
            HttpServletRequest request,
            String name,
            String fallback
    ) {
        String[] values = request.getParameterValues(name);
        if (values == null || values.length == 0 || values[0] == null) {
            return fallback;
        }
        return values[0];
    }

    private static String applicationPath(HttpServletRequest request) {
        String requestUri = request.getRequestURI();
        if (requestUri == null) {
            return "";
        }
        String contextPath = request.getContextPath();
        if (contextPath == null || contextPath.isEmpty()) {
            return requestUri;
        }
        return requestUri.startsWith(contextPath)
                ? requestUri.substring(contextPath.length())
                : requestUri;
    }

    record LegacySuccess(
            String status,
            int code,
            PersonalBankUserCountsView data,
            String message,
            String requestId
    ) {
    }
}
