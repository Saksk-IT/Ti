package io.saksk.ti.catalog.application;

import static org.assertj.core.api.Assertions.assertThat;

import io.saksk.ti.catalog.api.AuthenticatedCatalogViewer;
import io.saksk.ti.catalog.application.port.SubjectCatalogQueryPort;
import io.saksk.ti.catalog.domain.SubjectCatalogEntry;
import io.saksk.ti.identity.api.SubjectAccessDecision;
import io.saksk.ti.identity.api.SubjectAccessPolicyApi;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SubjectCatalogQueryServiceTest {

    private static final List<SubjectCatalogEntry> CATALOG = List.of(
            new SubjectCatalogEntry(1, "算法", 2),
            new SubjectCatalogEntry(2, "数据库", 0),
            new SubjectCatalogEntry(3, "受限", 4),
            new SubjectCatalogEntry(4, "  ", 99),
            new SubjectCatalogEntry(5, "", 100));

    @Test
    void ordinaryViewerPreservesWhitespaceButOmitsEmptyNamesAndAppliesIdentityBlacklist() {
        int[] catalogCalls = {0};
        SubjectCatalogQueryPort port = () -> {
            catalogCalls[0]++;
            return CATALOG;
        };
        SubjectAccessPolicyApi access = identityId ->
                new SubjectAccessDecision(true, false, Set.of(3));
        var service = new SubjectCatalogQueryService(port, access);

        var result = service.subjectCatalog(new AuthenticatedCatalogViewer(41));

        assertThat(result.subjects())
                .extracting(view -> view.id() + ":" + view.name() + ":" + view.questionCount())
                .containsExactly("1:算法:2", "2:数据库:0", "4:  :99");
        assertThat(result.quizCount()).isEqualTo(101);
        assertThat(catalogCalls[0]).isOne();
    }

    @Test
    void administratorBypassesBlacklistButNotTheEmptyNameCompatibilityFilter() {
        SubjectAccessPolicyApi access = identityId ->
                new SubjectAccessDecision(true, true, Set.of(1, 2, 3));
        var service = new SubjectCatalogQueryService(() -> CATALOG, access);

        var result = service.subjectCatalog(new AuthenticatedCatalogViewer(42));

        assertThat(result.subjects()).extracting(view -> view.id())
                .containsExactly(1, 2, 3, 4);
        assertThat(result.quizCount()).isEqualTo(105);
    }

    @Test
    void identityDeletedBetweenAuthenticationAndQueryGetsNoCatalogData() {
        int[] catalogCalls = {0};
        SubjectCatalogQueryPort port = () -> {
            catalogCalls[0]++;
            return CATALOG;
        };
        SubjectAccessPolicyApi access = identityId -> SubjectAccessDecision.missingIdentity();
        var service = new SubjectCatalogQueryService(port, access);

        var result = service.subjectCatalog(new AuthenticatedCatalogViewer(404));

        assertThat(result.subjects()).isEmpty();
        assertThat(result.quizCount()).isZero();
        assertThat(catalogCalls[0]).isZero();
    }
}
