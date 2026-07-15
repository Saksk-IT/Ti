package io.saksk.ti.web.contract;

public record PaginationMeta(
        int page,
        int pageSize,
        long totalItems,
        int totalPages,
        boolean hasNext,
        boolean hasPrevious
) {

    public static PaginationMeta of(int page, int pageSize, long totalItems) {
        validateInputs(page, pageSize, totalItems);
        long totalPagesLong = totalItems / pageSize + (totalItems % pageSize == 0 ? 0 : 1);
        if (totalPagesLong > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("totalPages exceeds the supported integer range");
        }
        int totalPages = (int) totalPagesLong;
        return new PaginationMeta(
                page,
                pageSize,
                totalItems,
                totalPages,
                page < totalPages,
                page > 1
        );
    }

    public PaginationMeta {
        validateInputs(page, pageSize, totalItems);
        long expectedTotalPages = totalItems / pageSize + (totalItems % pageSize == 0 ? 0 : 1);
        if (expectedTotalPages > Integer.MAX_VALUE || totalPages != (int) expectedTotalPages) {
            throw new IllegalArgumentException("totalPages must be derived from pageSize and totalItems");
        }
        if (hasNext != (page < totalPages)) {
            throw new IllegalArgumentException("hasNext is inconsistent with page and totalPages");
        }
        if (hasPrevious != (page > 1)) {
            throw new IllegalArgumentException("hasPrevious is inconsistent with page");
        }
    }

    private static void validateInputs(int page, int pageSize, long totalItems) {
        if (page < 1) {
            throw new IllegalArgumentException("page must be at least 1");
        }
        if (pageSize < 1 || pageSize > 100) {
            throw new IllegalArgumentException("pageSize must be between 1 and 100");
        }
        if (totalItems < 0) {
            throw new IllegalArgumentException("totalItems must not be negative");
        }
    }
}
