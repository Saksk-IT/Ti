package io.saksk.ti.web.security;

/** Legacy-compatible limiter for the seven public-bank catalog reads. */
public interface PublicBankReadRateLimiter {

    Decision acquireForIdentity(PublicBankReadRequestResolver.Route route, long identityId);

    Decision acquireForAddress(PublicBankReadRequestResolver.Route route, String clientAddress);

    record Decision(
            boolean allowed,
            int limit,
            int remaining,
            long retryAfterSeconds,
            long resetAtEpochSecond,
            String legacyLimitDescription
    ) {
        public Decision {
            if (limit < 1
                    || remaining < 0
                    || remaining > limit
                    || retryAfterSeconds < 1
                    || retryAfterSeconds > 86_401
                    || resetAtEpochSecond < 1
                    || legacyLimitDescription == null
                    || legacyLimitDescription.isBlank()) {
                throw new IllegalArgumentException("Invalid public-bank rate-limit decision");
            }
        }
    }
}
