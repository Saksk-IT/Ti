package io.saksk.ti.personalbank.api;

/** Server-derived caller identity for protected personal-bank operations. */
public record AuthenticatedPersonalBankViewer(long identityId) {

    public AuthenticatedPersonalBankViewer {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
    }
}
