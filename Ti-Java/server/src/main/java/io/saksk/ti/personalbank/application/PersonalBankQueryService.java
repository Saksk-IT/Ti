package io.saksk.ti.personalbank.application;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.api.PersonalBankShareListView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import io.saksk.ti.personalbank.application.port.PersonalBankShareQueryPort;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class PersonalBankQueryService implements PersonalBankApplicationApi {

    private final PersonalBankCategoryQueryPort categories;
    private final PersonalBankShareQueryPort shares;

    PersonalBankQueryService(
            PersonalBankCategoryQueryPort categories,
            PersonalBankShareQueryPort shares
    ) {
        this.categories = categories;
        this.shares = shares;
    }

    @Override
    @Transactional(readOnly = true)
    public List<PersonalBankCategoryView> listCategories(
            AuthenticatedPersonalBankViewer viewer
    ) {
        Objects.requireNonNull(viewer, "viewer");
        return List.copyOf(categories.listCategories(viewer.identityId()));
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<PersonalBankShareListView> findShares(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    ) {
        Objects.requireNonNull(viewer, "viewer");
        return shares.findShares(viewer.identityId(), bankId)
                .map(PersonalBankShareListView::new);
    }
}
