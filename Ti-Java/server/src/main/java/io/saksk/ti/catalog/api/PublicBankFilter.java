package io.saksk.ti.catalog.api;

import java.util.Locale;
import java.util.Objects;
import java.util.Optional;

public record PublicBankFilter(
        Optional<Long> boardId,
        String keyword,
        Optional<PublicBankSource> source
) {

    public PublicBankFilter {
        Objects.requireNonNull(boardId, "boardId");
        Objects.requireNonNull(keyword, "keyword");
        Objects.requireNonNull(source, "source");
        boardId.ifPresent(value -> {
            if (value <= 0) {
                throw new IllegalArgumentException("boardId must be positive when present");
            }
        });
        keyword = normalizeKeyword(keyword);
    }

    public static PublicBankFilter all() {
        return new PublicBankFilter(Optional.empty(), "", Optional.empty());
    }

    public static String normalizeKeyword(String value) {
        return String.join(" ", value.strip().toLowerCase(Locale.ROOT).split("\\s+"));
    }
}
