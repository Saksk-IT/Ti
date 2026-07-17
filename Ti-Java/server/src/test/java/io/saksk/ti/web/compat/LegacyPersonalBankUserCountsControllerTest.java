package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

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
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class LegacyPersonalBankUserCountsControllerTest {

    private final LearningApplicationApi learning = mock(LearningApplicationApi.class);
    private final PersonalBankUserCountsReadRequestResolver requests =
            mock(PersonalBankUserCountsReadRequestResolver.class);
    private final LegacyPersonalBankUserCountsSecurityErrorWriter errorWriter =
            mock(LegacyPersonalBankUserCountsSecurityErrorWriter.class);
    private final LegacyPersonalBankUserCountsController controller =
            new LegacyPersonalBankUserCountsController(learning, requests, errorWriter);

    @Test
    void availableReadUsesTheAuthoritativePrincipalAndFirstRawParameterValues() throws Exception {
        MockHttpServletRequest request = request(
                "GET",
                "/api/user/banks/api/99551/user-counts",
                "phase4c-controller-available");
        request.addParameter("q_type", " ALL ", "简答题");
        request.addParameter("source", "favorites", "mistakes");
        request.addParameter("tag", " 重点 ", "all");
        request.addParameter("viewer_id", "1");
        MockHttpServletResponse servletResponse = new MockHttpServletResponse();
        servletResponse.addHeader(HttpHeaders.VARY, "Access-Control-Request-Headers, Origin");
        when(requests.resolveRead(request)).thenReturn(Optional.of(
                resolution(Alias.API, BankIdKind.POSITIVE_INT, 99_551)));
        PersonalBankUserCountsView view = new PersonalBankUserCountsView(
                9L,
                5L,
                3L,
                List.of("选择题", "多选题"),
                true);
        when(learning.findPersonalBankUserCounts(any(), any()))
                .thenReturn(PersonalBankUserCountsResult.available(view));

        ResponseEntity<?> response = controller.userCounts(
                "99551",
                new TargetAuthenticatedPrincipal(99_451L, "owner"),
                request,
                servletResponse);

        ArgumentCaptor<AuthenticatedLearningViewer> viewer =
                ArgumentCaptor.forClass(AuthenticatedLearningViewer.class);
        ArgumentCaptor<PersonalBankUserCountsQuery> query =
                ArgumentCaptor.forClass(PersonalBankUserCountsQuery.class);
        verify(learning).findPersonalBankUserCounts(viewer.capture(), query.capture());
        assertThat(viewer.getValue()).isEqualTo(new AuthenticatedLearningViewer(99_451L));
        assertThat(query.getValue()).isEqualTo(new PersonalBankUserCountsQuery(
                99_551,
                " ALL ",
                "favorites",
                " 重点 "));
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getHeaders().getFirst(HttpHeaders.CONTENT_TYPE))
                .isEqualTo("application/json; charset=utf-8");
        var body = (LegacyPersonalBankUserCountsController.LegacySuccess) response.getBody();
        assertThat(body.status()).isEqualTo("success");
        assertThat(body.code()).isZero();
        assertThat(body.data()).isEqualTo(view);
        assertThat(body.message()).isEmpty();
        assertThat(body.requestId()).isEqualTo("phase4c-controller-available");
        assertThat(servletResponse.getHeader(HttpHeaders.VARY))
                .isEqualTo("Access-Control-Request-Headers, Origin, Cookie");
        verifyNoInteractions(errorWriter);
    }

    @Test
    void absentParametersUseTheFrozenHttpDefaults() throws Exception {
        MockHttpServletRequest request = request(
                "GET",
                "/user/banks/api/7/user-counts",
                "phase4c-controller-defaults");
        MockHttpServletResponse servletResponse = new MockHttpServletResponse();
        when(requests.resolveRead(request)).thenReturn(Optional.of(
                resolution(Alias.WEB, BankIdKind.POSITIVE_INT, 7)));
        when(learning.findPersonalBankUserCounts(any(), any()))
                .thenReturn(PersonalBankUserCountsResult.available(
                        new PersonalBankUserCountsView(0L, 0L, 0L, List.of(), false)));

        controller.userCounts(
                "7",
                new TargetAuthenticatedPrincipal(9L, "viewer"),
                request,
                servletResponse);

        ArgumentCaptor<PersonalBankUserCountsQuery> query =
                ArgumentCaptor.forClass(PersonalBankUserCountsQuery.class);
        verify(learning).findPersonalBankUserCounts(any(), query.capture());
        assertThat(query.getValue()).isEqualTo(new PersonalBankUserCountsQuery(
                7,
                "",
                "all",
                ""));
        assertThat(servletResponse.getHeader(HttpHeaders.VARY)).isEqualTo("Cookie");
    }

    @Test
    void applicationDenialUsesTheTerminalCompatibilityEnvelopeWriter() throws Exception {
        MockHttpServletRequest request = request(
                "GET",
                "/api/user/banks/api/99551/user-counts",
                "phase4c-controller-denied");
        MockHttpServletResponse response = new MockHttpServletResponse();
        when(requests.resolveRead(request)).thenReturn(Optional.of(
                resolution(Alias.API, BankIdKind.POSITIVE_INT, 99_551)));
        when(learning.findPersonalBankUserCounts(any(), any()))
                .thenReturn(PersonalBankUserCountsResult.denied());

        ResponseEntity<?> result = controller.userCounts(
                "99551",
                new TargetAuthenticatedPrincipal(99_451L, "owner"),
                request,
                response);

        assertThat(result).isNull();
        verify(errorWriter).writeDenied(request, response, Alias.API);
    }

    @Test
    void nonPositivePathStatesTerminateWithoutCallingTheLearningApi() throws Exception {
        assertPathBoundary(BankIdKind.CONVERTER_MISS, 0);
        assertPathBoundary(BankIdKind.ZERO, 0);
        assertPathBoundary(BankIdKind.OVERFLOW, 0);

        verifyNoInteractions(learning);
    }

    private void assertPathBoundary(BankIdKind kind, int bankId) throws Exception {
        MockHttpServletRequest request = request(
                "GET",
                "/api/user/banks/api/raw/user-counts",
                "phase4c-controller-" + kind.name().toLowerCase());
        MockHttpServletResponse response = new MockHttpServletResponse();
        when(requests.resolveRead(request)).thenReturn(Optional.of(
                resolution(Alias.API, kind, bankId)));

        ResponseEntity<?> result = controller.userCounts(
                "raw",
                new TargetAuthenticatedPrincipal(99_451L, "owner"),
                request,
                response);

        assertThat(result).isNull();
        switch (kind) {
            case CONVERTER_MISS -> verify(errorWriter)
                    .writeNotFound(request, response, Alias.API);
            case ZERO -> verify(errorWriter).writeDenied(request, response, Alias.API);
            case OVERFLOW -> verify(errorWriter)
                    .writeInternalFailure(request, response, Alias.API);
            case POSITIVE_INT -> verify(errorWriter, never())
                    .writeInternalFailure(request, response, Alias.API);
        }
    }

    private static Resolution resolution(Alias alias, BankIdKind kind, int bankId) {
        String normalized = switch (kind) {
            case CONVERTER_MISS -> "";
            case ZERO -> "0";
            case POSITIVE_INT -> Integer.toString(bankId);
            case OVERFLOW -> "2147483648";
        };
        return new Resolution(alias, kind, normalized, bankId);
    }

    private static MockHttpServletRequest request(
            String method,
            String path,
            String requestId
    ) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, path);
        request.setRequestURI(path);
        request.setAttribute(RequestId.ATTRIBUTE_NAME, requestId);
        return request;
    }
}
