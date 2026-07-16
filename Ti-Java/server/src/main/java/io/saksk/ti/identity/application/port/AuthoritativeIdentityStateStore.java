package io.saksk.ti.identity.application.port;

import io.saksk.ti.identity.domain.AuthoritativeIdentityState;
import java.util.Optional;

/** PostgreSQL authority lookup used after a legacy credential passes local verification. */
public interface AuthoritativeIdentityStateStore {

    Optional<AuthoritativeIdentityState> findById(long identityId);
}
