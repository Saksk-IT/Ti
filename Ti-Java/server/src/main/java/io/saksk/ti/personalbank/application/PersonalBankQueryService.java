package io.saksk.ti.personalbank.application;

import io.saksk.ti.personalbank.api.AuthenticatedPersonalBankViewer;
import io.saksk.ti.personalbank.api.PersonalBankApplicationApi;
import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import io.saksk.ti.personalbank.application.port.PersonalBankCategoryQueryPort;
import java.util.List;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
class PersonalBankQueryService implements PersonalBankApplicationApi {

    private final PersonalBankCategoryQueryPort categories;

    PersonalBankQueryService(PersonalBankCategoryQueryPort categories) {
        this.categories = categories;
    }

    @Override
    @Transactional(readOnly = true)
    public List<PersonalBankCategoryView> listCategories(
            AuthenticatedPersonalBankViewer viewer
    ) {
        Objects.requireNonNull(viewer, "viewer");
        return List.copyOf(categories.listCategories(viewer.identityId()));
    }
}
