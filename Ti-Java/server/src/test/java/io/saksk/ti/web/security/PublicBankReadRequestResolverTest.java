package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

class PublicBankReadRequestResolverTest {

    private final PublicBankReadRequestResolver resolver = new PublicBankReadRequestResolver();

    @Test
    void resolvesOnlyTheSevenPublicBankReadShapes() {
        assertThat(resolve("/api/public/banks"))
                .contains(PublicBankReadRequestResolver.Route.LEGACY_LIST);
        assertThat(resolve("/api/public/banks/boards"))
                .contains(PublicBankReadRequestResolver.Route.BOARDS);
        assertThat(resolve("/api/public/banks/card/system/41"))
                .contains(PublicBankReadRequestResolver.Route.CARD_DETAIL);
        assertThat(resolve("/api/public/banks/hot"))
                .contains(PublicBankReadRequestResolver.Route.HOT);
        assertThat(resolve("/api/public/banks/list"))
                .contains(PublicBankReadRequestResolver.Route.PLAZA_LIST);
        assertThat(resolve("/api/public/banks/summary"))
                .contains(PublicBankReadRequestResolver.Route.SUMMARY);
        assertThat(resolve("/api/public/banks/41"))
                .contains(PublicBankReadRequestResolver.Route.DETAIL);
    }

    @Test
    void canonicalizesUnreservedEncodingAndContextPath() {
        assertThat(resolve("/api/public/%62anks/list"))
                .contains(PublicBankReadRequestResolver.Route.PLAZA_LIST);
        MockHttpServletRequest request = request("GET", "/ti/api/public/banks/%34%31");
        request.setContextPath("/ti");
        assertThat(resolver.resolve(request))
                .contains(PublicBankReadRequestResolver.Route.DETAIL);
        assertThat(resolveRateLimited("/api/public/banks/%D9%A5%D9%A4%D9%A0%D9%A1"))
                .contains(PublicBankReadRequestResolver.Route.DETAIL);
    }

    @Test
    void rejectsReservedMalformedDoubleEncodedAndPendingRoutes() {
        assertThat(resolve("/api/public/banks%2flist")).isEmpty();
        assertThat(resolve("/api/public/banks%3Bv=1")).isEmpty();
        assertThat(resolve("/api/public/%2562anks/list")).isEmpty();
        assertThat(resolve("/api/public/banks/%7x")).isEmpty();
        assertThat(resolve("/api/public/banks/%C0%AF")).isEmpty();
        assertThat(resolve("/api/public/banks/%E2%82")).isEmpty();
        assertThat(resolve("/api/public/banks/joined")).isEmpty();
        assertThat(resolve("/api/public/banks/user/41/join")).isEmpty();
        assertThat(resolver.resolve(request("POST", "/api/public/banks"))).isEmpty();
    }

    @Test
    void rejectsLiteralMatrixParametersOnEveryPublicReadShape() {
        for (String path : java.util.List.of(
                "/api/public/banks;v=1",
                "/api/public/banks/list;v=1",
                "/api/public/banks/41;v=1",
                "/api/public/banks/card;v=1/user/41",
                "/api/public/banks/card/user;v=1/41",
                "/api/public/banks/card/user/41;v=1")) {
            assertThat(resolve(path)).as(path).isEmpty();
        }
    }

    @Test
    void admitsMalformedDetailIdentifiersSoMvcCanReturnLegacyConverter404() {
        assertThat(resolve("/api/public/banks/-1"))
                .contains(PublicBankReadRequestResolver.Route.DETAIL);
        assertThat(resolve("/api/public/banks/card/user/not-a-number"))
                .contains(PublicBankReadRequestResolver.Route.CARD_DETAIL);
    }

    @Test
    void rateLimitedRoutesExcludeConverter404sButKeepArbitraryPrecisionDigitIds() {
        assertThat(resolveRateLimited("/api/public/banks/-1")).isEmpty();
        assertThat(resolveRateLimited("/api/public/banks/card/user/not-a-number")).isEmpty();
        assertThat(resolveRateLimited("/api/public/banks/0"))
                .contains(PublicBankReadRequestResolver.Route.DETAIL);
        assertThat(resolveRateLimited(
                "/api/public/banks/card/user/999999999999999999999999999999999999999"))
                .contains(PublicBankReadRequestResolver.Route.CARD_DETAIL);
        assertThat(resolveRateLimited("/api/public/banks/٥٤٠١"))
                .contains(PublicBankReadRequestResolver.Route.DETAIL);
        assertThat(resolveRateLimited("/api/public/banks/card/system/５３０１"))
                .contains(PublicBankReadRequestResolver.Route.CARD_DETAIL);
        assertThat(resolveRateLimited("/api/public/banks/𝟝𝟜𝟘𝟙"))
                .contains(PublicBankReadRequestResolver.Route.DETAIL);
        assertThat(resolveRateLimited("/api/public/banks/²")).isEmpty();
        assertThat(resolveRateLimited("/api/public/banks/summary"))
                .contains(PublicBankReadRequestResolver.Route.SUMMARY);
    }

    private java.util.Optional<PublicBankReadRequestResolver.Route> resolve(String uri) {
        return resolver.resolve(request("GET", uri));
    }

    private java.util.Optional<PublicBankReadRequestResolver.Route> resolveRateLimited(String uri) {
        return resolver.resolveRateLimitedRoute(request("GET", uri));
    }

    private static MockHttpServletRequest request(String method, String uri) {
        return new MockHttpServletRequest(method, uri);
    }
}
