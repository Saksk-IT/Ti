package io.saksk.ti.catalog.api;

/** Viewer relationship projected into the catalog snapshot. */
public enum PublicBankRelation {
    NONE(false),
    PUBLIC(true),
    SHARED(true),
    BOTH(true);

    private final boolean joined;

    PublicBankRelation(boolean joined) {
        this.joined = joined;
    }

    public boolean joined() {
        return joined;
    }

    public static PublicBankRelation fromFlags(boolean hasPublic, boolean hasShared) {
        if (hasPublic && hasShared) {
            return BOTH;
        }
        if (hasPublic) {
            return PUBLIC;
        }
        if (hasShared) {
            return SHARED;
        }
        return NONE;
    }
}
