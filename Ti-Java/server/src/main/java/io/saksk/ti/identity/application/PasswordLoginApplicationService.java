package io.saksk.ti.identity.application;

import io.saksk.ti.identity.api.AuthenticateCommand;
import io.saksk.ti.identity.api.AuthenticationResult;
import io.saksk.ti.identity.api.IdentityApplicationApi;
import io.saksk.ti.identity.application.port.IdentityCredentialStore;
import io.saksk.ti.identity.application.port.PasswordHashPort;
import io.saksk.ti.identity.domain.IdentityCredential;
import io.saksk.ti.identity.domain.LoginIdentifier;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
class PasswordLoginApplicationService implements IdentityApplicationApi {

    private final IdentityCredentialStore credentials;
    private final PasswordHashPort passwordHashes;

    PasswordLoginApplicationService(
            IdentityCredentialStore credentials,
            PasswordHashPort passwordHashes
    ) {
        this.credentials = credentials;
        this.passwordHashes = passwordHashes;
    }

    @Override
    public AuthenticationResult authenticate(AuthenticateCommand command) {
        char[] password = command.passwordCopy();
        try {
            LoginIdentifier identifier = LoginIdentifier.parse(command.identifier()).orElse(null);
            if (identifier == null) {
                passwordHashes.performDummyVerification(password);
                return AuthenticationResult.invalidCredentials();
            }

            List<IdentityCredential> candidates = credentials.findForAuthentication(identifier);
            if (candidates.size() != 1) {
                passwordHashes.performDummyVerification(password);
                return AuthenticationResult.invalidCredentials();
            }

            IdentityCredential credential = candidates.getFirst();
            if (!passwordHashes.matches(password, credential.passwordHash())) {
                return AuthenticationResult.invalidCredentials();
            }
            return finalizeAgainstCurrentState(credential, password);
        } finally {
            Arrays.fill(password, '\0');
        }
    }

    private AuthenticationResult finalizeAgainstCurrentState(
            IdentityCredential initial,
            char[] password
    ) {
        IdentityCredential current = initial;
        boolean upgraded = false;
        for (int attempt = 0; attempt < 2; attempt++) {
            if (current.locked()) {
                return AuthenticationResult.accountLocked();
            }

            boolean needsUpgrade = !passwordHashes.isTargetHash(current.passwordHash());
            String confirmedHash = current.passwordHash();
            if (needsUpgrade || !current.passwordSet()) {
                confirmedHash = needsUpgrade
                        ? passwordHashes.encodeTarget(password)
                        : current.passwordHash();
                boolean replaced = credentials.replacePasswordHashAndMarkSet(
                        current.id(),
                        current.passwordHash(),
                        current.summary().sessionVersion(),
                        confirmedHash);
                if (!replaced) {
                    Optional<IdentityCredential> refreshed = refreshAndVerify(current.id(), password);
                    if (refreshed.isEmpty()) {
                        return AuthenticationResult.invalidCredentials();
                    }
                    current = refreshed.orElseThrow();
                    continue;
                }
                upgraded |= needsUpgrade;
            }

            Optional<io.saksk.ti.identity.api.IdentitySummary> confirmed =
                    credentials.confirmSuccessfulAuthentication(
                            current.id(),
                            confirmedHash,
                            current.summary().sessionVersion());
            if (confirmed.isPresent()) {
                return AuthenticationResult.authenticated(confirmed.orElseThrow(), upgraded);
            }

            Optional<IdentityCredential> refreshed = refreshAndVerify(current.id(), password);
            if (refreshed.isEmpty()) {
                return AuthenticationResult.invalidCredentials();
            }
            current = refreshed.orElseThrow();
        }
        throw new IllegalStateException("Credential state did not stabilize during authentication");
    }

    private Optional<IdentityCredential> refreshAndVerify(long identityId, char[] password) {
        Optional<IdentityCredential> refreshed = credentials.findByIdForAuthentication(identityId);
        if (refreshed.isEmpty()) {
            return Optional.empty();
        }
        IdentityCredential current = refreshed.orElseThrow();
        if (!passwordHashes.matches(password, current.passwordHash())) {
            return Optional.empty();
        }
        return Optional.of(current);
    }
}
