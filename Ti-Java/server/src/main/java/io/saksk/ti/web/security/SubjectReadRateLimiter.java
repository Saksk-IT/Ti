package io.saksk.ti.web.security;

/** Per-identity compatibility limiter for the protected subject-directory reads. */
public interface SubjectReadRateLimiter {

    Decision acquire(Route route, long identityId);

    enum Route {
        SUBJECTS("subjects"),
        SUBJECTS_META("subjects-meta");

        private final String key;

        Route(String key) {
            this.key = key;
        }

        String key() {
            return key;
        }
    }

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
                    || retryAfterSeconds > 3_600
                    || resetAtEpochSecond < 1
                    || legacyLimitDescription == null
                    || legacyLimitDescription.isBlank()) {
                throw new IllegalArgumentException("Invalid subject-read rate-limit decision");
            }
        }
    }
}
