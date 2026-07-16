package io.saksk.ti.web.security;

/** Removes login-request CSRF authority from a newly issued target Session. */
interface TargetSessionCsrfRevoker {

    void revoke(String sessionId);
}
