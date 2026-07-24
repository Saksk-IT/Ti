package io.saksk.ti.web.security;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.web.security.TransactionWriteRequestResolver.Route;
import java.net.URI;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

class TransactionWriteRequestResolverTest {

    private final TransactionWriteRequestResolver resolver =
            new TransactionWriteRequestResolver();

    @Test
    void resolvesExactlyTheNineAuthorizedMethodAndPathPairs() {
        Map<String, Route> routes = Map.of(
                "POST /api/favorite", Route.FAVORITE_WEB,
                "POST /api/quiz/favorite", Route.FAVORITE_API,
                "POST /api/record_result", Route.RECORD_RESULT_WEB,
                "POST /api/quiz/record_result", Route.RECORD_RESULT_API,
                "POST /api/quiz/study/learn/record", Route.STUDY_LEARN,
                "POST /api/quiz/study/review/record", Route.STUDY_REVIEW,
                "POST /api/quiz/study/review/master", Route.STUDY_MASTER,
                "POST /api/user/checkin", Route.CHECKIN,
                "PUT /api/quiz/questions/93001", Route.QUESTION_EDIT);

        routes.forEach((wire, expected) -> {
            String[] parts = wire.split(" ", 2);
            assertThat(resolver.resolve(request(parts[0], parts[1])))
                    .get()
                    .extracting(TransactionWriteRequestResolver.Resolution::route)
                    .isEqualTo(expected);
        });
        assertThat(resolver.resolve(request("GET", "/api/favorite"))).isEmpty();
        assertThat(resolver.resolve(request(
                "POST", "/api/quiz/study/review/master/extra"))).isEmpty();
        assertThat(resolver.resolve(request(
                "PUT", "/api/quiz/questions/-1"))).isEmpty();
    }

    @Test
    void questionEditNormalizesUnicodeNdAndRejectsReservedOrMatrixPaths() {
        String unicode = URI.create("/api/quiz/questions/９٣0٠1").toASCIIString();
        assertThat(resolver.resolve(request("PUT", unicode)))
                .get()
                .extracting(
                        TransactionWriteRequestResolver.Resolution::route,
                        resolution -> resolution.normalizedQuestionId().orElseThrow())
                .containsExactly(Route.QUESTION_EDIT, "93001");

        for (String path : new String[]{
                "/api/quiz/questions/%2F93001",
                "/api/quiz/questions/93001;v=1",
                "/api/quiz/questions/93001/extra"}) {
            assertThat(resolver.resolve(request("PUT", path))).isEmpty();
        }
    }

    @Test
    void pathOnlyResolutionSupportsExactOptionsWithoutAuthorizingWrongMethods() {
        MockHttpServletRequest preflight =
                request("OPTIONS", "/api/quiz/study/review/master");
        assertThat(resolver.resolve(preflight)).isEmpty();
        assertThat(resolver.resolvePath(preflight))
                .get()
                .extracting(TransactionWriteRequestResolver.Resolution::route)
                .isEqualTo(Route.STUDY_MASTER);
    }

    private static MockHttpServletRequest request(String method, String path) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, path);
        request.setRequestURI(path);
        request.setServletPath(path);
        return request;
    }
}
