package io.saksk.ti.catalog.api;

import java.util.Objects;

public record PublicBankRef(PublicBankSource source, long id) {

    public PublicBankRef {
        Objects.requireNonNull(source, "source");
        if (id < 0) {
            throw new IllegalArgumentException("id must be nonnegative");
        }
    }
}
