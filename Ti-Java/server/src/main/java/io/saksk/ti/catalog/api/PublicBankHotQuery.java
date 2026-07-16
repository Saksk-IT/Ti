package io.saksk.ti.catalog.api;

import java.util.Objects;

public record PublicBankHotQuery(PublicBankFilter filter, int limit) {

    public PublicBankHotQuery {
        Objects.requireNonNull(filter, "filter");
        if (limit < 1 || limit > 10) {
            throw new IllegalArgumentException("limit must be between 1 and 10");
        }
    }
}
