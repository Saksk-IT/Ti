package io.saksk.ti.personalbank.api;

import java.time.LocalDateTime;

/** Immutable raw projection of one legacy personal-bank share row. */
public record PersonalBankShareView(
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
        LocalDateTime createdAt
) {
}
