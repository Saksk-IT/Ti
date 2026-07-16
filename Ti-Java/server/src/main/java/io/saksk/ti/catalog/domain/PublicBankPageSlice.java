package io.saksk.ti.catalog.domain;

import io.saksk.ti.catalog.api.PublicBankCardView;
import java.util.List;

public record PublicBankPageSlice(List<PublicBankCardView> items, long total) {

    public PublicBankPageSlice {
        items = List.copyOf(items);
        if (total < 0) {
            throw new IllegalArgumentException("total must be nonnegative");
        }
    }
}
