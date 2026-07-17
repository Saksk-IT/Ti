package io.saksk.ti.personalbank.api;

import java.time.LocalDateTime;
import java.util.Objects;

/** Immutable raw projection of one share owned by the authenticated viewer. */
public record PersonalBankOwnedShareView(
        int id,
        int bankId,
        long ownerId,
        String shareCode,
        String shareToken,
        String permission,
        LocalDateTime expiresAt,
        Integer maxUses,
        Integer currentUses,
        Boolean isActive,
        LocalDateTime createdAt,
        String bankName
) {

    public PersonalBankOwnedShareView {
        Objects.requireNonNull(bankName, "bankName");
    }
}
