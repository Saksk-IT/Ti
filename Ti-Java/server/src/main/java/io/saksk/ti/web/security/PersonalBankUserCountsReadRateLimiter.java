package io.saksk.ti.web.security;

import io.saksk.ti.web.security.PersonalBankUserCountsReadRequestResolver.Alias;
import java.util.Objects;

/** Independent fixed-window limiter for the two protected user-counts aliases. */
public interface PersonalBankUserCountsReadRateLimiter {

    Decision acquireForIdentity(Alias alias, long identityId);

    Decision acquireForAddress(Alias alias, String clientAddress);

    enum Window {
        SECOND("second"),
        HOUR("hour"),
        DAY("day");

        private final String legacyUnit;

        Window(String legacyUnit) {
            this.legacyUnit = legacyUnit;
        }
    }

    record Decision(
            boolean allowed,
            Window window,
            int limit,
            int remaining,
            long retryAfterSeconds,
            long resetAtEpochSecond
    ) {
        public Decision {
            Objects.requireNonNull(window, "window");
            if (limit < 1
                    || remaining < 0
                    || remaining > limit
                    || !allowed && remaining != 0
                    || retryAfterSeconds < 1
                    || retryAfterSeconds > 86_401
                    || resetAtEpochSecond < 1) {
                throw new IllegalArgumentException("Invalid user-counts rate-limit decision");
            }
        }

        public String legacyLimitDescription() {
            return limit + " per 1 " + window.legacyUnit;
        }
    }
}
