package io.saksk.ti.catalog.api;

import java.util.List;
import java.util.Objects;

public record PublicBankPageView(
        List<PublicBankCardView> items,
        long total,
        int page,
        int pageSize,
        PublicBankSort sort,
        PublicBankFilter filter,
        List<PublicBankSort> availableSorts
) {

    public PublicBankPageView {
        items = List.copyOf(items);
        availableSorts = List.copyOf(availableSorts);
        Objects.requireNonNull(sort, "sort");
        Objects.requireNonNull(filter, "filter");
        if (total < 0 || page < 1 || pageSize < 1) {
            throw new IllegalArgumentException("page metadata must be valid");
        }
    }
}
