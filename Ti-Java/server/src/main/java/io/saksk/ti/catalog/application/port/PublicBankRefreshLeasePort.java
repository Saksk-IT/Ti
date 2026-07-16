package io.saksk.ti.catalog.application.port;

import java.util.Optional;

/** Advisory Redis lease used only to suppress duplicate public-bank projection work. */
public interface PublicBankRefreshLeasePort {

    Optional<Lease> tryAcquire();

    ReleaseOutcome release(Lease lease);

    record Lease(String token) {

        public Lease {
            if (token == null || !token.matches("[A-Za-z0-9_-]{43}")) {
                throw new IllegalArgumentException("Invalid public-bank refresh lease token");
            }
        }
    }

    enum ReleaseOutcome {
        RELEASED,
        LOST
    }
}
