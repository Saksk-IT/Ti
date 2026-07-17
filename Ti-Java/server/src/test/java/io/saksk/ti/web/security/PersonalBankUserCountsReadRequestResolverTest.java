package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.BankIdKind;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.CandidateKind;
import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Resolution;
import java.net.URI;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

class PersonalBankUserCountsReadRequestResolverTest {

    private final PersonalBankUserCountsReadRequestResolver resolver =
            new PersonalBankUserCountsReadRequestResolver();

    @Test
    void resolvesBothAliasesGetAndHeadWithCanonicalIntegerBoundaries() {
        assertResolution(
                "GET",
                "/api/user/banks/api/00099551/user-counts",
                Alias.API,
                BankIdKind.POSITIVE_INT,
                "99551",
                99_551);
        assertResolution(
                "HEAD",
                "/user/banks/api/2147483647/user-counts",
                Alias.WEB,
                BankIdKind.POSITIVE_INT,
                "2147483647",
                Integer.MAX_VALUE);
        assertResolution(
                "GET",
                "/api/user/banks/api/000/user-counts",
                Alias.API,
                BankIdKind.ZERO,
                "0",
                0);
        for (String value : List.of(
                "2147483648",
                "9223372036854775808",
                "999999999999999999999999999999999999999999999999999999")) {
            assertResolution(
                    "GET",
                    "/api/user/banks/api/" + value + "/user-counts",
                    Alias.API,
                    BankIdKind.OVERFLOW,
                    value,
                    0);
        }
    }

    @Test
    void strictlyDecodesAsciiAndUtf8UnicodeNdExactlyOnce() {
        assertResolution(
                "GET",
                "/api/user/banks/api/%39%39%35%35%31/user-counts",
                Alias.API,
                BankIdKind.POSITIVE_INT,
                "99551",
                99_551);
        for (String digits : List.of("٩٩٥٥١", "９９５５１", "𝟡９٥5١")) {
            String path = "/user/banks/api/" + digits + "/user-counts";
            assertResolution(
                    "GET",
                    URI.create(path).toASCIIString(),
                    Alias.WEB,
                    BankIdKind.POSITIVE_INT,
                    "99551",
                    99_551);
        }

        assertThat(resolve("GET", "/api/user/banks/api/%2539/user-counts")).isEmpty();
        assertThat(resolve("GET", "/api/user/banks/api/%C0%AF/user-counts")).isEmpty();
        assertThat(resolve("GET", "/api/user/banks/api/%E2%82/user-counts")).isEmpty();
        assertThat(resolve("GET", "/api/user/banks/api/%2F99551/user-counts")).isEmpty();
        assertThat(resolve("GET", "/api/user/banks/api/%3B99551/user-counts")).isEmpty();
    }

    @Test
    void converterMissesReachTheCompatibility404ButNeverConsumeRouteBudget() {
        for (String segment : List.of("-1", "+1", "1.0", "not-a-bank", "²", "Ⅳ")) {
            MockHttpServletRequest request = request(
                    "GET",
                    "/api/user/banks/api/" + segment + "/user-counts");
            assertThat(resolver.resolveRead(request))
                    .get()
                    .extracting(
                            PersonalBankUserCountsReadRequestResolver.Resolution::alias,
                            PersonalBankUserCountsReadRequestResolver.Resolution::bankIdKind)
                    .containsExactly(Alias.API, BankIdKind.CONVERTER_MISS);
            assertThat(resolver.resolveRateLimitedRoute(request)).isEmpty();
        }
    }

    @Test
    void optionsAreConverterValidOnlyAndNeverClassifiedAsRateLimitedReads() {
        for (String segment : List.of("0", "41", "2147483648")) {
            MockHttpServletRequest request = request(
                    "OPTIONS",
                    "/api/user/banks/api/" + segment + "/user-counts");
            assertThat(resolver.resolveBareOptions(request)).isPresent();
            assertThat(resolver.resolveRead(request)).isEmpty();
            assertThat(resolver.resolveRateLimitedRoute(request)).isEmpty();
        }
        MockHttpServletRequest converterMiss = request(
                "OPTIONS",
                "/api/user/banks/api/not-a-bank/user-counts");
        assertThat(resolver.resolveOptions(converterMiss))
                .get()
                .extracting(Resolution::bankIdKind)
                .isEqualTo(BankIdKind.CONVERTER_MISS);
        assertThat(resolver.resolveBareOptions(converterMiss)).isEmpty();
    }

    @Test
    void identifiesOnlyNarrowUserCountsNearMissesAndContextPaths() {
        for (String path : List.of(
                "/api/user/banks/api/user-counts",
                "/api/user/banks/api/41/user-counts/",
                "/api/user/banks/api/41/user-counts/extra",
                "/user/banks/api/extra/41/user-counts")) {
            assertThat(resolver.resolveCandidate(request("GET", path)))
                    .get()
                    .extracting(PersonalBankUserCountsReadRequestResolver.RouteCandidate::kind)
                    .isEqualTo(CandidateKind.NEAR_MISS);
        }
        assertThat(resolver.resolveCandidate(request(
                "GET", "/api/user/banks/api/41/user-counts")))
                .get()
                .extracting(PersonalBankUserCountsReadRequestResolver.RouteCandidate::kind)
                .isEqualTo(CandidateKind.EXACT);
        assertThat(resolver.resolveCandidate(request(
                "GET", "/api/user/banks/api/41/questions"))).isEmpty();
        assertThat(resolver.resolveCandidate(request(
                "POST", "/api/user/banks/api/41/user-counts"))).isEmpty();

        MockHttpServletRequest context = request(
                "GET", "/ti/api/user/banks/api/%34%31/user-counts");
        context.setContextPath("/ti");
        assertThat(resolver.resolveRead(context))
                .get()
                .extracting(
                        PersonalBankUserCountsReadRequestResolver.Resolution::alias,
                        PersonalBankUserCountsReadRequestResolver.Resolution::bankId)
                .containsExactly(Alias.API, 41);
    }

    @Test
    void leavesLiteralMatrixAndReservedEscapesToTheStrictFirewall() {
        for (String path : List.of(
                "/api/user/banks/api/41;role=owner/user-counts",
                "/api/user/banks/api/41/user-counts;v=1",
                "/api/user/banks/api/41%2fowner/user-counts",
                "/api/user/banks/api/41%3bowner/user-counts")) {
            MockHttpServletRequest request = request("GET", path);
            assertThat(resolver.resolveRead(request)).isEmpty();
            assertThat(resolver.resolveCandidate(request)).isEmpty();
        }
    }

    private void assertResolution(
            String method,
            String path,
            Alias alias,
            BankIdKind kind,
            String normalized,
            int bankId
    ) {
        assertThat(resolve(method, path))
                .contains(new PersonalBankUserCountsReadRequestResolver.Resolution(
                        alias,
                        kind,
                        normalized,
                        bankId));
    }

    private java.util.Optional<PersonalBankUserCountsReadRequestResolver.Resolution> resolve(
            String method,
            String path
    ) {
        return resolver.resolveRead(request(method, path));
    }

    private static MockHttpServletRequest request(String method, String path) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, path);
        request.setRequestURI(path);
        request.setServletPath(path);
        return request;
    }
}
