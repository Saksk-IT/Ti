package io.saksk.ti.catalog.api;

import java.util.Objects;

public record PublicBankSummaryView(
        long totalBanks,
        long totalQuestions,
        long totalBoards,
        long newBanks7d,
        long activeUsers7d,
        PublicBankSourceBreakdownView sourceBreakdown
) {

    public PublicBankSummaryView {
        Objects.requireNonNull(sourceBreakdown, "sourceBreakdown");
        if (totalBanks < 0 || totalQuestions < 0 || totalBoards < 0
                || newBanks7d < 0 || activeUsers7d < 0) {
            throw new IllegalArgumentException("summary counts must be nonnegative");
        }
    }
}
