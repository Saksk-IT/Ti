package io.saksk.ti.identity.application.port;

import io.saksk.ti.identity.domain.SubjectAccessState;
import java.util.Optional;

/** Identity-owned read access to users and user_subjects. */
public interface SubjectAccessReadPort {

    Optional<SubjectAccessState> findByIdentityId(long identityId);
}
