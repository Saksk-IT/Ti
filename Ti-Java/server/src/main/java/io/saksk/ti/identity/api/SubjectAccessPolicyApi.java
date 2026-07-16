package io.saksk.ti.identity.api;

/** Public identity boundary used by catalog without exposing identity persistence. */
public interface SubjectAccessPolicyApi {

    SubjectAccessDecision subjectAccess(long identityId);
}
