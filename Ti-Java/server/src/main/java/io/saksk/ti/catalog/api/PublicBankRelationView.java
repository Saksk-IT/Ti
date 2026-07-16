package io.saksk.ti.catalog.api;

import java.util.Objects;

public record PublicBankRelationView(PublicBankRelation joinedVia, boolean joined) {

    public static final PublicBankRelationView NONE =
            new PublicBankRelationView(PublicBankRelation.NONE, false);

    public PublicBankRelationView {
        Objects.requireNonNull(joinedVia, "joinedVia");
        if (joined != joinedVia.joined()) {
            throw new IllegalArgumentException("joined must match joinedVia");
        }
    }

    public static PublicBankRelationView fromFlags(boolean hasPublic, boolean hasShared) {
        PublicBankRelation relation = PublicBankRelation.fromFlags(hasPublic, hasShared);
        return new PublicBankRelationView(relation, relation.joined());
    }
}
