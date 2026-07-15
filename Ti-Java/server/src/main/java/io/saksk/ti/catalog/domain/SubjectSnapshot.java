package io.saksk.ti.catalog.domain;

import java.time.LocalDateTime;

/**
 * Read-only legacy subject state used inside catalog while Phase 4 behavior is still pending.
 * Foreign identifiers remain scalar values and never become cross-aggregate JPA associations.
 */
public record SubjectSnapshot(
        int id,
        String name,
        String description,
        Boolean locked,
        Integer plazaBoardId,
        boolean plazaFeatured,
        int plazaFeaturedWeight,
        LocalDateTime plazaFeaturedAt,
        LocalDateTime createdAt) {

    public SubjectSnapshot {
        if (id <= 0 || name == null || name.isBlank()) {
            throw new IllegalArgumentException("subject snapshot requires a positive id and name");
        }
    }
}
