package io.saksk.ti.catalog.api;

/** Server-derived caller identity for protected catalog reads. */
public record AuthenticatedCatalogViewer(long identityId) {

    public AuthenticatedCatalogViewer {
        if (identityId <= 0) {
            throw new IllegalArgumentException("identityId must be positive");
        }
    }
}
