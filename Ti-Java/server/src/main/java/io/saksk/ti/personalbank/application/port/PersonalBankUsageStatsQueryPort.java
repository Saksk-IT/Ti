package io.saksk.ti.personalbank.application.port;

import java.util.List;
import java.util.Optional;

/** Reads the three sequential legacy projections used to calculate bank usage statistics. */
public interface PersonalBankUsageStatsQueryPort {

    Optional<BankAccess> findBank(int bankId);

    List<SharedUserAccess> listSharedUsers(int bankId);

    List<Object> listPublicUserIds(int bankId);

    record BankAccess(
            int bankId,
            Long ownerId,
            Boolean publicBank,
            Integer status
    ) {
    }

    record SharedUserAccess(Object userId, Object expiresAt) {
    }
}
