package io.saksk.ti.web.security;

import io.saksk.ti.web.error.ErrorCode;
import io.saksk.ti.web.error.SafeSecurityErrorWriter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ReadListener;
import jakarta.servlet.ServletInputStream;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import jakarta.servlet.http.HttpServletResponse;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Set;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.web.filter.OncePerRequestFilter;

public final class CsrfIssuanceRateLimitFilter extends OncePerRequestFilter {

    private static final String CSRF_PATH = "/api/csrf";
    private static final String LOGIN_PATH = "/api/login";
    private static final Set<String> CSRF_SAFE_METHODS = Set.of("GET", "HEAD", "TRACE", "OPTIONS");
    static final int MAXIMUM_LOGIN_BODY_BYTES = 16 * 1_024;

    private final CsrfIssuanceRateLimiter rateLimiter;
    private final ClientAddressResolver clientAddresses;
    private final SafeSecurityErrorWriter errorWriter;

    public CsrfIssuanceRateLimitFilter(
            CsrfIssuanceRateLimiter rateLimiter,
            ClientAddressResolver clientAddresses,
            SafeSecurityErrorWriter errorWriter
    ) {
        this.rateLimiter = rateLimiter;
        this.clientAddresses = clientAddresses;
        this.errorWriter = errorWriter;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = applicationPath(request);
        boolean obtainsToken = (HttpMethod.GET.matches(request.getMethod())
                        || HttpMethod.HEAD.matches(request.getMethod()))
                && CSRF_PATH.equals(path);
        boolean unsafeMethod = !CSRF_SAFE_METHODS.contains(request.getMethod());
        return !obtainsToken && !unsafeMethod;
    }

    private static String applicationPath(HttpServletRequest request) {
        String path = request.getRequestURI();
        String contextPath = request.getContextPath();
        return !contextPath.isEmpty() && path.startsWith(contextPath)
                ? path.substring(contextPath.length())
                : path;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        if (request.getSession(false) == null) {
            CsrfIssuanceRateLimiter.Decision decision;
            try {
                decision = rateLimiter.acquire(clientAddresses.resolve(request));
            } catch (RuntimeException exception) {
                errorWriter.write(request, response, ErrorCode.SERVICE_UNAVAILABLE);
                return;
            }
            if (!decision.allowed()) {
                response.setHeader(HttpHeaders.RETRY_AFTER, Long.toString(decision.retryAfterSeconds()));
                response.setHeader("X-RateLimit-Limit", Integer.toString(decision.limit()));
                response.setHeader("X-RateLimit-Remaining", Integer.toString(decision.remaining()));
                errorWriter.write(request, response, ErrorCode.RATE_LIMITED);
                return;
            }
        }
        if (!HttpMethod.POST.matches(request.getMethod())
                || !LOGIN_PATH.equals(applicationPath(request))) {
            filterChain.doFilter(request, response);
            return;
        }
        if (request.getContentLengthLong() > MAXIMUM_LOGIN_BODY_BYTES) {
            errorWriter.write(request, response, ErrorCode.PAYLOAD_TOO_LARGE);
            return;
        }

        BoundedBody body = readBody(request);
        if (body == null) {
            errorWriter.write(request, response, ErrorCode.PAYLOAD_TOO_LARGE);
            return;
        }
        try {
            filterChain.doFilter(new CachedBodyRequest(request, body), response);
        } finally {
            Arrays.fill(body.bytes(), (byte) 0);
        }
    }

    private static BoundedBody readBody(HttpServletRequest request) throws IOException {
        byte[] bytes = new byte[MAXIMUM_LOGIN_BODY_BYTES + 1];
        int length = 0;
        try {
            while (length < bytes.length) {
                int read = request.getInputStream().read(bytes, length, bytes.length - length);
                if (read < 0) {
                    return new BoundedBody(bytes, length);
                }
                if (read == 0) {
                    continue;
                }
                length += read;
            }
            Arrays.fill(bytes, (byte) 0);
            return null;
        } catch (IOException exception) {
            Arrays.fill(bytes, (byte) 0);
            throw exception;
        }
    }

    private record BoundedBody(byte[] bytes, int length) {
    }

    private static final class CachedBodyRequest extends HttpServletRequestWrapper {
        private final BoundedBody body;

        private CachedBodyRequest(HttpServletRequest request, BoundedBody body) {
            super(request);
            this.body = body;
        }

        @Override
        public int getContentLength() {
            return body.length();
        }

        @Override
        public long getContentLengthLong() {
            return body.length();
        }

        @Override
        public ServletInputStream getInputStream() {
            ByteArrayInputStream input = new ByteArrayInputStream(
                    body.bytes(),
                    0,
                    body.length());
            return new ServletInputStream() {
                @Override
                public boolean isFinished() {
                    return input.available() == 0;
                }

                @Override
                public boolean isReady() {
                    return true;
                }

                @Override
                public void setReadListener(ReadListener readListener) {
                    throw new UnsupportedOperationException("Asynchronous reads are not supported");
                }

                @Override
                public int read() {
                    return input.read();
                }

                @Override
                public int read(byte[] target, int offset, int length) {
                    return input.read(target, offset, length);
                }

                @Override
                public int available() {
                    return input.available();
                }
            };
        }

        @Override
        public BufferedReader getReader() {
            return new BufferedReader(new InputStreamReader(
                    getInputStream(),
                    StandardCharsets.UTF_8));
        }
    }
}
