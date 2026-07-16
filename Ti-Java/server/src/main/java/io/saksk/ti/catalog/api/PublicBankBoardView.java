package io.saksk.ti.catalog.api;

import java.util.Objects;

public record PublicBankBoardView(
        long id,
        String slug,
        String name,
        String description,
        long bankCount
) {

    public PublicBankBoardView {
        Objects.requireNonNull(slug, "slug");
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(description, "description");
        if (id <= 0 || bankCount < 0) {
            throw new IllegalArgumentException("board id/count must be valid");
        }
    }
}
