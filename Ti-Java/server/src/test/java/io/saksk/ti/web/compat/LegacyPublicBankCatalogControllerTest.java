package io.saksk.ti.web.compat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.api.PublicBankBoardRef;
import io.saksk.ti.catalog.api.PublicBankCardView;
import io.saksk.ti.catalog.api.PublicBankCatalogApi;
import io.saksk.ti.catalog.api.PublicBankDetailView;
import io.saksk.ti.catalog.api.PublicBankHotQuery;
import io.saksk.ti.catalog.api.PublicBankPageView;
import io.saksk.ti.catalog.api.PublicBankRef;
import io.saksk.ti.catalog.api.PublicBankRelationView;
import io.saksk.ti.catalog.api.PublicBankSearchQuery;
import io.saksk.ti.catalog.api.PublicBankSort;
import io.saksk.ti.catalog.api.PublicBankSource;
import io.saksk.ti.web.request.RequestId;
import io.saksk.ti.web.security.TargetAuthenticatedPrincipal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import tools.jackson.databind.node.NullNode;

class LegacyPublicBankCatalogControllerTest {

    private final PublicBankCatalogApi catalog = mock(PublicBankCatalogApi.class);
    private final LegacyPublicBankCatalogController controller =
            new LegacyPublicBankCatalogController(catalog);

    @Test
    void legacyListPreservesCaseSensitiveSortSourceAndZeroPageSizeQuirks() {
        when(catalog.search(any(), any())).thenAnswer(invocation -> {
            PublicBankSearchQuery query = invocation.getArgument(0);
            return page(query, List.of(card(PublicBankSource.USER_PUBLIC)));
        });
        MockHttpServletRequest request = request("/api/public/banks");
        request.addParameter("sort", "popular");
        request.addParameter("type", "system");
        request.addParameter("page", "-9");
        request.addParameter("per_page", "0");
        request.addParameter("keyword", "  Needle   USER ");

        ResponseEntity<LegacyPublicBankCatalogController.LegacySuccess> response =
                controller.legacyList(null, request);

        ArgumentCaptor<PublicBankSearchQuery> query =
                ArgumentCaptor.forClass(PublicBankSearchQuery.class);
        ArgumentCaptor<Optional<AuthenticatedCatalogViewer>> viewer = optionalViewerCaptor();
        org.mockito.Mockito.verify(catalog).search(query.capture(), viewer.capture());
        assertThat(query.getValue().sort()).isEqualTo(PublicBankSort.HOT);
        assertThat(query.getValue().filter().source()).contains(PublicBankSource.SYSTEM);
        assertThat(query.getValue().filter().keyword()).isEqualTo("needle user");
        assertThat(query.getValue().page()).isOne();
        assertThat(query.getValue().pageSize()).isEqualTo(12);
        assertThat(viewer.getValue()).isEmpty();
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(data(response).get("total")).isEqualTo(1L);
    }

    @Test
    void plazaListNormalizesTabAndServerDerivedViewerWithoutTrustingRequestIdentity() {
        when(catalog.search(any(), any())).thenAnswer(invocation -> {
            PublicBankSearchQuery query = invocation.getArgument(0);
            return page(query, List.of());
        });
        MockHttpServletRequest request = request("/api/public/banks/list");
        request.addParameter("tab", " QuEsTiOnS ");
        request.addParameter("board_id", " +5201 ");
        request.addParameter("page", "bad");
        request.addParameter("per_page", "-4");
        request.addParameter("identity_id", "999999");
        TargetAuthenticatedPrincipal principal = new TargetAuthenticatedPrincipal(5102, "viewer");

        ResponseEntity<LegacyPublicBankCatalogController.LegacySuccess> response =
                controller.plazaList(principal, request);

        ArgumentCaptor<PublicBankSearchQuery> query =
                ArgumentCaptor.forClass(PublicBankSearchQuery.class);
        ArgumentCaptor<Optional<AuthenticatedCatalogViewer>> viewer = optionalViewerCaptor();
        org.mockito.Mockito.verify(catalog).search(query.capture(), viewer.capture());
        assertThat(query.getValue().sort()).isEqualTo(PublicBankSort.QUESTIONS);
        assertThat(query.getValue().filter().boardId()).contains(5201L);
        assertThat(query.getValue().page()).isOne();
        assertThat(query.getValue().pageSize()).isOne();
        assertThat(viewer.getValue()).contains(new AuthenticatedCatalogViewer(5102));
        assertThat(data(response).get("tab")).isEqualTo("questions");
        assertThat(data(response).get("available_tabs"))
                .isEqualTo(List.of("latest", "hot", "active", "featured"));
    }

    @Test
    void detailFlattensTheLegacyUserFieldsAndPreservesNulls() {
        PublicBankCardView card = card(PublicBankSource.USER_PUBLIC);
        when(catalog.detail(any(), any()))
                .thenReturn(Optional.of(new PublicBankDetailView(card, 7, 5101L, true)));
        MockHttpServletRequest request = request("/api/public/banks/card/user/5401");

        ResponseEntity<?> response = controller.cardDetail(
                "user", "5401", new TargetAuthenticatedPrincipal(5101, "owner"), request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        var body = (LegacyPublicBankCatalogController.LegacySuccess) response.getBody();
        @SuppressWarnings("unchecked")
        Map<String, Object> detail = (Map<String, Object>) body.data();
        assertThat(detail)
                .containsEntry("bank_type", "user")
                .containsEntry("share_count", 7L)
                .containsEntry("author_id", 5101L)
                .containsEntry("is_owner", true)
                .containsEntry("source_type", "user_public")
                .containsEntry("source_label", "用户公开")
                .containsEntry("detail_url", "/public/banks/card/user/5401")
                .containsEntry("practice_url", "/user/banks/5401/practice")
                .containsEntry("published_at", "2026-07-15 08:30:00");
        assertThat(detail.get("cover_image")).isEqualTo(NullNode.getInstance());
    }

    @Test
    void malformedPathIdentifierUsesTheLegacyConverter404Envelope() {
        MockHttpServletRequest request = request("/api/public/banks/-1");

        ResponseEntity<?> response = controller.detailAlias("-1", null, request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        var body = (LegacyPublicBankCatalogController.LegacyConverterError) response.getBody();
        assertThat(body.status()).isEqualTo("error");
        assertThat(body.statusCode()).isEqualTo(404);
        assertThat(body.payload()).isEqualTo(NullNode.getInstance());
        assertThat(body.message()).contains("requested URL was not found");
        assertThat(response.getHeaders().getFirst(HttpHeaders.CONTENT_TYPE))
                .isEqualTo("application/json");
        assertThat(response.getHeaders().getFirst("X-RateLimit-Limit")).isNull();
        assertThat(response.getHeaders().getFirst("X-RateLimit-Remaining")).isNull();
        assertThat(response.getHeaders().getFirst("X-RateLimit-Reset")).isNull();
        assertThat(response.getHeaders().getFirst(HttpHeaders.RETRY_AFTER)).isNull();
    }

    @Test
    void arbitraryPrecisionPathIdentifiersUseTheApprovedSafe500WithoutCatalogLookup() {
        String arbitraryPrecisionId = "999999999999999999999999999999999999999999999999";
        MockHttpServletRequest detailRequest =
                request("/api/public/banks/" + arbitraryPrecisionId);
        MockHttpServletRequest cardRequest =
                request("/api/public/banks/card/user/" + arbitraryPrecisionId);

        ResponseEntity<?> detail =
                controller.detailAlias(arbitraryPrecisionId, null, detailRequest);
        ResponseEntity<?> card =
                controller.cardDetail("user", arbitraryPrecisionId, null, cardRequest);

        assertSafeInternalFailure(detail);
        assertSafeInternalFailure(card);
        org.mockito.Mockito.verifyNoInteractions(catalog);
    }

    @Test
    void zeroAndLongMaxPathIdentifiersStillReachTheCatalog() {
        when(catalog.detail(any(), any())).thenReturn(Optional.empty());

        ResponseEntity<?> zero = controller.cardDetail(
                "system", "0", null, request("/api/public/banks/card/system/0"));
        ResponseEntity<?> longMax = controller.detailAlias(
                Long.toString(Long.MAX_VALUE),
                null,
                request("/api/public/banks/" + Long.MAX_VALUE));

        assertThat(zero.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(longMax.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        ArgumentCaptor<PublicBankRef> references = ArgumentCaptor.forClass(PublicBankRef.class);
        org.mockito.Mockito.verify(catalog, org.mockito.Mockito.times(2))
                .detail(references.capture(), any());
        assertThat(references.getAllValues()).containsExactly(
                new PublicBankRef(PublicBankSource.SYSTEM, 0),
                new PublicBankRef(PublicBankSource.USER_PUBLIC, Long.MAX_VALUE));
    }

    @Test
    void unicodeDecimalPathIdentifiersNormalizeLikeWerkzeugBeforeCatalogLookup() {
        when(catalog.detail(any(), any())).thenReturn(Optional.empty());

        ResponseEntity<?> arabicIndic = controller.detailAlias(
                "٥٤٠١", null, request("/api/public/banks/٥٤٠١"));
        ResponseEntity<?> fullwidth = controller.cardDetail(
                "system", "５３０１", null,
                request("/api/public/banks/card/system/５３０１"));
        ResponseEntity<?> supplementary = controller.detailAlias(
                "𝟝𝟜𝟘𝟙", null, request("/api/public/banks/𝟝𝟜𝟘𝟙"));

        assertThat(arabicIndic.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(fullwidth.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(supplementary.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        ArgumentCaptor<PublicBankRef> references = ArgumentCaptor.forClass(PublicBankRef.class);
        org.mockito.Mockito.verify(catalog, org.mockito.Mockito.times(3))
                .detail(references.capture(), any());
        assertThat(references.getAllValues()).containsExactly(
                new PublicBankRef(PublicBankSource.USER_PUBLIC, 5401),
                new PublicBankRef(PublicBankSource.SYSTEM, 5301),
                new PublicBankRef(PublicBankSource.USER_PUBLIC, 5401));
    }

    @Test
    void unicodeArbitraryPrecisionIdentifierUsesTheApprovedSafe500() {
        String hugeFullwidth = "９".repeat(48);

        ResponseEntity<?> response = controller.detailAlias(
                hugeFullwidth, null, request("/api/public/banks/" + hugeFullwidth));

        assertSafeInternalFailure(response);
        org.mockito.Mockito.verifyNoInteractions(catalog);
    }

    @Test
    void arbitraryPrecisionPageSizeAndLimitValuesUseTheLegacyClamps() {
        when(catalog.search(any(), any())).thenAnswer(invocation -> {
            PublicBankSearchQuery query = invocation.getArgument(0);
            return page(query, List.of());
        });
        when(catalog.hot(any(PublicBankHotQuery.class), any())).thenReturn(List.of());
        String hugePositive = "999999999999999999999999999999999999999999999999";
        String hugeNegative = "-999999999999999999999999999999999999999999999999";

        MockHttpServletRequest legacy = request("/api/public/banks");
        legacy.addParameter("page", hugeNegative);
        legacy.addParameter("per_page", hugePositive);
        controller.legacyList(null, legacy);

        MockHttpServletRequest plaza = request("/api/public/banks/list");
        plaza.addParameter("page", hugeNegative);
        plaza.addParameter("per_page", hugePositive);
        controller.plazaList(null, plaza);

        MockHttpServletRequest hot = request("/api/public/banks/hot");
        hot.addParameter("limit", hugePositive);
        controller.hot(hot);

        ArgumentCaptor<PublicBankSearchQuery> searches =
                ArgumentCaptor.forClass(PublicBankSearchQuery.class);
        org.mockito.Mockito.verify(catalog, org.mockito.Mockito.times(2))
                .search(searches.capture(), any());
        assertThat(searches.getAllValues())
                .extracting(PublicBankSearchQuery::page)
                .containsExactly(1, 1);
        assertThat(searches.getAllValues())
                .extracting(PublicBankSearchQuery::pageSize)
                .containsExactly(50, 50);

        ArgumentCaptor<PublicBankHotQuery> hotQuery =
                ArgumentCaptor.forClass(PublicBankHotQuery.class);
        org.mockito.Mockito.verify(catalog).hot(hotQuery.capture(), any());
        assertThat(hotQuery.getValue().limit()).isEqualTo(10);
    }

    private static PublicBankPageView page(
            PublicBankSearchQuery query,
            List<PublicBankCardView> items
    ) {
        return new PublicBankPageView(
                items,
                items.size(),
                query.page(),
                query.pageSize(),
                query.sort(),
                query.filter(),
                List.of(
                        PublicBankSort.LATEST,
                        PublicBankSort.HOT,
                        PublicBankSort.ACTIVE,
                        PublicBankSort.FEATURED));
    }

    private static PublicBankCardView card(PublicBankSource source) {
        return new PublicBankCardView(
                source == PublicBankSource.SYSTEM ? 5301 : 5401,
                source,
                "Atlas Needle User",
                "fixture",
                null,
                source == PublicBankSource.SYSTEM ? "系统题库" : "用户公开",
                null,
                9,
                4,
                2,
                2,
                3,
                19.23,
                10.45,
                21.23,
                LocalDateTime.of(2026, 7, 15, 8, 30),
                LocalDateTime.of(2026, 7, 16, 9, 30),
                false,
                0,
                new PublicBankBoardRef(5201, "alpha", "Alpha"),
                "free",
                "",
                source == PublicBankSource.USER_PUBLIC,
                PublicBankRelationView.NONE);
    }

    private static MockHttpServletRequest request(String path) {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", path);
        request.addHeader("X-Request-ID", "phase4a-controller-test");
        request.setAttribute(RequestId.ATTRIBUTE_NAME, "phase4a-controller-test");
        return request;
    }

    private static void assertSafeInternalFailure(ResponseEntity<?> response) {
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
        assertThat(response.getHeaders().getFirst(HttpHeaders.CONTENT_TYPE))
                .isEqualTo("application/json; charset=utf-8");
        var body = (LegacyPublicBankCatalogController.LegacyError) response.getBody();
        assertThat(body.status()).isEqualTo("error");
        assertThat(body.code()).isOne();
        assertThat(body.message()).isEqualTo("服务暂时不可用");
        assertThat(body.statusCode()).isEqualTo(500);
        assertThat(body.requestId()).isEqualTo("phase4a-controller-test");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> data(
            ResponseEntity<LegacyPublicBankCatalogController.LegacySuccess> response
    ) {
        return (Map<String, Object>) response.getBody().data();
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static ArgumentCaptor<Optional<AuthenticatedCatalogViewer>> optionalViewerCaptor() {
        return (ArgumentCaptor) ArgumentCaptor.forClass(Optional.class);
    }
}
