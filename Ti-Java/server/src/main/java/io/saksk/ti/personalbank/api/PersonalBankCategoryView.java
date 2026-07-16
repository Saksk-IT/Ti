package io.saksk.ti.personalbank.api;

import java.time.LocalDateTime;
import java.util.Objects;

/** Immutable raw projection of one legacy personal-bank category. */
public record PersonalBankCategoryView(
        int id,
        long userId,
        String name,
        String description,
        Integer sortOrder,
        LocalDateTime createdAt,
        LocalDateTime updatedAt,
        long bankCount
) {

    public PersonalBankCategoryView {
        Objects.requireNonNull(name, "name");
        if (bankCount < 0) {
            throw new IllegalArgumentException("bankCount must not be negative");
        }
    }
}
