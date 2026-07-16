package io.saksk.ti.catalog.application;

import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.api.CatalogApplicationApi;
import io.saksk.ti.catalog.api.SubjectCatalogView;
import io.saksk.ti.catalog.api.SubjectSummaryView;
import io.saksk.ti.catalog.application.port.SubjectCatalogQueryPort;
import io.saksk.ti.identity.api.SubjectAccessDecision;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import java.util.List;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Service
class SubjectCatalogQueryService implements CatalogApplicationApi {

    private final SubjectCatalogQueryPort subjects;
    private final SubjectAccessPolicyApi subjectAccess;

    SubjectCatalogQueryService(
            SubjectCatalogQueryPort subjects,
            SubjectAccessPolicyApi subjectAccess
    ) {
        this.subjects = subjects;
        this.subjectAccess = subjectAccess;
    }

    @Override
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public SubjectCatalogView subjectCatalog(AuthenticatedCatalogViewer viewer) {
        SubjectAccessDecision access = subjectAccess.subjectAccess(viewer.identityId());
        if (!access.identityExists()) {
            return new SubjectCatalogView(List.of(), 0);
        }

        Set<Integer> restricted = access.administrator()
                ? Set.of()
                : access.restrictedSubjectIds();
        List<SubjectSummaryView> visible = subjects.findUnlockedWithQuestionCounts().stream()
                .filter(subject -> !subject.name().isEmpty())
                .filter(subject -> !restricted.contains(subject.id()))
                .map(subject -> new SubjectSummaryView(
                        subject.id(),
                        subject.name(),
                        subject.questionCount()))
                .toList();
        long quizCount = visible.stream().mapToLong(SubjectSummaryView::questionCount).sum();
        return new SubjectCatalogView(visible, quizCount);
    }
}
