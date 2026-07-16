package io.saksk.ti.identity.application;

import io.saksk.ti.identity.api.IdentitySummary;
import io.saksk.ti.identity.api.SessionAuthorityApi;
import io.saksk.ti.identity.api.SessionAuthorizationResult;
import io.saksk.ti.identity.application.port.AuthoritativeIdentityStateStore;
import io.saksk.ti.identity.domain.AuthorizedLegacyIdentity;
import org.springframework.stereotype.Service;

@Service
class SessionAuthorityApplicationService implements SessionAuthorityApi {

    private final AuthoritativeIdentityStateStore identities;

    SessionAuthorityApplicationService(AuthoritativeIdentityStateStore identities) {
        this.identities = identities;
    }

    @Override
    public SessionAuthorizationResult authorize(long identityId, int sessionVersion) {
        if (identityId <= 0 || sessionVersion < 0) {
            return SessionAuthorizationResult.rejected();
        }
        try {
            return identities.findById(identityId)
                    .filter(state -> state.id() == identityId)
                    .filter(state -> !state.locked())
                    .filter(state -> state.sessionVersion() == sessionVersion)
                    .map(state -> SessionAuthorizationResult.authorized(
                            toSummary(state.authorize())))
                    .orElseGet(SessionAuthorizationResult::rejected);
        } catch (RuntimeException exception) {
            return SessionAuthorizationResult.unavailable();
        }
    }

    private static IdentitySummary toSummary(AuthorizedLegacyIdentity identity) {
        return new IdentitySummary(
                identity.id(),
                identity.username(),
                identity.administrator(),
                identity.subjectAdministrator(),
                identity.notificationAdministrator(),
                identity.sessionVersion());
    }
}
