package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

class SubjectReadRequestResolverTest {

    private final SubjectReadRequestResolver resolver = new SubjectReadRequestResolver();

    @Test
    void resolvesPlainAndEncodedUnreservedPathsThroughOneCanonicalRepresentation() {
        var plain = request("GET", "/api/quiz/subjects");
        var encodedList = request("GET", "/api/quiz/%73ubjects");
        var encodedMeta = request("GET", "/api/quiz/subjects/%6deta");
        var contextPath = request("GET", "/ti/api/quiz/%73ubjects");
        contextPath.setContextPath("/ti");

        assertThat(resolver.resolve(plain))
                .contains(SubjectReadRateLimiter.Route.SUBJECTS);
        assertThat(resolver.resolve(encodedList))
                .contains(SubjectReadRateLimiter.Route.SUBJECTS);
        assertThat(resolver.resolve(encodedMeta))
                .contains(SubjectReadRateLimiter.Route.SUBJECTS_META);
        assertThat(resolver.resolve(contextPath))
                .contains(SubjectReadRateLimiter.Route.SUBJECTS);
    }

    @Test
    void rejectsMalformedReservedDoubleEncodedAndNonGetAmbiguities() {
        assertThat(resolver.resolve(request("GET", "/api/quiz/subjects%2fmeta"))).isEmpty();
        assertThat(resolver.resolve(request("GET", "/api/quiz/%2573ubjects"))).isEmpty();
        assertThat(resolver.resolve(request("GET", "/api/quiz/%7subjects"))).isEmpty();
        assertThat(resolver.resolve(request("POST", "/api/quiz/%73ubjects"))).isEmpty();
    }

    private static MockHttpServletRequest request(String method, String uri) {
        return new MockHttpServletRequest(method, uri);
    }
}
