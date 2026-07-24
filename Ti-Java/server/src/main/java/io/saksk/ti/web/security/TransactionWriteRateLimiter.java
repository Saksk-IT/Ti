package io.saksk.ti.web.security;

import io.saksk.ti.web.security.TransactionWriteRequestResolver.Route;

/** Independent per-route fixed-minute limiter for Phase 4C transaction writes. */
public interface TransactionWriteRateLimiter {

    Decision acquireForIdentity(Route route, long identityId);

    Decision acquireForAddress(Route route, String clientAddress);

    record Decision(
            boolean allowed,
            int limit,
            int remaining,
            long retryAfterSeconds,
            long resetAtEpochSecond
    ) {
        public Decision {
            if (limit < 1
                    || remaining < 0
                    || remaining > limit
                    || !allowed && remaining != 0
                    || retryAfterSeconds < 1
                    || retryAfterSeconds > 61
                    || resetAtEpochSecond < 1) {
                throw new IllegalArgumentException(
                        "Invalid transaction-write rate-limit decision");
            }
        }

        public String legacyLimitDescription() {
            return limit + " per 1 minute";
        }
    }
}
