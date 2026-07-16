package io.saksk.ti.identity.api;

import java.util.Objects;
import java.util.Set;

/** Identity-owned subject visibility facts for one currently authenticated identity. */
public record SubjectAccessDecision(
        boolean identityExists,
        boolean administrator,
        Set<Integer> restrictedSubjectIds
) {

    public SubjectAccessDecision {
        restrictedSubjectIds = Set.copyOf(Objects.requireNonNull(
                restrictedSubjectIds, "restrictedSubjectIds"));
        if (!identityExists && (administrator || !restrictedSubjectIds.isEmpty())) {
            throw new IllegalArgumentException("missing identity cannot carry subject access facts");
        }
        if (restrictedSubjectIds.stream().anyMatch(id -> id == null || id <= 0)) {
            throw new IllegalArgumentException("restricted subject IDs must be positive");
        }
    }

    public static SubjectAccessDecision missingIdentity() {
        return new SubjectAccessDecision(false, false, Set.of());
    }
}
