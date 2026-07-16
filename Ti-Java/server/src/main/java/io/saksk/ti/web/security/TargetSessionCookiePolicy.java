package io.saksk.ti.web.security;

import jakarta.servlet.http.HttpServletRequest;

public final class TargetSessionCookiePolicy {

    static final String REMEMBER_REQUEST_ATTRIBUTE =
            TargetSessionCookiePolicy.class.getName() + ".remember";

    private TargetSessionCookiePolicy() {
    }

    public static void rememberForSevenDays(HttpServletRequest request) {
        request.setAttribute(REMEMBER_REQUEST_ATTRIBUTE, Boolean.TRUE);
    }
}
