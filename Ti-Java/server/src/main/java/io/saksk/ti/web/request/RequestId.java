package io.saksk.ti.web.request;

import jakarta.servlet.http.HttpServletRequest;

public final class RequestId {

    public static final String HEADER_NAME = "X-Request-ID";
    public static final String ATTRIBUTE_NAME = RequestId.class.getName();
    public static final String MDC_KEY = "request_id";

    private RequestId() {
    }

    public static String from(HttpServletRequest request) {
        Object requestId = request.getAttribute(ATTRIBUTE_NAME);
        return requestId instanceof String value ? value : "unavailable";
    }
}
