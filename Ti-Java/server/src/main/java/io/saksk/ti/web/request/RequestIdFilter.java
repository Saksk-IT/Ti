package io.saksk.ti.web.request;

import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestIdFilter extends OncePerRequestFilter {

    private static final int MAX_REQUEST_ID_LENGTH = 128;
    private static final Pattern SAFE_REQUEST_ID = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]*");

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String requestId = resolveRequestId(request.getHeader(RequestId.HEADER_NAME));
        String previousMdcValue = MDC.get(RequestId.MDC_KEY);

        request.setAttribute(RequestId.ATTRIBUTE_NAME, requestId);
        response.setHeader(RequestId.HEADER_NAME, requestId);
        MDC.put(RequestId.MDC_KEY, requestId);

        try {
            filterChain.doFilter(request, response);
        } finally {
            restoreMdc(previousMdcValue);
        }
    }

    private String resolveRequestId(String candidate) {
        if (candidate != null) {
            String normalized = candidate.trim();
            if (normalized.length() <= MAX_REQUEST_ID_LENGTH
                    && SAFE_REQUEST_ID.matcher(normalized).matches()) {
                return normalized;
            }
        }
        return UUID.randomUUID().toString();
    }

    private void restoreMdc(String previousValue) {
        if (previousValue == null) {
            MDC.remove(RequestId.MDC_KEY);
        } else {
            MDC.put(RequestId.MDC_KEY, previousValue);
        }
    }
}
