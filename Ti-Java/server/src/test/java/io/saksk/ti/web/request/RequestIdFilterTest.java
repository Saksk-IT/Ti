package io.saksk.ti.web.request;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class RequestIdFilterTest {

    private final RequestIdFilter filter = new RequestIdFilter();

    @Test
    void preservesSafeCallerRequestIdInHeaderAndRequestAttribute() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/test");
        request.addHeader(RequestId.HEADER_NAME, "client-request_01");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getHeader(RequestId.HEADER_NAME)).isEqualTo("client-request_01");
        assertThat(request.getAttribute(RequestId.ATTRIBUTE_NAME)).isEqualTo("client-request_01");
        assertThat(MDC.get(RequestId.MDC_KEY)).isNull();
    }

    @Test
    void replacesUnsafeCallerRequestIdWithoutReflectingControlCharacters() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/test");
        request.addHeader(RequestId.HEADER_NAME, "unsafe value\nforged");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        String generated = response.getHeader(RequestId.HEADER_NAME);
        assertThat(generated)
                .isNotBlank()
                .doesNotContain("unsafe", "\n", "\r", " ");
        assertThat(request.getAttribute(RequestId.ATTRIBUTE_NAME)).isEqualTo(generated);
    }
}
