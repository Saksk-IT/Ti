package io.saksk.ti.personalbank.api;

import java.util.List;

/** Immutable raw projection of the legacy share-list result. */
public record PersonalBankShareListView(List<PersonalBankShareView> shares) {

    public PersonalBankShareListView {
        shares = List.copyOf(shares);
    }
}
