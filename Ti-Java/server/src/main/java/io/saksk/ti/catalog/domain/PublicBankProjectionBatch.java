package io.saksk.ti.catalog.domain;

import io.saksk.ti.catalog.api.PublicBankRef;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/** A complete replacement generation, including all visible banks and viewer state. */
public record PublicBankProjectionBatch(
        PublicBankSnapshotCommit commit,
        List<PublicBankMetricProjection> metrics,
        List<PublicBankViewerProjection> viewers
) {

    public PublicBankProjectionBatch {
        Objects.requireNonNull(commit, "commit");
        metrics = List.copyOf(Objects.requireNonNull(metrics, "metrics"));
        viewers = List.copyOf(Objects.requireNonNull(viewers, "viewers"));

        Set<PublicBankRef> metricReferences = new HashSet<>();
        for (PublicBankMetricProjection metric : metrics) {
            Objects.requireNonNull(metric, "metric");
            if (!metricReferences.add(metric.reference())) {
                throw new IllegalArgumentException(
                        "duplicate public-bank metric reference: " + metric.reference());
            }
        }

        Set<ViewerKey> viewerKeys = new HashSet<>();
        for (PublicBankViewerProjection viewer : viewers) {
            Objects.requireNonNull(viewer, "viewer");
            if (!metricReferences.contains(viewer.reference())) {
                throw new IllegalArgumentException(
                        "viewer projection references a non-visible bank: "
                                + viewer.reference());
            }
            ViewerKey key = new ViewerKey(viewer.identityId(), viewer.reference());
            if (!viewerKeys.add(key)) {
                throw new IllegalArgumentException("duplicate public-bank viewer projection: " + key);
            }
        }
    }

    private record ViewerKey(long identityId, PublicBankRef reference) {}
}
