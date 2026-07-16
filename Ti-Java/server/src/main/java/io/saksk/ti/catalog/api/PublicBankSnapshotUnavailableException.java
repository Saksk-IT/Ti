package io.saksk.ti.catalog.api;

/** Safe public signal for cold, partial, inconsistent or hard-expired catalog snapshots. */
public final class PublicBankSnapshotUnavailableException extends RuntimeException {

    public PublicBankSnapshotUnavailableException() {
        super("Public bank snapshot is unavailable");
    }
}
