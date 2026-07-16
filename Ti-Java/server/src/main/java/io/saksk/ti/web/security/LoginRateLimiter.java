package io.saksk.ti.web.security;

public interface LoginRateLimiter {

    Decision acquire(String remoteAddress, String loginIdentifier);

    record Decision(boolean allowed, int limit, int remaining, long retryAfterSeconds) {
        public Decision {
            if (limit < 1
                    || remaining < 0
                    || remaining > limit
                    || retryAfterSeconds < 1
                    || retryAfterSeconds > 60) {
                throw new IllegalArgumentException("Invalid login rate-limit decision");
            }
        }
    }
}
