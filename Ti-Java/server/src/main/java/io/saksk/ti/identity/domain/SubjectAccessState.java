package io.saksk.ti.identity.domain;

import java.util.Objects;
import java.util.Set;

/** Current identity-owned administrator flag and subject blacklist. */
public record SubjectAccessState(boolean administrator, Set<Integer> restrictedSubjectIds) {

    public SubjectAccessState {
        restrictedSubjectIds = Set.copyOf(Objects.requireNonNull(
                restrictedSubjectIds, "restrictedSubjectIds"));
        if (restrictedSubjectIds.stream().anyMatch(id -> id == null || id <= 0)) {
            throw new IllegalArgumentException("restricted subject IDs must be positive");
        }
    }
}
