package io.saksk.ti.catalog.api;

import java.util.Objects;

public record PublicBankDetailView(
        PublicBankCardView card,
        long shareCount,
        Long authorId,
        boolean owner
) {

    public PublicBankDetailView {
        Objects.requireNonNull(card, "card");
        if (shareCount < 0 || authorId != null && authorId <= 0) {
            throw new IllegalArgumentException("detail counts and author id must be valid");
        }
        if (card.source() == PublicBankSource.SYSTEM && (authorId != null || owner)) {
            throw new IllegalArgumentException("system banks cannot have a projected user owner");
        }
    }
}
