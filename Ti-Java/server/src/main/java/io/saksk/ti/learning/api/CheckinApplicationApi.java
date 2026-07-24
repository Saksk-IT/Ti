package io.saksk.ti.learning.api;

/** Public learning boundary for the legacy daily check-in write. */
public interface CheckinApplicationApi {

    CheckinResult checkIn(CheckinCommand command);
}
