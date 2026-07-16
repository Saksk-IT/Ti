package io.saksk.ti.identity.application;

import io.saksk.ti.identity.api.SubjectAccessDecision;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import io.saksk.ti.identity.application.port.SubjectAccessReadPort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class SubjectAccessPolicyService implements SubjectAccessPolicyApi {

    private final SubjectAccessReadPort subjectAccess;

    SubjectAccessPolicyService(SubjectAccessReadPort subjectAccess) {
        this.subjectAccess = subjectAccess;
    }

    @Override
    @Transactional(readOnly = true)
    public SubjectAccessDecision subjectAccess(long identityId) {
        if (identityId <= 0) {
            return SubjectAccessDecision.missingIdentity();
        }
        return subjectAccess.findByIdentityId(identityId)
                .map(state -> new SubjectAccessDecision(
                        true,
                        state.administrator(),
                        state.restrictedSubjectIds()))
                .orElseGet(SubjectAccessDecision::missingIdentity);
    }
}
