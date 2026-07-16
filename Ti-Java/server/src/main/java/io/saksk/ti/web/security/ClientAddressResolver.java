package io.saksk.ti.web.security;

import jakarta.servlet.http.HttpServletRequest;

/** Resolves the rate-limit subject without trusting caller-controlled forwarding headers. */
public interface ClientAddressResolver {

    String resolve(HttpServletRequest request);
}
