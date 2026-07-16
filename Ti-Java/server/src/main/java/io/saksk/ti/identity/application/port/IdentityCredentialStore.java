package io.saksk.ti.identity.application.port;

import io.saksk.ti.identity.domain.IdentityCredential;
import io.saksk.ti.identity.domain.LoginIdentifier;
import java.util.List;
import java.util.Optional;

public interface IdentityCredentialStore {

    List<IdentityCredential> findForAuthentication(LoginIdentifier identifier);

    Optional<IdentityCredential> findByIdForAuthentication(long identityId);

    boolean replacePasswordHashAndMarkSet(
            long identityId,
            String observedHash,
            int observedSessionVersion,
            String targetHash);

    Optional<io.saksk.ti.identity.api.IdentitySummary> confirmSuccessfulAuthentication(
            long identityId,
            String observedHash,
            int observedSessionVersion);
}
