package io.saksk.ti.catalog.api;

public record PublicBankBoardRef(Integer id, String slug, String name) {

    public PublicBankBoardRef {
        if (id != null && id <= 0) {
            throw new IllegalArgumentException("board id must be positive when present");
        }
        slug = slug == null || slug.isBlank() ? null : slug;
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("board name must not be blank");
        }
    }
}
