package io.saksk.ti.catalog.infrastructure.persistence;

import io.saksk.ti.catalog.domain.SubjectSnapshot;
import jakarta.persistence.Access;
import jakarta.persistence.AccessType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import org.hibernate.annotations.Immutable;

/** Exact, read-only mapping of the current legacy {@code subjects} schema. */
@Entity(name = "CatalogSubjectRead")
@Table(name = "subjects")
@Access(AccessType.FIELD)
@Immutable
public class SubjectReadEntity {

    @Id
    @Column(name = "id", nullable = false, insertable = false, updatable = false)
    private Integer id;

    @Column(name = "name", nullable = false, insertable = false, updatable = false)
    private String name;

    @Column(name = "description", insertable = false, updatable = false)
    private String description;

    @Column(name = "is_locked", insertable = false, updatable = false)
    private Boolean locked;

    @Column(name = "plaza_board_id", insertable = false, updatable = false)
    private Integer plazaBoardId;

    @Column(name = "is_plaza_featured", nullable = false, insertable = false, updatable = false)
    private boolean plazaFeatured;

    @Column(name = "plaza_featured_weight", nullable = false, insertable = false, updatable = false)
    private int plazaFeaturedWeight;

    @Column(name = "plaza_featured_at", insertable = false, updatable = false)
    private LocalDateTime plazaFeaturedAt;

    @Column(name = "created_at", insertable = false, updatable = false)
    private LocalDateTime createdAt;

    protected SubjectReadEntity() {}

    SubjectReadEntity(
            Integer id,
            String name,
            String description,
            Boolean locked,
            Integer plazaBoardId,
            boolean plazaFeatured,
            int plazaFeaturedWeight,
            LocalDateTime plazaFeaturedAt,
            LocalDateTime createdAt) {
        this.id = id;
        this.name = name;
        this.description = description;
        this.locked = locked;
        this.plazaBoardId = plazaBoardId;
        this.plazaFeatured = plazaFeatured;
        this.plazaFeaturedWeight = plazaFeaturedWeight;
        this.plazaFeaturedAt = plazaFeaturedAt;
        this.createdAt = createdAt;
    }

    SubjectSnapshot toSnapshot() {
        return new SubjectSnapshot(
                id,
                name,
                description,
                locked,
                plazaBoardId,
                plazaFeatured,
                plazaFeaturedWeight,
                plazaFeaturedAt,
                createdAt);
    }
}
