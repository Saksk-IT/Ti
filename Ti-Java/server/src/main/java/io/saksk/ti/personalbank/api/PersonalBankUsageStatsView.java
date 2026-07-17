package io.saksk.ti.personalbank.api;

/** Immutable HTTP-neutral usage counts for one legacy personal bank. */
public record PersonalBankUsageStatsView(
        int bankId,
        boolean publicBank,
        long ownerId,
        int ownerCount,
        int sharedUsers,
        int publicUsers,
        int totalUsers,
        int totalUsersExcludingOwner
) {
}
