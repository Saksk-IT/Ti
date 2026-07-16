package io.saksk.ti.identity.api;

/** Re-authorizes a server-side session against current PostgreSQL state. */
public interface SessionAuthorityApi {

    SessionAuthorizationResult authorize(long identityId, int sessionVersion);
}
