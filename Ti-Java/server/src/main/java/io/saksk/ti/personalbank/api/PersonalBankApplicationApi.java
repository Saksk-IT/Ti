package io.saksk.ti.personalbank.api;

import java.util.List;

/** Public HTTP-neutral application boundary for personal-bank use cases. */
public interface PersonalBankApplicationApi {

    List<PersonalBankCategoryView> listCategories(AuthenticatedPersonalBankViewer viewer);
}
