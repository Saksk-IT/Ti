package io.saksk.ti.catalog.api;

import java.util.Objects;

public record PublicBankSearchQuery(
        PublicBankFilter filter,
        PublicBankSort sort,
        int page,
        int pageSize
) {

    public PublicBankSearchQuery {
        Objects.requireNonNull(filter, "filter");
        Objects.requireNonNull(sort, "sort");
        if (page < 1) {
            throw new IllegalArgumentException("page must be positive");
        }
        if (pageSize < 1 || pageSize > 50) {
            throw new IllegalArgumentException("pageSize must be between 1 and 50");
        }
    }

    public long offset() {
        return Math.multiplyExact((long) page - 1, pageSize);
    }
}
