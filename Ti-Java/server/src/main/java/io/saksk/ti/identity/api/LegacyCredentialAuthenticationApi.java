package io.saksk.ti.identity.api;

import java.util.Optional;

/** Temporary, kill-switched transition boundary for locally verified legacy credentials. */
public interface LegacyCredentialAuthenticationApi {

    Optional<LegacyAuthenticationResult> authenticateJwt(String token);

    Optional<LegacyAuthenticationResult> authenticateFlaskSession(String cookie);
}
