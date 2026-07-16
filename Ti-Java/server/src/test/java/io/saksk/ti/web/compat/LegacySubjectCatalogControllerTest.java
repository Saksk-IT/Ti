package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.api.CatalogApplicationApi;
import io.saksk.ti.catalog.api.SubjectCatalogView;
import io.saksk.ti.catalog.api.SubjectSummaryView;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import io.saksk.ti.web.security.SubjectReadRequestResolver;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

class LegacySubjectCatalogControllerTest {

    @Test
    void rendersLegacyDuplicateListAndMetadataShapesFromOnePublicCatalogBoundary() {
        long[] viewerIdentity = {0};
        CatalogApplicationApi catalog = viewer -> {
            viewerIdentity[0] = viewer.identityId();
            return new SubjectCatalogView(List.of(
                    new SubjectSummaryView(7, "算法", 2),
                    new SubjectSummaryView(9, "数据库", 0)), 2);
        };
        var controller = new LegacySubjectCatalogController(
                catalog,
                new SubjectReadRequestResolver());
        var request = new MockHttpServletRequest();
        request.setAttribute(RequestId.ATTRIBUTE_NAME, "phase4a-controller-001");
        var principal = new TargetAuthenticatedPrincipal(41, "redacted");

        var names = controller.subjects(principal, request);
        var metadata = controller.metadata(principal, request);

        assertThat(viewerIdentity[0]).isEqualTo(41);
        assertThat(names.getHeaders().getFirst("Content-Type"))
                .isEqualTo("application/json; charset=utf-8");
        assertThat(names.getHeaders().getFirst("Vary")).isEqualTo("Origin, Cookie");
        assertThat(names.getBody()).isNotNull();
        assertThat(names.getBody().subjects()).containsExactly("算法", "数据库");
        assertThat(names.getBody().data().subjects())
                .isEqualTo(names.getBody().subjects());
        assertThat(names.getBody().message()).isEmpty();
        assertThat(names.getBody().requestId()).isEqualTo("phase4a-controller-001");

        assertThat(metadata.getBody()).isNotNull();
        assertThat(metadata.getBody().data().quizCount()).isEqualTo(2);
        assertThat(metadata.getBody().data().subjects())
                .extracting(item -> item.id() + ":" + item.name() + ":" + item.questionCount())
                .containsExactly("7:算法:2", "9:数据库:0");
    }

    @Test
    void infrastructureFailuresKeepRouteSpecificLegacyShapesWithoutLeakingTheException() {
        CatalogApplicationApi catalog = viewer -> {
            throw new IllegalStateException("database-password=secret");
        };
        var controller = new LegacySubjectCatalogController(
                catalog,
                new SubjectReadRequestResolver());

        var listRequest = new MockHttpServletRequest("GET", "/api/quiz/subjects");
        listRequest.setAttribute(RequestId.ATTRIBUTE_NAME, "phase4a-list-failure");
        var list = controller.safeReadFailure(new IllegalStateException("secret"), listRequest);
        assertThat(list.getStatusCode().value()).isEqualTo(500);
        assertThat(list.getBody())
                .isEqualTo(new LegacySubjectCatalogController.LegacySubjectListFailure(
                        "error", "服务暂时不可用", List.of(), 500, "phase4a-list-failure"));
        assertThat(list.getBody().toString()).doesNotContain("secret", "password");

        var metaRequest = new MockHttpServletRequest(
                "GET", "/api/quiz/subjects/%6deta");
        metaRequest.setServletPath("/api/quiz/subjects/meta");
        metaRequest.setAttribute(RequestId.ATTRIBUTE_NAME, "phase4a-meta-failure");
        var meta = controller.safeReadFailure(new IllegalStateException("secret"), metaRequest);
        assertThat(meta.getStatusCode().value()).isEqualTo(500);
        assertThat(meta.getBody())
                .isEqualTo(new LegacySubjectCatalogController.LegacySubjectMetaFailure(
                        "error",
                        "服务暂时不可用",
                        new LegacySubjectCatalogController.LegacySubjectMetaData(List.of(), 0),
                        500,
                        "phase4a-meta-failure"));
        assertThat(meta.getBody().toString()).doesNotContain("secret", "password");
    }
}
