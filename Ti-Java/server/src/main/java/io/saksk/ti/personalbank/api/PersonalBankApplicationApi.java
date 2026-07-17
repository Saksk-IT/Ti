package io.saksk.ti.personalbank.api;

import java.util.List;
import java.util.Optional;

/** Public HTTP-neutral application boundary for personal-bank use cases. */
public interface PersonalBankApplicationApi {

    List<PersonalBankCategoryView> listCategories(AuthenticatedPersonalBankViewer viewer);

    Optional<PersonalBankShareListView> findShares(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    );

    List<PersonalBankOwnedShareView> listOwnedShares(
            AuthenticatedPersonalBankViewer viewer
    );

    PersonalBankUsageStatsResult findUsageStats(
            AuthenticatedPersonalBankViewer viewer,
            int bankId
    );
}
