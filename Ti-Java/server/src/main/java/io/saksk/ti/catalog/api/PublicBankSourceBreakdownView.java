package io.saksk.ti.catalog.api;

public record PublicBankSourceBreakdownView(long system, long userPublic) {

    public PublicBankSourceBreakdownView {
        if (system < 0 || userPublic < 0) {
            throw new IllegalArgumentException("source counts must be nonnegative");
        }
    }
}
