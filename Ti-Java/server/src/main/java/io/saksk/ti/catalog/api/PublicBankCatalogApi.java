package io.saksk.ti.catalog.api;

import java.util.List;
import java.util.Optional;

/** Public application boundary for the catalog-owned public-bank snapshot. */
public interface PublicBankCatalogApi {

    PublicBankPageView search(
            PublicBankSearchQuery query,
            Optional<AuthenticatedCatalogViewer> viewer);

    List<PublicBankBoardView> boards(PublicBankFilter filter);

    List<PublicBankCardView> hot(
            PublicBankHotQuery query,
            Optional<AuthenticatedCatalogViewer> viewer);

    PublicBankSummaryView summary(PublicBankFilter filter);

    Optional<PublicBankDetailView> detail(
            PublicBankRef ref,
            Optional<AuthenticatedCatalogViewer> viewer);
}
