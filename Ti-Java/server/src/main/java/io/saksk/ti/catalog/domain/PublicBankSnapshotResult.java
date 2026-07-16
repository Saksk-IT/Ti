package io.saksk.ti.catalog.domain;

import java.util.Objects;

public record PublicBankSnapshotResult<T>(PublicBankSnapshot snapshot, T data) {

    public PublicBankSnapshotResult {
        Objects.requireNonNull(snapshot, "snapshot");
        Objects.requireNonNull(data, "data");
    }
}
