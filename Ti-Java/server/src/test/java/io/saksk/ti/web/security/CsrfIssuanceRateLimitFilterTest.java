package io.saksk.ti.web.security;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import io.saksk.ti.web.error.ErrorCode;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class CsrfIssuanceRateLimitFilterTest {

    private CsrfIssuanceRateLimiter limiter;
    private ClientAddressResolver addresses;
    private SafeSecurityErrorWriter errors;
    private CsrfIssuanceRateLimitFilter filter;

    @BeforeEach
    void setUp() {
        limiter = mock(CsrfIssuanceRateLimiter.class);
        addresses = mock(ClientAddressResolver.class);
        errors = mock(SafeSecurityErrorWriter.class);
        filter = new CsrfIssuanceRateLimitFilter(limiter, addresses, errors);
    }

    @Test
    void limitsTokenGetBeforeTheSecurityChainCanCreateASession() throws Exception {
        MockHttpServletRequest request = request("GET", "/api/csrf");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        when(addresses.resolve(request)).thenReturn("203.0.113.7");
        when(limiter.acquire("203.0.113.7"))
                .thenReturn(new CsrfIssuanceRateLimiter.Decision(false, 30, 0, 27));

        filter.doFilter(request, response, chain);

        verify(chain, never()).doFilter(request, response);
        verify(errors).write(request, response, ErrorCode.RATE_LIMITED);
        org.assertj.core.api.Assertions.assertThat(response.getHeader("Retry-After")).isEqualTo("27");
    }

    @Test
    void alsoLimitsTokenlessLoginPostsBeforeCsrfMaterialization() throws Exception {
        MockHttpServletRequest request = request("POST", "/api/login");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        when(addresses.resolve(request)).thenReturn("198.51.100.4");
        when(limiter.acquire("198.51.100.4"))
                .thenReturn(new CsrfIssuanceRateLimiter.Decision(true, 30, 29, 60));

        filter.doFilter(request, response, chain);

        verify(chain).doFilter(
                org.mockito.ArgumentMatchers.any(HttpServletRequest.class),
                org.mockito.ArgumentMatchers.eq(response));
    }

    @Test
    void headTokenRequestsCannotBypassTheGetBudget() throws Exception {
        MockHttpServletRequest request = request("HEAD", "/api/csrf");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        when(addresses.resolve(request)).thenReturn("198.51.100.5");
        when(limiter.acquire("198.51.100.5"))
                .thenReturn(new CsrfIssuanceRateLimiter.Decision(false, 30, 0, 60));

        filter.doFilter(request, response, chain);

        verify(errors).write(request, response, ErrorCode.RATE_LIMITED);
        verify(chain, never()).doFilter(request, response);
    }

    @Test
    void RedisFailureFailsClosedAndUnrelatedRoutesDoNotConsumeTheBudget() throws Exception {
        MockHttpServletRequest request = request("GET", "/api/csrf");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        when(addresses.resolve(request)).thenReturn("127.0.0.1");
        when(limiter.acquire("127.0.0.1")).thenThrow(new IllegalStateException("down"));

        filter.doFilter(request, response, chain);

        verify(errors).write(request, response, ErrorCode.SERVICE_UNAVAILABLE);
        verify(chain, never()).doFilter(request, response);

        MockHttpServletRequest unrelated = request("GET", "/api/auth/login-methods");
        FilterChain unrelatedChain = mock(FilterChain.class);
        org.mockito.Mockito.reset(limiter);
        filter.doFilter(unrelated, new MockHttpServletResponse(), unrelatedChain);
        verify(unrelatedChain).doFilter(
                org.mockito.ArgumentMatchers.eq(unrelated),
                org.mockito.ArgumentMatchers.any());
        org.mockito.Mockito.verifyNoInteractions(limiter);
    }

    @Test
    void rejectsDeclaredAndActuallyOversizedLoginBodiesBeforeJsonParsing() throws Exception {
        MockHttpServletRequest declared = request("POST", "/api/login");
        declared.setContent(new byte[CsrfIssuanceRateLimitFilter.MAXIMUM_LOGIN_BODY_BYTES + 1]);
        when(addresses.resolve(declared)).thenReturn("198.51.100.8");
        when(limiter.acquire("198.51.100.8"))
                .thenReturn(new CsrfIssuanceRateLimiter.Decision(true, 30, 29, 60));
        FilterChain declaredChain = mock(FilterChain.class);

        filter.doFilter(declared, new MockHttpServletResponse(), declaredChain);

        verify(declaredChain, never()).doFilter(
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
        verify(errors).write(
                org.mockito.ArgumentMatchers.eq(declared),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.eq(ErrorCode.PAYLOAD_TOO_LARGE));

        MockHttpServletRequest chunked = new MockHttpServletRequest("POST", "/api/login") {
            @Override
            public int getContentLength() {
                return -1;
            }

            @Override
            public long getContentLengthLong() {
                return -1;
            }
        };
        chunked.setServletPath("/api/login");
        chunked.setContent(new byte[CsrfIssuanceRateLimitFilter.MAXIMUM_LOGIN_BODY_BYTES + 1]);
        when(addresses.resolve(chunked)).thenReturn("198.51.100.9");
        when(limiter.acquire("198.51.100.9"))
                .thenReturn(new CsrfIssuanceRateLimiter.Decision(true, 30, 29, 60));
        FilterChain chunkedChain = mock(FilterChain.class);

        filter.doFilter(chunked, new MockHttpServletResponse(), chunkedChain);

        verify(chunkedChain, never()).doFilter(
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.any());
        verify(errors).write(
                org.mockito.ArgumentMatchers.eq(chunked),
                org.mockito.ArgumentMatchers.any(),
                org.mockito.ArgumentMatchers.eq(ErrorCode.PAYLOAD_TOO_LARGE));
    }

    @Test
    void acceptsTheExactBodyBoundaryAndReplaysItOnceToDownstreamJson() throws Exception {
        MockHttpServletRequest request = request("POST", "/api/login");
        byte[] content = new byte[CsrfIssuanceRateLimitFilter.MAXIMUM_LOGIN_BODY_BYTES];
        java.util.Arrays.fill(content, (byte) 'x');
        request.setContent(content);
        when(addresses.resolve(request)).thenReturn("198.51.100.10");
        when(limiter.acquire("198.51.100.10"))
                .thenReturn(new CsrfIssuanceRateLimiter.Decision(true, 30, 29, 60));
        AtomicInteger observedLength = new AtomicInteger();

        filter.doFilter(request, new MockHttpServletResponse(), (downstream, response) ->
                observedLength.set(downstream.getInputStream().readAllBytes().length));

        org.assertj.core.api.Assertions.assertThat(observedLength.get())
                .isEqualTo(CsrfIssuanceRateLimitFilter.MAXIMUM_LOGIN_BODY_BYTES);
    }

    private static MockHttpServletRequest request(String method, String path) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, path);
        request.setServletPath(path);
        return request;
    }
}
