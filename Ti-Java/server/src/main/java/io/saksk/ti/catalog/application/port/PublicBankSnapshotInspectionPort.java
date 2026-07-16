package io.saksk.ti.catalog.application.port;

import io.saksk.ti.catalog.domain.PublicBankSnapshot;

/** Constant-time snapshot marker inspection used by readiness, never by compatibility payloads. */
@FunctionalInterface
public interface PublicBankSnapshotInspectionPort {

    PublicBankSnapshot inspect();
}
