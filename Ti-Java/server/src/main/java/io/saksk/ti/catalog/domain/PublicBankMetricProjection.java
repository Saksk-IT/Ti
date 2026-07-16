package io.saksk.ti.catalog.domain;

import io.saksk.ti.catalog.api.PublicBankRef;
import java.time.LocalDateTime;
import java.util.Objects;

/** One catalog-owned public-bank metric row supplied to the snapshot projector. */
public record PublicBankMetricProjection(
        PublicBankRef reference,
        String name,
        String description,
        String coverImage,
        Long ownerId,
        String ownerLabel,
        String ownerAvatar,
        long questionCountTotal,
        Integer boardId,
        boolean featured,
        int featuredWeight,
        LocalDateTime publishedAt,
        LocalDateTime lastActivityAt,
        long joinCountTotal,
        long joinUsers7d,
        long joinUsers30d,
        long answerCount7d,
        long answerCount30d,
        long answerUsers7d,
        long answerUsers30d,
        double hotScore,
        double activeScore,
        double recommendedScore,
        String joinMode,
        String joinNote,
        boolean allowCopy,
        long shareCount
) {

    public PublicBankMetricProjection {
        Objects.requireNonNull(reference, "reference");
        if (reference.id() <= 0) {
            throw new IllegalArgumentException("projection source ID must be positive");
        }
        name = requireNonBlank(name, "name");
        ownerLabel = Objects.requireNonNull(ownerLabel, "ownerLabel");
        joinMode = requireNonBlank(joinMode, "joinMode");
        joinNote = Objects.requireNonNull(joinNote, "joinNote");
        if (ownerId != null && ownerId <= 0) {
            throw new IllegalArgumentException("ownerId must be positive when present");
        }
        if (boardId != null && boardId <= 0) {
            throw new IllegalArgumentException("boardId must be positive when present");
        }
        if (featuredWeight < 0
                || questionCountTotal < 0
                || joinCountTotal < 0
                || joinUsers7d < 0
                || joinUsers30d < 0
                || answerCount7d < 0
                || answerCount30d < 0
                || answerUsers7d < 0
                || answerUsers30d < 0
                || shareCount < 0) {
            throw new IllegalArgumentException("projection counters must be nonnegative");
        }
        if (!Double.isFinite(hotScore)
                || !Double.isFinite(activeScore)
                || !Double.isFinite(recommendedScore)) {
            throw new IllegalArgumentException("projection scores must be finite");
        }
    }

    private static String requireNonBlank(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " must not be blank");
        }
        return value;
    }
}
