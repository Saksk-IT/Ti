package io.saksk.ti.catalog.api;

import java.time.LocalDateTime;
import java.util.Objects;

public record PublicBankCardView(
        long id,
        PublicBankSource source,
        String name,
        String description,
        String coverImage,
        String ownerLabel,
        String ownerAvatar,
        long questionCount,
        long participantsTotal,
        long joinUsers7d,
        long answerUsers7d,
        long answerCount7d,
        double hotScore,
        double activeScore,
        double recommendedScore,
        LocalDateTime publishedAt,
        LocalDateTime lastActivityAt,
        boolean featured,
        int featuredWeight,
        PublicBankBoardRef board,
        String joinMode,
        String joinNote,
        boolean allowCopy,
        PublicBankRelationView relation
) {

    public PublicBankCardView {
        Objects.requireNonNull(source, "source");
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(description, "description");
        Objects.requireNonNull(ownerLabel, "ownerLabel");
        Objects.requireNonNull(board, "board");
        Objects.requireNonNull(joinMode, "joinMode");
        Objects.requireNonNull(joinNote, "joinNote");
        Objects.requireNonNull(relation, "relation");
        if (id < 0 || questionCount < 0 || participantsTotal < 0 || joinUsers7d < 0
                || answerUsers7d < 0 || answerCount7d < 0 || featuredWeight < 0) {
            throw new IllegalArgumentException("public-bank counts and ids must be nonnegative");
        }
    }
}
