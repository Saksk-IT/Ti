package io.saksk.ti.personalbank.application.port;

import io.saksk.ti.personalbank.api.PersonalBankCategoryView;
import java.util.List;

/** Reads the legacy category inventory owned by the personal-bank module. */
public interface PersonalBankCategoryQueryPort {

    List<PersonalBankCategoryView> listCategories(long userId);
}
